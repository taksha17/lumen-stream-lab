# Contributing to Lumen Stream Lab

Thanks for helping scale this beyond one laptop. The reference GTX 1650 rig validates the idea; **your hardware makes the project better**.

## Quick start (any machine)

```bash
git clone <repo-url>
cd lumen-stream-lab

# 1. Profile YOUR hardware (not the lab's)
./scripts/probe.sh          # or: python3 lumen.py probe
# → writes hardware.json (gitignore this if it contains paths you care about)

# 2. Bench YOUR baseline
./scripts/bench.sh --backend ollama --model llama3.2:3b
# Record median tok/s in results/ or open a PR with hardware/<your-id>.json

# 3. Copy config template
cp lumen.yaml.example lumen.yaml
# Edit tiers and paths for your environment

# 4. Test routing (no GPU required for logic)
python3 lumen.py route --prompt "Explain TCP vs UDP"
```

Windows reference-lab scripts live under `deploy/` — optional, not required for contributions.

## What to contribute

| Area | How |
|------|-----|
| **Hardware profile** | Add `hardware/<name>.json` with probed specs + measured baselines |
| **Faster tier model** | Bench on your GPU; update `lumen.yaml.example` or document in `RESULTS.md` |
| **Router rules** | Edit `lumen_router.py` **and** `deploy/win-router-lib.ps1` (must stay in sync) |
| **Training recipe** | New `soup-*-<vram-class>.yaml` with documented VRAM peak |
| **Portable tooling** | Prefer `scripts/` + `lumen.py` over Windows-only paths |
| **Docs** | `SCALING.md`, `PLAYBOOK.md`, benchmark notes |

## Pull request checklist

- [ ] Routing changes mirrored in **Python + PowerShell** (`lumen_router.py`, `win-router-lib.ps1`)
- [ ] No hardcoded `D:\`, server IP, or lab-only tok/s in shared logic
- [ ] Baselines documented as **reference** or **profile-specific**, not global truth
- [ ] If changing reference regression: run `win-regression.ps1` on reference lab or explain why N/A
- [ ] `AGENTS.md` updated if workflow or paths change

## Hardware profiles

- **Reference:** `hardware/reference-lab.json` — GTX 1650, `48.38` / `70.02` tok/s numbers
- **Yours:** probe locally; optional PR with anonymized profile for the model zoo / docs

Do not expect the same model names to fit all GPUs. A 24GB contributor might use resident `qwen2.5:7b` for balanced and skip LFM entirely — that's valid; document the profile.

## Training on larger GPUs

Reference lab constraints (4GB) are documented in `AGENTS.md` §GTX 1650 — they are **one data point**:

| Constraint | Reference lab | Larger GPU |
|------------|---------------|------------|
| `max_length: 64` | Required for 7B stream | Try 128–512 |
| `quantization: none` | Turing BF16 issue | May use 4bit on newer cards |
| `stream_layers` | Required for 7B train | May train resident |
| Quality tier auto | Off by default (10 tok/s) | May auto-route more often |

Add a new yaml per class; don't remove the 4GB recipe — it's our accessibility baseline.

## Code of conduct

Be kind. Prefer measured benchmarks over claims. Negative results belong in `RESULTS.md`.

## Questions

Open an issue with your `hardware.json` (redact paths) and baseline bench JSON. We'll help tune tiers for your class.
