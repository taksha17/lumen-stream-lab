# Contributing to Lumen Stream Lab

Thanks for helping scale this beyond one laptop. The reference GTX 1650 rig validates the idea on **minimum hardware**; **your GPU makes the project better**.

**Read first:**

| Doc | Why |
|-----|-----|
| [docs/README.md](./docs/README.md) | Documentation index |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | How the system fits together |
| [docs/REFERENCE-RESULTS.md](./docs/REFERENCE-RESULTS.md) | What we have proven so far |
| [docs/HARDWARE-TESTING.md](./docs/HARDWARE-TESTING.md) | **What we cannot test — we need you** |
| [docs/ENTERPRISE-CASE-STUDY.md](./docs/ENTERPRISE-CASE-STUDY.md) | Real-world enterprise narrative |
| [docs/MODELS.md](./docs/MODELS.md) | Model setup |

---

## We are looking for collaborators

Especially if you have:

| Hardware | What we'd love from you |
|----------|-------------------------|
| **8–12 GB** (RTX 3060/4060, etc.) | Resident 7B as balanced tier, longer Soup `max_length` |
| **16–24 GB** (3090, 4090, A5000) | Higher orchestration ceiling, speculation benchmarks |
| **Apple Silicon** | Ollama vs mlx backend shootout |
| **AMD GPU** | ROCm/Ollama tier recommendations |
| **CPU-only server** | Routing + CPU inference baselines |

Open an issue with label `hardware-profile` or PR `hardware/<your-id>.json`. Template in [HARDWARE-TESTING.md](./docs/HARDWARE-TESTING.md).

---

## Quick start (any machine)

```bash
git clone https://github.com/taksha17/lumen-stream-lab.git
cd lumen-stream-lab

# Interactive UI (recommended)
python3 lumen.py

# Or step by step:
python3 lumen.py probe              # hardware.json (gitignored)
python3 lumen.py                    # menu → setup check
cp lumen.yaml.example lumen.yaml    # edit tiers for your box
```

See [docs/MODELS.md](./docs/MODELS.md) for `ollama pull` commands.

---

## Contribution areas

| Area | How | Priority |
|------|-----|----------|
| **Hardware profile** | `hardware/<name>.json` + bench medians | **High** — we need mid/high VRAM data |
| **Backend shootout** | `scripts/bench_backends.py` on your GPU | High |
| **Faster tier model** | Bench + update `lumen.yaml.example` or profile | Medium |
| **Router rules** | `lumen_router.py` **and** `deploy/win-router-lib.ps1` | Medium |
| **Training recipe** | `soup-*-<vram-class>.yaml` | Medium |
| **Docs / diagrams** | `docs/` | Always welcome |
| **Gateway / menu UX** | `lumen_menu.py`, `lumen_gateway.py` | Medium |

---

## Pull request checklist

- [ ] Routing changes mirrored in **Python + PowerShell** (`lumen_router.py`, `win-router-lib.ps1`)
- [ ] `python3 -m unittest discover -s tests -v` passes
- [ ] No hardcoded server IPs, `D:\` paths, or lab-only tok/s in shared logic
- [ ] Baselines labeled **reference-lab** vs **profile-specific** in docs
- [ ] If reference regression affected: note in PR or run `win-regression.ps1`
- [ ] `AGENTS.md` updated if agent workflow changes

---

## Hardware profiles

### Reference (CI / docs only)

[`hardware/reference-lab.json`](./hardware/reference-lab.json) — GTX 1650, 48.38 → 70.02 tok/s orchestration.

### Contributor (you add these)

```json
{
  "id": "contributor-example",
  "role": "contributor",
  "gpu": "NVIDIA RTX 4090",
  "vram_gb": 24,
  "measured_baselines": {
    "llama3.2:3b_tok_s": 0,
    "orchestration_mean_tok_s": 0,
    "orchestration_gain_pct": 0
  },
  "recommended_tiers": {
    "balanced": "your-best-model"
  },
  "notes": "Optional"
}
```

Do **not** change global router defaults to match your box only — add a profile and document in `docs/REFERENCE-RESULTS.md` or a new `docs/profiles/<name>.md`.

---

## Training on larger GPUs

Reference lab constraints are **one data point** (4GB Turing):

| Constraint | Reference lab | Your GPU |
|------------|---------------|----------|
| `max_length: 64` | Required for 7B stream | Try 128–512 |
| `quantization: none` | BF16 amp issue on Turing | Try 4bit on Ampere+ |
| `stream_layers` | Required for 7B train | May train resident |
| Quality auto-route | Off (10 tok/s) | May enable on 24GB+ |

Add new yaml; keep 4GB recipes for accessibility.

---

## Benchmark protocol

Follow [benchmarks/PROTOCOL.md](./benchmarks/PROTOCOL.md):

- `num_predict = 128` for comparability
- Report **median** of 5 runs after 2 warmup
- Use API `eval_duration` decode rate when possible
- Negative results welcome in `RESULTS.md`

---

## Code of conduct

Be kind. Prefer measured benchmarks over claims. Disagree with data.

---

## Questions

- [GitHub Issues](https://github.com/taksha17/lumen-stream-lab/issues/new/choose)
- Include redacted `hardware.json` and median tok/s
- Say what hardware class you represent (`low` / `mid` / `high`)

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](./LICENSE).
