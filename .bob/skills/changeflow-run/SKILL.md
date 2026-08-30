---
name: changeflow-run
description: Use when the user wants to run the full ChangeFlow pipeline, process a git diff end-to-end through all agents, get a complete SDLC report, or trigger the IBM Bob 2.0 multi-agent pipeline.
metadata:
  argument-hint: "[path/to/change.patch]"
---

# ChangeFlow Full Pipeline (Agents 00–05)

You are acting as the **ChangeFlow Orchestrator** — IBM Bob 2.0 coordinating the complete
6-phase multi-agent SDLC pipeline. This is the master workflow skill.

Read `AGENTS.md` for the full project context before starting.
The pipeline follows the Observe → Think → Act loop from the IBM Bob 2.0 architecture (KB §2).

## Step 1 — Resolve the patch file

Check if the user provided a patch file argument. If not, use the default:
```
benchmarks/sample-diff.patch
```

If the user said something like "run on my changes" or "review the current diff", first run:
```bash
git diff HEAD > /tmp/current-changes.patch
```
and use `/tmp/current-changes.patch` as the patch file.

## Step 2 — Run the full pipeline

```bash
python core/cli.py run <patch_file> --save
```

The `--save` flag persists the output to `benchmarks/latest-pipeline-run.json`.
This command runs all 6 phases internally:
- Phase 0: Onboarding pre-flight
- Phase 1: Change Analyzer (sequential)
- Phase 2: Code Reviewer + Documentation Agent + Test Engineer (parallel)
- Phase 3: Validation Gatekeeper (sequential)

The command prints live phase banners to stderr. Wait for it to complete.

## Step 3 — Parse the top-level result

```json
{
  "pipeline_status": "READY_FOR_HUMAN_REVIEW | BLOCKED",
  "total_execution_time": <seconds>,
  "report": { ... metrics ... },
  "agents": {
    "onboarding":     { "status": ..., "data": { "stack": ..., "starter_tasks": ... } },
    "analyzer":       { "status": ..., "data": { "files_changed": ..., "risk_level": ... } },
    "reviewer":       { "status": ..., "score": ..., "findings": [...] },
    "documentation":  { "status": ..., "docs_updated": [...] },
    "tester":         { "status": ..., "tests_passed": ..., "coverage_percentage": ... },
    "validation":     { "gate_status": ..., "readiness_score": ..., "checklists": {...} }
  }
}
```

## Step 4 — Phase 0: Onboarding summary

If `agents.onboarding.status` is `COMPLETED`:
- Note the detected stack from `agents.onboarding.data.stack`.
- List any starter tasks found.

## Step 5 — Phase 1: Impact summary

From `agents.analyzer.data`:
- Report files changed, blast radius score, risk level.
- List affected APIs and tests.

## Step 6 — Phase 2: Parallel agents summary

**Code Reviewer** (`agents.reviewer`):
- Show the severity table from `agent_report_markdown` or build from `findings`.
- List all Critical and High findings with exact file:line and suggested fix.

**Documentation Agent** (`agents.documentation`):
- Report which docs were updated or are already in sync.

**Test Engineer** (`agents.tester`):
- Show test execution results: passed/failed counts, coverage.
- For each skeleton in `skeletons_generated`, note the file and coverage estimate.
- Report any self-healing iteration results.

## Step 7 — Phase 3: Quality Gate scorecard

Reproduce the validation scorecard from `agents.validation`:
```
=======================================================
🏁 ChangeFlow Quality Gate: <pipeline_status>
Readiness Score: <readiness_score>/100
=======================================================
✔/✘ 01-change-analyzer: <blast_radius_score>/100 blast radius
✔/✘ 02-code-reviewer:   <score>/100 — <critical>C/<high>H findings
✔/✘ 03-documentation:   <sync_status>
✔/✘ 04-test-engineer:   <tests_passed>/<tests_executed> tests, <coverage>% coverage
-------------------------------------------------------
⚡ 100 min manual → <human_minutes> min review
   (-<effort_saved_percentage>% effort | <speedup_factor> speedup)
   Automation wall-clock: <total_execution_time>s (measured this run)
-------------------------------------------------------
```

If `pipeline_status` is `BLOCKED`:
- List every failing gate with the exact reason and pointer to fix it.
- Do NOT suggest the change is safe to merge.

If `pipeline_status` is `READY_FOR_HUMAN_REVIEW`:
- Invite the developer to perform final review and merge sign-off.
- Remind: human approval is always required — Bob never merges autonomously.

## Step 8 — Update .bob/memory.md if new heuristics were discovered

If the pipeline revealed a new pattern not already in `.bob/memory.md` (e.g., a new payment rail,
a new security scar, or a new cross-layer dependency pattern), append it as a new heuristic entry.
Ask the developer for confirmation before writing.

## Safety rails
- DO NOT merge or push to any branch — pipeline analysis only.
- DO NOT expose `.env` contents or any credential.
- DO NOT fabricate metrics — all numbers come from the CLI JSON output.
- If `total_execution_time` is missing or the CLI crashes, show the raw error and ask the user to
  check `npm install` in `sample-app/` and that Python 3.12 is active.
