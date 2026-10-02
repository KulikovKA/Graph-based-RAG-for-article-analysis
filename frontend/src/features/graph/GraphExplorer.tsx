import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../../api/client';
import type { GraphEdge, GraphNode, GraphView, Run } from '../../api/types';

const colors: Record<string, string> = {
  Idea: '#493c82', IdeaFeature: '#7563bb', Patent: '#187b78', ScientificWork: '#356da8',
};

export function GraphExplorer({ run, onCitation }: { run: Run; onCitation: (id: string) => void }) {
  const [graph, setGraph] = useState<GraphView | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [scale, setScale] = useState(1);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [neighborCursor, setNeighborCursor] = useState<string | null>(null);
  const baseIds = useRef<Set<string>>(new Set());
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  useEffect(() => {
    let active = true;
    setGraph(null); setSelected(null); setError(false); setExpanded(new Set()); setNeighborCursor(null);
    if (run.graph_url) void api.graph(run.id).then((value) => { if (active) { setGraph(value); baseIds.current = new Set(value.nodes.map((node) => node.id)); } }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [run.id, run.graph_url]);
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const positions = useMemo(() => nodes.map((node, index) => {
    const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2 - Math.PI / 2;
    const radius = node.type === 'Idea' ? 0 : node.type === 'IdeaFeature' ? 165 : 310;
    return { node, x: 430 + Math.cos(angle) * radius, y: 270 + Math.sin(angle) * radius };
  }), [nodes]);
  const positionById = new Map(positions.map((item) => [item.node.id, item]));
  const selectedNode = nodes.find((node) => node.id === selected);
  const expandedSource = nodes.find((node) => expanded.has(node.id));
  const pathEdges = useMemo(() => {
    if (!selected || !nodes.length) return new Set<string>();
    const root = nodes.find((node) => node.type === 'Idea')?.id;
    if (!root) return new Set<string>();
    const previous = new Map<string, GraphEdge>();
    const queue = [root];
    const visited = new Set(queue);
    while (queue.length) {
      const current = queue.shift()!;
      if (current === selected) break;
      for (const edge of edges) {
        const next = edge.source === current ? edge.target : edge.target === current ? edge.source : null;
        if (next && !visited.has(next)) { visited.add(next); previous.set(next, edge); queue.push(next); }
      }
    }
    const result = new Set<string>();
    let current = selected;
    while (previous.has(current)) { const edge = previous.get(current)!; result.add(edge.id); current = edge.source === current ? edge.target : edge.source; }
    return result;
  }, [edges, nodes, selected]);
  async function expand(node: GraphNode, cursor?: string) {
    try {
      const page = await api.graphNeighbors(run.id, node.id, cursor);
      setGraph((value) => value ? ({ ...value,
        nodes: [...value.nodes, ...page.nodes.filter((item) => !value.nodes.some((old) => old.id === item.id))].slice(0, 100),
        edges: [...value.edges, ...page.edges.filter((item) => !value.edges.some((old) => old.id === item.id))].slice(0, 200),
      }) : page);
      setExpanded((value) => new Set(value).add(node.id)); setNeighborCursor(page.next_cursor);
    } catch { setError(true); }
  }
  function collapse(node: GraphNode) {
    setExpanded((value) => { const next = new Set(value); next.delete(node.id); return next; });
    setNeighborCursor(null);
    setGraph((value) => value ? ({ ...value,
      nodes: value.nodes.filter((item) => baseIds.current.has(item.id) || !edges.some((edge) =>
        (edge.source === node.id && edge.target === item.id) || (edge.target === node.id && edge.source === item.id))),
      edges: value.edges.filter((edge) => baseIds.current.has(edge.source) && baseIds.current.has(edge.target)),
    }) : value);
  }
  if (!run.graph_url) return null;
  return <section className="graph-explorer" aria-label="Карта анализа">
    <header className="graph-heading"><div><span className="eyebrow">Карта анализа</span><p>Связи в сохранённом анализе и его источниках</p></div>
      <div className="graph-zoom"><button aria-label="Уменьшить" onClick={() => setScale((v) => Math.max(.65, v - .15))}>−</button><button aria-label="Увеличить" onClick={() => setScale((v) => Math.min(1.8, v + .15))}>+</button></div>
    </header>
    {error && <p className="muted" role="status">Карта пока недоступна. Обновите анализ или повторите загрузку.</p>}
    {!graph ? <p className="muted">Загружаем карту…</p> : nodes.length === 0 ? <p className="muted">Для этого результата нет графовых связей.</p> : <>
      <svg className="graph-canvas" viewBox="0 0 860 540" role="img" aria-label="Интерактивный граф связей"
        onPointerDown={(event) => { if (event.target === event.currentTarget) { event.currentTarget.setPointerCapture(event.pointerId); drag.current = { x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y }; } }}
        onPointerMove={(event) => { if (drag.current) { const box = event.currentTarget.getBoundingClientRect(); setPan({ x: drag.current.panX + (event.clientX - drag.current.x) * 860 / box.width, y: drag.current.panY + (event.clientY - drag.current.y) * 540 / box.height }); } }}
        onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
        <g transform={`translate(${430 * (1-scale) + pan.x} ${270 * (1-scale) + pan.y}) scale(${scale})`}>
          {edges.map((edge) => { const a = positionById.get(edge.source), b = positionById.get(edge.target); return a && b ? <line key={edge.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className={pathEdges.has(edge.id) ? 'graph-edge active' : 'graph-edge'} /> : null; })}
          {positions.map(({ node, x, y }) => <g key={node.id} className="graph-node" role="button" tabIndex={0} aria-label={node.label} onClick={() => setSelected(node.id)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') setSelected(node.id); }}>
            <circle cx={x} cy={y} r={node.type === 'Idea' ? 35 : node.type === 'IdeaFeature' ? 25 : 21} fill={colors[node.type] ?? '#718096'} />
            <text x={x} y={y + 4}>{node.label.length > 24 ? `${node.label.slice(0, 22)}…` : node.label}</text>
          </g>)}
        </g>
      </svg>
      <div className="graph-mobile-list">{nodes.map((node) => <button key={node.id} onClick={() => setSelected(node.id)}><span style={{ background: colors[node.type] ?? '#718096' }} />{node.label}</button>)}</div>
      {selectedNode && <aside className="graph-details"><button className="graph-close" aria-label="Закрыть детали" onClick={() => setSelected(null)}>×</button><span className="eyebrow">{selectedNode.type === 'IdeaFeature' ? 'Признак идеи' : selectedNode.type === 'TechnicalFeature' ? 'Признак из источника' : selectedNode.type === 'Idea' ? 'Идея' : 'Источник'}</span><strong>{selectedNode.label}</strong>
        <div className="graph-detail-actions">{selectedNode.evidence_ids.map((id, index) => <button className="text-button" key={id} onClick={() => onCitation(id)}>Открыть цитату {index + 1}</button>)}
          {expandedSource && selectedNode.id !== expandedSource.id && <button className="text-button" onClick={() => collapse(expandedSource)}>Свернуть связи</button>}
          {(selectedNode.type === 'Patent' || selectedNode.type === 'ScientificWork') && (expanded.has(selectedNode.id)
            ? <><button className="text-button" onClick={() => collapse(selectedNode)}>Свернуть связи</button>{neighborCursor && <button className="text-button" onClick={() => void expand(selectedNode, neighborCursor)}>Загрузить ещё 20</button>}</>
            : <button className="text-button" onClick={() => void expand(selectedNode)}>Раскрыть один hop</button>)}</div>
      </aside>}
      {graph.truncated && <p className="graph-note">Показана часть карты. Откройте узел, чтобы изучить его связи.</p>}
    </>}
  </section>;
}
