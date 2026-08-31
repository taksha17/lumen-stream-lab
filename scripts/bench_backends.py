#!/usr/bin/env python3
"""Compare resident decode throughput: Ollama vs llama.cpp (llama-cli).

Usage:
  python3 scripts/bench_backends.py --backend ollama --model llama3.2:3b
  python3 scripts/bench_backends.py --backend llamacpp --gguf path/to/model.gguf
  python3 scripts/bench_backends.py --compare results/bench-ollama.json results/bench-llamacpp.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT = "Explain quantum computing in simple terms."


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[len(s) // 2]


def bench_ollama(
    model: str,
    prompt: str,
    *,
    num_predict: int = 128,
    warmup: int = 2,
    runs: int = 5,
) -> dict:
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": 0},
        }
    ).encode()
    rates: list[float] = []
    run_rows = []

    for i in range(warmup + runs):
        label = f"warmup-{i + 1}" if i < warmup else f"run-{i - warmup + 1}"
        req = urlrequest.Request(
            "http://127.0.0.1:11434/api/generate",
            data=body,
            headers={"content-type": "application/json"},
        )
        t0 = time.perf_counter()
        with urlrequest.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode())
        wall = time.perf_counter() - t0
        eval_count = int(data.get("eval_count") or 0)
        eval_ns = float(data.get("eval_duration") or 0)
        rate = eval_count / (eval_ns / 1e9) if eval_ns > 0 else 0.0
        row = {
            "label": label,
            "decode_tok_s": round(rate, 2),
            "eval_count": eval_count,
            "wall_s": round(wall, 2),
        }
        run_rows.append(row)
        if i >= warmup and rate > 0:
            rates.append(rate)
        print(f"{label}: {rate:.2f} tok/s ({eval_count} tokens)")

    med = round(median(rates), 2)
    return {
        "backend": "ollama",
        "model": model,
        "prompt": prompt,
        "num_predict": num_predict,
        "median_decode_tok_s": med,
        "runs": run_rows,
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def bench_llamacpp(
    gguf: Path,
    prompt: str,
    *,
    num_predict: int = 128,
    warmup: int = 2,
    runs: int = 5,
    ngl: int = 99,
) -> dict:
    cli = shutil.which("llama-cli") or shutil.which("llama")
    if not cli:
        raise SystemExit("llama-cli not in PATH — install llama.cpp or set LLAMA_CLI")

    rates: list[float] = []
    run_rows = []

    for i in range(warmup + runs):
        label = f"warmup-{i + 1}" if i < warmup else f"run-{i - warmup + 1}"
        cmd = [
            cli,
            "-m",
            str(gguf),
            "-p",
            prompt,
            "-n",
            str(num_predict),
            "--temp",
            "0",
            "-ngl",
            str(ngl),
            "--no-display-prompt",
        ]
        t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        wall = time.perf_counter() - t0
        out = proc.stdout + proc.stderr
        rate = 0.0
        tokens = 0
        for line in out.splitlines():
            m = re.search(r"eval time\s*=\s*[\d.]+\s*ms\s*/\s*(\d+)\s*runs", line, re.I)
            if m:
                tokens = int(m.group(1))
            m2 = re.search(r"(\d+\.?\d*)\s*tokens per second", line, re.I)
            if m2:
                rate = float(m2.group(1))
        if rate == 0.0 and tokens > 0 and wall > 0:
            rate = tokens / wall
        row = {
            "label": label,
            "decode_tok_s": round(rate, 2),
            "eval_count": tokens,
            "wall_s": round(wall, 2),
            "exit_code": proc.returncode,
        }
        run_rows.append(row)
        if i >= warmup and rate > 0:
            rates.append(rate)
        print(f"{label}: {rate:.2f} tok/s ({tokens} tokens)")

    med = round(median(rates), 2)
    return {
        "backend": "llamacpp",
        "gguf": str(gguf),
        "prompt": prompt,
        "num_predict": num_predict,
        "median_decode_tok_s": med,
        "runs": run_rows,
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def compare_reports(a: dict, b: dict) -> dict:
    ra = float(a.get("median_decode_tok_s") or 0)
    rb = float(b.get("median_decode_tok_s") or 0)
    winner = a.get("backend") if ra >= rb else b.get("backend")
    gain = ((max(ra, rb) - min(ra, rb)) / min(ra, rb) * 100) if min(ra, rb) > 0 else 0.0
    return {
        "a": {"backend": a.get("backend"), "median_decode_tok_s": ra},
        "b": {"backend": b.get("backend"), "median_decode_tok_s": rb},
        "winner": winner,
        "delta_pct": round(gain, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Bench Ollama vs llama.cpp resident decode")
    ap.add_argument("--backend", choices=["ollama", "llamacpp"])
    ap.add_argument("--model", default="llama3.2:3b")
    ap.add_argument("--gguf", type=Path, help="GGUF path for llamacpp backend")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--num-predict", type=int, default=128)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", type=Path, help="Write JSON report")
    ap.add_argument("--compare", nargs=2, metavar=("A.json", "B.json"))
    args = ap.parse_args()

    if args.compare:
        a = json.loads(Path(args.compare[0]).read_text(encoding="utf-8"))
        b = json.loads(Path(args.compare[1]).read_text(encoding="utf-8"))
        summary = compare_reports(a, b)
        print(json.dumps(summary, indent=2))
        return 0

    if not args.backend:
        ap.error("--backend is required unless --compare")

    if args.backend == "ollama":
        result = bench_ollama(
            args.model,
            args.prompt,
            num_predict=args.num_predict,
            warmup=args.warmup,
            runs=args.runs,
        )
    else:
        if not args.gguf or not args.gguf.exists():
            raise SystemExit("--gguf path required and must exist for llamacpp")
        result = bench_llamacpp(
            args.gguf,
            args.prompt,
            num_predict=args.num_predict,
            warmup=args.warmup,
            runs=args.runs,
        )

    print(f"\nMEDIAN: {result['median_decode_tok_s']} tok/s")
    out = args.out or ROOT / "results" / f"bench-{result['backend']}-last.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
