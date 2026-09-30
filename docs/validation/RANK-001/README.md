# RANK-001 CPU benchmark

The frozen EVAL-000 synthetic dev fixtures compare deterministic BM25 with the
pinned `Qwen/Qwen3-Reranker-0.6B` CPU cross-encoder. Run from the repository root
with the inference extra and already cached model:

```powershell
python scripts/benchmark_rerank_evidence.py
```

The run scored all eight fixture documents for each of the nine labeled cases.
Qwen was selected because it improved Recall@3 from 0.889 to 1.000, while MRR
was 1.000 for both. The repeated run measured a 2.09 second median, including
the 8.69 second cold request; warm calls were about 1.99–2.35 seconds. BM25's
median was 0.24 ms. Exact per-case values and pinned model revision are in
`benchmark.json`.

## Gemma Analyst prompt token budget

RANK-001's full prompt budget was repeated using the pinned Google Gemma 4
tokenizer. The 262,144 tokenizer IDs matched the selected Ollama GGUF vocabulary
with zero differences. The exact `tokenizer.json` SHA-256 and revision are pinned
in `config/models.yaml` and `docs/model_inventory.json`; `GemmaTokenCounter`
rejects a different file hash before counting.

The tokenizer-aware script evaluated nine EVAL-000 queries, counting both prompt
framing strings plus the full JSON serialization of every selected evidence item,
including IDs and metadata. All packs fit the 6,000-token budget; counts ranged
from 340 to 5,222 with a median of 4,935. Details are in
[`token_budget_gemma4.json`](token_budget_gemma4.json). The framing in this probe
is representative; ANALYST-001 must pass its final prompt framing to the same
counter when it builds an evidence pack.

This is a small CPU quality/latency check, not a production latency guarantee.
It ranks the complete eight-document fixture corpus rather than an online
retrieval candidate distribution. The selected cross-encoder is optional and
injected through the inference provider; BM25 is an explicit deterministic
fallback when no scorer is configured. Evaluation is limited to synthetic dev
cases and does not establish semantic faithfulness.
