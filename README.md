# Lumen Stream Lab

> **Orchestrate Soup, AirLLM, and Colibri — measure everything — beat always-3B by ≥40% decode tok/s via hybrid routing.**

Open-source orchestration playbook. We **tune and CI-test on a reference lab** (GTX 1650 4GB) but the tool is **not limited to that hardware** — contributors with stronger GPUs should probe locally, set their own baselines, and PR better tier defaults. See [**SCALING.md**](./SCALING.md) and [**CONTRIBUTING.md**](./CONTRIBUTING.md).

## Status (2026-08-31)

| Metric | Result |
|--------|--------|
| Baseline | `llama3.2:3b` @ **48.38 tok/s** (always one model) |
| **Lumen hybrid orchestration** | **68.03 tok/s** mean (**+40.6% PASS**) |
| Router | 1B fast / LFM general / qwen domain / 7B opt-in |

## Hybrid router tiers

| Tier | Model | When |
|------|-------|------|
| `fast` | `llama3.2:1b` | Arithmetic, greetings, short facts |
| `balanced` | `lfm-balanced` | General explain/coding (~65 tok/s) |
| `balanced` (domain) | `qwen2.5-3b-lumen` | Lumen Stream Lab / Soup / routing keywords |
| `quality` | `qwen2.5-7b-lumen` | Prompt >50 words or `-Tier quality` |

## Reference lab (optional — our CI rig)

The numbers below are from `hardware/reference-lab.json`. Your machine will differ; run `python3 lumen.py probe` and bench your own baseline.

### Windows reference server (`192.168.4.31`, `D:\lumen-stream-lab`)

```powershell
. D:\lumen-stream-lab\deploy\win-env-d.ps1

# Route a prompt
.\deploy\win-route.ps1 -Prompt "What is Lumen Stream Lab?"

# Regression gate (speed + domain smoke)
powershell -File D:\lumen-stream-lab\deploy\win-regression.ps1

# Full gate including router quality eval (~30 min)
powershell -File D:\lumen-stream-lab\deploy\win-regression.ps1 -Full
```

## Any machine (portable path)

```bash
git clone <repo-url> && cd lumen-stream-lab

# Profile YOUR hardware (writes hardware.json)
python3 lumen.py probe

# Hybrid routing plan (JSON) — logic is GPU-agnostic
python3 lumen.py route --prompt "Explain TCP vs UDP"

# +40% check vs YOUR baseline (reference lab example: 48.38 → 68.03)
python3 scripts/compare.py --baseline <your-3b-tok-s> --optimized <your-orchestration-mean> --min-gain 0.40
```

Copy `lumen.yaml.example` → `lumen.yaml` and set `hardware.profile`, tiers, and paths for your environment.

## Documentation

| File | Contents |
|------|----------|
| [**RESULTS.md**](./RESULTS.md) | Benchmark log (+40% PASS) |
| [**VISION.md**](./VISION.md) | Goal and strategy |
| [**ARCHITECTURE.md**](./ARCHITECTURE.md) | Orchestrator design |
| [**PLAYBOOK.md**](./PLAYBOOK.md) | Soup / AirLLM / Colibri limits |
| [**benchmarks/PROTOCOL.md**](./benchmarks/PROTOCOL.md) | Fair measurement rules |
| [**SCALING.md**](./SCALING.md) | Hardware profiles, OSS scaling model |
| [**CONTRIBUTING.md**](./CONTRIBUTING.md) | How to contribute benches and profiles |
| [**hardware/reference-lab.json**](./hardware/reference-lab.json) | Reference CI rig (not a global default) |

## Key idea

**Streaming fits oversized models — it does not speed up models that already fit in VRAM.**

Lumen wins by routing each prompt to the right model size (1B / LFM / fine-tuned 3B / 7B), not by making one 3B kernel 40% faster.

Soup: **train** → export GGUF → Lumen **serves** via hybrid router.
