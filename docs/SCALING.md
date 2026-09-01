# Scaling and hardware profiles

Lumen is **open source and hardware-agnostic**. The GTX 1650 lab is our **reference profile** — where we prove the orchestration idea on modest hardware — not a ceiling for the project.

## Design principle

| Layer | Scoped to lab? | What scales |
|-------|----------------|-------------|
| **Orchestration logic** (route, bench, compare) | No | Any GPU/CPU; probe + config |
| **Reference numbers** (`48.38` tok/s, `70.02` mean) | Yes | CI regression on reference rig only |
| **Default tier models** | Tunable | Contributors swap faster/larger models |
| **Soup train configs** | Per profile | `max_length`, stream_layers, quant per VRAM class |
| **Windows deploy scripts** | Optional | Linux `scripts/` path is portable |

**Rule:** Tune defaults using the reference lab; **never hardcode** lab paths, IPs, or tok/s in shared routing logic.

## Hardware classes (informal)

Lumen does not require a fixed taxonomy yet. Use these for docs and future auto-tuning:

| Class | VRAM | Typical behavior |
|-------|------|------------------|
| `low` | ≤ 6 GB | Reference lab: hybrid router, stream_layers train, quality 7B opt-in |
| `mid` | 8–16 GB | Resident 7B/13B, longer context, speculative decode worth re-testing |
| `high` | 24 GB+ | Larger models resident, MoE experiments, higher `max_length` training |
| `cpu_only` | — | Ollama CPU; routing still applies, absolute tok/s differ |

Contributors: run `lumen probe` (or `./scripts/probe.sh`), save `hardware.json`, bench your baseline model, set `target_improvement: 0.40` **relative to your machine**.

## Reference vs local config

```
hardware/
  reference-lab.json    ← checked in; CI / docs / regression comparison
  your-machine.json     ← gitignored; from probe on contributor box

lumen.yaml              ← YOUR tiers, YOUR baseline, YOUR paths
```

Example `lumen.yaml` (see `lumen.yaml.example`):

```yaml
hardware:
  profile: hardware.json              # your probe output
  reference_profile: hardware/reference-lab.json  # optional compare
  vram_class: auto                    # auto | low | mid | high

benchmark:
  baseline_model: llama3.2:3b         # measure on YOUR hardware
  target_improvement: 0.40            # +40% vs YOUR baseline, not ours
```

## What contributors can improve

1. **New tier models** — bench on your GPU, PR updated defaults or profile-specific overrides
2. **New hardware profiles** — add `hardware/<name>.json` + `RESULTS` snippet
3. **Portable scripts** — Linux-first `scripts/bench.sh`, `lumen.py`; Windows `deploy/` stays optional
4. **Training recipes** — `soup-*.yaml` per VRAM class (e.g. `soup-3b-mid.yaml` for 12GB)
5. **Backend plugins** — llama.cpp vs Ollama vs vLLM in [ARCHITECTURE.md](./ARCHITECTURE.md) resident path

## CI strategy (target)

| Job | Hardware | Purpose |
|-----|----------|---------|
| `reference-regression` | Reference lab (or recorded fixtures) | Router logic + +40% gate vs `48.38` baseline |
| `contributor-bench` | Optional self-hosted runners | Upload `hardware.json` + bench JSON; no fixed tok/s |
| `lint / route parity` | Any CPU | `lumen_router.py` ↔ `win-router-lib.ps1` same decisions |

We are not there yet on GitHub Actions; `deploy/win-regression.ps1` is the reference implementation.

## Paths are not universal

| Lab-specific (do not require for OSS) | Portable |
|---------------------------------------|----------|
| `D:\lumen-stream-lab` | `$LUMEN_LAB_ROOT` / repo root |
| `192.168.4.31` SSH deploy | `git clone` + local `ollama` |
| `win-*.ps1` | `lumen.py`, `scripts/*.sh` |

Set `LUMEN_LAB_ROOT` or run from repo root; see `CONTRIBUTING.md`.

## Open-source goal

Ship a **router + bench + train playbook** that anyone can run on their stack. The reference lab proves it works on a $0 marginal-cost GPU; contributors with 24GB+ cards should beat our absolute tok/s while using the same orchestration rules.

See also: [CONTRIBUTING.md](../CONTRIBUTING.md), [VISION.md](./VISION.md), [benchmarks/PROTOCOL.md](../benchmarks/PROTOCOL.md).
