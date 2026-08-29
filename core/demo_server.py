#!/usr/bin/env python3
"""
ChangeFlow Demo Server (stdlib only).

Serves the real pipeline data to the dashboard:
  GET  /api/latest   -> latest pipeline run (benchmarks/latest-pipeline-run.json)
  POST /api/run      -> executes the ChangeFlow orchestrator and returns fresh results
  GET  /api/diff     -> the target diff text (benchmarks/sample-diff.patch)
  GET  /api/config   -> benchmark assumptions dataset

Run with:  python core/demo_server.py  (default port 8787)
"""

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

LATEST_FILE = os.path.join(ROOT, "benchmarks", "latest-pipeline-run.json")
DIFF_FILE = os.path.join(ROOT, "benchmarks", "sample-diff.patch")
CONFIG_FILE = os.path.join(ROOT, "benchmarks", "benchmark-results.json")


def run_pipeline() -> dict:
    from core.orchestrator import ChangeFlowOrchestrator
    orchestrator = ChangeFlowOrchestrator(ROOT)
    result = orchestrator.execute_pipeline(DIFF_FILE)
    with open(LATEST_FILE, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    return result


def read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


class ChangeFlowHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        if self.path.startswith("/api/latest"):
            self._send(200, read_json(LATEST_FILE))
        elif self.path.startswith("/api/diff"):
            try:
                with open(DIFF_FILE, "r", encoding="utf-8") as fh:
                    diff = fh.read()
                self._send(200, {"diff": diff, "path": "benchmarks/sample-diff.patch"})
            except OSError:
                self._send(404, {"error": "diff file not found"})
        elif self.path.startswith("/api/config"):
            self._send(200, read_json(CONFIG_FILE))
        else:
            self._send(404, {"error": "not found", "hint": "GET /api/latest, /api/diff, /api/config | POST /api/run"})

    def do_POST(self):
        if self.path.startswith("/api/run"):
            started = time.time()
            try:
                result = run_pipeline()
                result["server_execution_time"] = round(time.time() - started, 3)
                self._send(200, result)
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        else:
            self._send(404, {"error": "not found"})


def main() -> None:
    port = int(os.environ.get("CHANGEFLOW_PORT", "8787"))
    server = ThreadingHTTPServer(("127.0.0.1", port), ChangeFlowHandler)
    print(f"ChangeFlow Demo Server running on http://localhost:{port}")
    print("  GET  /api/latest  |  POST /api/run  |  GET  /api/diff  |  GET  /api/config")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()