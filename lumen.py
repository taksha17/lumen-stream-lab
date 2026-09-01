#!/usr/bin/env python3
"""
Lumen orchestrator - route to fastest backend and apply speed stack config.
Usage:
  python lumen.py menu          # interactive terminal UI
  python lumen.py               # same as menu (no args)
  python lumen.py probe
  python lumen.py bench --model llama3.2:3b
  python lumen.py compare --baseline 47 --optimized 66
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_hardware() -> dict:
    p = ROOT / "hardware.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def load_reference_profile() -> dict:
    """Reference CI rig — not assumed to be the user's machine."""
    p = ROOT / "hardware" / "reference-lab.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def cmd_probe(_: argparse.Namespace) -> int:
    hw = {
        "probed_at": __import__("datetime").datetime.now().isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
    }
    try:
        import torch

        hw["torch"] = torch.__version__
        hw["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            hw["gpu"] = torch.cuda.get_device_name(0)
            hw["vram_mb"] = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
    except ImportError:
        hw["torch"] = None
        hw["cuda_available"] = False

    out = ROOT / "hardware.json"
    out.write_text(json.dumps(hw, indent=2), encoding="utf-8")
    print(json.dumps(hw, indent=2))
    print(f"Wrote {out}")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Run Ollama benchmark via subprocess if available."""
    model = args.model
    prompt = args.prompt or "Explain quantum computing in simple terms."

    try:
        proc = subprocess.run(
            ["ollama", "run", model, prompt, "--verbose"],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        print("ollama not in PATH", file=sys.stderr)
        return 1

    out = proc.stdout + proc.stderr
    decode_rate = None
    for line in out.splitlines():
        if "eval rate:" in line and "prompt" not in line:
            parts = line.split("eval rate:")[-1].strip().split()
            if parts:
                decode_rate = float(parts[0])

    result = {"model": model, "decode_tok_s": decode_rate, "raw_tail": out[-500:]}
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    path = results_dir / "bench-last.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if decode_rate else 1


def cmd_compare(args: argparse.Namespace) -> int:
    baseline = args.baseline
    optimized = args.optimized
    min_gain = args.min_gain
    gain = (optimized - baseline) / baseline
    passed = gain >= min_gain
    print(f"Baseline:  {baseline:.2f} tok/s")
    print(f"Optimized: {optimized:.2f} tok/s")
    print(f"Gain:      {gain * 100:.1f}%")
    print(f"Target:    >= {min_gain * 100:.0f}%")
    print(f"Result:    {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def cmd_route(args: argparse.Namespace) -> int:
    from lumen_router import route_decision

    prompt = args.prompt or ""
    tier = args.tier or "auto"
    decision = route_decision(prompt, tier)
    ref = load_reference_profile()
    measured = ref.get("measured_baselines", {})
    baseline = measured.get("llama3.2:3b_tok_s")
    target = None
    if baseline is not None:
        min_gain = ref.get("orchestration_target", {}).get("min_gain", 0.40)
        target = round(baseline * (1 + min_gain), 2)
    plan = {
        "prompt": prompt,
        "tier": decision["tier"],
        "model": decision["model"],
        "reason": decision["reason"],
        "backend": "ollama",
        "path": "resident",
        "reference_profile": ref.get("id", "reference-lab"),
        "reference_baseline_3b_tok_s": baseline,
        "reference_target_tok_s": target,
        "note": "Bench your own baseline on your hardware; reference numbers are CI-only.",
    }
    if decision.get("system_prompt"):
        plan["system_prompt"] = decision["system_prompt"]
    print(json.dumps(plan, indent=2))
    return 0


def cmd_menu(_: argparse.Namespace) -> int:
    from lumen_menu import run_interactive

    return run_interactive()


def main() -> int:
    if len(sys.argv) == 1:
        return cmd_menu(argparse.Namespace())

    parser = argparse.ArgumentParser(prog="lumen", description="Lumen Stream Lab orchestrator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe", help="Write hardware.json")
    p_probe.set_defaults(func=cmd_probe)

    p_bench = sub.add_parser("bench", help="Quick Ollama benchmark")
    p_bench.add_argument("--model", default="llama3.2:3b")
    p_bench.add_argument("--prompt", default=None)
    p_bench.set_defaults(func=cmd_bench)

    p_cmp = sub.add_parser("compare", help="Check +40% target")
    p_cmp.add_argument("--baseline", type=float, required=True)
    p_cmp.add_argument("--optimized", type=float, required=True)
    p_cmp.add_argument("--min-gain", type=float, default=0.40)
    p_cmp.set_defaults(func=cmd_compare)

    p_route = sub.add_parser("route", help="Hybrid tier routing plan (JSON)")
    p_route.add_argument("--prompt", default="", help="User prompt for auto routing")
    p_route.add_argument("--tier", default="auto", choices=["auto", "fast", "balanced", "quality"])
    p_route.set_defaults(func=cmd_route)

    p_menu = sub.add_parser("menu", help="Interactive terminal UI (chat, bench, gateway)")
    p_menu.set_defaults(func=cmd_menu)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
