#!/usr/bin/env python3
"""A/B keyword router vs learned v2 (routing parity + optional holdout).

Does not change production defaults. Writes results/router-v2-ab-last.json.

Usage:
  python3 scripts/ab_router_v2.py
  python3 scripts/ab_router_v2.py --holdout
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lumen_router import route_with_engine  # noqa: E402

PROMPTS = ROOT / "data" / "router-eval-prompts.json"

# Holdout-style prompts not in E01–E12 — where v2 may diverge from keyword.
HOLDOUT = [
    {"id": "H01", "prompt": "hi"},
    {"id": "H02", "prompt": "Thanks!"},
    {"id": "H03", "prompt": "What is 15 * 3?"},
    {"id": "H04", "prompt": "Summarize the difference between HTTP and HTTPS briefly."},
    {"id": "H05", "prompt": "How does Ollama keep_alive interact with VRAM on a 4GB GPU?"},
    {"id": "H06", "prompt": "Is Lumen Stream Lab a PHP framework?"},
    {"id": "H07", "prompt": "Explain layer streaming for Soup fine-tunes in one paragraph."},
    {
        "id": "H08",
        "prompt": (
            "Write a detailed comprehensive essay on distributed systems consensus "
            "algorithms covering Paxos Raft and practical trade-offs for production "
            "deployments with failure modes and recovery strategies."
        ),
    },
    {"id": "H09", "prompt": "debug this stack trace please"},
    {"id": "H10", "prompt": "capital of Japan"},
]


def compare_rows(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    rows = []
    divergences = []
    for entry in entries:
        prompt = entry["prompt"]
        v1 = route_with_engine(prompt, engine="keyword")
        v2 = route_with_engine(prompt, engine="v2")
        row = {
            "id": entry.get("id"),
            "prompt": prompt[:120],
            "v1_tier": v1["tier"],
            "v1_model": v1["model"],
            "v2_tier": v2["tier"],
            "v2_model": v2["model"],
            "match": v1["tier"] == v2["tier"] and v1["model"] == v2["model"],
        }
        rows.append(row)
        if not row["match"]:
            divergences.append(row)
    return rows, divergences


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--holdout",
        action="store_true",
        help="Also compare HOLDOUT prompts (may diverge)",
    )
    args = ap.parse_args()

    eval_prompts = json.loads(PROMPTS.read_text(encoding="utf-8"))
    eval_rows, eval_div = compare_rows(eval_prompts)
    hold_rows: list[dict] = []
    hold_div: list[dict] = []
    if args.holdout:
        hold_rows, hold_div = compare_rows(HOLDOUT)

    summary = {
        "eval_n": len(eval_rows),
        "eval_match": sum(1 for r in eval_rows if r["match"]),
        "eval_divergences": len(eval_div),
        "holdout_n": len(hold_rows),
        "holdout_match": sum(1 for r in hold_rows if r["match"]) if hold_rows else None,
        "holdout_divergences": len(hold_div),
        "policy": "Default remains keyword until holdout quality/speed wins are proven",
    }

    out = {
        "summary": summary,
        "eval": eval_rows,
        "eval_divergences": eval_div,
        "holdout": hold_rows,
        "holdout_divergences": hold_div,
    }
    path = ROOT / "results" / "router-v2-ab-last.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=== Router v2 A/B ===")
    print(
        f"Eval suite: {summary['eval_match']}/{summary['eval_n']} match "
        f"({summary['eval_divergences']} divergences)"
    )
    if args.holdout:
        print(
            f"Holdout:    {summary['holdout_match']}/{summary['holdout_n']} match "
            f"({summary['holdout_divergences']} divergences)"
        )
        for d in hold_div:
            print(
                f"  DIFF {d['id']}: keyword={d['v1_tier']}/{d['v1_model']} "
                f"v2={d['v2_tier']}/{d['v2_model']} :: {d['prompt']!r}"
            )
    print(f"Wrote {path}")
    print("Default: keep LUMEN_ROUTER unset (keyword). Opt-in: LUMEN_ROUTER=v2")
    return 0 if summary["eval_divergences"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
