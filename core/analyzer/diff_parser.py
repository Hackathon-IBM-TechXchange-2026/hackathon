#!/usr/bin/env python3
"""
Diff Parser and Impact Analyzer for ChangeFlow.
Parses unified git diffs, extracts modified entities, maps dependencies, and computes blast radius.
"""

import os
import re
import glob
import json
from typing import Dict, List, Any, Optional, Tuple

class DiffParser:
    # Route-like string literal such as "/payments" or "/api/v1/payments/:id"
    ROUTE_LITERAL_RE = re.compile(r"['\"`](/(?:[A-Za-z0-9_\-/:.{}[\]@]+))['\"`]")
    IMPORT_RE = re.compile(r"^\s*import\s+[^'\"]*?from\s+['\"]([^'\"]+)['\"]")
    HANDLER_VERB_RE = re.compile(r"handle(Get|Post|Put|Patch|Delete|Head|Options)")
    DOC_ENDPOINT_PATTERN = re.compile(r"-\s*\*\*Path\*\*:\s*`?([^`\n]+)`?")
    DOC_METHOD_PATTERN = re.compile(r"-\s*\*\*Method\*\*:\s*`?([^`\n]+)`?")

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
        """Analyzes impact against real repository artifacts: import graph, docs, and test files."""
        impacted_components = []
        affected_apis = []
        affected_tests = []
        affected_docs = []

        total_additions = sum(f["additions"] for f in files)
        total_deletions = sum(f["deletions"] for f in files)
        total_changes = total_additions + total_deletions

        changed_paths = [f["new_path"] for f in files]
        changed_abs = [self._abs_path(p) for p in changed_paths]
        for f in files:
            impacted_components.append(f["new_path"])

        dependent_sources = self._find_dependent_sources(changed_abs)
        stems = set()
        for p in list(changed_paths) + list(dependent_sources):
            stem = os.path.splitext(os.path.basename(p))[0].split(".")[0]
            stems.add(stem.lower())

        # 1. Affected APIs: real documented endpoints whose domain matches a changed module
        #    or is referenced by a route literal in changed/dependent source code.
        route_literals = set()
        for src in changed_abs + dependent_sources:
            route_literals.update(self._extract_route_literals(src))

        for method, path in self._parse_documented_endpoints():
            full_path = self._join_doc_endpoint(path)
            hit_reason = self._match_endpoint_to_stem(full_path, stems)
            if hit_reason is None:
                hit_reason = self._match_endpoint_to_route_literal(full_path, route_literals)
            if hit_reason is not None:
                affected_apis.append({
                    "endpoint": full_path,
                    "method": method.upper(),
                    "reason": hit_reason
                })

        # 2. Affected test files: test suites that really import a changed module.
        for test_file in glob.glob(os.path.join(self.workspace_root, "**/*.test.ts"), recursive=True):
            test_abs = os.path.abspath(test_file)
            if self._file_imports_any(test_abs, changed_abs):
                affected_tests.append(os.path.relpath(test_abs, self.workspace_root))

        # 3. Affected documentation: real doc files that mention a changed module / its entities.
        for doc_file in glob.glob(os.path.join(self.workspace_root, "**/docs/**/*.md"), recursive=True):
            name = os.path.basename(doc_file)
            for stem in stems:
                if stem in os.path.basename(name).lower():
                    affected_docs.append(os.path.relpath(doc_file, self.workspace_root))
                    break
            else:
                if self._doc_references_file(doc_file, stems):
                    affected_docs.append(os.path.relpath(doc_file, self.workspace_root))

        # Deduplicate preserving order
        affected_apis = list({(a["method"], a["endpoint"]): a for a in affected_apis}.values())
        affected_tests = list(dict.fromkeys(affected_tests))
        affected_docs = list(dict.fromkeys(affected_docs))

        # Risk level determination (computed from real diff stats)
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

    # --- real repository analysis helpers ------------------------------------

    def _abs_path(self, rel_path: str) -> str:
        return os.path.normpath(os.path.join(self.workspace_root, rel_path))

    def _find_dependent_sources(self, changed_abs: List[str]) -> List[str]:
        """Files under src/ trees that import one of the changed modules (upstream blast radius)."""
        changed_abs = {os.path.normpath(p) for p in changed_abs}
        dependents = []
        for src in glob.glob(os.path.join(self.workspace_root, "**/src/**/*.ts"), recursive=True):
            abs_src = os.path.abspath(src)
            if abs_src in changed_abs:
                continue
            imported = self._resolve_imports(abs_src)
            if imported & changed_abs:
                dependents.append(abs_src)
        return dependents

    def _resolve_imports(self, src_file: str) -> set:
        try:
            with open(src_file, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            return set()
        base_dir = os.path.dirname(src_file)
        resolved = set()
        for match in self.IMPORT_RE.finditer(content):
            spec = match.group(1).strip()
            if not spec.startswith("."):
                continue
            candidate = os.path.normpath(os.path.join(base_dir, spec))
            candidates = [candidate, candidate + ".ts", candidate + ".tsx", candidate + "/index.ts"]
            for cand in candidates:
                if os.path.exists(cand):
                    resolved.add(os.path.abspath(cand))
                    break
        return resolved

    def _file_imports_any(self, abs_file: str, changed_abs) -> bool:
        return bool(self._resolve_imports(abs_file) & set(changed_abs))

    def _extract_route_literals(self, src_file: str) -> set:
        try:
            with open(src_file, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            return set()
        literals = {m.group(1) for m in self.ROUTE_LITERAL_RE.finditer(content)}
        for verb in self.HANDLER_VERB_RE.findall(content):
            verb_literal = "/" + verb.lower()
            literals.add(verb_literal)
        return literals

    def _parse_documented_endpoints(self) -> List[Tuple[str, str]]:
        """Parses real endpoint declarations from repository docs (e.g. API.md)."""
        endpoints = []
        for doc_file in glob.glob(os.path.join(self.workspace_root, "**/docs/API.md"), recursive=True):
            try:
                with open(doc_file, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError:
                continue
            base_url = ""
            current_method = None
            for i, line in enumerate(lines):
                if "Base URL" in line:
                    base_match = re.search(r"`?([/a-zA-Z0-9_\-/:.]+)`?", line)
                    if base_match and "/" in base_match.group(1):
                        base_url = base_match.group(1).strip().rstrip("/")
                    else:
                        for nxt in lines[i + 1:]:
                            nxt = nxt.strip()
                            if nxt:
                                base_url = nxt.strip("`").strip().rstrip("/")
                                break
                mm = self.DOC_METHOD_PATTERN.search(line)
                if mm:
                    current_method = mm.group(1).strip()
                mp = self.DOC_ENDPOINT_PATTERN.search(line)
                if mp:
                    path = mp.group(1).strip().strip("`")
                    if not path.startswith(("http", "/api")):
                        path = base_url + path
                    endpoints.append((current_method or "ANY", path))
        return endpoints

    def _join_doc_endpoint(self, path: str) -> str:
        return path

    def _match_endpoint_to_stem(self, full_path: str, stems: set) -> Optional[str]:
        tokens = [t for t in full_path.split("/") if len(t) > 2]
        for token in tokens:
            domain = token.rstrip("s")
            if domain in stems:
                return f"Changed/dependent component '{domain}' serves endpoint {full_path}"
        return None

    def _match_endpoint_to_route_literal(self, full_path: str, route_literals: set) -> Optional[str]:
        if any(x in route_literals for x in [full_path, "/" + full_path.split("/")[-1]]):
            return f"Route literal for {full_path} referenced by changed/dependent source"
        return None

    def _doc_references_file(self, doc_file: str, stems: set) -> bool:
        try:
            with open(doc_file, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read().lower()
        except OSError:
            return False
        return any(stem in content for stem in stems)

if __name__ == "__main__":
    import sys
    parser = DiffParser()
    default_patch = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../benchmarks/sample-diff.patch"))
    patch_file = sys.argv[1] if len(sys.argv) > 1 else default_patch
    result = parser.parse_patch_file(patch_file)
    print(json.dumps(result, indent=2))

