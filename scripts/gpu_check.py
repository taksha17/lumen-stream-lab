#!/usr/bin/env python3
"""Generate one Ollama prompt while sampling nvidia-smi (CUDA util + VRAM)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from gpu_metrics import GpuSampler, snapshot, summarize_for_humans  # noqa: E402


def ollama_generate(model: str, prompt: str, num_predict: int) -> dict:
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": 0.2},
        }
    ).encode()
    req = urlrequest.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"content-type": "application/json"},
    )
    with urlrequest.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def ollama_ps() -> str:
    try:
        with urlrequest.urlopen("http://127.0.0.1:11434/api/ps", timeout=5) as resp:
            data = json.loads(resp.read().decode())
        models = data.get("models") or []
        if not models:
            return "(no models loaded)"
        lines = []
        for m in models:
            vram = m.get("size_vram")
            lines.append(
                f"{m.get('name')} size_vram={vram} size={m.get('size')}"
            )
        return "\n".join(lines)
    except (URLError, OSError, json.JSONDecodeError) as exc:
        return f"(api/ps failed: {exc})"


def main() -> int:
    p = argparse.ArgumentParser(description="Ollama generate + GPU util samples")
    p.add_argument("--model", default="llama3.2:3b")
    p.add_argument(
        "--prompt",
        default="Explain gravity in two short paragraphs so decode lasts long enough to sample the GPU.",
    )
    p.add_argument("--num-predict", type=int, default=128)
    p.add_argument("--out", default="", help="Write JSON under results/ (gitignored)")
    args = p.parse_args()

    idle = snapshot()
    print(summarize_for_humans(idle))
    print()

    sampler = GpuSampler(interval_s=0.2)
    sampler.start()
    t0 = time.perf_counter()
    try:
        data = ollama_generate(args.model, args.prompt, args.num_predict)
    except (URLError, OSError) as exc:
        sampler.stop()
        print(f"Ollama generate failed: {exc}")
        print("Start: ollama serve")
        return 1
    wall = time.perf_counter() - t0
    during = sampler.stop()

    eval_count = int(data.get("eval_count") or 0)
    eval_ns = float(data.get("eval_duration") or 0)
    tok_s = eval_count / (eval_ns / 1e9) if eval_ns > 0 else None

    report = {
        "model": args.model,
        "wall_s": round(wall, 3),
        "decode_tok_s": round(tok_s, 2) if tok_s else None,
        "eval_count": eval_count,
        "gpu_idle": idle,
        "gpu_during": {k: v for k, v in during.items() if k != "samples"},
        "gpu_during_samples": during.get("samples"),
        "ollama_ps": ollama_ps(),
    }

    print(summarize_for_humans(idle, during))
    print(f"decode_tok_s={report['decode_tok_s']} wall_s={report['wall_s']}")
    print("ollama ps:")
    print(report["ollama_ps"])

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
