#!/usr/bin/env python3
"""Show which upgrade-candidate Ollama tags are present locally. No network, no hostnames."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "data" / "upgrade-candidates.json"


def ollama_names() -> set[str]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode())
        return {m.get("name", "") for m in data.get("models", [])}
    except OSError:
        return set()


def main() -> int:
    payload = json.loads(CAND.read_text(encoding="utf-8"))
    installed = ollama_names()
    if not installed:
        print("Ollama API not reachable at 127.0.0.1:11434 (start ollama serve).")
        print("Candidate tags to pull when ready:\n")
    else:
        print(f"Ollama tags on this machine: {len(installed)}\n")

    print("Resident candidates")
    for row in payload["resident_candidates"]:
        tag = row["ollama"]
        hit = any(tag == n or n.startswith(tag + ":") or n.startswith(tag) for n in installed)
        mark = "YES" if hit else "—"
        print(f"  [{mark:3}] {tag:36} slot={row['slot']}")
    print("\nQuality-eval only (do not add to auto router)")
    for row in payload["quality_eval_only"]:
        tag = row["ollama"]
        hit = any(tag == n or n.startswith(tag) for n in installed)
        mark = "YES" if hit else "—"
        print(f"  [{mark:3}] {tag}")
    print("\nEnable experimental code auto-route only after a bench PASS:")
    print("  LUMEN_CODE_TIER=1 python3 lumen.py route --prompt \"Write a Python function...\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
