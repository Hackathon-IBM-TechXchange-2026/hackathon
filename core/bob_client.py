"""
Bob AI Client (IBM watsonx.ai wrapper)
=======================================

Thin integration layer that routes completions through IBM watsonx.ai.
All other ChangeFlow agents call this single module so the AI integration
point is centralised.

Environment variables required:
    IBM_CLOUD_API_KEY   — IBM Cloud IAM API key
    WATSONX_PROJECT_ID  — watsonx.ai project ID (from project settings)
    WATSONX_URL         — base URL (default: https://us-south.ml.cloud.ibm.com)
    WATSONX_MODEL_ID    — model to use (default: ibm/granite-13b-instruct-v2)
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
import urllib.request
import urllib.error
from typing import Any

# ---------------------------------------------------------------------------
# Typed exception hierarchy
# ---------------------------------------------------------------------------


class BobClientError(Exception):
    """Base error for all Bob AI client failures."""

    def __init__(self, message: str, trace_id: str | None = None, cause: Exception | None = None) -> None:
        self.message = message
        self.trace_id = trace_id or str(uuid.uuid4())
        self.cause = cause
        super().__init__(message)

    def to_dict(self) -> dict[str, str]:
        return {"error": self.message, "traceId": self.trace_id}


class BobAuthError(BobClientError):
    """Raised when IBM IAM token acquisition fails."""


class BobTimeoutError(BobClientError):
    """Raised when the watsonx.ai API does not respond in time."""


class BobResponseError(BobClientError):
    """Raised when the API returns an unexpected / unparseable response."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_URL = "https://us-south.ml.cloud.ibm.com"
_DEFAULT_MODEL = "ibm/granite-3-3-8b-instruct"
_IAM_URL = "https://iam.cloud.ibm.com/identity/token"
_TOKEN_BUFFER_SECS = 60          # Refresh IAM token this many seconds before expiry
_DEFAULT_TIMEOUT = 60            # seconds for each HTTP call


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


# ---------------------------------------------------------------------------
# IAM token cache (process-level singleton)
# ---------------------------------------------------------------------------

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


def _get_iam_token() -> str:
    """Returns a valid IBM IAM bearer token, fetching a new one if needed."""
    api_key = _env("IBM_CLOUD_API_KEY")
    if not api_key:
        raise BobAuthError(
            "IBM_CLOUD_API_KEY environment variable is not set. "
            "Copy .env.example to .env and populate your credentials."
        )

    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - _TOKEN_BUFFER_SECS:
        return _token_cache["token"]  # type: ignore[return-value]

    payload = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={urllib.parse.quote(api_key)}"  # noqa: E501
    req = urllib.request.Request(
        _IAM_URL,
        data=payload.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise BobAuthError(f"IAM token request failed (HTTP {exc.code}): {exc.reason}", cause=exc) from exc
    except OSError as exc:
        raise BobAuthError(f"IAM token network error: {exc}", cause=exc) from exc

    token: str = data.get("access_token", "")
    expires_in: float = float(data.get("expires_in", 3600))
    if not token:
        raise BobAuthError("IAM response did not contain an access_token.")

    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expires_in
    return token


# ---------------------------------------------------------------------------
# Core completion call
# ---------------------------------------------------------------------------

import urllib.parse  # noqa: E402 — placed after _IAM_URL uses urllib.parse


def complete(system_prompt: str, user_prompt: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """
    Calls IBM watsonx.ai text generation and returns the raw text response.

    Raises BobClientError (or a subclass) on any failure — never silently
    swallows exceptions per coding-standards.md.
    """
    trace_id = str(uuid.uuid4())
    base_url = _env("WATSONX_URL", _DEFAULT_URL).rstrip("/")
    model_id = _env("WATSONX_MODEL_ID", _DEFAULT_MODEL)
    project_id = _env("WATSONX_PROJECT_ID")
    if not project_id:
        raise BobClientError(
            "WATSONX_PROJECT_ID environment variable is not set.",
            trace_id=trace_id,
        )

    token = _get_iam_token()

    full_prompt = f"{system_prompt}\n\n{user_prompt}" if system_prompt else user_prompt
    body = {
        "model_id": model_id,
        "input": full_prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": 2048,
            "min_new_tokens": 1,
            "stop_sequences": [],
            "temperature": 0.1,
        },
        "project_id": project_id,
    }
    url = f"{base_url}/ml/v1/text/generation?version=2023-05-29"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_snippet = exc.read(512).decode(errors="replace") if exc.fp else ""
        raise BobResponseError(
            f"watsonx.ai API error (HTTP {exc.code}): {body_snippet}",
            trace_id=trace_id, cause=exc,
        ) from exc
    except TimeoutError as exc:
        raise BobTimeoutError(
            f"watsonx.ai did not respond within {timeout}s.",
            trace_id=trace_id, cause=exc,
        ) from exc
    except OSError as exc:
        raise BobResponseError(
            f"Network error reaching watsonx.ai: {exc}",
            trace_id=trace_id, cause=exc,
        ) from exc

    results = data.get("results", [])
    if not results:
        raise BobResponseError(
            f"watsonx.ai returned no results. Full response: {json.dumps(data)[:512]}",
            trace_id=trace_id,
        )
    generated_text: str = results[0].get("generated_text", "")
    return generated_text


def complete_json(system_prompt: str, user_prompt: str, schema_hint: str = "") -> dict[str, Any]:
    """
    Calls complete() and parses the first ```json ... ``` fenced block from the reply.
    Falls back to parsing the entire response as JSON if no fence is present.

    Returns a parsed Python dict whose keys should match the agent output schema.
    On any parse failure, raises BobResponseError with the raw text attached.
    """
    full_system = system_prompt
    if schema_hint:
        full_system = f"{system_prompt}\n\nReturn ONLY valid JSON matching this schema:\n{schema_hint}"

    raw = complete(full_system, user_prompt)

    # Extract first ```json ... ``` fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?})\s*```", raw, re.DOTALL)
    candidate = fence_match.group(1) if fence_match else raw.strip()

    try:
        return json.loads(candidate)
    except ValueError:
        # Try to find any top-level JSON object in the text
        brace_match = re.search(r"\{.*}", candidate, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except ValueError:
                pass
        raise BobResponseError(
            f"Could not parse JSON from watsonx.ai response. Raw text (first 512 chars): {raw[:512]}",
        ) from None


# ---------------------------------------------------------------------------
# Smoke-test __main__
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys  # noqa: F811

    # Load .env if present
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

    print("=== Bob AI Client Smoke Test ===")
    print(f"Model: {_env('WATSONX_MODEL_ID', _DEFAULT_MODEL)}")
    print(f"URL:   {_env('WATSONX_URL', _DEFAULT_URL)}\n")

    try:
        text = complete(
            "You are a helpful assistant. Reply concisely.",
            "Say 'Hello from watsonx' and nothing else.",
        )
        print(f"[complete()] → {text!r}\n")
    except BobClientError as exc:
        print(f"[complete() FAILED] {exc.to_dict()}", file=sys.stderr)
        sys.exit(1)

    try:
        result = complete_json(
            "You are a JSON-only responder.",
            'Return {"status": "ok", "message": "watsonx connected"}',
        )
        print(f"[complete_json()] → {result}\n")
    except BobClientError as exc:
        print(f"[complete_json() FAILED] {exc.to_dict()}", file=sys.stderr)
        sys.exit(1)

    print("Smoke test PASSED ✓")
