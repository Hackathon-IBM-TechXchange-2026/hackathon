#!/usr/bin/env python3
"""
ChangeFlow CLI — IBM Bob 2.0 Agent Tool Interface.

Exposes every orchestrator phase as a standalone subcommand so that Bob skills
can invoke individual agents or the full pipeline and receive clean JSON on stdout.

Usage:
    python core/cli.py onboard
    python core/cli.py analyze   <patch_file>
    python core/cli.py review    <patch_file>
    python core/cli.py test      <patch_file>
    python core/cli.py validate  <patch_file>
    python core/cli.py run       <patch_file>          # full pipeline
    python core/cli.py run       --save                # full pipeline + write JSON

All subcommands exit 0 on success and print a single JSON object to stdout.
Errors exit 1 and print {"error": "<message>"} to stdout (never to stderr).
"""

import os
import sys
import json
import argparse

# Ensure the project root is importable from any working directory
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_DEFAULT_PATCH = os.path.join(_ROOT, "benchmarks", "sample-diff.patch")
_DEFAULT_OUTPUT = os.path.join(_ROOT, "benchmarks", "latest-pipeline-run.json")


def _json_out(data: dict, save_path: str | None = None) -> None:
    """Print JSON to stdout and optionally persist to a file."""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    print(text)
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"\n📄 Output written to: {save_path}", file=sys.stderr)


class _StdoutToStderr:
    """Context manager that redirects sys.stdout to sys.stderr so that
    orchestrator print() banners don't pollute the JSON output on stdout."""

    def __enter__(self):
        self._orig = sys.stdout
        sys.stdout = sys.stderr
        return self

    def __exit__(self, *_):
        sys.stdout = self._orig


def _make_orchestrator():
    from core.orchestrator import ChangeFlowOrchestrator
    return ChangeFlowOrchestrator(_ROOT)


# ──────────────────────────────────────────────────────────────────────────────
# Subcommand handlers
# ──────────────────────────────────────────────────────────────────────────────

def cmd_onboard(_args) -> dict:
    """Agent 00: Scan repo stack, generate AGENTS.md and Mermaid diagrams."""
    with _StdoutToStderr():
        orc = _make_orchestrator()
        return orc.run_onboarding_agent()


def cmd_analyze(args) -> dict:
    """Agent 01: Parse the diff and build the dependency impact map."""
    patch = getattr(args, "patch", _DEFAULT_PATCH)
    if not os.path.exists(patch):
        return {"error": f"Patch file not found: {patch}"}
    with _StdoutToStderr():
        orc = _make_orchestrator()
        return orc.run_analyzer_agent(patch)


def cmd_review(args) -> dict:
    """Agent 02: Static security + quality analysis of changed files."""
    patch = getattr(args, "patch", _DEFAULT_PATCH)
    if not os.path.exists(patch):
        return {"error": f"Patch file not found: {patch}"}
    with _StdoutToStderr():
        orc = _make_orchestrator()
        analyzer = orc.run_analyzer_agent(patch)
        return orc.run_code_reviewer_agent(analyzer["data"])


def cmd_test(args) -> dict:
    """Agent 04: PyTest skeleton generation, self-healing loop, Jest suite."""
    patch = getattr(args, "patch", _DEFAULT_PATCH)
    if not os.path.exists(patch):
        return {"error": f"Patch file not found: {patch}"}
    with _StdoutToStderr():
        orc = _make_orchestrator()
        analyzer = orc.run_analyzer_agent(patch)
        return orc.run_test_engineer_agent(analyzer["data"])


def cmd_validate(args) -> dict:
    """Agent 05: Quality gate — consolidates all phase results."""
    patch = getattr(args, "patch", _DEFAULT_PATCH)
    if not os.path.exists(patch):
        return {"error": f"Patch file not found: {patch}"}
    with _StdoutToStderr():
        import concurrent.futures
        orc = _make_orchestrator()
        orc._pipeline_start = __import__("time").time()
        analyzer = orc.run_analyzer_agent(patch)
        impact = analyzer["data"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            fr = ex.submit(orc.run_code_reviewer_agent, impact)
            fd = ex.submit(orc.run_documentation_agent, analyzer)
            ft = ex.submit(orc.run_test_engineer_agent, impact)
            reviewer, doc, test = fr.result(), fd.result(), ft.result()
        return orc.run_validation_agent(analyzer, reviewer, doc, test)


def cmd_run(args) -> dict:
    """Full pipeline: phases 0–5 in the canonical order."""
    patch = getattr(args, "patch", _DEFAULT_PATCH)
    if not os.path.exists(patch):
        return {"error": f"Patch file not found: {patch}"}
    save = getattr(args, "save", False)
    with _StdoutToStderr():
        orc = _make_orchestrator()
        result = orc.execute_pipeline(patch)
    if save:
        with open(_DEFAULT_OUTPUT, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
        print(f"📄 Full pipeline run written to: {_DEFAULT_OUTPUT}", file=sys.stderr)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Argument parser
# ──────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python core/cli.py",
        description="ChangeFlow CLI — IBM Bob 2.0 agent tool interface",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("onboard", help="Agent 00: Repo stack scan & AGENTS.md generation")

    for name, help_text in [
        ("analyze", "Agent 01: Diff parsing and dependency impact map"),
        ("review",  "Agent 02: Static security + quality analysis"),
        ("test",    "Agent 04: PyTest skeleton, self-healing loop, Jest suite"),
        ("validate","Agent 05: Quality gate consolidation"),
    ]:
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument(
            "patch", nargs="?", default=_DEFAULT_PATCH,
            help=f"Path to the .patch file (default: {_DEFAULT_PATCH})"
        )

    run_p = sub.add_parser("run", help="Full pipeline (phases 0–5)")
    run_p.add_argument(
        "patch", nargs="?", default=_DEFAULT_PATCH,
        help=f"Path to the .patch file (default: {_DEFAULT_PATCH})"
    )
    run_p.add_argument(
        "--save", action="store_true",
        help=f"Persist JSON output to {_DEFAULT_OUTPUT}"
    )

    return p


_HANDLERS = {
    "onboard":  cmd_onboard,
    "analyze":  cmd_analyze,
    "review":   cmd_review,
    "test":     cmd_test,
    "validate": cmd_validate,
    "run":      cmd_run,
}


def main():
    parser = build_parser()
    args = parser.parse_args()
    handler = _HANDLERS[args.command]
    try:
        result = handler(args)
    except Exception as exc:
        result = {"error": str(exc), "command": args.command}
        sys.exit(1)
    _json_out(result)


if __name__ == "__main__":
    main()
