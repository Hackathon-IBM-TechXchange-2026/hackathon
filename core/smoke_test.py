#!/usr/bin/env python3
"""
ChangeFlow Smoke Test — Sub-Task 5 validation.

Runs the full pipeline against benchmarks/sample-diff.patch and asserts:
  1. No *_markdown field contains the old static placeholder strings.
  2. The pipeline completes without raising an exception.
  3. The required JSON schema keys are present in the output.

Usage:
    python3 core/smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Load .env if present so watsonx credentials are available
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8") as _fh:
        for _line in _fh:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

STATIC_PLACEHOLDERS = [
    "Execução não solicitada nesta chamada",
    "aqui entraria a chamada ao Bob",
    "Nenhum fixer_callback configurado",
]


def check_no_placeholders(obj: object, path: str = "") -> list[str]:
    """Recursively walk *obj* and return a list of paths where a static placeholder was found."""
    violations: list[str] = []
    if isinstance(obj, str):
        for placeholder in STATIC_PLACEHOLDERS:
            if placeholder in obj:
                violations.append(f"{path}: contains placeholder '{placeholder}'")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            violations.extend(check_no_placeholders(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(check_no_placeholders(item, f"{path}[{i}]"))
    return violations


def main() -> None:
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    patch_file = os.path.join(workspace_root, "benchmarks", "sample-diff.patch")

    if not os.path.exists(patch_file):
        print(f"[smoke_test] SKIP — patch file not found: {patch_file}")
        sys.exit(0)

    print("[smoke_test] Running full ChangeFlow pipeline...")
    from core.orchestrator import ChangeFlowOrchestrator  # noqa: PLC0415

    orchestrator = ChangeFlowOrchestrator(workspace_root)
    try:
        result = orchestrator.execute_pipeline(patch_file)
    except Exception as exc:
        print(f"[smoke_test] FAIL — pipeline raised exception: {exc}", file=sys.stderr)
        sys.exit(1)

    # ── Assertion 1: no static placeholders ──────────────────────────────────
    violations = check_no_placeholders(result)
    if violations:
        print("[smoke_test] FAIL — static placeholder text found in output:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        sys.exit(1)

    # ── Assertion 2: required top-level schema keys present ──────────────────
    required_keys = ["pipeline_status", "total_execution_time", "report", "agents"]
    for key in required_keys:
        assert key in result, f"Missing top-level key: {key}"

    # ── Assertion 3: tester output includes test_report_markdown key ─────────
    tester = result.get("agents", {}).get("tester", {})
    assert "test_report_markdown" in tester, "tester output missing 'test_report_markdown' key"

    # ── Assertion 4: reviewer output includes 'basis' key ────────────────────
    reviewer = result.get("agents", {}).get("reviewer", {})
    assert "basis" in reviewer, "reviewer output missing 'basis' key"

    print("[smoke_test] PASS ✓  Pipeline completed, no static placeholders, schema verified.")
    print(f"  gate_status     : {result['pipeline_status']}")
    print(f"  reviewer basis  : {reviewer.get('basis')}")
    print(f"  summary_verdict : {result['agents']['validation'].get('summary_verdict', '')[:120]}")

    # Persist the output
    out_path = os.path.join(workspace_root, "benchmarks", "latest-pipeline-run.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print(f"  Output written  : {out_path}")


if __name__ == "__main__":
    main()
