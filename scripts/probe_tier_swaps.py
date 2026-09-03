#!/usr/bin/env python3
"""Probe candidate swaps for hybrid tiers (tok/s + VRAM). Does not change defaults.

Usage:
  python3 scripts/probe_tier_swaps.py
  python3 scripts/probe_tier_swaps.py --slot balanced
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
REASON_PROMPT = (
    "A store has 47 apples. It sells 19 in the morning and receives 12 more "
    "in the afternoon. How many apples are left? Show brief steps."
)

PROBES = [
    {"slot": "fast", "model": "llama3.2:1b", "prompt": FAST_PROMPT, "num_predict": 64},
    {"slot": "fast_candidate", "model": "qwen3:1.7b", "prompt": FAST_PROMPT, "num_predict": 64},
    {"slot": "balanced", "model": "lfm-balanced", "prompt": GENERAL_PROMPT, "num_predict": 96},
    {
        "slot": "balanced_candidate",
        "model": "qwen3:4b",
        "prompt": GENERAL_PROMPT,
        "num_predict": 96,
    },
    {
        "slot": "balanced_candidate",
        "model": "phi4-mini",
        "prompt": GENERAL_PROMPT,
        "num_predict": 96,
    },
    {
        "slot": "balanced_candidate",
        "model": "gemma3:4b-it-qat",
        "prompt": GENERAL_PROMPT,
        "num_predict": 96,
    },
    {
        "slot": "balanced_reason",
        "model": "lfm-balanced",
        "prompt": REASON_PROMPT,
        "num_predict": 128,
    },
    {
        "slot": "balanced_reason",
        "model": "qwen3:4b",
        "prompt": REASON_PROMPT,
        "num_predict": 128,
    },
    {
        "slot": "balanced_reason",
        "model": "phi4-mini",
        "prompt": REASON_PROMPT,
        "num_predict": 128,
    },
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


def model_installed(model: str, installed: set[str] | None = None) -> bool:
    names = installed if installed is not None else model_names()
    return any(model == n or n.startswith(model + ":") or n.startswith(model) for n in names)


def pull(model: str) -> None:
    print(f"  pull {model} ...")
    api_json("POST", "/api/pull", {"name": model, "stream": False}, timeout=1800)
    print(f"  pull {model} done")


def generate(model: str, prompt: str, num_predict: int) -> dict:
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": 0.2},
        "keep_alive": 0,  # free VRAM between candidates on 4GB
    }
    if "lumen" in model:
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
    load_ns = float(data.get("load_duration") or 0)
    tok_s = eval_count / (eval_ns / 1e9) if eval_ns > 0 else None
    return {
        "slot": slot,
        "model": model,
        "decode_tok_s": round(tok_s, 2) if tok_s else None,
        "wall_s": round(wall, 3),
        "load_s": round(load_ns / 1e9, 3) if load_ns else None,
        "eval_count": eval_count,
        "gpu_util_max": during.get("util_gpu_pct_max"),
        "vram_peak_mib": during.get("memory_used_mib_max"),
        "response_preview": (data.get("response") or "")[:280],
    }


def filter_probes(slot_filter: str | None) -> list[dict]:
    if not slot_filter or slot_filter == "all":
        return list(PROBES)
    key = slot_filter.lower()
    if key == "balanced":
        return [
            p
            for p in PROBES
            if p["slot"] in ("balanced", "balanced_candidate", "balanced_reason")
        ]
    if key == "fast":
        return [p for p in PROBES if p["slot"] in ("fast", "fast_candidate")]
    if key == "domain":
        return [p for p in PROBES if p["slot"] in ("domain", "domain_baseline")]
    return [p for p in PROBES if p["slot"] == key]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pull", action="store_true")
    ap.add_argument(
        "--slot",
        default="all",
        help="all | fast | balanced | domain | or exact slot name",
    )
    args = ap.parse_args()
    probes = filter_probes(args.slot)

    try:
        ensure_ollama()
    except (URLError, OSError) as exc:
        print(f"Ollama not reachable: {exc}")
        return 1

    installed = model_names()
    needed = {p["model"] for p in probes}
    missing = [m for m in needed if not model_installed(m, installed)]
    if missing and not args.skip_pull:
        for m in missing:
            try:
                pull(m)
            except (URLError, OSError, TimeoutError) as exc:
                print(f"  skip {m}: {exc}")
    elif missing:
        print(f"Missing models (use without --skip-pull): {missing}")

    rows: list[dict] = []
    print(f"=== tier swap probe (slot={args.slot}) ===\n")
    for p in probes:
        model = p["model"]
        if not model_installed(model):
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
            preview = (row.get("response_preview") or "").replace("\n", " ")[:120]
            if preview:
                print(f"  preview: {preview}")
        except (URLError, OSError, TimeoutError) as exc:
            print(f"FAIL {p['slot']} ({model}): {exc}")
            rows.append(
                {
                    "slot": p["slot"],
                    "model": model,
                    "error": str(exc),
                }
            )

    by_slot = {r["slot"]: r for r in rows if "error" not in r}
    notes: list[str] = []
    if "fast" in by_slot and "fast_candidate" in by_slot:
        a, b = by_slot["fast"], by_slot["fast_candidate"]
        if (b.get("decode_tok_s") or 0) > (a.get("decode_tok_s") or 0) * 1.05:
            notes.append("fast_candidate faster than llama3.2:1b — consider A/B before swap")
        else:
            notes.append("keep llama3.2:1b as fast unless quality wins")

    bal = [r for r in rows if r.get("slot") == "balanced" and "error" not in r]
    cands = [r for r in rows if r.get("slot") == "balanced_candidate" and "error" not in r]
    if bal and cands:
        base_tok = bal[0].get("decode_tok_s") or 0
        for c in cands:
            ct = c.get("decode_tok_s") or 0
            vram = c.get("vram_peak_mib")
            if ct >= base_tok * 0.95 and (vram is None or vram < 3800):
                notes.append(
                    f"{c['model']}: tok/s {ct} vs LFM {base_tok} — possible A/B if quality better"
                )
            else:
                notes.append(
                    f"{c['model']}: keep LFM — tok/s {ct} vs {base_tok} "
                    f"(VRAM={vram})"
                )

    if "domain" in by_slot and "domain_baseline" in by_slot:
        notes.append(
            "Compare response_preview manually for domain accuracy; tok/s alone does not promote lumen"
        )

    out = {
        "slot_filter": args.slot,
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
