# LLM-004 — frozen Analyst model comparison

Status: **complete for the user-directed low/medium matrix**. Production Analyst configuration remains pinned to
`gpt-oss:20b`; this benchmark does not edit production model configuration or
historical LLM-003 artifacts.

## Protocol

The benchmark uses the unchanged 18-case gold fixture at
`eval/llm003/analyst.jsonl` and the unchanged prompt at
`prompts/analyst_v1.txt`. Every profile receives the same deterministic
EvidencePack construction, AnalysisV1 contract and production Analyst
validator. Fixture and prompt SHA-256 values are recorded per run in
`results.json`. Exact-case scoring also requires the expected unresolved
feature state; there is no model-specific expectation and no LLM judge.

Only model ID and reasoning effort vary. Shared runtime settings are Ollama
0.34.4, temperature 0, top_p 0.9, 2,048 output tokens, 131,072 context,
600-second per-case timeout, and 3,600-second keep-alive. Generation is
sequential. Runtime-reported output token counts are retained only when
Ollama can distinguish final output from reasoning. Latencies include
validation; TTFT and generation duration are included where reported.

Before scoring, Ollama metadata and the exact pinned upstream tokenizer were
compared by `scripts/verify_llm004_tokenizer.py`. The file source, revision,
SHA-256, token IDs, BPE merge equality, GGUF padding-token count, architecture,
context and template hashes are in `tokenizer_verification.json`. The two
models use an identical Ollama chat template; template sampling defaults are
overridden by the shared benchmark settings.

## Model identities

| Exact tag | Digest | Size | Quantization | Architecture | Context |
|---|---|---:|---|---|---:|
| `gpt-oss:20b` | `17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7` | 13,793,441,244 B | MXFP4 | gptoss, 20.9B | 131,072 |
| `ducquoc/gpt-oss-sonnet:latest` | `800cc044c04f0c2ea3cf50ea70846b944d08b9f7e92c81c538379a7285f446f5` | 13,793,460,370 B | MXFP4 | gptoss, 20.9B | 131,072 |

Both models advertise Ollama's `low`, `medium`, and `high` thinking profiles.
The user directed the scored matrix to use `low` and `medium` only after the
`gpt-oss:20b / high` run exceeded several minutes per case without improving
the observed predictions. That high run was stopped after 6/18 cases and is
retained as a partial, excluded raw file; Sonnet/high was not run. High is
supported by the runtime, not marked unsupported. Scored runs are recorded
independently in `raw/` by model and profile. These files contain case IDs,
predicted labels, validator outcomes,
latencies, and aggregate-safe metadata; they do not contain prompts, raw model
responses, or reasoning channels. `results.json` is checkpointed after each
completed profile.

## Results and decision

See `results.json` for the final per-profile metrics, per-label accuracy,
gold-to-predicted confusion tables, exact fixture/prompt hashes, and gate
outcomes. All four completed profiles passed schema/citation/fallback,
unsupported-claim, and reasoning-privacy gates. The best score is 13/18 for
both `gpt-oss:20b / medium` and `ducquoc/gpt-oss-sonnet / medium` (72.2%);
neither reaches 17/18. GPT-OSS medium has lower median and P95 latency of those
two ties, so it is the winner among the completed matrix. Production remains
on `gpt-oss:20b / low`: the selected model identity did not change, and the
target score was not achieved. The fresh GPT-OSS low run scored 11/18 versus
the historical LLM-003 low score of 13/18. The LLM-003 runner did not pin
`num_ctx`; LLM-004 explicitly set it to 131,072 for both models. That runtime
difference may explain some of the score change, but the evidence does not
establish causality. Resolve it before promoting a reasoning-profile change.

The five failed cases in the LLM-003 `gpt-oss:20b low` baseline are AN-04,
AN-06, AN-08, AN-10, and AN-16. Per-model low/medium predictions are
summarized in `results.json`. Partial/uncertain confusion patterns recur in
both models; relation classification is a candidate for extraction into a
dedicated classifier, but no classifier was implemented. The high-profile
condition was not completed after the user directed us to skip further high
runs.

## Reproduction

```powershell
python scripts/verify_llm004_tokenizer.py
python scripts/llm004_benchmark.py gpt_oss low
python scripts/llm004_benchmark.py gpt_oss medium
python scripts/llm004_benchmark.py gpt_oss_sonnet low
python scripts/llm004_benchmark.py gpt_oss_sonnet medium
```

The benchmark resumes from already completed case records for its selected
model/profile. Do not run another inference workload in parallel with the
benchmark.
