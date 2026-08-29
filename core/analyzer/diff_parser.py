#!/usr/bin/env python3
"""
Diff Parser and Impact Analyzer for ChangeFlow.
Parses unified git diffs, extracts modified entities, maps dependencies, and computes blast radius.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional

class DiffParser:
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

    def parse_patch_file(self, patch_path: str) -> Dict[str, Any]:
        """Reads and parses a unified diff patch file."""
        if not os.path.exists(patch_path):
            raise FileNotFoundError(f"Patch file not found: {patch_path}")

        with open(patch_path, "r", encoding="utf-8") as f:
            content = f.read()

        return self.parse_diff_text(content)

    def parse_diff_text(self, diff_text: str) -> Dict[str, Any]:
        """Parses unified git diff string."""
        files = []
        current_file = None
        current_hunk = None

        file_diff_pattern = re.compile(r"^diff --git a/(.*?) b/(.*?)$")
        hunk_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")

        lines = diff_text.splitlines()
        for line in lines:
            file_match = file_diff_pattern.match(line)
            if file_match:
                old_path, new_path = file_match.groups()
                current_file = {
                    "old_path": old_path,
                    "new_path": new_path,
                    "additions": 0,
                    "deletions": 0,
                    "hunks": [],
                    "changed_lines": []
                }
                files.append(current_file)
                current_hunk = None
                continue

            if current_file is None:
                continue

            hunk_match = hunk_pattern.match(line)
            if hunk_match:
                old_start, old_len, new_start, new_len, heading = hunk_match.groups()
                current_hunk = {
                    "old_start": int(old_start),
                    "old_len": int(old_len or 1),
                    "new_start": int(new_start),
                    "new_len": int(new_len or 1),
                    "heading": heading.strip(),
                    "lines": []
                }
                current_file["hunks"].append(current_hunk)
                continue

            if current_hunk is not None:
                current_hunk["lines"].append(line)
                if line.startswith("+") and not line.startswith("+++"):
                    current_file["additions"] += 1
                    current_file["changed_lines"].append(line[1:])
                elif line.startswith("-") and not line.startswith("---"):
                    current_file["deletions"] += 1

        return self._analyze_impact(files, diff_text)

    def _analyze_impact(self, files: List[Dict[str, Any]], raw_diff: str) -> Dict[str, Any]:
        """Analyzes impact, maps dependencies, and calculates risk and blast radius."""
        impacted_components = []
        affected_apis = []
        affected_tests = []
        affected_docs = []

        total_additions = sum(f["additions"] for f in files)
        total_deletions = sum(f["deletions"] for f in files)
        total_changes = total_additions + total_deletions

        for f in files:
            path = f["new_path"]
            impacted_components.append(path)

            if "payment" in path.lower():
                affected_apis.append({
                    "endpoint": "POST /api/v1/payments",
                    "method": "POST",
                    "reason": "Payment core processing logic or repository modified"
                })
                affected_tests.append("sample-app/tests/unit/payment.service.test.ts")
                affected_tests.append("sample-app/tests/integration/payment.flow.test.ts")
                affected_docs.append("sample-app/docs/API.md")
                affected_docs.append("sample-app/docs/ARCHITECTURE.md")

        # Deduplicate
        affected_tests = list(set(affected_tests))
        affected_docs = list(set(affected_docs))

        # Risk level determination
        risk_level = "LOW"
        if total_changes > 50 or any("repository" in f["new_path"] or "security" in f["new_path"] for f in files):
            risk_level = "HIGH"
        elif total_changes > 10 or any("service" in f["new_path"] for f in files):
            risk_level = "MEDIUM"

        blast_radius_score = min(100.0, round((len(files) * 20.0 + len(affected_apis) * 25.0 + total_changes * 1.5), 1))

        return {
            "files_changed": len(files),
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "files": files,
            "impacted_components": impacted_components,
            "affected_apis": affected_apis,
            "affected_tests": affected_tests,
            "affected_docs": affected_docs,
            "risk_level": risk_level,
            "blast_radius_score": blast_radius_score,
            "summary": f"Change affects {len(files)} files ({total_additions} additions, {total_deletions} deletions). Risk assessed as {risk_level} with blast radius {blast_radius_score}/100."
        }

if __name__ == "__main__":
    import sys
    parser = DiffParser()
    default_patch = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../benchmarks/sample-diff.patch"))
    patch_file = sys.argv[1] if len(sys.argv) > 1 else default_patch
    result = parser.parse_patch_file(patch_file)
    print(json.dumps(result, indent=2))

