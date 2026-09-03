#!/usr/bin/env python3
"""Measure wall / load cost when chat jumps across hybrid tiers.

Compares keep_alive=0 (unload every generate) vs keep_alive=10m (default).

Usage:
  python3 scripts/bench_tier_thrash.py
  python3 scripts/bench_tier_thrash.py --keep-alive 10m

Writes results/tier-thrash-last.json (gitignored).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lumen_router import MODELS, ollama_generate_payload  # noqa: E402

OLLAMA = "http://127.0.0.1:11434"

# Cross-tier chat pattern: fast → LFM → domain → fast (common hybrid thrash).
CROSS_STEPS = [
    ("fast", MODELS["fast"], "What is 2+2? One short sentence.", 32),
    ("balanced", MODELS["balanced"], "Explain TCP vs UDP in two short sentences.", 64),
    (
        "domain",
        MODELS["balanced_domain"],
        "What is Lumen Stream Lab? Answer in two short sentences.",
        64,
    ),
    ("fast", MODELS["fast"], "Capital of France? One word.", 16),
]

# Same-tier streak: keep_alive should win hard here.
STREAK_STEPS = [
    ("balanced", MODELS["balanced"], "Name one benefit of UDP. One sentence.", 48),
    ("balanced", MODELS["balanced"], "Name one benefit of TCP. One sentence.", 48),
    ("balanced", MODELS["balanced"], "Name one downside of UDP. One sentence.", 48),
]


def api_json(method: str, path: str, payload: dict | None = None, timeout: int = 600) -> dict:
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


def ns_to_s(ns: int | float | None) -> float:
    if not ns:
        return 0.0
    return float(ns) / 1e9


def one_generate(
    model: str,
    prompt: str,
    num_predict: int,
    keep_alive: str | int,
) -> dict:
    payload = ollama_generate_payload(
        model,
        prompt,
        stream=False,
        options={"num_predict": num_predict, "temperature": 0.2},
        keep_alive=keep_alive,
    )
    t0 = time.perf_counter()
    data = api_json("POST", "/api/generate", payload, timeout=300)
    wall = time.perf_counter() - t0
    eval_count = int(data.get("eval_count") or 0)
    eval_dur = ns_to_s(data.get("eval_duration"))
    load_s = ns_to_s(data.get("load_duration"))
    tok_s = (eval_count / eval_dur) if eval_dur > 0 else 0.0
    return {
        "model": model,
        "wall_s": round(wall, 3),
        "load_s": round(load_s, 3),
        "eval_s": round(eval_dur, 3),
        "eval_count": eval_count,
        "tok_s": round(tok_s, 2),
        "keep_alive": keep_alive,
    }


def run_sequence(name: str, steps: list, keep_alive: str | int) -> dict:
    rows = []
    for tier, model, prompt, npred in steps:
        row = one_generate(model, prompt, npred, keep_alive)
        row["tier"] = tier
        rows.append(row)
        print(
            f"  [{name} ka={keep_alive}] {tier}/{model}: "
            f"wall={row['wall_s']:.2f}s load={row['load_s']:.2f}s "
            f"tok/s={row['tok_s']:.1f}"
        )
    return {
        "name": name,
        "keep_alive": keep_alive,
        "total_wall_s": round(sum(r["wall_s"] for r in rows), 3),
        "total_load_s": round(sum(r["load_s"] for r in rows), 3),
        "steps": rows,
    }


def unload_all() -> None:
    """Force unload by generate keep_alive=0 on known hybrid models."""
    for model in {
        MODELS["fast"],
        MODELS["balanced"],
        MODELS["balanced_domain"],
    }:
        try:
            api_json(
                "POST",
                "/api/generate",
                {
                    "model": model,
                    "prompt": "x",
                    "stream": False,
                    "keep_alive": 0,
                    "options": {"num_predict": 1},
                },
                timeout=120,
            )
        except URLError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--keep-alive",
        default="10m",
        help="Resident keep_alive for the 'on' arm (default 10m)",
    )
    args = ap.parse_args()

    try:
        api_json("GET", "/api/tags", timeout=5)
    except URLError as exc:
        print(f"Ollama not reachable: {exc}", file=sys.stderr)
        return 1

    # Avoid LUMEN_KEEP_ALIVE env leaking into explicit keep_alive=0 arms.
    os.environ.pop("LUMEN_KEEP_ALIVE", None)

    print("=== Tier thrash bench ===")
    print("Unloading models before each arm...\n")

    results = []
    for arm_name, ka in (("unload_each", 0), ("keep_alive", args.keep_alive)):
        unload_all()
        time.sleep(2)
        print(f"-- arm: {arm_name} (keep_alive={ka})")
        cross = run_sequence("cross_tier", CROSS_STEPS, ka)
        streak = run_sequence("same_tier_streak", STREAK_STEPS, ka)
        results.append({"arm": arm_name, "cross": cross, "streak": streak})
        print(
            f"  totals: cross wall={cross['total_wall_s']:.2f}s "
            f"load={cross['total_load_s']:.2f}s | "
            f"streak wall={streak['total_wall_s']:.2f}s "
            f"load={streak['total_load_s']:.2f}s\n"
        )

    unload = next(r for r in results if r["arm"] == "unload_each")
    keep = next(r for r in results if r["arm"] == "keep_alive")

    def delta(a: float, b: float) -> str:
        if a <= 0:
            return "n/a"
        pct = (a - b) / a * 100.0
        return f"{pct:+.1f}%"

    summary = {
        "cross_wall_unload_s": unload["cross"]["total_wall_s"],
        "cross_wall_keep_s": keep["cross"]["total_wall_s"],
        "cross_wall_delta": delta(
            unload["cross"]["total_wall_s"], keep["cross"]["total_wall_s"]
        ),
        "streak_wall_unload_s": unload["streak"]["total_wall_s"],
        "streak_wall_keep_s": keep["streak"]["total_wall_s"],
        "streak_wall_delta": delta(
            unload["streak"]["total_wall_s"], keep["streak"]["total_wall_s"]
        ),
        "keep_alive_value": args.keep_alive,
    }

    out = {
        "summary": summary,
        "arms": results,
    }
    out_path = ROOT / "results" / "tier-thrash-last.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=== SUMMARY ===")
    print(
        f"Cross-tier wall: unload={summary['cross_wall_unload_s']:.2f}s -> "
        f"keep={summary['cross_wall_keep_s']:.2f}s "
        f"({summary['cross_wall_delta']} vs unload)"
    )
    print(
        f"Same-tier streak: unload={summary['streak_wall_unload_s']:.2f}s -> "
        f"keep={summary['streak_wall_keep_s']:.2f}s "
        f"({summary['streak_wall_delta']} vs unload)"
    )
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
