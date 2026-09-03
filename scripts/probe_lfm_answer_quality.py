#!/usr/bin/env python3
"""Probe LFM answer quality: num_predict, visible_response, optional think-closed alias.

Usage (lab):
  python scripts/probe_lfm_answer_quality.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lumen_router import ollama_generate_payload, visible_response  # noqa: E402

OLLAMA = "http://127.0.0.1:11434"
PROMPTS = [
    ("tcp", "Explain TCP vs UDP in two short sentences.", 96),
    ("tcp_long", "Explain TCP vs UDP in two short sentences.", 192),
    ("apples", "A store has 47 apples. It sells 19 then gets 12. How many left? Brief steps.", 128),
    ("apples_long", "A store has 47 apples. It sells 19 then gets 12. How many left? Brief steps.", 256),
]


def api(method: str, path: str, payload: dict | None = None, timeout: int = 300) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urlrequest.Request(
        f"{OLLAMA}{path}",
        data=data,
        method=method,
        headers={"content-type": "application/json"} if data else {},
    )
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def one(model: str, prompt: str, npred: int) -> dict:
    payload = ollama_generate_payload(
        model,
        prompt,
        stream=False,
        options={"num_predict": npred, "temperature": 0.5},
        keep_alive="5m",
        think=False,
    )
    t0 = time.perf_counter()
    data = api("POST", "/api/generate", payload)
    wall = time.perf_counter() - t0
    raw = data.get("response") or ""
    vis = visible_response(data)
    ec = int(data.get("eval_count") or 0)
    ed = float(data.get("eval_duration") or 0)
    tok_s = ec / (ed / 1e9) if ed else 0.0
    return {
        "model": model,
        "num_predict": npred,
        "tok_s": round(tok_s, 2),
        "wall_s": round(wall, 3),
        "eval_count": ec,
        "raw_preview": raw[:220].replace("\n", " "),
        "visible_preview": vis[:220].replace("\n", " "),
        "visible_better": len(vis) > 0 and not vis.lower().startswith("the user wants"),
    }


def main() -> int:
    try:
        api("GET", "/api/tags", timeout=5)
    except URLError as exc:
        print(f"Ollama down: {exc}")
        return 1

    models = ["lfm-balanced"]
    tags = {m.get("name", "") for m in api("GET", "/api/tags").get("models", [])}
    if any(n.startswith("lfm-balanced-direct") for n in tags):
        models.append("lfm-balanced-direct")

    rows = []
    print("=== LFM answer quality probe ===\n")
    for model in models:
        for name, prompt, npred in PROMPTS:
            row = one(model, prompt, npred)
            row["case"] = name
            rows.append(row)
            flag = "OK" if row["visible_better"] else "META"
            print(
                f"[{flag}] {model} {name} n={npred} tok/s={row['tok_s']} "
                f"vis={row['visible_preview'][:100]!r}"
            )

    out = {"runs": rows}
    path = ROOT / "results" / "lfm-answer-quality-last.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
