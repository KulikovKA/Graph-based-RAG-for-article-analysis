"""Проверка плана и закреплённых версий источников без проверки работы приложения."""
import argparse
import hashlib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]


def check(online=False):
    text = (ROOT / 'TASKS.md').read_text(encoding='utf-8')
    rows = {}
    for row in text.splitlines():
        if re.match(r'\| [A-Z]+-\d{3} \|', row):
            values = [x.strip() for x in row.split('|')[1:-1]]
            assert values[0] not in rows, ('duplicate row', values[0])
            rows[values[0]] = values
    cards = {}
    costs = {}
    for match in re.finditer(r'^### ([A-Z]+-\d{3}) — (.*?)(?=^### |^## Milestones|\Z)', text, re.M | re.S):
        task, body = match.groups()
        assert task not in cards
        dep, priority = re.search(r'\*\*Depends / priority:\*\* ([^;]+); (P\d)', body).groups()
        deps = [] if dep == 'нет' else dep.split(',')
        model = re.search(r'\*\*Модель:\*\* ([^.]+)\.', body)[1].replace(' ', '')
        size = re.search(r'\*\*Размер:\*\* [SML], ([\d.]+)–([\d.]+) ч', body)
        review = re.search(r'(?:review (\d+) мин|(\d+) мин review)', body)
        assert size, ('missing estimate',task)
        assert review, ('missing review estimate',task)
        assert '**Приёмка/тесты:**' in body and '**Не делать:**' in body, task
        cards[task] = {'depends':deps, 'priority':priority, 'model':model}
        costs[task] = [float(size[1]), float(size[2]), int(review[1] or review[2])]
        assert task in rows
        row = rows[task]
        assert row[2] == priority and row[3].replace(' ','') == model, ('metadata mismatch',task)
        assert ([] if row[4]=='—' else row[4].split(',')) == deps, ('depends mismatch',task)
    assert set(cards) == set(rows)
    for task,c in cards.items():
        assert set(c['depends']) <= set(cards), ('unknown dependency', task)
        assert task not in c['depends']
    visited, active, topo = set(), set(), []
    def visit(task):
        assert task not in active, ('cycle', task)
        if task in visited:
            return
        active.add(task)
        for dep in cards[task]['depends']:
            visit(dep)
        active.remove(task)
        visited.add(task)
        topo.append(task)
    for task in cards:
        visit(task)
    roots = [t for t,c in cards.items() if not c['depends']]
    assert roots == ['ARCH-001'], roots
    for task,c in cards.items():
        if c['priority'] == 'P0':
            def closure(t):
                return {t} | set().union(*(closure(d) for d in cards[t]['depends']))
            assert all(cards[d]['priority']=='P0' for d in closure(task)), ('P0 blocked by P1',task)
    mermaid = re.search(r'```mermaid\n(.*?)```',text,re.S)[1]
    aliases = dict(re.findall(r'^\s+(\w+)\[([A-Z]+-\d{3})\]',mermaid,re.M))
    actual_edges = {(aliases[a],aliases[b]) for a,b in re.findall(r'^\s+(\w+) --> (\w+)$',mermaid,re.M)}
    expected_edges = {(d,t) for t,c in cards.items() for d in c['depends']}
    assert actual_edges == expected_edges, ('mermaid mismatch',actual_edges ^ expected_edges)
    assert set(aliases.values()) == set(cards)

    manifest = json.loads((ROOT/'docs/donors.lock.json').read_text(encoding='utf-8'))
    pinned_urls = {f['url'] for d in manifest['donors'] for f in d['files']}
    link_count = 0
    # Исторический отчёт ARCH-001 неизменяем и участвует в проверке ссылок.
    docs = [ROOT/'README.md', ROOT/'TASKS.md', ROOT/'task.md', *sorted((ROOT/'docs').rglob('*.md'))]
    for path in docs:
        content = path.read_text(encoding='utf-8')
        for url in re.findall(r'https://github.com/[^\s)]+/blob/[^\s)]+',content):
            assert url in pinned_urls, ('unverified donor link',path,url)
        for target in re.findall(r'\]\(([^)]+)\)',content):
            if '://' in target or target.startswith('#'):
                continue
            relative = target.split('#',1)[0]
            assert (path.parent/relative).exists(), ('broken local link',path,target)
            link_count += 1
    source_results = []
    if online:
        def get(url):
            request = Request(url,headers={'User-Agent':'ARCH-002-planning-audit'})
            with urlopen(request,timeout=30) as response:
                return response.read()
        def verify_donor(donor):
            data = json.loads(get(f"https://api.github.com/repos/{donor['repository']}/commits/{donor['commit']}"))
            assert data['sha']==donor['commit'] and data['commit']['tree']['sha']==donor['tree']
            return {'repository':donor['repository'],'commit':donor['commit'],'tree_verified':True}
        def verify_file(pair):
            donor, f = pair
            url = f"https://raw.githubusercontent.com/{donor['repository']}/{donor['commit']}/{f['path']}"
            assert hashlib.sha256(get(url)).hexdigest()==f['sha256'], url
            return f['url']
        with ThreadPoolExecutor(max_workers=4) as pool:
            source_results = list(pool.map(verify_donor,manifest['donors']))
            files = list(pool.map(verify_file,[(d,f) for d in manifest['donors'] for f in d['files']]))
        assert len(files) == len(pinned_urls)
    totals = [sum(c[i] for c in costs.values()) for i in range(3)]
    future = [t for t in cards if t not in {'ARCH-001','ARCH-002'}]
    remaining = [sum(costs[t][i] for t in future) for i in range(3)]
    target_sized = [t for t in future if costs[t][1] <= 2]
    return {
        'task':'ARCH-002', 'status':'passed', 'tasks':len(cards),
        'hard_dependencies':len(expected_edges), 'roots':roots, 'topological_order':topo,
        'p0_tasks':sum(c['priority']=='P0' for c in cards.values()),
        'p0_has_no_p1_prerequisites':True, 'mermaid_matches_cards_and_table':True,
        'local_links_checked':link_count, 'donor_files':len(pinned_urls),
        'online_sources_verified':online, 'donors':source_results,
        'estimates_all':{'agent_hours_min':totals[0],'agent_hours_max':totals[1],'review_minutes':totals[2]},
        'estimates_remaining':{'agent_hours_min':remaining[0],'agent_hours_max':remaining[1],'review_minutes':remaining[2]},
        'implementation_tasks_max_2h':len(target_sized), 'implementation_tasks':len(future),
        'model_task_counts':dict(Counter(c['model'] for c in cards.values())),
        'limits':'Document structure and online source checks only; semantic review is recorded in ARCH_REVIEW.md. No production tests.'
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--online', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check(args.online)
    output = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.write_text(output,encoding='utf-8')
    print(output)
