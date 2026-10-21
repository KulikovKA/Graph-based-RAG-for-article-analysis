"""Keep HOLDOUT annotations outside the repository and experiment inputs."""
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent


def private_root():
    p=BASE/'annotations/private_holdout_location.json'
    return Path(json.loads(p.read_text(encoding='utf-8'))['path']) if p.exists() else Path.home()/'.codex/private/graph_gold_pilot24'


def draft_paths():
    return sorted((BASE/'annotations/drafts').glob('*.jsonl'))+sorted((private_root()/'drafts').glob('*.jsonl'))


def draft_path(code,split):
    return (private_root()/'drafts' if split=='HOLDOUT' else BASE/'annotations/drafts')/(code+'.jsonl')
