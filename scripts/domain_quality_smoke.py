#!/usr/bin/env python3
"""Compare domain model vs stock 3B using production ollama_generate_payload."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lumen_router import ollama_generate_payload, route_decision  # noqa: E402

PROMPT = "What is Lumen Stream Lab?"
MODELS = ["qwen2.5-3b-lumen", "qwen2.5:3b-instruct-q4_K_M"]


def main() -> int:
    print("ROUTE", json.dumps(route_decision(PROMPT), indent=2))
    print()
    for model in MODELS:
        payload = ollama_generate_payload(
            model,
            PROMPT,
            stream=False,
            options={"num_predict": 128, "temperature": 0.2},
        )
        payload["keep_alive"] = "5m"
        body = json.dumps(payload).encode()
        req = urlrequest.Request(
            "http://127.0.0.1:11434/api/generate",
            data=body,
            headers={"content-type": "application/json"},
        )
        t0 = time.perf_counter()
        with urlrequest.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode())
        wall = time.perf_counter() - t0
        print(f"=== {model} wall={wall:.2f}s ===")
        print((data.get("response") or "")[:600])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
