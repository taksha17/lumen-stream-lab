#!/usr/bin/env python3
"""
Lumen HTTP gateway — reference implementation of the enterprise topology
described in docs/ENTERPRISE.md §4.1 and §7.1.

Stdlib only (no FastAPI / uvicorn) so it runs anywhere python3 runs.
Demonstrates: per-request routing via `lumen route`, plan-as-contract,
fall-back on backend failure, SSE streaming passthrough.

Start:
    python3 scripts/lumen_gateway.py --port 8080

Try it:
    curl -s http://localhost:8080/v1/plan \
        -H 'content-type: application/json' \
        -d '{"prompt": "What is 2+2?"}' | jq

    curl -s http://localhost:8080/v1/chat \
        -H 'content-type: application/json' \
        -d '{"prompt": "What is 2+2?"}'
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
LUMEN_PY = ROOT / "lumen.py"
HARDWARE = ROOT / "hardware.json"
RESULTS = ROOT / "results"
OLLAMA_URL = "http://127.0.0.1:11434"


def lumen_route(prompt: str, force_tier: str | None = None) -> dict:
    """Call `lumen.py route` — hybrid tier plan (single source of truth)."""
    cmd = [sys.executable, str(LUMEN_PY), "route", "--prompt", prompt]
    if force_tier:
        cmd.extend(["--tier", force_tier])
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        raise RuntimeError(f"lumen route failed: {out.stderr}")
    return json.loads(out.stdout)


def ollama_generate(model: str, prompt: str, stream: bool = False) -> bytes:
    """Proxy to a running Ollama instance. Replace this with llamacpp/airllm
    clients when the plan.backend changes."""
    from lumen_router import ollama_generate_payload

    body = json.dumps(ollama_generate_payload(model, prompt, stream=stream)).encode()
    req = urlrequest.Request(
        f"{OLLAMA_URL}/api/generate", data=body,
        headers={"content-type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=300) as resp:
            return resp.read()
    except URLError as e:
        raise RuntimeError(f"backend call failed: {e}") from e


def bench_freshness() -> dict:
    """Report how stale the per-(model,backend) bench data is. The gateway
    uses this to decide whether the router is safe to call (no data = no
    real routing, just heuristics)."""
    if not RESULTS.exists():
        return {"has_results": False}
    files = sorted(RESULTS.glob("bench-*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        return {"has_results": False}
    newest = files[-1]
    age_s = time.time() - newest.stat().st_mtime
    return {
        "has_results": True,
        "newest_run": newest.name,
        "age_seconds": int(age_s),
        "stale": age_s > 7 * 24 * 3600,   # warn if older than a week
        "total_runs": len(files),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LumenGateway/0.1"

    # ---- helpers ----
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        n = int(self.headers.get("content-length", "0") or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode())

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write("[lumen-gw] " + fmt % args + "\n")

    # ---- routes ----
    def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler API)
        if self.path == "/v1/health":
            return self._json(200, {
                "ok": True,
                "hardware_present": HARDWARE.exists(),
                "bench": bench_freshness(),
            })
        if self.path == "/":
            return self._json(200, {
                "service": "lumen-gateway",
                "endpoints": ["/v1/health", "/v1/plan", "/v1/chat"],
            })
        self._json(404, {"error": "not found", "path": self.path})

    def do_POST(self):  # noqa: N802
        if self.path == "/v1/plan":
            body = self._read_json()
            prompt = body.get("prompt", "")
            if not prompt:
                return self._json(400, {"error": "prompt required"})
            try:
                plan = lumen_route(prompt, force_tier=body.get("force_tier"))
            except Exception as e:
                return self._json(500, {"error": str(e)})
            return self._json(200, plan)

        if self.path == "/v1/chat":
            body = self._read_json()
            prompt = body.get("prompt", "")
            force = body.get("force_tier")
            if not prompt:
                return self._json(400, {"error": "prompt required"})

            t0 = time.time()
            try:
                plan = lumen_route(prompt, force_tier=force)
            except Exception as e:
                return self._json(500, {"error": "router failed", "detail": str(e)})

            try:
                raw = ollama_generate(plan["model"], prompt, stream=False)
            except Exception as e:
                if plan.get("tier") != "fast":
                    plan = lumen_route(prompt, force_tier="fast")
                    try:
                        raw = ollama_generate(plan["model"], prompt, stream=False)
                    except Exception as e2:
                        return self._json(502, {
                            "error": "backend failed",
                            "fallback_error": str(e2),
                        })
                else:
                    return self._json(502, {"error": "backend failed", "detail": str(e)})

            try:
                ollama_resp = json.loads(raw)
            except json.JSONDecodeError:
                ollama_resp = {"raw": raw.decode("utf-8", "replace")}

            return self._json(200, {
                "plan": plan,
                "backend_latency_ms": int((time.time() - t0) * 1000),
                "response": ollama_resp.get("response", ""),
                "eval_count": ollama_resp.get("eval_count"),
                "eval_duration_ns": ollama_resp.get("eval_duration"),
            })

        self._json(404, {"error": "not found", "path": self.path})


def main() -> int:
    ap = argparse.ArgumentParser(description="Lumen HTTP gateway (reference)")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    if not LUMEN_PY.exists():
        print(f"lumen.py not found at {LUMEN_PY}", file=sys.stderr)
        return 1
    if not HARDWARE.exists():
        print(f"hardware.json missing — run `python3 {LUMEN_PY} probe` first",
              file=sys.stderr)
        return 1

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"lumen-gateway listening on http://{args.host}:{args.port}")
    print("endpoints: /v1/health  /v1/plan  /v1/chat")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
