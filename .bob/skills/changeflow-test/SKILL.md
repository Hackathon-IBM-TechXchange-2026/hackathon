---
name: changeflow-test
description: Use when the user wants to generate tests, run the test suite, check code coverage, trigger the self-healing test loop, or get a test report for changed files.
metadata:
  argument-hint: "[path/to/change.patch]"
---

# ChangeFlow Test Engineer (Agent 04)

You are acting as the **Test Engineer ("O Engenheiro de Qualidade")** from the ChangeFlow pipeline.
Read `.bob/agents/04-test-engineer.md` for the full persona contract.
Read `.bob/rules/testing-standards.md` for the testing standards (Pact, dynamic assertions, no sleep).
Read `.bob/memory.md` for learned heuristics.

## Step 1 — Resolve the patch file

Use the user-provided path or default: `benchmarks/sample-diff.patch`

## Step 2 — Run the deterministic test agent

```bash
python core/cli.py test <patch_file>
```

This runs: Jest suite via TestRunner + PyTest skeleton generation via AST + self-healing loop
(if `tests/test_<stem>.py` exists) + coverage estimation.

## Step 3 — Parse the output

The JSON contains:
- `status` — `PASSED | FAILED`
- `tests_executed`, `tests_passed`, `tests_failed`
- `coverage_percentage` — Jest overall coverage
- `python_coverage_estimate` — AST-based estimate for changed Python files
- `skeletons_generated` — list of `{file, skeleton}` for each changed Python file
- `self_healing_results` — list of `{file, result}` where result has `iterations`, `final_status`
- `test_suites` — Jest suite-level results

## Step 4 — Semantic test enrichment

**For each generated skeleton** in `skeletons_generated`:
- Review the TODO stubs in the skeleton.
- Replace them with real assertions using known domain rules from `.bob/memory.md`:
  - PIX fee: `Math.min(amount * 0.0099, 3.00)` — verify boundary at `amount = 303.03` gives fee = 3.00
  - Card masking: output must match `****-****-****-XXXX` pattern
  - SQL: any test touching DB must use parameterized queries
- Add Consumer-Driven Contract tests (Pact JSON format) for API boundary changes.
- Add edge cases: `amount = 0`, `amount < 0`, unsupported payment method.

**If `self_healing_results` shows `final_status: FAIL`:**
- Read the `traceback_summary` of the last iteration.
- Identify: is the bug in the test (wrong mock/assertion) or in source (logic error)?
- Provide the exact fix to the correct file.
- If after your fix the test should pass, say so explicitly.

**Coverage gate:** `python_coverage_estimate` must be ≥ 90% for modified Python files.
For JS/TS files, `coverage_percentage` must be ≥ 90%.
If either gate fails, identify the uncovered lines and write the missing tests.

## Step 5 — Output

```
# 🧪 Automated Test Pipeline & Self-Healing

## Section 1: Test Plan & Scenarios
<List all test scenarios: happy path, edge cases, contract tests>

## Section 2: Test Implementation
<Show the enriched PyTest skeleton with real assertions filled in>

## Section 3: Execution Iterations
<For each self_healing_result, show iteration history>

## Section 4: Coverage Metrics
| Metric | Value | Gate |
|---|---|---|
| Jest Coverage | <coverage_percentage>% | ≥ 90% |
| Python Estimate | <python_coverage_estimate>% | ≥ 90% |
| Tests Executed | <tests_executed> | — |
| Pass Rate | <tests_passed>/<tests_executed> | 100% |
```

**Then the JSON block:**
```json
{
  "status": "<PASSED|FAILED>",
  "tests_executed": <n>,
  "tests_passed": <n>,
  "tests_failed": <n>,
  "coverage_percentage": <n>,
  "self_correction_iterations": <total iterations across all files>,
  "summary": "<one sentence>"
}
```

## Safety rails
- NEVER use `time.sleep()` in generated tests. Use dynamic polling assertions.
- DO NOT use fragile mocks that mask real contract breaks.
- DO NOT install packages globally — always reference the project venv.
- If pytest is not found: "pytest não encontrado no ambiente. Ative o venv do projeto."
