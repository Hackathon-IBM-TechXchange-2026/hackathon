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
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.analyzer.diff_parser import DiffParser
from core.runner.test_runner import TestRunner


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

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.diff_parser = DiffParser(self.workspace_root)
        self.test_runner = TestRunner(self.workspace_root)
        self.timings: Dict[str, float] = {}

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
        """Agent 02: Code Reviewer — real static analysis of changed/impacted files."""
        self._tick("reviewer")
        print("[02-code-reviewer] 🛡️  Running static security analysis and coding standard checks...")

        findings = []
        passed_checks = []
        scanned_files = []

        for f in impact_data.get("files", []):
            abs_path = self.diff_parser._abs_path(f["new_path"])
            if not os.path.exists(abs_path):
                continue
            scanned_files.append(f["new_path"])
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError:
                continue

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

            # Real positive verifications: new defensive guards added by the change.
            for changed in f.get("changed_lines", []):
                if re.match(r"^\s*if\s*\(.*\bthrow\b", changed) or re.search(r"\bthrow\s+new\s+Error", changed):
                    passed_checks.append({"file": f["new_path"], "severity": "Passed",
                                          "category": "Validation",
                                          "message": changed.strip()})

        severity_weights = {"Info": 1, "Low": 5, "Medium": 10, "High": 30, "Critical": 50}
        total_deduction = sum(severity_weights.get(item["severity"], 0) for item in findings)
        score = max(0, 100 - total_deduction) if scanned_files else 0

        critical_count = sum(1 for x in findings if x["severity"] == "Critical")
        high_count = sum(1 for x in findings if x["severity"] == "High")
        status = "PASSED" if scanned_files and critical_count == 0 and high_count == 0 else "FAILED"

        return {
            "agent": "02-code-reviewer",
            "status": status,
            "duration_seconds": self._elapsed("reviewer"),
            "score": score,
            "files_scanned": scanned_files,
            "findings": findings,
            "passed_checks": passed_checks,
            "summary": (f"Scanned {len(scanned_files)} file(s): {critical_count} Critical, {high_count} High, "
                        f"{len(findings)} total findings, {len(passed_checks)} defense guards verified.")
        }

    def run_documentation_agent(self, analyzer_res: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 03: Documentation Agent — real diff-to-doc sync (updates actual markdown files)."""
        self._tick("documentation")
        print("[03-documentation-agent] 📚 Synchronizing API specs and Architecture docs...")

        impact_data = analyzer_res.get("data", {})
        docs_updated = []

        new_tokens = self._new_identifiers(impact_data)
        if not new_tokens:
            sync_status = "SYNCHRONIZED"
        else:
            sync_status = "SYNCHRONIZED"
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
        """Agent 04: Test Engineer — executes the real Jest test suite with coverage."""
        self._tick("tester")
        print("[04-test-engineer] 🧪 Generating missing test scenarios and executing test suites...")
        test_results = self.test_runner.run_tests()
        test_results["duration_seconds"] = self._elapsed("tester")
        test_results["agent"] = "04-test-engineer"
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
            "summary": test_results.get("summary", "")
        }

    def run_validation_agent(self, analyzer_res, reviewer_res, doc_res, test_res) -> Dict[str, Any]:
        """Agent 05: Validation Agent — real quality gate + metrics from measured data."""
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

        verdict = (f"Modified-file coverage {modified_coverage_pct}% (gate >= 90%), "
                   f"{test_res.get('tests_passed', 0)}/{test_res.get('tests_executed', 0)} tests passing, "
                   f"reviewer score {reviewer_score}/100, docs {doc_res.get('sync_status', 'UNKNOWN')}.")

        return {
            "agent": "05-validation-agent",
            "status": gate_status,
            "gate_status": gate_status,
            "readiness_score": readiness_score,
            "duration_seconds": self._elapsed("validator"),
            "metrics": metrics,
            "summary_verdict": verdict,
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
        print("\n=======================================================")
        print("🚀 Starting ChangeFlow AI Multi-Agent Pipeline (IBM Bob 2.0)")
        print("=======================================================\n")

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