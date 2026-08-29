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
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

LATEST_FILE = os.path.join(ROOT, "benchmarks", "latest-pipeline-run.json")
DIFF_FILE = os.path.join(ROOT, "benchmarks", "sample-diff.patch")
CONFIG_FILE = os.path.join(ROOT, "benchmarks", "benchmark-results.json")

DEFAULT_PORT = 8787


def run_pipeline() -> dict:
    from core.orchestrator import ChangeFlowOrchestrator
    orchestrator = ChangeFlowOrchestrator(ROOT)
    result = orchestrator.execute_pipeline(DIFF_FILE)
    _atomic_write_json(LATEST_FILE, result)
    return result


def _atomic_write_json(path: str, payload: dict) -> None:
    """Escreve em um arquivo temporário e faz rename atômico.

    Evita que um GET concorrente (o servidor é multi-thread) leia um
    arquivo parcialmente escrito enquanto um POST /api/run está em
    andamento — ver bug #4 do review.
    """
    directory = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_path, path)  # atômico no mesmo filesystem (POSIX e Windows)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def read_json(path: str) -> tuple[int, dict]:
    """Retorna (status_http, payload).

    - 404 se o arquivo não existe (ex.: pipeline ainda não rodou).
    - 200 com o conteúdo se existe e é JSON válido.
    - 500 se existe mas está corrompido/ilegível.

    Antes, /api/latest e /api/config devolviam 200 {} silenciosamente
    quando o arquivo não existia, enquanto /api/diff devolvia 404 no
    mesmo cenário — comportamento inconsistente (bug #3 do review).
    """
    if not os.path.exists(path):
        return 404, {"error": "not found", "path": os.path.relpath(path, ROOT)}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return 200, json.load(fh)
    except ValueError:
        return 500, {"error": "invalid JSON on disk", "path": os.path.relpath(path, ROOT)}


class ChangeFlowHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload=None) -> None:
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        # Reflete os headers pedidos no preflight em vez de fixar só
        # "Content-Type" — evita falha de CORS se o front mandar outro
        # header custom no futuro.
        requested_headers = self.headers.get("Access-Control-Request-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Headers", requested_headers)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _path(self) -> str:
        """Path sem query string e sem barra final, para comparação exata."""
        return urlsplit(self.path).path.rstrip("/") or "/"

    def do_OPTIONS(self):
        # 204 No Content não pode ter corpo (RFC 7231 §6.3.5) — antes o
        # servidor mandava Content-Length: 2 e o corpo "{}" (bug #1).
        self._send(204, None)

    def do_GET(self):
        path = self._path()
        if path == "/api/latest":
            status, payload = read_json(LATEST_FILE)
            self._send(status, payload)
        elif path == "/api/diff":
            if not os.path.exists(DIFF_FILE):
                self._send(404, {"error": "diff file not found", "path": "benchmarks/sample-diff.patch"})
                return
            try:
                with open(DIFF_FILE, "r", encoding="utf-8") as fh:
                    diff = fh.read()
                self._send(200, {"diff": diff, "path": "benchmarks/sample-diff.patch"})
            except OSError as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/config":
            status, payload = read_json(CONFIG_FILE)
            self._send(status, payload)
        else:
            self._send(404, {"error": "not found", "hint": "GET /api/latest, /api/diff, /api/config | POST /api/run"})

    def do_POST(self):
        path = self._path()
        if path == "/api/run":
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
    # Antes: int(os.environ.get(...)) sem tratamento — CHANGEFLOW_PORT=abc
    # derrubava o processo com um traceback cru (bug #5).
    raw_port = os.environ.get("CHANGEFLOW_PORT", str(DEFAULT_PORT))
    try:
        port = int(raw_port)
    except ValueError:
        print(f"CHANGEFLOW_PORT inválido ('{raw_port}') — usando a porta padrão {DEFAULT_PORT}.")
        port = DEFAULT_PORT

    server = ThreadingHTTPServer(("127.0.0.1", port), ChangeFlowHandler)
    print(f"ChangeFlow Demo Server running on http://localhost:{port}")
    print("  GET  /api/latest  |  POST /api/run  |  GET  /api/diff  |  GET  /api/config")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()