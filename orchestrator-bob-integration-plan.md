# Plan: Integrate core/orchestrator.py into IBM Bob 2.0 Agent Definitions

## Top-Level Overview

**Goal:** Bridge the Python `ChangeFlowOrchestrator` pipeline to the IBM Bob IDE agent system.
The orchestrator's Python modules are the *deterministic hands*; the `.bob/agents/*.md` specs are
the *LLM persona/reasoning layer*. Currently neither knows about the other.

**Scope:**
- Create `AGENTS.md` at repo root — Bob's stateful project memory (KB §4, ≤200 lines rule).
- Create `.bob/agents/00-onboarding.md` — missing spec for the already-wired Agent 00.
- Update all five existing `.bob/agents/0X-*.md` specs to add a `PYTHON EXECUTION HOOK` section
  that instructs Bob to call the orchestrator CLI and consume its JSON output as ground truth.
- No changes to any `.py` files (they already work correctly).

**Non-goals:** Modifying the Python pipeline, changing `.bob/rules/`, changing `.bob/memory.md`.

---

## Sub-Task 01 — Create AGENTS.md (Stateful Project Memory)

**Intent:** The KB doc (§4) mandates an `AGENTS.md` at the repo root as Bob's context anchor,
preventing AI Amnesia and keeping the agent within 200 lines to avoid context saturation.

**Expected Outcomes:**
- `AGENTS.md` exists at the repo root, ≤200 lines.
- Contains: project purpose, stack, architecture, security scars, golden paths, and agent index.

**Todo List:**
1. Write `AGENTS.md` covering: project name/purpose, Python 3.x stack, pipeline architecture,
   security rules (SQL parameterization, PCI card masking, no CVV), pathlib pathing scar,
   agent index (00–05) with their Python entry points.

**Relevant Context:**
- `refs/Knowledge Base & Strategic Context_ IBM Bob 2.0 Autonomous SDLC Agent.pdf` §4
- `.bob/memory.md` (existing heuristics to carry forward)
- `.bob/rules/coding-standards.md`

**Status:** [x] done

---

## Sub-Task 02 — Create .bob/agents/00-onboarding.md

**Intent:** The Python `run_onboarding_agent()` is already wired into the pipeline as Phase 0
but has no corresponding Bob spec. This creates the persona + execution hook so Bob can trigger
it via `/init` and consume its structured output.

**Expected Outcomes:**
- `.bob/agents/00-onboarding.md` exists.
- Spec follows the same structure as existing agent specs (Role, Execution Contract, Output Format,
  Error Handling, strict_rules).
- Contains an execution hook: `python core/orchestrator.py` is not called standalone here;
  instead the hook runs `python -c "from core.agents.onboarding_agent import run; import json; print(json.dumps(run('.')))"`.
- Output JSON keys match what `onboarding_agent.run()` returns:
  `agents_md`, `report_markdown`, `stack`, `starter_tasks`.

**Relevant Context:**
- `core/agents/onboarding_agent.py` — `run()` function return shape
- `core/agents/bob-agent-onboarding.md` — persona description source
- `.bob/agents/01-change-analyzer.md` — structural template to follow

**Status:** [x] done

---

## Sub-Task 03 — Update 01-change-analyzer.md with Python Execution Hook

**Intent:** Tell Bob that after its semantic analysis it must run the Python diff parser and
reconcile its impact map with the deterministic output. This closes the loop between LLM
reasoning and measured reality.

**Expected Outcomes:**
- A `## PYTHON EXECUTION HOOK` section is appended to `.bob/agents/01-change-analyzer.md`.
- Hook command: `python core/orchestrator.py <patch_file>` (or the diff_parser directly).
- Bob is instructed to use the JSON `data` key from Agent 01 output as authoritative.

**Relevant Context:**
- `core/orchestrator.py:88` — `run_analyzer_agent()`
- `core/analyzer/diff_parser.py` — `parse_patch_file()`

**Status:** [x] done

---

## Sub-Task 04 — Update 02-code-reviewer.md with Python Execution Hook

**Intent:** The code reviewer spec must direct Bob to invoke `scan_content` via the orchestrator
and merge the deterministic findings (SQL injection, PCI log exposure, handle leaks) into its
semantic review before outputting the final report.

**Expected Outcomes:**
- `## PYTHON EXECUTION HOOK` section added to `.bob/agents/02-code-reviewer.md`.
- Hook: `python -c "from core.agents.code_reviewer_agent import run, build_report; import json, sys; print(json.dumps(run(sys.argv[1:])))" -- <files>`.
- Bob uses the `findings` list as the baseline and enriches it semantically.

**Relevant Context:**
- `core/agents/code_reviewer_agent.py` — `run()`, `scan_content()`, `build_report()`
- `core/orchestrator.py:100` — `run_code_reviewer_agent()`

**Status:** [x] done

---

## Sub-Task 05 — Update 04-test-engineer.md with Python Execution Hook

**Intent:** Direct Bob to invoke `generate_test_skeleton()` for changed Python files and run
the `self_healing_loop()`, then add semantic value (contract tests, edge cases) on top of the
deterministic skeleton.

**Expected Outcomes:**
- `## PYTHON EXECUTION HOOK` section added to `.bob/agents/04-test-engineer.md`.
- Hook: `python -c "from core.agents.test_engineer_agent import generate_test_skeleton; from pathlib import Path; import sys; print(generate_test_skeleton(Path(sys.argv[1])))" <module.py>`.
- Bob uses generated skeleton as the test file base and fills in real assertions.

**Relevant Context:**
- `core/agents/test_engineer_agent.py` — `generate_test_skeleton()`, `self_healing_loop()`
- `core/orchestrator.py:306` — `run_test_engineer_agent()`

**Status:** [x] done

---

## Sub-Task 06 — Smoke Validation

**Intent:** Verify all new/changed files are syntactically valid and Bob import chain is intact.

**Expected Outcomes:**
- `python -c "from core.orchestrator import ChangeFlowOrchestrator; print('ok')"` passes.
- All `.bob/agents/*.md` files parse without errors.

**Status:** [x] done
