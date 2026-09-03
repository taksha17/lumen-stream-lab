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
import time
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
    """Ollama generate + nvidia-smi samples during decode."""
    model = args.model
    prompt = args.prompt or "Explain quantum computing in simple terms with enough tokens to load the GPU."

    sys.path.insert(0, str(ROOT / "scripts"))
    from gpu_check import ollama_generate, ollama_ps  # noqa: WPS433
    from gpu_metrics import GpuSampler, snapshot, summarize_for_humans  # noqa: WPS433

    idle = snapshot()
    sampler = GpuSampler(interval_s=0.2)
    sampler.start()
    t0 = time.perf_counter()
    try:
        data = ollama_generate(model, prompt, int(getattr(args, "num_predict", 128)))
    except Exception as exc:  # urllib errors
        sampler.stop()
        print(f"Ollama generate failed: {exc}", file=sys.stderr)
        print("Start ollama serve and pull the model.", file=sys.stderr)
        return 1
    wall = time.perf_counter() - t0
    during = sampler.stop()

    eval_count = int(data.get("eval_count") or 0)
    eval_ns = float(data.get("eval_duration") or 0)
    decode_rate = eval_count / (eval_ns / 1e9) if eval_ns > 0 else None

    result = {
        "model": model,
        "decode_tok_s": round(decode_rate, 2) if decode_rate else None,
        "wall_s": round(wall, 3),
        "eval_count": eval_count,
        "gpu_idle": idle,
        "gpu_during": {k: v for k, v in during.items() if k != "samples"},
        "ollama_ps": ollama_ps(),
    }
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    path = results_dir / "bench-last.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print()
    print(summarize_for_humans(idle, during))
    print(f"Wrote {path}")
    return 0 if decode_rate else 1


def cmd_gpu(args: argparse.Namespace) -> int:
    """Dedicated GPU+Ollama check (same as scripts/gpu_check.py)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from gpu_check import main as gpu_main  # noqa: WPS433

    argv = ["gpu_check.py", "--model", args.model, "--num-predict", str(args.num_predict)]
    if args.prompt:
        argv.extend(["--prompt", args.prompt])
    if args.out:
        argv.extend(["--out", args.out])
    old = sys.argv
    try:
        sys.argv = argv
        return gpu_main()
    finally:
        sys.argv = old


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
    from lumen_router import resolve_router_engine, route_with_engine

    prompt = args.prompt or ""
    tier = args.tier or "auto"
    engine = args.router or resolve_router_engine()
    decision = route_with_engine(prompt, tier, engine=engine)
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
        "router": decision.get("router", engine),
        "backend": "ollama",
        "path": "resident",
        "reference_profile": ref.get("id", "reference-lab"),
        "reference_baseline_3b_tok_s": baseline,
        "reference_target_tok_s": target,
        "note": "Bench your own baseline on your hardware; reference numbers are CI-only.",
    }
    if decision.get("system_prompt"):
        plan["system_prompt"] = decision["system_prompt"]
    if decision.get("options"):
        plan["options"] = decision["options"]
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

    p_bench = sub.add_parser("bench", help="Ollama generate + GPU util samples")
    p_bench.add_argument("--model", default="llama3.2:3b")
    p_bench.add_argument("--prompt", default=None)
    p_bench.add_argument("--num-predict", type=int, default=128)
    p_bench.set_defaults(func=cmd_bench)

    p_gpu = sub.add_parser("gpu", help="Sample nvidia-smi during one Ollama generate")
    p_gpu.add_argument("--model", default="llama3.2:3b")
    p_gpu.add_argument("--prompt", default=None)
    p_gpu.add_argument("--num-predict", type=int, default=128)
    p_gpu.add_argument("--out", default="", help="Optional JSON path under results/")
    p_gpu.set_defaults(func=cmd_gpu)

    p_cmp = sub.add_parser("compare", help="Check +40% target")
    p_cmp.add_argument("--baseline", type=float, required=True)
    p_cmp.add_argument("--optimized", type=float, required=True)
    p_cmp.add_argument("--min-gain", type=float, default=0.40)
    p_cmp.set_defaults(func=cmd_compare)

    p_route = sub.add_parser("route", help="Hybrid tier routing plan (JSON)")
    p_route.add_argument("--prompt", default="", help="User prompt for auto routing")
    p_route.add_argument("--tier", default="auto", choices=["auto", "fast", "balanced", "quality", "code", "reason"])
    p_route.add_argument(
        "--router",
        default=None,
        choices=["keyword", "v2"],
        help="Routing engine (default: LUMEN_ROUTER or keyword)",
    )
    p_route.set_defaults(func=cmd_route)

    p_menu = sub.add_parser("menu", help="Interactive terminal UI (chat, bench, gateway)")
    p_menu.set_defaults(func=cmd_menu)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
