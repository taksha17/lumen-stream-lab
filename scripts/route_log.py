#!/usr/bin/env python3
"""Append-only route decision log for router v3 training.

Default path: results/route-log.jsonl (gitignored via results/*).
Disable with LUMEN_ROUTE_LOG=0.

Schema (one JSON object per line):
  id, ts, source, prompt, prompt_hash, tier, model, reason, router,
  wall_s, tok_s, eval_count, label_class, feedback, note
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG = ROOT / "results" / "route-log.jsonl"
MAX_PROMPT_CHARS = 800


def logging_enabled() -> bool:
    raw = (os.environ.get("LUMEN_ROUTE_LOG") or "1").strip().lower()
    return raw not in ("0", "false", "off", "no")


def log_path() -> Path:
    override = (os.environ.get("LUMEN_ROUTE_LOG_PATH") or "").strip()
    return Path(override) if override else DEFAULT_LOG


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def label_class_from_plan(tier: str | None, model: str | None) -> str:
    """Map plan to v2/v3 class names."""
    t = (tier or "").lower()
    m = model or ""
    if t == "fast":
        return "fast"
    if t == "quality":
        return "quality"
    if "lumen" in m or m.endswith("3b-lumen"):
        return "balanced_domain"
    return "balanced_lfm"


def append_route_event(
    *,
    prompt: str,
    tier: str,
    model: str,
    reason: str = "",
    router: str = "keyword",
    source: str = "unknown",
    wall_s: float | None = None,
    tok_s: float | None = None,
    eval_count: int | None = None,
    feedback: str | None = None,
    note: str = "",
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Append one route/generate event. Returns the record or None if disabled."""
    if not logging_enabled():
        return None
    dest = path or log_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = (prompt or "")[:MAX_PROMPT_CHARS]
    rec: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        "prompt": text,
        "prompt_hash": prompt_hash(prompt or ""),
        "tier": tier,
        "model": model,
        "reason": reason,
        "router": router,
        "label_class": label_class_from_plan(tier, model),
        "wall_s": wall_s,
        "tok_s": tok_s,
        "eval_count": eval_count,
        "feedback": feedback,
        "note": note,
    }
    with dest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read_events(path: Path | None = None) -> list[dict[str, Any]]:
    dest = path or log_path()
    if not dest.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in dest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def set_feedback(event_id: str, feedback: str, path: Path | None = None) -> bool:
    """Rewrite log with feedback on matching id (small files only)."""
    dest = path or log_path()
    rows = read_events(dest)
    found = False
    fb = feedback.strip().lower()
    if fb not in ("up", "down", "good", "bad", "skip"):
        raise ValueError("feedback must be up|down|good|bad|skip")
    if fb == "good":
        fb = "up"
    if fb == "bad":
        fb = "down"
    for row in rows:
        if row.get("id") == event_id:
            row["feedback"] = fb
            found = True
            break
    if not found:
        return False
    dest.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    return True


def feedback_last(feedback: str, path: Path | None = None) -> dict[str, Any] | None:
    rows = read_events(path)
    if not rows:
        return None
    last = rows[-1]
    if set_feedback(str(last["id"]), feedback, path):
        last["feedback"] = "up" if feedback in ("up", "good") else (
            "down" if feedback in ("down", "bad") else feedback
        )
        return last
    return None


def stats(path: Path | None = None) -> dict[str, Any]:
    rows = read_events(path)
    by_class: dict[str, int] = {}
    by_feedback: dict[str, int] = {}
    for r in rows:
        cls = r.get("label_class") or "unknown"
        by_class[cls] = by_class.get(cls, 0) + 1
        fb = r.get("feedback") or "none"
        by_feedback[fb] = by_feedback.get(fb, 0) + 1
    return {
        "path": str(path or log_path()),
        "n": len(rows),
        "by_class": by_class,
        "by_feedback": by_feedback,
        "with_feedback": sum(1 for r in rows if r.get("feedback") in ("up", "down")),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Route log utilities for router v3")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_stats = sub.add_parser("stats", help="Summarize route-log.jsonl")
    p_stats.set_defaults(func=lambda _: print(json.dumps(stats(), indent=2)))

    p_fb = sub.add_parser("feedback", help="Mark last event up/down")
    p_fb.add_argument("rating", choices=["up", "down", "good", "bad"])
    p_fb.set_defaults(func=None)

    args = ap.parse_args()
    if args.cmd == "feedback":
        rec = feedback_last(args.rating)
        if not rec:
            print("No events to rate", file=__import__("sys").stderr)
            return 1
        print(json.dumps({"ok": True, "id": rec["id"], "feedback": rec.get("feedback")}, indent=2))
        return 0
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
