#!/usr/bin/env python3
"""Probe candidate swaps for fast + domain tiers (tok/s + VRAM). Does not change defaults.

Usage:
  python3 scripts/probe_tier_swaps.py
  python3 scripts/probe_tier_swaps.py --skip-pull

Writes results/tier-swap-probe-last.json (gitignored).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from gpu_metrics import GpuSampler  # noqa: E402

OLLAMA = "http://127.0.0.1:11434"

FAST_PROMPT = "What is 2+2? Reply with one short sentence."
DOMAIN_PROMPT = "What is Lumen Stream Lab? Answer in 2-3 sentences."
GENERAL_PROMPT = "Explain TCP vs UDP in two short sentences."

PROBES = [
    {"slot": "fast", "model": "llama3.2:1b", "prompt": FAST_PROMPT, "num_predict": 64},
    {"slot": "fast_candidate", "model": "qwen3:1.7b", "prompt": FAST_PROMPT, "num_predict": 64},
    {"slot": "balanced", "model": "lfm-balanced", "prompt": GENERAL_PROMPT, "num_predict": 96},
    {
        "slot": "domain",
        "model": "qwen2.5-3b-lumen",
        "prompt": DOMAIN_PROMPT,
        "num_predict": 128,
    },
    {
        "slot": "domain_baseline",
        "model": "qwen2.5:3b-instruct-q4_K_M",
        "prompt": DOMAIN_PROMPT,
        "num_predict": 128,
    },
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


def ensure_ollama() -> None:
    api_json("GET", "/api/tags", timeout=5)


def model_names() -> set[str]:
    tags = api_json("GET", "/api/tags", timeout=10)
    return {m.get("name", "") for m in tags.get("models", [])}


def pull(model: str) -> None:
    print(f"  pull {model} ...")
    api_json("POST", "/api/pull", {"name": model, "stream": False}, timeout=900)
    print(f"  pull {model} done")


def generate(model: str, prompt: str, num_predict: int) -> dict:
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": 0.2},
        "keep_alive": "10m",
    }
    if "lumen" in model:
        # Domain model benefits from system prompt when present on disk
        sys_path = ROOT / "data" / "domain-system-prompt.txt"
        if sys_path.exists():
            body["system"] = sys_path.read_text(encoding="utf-8").strip()
    return api_json("POST", "/api/generate", body, timeout=300)


def one(slot: str, model: str, prompt: str, num_predict: int) -> dict:
    sampler = GpuSampler(interval_s=0.2)
    sampler.start()
    t0 = time.perf_counter()
    data = generate(model, prompt, num_predict)
    wall = time.perf_counter() - t0
    during = sampler.stop()
    eval_count = int(data.get("eval_count") or 0)
    eval_ns = float(data.get("eval_duration") or 0)
    tok_s = eval_count / (eval_ns / 1e9) if eval_ns > 0 else None
    return {
        "slot": slot,
        "model": model,
        "decode_tok_s": round(tok_s, 2) if tok_s else None,
        "wall_s": round(wall, 3),
        "eval_count": eval_count,
        "gpu_util_max": during.get("util_gpu_pct_max"),
        "vram_peak_mib": during.get("memory_used_mib_max"),
        "response_preview": (data.get("response") or "")[:280],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pull", action="store_true")
    args = ap.parse_args()

    try:
        ensure_ollama()
    except (URLError, OSError) as exc:
        print(f"Ollama not reachable: {exc}")
        return 1

    installed = model_names()
    needed = {p["model"] for p in PROBES}
    missing = [m for m in needed if not any(m == n or n.startswith(m) for n in installed)]
    if missing and not args.skip_pull:
        for m in missing:
            try:
                pull(m)
            except (URLError, OSError) as exc:
                print(f"  skip {m}: {exc}")
    elif missing:
        print(f"Missing models (use without --skip-pull): {missing}")

    rows: list[dict] = []
    print("=== tier swap probe ===\n")
    for p in PROBES:
        model = p["model"]
        if not any(model == n or n.startswith(model) for n in model_names()):
            print(f"SKIP {p['slot']} ({model}) — not installed")
            continue
        try:
            row = one(p["slot"], model, p["prompt"], p["num_predict"])
            rows.append(row)
            print(
                f"{p['slot']:18} {model:32} "
                f"{row['decode_tok_s']} tok/s  wall={row['wall_s']}s  "
                f"util_max={row['gpu_util_max']}%  VRAM={row['vram_peak_mib']} MiB"
            )
        except (URLError, OSError) as exc:
            print(f"FAIL {p['slot']} ({model}): {exc}")
            return 1

    by_slot = {r["slot"]: r for r in rows}
    notes: list[str] = []
    if "fast" in by_slot and "fast_candidate" in by_slot:
        a, b = by_slot["fast"], by_slot["fast_candidate"]
        if (b.get("decode_tok_s") or 0) > (a.get("decode_tok_s") or 0) * 1.05:
            notes.append("fast_candidate faster than llama3.2:1b — consider A/B before swap")
        else:
            notes.append("keep llama3.2:1b as fast unless quality wins")
    if "domain" in by_slot and "domain_baseline" in by_slot:
        notes.append(
            "Compare response_preview manually for domain accuracy; tok/s alone does not promote lumen"
        )

    out = {
        "runs": rows,
        "notes": notes,
        "policy": "Do not change MODELS defaults until win-regression / domain smoke PASS",
    }
    path = ROOT / "results" / "tier-swap-probe-last.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nNotes: {notes}")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
