#!/usr/bin/env python3
"""Smoke tuned lfm-balanced: general + reason prompts."""
from __future__ import annotations

import json
import urllib.request

OLLAMA = "http://127.0.0.1:11434"


def gen(prompt: str, n: int = 96) -> None:
    body = json.dumps(
        {
            "model": "lfm-balanced",
            "prompt": prompt,
            "stream": False,
            "keep_alive": 0,
            "options": {"num_predict": n, "temperature": 0.5},
        }
    ).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate",
        data=body,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode())
    ec = int(data.get("eval_count") or 0)
    ed = float(data.get("eval_duration") or 0)
    tok_s = ec / (ed / 1e9) if ed else 0.0
    print(f"tok/s={tok_s:.2f} eval={ec}")
    print((data.get("response") or "")[:600])
    print("---")


def main() -> int:
    gen("Explain TCP vs UDP in two short sentences.", 96)
    gen(
        "A store has 47 apples. It sells 19 in the morning and receives 12 more "
        "in the afternoon. How many apples are left? Show brief steps.",
        128,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
