# AGENTS.md — ChangeFlow IBM Bob 2.0 Project Context
<!-- Kept under 200 lines per the "Context Window Saturation" rule (KB §4). -->
<!-- Bob must read this file at the start of EVERY session. DO NOT edit manually. -->
Last Updated: 2026-08-29
Project: ChangeFlow — IBM TechXchange Hackathon 2026

---

## 1. Project Purpose & Scope

ChangeFlow is an **autonomous SDLC orchestration pipeline** built on IBM Bob 2.0.
It accepts a Git diff (`.patch` file) and runs a 6-phase multi-agent pipeline that:
- Maps the change's blast radius across the codebase (Agent 01)
- Performs security + quality static analysis (Agent 02)
- Keeps API and architecture documentation in sync (Agent 03)
- Generates PyTest skeletons and runs self-healing test loops (Agent 04)
- Issues a quality gate sign-off scorecard (Agent 05)

**Domain:** Financial Transactions & Multi-Rail Payments (CREDIT_CARD, DEBIT_CARD, BANK_TRANSFER, PIX).

---

## 2. Stack & Entry Points

| Layer | Technology | Entry Point |
|---|---|---|
| Orchestrator | Python 3.12 | `core/orchestrator.py` |
| Diff Parser | Python stdlib + regex | `core/analyzer/diff_parser.py` |
| Test Runner | Node.js / Jest | `core/runner/test_runner.py` |
| Onboarding Agent | Python AST + pathlib | `core/agents/onboarding_agent.py` |
| Code Reviewer Agent | Python regex | `core/agents/code_reviewer_agent.py` |
| Test Engineer Agent | Python AST + pytest | `core/agents/test_engineer_agent.py` |

**Run the full pipeline:**
```bash
python core/orchestrator.py benchmarks/sample-diff.patch
# Output → benchmarks/latest-pipeline-run.json
```

---

## 3. Agent Index

| ID | Spec | Python Method | Phase |
|---|---|---|---|
| 00 | `.bob/agents/00-onboarding.md` | `run_onboarding_agent()` | Pre-flight |
| 01 | `.bob/agents/01-change-analyzer.md` | `run_analyzer_agent(patch)` | Sequential |
| 02 | `.bob/agents/02-code-reviewer.md` | `run_code_reviewer_agent(impact)` | Parallel |
| 03 | `.bob/agents/03-documentation-agent.md` | `run_documentation_agent(analyzer_res)` | Parallel |
| 04 | `.bob/agents/04-test-engineer.md` | `run_test_engineer_agent(impact)` | Parallel |
| 05 | `.bob/agents/05-validation-agent.md` | `run_validation_agent(...)` | Gatekeeper |

The Python layer is the **deterministic hands** — always trust its JSON over LLM inference
when they conflict. The `.md` specs are the **semantic reasoning layer** that enriches output.

---

## 4. Architecture Pattern

```
core/
├── orchestrator.py          # ChangeFlowOrchestrator — pipeline coordinator
├── analyzer/diff_parser.py  # Parses .patch files, builds impact map
├── runner/test_runner.py    # Executes Jest suite, collects coverage
└── agents/
    ├── onboarding_agent.py  # Stack detection, AGENTS.md, Mermaid diagrams
    ├── code_reviewer_agent.py  # SAST: SQL injection, PCI, handle leaks, complexity
    └── test_engineer_agent.py  # AST → PyTest skeleton, self-healing loop
```

Pipeline execution order (in `execute_pipeline(patch_path)`):
1. **Phase 0** — Onboarding (pre-flight repo scan)
2. **Phase 1** — Change Analyzer (sequential, feeds Phase 2)
3. **Phase 2** — Reviewer + Doc Agent + Test Engineer (parallel, ThreadPoolExecutor)
4. **Phase 3** — Validation Gatekeeper (sequential, consolidates all results)

---

## 5. Security Golden Paths (Learning Scars)

> These are permanent rules derived from past errors. They are non-negotiable.

- **SQL Scar:** ALL database queries must use parameterized placeholders (`?`).
  F-string / `%s`-concatenated queries are a CRITICAL violation and an immediate pipeline BLOCK.

- **PCI Scar:** Card numbers must be masked as `****-****-****-XXXX` in ALL outputs
  (logs, API responses, exceptions). CVV MUST NEVER be stored, logged, or returned.

- **Pathing Scar:** Always use `pathlib.Path(file).parent.resolve()` for directory resolution.
  `os.chdir()` and hardcoded absolute string paths are forbidden anti-patterns.

- **Exception Scar:** `except: pass` and bare `except Exception:` are forbidden.
  All caught exceptions must be handled with contextual enrichment or re-raised as domain errors.

- **Secret Scar:** Credentials, API keys, and tokens must never be hardcoded in source.
  Always use environment variables sourced from `.env` (never committed) via `.env.example`.

---

## 6. Quality Gates (enforced by Agent 05)

| Gate | Threshold | Block on Fail? |
|---|---|---|
| Critical/High findings | 0 | YES |
| Test pass rate | 100% | YES |
| Modified-file coverage | ≥ 90% | YES |
| Docs sync status | SYNCHRONIZED | YES |
| Readiness score | ≥ 75 / 100 | Warning only |

---

## 7. Key Rules for Bob

- **DO NOT** edit `bob_Documentation.md` manually — it is auto-generated.
- **DO NOT** install packages globally — always use the project venv.
- **DO NOT** run destructive DB commands without explicit human confirmation.
- All new tests must use **pytest** (not unittest). Existing unittest tests may stay.
- Benchmark baseline: **100 min manual → 8 min human review** (~92% effort reduction).
- Output of each pipeline run is persisted to `benchmarks/latest-pipeline-run.json`.
