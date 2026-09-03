# Models required for Lumen hybrid routing

Lumen routes prompts across **four tiers**. You need these Ollama models (or equivalents) on your machine. GGUF weights are **not** stored in this repo.

## Quick pull (reference lab defaults)

```bash
# Stock tiers
ollama pull llama3.2:1b
ollama pull llama3.2:3b          # baseline for +40% comparison

# Balanced general (LFM 2.5-2.6B alias — see below)
ollama pull oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU

# Quality tier (optional — slow on 4GB GPUs)
ollama pull qwen2.5:7b-instruct-q4_K_M
```

**Windows reference lab:** run `deploy\win-create-lfm-alias.ps1` to create the `lfm-balanced` alias.

---

## Tier map

| Lumen tier | Ollama name | Source | Role |
|------------|-------------|--------|------|
| `fast` | `llama3.2:1b` | `ollama pull llama3.2:1b` | Short/simple prompts (~100+ tok/s on modest GPU) |
| `balanced` | `lfm-balanced` | alias → LFM 2.5-2.6B Q4 | General explain/coding (~65 tok/s ref. lab) |
| `balanced` (domain) | `qwen2.5-3b-lumen` | **fine-tuned** (see below) | Lumen/Soup/routing keywords |
| `quality` | `qwen2.5-7b-lumen` | **fine-tuned** (see below) | Long prompts or `-Tier quality` |
| `code` (experimental) | `qwen2.5-coder:3b` | `ollama pull qwen2.5-coder:3b` | Auto-route **off** unless `LUMEN_CODE_TIER=1`. Forced `--tier code` uses low-temp / concise presets ([UPGRADES.md](../UPGRADES.md)). Tune: `python3 scripts/tune_code_tier.py` |

---

## Domain models (`qwen2.5-*-lumen`)

These are **LoRA fine-tunes** trained with [Soup](https://github.com/getsoup-ai/soup) `stream_layers` on a 4GB GPU, exported to GGUF, and deployed via Ollama.

### Option A — Train your own (recommended for contributors)

1. Install Soup and set cache paths (`SOUP_LAYER_STREAM_CACHE_DIR`, `HF_HOME`).
2. Use configs in `config/soup/`: `soup-3b-stream-s07.yaml`, `soup-7b-stream-s06.yaml`.
3. Train: `soup train --config config/soup/soup-3b-stream-s07.yaml --yes`
4. Export: `soup export --model output-3b-stream-s07 --base Qwen/Qwen2.5-3B-Instruct --format gguf --quant q4_k_m`
5. Deploy:

```bash
# Modelfile example
cat > Modelfile <<'EOF'
FROM ./qwen2.5-3b-lumen.q4_k_m.gguf
PARAMETER temperature 0.7
EOF
ollama create qwen2.5-3b-lumen -f Modelfile
```

Reference scripts: `deploy/win-train-3b-s07.ps1`, `deploy/win-export-3b-s07.ps1`, `deploy/win-deploy-ollama-7b.ps1`.

### Option B — Use stock Qwen as fallback

For routing tests only (not domain quality gates):

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
# Edit lumen.yaml: balanced_domain: qwen2.5:3b-instruct-q4_K_M
```

Domain smoke tests (E11/E12) expect `qwen2.5-3b-lumen` with the system prompt in `data/domain-system-prompt.txt`.

### Option C — Download from Hugging Face (no training)

Published S07 export: **[takshathosani17/qwen2.5-3b-lumen](https://huggingface.co/takshathosani17/qwen2.5-3b-lumen)**

```bash
pip install -U "huggingface_hub[cli]"
hf download takshathosani17/qwen2.5-3b-lumen --local-dir ./qwen-lumen
cd qwen-lumen
ollama create qwen2.5-3b-lumen -f Modelfile
```

Verify domain routing: `lumen route --prompt "What is Lumen Stream Lab?"` should pick `qwen2.5-3b-lumen`.

See [HUGGINGFACE-PUBLISH.md](./HUGGINGFACE-PUBLISH.md) if you need to re-publish or update the GGUF.

### Option D — Download 7B from Hugging Face (quality tier)

After publish: **[takshathosani17/qwen2.5-7b-lumen](https://huggingface.co/takshathosani17/qwen2.5-7b-lumen)**

```bash
hf download takshathosani17/qwen2.5-7b-lumen --local-dir ./qwen-7b-lumen
cd qwen-7b-lumen && ollama create qwen2.5-7b-lumen -f Modelfile
```

Publish from reference lab: `./deploy/publish-hf-remote.sh USER/qwen2.5-7b-lumen --variant 7b`

---

## `lfm-balanced` alias

```powershell
# Windows
powershell -File deploy\win-create-lfm-alias.ps1
```

```bash
# Linux/macOS (manual)
ollama pull oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU
printf 'FROM oamazonasgabriel/lfm2.5-2.6b:q4_k_m-8gbGPU\nPARAMETER temperature 0.7\n' > /tmp/lfm.Modelfile
ollama create lfm-balanced -f /tmp/lfm.Modelfile
```

---

## Backend shootout (Ollama vs llama.cpp)

Same weights, different runtime — pick the faster resident backend per GPU.

```bash
# Portable (needs llama-cli in PATH + GGUF path)
python3 scripts/bench_backends.py --backend ollama --model llama3.2:3b
python3 scripts/bench_backends.py --backend llamacpp --gguf /path/to/model.gguf
python3 scripts/bench_backends.py --compare results/bench-ollama-last.json results/bench-llamacpp-last.json
```

```powershell
# Windows reference lab (auto-resolves Ollama blob)
powershell -File deploy\win-bench-llamacpp-vs-ollama.ps1 -Model llama3.2:3b
```

---

## Verify setup

```bash
python3 lumen.py route --prompt "What is 2+2?"
python3 lumen.py route --prompt "What is Lumen Stream Lab?"
ollama list
```

Regression gate (Windows server): `deploy\win-regression.ps1`

---

## Hardware notes

| VRAM | What fits |
|------|-----------|
| 4 GB (reference lab) | 1B/3B resident; 7B quality opt-in only; Soup train uses `stream_layers` |
| 8–16 GB | Resident 7B; may lower `quality_min_words` in `lumen.yaml` |
| 24 GB+ | Larger models, longer context; contribute a `hardware/<name>.json` profile |

See [SCALING.md](./SCALING.md) and [hardware/reference-lab.json](../hardware/reference-lab.json).
