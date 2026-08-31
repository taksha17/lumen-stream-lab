#!/usr/bin/env python3
"""
Append every `bench` JSON to a single history log and print a markdown table
comparing the newest run to the previous N. Lets you spot regressions the
same way you'd spot them in a CI dashboard.

Usage:
    python3 scripts/bench_history.py              # show last 10 runs
    python3 scripts/bench_history.py --last 20    # show last 20
    python3 scripts/bench_history.py --record path/to/bench.json   # append

History lives at results/bench-history.jsonl (one JSON object per line).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
HISTORY = RESULTS / "bench-history.jsonl"


def record(bench_path: Path) -> dict:
    """Append a bench JSON to the history log and return the normalized record."""
    data = json.loads(bench_path.read_text())
    record_obj = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(bench_path.resolve().relative_to(ROOT.resolve())
                          if bench_path.is_absolute() else str(bench_path)),
        "model": data.get("model"),
        "decode_tok_s": data.get("decode_tok_s"),
        # include any other top-level fields verbatim so we don't lose data
        **{k: v for k, v in data.items()
           if k not in {"model", "decode_tok_s", "raw_tail"}},
    }
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record_obj) + "\n")
    return record_obj


def load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    return [json.loads(line) for line in HISTORY.read_text().splitlines() if line]


def render_markdown(rows: list[dict]) -> str:
    if not rows:
        return "_no history yet — run `bench` and `--record` to start_"
    header = "| recorded_at | model | decode tok/s | source |"
    sep    = "|-------------|-------|--------------|--------|"
    lines = [header, sep]
    for r in rows:
        lines.append(
            f"| {r.get('recorded_at', '?')} "
            f"| {r.get('model', '?')} "
            f"| {r.get('decode_tok_s', '?')} "
            f"| {r.get('source_file', '?')} |"
        )
    # simple regression check: compare last 2 of same model
    last_by_model: dict[str, dict] = {}
    for r in rows:
        last_by_model.setdefault(r.get("model", ""), r)
    if last_by_model:
        lines.append("")
        lines.append("**Latest per model (vs previous run):**")
        for model, last in last_by_model.items():
            prior = [r for r in rows if r.get("model") == model][-2:-1]
            if prior and last.get("decode_tok_s") and prior[0].get("decode_tok_s"):
                a, b = prior[0]["decode_tok_s"], last["decode_tok_s"]
                if a > 0:
                    delta = (b - a) / a * 100
                    flag = "🟢" if delta >= -5 else "🔴"
                    lines.append(
                        f"- {model}: {a:.2f} → {b:.2f} tok/s "
                        f"({delta:+.1f}%) {flag}"
                    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Lumen bench history")
    ap.add_argument("--last", type=int, default=10,
                    help="How many recent runs to show (default: 10)")
    ap.add_argument("--record", type=str, default=None,
                    help="Path to a bench JSON to append to history")
    args = ap.parse_args()

    if args.record:
        p = Path(args.record)
        if not p.exists():
            print(f"file not found: {p}", file=sys.stderr)
            return 1
        rec = record(p)
        print(f"recorded: {rec['model']} @ {rec['decode_tok_s']} tok/s")
        return 0

    rows = load_history()[-args.last:]
    print(render_markdown(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
