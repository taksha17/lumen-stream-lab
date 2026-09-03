#!/usr/bin/env python3
"""Compare Ollama think flag for LFM / Qwen3."""
from __future__ import annotations

import json
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
PROMPT = "Explain TCP vs UDP in two short sentences."


def try_gen(label: str, model: str, extra: dict) -> None:
    body: dict = {
        "model": model,
        "prompt": PROMPT,
        "stream": False,
        "keep_alive": "5m",
        "options": {"num_predict": 96, "temperature": 0.5},
    }
    body.update(extra)
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate",
        data=data,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        d = json.loads(resp.read().decode())
    ec = int(d.get("eval_count") or 0)
    ed = float(d.get("eval_duration") or 0)
    tok_s = ec / (ed / 1e9) if ed else 0.0
    print(f"=== {label} tok/s={tok_s:.2f} eval={ec}")
    print("thinking:", repr((d.get("thinking") or "")[:120]))
    print("response:", repr((d.get("response") or "")[:400]))
    print()


def main() -> int:
    try_gen("lfm_default", "lfm-balanced", {})
    try_gen("lfm_think_false", "lfm-balanced", {"think": False})
    try_gen("qwen3_default", "qwen3:4b", {})
    try_gen("qwen3_think_false", "qwen3:4b", {"think": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
