#!/usr/bin/env python3
"""Sweep Ollama options for the experimental code tier (tok/s + wall + VRAM).

Usage:
  python3 scripts/tune_code_tier.py
  python3 scripts/tune_code_tier.py --model qwen2.5-coder:3b --baseline lfm-balanced

Writes results/code-tier-tune-last.json (gitignored). Does not enable LUMEN_CODE_TIER.
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from gpu_metrics import GpuSampler  # noqa: E402
from lumen_router import CODE_SYSTEM_PROMPT, MODELS  # noqa: E402

CODE_PROMPT = (
    "Write a Python function median_tok_s(runs: list[float]) -> float that returns "
    "the median decode tok/s. Include a one-line docstring and a tiny doctest. "
    "No explanation outside the code block."
)

SWEEPS: list[dict] = [
    {"label": "baseline_chatlike", "temperature": 0.7, "num_ctx": 2048, "num_batch": 512},
    {"label": "code_default", "temperature": 0.1, "num_ctx": 2048, "num_batch": 512},
    {"label": "code_ctx1024", "temperature": 0.1, "num_ctx": 1024, "num_batch": 512},
    {"label": "code_ctx1536", "temperature": 0.1, "num_ctx": 1536, "num_batch": 512},
    {"label": "code_batch256", "temperature": 0.1, "num_ctx": 2048, "num_batch": 256},
    {"label": "code_ctx1024_batch256", "temperature": 0.1, "num_ctx": 1024, "num_batch": 256},
    {"label": "code_temp0", "temperature": 0.0, "num_ctx": 2048, "num_batch": 512},
]


def generate(model: str, prompt: str, options: dict, system: str | None = None) -> dict:
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": options,
    }
    if system:
        payload["system"] = system
    body = json.dumps(payload).encode()
    req = urlrequest.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"content-type": "application/json"},
    )
    with urlrequest.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def one_run(model: str, label: str, opts: dict, *, use_code_system: bool) -> dict:
    options = {
        "num_predict": 128,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
        **{k: v for k, v in opts.items() if k != "label"},
    }
    sampler = GpuSampler(interval_s=0.2)
    sampler.start()
    t0 = time.perf_counter()
    data = generate(
        model,
        CODE_PROMPT,
        options,
        system=CODE_SYSTEM_PROMPT if use_code_system else None,
    )
    wall = time.perf_counter() - t0
    during = sampler.stop()
    eval_count = int(data.get("eval_count") or 0)
    eval_ns = float(data.get("eval_duration") or 0)
    tok_s = eval_count / (eval_ns / 1e9) if eval_ns > 0 else None
    text = (data.get("response") or "")[:400]
    return {
        "label": label,
        "model": model,
        "options": options,
        "decode_tok_s": round(tok_s, 2) if tok_s else None,
        "wall_s": round(wall, 3),
        "eval_count": eval_count,
        "gpu_util_max": during.get("util_gpu_pct_max"),
        "vram_peak_mib": during.get("memory_used_mib_max"),
        "response_preview": text,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Tune code-tier Ollama options")
    ap.add_argument("--model", default=MODELS["code"])
    ap.add_argument("--baseline", default=MODELS["balanced"], help="Compare wall/tok/s")
    ap.add_argument("--skip-baseline", action="store_true")
    args = ap.parse_args()

    results: list[dict] = []
    print(f"Model: {args.model}")
    print(f"Prompt: {CODE_PROMPT[:80]}...\n")

    if not args.skip_baseline:
        print("--- baseline LFM (chat options) ---")
        try:
            row = one_run(
                args.baseline,
                "lfm_balanced_chat",
                {"temperature": 0.7, "num_ctx": 2048, "num_batch": 512},
                use_code_system=False,
            )
            results.append(row)
            print(
                f"  {row['label']}: {row['decode_tok_s']} tok/s  "
                f"wall={row['wall_s']}s  util_max={row['gpu_util_max']}%  "
                f"VRAM={row['vram_peak_mib']} MiB"
            )
        except (URLError, OSError) as exc:
            print(f"  baseline failed: {exc}")
            return 1

    print(f"\n--- sweep {args.model} ---")
    for cfg in SWEEPS:
        label = cfg["label"]
        try:
            row = one_run(args.model, label, cfg, use_code_system=True)
            results.append(row)
            print(
                f"  {label}: {row['decode_tok_s']} tok/s  "
                f"wall={row['wall_s']}s  util_max={row['gpu_util_max']}%  "
                f"VRAM={row['vram_peak_mib']} MiB  "
                f"ctx={cfg['num_ctx']} temp={cfg['temperature']} batch={cfg['num_batch']}"
            )
        except (URLError, OSError) as exc:
            print(f"  {label} failed: {exc}")
            return 1

    coder_rows = [r for r in results if r["model"] == args.model and r.get("decode_tok_s")]
    best = max(coder_rows, key=lambda r: r["decode_tok_s"]) if coder_rows else None
    summary = {
        "prompt": CODE_PROMPT,
        "runs": results,
        "best_coder": best,
        "note": (
            "Auto LUMEN_CODE_TIER stays off unless orchestration mean still beats +40%. "
            "Apply best options via LUMEN_CODE_TEMPERATURE / LUMEN_CODE_NUM_CTX / LUMEN_CODE_NUM_BATCH "
            "or update CODE_DEFAULT_OPTIONS in lumen_router.py."
        ),
    }
    out = ROOT / "results" / "code-tier-tune-last.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nBest coder config: {best['label'] if best else 'n/a'}")
    if best:
        print(f"  options={best['options']}")
        print(f"  {best['decode_tok_s']} tok/s wall={best['wall_s']}s")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
