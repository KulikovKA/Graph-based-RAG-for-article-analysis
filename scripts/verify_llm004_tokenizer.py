"""Reproduce the LLM-004 GPT-OSS tokenizer/template compatibility check."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TOKENIZER = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".cache/llm004-tokenizer/tokenizer.json"
EXPECTED_SHA256 = "0614fe83cadab421296e664e1f48f4261fa8fef6e03e63bb75c20f38e37d07d3"
MODELS = ("gpt-oss:20b", "ducquoc/gpt-oss-sonnet:latest")
BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def api(path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(BASE + path, data=data,
                      headers={"Content-Type": "application/json"} if data else {})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    from tokenizers import Tokenizer

    raw = TOKENIZER.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != EXPECTED_SHA256:
        raise SystemExit(f"Tokenizer SHA mismatch: {actual_sha}")
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    upstream_vocab_size = len(tokenizer.get_vocab(with_added_tokens=True))
    merges = json.loads(tokenizer.to_str())["model"]["merges"]
    if merges and isinstance(merges[0], list):
        merges = [" ".join(row) for row in merges]

    checks: dict[str, object] = {}
    templates: set[str] = set()
    for model in MODELS:
        info = api("/api/show", {"model": model, "verbose": True})
        model_info = info["model_info"]
        tokens = model_info["tokenizer.ggml.tokens"]
        gguf_merges = model_info["tokenizer.ggml.merges"]
        shared_vocab_match = all(tokenizer.id_to_token(i) == tokens[i]
                                 for i in range(upstream_vocab_size))
        merges_match = merges == gguf_merges
        template_sha = hashlib.sha256(str(info["template"]).encode()).hexdigest()
        templates.add(template_sha)
        checks[model] = {
            "architecture": model_info["general.architecture"],
            "context_length": model_info["gptoss.context_length"],
            "ollama_vocab_entries": len(tokens),
            "upstream_vocab_entries": upstream_vocab_size,
            "ollama_padding_tokens": len(tokens) - upstream_vocab_size,
            "shared_vocab_ids_match": shared_vocab_match,
            "bpe_merge_count": len(gguf_merges),
            "bpe_merges_match": merges_match,
            "template_sha256": template_sha,
            "thinking_profiles": info.get("thinking", {}).get("values", []),
        }
    result = {
        "tokenizer_source": "https://huggingface.co/openai/gpt-oss-20b",
        "tokenizer_revision": "6cee5e81ee83917806bbde320786a8fb61efebee",
        "tokenizer_file": "tokenizer.json",
        "tokenizer_sha256": actual_sha,
        "tokenizer_bytes": len(raw),
        "models": checks,
        "templates_identical": len(templates) == 1,
        "compatible": len(templates) == 1 and all(
            c["shared_vocab_ids_match"] and c["bpe_merges_match"] for c in checks.values()
        ),
    }
    target = ROOT / "docs/validation/LLM-004/tokenizer_verification.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["compatible"]:
        raise SystemExit("Tokenizer contract mismatch")


if __name__ == "__main__":
    main()
