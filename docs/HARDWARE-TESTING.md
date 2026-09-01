# Hardware testing & contributor call

Lumen is **open source and hardware-agnostic**. Our reference lab is a **minimum-viable CI rig** — not the ceiling for the project. This doc explains what we can prove on 4GB, what we cannot, and **how to contribute results from stronger hardware**.

---

## Reference lab (what we test on today)

| Spec | Value |
|------|-------|
| CPU | AMD Ryzen 5 5600H (6C/12T) |
| RAM | 16 GB |
| GPU | NVIDIA GeForce GTX 1650 Mobile |
| VRAM | **4 GB** |
| Disk | NVMe (~150 GB free) |
| OS | Windows 11 (bench server), Linux (dev) |

Profile file: [`hardware/reference-lab.json`](../hardware/reference-lab.json)

---

## What the reference lab CAN prove

| Capability | Status | Evidence |
|------------|--------|----------|
| Hybrid routing logic (12/12 prompts) | **Proven** | Router eval, CI tests |
| +40% mean vs always-3B | **Proven** | ~70 tok/s vs 48.38 baseline |
| Domain smoke (E11/E12/E05) | **Proven** | System prompt + S07 model |
| Soup 7B/3B train on 4GB (`stream_layers`) | **Proven** | S05–S07 |
| Ollama as default resident backend | **Proven** | ~49 vs ~17 tok/s vs llama.cpp |
| Portable CLI / gateway / menu | **Proven** | `lumen.py`, `lumen_gateway.py` |
| Open-source contributor path | **Proven** | docs, CI, no server IP required |

---

## What the reference lab CANNOT prove (we need you)

| Gap | Why 4GB blocks it | What we need from contributors |
|-----|-------------------|-------------------------------|
| **Resident 7B/13B as balanced tier** | 7B runs ~10 tok/s; OOM if auto-routed | 8–24 GB GPU: bench resident 7B/8B as default balanced |
| **Long-context training** | `max_length: 64` only on 7B stream | 12GB+: `max_length` 128–512 recipes |
| **4-bit QLoRA on 7B** | Turing BF16 amp crash | Ampere+ : QLoRA bench + yaml |
| **Speculative decode at scale** | ~1% gain on 3B here | Faster GPU: draft 1B + verify 7B/13B |
| **MoE / Colibri speed path** | Not enough VRAM for meaningful MoE | 24GB+: expert streaming benchmarks |
| **llama.cpp vs Ollama winner** | Ollama wins here; may flip elsewhere | Re-run shootout on your card |
| **Higher absolute tok/s ceiling** | 1650 caps ~110 tok/s (1B) | RTX 3090/4090, Apple M-series, etc. |
| **Production load (batch/concurrency)** | Single-user laptop benches | Multi-GPU / vLLM contributor |

---

## VRAM class matrix (informal)

| Class | VRAM | Reference | Expected contributor wins |
|-------|------|-----------|---------------------------|
| `low` | ≤ 6 GB | **This lab** | Hybrid router, stream_layers train, quality opt-in |
| `mid` | 8–16 GB | — | Resident 7B balanced, longer context, better speculation |
| `high` | 24 GB+ | — | Larger models, MoE experiments, batch serving |
| `cpu_only` | — | — | Routing logic still valid; document CPU tok/s |

Set `vram_class` in `lumen.yaml` — see `lumen.yaml.example`.

---

## Known reference-lab limitations (hard numbers)

From Soup training and inference on GTX 1650:

| Constraint | Value | Symptom if violated |
|------------|-------|---------------------|
| `max_length` (7B stream) | 64 | OOM at step 0 |
| `max_length` (3B stream) | 64 stable; 96 smoke fits | Quality regression at 96 full train |
| `quantization` | `none` | BF16 amp crash with 4-bit QLoRA |
| `stream_layers` | required for 7B train | Cannot resident-train 7B |
| 7B inference via Soup chat | fails | Use Ollama GGUF instead |
| Quality tier auto-route | off by default | ~10 tok/s kills orchestration mean |
| Thermal / power | laptop TDP | Sustained vs burst tok/s differ |

---

## Contributor call: test on better hardware

We are actively looking for collaborators who can run Lumen on **stronger GPUs** and publish reproducible profiles.

### What to run (30–60 minutes)

```bash
git clone https://github.com/taksha17/lumen-stream-lab.git
cd lumen-stream-lab

python3 lumen.py              # option 1: setup check
python3 lumen.py probe          # writes hardware.json

# Pull models — see docs/MODELS.md
ollama pull llama3.2:1b
ollama pull llama3.2:3b

# Baseline + orchestration (if you have full tier models)
python3 lumen.py bench --model llama3.2:3b
powershell -File deploy/win-regression.ps1   # Windows only, or manual benches

# Backend shootout
python3 scripts/bench_backends.py --backend ollama --model llama3.2:3b
# + llamacpp if you have llama-cli and GGUF path
```

### What to submit (open a PR or issue)

1. **`hardware/<your-id>.json`** — anonymized specs + measured baselines:

```json
{
  "id": "contributor-rtx4090",
  "role": "contributor",
  "gpu": "NVIDIA RTX 4090",
  "vram_gb": 24,
  "measured_baselines": {
    "llama3.2:3b_tok_s": 0,
    "orchestration_mean_tok_s": 0,
    "orchestration_gain_pct": 0
  },
  "recommended_tiers": {
    "balanced": "your-model-here"
  },
  "notes": "Optional: what you changed vs reference defaults"
}
```

2. **Bench JSON** (optional) — attach sanitized `results/bench-*.json` or paste medians in the issue.

3. **Tier recommendations** — if LFM is not best on your GPU, document the faster balanced model.

### Good first contributor issues

- Label: `hardware-profile`, `help wanted`
- "I have a 12GB GPU — here's my orchestration mean"
- "llama.cpp beats Ollama on AMD RX 7900 XTX"
- "Resident 7B as balanced tier on 24GB — config + numbers"

We will **not** merge profile-specific tok/s into shared routing logic — only into `hardware/*` and docs.

---

## CI vs physical hardware

| Job | Runs on | Purpose |
|-----|---------|---------|
| GitHub Actions `ci.yml` | Ubuntu CPU | Router parity, CLI smoke |
| `win-regression.ps1` | Reference lab (manual) | +40% + domain gate |
| Future: self-hosted runner | Your GPU | Live regression upload |

Until self-hosted CI exists, **reference numbers live in fixtures** — contributors compare locally.

---

## Questions?

Open a [GitHub issue](https://github.com/taksha17/lumen-stream-lab/issues/new/choose) with:

- `hardware.json` (redact paths)
- GPU model + VRAM
- Median tok/s for baseline and orchestration (if run)
- What you'd like to help validate

See also [CONTRIBUTING.md](../CONTRIBUTING.md).
