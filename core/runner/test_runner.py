#!/usr/bin/env python3
"""
Test Runner for ChangeFlow.
Executes test suites in sample-app, captures real test results, execution timing,
and coverage statistics computed from the Jest coverage map.
"""

import os
import subprocess
import time
import json
from typing import Dict, Any, Optional

class TestRunner:
    def __init__(self, workspace_root: Optional[str] = None, app_dir: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        # app_dir can be an absolute path or a path relative to workspace_root
        if app_dir:
            self.sample_app_dir = app_dir if os.path.isabs(app_dir) else os.path.join(self.workspace_root, app_dir)
        else:
            self.sample_app_dir = os.path.join(self.workspace_root, "sample-app")

    def run_tests(self) -> Dict[str, Any]:
        """Executes Jest tests with coverage in the app directory and parses the real output."""
        start_time = time.time()

        has_node_modules = os.path.exists(os.path.join(self.sample_app_dir, "node_modules"))
        if not has_node_modules:
            return self._failure(f"node_modules not installed. Run `npm install` inside {self.sample_app_dir}.")

        try:
            cmd = ["npx", "jest", "--coverage", "--json", "--colors=false"]
            process = subprocess.run(
                cmd,
                cwd=self.sample_app_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120
            )
        except Exception as exc:
            return self._failure(f"Failed to run jest: {exc}")

        elapsed = round(time.time() - start_time, 2)

        try:
            jest_data = json.loads(process.stdout or "{}")
        except ValueError:
            return self._failure("jest did not return parseable JSON output.")

        num_total = int(jest_data.get("numTotalTests", 0))
        num_passed = int(jest_data.get("numPassedTests", 0))
        num_failed = int(jest_data.get("numFailedTests", 0))
        num_failed_suites = int(jest_data.get("numFailedTestSuites", 0))

        test_suites = []
        for suite in jest_data.get("testResults", []):
            rel_name = os.path.relpath(suite.get("name", ""), self.workspace_root)
            assertions = suite.get("assertionResults", [])
            passed_in_suite = sum(1 for a in assertions if a.get("status") == "passed")
            failed_in_suite = sum(1 for a in assertions if a.get("status") == "failed")
            if not assertions:
                passed_in_suite = suite.get("numPassingTests", 0)
                failed_in_suite = suite.get("numFailingTests", 0)
            test_suites.append({
                "suite": rel_name,
                "status": "PASSED" if suite.get("status") == "passed" else "FAILED",
                "passed": passed_in_suite,
                "failed": failed_in_suite,
                "duration_ms": suite.get("endTime", 0) - suite.get("startTime", 0)
            })

        coverage = self._compute_coverage(jest_data.get("coverageMap") or {})
        total_statements = coverage["total"]["statements"]["total"]
        covered_statements = coverage["total"]["statements"]["covered"]
        coverage_percentage = round((covered_statements / total_statements) * 100, 1) if total_statements else 0.0

        overall_status = "PASSED" if num_failed == 0 and num_failed_suites == 0 else "FAILED"

        return {
            "status": overall_status,
            "tests_executed": num_total,
            "tests_passed": num_passed,
            "tests_failed": num_failed,
            "coverage_percentage": coverage_percentage,
            "coverage": coverage,
            "execution_time_seconds": elapsed,
            "test_suites": test_suites,
            "summary": (f"{num_passed}/{num_total} tests passing over {len(test_suites)} suites, "
                        f"{coverage_percentage}% statement coverage.")
        }

    def _compute_coverage(self, coverage_map: Dict[str, Any]) -> Dict[str, Any]:
        """Computes real statement/function/branch coverage from a Jest coverage map."""
        totals = {"statements": {"covered": 0, "total": 0},
                  "functions": {"covered": 0, "total": 0},
                  "branches": {"covered": 0, "total": 0}}
        files = {}

        for path, fc in coverage_map.items():
            if not isinstance(fc, dict):
                continue
            if "s" not in fc and isinstance(fc, dict) and "data" in fc:
                fc = fc["data"].get(path, {})

            s = fc.get("s", {}) or {}
            statements_covered = sum(1 for v in s.values() if int(v) > 0)
            statements_total = len(s)

            f_map = fc.get("f", {}) or {}
            functions_covered = sum(1 for v in f_map.values() if int(v) > 0)
            functions_total = len(f_map)

            b_map = fc.get("b", {}) or {}
            branches_covered = 0
            branches_total = 0
            for alternatives in b_map.values():
                if alternatives:
                    branches_total += len(alternatives)
                    if any(int(v) > 0 for v in alternatives):
                        branches_covered += 1

            files[os.path.relpath(path, self.workspace_root)] = {
                "statements_percentage": round((statements_covered / statements_total) * 100, 1) if statements_total else 0.0,
                "functions_percentage": round((functions_covered / functions_total) * 100, 1) if functions_total else 0.0,
                "branches_percentage": round((branches_covered / branches_total) * 100, 1) if branches_total else 0.0,
                "statements": f"{statements_covered}/{statements_total}",
                "functions": f"{functions_covered}/{functions_total}",
                "branches": f"{branches_covered}/{branches_total}"
            }

            totals["statements"]["covered"] += statements_covered
            totals["statements"]["total"] += statements_total
            totals["functions"]["covered"] += functions_covered
            totals["functions"]["total"] += functions_total
            totals["branches"]["covered"] += branches_covered
            totals["branches"]["total"] += branches_total

        return {
            "overall": {
                key: round((val["covered"] / val["total"]) * 100, 1) if val["total"] else 0.0
                for key, val in totals.items()
            },
            "total": totals,
            "files": files
        }

    def _failure(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "FAILED",
            "tests_executed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "coverage_percentage": 0.0,
            "coverage": {"overall": {"statements": 0.0, "functions": 0.0, "branches": 0.0}, "total": {}, "files": {}},
            "execution_time_seconds": 0.0,
            "test_suites": [],
            "error": reason,
            "summary": f"Test execution failed: {reason}"
        }

if __name__ == "__main__":
    runner = TestRunner()
    result = runner.run_tests()
    print(json.dumps(result, indent=2))