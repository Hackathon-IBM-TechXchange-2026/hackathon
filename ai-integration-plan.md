# ChangeFlow — AI Integration & Reliability Plan

## Top-Level Overview

The ChangeFlow pipeline currently operates in **pure-deterministic mode**: every analysis decision
(code review, test generation, documentation sync) is implemented with hand-written regex rules
and heuristic Python logic.  There are three concrete problems to fix:

1. **Replace regex-based logic with Bob/LLM calls** — The `code_reviewer_agent.py` and the
   `REVIEW_PATTERNS` block in `orchestrator.py` perform static analysis using regex. These
   must be replaced/augmented with real calls to Bob's generative AI, which already has the
   correct persona definitions in `.bob/agents/02-code-reviewer.md` and
   `.bob/agents/04-test-engineer.md`. The `test_engineer_agent.py` self-healing loop
   also has a placeholder comment where Bob is supposed to rewrite failing tests but
   `fixer_callback` is always `None`.

2. **Make reports consistent and dynamic** — The validation report aggregates real measured values
   (test counts, coverage %, timing) but the **per-agent markdown reports** (`build_report()` in
   `code_reviewer_agent.py`, `build_report()` in `test_engineer_agent.py`) are still static
   templates whose content is not driven by what Bob actually found.  The `latest-pipeline-run.json`
   written to disk must reflect the real AI output, not regex-derived findings.

3. **Fix new-file test detection** — `run_test_engineer_agent()` in `orchestrator.py` only tries
   PyTest self-healing for Python files and only if
   `Path(workspace_root) / "tests" / f"test_{stem}.py"` already exists.  When a **new TypeScript
   file** is added to `sample-app/src/` there are no corresponding test stubs and the Jest
   `testMatch` pattern only covers files that already exist in `tests/`. The pipeline must:
   (a) detect newly added `.ts` files with no matching test, (b) ask Bob to author the missing
   test file, and (c) write it to `sample-app/tests/` before running Jest.

---

## Sub-Task 1 — Bob AI Client Wrapper

**Status:** [ ] pending

### Intent
Create a thin Python module `core/bob_client.py` that wraps calls to Bob's generative AI.
All other agents will call this single module so the integration point is in one place.
Bob is already running as the orchestrating IDE — we communicate with it through its
MCP/tool protocol by writing a prompt to a temporary file and reading the structured
JSON response, OR by invoking Bob's HTTP completion endpoint if exposed.
The wrapper must support:
- A `complete(system_prompt: str, user_prompt: str) -> str` function that returns the raw text
  response from Bob.
- A `complete_json(system_prompt: str, user_prompt: str, schema_hint: str) -> dict` variant
  that parses the JSON block from Bob's reply.
- A configurable timeout and a clean fallback that surfaces the error as a structured failure
  dict (never silently swallows exceptions per `coding-standards.md`).

### Expected Outcomes
- `core/bob_client.py` exists and is importable.
- Calling `complete()` with a diff string returns a non-empty string response from Bob.
- Calling `complete_json()` returns a parsed Python dict whose keys match the agent output
  schema defined in the `.bob/agents/*.md` files.
- All exceptions are typed (e.g. `BobClientError`) and include a `traceId`.

### Todo List
1. Identify Bob's available HTTP/IPC interface for completions (check environment, `.bob/` dir,
   or MCP server config).
2. Create `core/bob_client.py` with `BobClientError`, `complete()`, and `complete_json()`.
3. Add a `__main__` smoke test block that runs a minimal round-trip and prints the result.

### Relevant Context
- `.bob/agents/02-code-reviewer.md` — system prompt for the reviewer persona.
- `.bob/agents/04-test-engineer.md` — system prompt for the test engineer persona.
- `core/agents/code_reviewer_agent.py` — will call `bob_client.complete_json()`.
- `core/agents/test_engineer_agent.py` — `fixer_callback` will call `bob_client.complete()`.
- Project rule: no `any` typing, no bare except, typed exceptions required.

---

## Sub-Task 2 — Replace Code Reviewer Regex with Bob AI Call

**Status:** [ ] pending

### Intent
Remove the deterministic `RULES` regex array from `code_reviewer_agent.py` and the
`REVIEW_PATTERNS` block in `orchestrator.py` as the **primary** analysis engine.
Instead, feed the changed file content to Bob via `bob_client.complete_json()` using the
system prompt defined in `.bob/agents/02-code-reviewer.md`.

The regex rules may be kept as a **fast pre-filter** that runs first and flags obvious
issues (SQL injection, hardcoded secrets) before the AI call, but Bob's output is
the authoritative finding list. The final `findings[]` array must come from Bob's
structured JSON response.

### Expected Outcomes
- `run_code_reviewer_agent()` in `orchestrator.py` calls Bob and the response's `findings[]`
  array is what gets stored in `reviewer_output["findings"]`.
- The `agent_report_markdown` field contains Bob's actual reasoning, not the regex-templated
  markdown table.
- The `score` field in the response comes from Bob's `"score"` field in its JSON reply.
- If Bob is unavailable, fall back to the regex-only scan and mark `basis: "fallback_regex"`.

### Todo List
1. Load the system prompt from `.bob/agents/02-code-reviewer.md`.
2. In `run_code_reviewer_agent()`, after collecting file contents, call
   `bob_client.complete_json(system_prompt, diff_context)`.
3. Map Bob's `findings[]` output to the internal dict format already used
   (`file`, `line`, `severity`, `category`, `message`).
4. Remove the duplicate regex scan from `REVIEW_PATTERNS` in `orchestrator.py`
   (keep `code_reviewer_agent.py`'s `RULES` as fallback only).
5. Update `build_report()` in `code_reviewer_agent.py` to accept Bob's raw markdown
   summary as an optional parameter and prefer it over the auto-generated template.

### Relevant Context
- `core/orchestrator.py:100-188` — `run_code_reviewer_agent()` method.
- `core/orchestrator.py:33-48` — `REVIEW_PATTERNS` to be demoted to fallback.
- `core/agents/code_reviewer_agent.py:55-94` — `RULES` list (keep as fallback).
- `.bob/agents/02-code-reviewer.md` — exact system prompt and output JSON schema.

---

## Sub-Task 3 — Bob-Powered Self-Healing in Test Engineer Agent

**Status:** [ ] pending

### Intent
Wire up the `fixer_callback` in `test_engineer_agent.py`'s `self_healing_loop()`.
Currently the loop runs up to 3 iterations but has no actual fixer — the callback is
always `None`, which means the loop exits immediately after the first failure without
ever fixing anything.

The fix: implement a `bob_fixer_callback(test_path: str, result: TestRunResult) -> None`
function in `core/agents/test_engineer_agent.py` that:
1. Reads the failing test file and the traceback from `result`.
2. Calls `bob_client.complete()` with the `.bob/agents/04-test-engineer.md` persona,
   passing the test file content + traceback as context.
3. Parses the corrected test code from Bob's response.
4. Writes the corrected test back to `test_path` on disk.

Then pass `bob_fixer_callback` as the default `fixer_callback` in `self_healing_loop()`.

### Expected Outcomes
- `self_healing_loop()` actually attempts up to 3 AI-driven repair iterations when tests fail.
- Each iteration log entry in `healing_result["iterations"]` contains Bob's reasoning summary.
- `test_engineer_agent.py` no longer has the comment "aqui entraria a chamada ao Bob" as a
  placeholder — it is real code.

### Todo List
1. Implement `bob_fixer_callback(test_path: str, result: TestRunResult) -> None` using
   `bob_client.complete()`.
2. Parse the fenced code block from Bob's reply and write it to `test_path`.
3. Update `self_healing_loop()` default: pass `bob_fixer_callback` as default for
   `fixer_callback` parameter.
4. Propagate `bob_fixer_callback` in `run_test_engineer_agent()` within `orchestrator.py`.

### Relevant Context
- `core/agents/test_engineer_agent.py:153-185` — `self_healing_loop()`.
- `core/agents/test_engineer_agent.py:147-150` — `FixerCallback` type alias.
- `.bob/agents/04-test-engineer.md` — system prompt and expected output format.
- `core/orchestrator.py:335-340` — where `self_healing_loop(test_path)` is called with no callback.

---

## Sub-Task 4 — New TypeScript File Test Generation

**Status:** [ ] pending

### Intent
When a diff introduces a **new** TypeScript source file under `sample-app/src/` that has no
corresponding test file in `sample-app/tests/`, the pipeline must:
1. Detect the gap (new `.ts` file without a matching `*.test.ts`).
2. Ask Bob (via `.bob/agents/04-test-engineer.md` persona) to author a full Jest test suite
   for that new file, given its source code as context.
3. Write the generated test file to the appropriate location under `sample-app/tests/`
   (mirroring the `src/` sub-path: `src/services/foo.ts` → `tests/unit/foo.test.ts`).
4. Re-run Jest so the new tests are included in coverage metrics.

This replaces the current limitation where `run_test_engineer_agent()` skips non-`.py`
files entirely and only handles pre-existing test files.

### Expected Outcomes
- If a new `sample-app/src/services/foo.service.ts` is added in a diff, a
  `sample-app/tests/unit/foo.service.test.ts` is created by Bob and executed.
- Jest coverage metrics in `latest-pipeline-run.json` include the new file.
- The `skeletons_generated` field in the tester output lists the new TypeScript tests.
- If Bob's generated tests fail on the first run, the self-healing loop (Sub-Task 3)
  kicks in automatically.

### Todo List
1. In `run_test_engineer_agent()`, add a detection step: for each changed file with a
   `.ts` extension under `src/`, compute the expected test path and check if it exists.
2. For missing test files, read the source file content and call
   `bob_client.complete_json()` with the test engineer persona to generate a Jest test suite.
3. Write the generated test content to the computed `tests/unit/<stem>.test.ts` path.
4. Call `self.test_runner.run_tests()` a second time (or once after all stubs are written)
   so the new tests are included in the run.
5. Append generated test file info to `skeletons_generated` in the agent output.

### Relevant Context
- `core/orchestrator.py:308-361` — `run_test_engineer_agent()` method.
- `core/runner/test_runner.py:19-87` — `run_tests()` — runs Jest over the whole `sample-app`.
- `sample-app/jest.config.js` — `testMatch: ['**/*.test.ts']` already picks up new files.
- `.bob/agents/04-test-engineer.md` — system prompt with Pact contract example.

---

## Sub-Task 5 — Dynamic, Coherent Report Generation

**Status:** [ ] pending

### Intent
Make every report section in `latest-pipeline-run.json` and the per-agent markdown reports
driven by real AI output, not static templates. Specifically:

- `agents.reviewer.agent_report_markdown` must contain Bob's actual review narrative
  (from Sub-Task 2), not the regex-generated markdown table.
- `agents.tester` must include a `test_report_markdown` field that is Bob's formatted
  test summary (from Sub-Task 3 + 4 healing loop output).
- `agents.validation.summary_verdict` must be Bob's synthesized quality verdict, not a
  f-string template.
- All numeric fields (`tests_executed`, `tests_passed`, `coverage_percentage`,
  `readiness_score`) must continue to come from real Jest execution output — they are
  already real and must remain so.
- The `latest-pipeline-run.json` schema must not change (dashboard compatibility).

### Expected Outcomes
- Opening `latest-pipeline-run.json` shows Bob's narrative text in every `*_markdown` field.
- `agents.reviewer.findings[]` matches what Bob identified, not what regex matched.
- `agents.validation.summary_verdict` is a coherent summary written by the validation agent.
- No field contains placeholder text like "Execução não solicitada nesta chamada".

### Todo List
1. In `run_code_reviewer_agent()`, set `agent_report_markdown` from Bob's response text.
2. In `run_test_engineer_agent()`, add `test_report_markdown` from the test engineer Bob call.
3. In `run_validation_agent()`, call Bob's validation persona (`.bob/agents/05-validation-agent.md`)
   with the aggregated metrics dict and store its textual summary in `summary_verdict`.
4. Verify `latest-pipeline-run.json` schema compatibility with `dashboard/src/App.jsx`
   (read App.jsx to confirm which keys the dashboard consumes).
5. Write a smoke-test script `core/smoke_test.py` that runs the full pipeline against
   `benchmarks/sample-diff.patch` and asserts that no `*_markdown` field contains the
   static placeholder strings.

### Relevant Context
- `core/orchestrator.py:177-188` — where `agent_report_markdown` is currently set.
- `core/orchestrator.py:363-411` — `run_validation_agent()` — `summary_verdict` f-string.
- `.bob/agents/05-validation-agent.md` — validation persona output schema.
- `dashboard/src/App.jsx` — consumer of `/api/latest` JSON (must not break).
- `benchmarks/latest-pipeline-run.json` — current schema reference.
