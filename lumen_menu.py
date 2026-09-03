"""Interactive terminal UI for Lumen Stream Lab (stdlib only)."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

ROOT = Path(__file__).resolve().parent

BANNER = """
==========================================
  LUMEN STREAM LAB
  interactive menu
==========================================
"""

MENU = """
  1) Setup check        (Ollama, GPU probe, models)
  2) Chat               (route + generate in a loop)
  3) Route one prompt   (plan JSON only)
  4) Bench a model      (decode tok/s + GPU util samples)
  5) +40% compare       (baseline vs orchestration mean)
  6) HTTP gateway       (local :8080)
  7) Backend shootout   (Ollama vs llama.cpp)
  8) Run router tests   (CI parity suite)
  9) Open docs          (paths + GitHub)
  0) Exit
"""


def _pause() -> None:
    try:
        input("\nPress Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        print()


def _prompt(text: str, default: str = "") -> str:
    try:
        suffix = f" [{default}]" if default else ""
        line = input(f"{text}{suffix}: ").strip()
        return line or default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def _prompt_float(text: str, default: float) -> float:
    raw = _prompt(text, str(default))
    try:
        return float(raw)
    except ValueError:
        return default


def _ollama_ok() -> bool:
    try:
        with urlrequest.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as resp:
            return resp.status == 200
    except (urlerror.URLError, OSError):
        return False


def _ollama_models() -> list[str]:
    try:
        with urlrequest.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return [m.get("name", "") for m in data.get("models", [])]
    except (urlerror.URLError, OSError, json.JSONDecodeError):
        return []


def _generate_ollama(
    model: str,
    prompt: str,
    *,
    tier: str | None = None,
    options: dict | None = None,
) -> tuple[str, float | None]:
    from lumen_router import ollama_generate_payload, visible_response

    body = json.dumps(
        ollama_generate_payload(model, prompt, stream=False, options=options, tier=tier)
    ).encode()
    req = urlrequest.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"content-type": "application/json"},
    )
    t0 = time.perf_counter()
    with urlrequest.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
    wall = time.perf_counter() - t0
    text = visible_response(data)
    eval_count = int(data.get("eval_count") or 0)
    eval_ns = float(data.get("eval_duration") or 0)
    rate = eval_count / (eval_ns / 1e9) if eval_ns > 0 else None
    if rate is None and eval_count > 0 and wall > 0:
        rate = eval_count / wall
    return text, rate


def action_setup() -> None:
    print("\n=== Setup check ===\n")
    print(f"Platform: {platform.platform()}")
    print(f"Repo:     {ROOT}")

    ollama_bin = shutil.which("ollama")
    print(f"Ollama:   {'found at ' + ollama_bin if ollama_bin else 'NOT in PATH'}")
    print(f"API:      {'running' if _ollama_ok() else 'not reachable (start: ollama serve)'}")

    hw = ROOT / "hardware.json"
    if hw.exists():
        print(f"hardware.json: OK ({hw})")
    else:
        print("hardware.json: missing — run option 1 again after probe, or choose probe now")
        if _prompt("Run probe now? (y/n)", "y").lower().startswith("y"):
            subprocess.run([sys.executable, str(ROOT / "lumen.py"), "probe"], check=False)

    models = _ollama_models()
    if models:
        print(f"\nOllama models ({len(models)}):")
        for name in sorted(models)[:12]:
            print(f"  - {name}")
        if len(models) > 12:
            print(f"  ... and {len(models) - 12} more")
    else:
        print("\nNo models listed. See docs/MODELS.md:")
        print("  ollama pull llama3.2:1b")
        print("  ollama pull llama3.2:3b")

    cfg = ROOT / "lumen.yaml"
    if cfg.exists():
        print(f"\nlumen.yaml: found")
    else:
        print(f"\nlumen.yaml: not found (copy lumen.yaml.example -> lumen.yaml)")

    if platform.system() == "Windows":
        ps = ROOT / "deploy" / "win-regression.ps1"
        if ps.exists():
            print(f"\nWindows regression: powershell -File {ps}")

    print("\nDomain models on Hugging Face (no Soup training needed):")
    print("  3B: https://huggingface.co/takshathosani17/qwen2.5-3b-lumen")
    print("  7B: publish with deploy/publish-hf-remote.sh (after HF upload)")
    print("  Install: hf download USER/qwen2.5-3b-lumen --local-dir ./qwen-lumen")
    print("           ollama create qwen2.5-3b-lumen -f qwen-lumen/Modelfile")

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from gpu_metrics import snapshot, summarize_for_humans

        print("\n--- GPU (nvidia-smi) ---")
        print(summarize_for_humans(snapshot()))
        print("During benches: python3 lumen.py gpu --model llama3.2:3b")
        print("Windows Task Manager 'GPU' often stays at 0% (3D engine). Use nvidia-smi CUDA util.")
    except Exception as exc:
        print(f"\nGPU probe skipped: {exc}")


def action_chat() -> None:
    from lumen_router import resolve_router_engine, route_with_engine

    if not _ollama_ok():
        print("\nOllama is not running. Start it with: ollama serve")
        return

    engine = resolve_router_engine()
    print("\n=== Chat (route + generate) ===")
    print(f"Router engine: {engine} (set LUMEN_ROUTER=v2 for learned)")
    print("Type a prompt, or /quit to leave.")
    print("/tier auto|fast|balanced|quality|code  (code = opt-in coder; auto-route stays off)\n")

    forced_tier: str | None = None
    allowed = {"auto", "fast", "balanced", "quality", "code"}
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user.lower() in ("/quit", "/exit", "/q"):
            break
        if user.lower().startswith("/tier "):
            forced_tier = user.split(maxsplit=1)[1].strip().lower() if " " in user else "auto"
            if forced_tier not in allowed:
                print(f"unknown tier (use: {'|'.join(sorted(allowed))})")
                continue
            if forced_tier == "auto":
                forced_tier = None
                print("forced tier: auto")
            else:
                print(f"forced tier: {forced_tier}")
            continue

        decision = route_with_engine(user, forced_tier or "auto")
        model = decision["model"]
        print(f"\n[router={decision.get('router', engine)} tier={decision['tier']} model={model}]")
        print(f"[reason: {decision['reason']}]\n")

        try:
            answer, rate = _generate_ollama(
                model,
                user,
                tier=decision["tier"],
                options=decision.get("options"),
            )
        except urlerror.URLError as e:
            print(f"Generate failed: {e}")
            continue

        print(answer.strip())
        if rate is not None:
            print(f"\n--- {rate:.1f} tok/s ---\n")
        else:
            print()


def action_route() -> None:
    prompt = _prompt("Prompt")
    if not prompt:
        return
    subprocess.run(
        [sys.executable, str(ROOT / "lumen.py"), "route", "--prompt", prompt],
        check=False,
    )


def action_bench() -> None:
    model = _prompt("Model", "llama3.2:3b")
    subprocess.run(
        [sys.executable, str(ROOT / "lumen.py"), "bench", "--model", model],
        check=False,
    )


def action_compare() -> None:
    ref_path = ROOT / "hardware" / "reference-lab.json"
    default_base = 48.38
    default_opt = 70.0
    if ref_path.exists():
        ref = json.loads(ref_path.read_text(encoding="utf-8"))
        mb = ref.get("measured_baselines", {})
        default_base = float(mb.get("llama3.2:3b_tok_s", default_base))
        default_opt = float(mb.get("orchestration_mean_tok_s", default_opt))

    baseline = _prompt_float("Baseline tok/s (always-3B)", default_base)
    optimized = _prompt_float("Orchestration mean tok/s", default_opt)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "compare.py"),
            "--baseline",
            str(baseline),
            "--optimized",
            str(optimized),
            "--min-gain",
            "0.40",
        ],
        check=False,
    )


def action_gateway() -> None:
    port = _prompt("Port", "8080")
    gw = ROOT / "scripts" / "lumen_gateway.py"
    print(f"\nStarting gateway on http://127.0.0.1:{port}")
    print("Try: curl -s http://127.0.0.1:{0}/v1/plan -H 'content-type: application/json' -d '{{\"prompt\":\"What is 2+2?\"}}'".format(port))
    print("Ctrl+C to stop.\n")
    try:
        subprocess.run(
            [sys.executable, str(gw), "--port", port],
            check=False,
        )
    except KeyboardInterrupt:
        print("\nGateway stopped.")


def action_shootout() -> None:
    if platform.system() == "Windows":
        ps = ROOT / "deploy" / "win-bench-llamacpp-vs-ollama.ps1"
        if ps.exists():
            print(f"\nRunning {ps.name} ...\n")
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps)],
                cwd=str(ROOT),
                check=False,
            )
            return
    model = _prompt("Ollama model", "llama3.2:3b")
    print("\n--- Ollama bench ---")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "bench_backends.py"),
            "--backend",
            "ollama",
            "--model",
            model,
            "--out",
            str(ROOT / "results" / "bench-ollama-shootout.json"),
        ],
        check=False,
    )
    gguf = _prompt("GGUF path for llama.cpp (leave empty to skip)", "")
    if gguf and Path(gguf).exists():
        print("\n--- llama.cpp bench ---")
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "bench_backends.py"),
                "--backend",
                "llamacpp",
                "--gguf",
                gguf,
                "--out",
                str(ROOT / "results" / "bench-llamacpp-shootout.json"),
            ],
            check=False,
        )
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "bench_backends.py"),
                "--compare",
                str(ROOT / "results" / "bench-ollama-shootout.json"),
                str(ROOT / "results" / "bench-llamacpp-shootout.json"),
            ],
            check=False,
        )


def action_tests() -> None:
    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=str(ROOT),
        check=False,
    )


def action_docs() -> None:
    docs = [
        ("Docs index", ROOT / "docs" / "README.md"),
        ("Architecture (detailed)", ROOT / "docs" / "ARCHITECTURE.md"),
        ("Reference results", ROOT / "docs" / "REFERENCE-RESULTS.md"),
        ("Hardware testing / contributors", ROOT / "docs" / "HARDWARE-TESTING.md"),
        ("Enterprise case study", ROOT / "docs" / "ENTERPRISE-CASE-STUDY.md"),
        ("Models setup", ROOT / "docs" / "MODELS.md"),
        ("Contributing", ROOT / "CONTRIBUTING.md"),
        ("Agent integration (Hermes)", ROOT / "docs" / "AGENT-INTEGRATION.md"),
        ("Tool comparison", ROOT / "docs" / "TOOL-COMPARISON.md"),
        ("Terminal UI guide", ROOT / "docs" / "TERMINAL-UI.md"),
        ("Repo layout", ROOT / "docs" / "REPO-LAYOUT.md"),
        ("Enterprise integration", ROOT / "docs" / "ENTERPRISE.md"),
        ("Results log", ROOT / "docs" / "RESULTS.md"),
        ("Upgrades changelog", ROOT / "UPGRADES.md"),
    ]
    print("\n=== Documentation ===\n")
    for label, path in docs:
        status = "OK" if path.exists() else "missing"
        print(f"  [{status}] {label}: {path}")
    print("\nGitHub: https://github.com/taksha17/lumen-stream-lab")


def run_interactive() -> int:
    actions = {
        "1": action_setup,
        "2": action_chat,
        "3": action_route,
        "4": action_bench,
        "5": action_compare,
        "6": action_gateway,
        "7": action_shootout,
        "8": action_tests,
        "9": action_docs,
        "0": lambda: None,
    }

    print(BANNER)
    while True:
        print(MENU)
        try:
            choice = input("Choose> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0
        if choice in ("0", "q", "quit", "exit"):
            print("Bye.")
            return 0
        action = actions.get(choice)
        if not action:
            print("Unknown option.")
            continue
        try:
            action()
        except KeyboardInterrupt:
            print("\n(interrupted)")
        if choice != "6":
            _pause()
    return 0
