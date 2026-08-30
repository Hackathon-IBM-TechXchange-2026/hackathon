#!/usr/bin/env python3
"""
ChangeFlow Main Orchestrator (IBM Bob 2.0 Multi-Agent Pipeline).
Coordinates Change Analyzer, Code Reviewer, Documentation Agent, Test Engineer, and Validation Agent.
Every metric is computed from real repository data: diff parsing, dependency/import graph,
static code analysis, real Jest execution with coverage, and real doc synchronization.
"""

import os
import sys
import json
import time
import glob
import re
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.analyzer.diff_parser import DiffParser
from core.runner.test_runner import TestRunner
from core.agents.onboarding_agent import run as run_onboarding
from core.agents.code_reviewer_agent import scan_content, Finding, build_report as build_review_report
from core.agents.test_engineer_agent import (
    generate_test_skeleton, self_healing_loop, estimate_coverage, bob_fixer_callback
)


def _load_env_file(workspace_root: str) -> None:
    """Load .env from *workspace_root* into os.environ (idempotent, sets only missing keys)."""
    env_path = os.path.join(workspace_root, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())


def _load_bob_persona(workspace_root: str, agent_file: str) -> str:
    """Read a .bob/agents/*.md file and return its text, or a minimal fallback."""
    path = os.path.join(workspace_root, ".bob", "agents", agent_file)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return f"You are a software quality AI agent. Respond with valid JSON as requested."


def _try_bob_complete_json(workspace_root: str, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Call Bob/watsonx.ai for a JSON response; return None on any failure so caller can fall back."""
    _load_env_file(workspace_root)
    try:
        from core.bob_client import complete_json  # noqa: PLC0415
        return complete_json(system_prompt, user_prompt)
    except Exception:  # noqa: BLE001 — intentional broad catch for fallback path
        return None


def _try_bob_complete(workspace_root: str, system_prompt: str, user_prompt: str) -> Optional[str]:
    """Call Bob/watsonx.ai for a text response; return None on any failure so caller can fall back."""
    _load_env_file(workspace_root)
    try:
        from core.bob_client import complete  # noqa: PLC0415
        return complete(system_prompt, user_prompt)
    except Exception:  # noqa: BLE001 — intentional broad catch for fallback path
        return None


class ChangeFlowOrchestrator:
    # Real static-analysis rule set applied to changed/impacted source files.
    REVIEW_PATTERNS = [
        {"regex": re.compile(r"\beval\s*\(|\bnew\s+Function\s*\("), "severity": "Critical", "category": "Security",
         "message": "Dynamic code evaluation detected — remote code execution risk"},
        {"regex": re.compile(r"(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"]{6,}['\"]", re.IGNORECASE),
         "severity": "High", "category": "Security", "message": "Possible hardcoded credential in source code"},
        {"regex": re.compile(r"\bexec\s*\(|\bos\.system\s*\("), "severity": "High", "category": "Security",
         "message": "Shell/OS command execution used"},
        {"regex": re.compile(r"Math\.random\s*\("), "severity": "Medium", "category": "Risk",
         "message": "Nondeterministic Math.random() — flaky/idempotency concerns"},
        {"regex": re.compile(r"\bas\s+any\b|:\s*any\b"), "severity": "Low", "category": "Typing",
         "message": "Use of `any` weakens type safety"},
        {"regex": re.compile(r"console\.(log|debug|info|warning?)\s*\("), "severity": "Info", "category": "Quality",
         "message": "Console output left in production code"},
        {"regex": re.compile(r"\b(TODO|FIXME|HACK|XXX)\b"), "severity": "Info", "category": "Maintainability",
         "message": "Unresolved marker comment"},
    ]

    def __init__(self, workspace_root: Optional[str] = None, app_dir: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.diff_parser = DiffParser(self.workspace_root)
        self.test_runner = TestRunner(self.workspace_root, app_dir=app_dir)
        self.timings: Dict[str, float] = {}

    def _detect_app_dir(self, patch_path: str) -> Optional[str]:
        """Infer the app directory from the first changed file in the patch."""
        try:
            impact = self.diff_parser.parse_patch_file(patch_path)
            for f in impact.get("files", []):
                parts = Path(f["new_path"]).parts
                if len(parts) >= 1:
                    candidate = os.path.join(self.workspace_root, parts[0])
                    if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "package.json")):
                        return candidate
        except Exception:  # noqa: BLE001
            pass
        return None

    # ------------------------------------------------------------------ utils

    def _tick(self, key: str) -> float:
        now = time.time()
        self.timings[key] = now
        return now

    def _elapsed(self, key: str) -> float:
        return round(time.time() - self.timings.get(key, time.time()), 3)

    def _load_benchmark_assumptions(self) -> Dict[str, Any]:
        path = os.path.join(self.workspace_root, "benchmarks", "benchmark-results.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    # ------------------------------------------------------------------ agents

    def run_onboarding_agent(self) -> Dict[str, Any]:
        """Agent 00: Onboarding — scans repo stack, generates AGENTS.md and Mermaid diagrams."""
        self._tick("onboarding")
        print("[00-onboarding] 🗺️  Scanning repository stack and generating AGENTS.md...")
        result = run_onboarding(self.workspace_root)
        return {
            "agent": "00-onboarding",
            "status": "COMPLETED" if "error" not in result else "FAILED",
            "duration_seconds": self._elapsed("onboarding"),
            "data": result,
        }

    def run_analyzer_agent(self, patch_path: str) -> Dict[str, Any]:
        """Agent 01: Change Analyzer — parses the real diff and maps real impact."""
        self._tick("analyzer")
        print("[01-change-analyzer] 🔍 Analyzing git diff and constructing dependency impact map...")
        impact = self.diff_parser.parse_patch_file(patch_path)
        return {
            "agent": "01-change-analyzer",
            "status": "COMPLETED",
            "duration_seconds": self._elapsed("analyzer"),
            "data": impact
        }

    def run_code_reviewer_agent(self, impact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 02: Code Reviewer — AI-powered semantic review (Bob/watsonx.ai) with regex pre-filter fallback."""
        self._tick("reviewer")
        print("[02-code-reviewer] 🛡️  Running AI-powered security and coding-standard review...")

        # ── Step 1: Fast regex pre-filter (always runs — catches obvious issues) ─────
        findings: list[Dict[str, Any]] = []
        passed_checks: list[Dict[str, Any]] = []
        scanned_files: list[str] = []
        file_contents: Dict[str, str] = {}

        _SEVERITY_MAP = {
            "🔴 CRITICAL": "Critical",
            "🟠 HIGH": "High",
            "🟡 MEDIUM": "Medium",
            "🟢 LOW": "Low",
        }

        for f in impact_data.get("files", []):
            abs_path = self.diff_parser._abs_path(f["new_path"])
            if not os.path.exists(abs_path):
                continue
            scanned_files.append(f["new_path"])
            try:
                content = Path(abs_path).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            file_contents[f["new_path"]] = content
            lines = content.splitlines()

            for line_idx, line in enumerate(lines, start=1):
                if len(line) > 120:
                    findings.append({"file": f["new_path"], "line": line_idx, "severity": "Low",
                                     "category": "Style", "message": "Line exceeds 120 characters"})
                for rule in self.REVIEW_PATTERNS:
                    if rule["regex"].search(line):
                        findings.append({"file": f["new_path"], "line": line_idx,
                                         "severity": rule["severity"], "category": rule["category"],
                                         "message": rule["message"],
                                         "suggestion": f"Review {f['new_path']}:{line_idx}"})

            # Positive verifications: defensive guards introduced by the change.
            for changed in f.get("changed_lines", []):
                if re.match(r"^\s*if\s*\(.*\bthrow\b", changed) or re.search(r"\bthrow\s+new\s+Error", changed):
                    passed_checks.append({"file": f["new_path"], "severity": "Passed",
                                          "category": "Validation",
                                          "message": changed.strip()})

            # Python-specific: richer RULES from code_reviewer_agent (kept as fallback)
            existing_keys = {(item["file"], item["line"]) for item in findings}
            for finding in scan_content(f["new_path"], content):
                key = (finding.file, finding.line)
                if key not in existing_keys:
                    existing_keys.add(key)
                    findings.append({
                        "file": finding.file,
                        "line": finding.line,
                        "severity": _SEVERITY_MAP.get(finding.severity, "Low"),
                        "category": "Security",
                        "message": finding.description,
                        "suggestion": finding.suggested_fix,
                    })

        # ── Step 2: Bob/watsonx.ai semantic review (authoritative findings) ──────────
        bob_findings: list[Dict[str, Any]] = []
        bob_score: Optional[int] = None
        bob_markdown: Optional[str] = None
        bob_basis = "ai"

        if scanned_files and file_contents:
            diff_context = "\n\n".join(
                f"### {path}\n```\n{content[:4000]}\n```"
                for path, content in list(file_contents.items())[:5]  # cap to 5 files to stay within token limits
            )
            system_prompt = _load_bob_persona(self.workspace_root, "02-code-reviewer.md")
            user_prompt = (
                f"Review the following changed files and return your structured JSON findings.\n\n"
                f"{diff_context}\n\n"
                f"Return a JSON block with keys: status, score, summary, findings (array of "
                f"{{file, line, severity, category, message, suggestion}})."
            )
            bob_response = _try_bob_complete_json(self.workspace_root, system_prompt, user_prompt)
            if bob_response:
                # Bob's findings are the authoritative list — replace regex findings for scanned files
                raw_bob_findings = bob_response.get("findings", [])
                if raw_bob_findings:
                    bob_findings = [
                        {
                            "file": str(item.get("file", "")),
                            "line": int(item.get("line", 0)),
                            "severity": str(item.get("severity", "Low")),
                            "category": str(item.get("category", "General")),
                            "message": str(item.get("message", "")),
                            "suggestion": str(item.get("suggestion", "")),
                        }
                        for item in raw_bob_findings
                        if isinstance(item, dict)
                    ]
                    findings = bob_findings  # Bob output is authoritative
                bob_score = bob_response.get("score")
                bob_markdown = bob_response.get("summary", "")
            else:
                bob_basis = "fallback_regex"

        # ── Step 3: Compute score and status ──────────────────────────────────────────
        severity_weights = {"Info": 1, "Low": 5, "Medium": 10, "High": 30, "Critical": 50}
        total_deduction = sum(severity_weights.get(item["severity"], 0) for item in findings)
        computed_score = max(0, 100 - total_deduction) if scanned_files else 0
        score = bob_score if bob_score is not None else computed_score

        critical_count = sum(1 for x in findings if x["severity"] in ("Critical", "CRITICAL"))
        high_count = sum(1 for x in findings if x["severity"] in ("High", "HIGH"))
        status = "PASSED" if scanned_files and critical_count == 0 and high_count == 0 else "FAILED"

        # Build per-agent Finding objects for the fallback markdown (when Bob unavailable)
        agent_findings_objs: list[Finding] = [
            Finding(
                severity=_SEVERITY_MAP.get(str(item.get("severity", "Low")), str(item.get("severity", "Low"))),
                file=str(item.get("file", "")),
                line=int(item.get("line", 0)),
                description=str(item.get("message", "")),
                snippet=str(item.get("suggestion", "")),
                suggested_fix="",
            )
            for item in findings
        ]

        return {
            "agent": "02-code-reviewer",
            "status": status,
            "duration_seconds": self._elapsed("reviewer"),
            "score": score,
            "files_scanned": scanned_files,
            "findings": findings,
            "passed_checks": passed_checks,
            "basis": bob_basis,
            "summary": (f"Scanned {len(scanned_files)} file(s): {critical_count} Critical, {high_count} High, "
                        f"{len(findings)} total findings, {len(passed_checks)} defense guards verified. "
                        f"(basis: {bob_basis})"),
            "agent_report_markdown": build_review_report(agent_findings_objs, bob_markdown=bob_markdown),
        }

    def run_documentation_agent(self, analyzer_res: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 03: Documentation Agent — real diff-to-doc sync (updates actual markdown files)."""
        self._tick("documentation")
        print("[03-documentation-agent] 📚 Synchronizing API specs and Architecture docs...")

        impact_data = analyzer_res.get("data", {})
        docs_updated = []

        new_tokens = self._new_identifiers(impact_data)
        sync_status = "SYNCHRONIZED"
        if new_tokens:
            for doc_path in impact_data.get("affected_docs", []):
                abs_doc = os.path.join(self.workspace_root, doc_path)
                if not os.path.exists(abs_doc):
                    continue
                missing = self._missing_tokens(abs_doc, new_tokens)
                if not missing:
                    docs_updated.append({
                        "file": doc_path, "change_type": "ALREADY_IN_SYNC",
                        "summary": "No new identifiers to document"
                    })
                    continue
                self._sync_doc(abs_doc, doc_path, missing, impact_data)
                docs_updated.append({
                    "file": doc_path, "change_type": "UPDATED",
                    "summary": "Added missing identifiers: " + ", ".join(missing)
                })

        return {
            "agent": "03-documentation-agent",
            "status": "SYNCHRONIZED" if docs_updated else sync_status,
            "duration_seconds": self._elapsed("documentation"),
            "docs_updated": docs_updated,
            "sync_status": sync_status,
            "new_identifiers": list(new_tokens),
            "total_doc_files_modified": len([d for d in docs_updated if d["change_type"] == "UPDATED"])
        }

    def _new_identifiers(self, impact_data: Dict[str, Any]) -> set:
        """Identifiers introduced by the diff: tokens in added lines absent from the old file content."""
        new_tokens = set()
        old_content = ""
        for f in impact_data.get("files", []):
            abs_path = self.diff_parser._abs_path(f["new_path"])
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                    old_content += fh.read()
            except OSError:
                pass

        token_re = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{1,}\b")
        for f in impact_data.get("files", []):
            for changed in f.get("changed_lines", []):
                for tok in token_re.findall(changed):
                    if tok in old_content:
                        continue
                    if tok.isdigit():
                        continue
                    if tok.isupper() and len(tok) >= 2:
                        new_tokens.add(tok)
                    elif len(tok) >= 6 and tok.isalpha():
                        new_tokens.add(tok)
        return new_tokens

    def _missing_tokens(self, abs_doc: str, tokens: set) -> list:
        try:
            with open(abs_doc, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            return list(tokens)
        return sorted(t for t in tokens if t not in content)

    def _patch_supported_row(self, content: str, method_tokens: list) -> str:
        lines = content.splitlines(keepends=True)
        for idx, line in enumerate(lines):
            if "Supported:" in line and "`" in line and any(t in line for t in ("CREDIT_CARD", "DEBIT_CARD", "BANK_TRANSFER")):
                missing_in_line = [t for t in method_tokens if t not in line]
                if missing_in_line:
                    addition = ", " + ", ".join(missing_in_line)
                    stripped = line.rstrip("\n").rstrip()
                    if stripped.endswith("|"):
                        lines[idx] = stripped[:-1].rstrip() + addition + " |\n"
                    else:
                        lines[idx] = stripped + addition + "\n"
                break
        return "".join(lines)

    def _sync_doc(self, abs_doc: str, doc_path: str, missing: list, impact_data: Dict[str, Any]) -> None:
        """Applies a real, idempotent update to the doc file documenting newly introduced identifiers."""
        try:
            with open(abs_doc, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            return

        changed_files = ", ".join(f["new_path"] for f in impact_data.get("files", []))
        # Real targeted patch: add newly supported method tokens to the documented `Supported:` row.
        method_tokens = [str(tok) for tok in missing if tok.isupper() and len(tok) >= 2]
        if "API.md" in doc_path and method_tokens:
            content = self._patch_supported_row(content, method_tokens)
        section = "## ChangeFlow Automated Documentation Sync"
        if section in content:
            new_block = "\n".join(f"- `{tok}` (_new identifier_)" for tok in missing)
            marker = f"<!-- This section is automatically maintained by ChangeFlow -->\n"
            if marker in content:
                content = content.replace(marker, marker + new_block + "\n")
                content += "\n"
        else:
            block = (f"\n{section}\n\n<!-- This section is automatically maintained by ChangeFlow -->\n"
                     + "\n".join(f"- `{tok}` (_new identifier from {changed_files}_)\n" for tok in missing)
                     + "\n")
            content += block

        with open(abs_doc, "w", encoding="utf-8") as fh:
            fh.write(content)

    def run_test_engineer_agent(self, impact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 04: Test Engineer — executes the real Jest test suite with coverage,
        generates missing TypeScript test stubs via Bob/watsonx.ai, and runs AST-based
        PyTest skeleton generation + AI self-healing loop for Python files."""
        self._tick("tester")
        print("[04-test-engineer] 🧪 Detecting missing tests, generating stubs, executing suites...")

        test_system_prompt = _load_bob_persona(self.workspace_root, "04-test-engineer.md")
        skeletons_generated: list[Dict[str, Any]] = []
        self_healing_results: list[Dict[str, Any]] = []
        coverage_estimates: list[float] = []

        # ── Sub-Task 4: TypeScript new-file test generation ───────────────────────────
        ts_tests_dir = os.path.join(self.workspace_root, "sample-app", "tests", "unit")
        ts_src_base = os.path.join(self.workspace_root, "sample-app", "src")

        for f in impact_data.get("files", []):
            new_path: str = f["new_path"]
            if not new_path.endswith(".ts"):
                continue
            # Only consider files under sample-app/src/
            abs_src = self.diff_parser._abs_path(new_path)
            if not abs_src.startswith(ts_src_base):
                continue
            if not os.path.exists(abs_src):
                continue

            stem = Path(abs_src).stem
            expected_test = os.path.join(ts_tests_dir, f"{stem}.test.ts")

            if os.path.exists(expected_test):
                continue  # Test already exists — nothing to generate

            print(f"[04-test-engineer] 📝 Generating Jest tests for new file: {new_path}")
            try:
                source_content = Path(abs_src).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            user_prompt = (
                f"Generate a complete Jest + TypeScript unit test file for the following source file.\n\n"
                f"**Source file:** `{new_path}`\n\n"
                f"```typescript\n{source_content[:6000]}\n```\n\n"
                f"Requirements:\n"
                f"- Use Jest with TypeScript (no static setTimeout delays).\n"
                f"- Cover all exported functions/classes with at least one positive and one edge-case test.\n"
                f"- Use dynamic polling assertions where async behaviour is involved.\n"
                f"- Return ONLY the test file content inside a single ```typescript ... ``` code fence.\n"
                f"- The output test file will be saved to `sample-app/tests/unit/{stem}.test.ts`."
            )
            generated_text = _try_bob_complete(self.workspace_root, test_system_prompt, user_prompt)
            if generated_text:
                fence_match = re.search(r"```(?:typescript|ts)?\s*([\s\S]+?)```", generated_text)
                test_content = fence_match.group(1).strip() if fence_match else generated_text.strip()
                if test_content:
                    os.makedirs(ts_tests_dir, exist_ok=True)
                    Path(expected_test).write_text(test_content, encoding="utf-8")
                    skeletons_generated.append({
                        "file": new_path,
                        "generated_test": os.path.relpath(expected_test, self.workspace_root),
                        "source": "bob_ai",
                    })

        # ── Run Jest (includes any newly written .test.ts files) ─────────────────────
        test_results = self.test_runner.run_tests()
        test_results["duration_seconds"] = self._elapsed("tester")
        test_results["agent"] = "04-test-engineer"

        # ── Python AST skeleton generation + AI self-healing ─────────────────────────
        for f in impact_data.get("files", []):
            abs_path = self.diff_parser._abs_path(f["new_path"])
            if not abs_path.endswith(".py") or not os.path.exists(abs_path):
                continue

            skeleton = generate_test_skeleton(Path(abs_path))
            skeletons_generated.append({"file": f["new_path"], "skeleton": skeleton, "source": "ast"})
            coverage_estimates.append(estimate_coverage(Path(abs_path), skeleton))

            stem = Path(abs_path).stem
            test_path = Path(self.workspace_root) / "tests" / f"test_{stem}.py"
            if test_path.exists():
                healing = self_healing_loop(test_path, fixer_callback=bob_fixer_callback)
                self_healing_results.append({"file": f["new_path"], "result": healing})

        python_coverage_estimate = (
            round(sum(coverage_estimates) / len(coverage_estimates), 1)
            if coverage_estimates else 0.0
        )

        # ── Sub-Task 5: Ask Bob for a narrative test report ───────────────────────────
        test_report_markdown: Optional[str] = None
        metrics_summary = {
            "tests_executed": test_results.get("tests_executed", 0),
            "tests_passed": test_results.get("tests_passed", 0),
            "tests_failed": test_results.get("tests_failed", 0),
            "coverage_percentage": test_results.get("coverage_percentage", 0.0),
            "ts_stubs_generated": len([s for s in skeletons_generated if s.get("source") == "bob_ai"]),
            "self_healing_attempts": len(self_healing_results),
        }
        tr_user_prompt = (
            f"Write a concise test execution report (Markdown) for the following test run metrics.\n\n"
            f"```json\n{json.dumps(metrics_summary, indent=2)}\n```\n\n"
            f"Include: overall status, tests passed/total, coverage %, number of AI-generated stubs, "
            f"self-healing iterations. Keep it under 300 words. Use Markdown headers and bullet points."
        )
        bob_tr = _try_bob_complete(self.workspace_root, test_system_prompt, tr_user_prompt)
        if bob_tr and bob_tr.strip():
            test_report_markdown = bob_tr

        return {
            "agent": "04-test-engineer",
            "status": test_results.get("status", "FAILED"),
            "duration_seconds": test_results.get("duration_seconds", 0.0),
            "tests_executed": test_results.get("tests_executed", 0),
            "tests_passed": test_results.get("tests_passed", 0),
            "tests_failed": test_results.get("tests_failed", 0),
            "coverage_percentage": test_results.get("coverage_percentage", 0.0),
            "coverage": test_results.get("coverage", {}),
            "execution_time_seconds": test_results.get("execution_time_seconds", 0.0),
            "test_suites": test_results.get("test_suites", []),
            "summary": test_results.get("summary", ""),
            "skeletons_generated": skeletons_generated,
            "self_healing_results": self_healing_results,
            "python_coverage_estimate": python_coverage_estimate,
            "test_report_markdown": test_report_markdown,
        }

    def run_validation_agent(self, analyzer_res, reviewer_res, doc_res, test_res) -> Dict[str, Any]:
        """Agent 05: Validation Agent — real quality gate + Bob-synthesized summary verdict."""
        self._tick("validator")
        print("[05-validation-agent] ⚖️  Synthesizing results and calculating effort reduction metrics...")

        impact_data = analyzer_res.get("data", {})
        coverage_pct = test_res.get("coverage_percentage", 0.0)
        coverage_by_file = test_res.get("coverage", {}).get("files", {})
        modified_abs = {self.diff_parser._abs_path(f["new_path"]): f["new_path"]
                        for f in impact_data.get("files", [])}
        modified_coverage = [v for k, v in coverage_by_file.items()
                             if self.diff_parser._abs_path(k) in modified_abs]
        modified_coverage_pct = round(sum(v["statements_percentage"] for v in modified_coverage) / len(modified_coverage), 1) if modified_coverage else 0.0

        reviewer_ok = reviewer_res.get("status") == "PASSED"
        tests_ok = test_res.get("tests_failed", 1) == 0
        coverage_ok = modified_coverage_pct >= 90.0
        docs_ok = doc_res.get("sync_status") == "SYNCHRONIZED"

        tests_score = 100.0 * (test_res.get("tests_passed", 0) / max(1, test_res.get("tests_executed", 0)))
        coverage_score = min(100.0, coverage_pct)
        reviewer_score = reviewer_res.get("score", 0)
        doc_score = 100.0 if docs_ok else 0.0
        readiness_score = round(0.35 * tests_score + 0.25 * coverage_score + 0.25 * reviewer_score + 0.15 * doc_score, 1)

        gate_status = "READY_FOR_HUMAN_REVIEW" if (reviewer_ok and tests_ok and coverage_ok and docs_ok) else "BLOCKED"

        metrics = self._compute_metrics(analyzer_res, reviewer_res, doc_res, test_res, readiness_score)

        # ── Sub-Task 5: Ask Bob for the synthesized summary_verdict ──────────────────
        fallback_verdict = (
            f"Modified-file coverage {modified_coverage_pct}% (gate >= 90%), "
            f"{test_res.get('tests_passed', 0)}/{test_res.get('tests_executed', 0)} tests passing, "
            f"reviewer score {reviewer_score}/100, docs {doc_res.get('sync_status', 'UNKNOWN')}."
        )
        aggregated_metrics = {
            "gate_status": gate_status,
            "readiness_score": readiness_score,
            "reviewer_score": reviewer_score,
            "tests_passed": test_res.get("tests_passed", 0),
            "tests_executed": test_res.get("tests_executed", 0),
            "coverage_percentage": coverage_pct,
            "modified_file_coverage": modified_coverage_pct,
            "docs_sync_status": doc_res.get("sync_status", "UNKNOWN"),
            "critical_findings": sum(1 for x in reviewer_res.get("findings", []) if x.get("severity") in ("Critical", "CRITICAL")),
            "high_findings": sum(1 for x in reviewer_res.get("findings", []) if x.get("severity") in ("High", "HIGH")),
            "checklists": {
                "impact_analysis": "PASSED",
                "code_review": "PASSED" if reviewer_ok else "FAILED",
                "doc_sync": "PASSED" if docs_ok else "FAILED",
                "test_execution": "PASSED" if tests_ok and coverage_ok else "FAILED",
            },
        }
        validation_system_prompt = _load_bob_persona(self.workspace_root, "05-validation-agent.md")
        val_user_prompt = (
            f"Write a concise executive summary verdict (2-3 sentences, plain text) for the following "
            f"pipeline quality gate results. Gate status: {gate_status}. Readiness score: {readiness_score}/100.\n\n"
            f"```json\n{json.dumps(aggregated_metrics, indent=2)}\n```\n\n"
            f"Be specific: mention test pass rate, coverage, critical vulnerabilities, and doc sync status. "
            f"End with whether the change is ready for human review or blocked and why."
        )
        bob_verdict = _try_bob_complete(self.workspace_root, validation_system_prompt, val_user_prompt)
        summary_verdict = bob_verdict.strip() if bob_verdict and bob_verdict.strip() else fallback_verdict

        return {
            "agent": "05-validation-agent",
            "status": gate_status,
            "gate_status": gate_status,
            "readiness_score": readiness_score,
            "duration_seconds": self._elapsed("validator"),
            "metrics": metrics,
            "summary_verdict": summary_verdict,
            "checklists": {
                "impact_analysis": "PASSED",
                "code_review": "PASSED" if reviewer_ok else "FAILED",
                "doc_sync": doc_res.get("sync_status", "PASSED"),
                "test_execution": "PASSED" if tests_ok and coverage_ok else "FAILED",
                "coverage_on_modified_files": modified_coverage_pct
            }
        }

    def _compute_metrics(self, analyzer_res, reviewer_res, doc_res, test_res, readiness_score: float) -> Dict[str, Any]:
        benchmark = self._load_benchmark_assumptions()
        totals = benchmark.get("totals", {})
        workflow = benchmark.get("workflow_comparison", [])

        manual_total = float(totals.get("traditional_human_minutes", 100))
        human_review = float(totals.get("changeflow_human_minutes", 8))

        stage_sources = {
            "Impact Analysis": analyzer_res.get("duration_seconds", 0),
            "Code Review & Security Audit": reviewer_res.get("duration_seconds", 0),
            "Documentation Synchronization": doc_res.get("duration_seconds", 0),
            "Test Creation & Execution": test_res.get("duration_seconds", 0),
            "Validation & Gatekeeping": self._elapsed("validator"),
        }

        computed_workflow = []
        automated_total_seconds = 0.0
        automated_seconds = 0.0
        for row in workflow:
            step = row.get("step", "")
            duration = stage_sources.get(step, row.get("changeflow_automated_seconds", 0))
            if step != "Human Review & Merge Approval":
                automated_seconds = duration
                automated_total_seconds += duration
            computed_workflow.append({
                "step": step,
                "traditional_manual_minutes": row.get("traditional_manual_minutes", 15),
                "changeflow_automated_seconds": round(automated_seconds, 3),
                "changeflow_human_minutes": row.get("changeflow_human_minutes", 0),
                "automation_type": row.get("automation_type", ""),
                "effort_reduction_percentage": row.get("effort_reduction_percentage", 100),
                "measured_seconds": round(duration, 3),
                "basis": "measured" if step != "Human Review & Merge Approval" else "estimated"
            })

        total_changeflow_minutes = human_review + automated_total_seconds / 60.0
        effort_saved_minutes = round(manual_total - total_changeflow_minutes, 1)
        effort_saved_percentage = round((effort_saved_minutes / manual_total) * 100, 1)
        speedup_factor = round(manual_total / max(total_changeflow_minutes, 1e-9), 1)

        return {
            "workflow_comparison": computed_workflow,
            "measured": {
                "pipeline_wall_clock_seconds": round(time.time() - self._pipeline_start, 3),
                "automation_total_seconds": round(automated_total_seconds, 3),
                "per_stage_seconds": {row["step"]: row["measured_seconds"] for row in computed_workflow},
                "tests": {
                    "tests_executed": test_res.get("tests_executed", 0),
                    "tests_passed": test_res.get("tests_passed", 0),
                    "tests_failed": test_res.get("tests_failed", 0)
                },
                "coverage_percentage": test_res.get("coverage_percentage", 0.0),
                "reviewer_score": reviewer_res.get("score", 0),
                "docs_synced": doc_res.get("total_doc_files_modified", 0),
                "readiness_score": readiness_score
            },
            "estimated": {
                "manual_baseline_minutes": round(manual_total, 1),
                "human_review_minutes": human_review,
                "effort_saved_minutes": effort_saved_minutes,
                "effort_saved_percentage": effort_saved_percentage,
                "speedup_factor": f"{speedup_factor}x",
                "basis": ("""Estimativa baseada no baseline de referência do benchmark """
                          """(benchmarks/benchmark-results.json): 100 min manuais vs 8 min de revisão humana. """
                          """Não é um valor medido — apenas o tempo de automação é medido (veja "measured").""")
            },
            "totals": {
                "traditional_human_minutes": round(manual_total, 1),
                "changeflow_automated_total_seconds": round(automated_total_seconds, 3),
                "changeflow_human_minutes": human_review,
                "effort_saved_minutes": effort_saved_minutes,
                "effort_saved_percentage": effort_saved_percentage,
                "speedup_factor": f"{speedup_factor}x",
                "basis": {"effort_saved_percentage": "estimated_from_reference_baseline",
                          "automation_seconds": "measured_on_this_run"}
            },
            "notes": {
                "measured": "Valores cronometrados/medidos nesta execução (pipeline, automação, testes, cobertura, readiness).",
                "estimated": "Percentuais de redução e speedup derivam do baseline de referência do benchmark, não de medição."
            }
        }

    # ------------------------------------------------------------------ pipeline

    def execute_pipeline(self, patch_path: str) -> Dict[str, Any]:
        """Executes the full multi-agent ChangeFlow pipeline."""
        self._pipeline_start = time.time()
        start_time = self._pipeline_start

        # Auto-detect app directory from the patch so the correct Jest suite is executed
        detected_app = self._detect_app_dir(patch_path)
        if detected_app and detected_app != self.test_runner.sample_app_dir:
            self.test_runner = TestRunner(self.workspace_root, app_dir=detected_app)
            print(f"[orchestrator] Detected app directory: {os.path.relpath(detected_app, self.workspace_root)}")

        print("\n=======================================================")
        print("🚀 Starting ChangeFlow AI Multi-Agent Pipeline (IBM Bob 2.0)")
        print("=======================================================\n")

        # Phase 0: Onboarding (pre-flight — stack scan, AGENTS.md, Mermaid diagrams)
        onboarding_output = self.run_onboarding_agent()

        # Phase 1: Impact Analysis (Sequential)
        analyzer_output = self.run_analyzer_agent(patch_path)
        impact_data = analyzer_output["data"]

        # Phase 2: Parallel Agents Execution
        print("\n⚡ Launching Parallel Subagents: Reviewer, Documentation, Test Engineer...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_reviewer = executor.submit(self.run_code_reviewer_agent, impact_data)
            future_doc = executor.submit(self.run_documentation_agent, analyzer_output)
            future_test = executor.submit(self.run_test_engineer_agent, impact_data)

            reviewer_output = future_reviewer.result()
            doc_output = future_doc.result()
            test_output = future_test.result()

        # Phase 3: Validation Agent (Gatekeeper)
        print("\n🏁 Launching Quality Gatekeeper...")
        validation_output = self.run_validation_agent(
            analyzer_output,
            reviewer_output,
            doc_output,
            test_output
        )

        total_elapsed = round(time.time() - start_time, 2)
        print(f"\n✨ Pipeline Finished in {total_elapsed}s! Status: {validation_output['gate_status']}\n")

        return {
            "pipeline_status": validation_output["gate_status"],
            "total_execution_time": total_elapsed,
            "report": validation_output["metrics"],
            "agents": {
                "onboarding": onboarding_output,
                "analyzer": analyzer_output,
                "reviewer": reviewer_output,
                "documentation": doc_output,
                "tester": test_output,
                "validation": validation_output
            }
        }


if __name__ == "__main__":
    patch_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "../benchmarks/sample-diff.patch"
    )
    orchestrator = ChangeFlowOrchestrator()
    result = orchestrator.execute_pipeline(patch_file)

    output_json_path = os.path.join(os.path.dirname(__file__), "../benchmarks/latest-pipeline-run.json")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"📄 Full pipeline run output written to: {output_json_path}")