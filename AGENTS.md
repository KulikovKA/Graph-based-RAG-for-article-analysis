# AGENTS.md — Codex Operating Rules for the Main Repository

Repository: `KulikovKA/Graph-based-RAG-for-article-analysis`.

**Instruction language:** This file is written in English. Continue communicating with the user, writing final reports, new code comments, and commit messages **in Russian**, as established by `task.md`. Do not rename existing public contracts solely to translate them.

## 1. Project Context and Sources of Truth

Before substantial work, read `task.md`, the active task entries in `TASKS.md`, `docs/FINAL_PROJECT_PLAN.md`, and the relevant domain-specific documents. The historical section of `TASKS.md` is not the current backlog: the active summary, integration gates, and release gates take precedence. Verify completion claims against code and evidence, not task labels alone.

The application has two modes sharing one retrieval infrastructure: **Knowledge Graph Explorer** and **Patent Research Assistant**. This repository contains the final application and integrations of verified components. KG, NER/RE, entity linking, reranking, and agent experiments belong in the separate **RESEARCH** repository. Do not recreate the research corpus or run heavy experiments here unless explicitly requested.

Target stack: FastAPI, React/TypeScript, PostgreSQL, Neo4j, Qdrant, Redis, Groq API for generative roles, and Airflow for offline updates. Local NER, embedding, and reranking models are permitted. LightRAG is a legacy component, not part of the target runtime. Do not remove its production wiring except through the dedicated migration task and regression gate.

## 2. Mandatory Specification-Driven Development (SDD)

**Apply SDD across the entire diploma project**: research, backend, frontend, APIs, data, Airflow DAGs, ML integration, security, and documentation. Use the sequence:

**SPEC → DESIGN → TASKS/TESTS → IMPLEMENT → VERIFY → REVIEW → PUBLISH**

SDD is a discipline of verifiable requirements and evidence, **not** a mandate to install a framework or produce unnecessary files. Check whether an adequate specification already exists before writing code. For a small fix, an existing task entry and clear testable acceptance criteria may be sufficient.

1. **SPEC — before delegating.** Locate the active task in `TASKS.md`; consult `docs/FINAL_PROJECT_PLAN.md`, ADRs, and applicable API/LLM/GRAPH/DATA contracts. Confirm the objective, scope, non-goals, observable behavior, inputs/outputs, failures, security, versions, and acceptance criteria. If these are insufficient or a public contract changes, create or update a concise `docs/specs/<TASK-ID>.md` with measurable **Given/When/Then** scenarios for successful, empty, failure, and adversarial cases. Research experiment specifications belong in RESEARCH and must include the hypothesis, baseline, frozen corpus/splits, metrics, budget, and stop conditions; do not duplicate the product backlog there.
2. **DESIGN.** Before implementation, record a minimal plan for changed files, module boundaries, DTOs/ports, migrations, backward compatibility, provenance, and rollback. Identify independently buildable parts and the required `I-*` / `G-*` integration or release gates. An agent's suggestion is not automatically an approved architectural change. Scope or architecture changes require an updated specification and explicit agreement rather than incidental implementation.
3. **TASKS + TESTS.** Split work into small steps with clear file ownership. Map every SPEC acceptance criterion to a test or an explicit verification method. Prefer contract tests before implementation where useful; otherwise add them in the same change. Never claim evidence from commands that were not run, fabricated metrics, or placeholder tests.
4. **IMPLEMENT.** Implement only the approved scope. Preserve existing APIs, data, and compatibility. Return to SPEC/DESIGN when requirements are unclear; do not silently expand the work. Avoid running heavy LLM/ML benchmarks alongside an active experiment unless the user authorizes it.
5. **VERIFY — mandatory and distinct from the implementer's self-check.** The orchestrator or an independent verification subagent must trace **requirement → code/artifact → test → actual result** for every criterion. Run relevant static, unit/contract, integration, negative, and security checks. For UI: type checking and Playwright; API: schemas, ownership, and responses; KG: provenance, offsets, and snapshots; agent: injection, budgets, tool allowlists, retries, timeouts, fallback, and data leakage; Airflow: idempotency, checkpoints, and recovery after partial failures. For research: frozen snapshot reproducibility, no holdout leakage, correct metrics, and baseline comparability. **Label mock/fake tests as component-level verification, never live integration evidence.**
6. **REVIEW + PUBLISH.** The orchestrator personally reads the diff and verification report, checks scope and SPEC compliance, and requests fixes when necessary. Only then integrate, commit, and perform authorized push as described in `task.md`. Change task and `I-*` / `G-*` gate status only when all required evidence exists.

**Minimum traceability:** Each nontrivial task report must contain the task ID, SPEC or contract reference, code/data versions, acceptance criteria, changed files, exact executed commands, verification results, open risks, and outstanding integration/release gates. A table in the report is sufficient; do not generate another file merely for the table. Use **PASS**, **FAIL**, **BLOCKED**, and **NOT RUN** unambiguously. `NOT RUN` is never PASS. Research work must also capture a pinned commit, configuration, dataset/split, measured metrics, and reproducible report.

**Completion gate:** A task must not be marked completed merely because code exists, a subagent reports success, mock tests pass, or no errors are visible. An independent component may be reviewed and integrated with an outstanding gate, but the overall task remains incomplete whenever its acceptance criteria require real integration. Do not prevent independent work on other tasks because a completion gate is still open.

**Concurrency:** The maximum is **six subagents**. Prefer **up to five implementers plus one independent verifier** when verification is active. If all six are implementing, start verification after a slot becomes free. An implementer must not be the sole verifier of their own work; the orchestrator always performs a separate final review.

**Initial SDD audit:** On a request such as “verify SDD,” first perform a read-only audit: `TASKS.md → existing specifications/contracts → implementation → tests → evidence and status`. Find gaps, invalid dependencies, and unsupported gate closures. Run only available low-resource checks, clearly identifying deferred integration, E2E, or ML tests. Do not change production code, task status, or push merely for an audit unless explicitly instructed.

## 3. Roles: Orchestrator and Subagents

- **Orchestrator:** The main Codex session. The user selects its model and reasoning effort via `/model`. Do not override that choice in project configuration or subagent instructions.
- **Subagents:** Scoped implementers. The project's `.codex/config.toml` sets the intended default to `gpt-6.1-terra`, `xhigh`, with at most **six** concurrent subagents. Do not override these settings unless the user explicitly asks.
- **Six is a maximum, not a target.** Delegate only genuinely independent, useful work. Simple tasks do not require subagents.
- Subagents **must not push to the shared branch, merge into `main`, or unilaterally update task-completion statuses**. They return their scoped diff or feature-branch commits, actual test results, changed files, and open risks.
- The orchestrator owns final review, fixes, sequential integration, status updates, per-task commits, and push under `task.md`.
- Do not rely on the author to review their own changes. The orchestrator must perform **its own final review of each contribution** and arrange an independent check when warranted.

## 4. Parallel-Work Protocol

1. Inspect `git status`, the current branch, and the starting SHA. Publish a concise plan with task IDs, owners, file boundaries, acceptance criteria, dependencies, and resource-intensive steps before delegation.
2. Partition work around stable contracts and test fixtures. Agree on DTOs/ports before concurrent edits. UI development need not wait for completed backend services if contract-aligned mock APIs are available.
3. Prefer separate Git worktrees and feature branches. **Spawning a subagent does not automatically isolate its filesystem.** If sharing one tree, enforce nonoverlapping file ownership and prevent concurrent Git commit/checkout/merge/rebase operations.
4. Assign each subagent one task ID or one explicitly bounded part of it, allowed and forbidden files, tests, and stop criteria. Require the agent to identify ownership conflicts before editing.
5. Reserve shared files (`TASKS.md`, `task.md`, `docs/FINAL_PROJECT_PLAN.md`, `compose.yaml`, shared API DTOs, and migrations) for the orchestrator unless one exclusive owner is explicitly assigned. Subagents may propose patches but must not concurrently edit those files.
6. Do not run multiple heavy Docker stacks, full test suites, ML benchmarks, model downloads, or broad scans simultaneously. While a RESEARCH benchmark is active, favor fake/mock tests, focused unit/contract checks, and frontend lint/type checking. Schedule any heavier check separately.
7. If two tasks need the same file or incompatible contracts, stop the conflicting portion and replan rather than allowing a race.

### Preferred First Wave of Six Tasks — Only When Requested

| Task | Subagent-owned work | Reserved for orchestrator / integration |
| --- | --- | --- |
| `INT-GROQ-001` | Groq adapter, inference contracts, target configuration, contract tests | Shared `compose.yaml` updates; live user traffic before guards |
| `APP-MEM-001` | PostgreSQL memory/summaries, Redis caching, corresponding tests | Common `analysis_run.py` wiring; final `I-MEM` |
| `APP-UI-001` | `frontend/` only; two modes, mock API, frontend tests | Real `I-UI`; backend DTO changes |
| `APP-AIR-001` | `airflow/`, isolated DAG/service adapters, fake-dependency tests | `compose.yaml`, full live ingestion, `I-AIR` |
| `APP-GRAPH-001` | Graph Explorer backend routes/ports, contract and security tests | `frontend/`, real `INT-RET` and `I-KG` |
| `APP-EXPORT-001` | Backend export service/endpoint; completed-run tests | `frontend/` button, PDF/E2E at `I-UI` and `G-TEST` |

This is permission to **begin independent work**, not automatic permission to close a task. The latest user request and real task status take precedence. `APP-GUARD-001` may be developed in a later parallel wave. **Do not send real private user ideas through the new Groq pipeline before `I-SEC` passes.**

## 5. Mandatory Orchestrator Review

For **every** subagent result, **before integration, commit, or push**:

**SDD gate:** Confirm that a sufficient SPEC exists and that its criteria trace to tests. Obtain an independent VERIFY report or perform a separate verification yourself rather than treating the implementer's statements as evidence. High-risk or conflicting changes require an additional independent check.

1. Compare the task, specification, and approved criteria; reject scope creep and unjustified dependencies.
2. Read the **complete diff** and relevant surrounding code. Check types, API compatibility, migrations, errors, retries, cancellation, and dependency degradation.
3. Review security: ownership, user/chat isolation, untrusted documents, prompt injection, SQL/Cypher allowlists, secrets, Groq data minimization, provenance, and evidence integrity.
4. Re-run appropriate focused tests independently; inspect skipped checks and ensure mock tests are not described as live integration.
5. Check that unrelated worktrees/files are untouched, existing behavior is preserved, and no invalid imports or dependencies were introduced.
6. If a result is deficient, send specific findings back or fix them; then repeat the relevant verification. “Tests passed” alone is insufficient.
7. Integrate changes sequentially only after review. Keep separate task-level history and leave integration/release gate status **open** unless actual E2E evidence exists.

**Important: “Can start a task” is not “can close a task.”** Passing component tests is not a substitute for required `I-*` and `G-*` acceptance.

## 6. Commits and Push — Authorized

The orchestrator is **explicitly authorized** to run `git add`, `git commit`, and `git push` within the user's requested work in this repository, subject to `task.md`, successful review, and checks. No extra user confirmation is necessary solely for a normal push **when the Codex environment already permits it**. These instructions do not bypass sandbox, network, or approval policies; use the environment's normal permission flow if required.

- Create a separate meaningful **Russian-language** commit for each accepted unit of work; push to the designated current branch after sequential integration.
- If work was done in worktrees, integrate feature-branch commits sequentially, resolve conflicts explicitly, and rerun affected checks.
- Never force-push, rewrite published history, perform destructive `reset --hard`, or delete large amounts of data without specific authorization.
- Never commit `.env`, API keys, tokens, private user data, databases, downloaded corpora, model weights, caches, or temporary benchmark artifacts. Inspect the staged diff and `git status` before push.
- Verify the pushed SHA on the remote branch. If publication fails, report **pending publication**; do not mark the task completed.
- No subagent may bypass the orchestrator and push to the shared branch.

## 7. Quality and Reporting Rules

- Prefer small changes and existing components. Do not refactor arbitrarily or add infrastructure without a demonstrated need.
- Do not claim that no abstract match proves patent novelty. A correct citation does not by itself prove the semantic truth of a factual relation.
- Preserve historical data, snapshots, and contracts. KG and document-index changes must respect revisions and provenance.
- Do not transmit private ideas to Groq without the specified notice and guard/consent requirements.
- Declare completion based on executed tests and satisfied gates, not the existence of a file or placeholder.
- The orchestrator's final report must include tasks and subagents, diffs/changed files, review outcomes, actual tests, open `I-*`/`G-*` gates, commits, pushed SHAs, blockers, and the next independently executable step.

## 8. Useful Checks

Backend: use `ruff check .`, `mypy src`, and `pytest` **selectively** on changed modules; reserve the full suite for the final integration gate.

Frontend: inside `frontend/`, use relevant available commands such as `npm run lint`, `npm run typecheck`, `npm run build`, unit tests, and Playwright fixtures. Inspect package scripts instead of assuming every script exists.

Configuration: run `docker compose config` when topology changes. Do not spin up unnecessary services while a heavy benchmark is active.
