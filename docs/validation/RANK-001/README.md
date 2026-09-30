# RANK-001 CPU benchmark

The frozen EVAL-000 synthetic dev fixtures compare deterministic BM25 with the
pinned `Qwen/Qwen3-Reranker-0.6B` CPU cross-encoder. Run from the repository root
with the inference extra and already cached model:

```powershell
python scripts/benchmark_rerank_evidence.py
```

The run scored all eight fixture documents for each of the nine labeled cases.
Qwen was selected because it improved Recall@3 from 0.889 to 1.000, while MRR
was 1.000 for both. Its median elapsed time was about 2.30 seconds per case
including the cold first request (9.54 seconds); the remaining warm calls were
about 2.18–2.45 seconds. BM25's median was 0.24 ms. Exact per-case values and pinned
model revision are in `benchmark.json`.

This is a small CPU quality/latency check, not a production latency guarantee.
It ranks the complete eight-document fixture corpus rather than an online
retrieval candidate distribution. The selected cross-encoder is optional and
injected through the inference provider; BM25 is an explicit deterministic
fallback when no scorer is configured. Evaluation is limited to synthetic dev
cases and does not establish semantic faithfulness.
