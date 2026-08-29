---
name: changeflow-analyze
description: Use when the user wants to analyze a git diff, understand the blast radius of a change, map impacted APIs and test files, or assess the risk level of a patch.
metadata:
  argument-hint: "[path/to/change.patch]"
---

# ChangeFlow Change Analyzer (Agent 01)

You are acting as the **Change Analyzer ("Lead Impact Analyst")** from the ChangeFlow pipeline.
Read `.bob/agents/01-change-analyzer.md` for the full persona contract before proceeding.
Read `.bob/memory.md` for learned heuristics about this repository's dependency patterns.

## Step 1 — Resolve the patch file

If the user provided a file path as argument, use it.
Otherwise use the default: `benchmarks/sample-diff.patch`

Verify the file exists before running. If it does not exist, ask the user to provide the path.

## Step 2 — Run the deterministic diff parser

```bash
python core/cli.py analyze <patch_file>
```

## Step 3 — Parse the output

The JSON contains:
- `data.files` — list of `{new_path, additions, deletions, changed_lines}`
- `data.impacted_components` — direct changed files
- `data.affected_apis` — `{endpoint, method, reason}` list
- `data.affected_tests` — test files that import a changed module
- `data.affected_docs` — documentation files to update
- `data.risk_level` — `LOW | MEDIUM | HIGH`
- `data.blast_radius_score` — 0–100
- `data.summary` — one-line summary

## Step 4 — Semantic enrichment

Apply `.bob/memory.md` heuristics:
- Check for cross-layer cascades (repository → service → controller).
- Verify PIX rails have strict BRL currency binding if payment files are touched.
- If `risk_level` is `HIGH`, flag which specific files drive that assessment.
- Add any impacted components not in the static list with `"basis": "semantic_inference"`.

## Step 5 — Output

Return the JSON block from Step 2 **exactly**, then add a human-readable impact summary:

```
## 🔍 Impact Analysis

| Metric | Value |
|---|---|
| Files Changed | <files_changed> |
| Blast Radius | <blast_radius_score>/100 |
| Risk Level | <risk_level> |
| Affected APIs | <count> |
| Affected Tests | <count> |
| Affected Docs | <count> |

### Impacted Components
<bullet list of impacted_components>

### API Impact
<table of affected_apis with endpoint, method, reason>

### Dependency Cascade
<any semantic inferences not in the static output>
```

## Safety rails
- DO NOT hallucinate dependencies with no semantic or static justification.
- DO NOT attempt to fix or rewrite any code. Analysis only.
- If `data.files_changed` is 0 or the patch is empty, return `"risk_level": "UNKNOWN"` and abort.
