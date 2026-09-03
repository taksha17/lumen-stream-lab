#!/usr/bin/env python3
"""Seed results/route-log.jsonl from the E01–E12 eval suite (teacher labels).

Safe to re-run: appends with source=seed_eval (does not wipe existing feedback).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lumen_router import route_decision  # noqa: E402
from route_log import append_route_event, stats  # noqa: E402

PROMPTS = ROOT / "data" / "router-eval-prompts.json"


def main() -> int:
    entries = json.loads(PROMPTS.read_text(encoding="utf-8"))
    n = 0
    for entry in entries:
        prompt = entry["prompt"]
        d = route_decision(prompt)
        append_route_event(
            prompt=prompt,
            tier=d["tier"],
            model=d["model"],
            reason=d.get("reason", ""),
            router="keyword",
            source="seed_eval",
            note=f"eval:{entry.get('id', '')}",
            feedback="up",  # teacher-trusted seed
        )
        n += 1
    print(f"Seeded {n} eval prompts")
    print(json.dumps(stats(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
