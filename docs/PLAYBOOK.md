# Lumen Stream Lab — Local LLM Playbook

> **Fine-tune, stream, and run large models on modest hardware.**  
> A practical guide for the server laptop test rig and the Soup / AirLLM / Colibri ecosystem.

---

## Table of contents

1. [Hardware profile](#hardware-profile)
2. [The three tools at a glance](#the-three-tools-at-a-glance)
3. [What works on this machine](#what-works-on-this-machine)
4. [Training vs inference token speed](#training-vs-inference-token-speed)
5. [Theoretical speeds (unified combo)](#theoretical-speeds-unified-combo)
6. [Disk compression and I/O tricks](#disk-compression-and-io-tricks)
7. [Bottleneck decision tree](#bottleneck-decision-tree)
8. [Concrete test plans](#concrete-test-plans)
9. [Setup commands](#setup-commands)
10. [Open research directions](#open-research-directions)
11. [References](#references)

---

## Hardware profile

| Component | Spec | Role |
|-----------|------|------|
| **CPU** | AMD Ryzen 5 5600H (6C / 12T) | Prefetch, tokenization, CPU inference paths |
| **RAM** | 16 GB DDR4-2666 (~42 GB/s theoretical) | Layer / dense weight store for streaming |
| **Storage** | ~150 GB free NVMe (~1.5 GB/s read) | Model weights; Colibri disk tier |
| **GPU** | NVIDIA GTX 1650 Mobile, 4 GB VRAM | CUDA compute; Soup's design target |

### Hard limits

- **VRAM (4 GB)** — batch size 1, seq ~512 for 8B; no Tensor Cores on most 1650 Mobile SKUs
- **RAM (16 GB)** — tight for large models; close other apps during training
- **Disk (150 GB)** — blocks frontier Colibri models (372 GB–1.6 TB)
- **PCIe 3.0 ×8** — ~6–7 GB/s RAM → GPU; often the real cap for layer streaming

---

## The three tools at a glance

| | [Soup](https://github.com/MakazhanAlpamys/Soup) | [AirLLM](https://github.com/lyogavin/airllm) | [Colibri](https://github.com/JustVugg/colibri) |
|---|---|---|---|
| **Primary job** | Fine-tune / post-train LLMs | Run inference on huge dense models | Run frontier MoE inference |
| **Stars** | ~4k | ~33k | ~26k |
| **Stack** | Python (PyTorch) | Python (PyTorch) | Pure C engine + Python launcher |
| **VRAM trick** | Layer streaming during **training** | One layer on GPU at a time (**inference**) | Experts streamed across VRAM / RAM / NVMe |
| **Typical entry** | `soup train --config soup.yaml` | `AutoModel.from_pretrained(...).generate()` | `COLI_MODEL=... ./coli chat` |
| **GPU required?** | Yes for practical training | Yes (CUDA / MPS) | No (GPU optional for speed) |

### How they relate

```
┌─────────────────────────────────────────────────────────┐
│  TRAINING — adapt a model to your data                  │
│  → Soup (layer streaming + QLoRA + YAML pipeline)       │
└─────────────────────────────────────────────────────────┘
                          ↓ export / merge / GGUF
┌─────────────────────────────────────────────────────────┐
│  INFERENCE — run a model                                │
│  → AirLLM: any HF model, layer-at-a-time                │
│  → Colibri: frontier MoE, expert-at-a-time              │
│  → Ollama / llama.cpp: small resident models (fastest)  │
└─────────────────────────────────────────────────────────┘
```

### Shared insight

All three solve: **model weights ≫ GPU VRAM**.

The fix is the same idea applied differently:

- **Soup** — stream **layers** during training (forward + backward)
- **AirLLM** — stream **layers** during inference
- **Colibri** — stream **experts** during inference (MoE sparsity)

Colibri is already the low-level implementation for inference I/O. Soup owns the training loop. AirLLM is the generic Hugging Face inference wrapper.

---

## What works on this machine

### With GTX 1650 4 GB (current config)

```
┌─────────────────────────────────────────────────────────────┐
│  STRONG FIT                                                 │
│  • Soup: fine-tune 7–8B with stream_layers + 4bit           │
│  • Ollama / llama.cpp: 7B Q4 chat (~12–30 tok/s)            │
│  • AirLLM: 7–8B inference experiments                       │
├─────────────────────────────────────────────────────────────┤
│  WORKABLE                                                   │
│  • AirLLM 13–32B (slow, 1–4 tok/s)                          │
│  • Colibri OLMoE (~7 GB) or Qwen3.6 (~20 GB)                │
│  • Soup DPO / ORPO on 8B (layer streaming, v0.72.4+)       │
├─────────────────────────────────────────────────────────────┤
│  NOT VIABLE                                                 │
│  • Colibri GLM-5.2 / Kimi K3 (disk: 372 GB–1.6 TB)          │
│  • AirLLM 70B (disk ~140 GB+ and very slow)                 │
│  • Full fine-tune (non-LoRA) of 8B+ on 4 GB VRAM            │
└─────────────────────────────────────────────────────────────┘
```

### Per-tool viability

#### Soup

| Use case | Viable? | Notes |
|----------|---------|-------|
| `soup init`, data tools, configs | ✅ | Light install, no GPU |
| `soup train` 8B LoRA | ✅ | `stream_layers: true`, `quantization: 4bit` |
| Layer streaming headline | ✅ | ~3.3 GB peak VRAM (RTX 3050 ref.; 1650 ~60–70% speed) |
| CPU-only training | ❌ | Impractical; quantization auto-disabled |

#### AirLLM

| Model | Disk | Speed (rough, 1650) |
|-------|------|---------------------|
| 7–8B 4-bit | ~5–8 GB ✅ | 4–12 tok/s |
| 13–32B | ~15–40 GB ✅ | 1–4 tok/s |
| 70B | ~140 GB+ ⚠️ | 0.3–1.5 tok/s |

#### Colibri

| Model | Disk | Fits 150 GB? |
|-------|------|--------------|
| OLMoE | ~7 GB | ✅ |
| Qwen3.6 | ~20 GB | ✅ |
| DeepSeek V4 Flash | ~167 GB | ⚠️ Barely |
| GLM-5.2 | ~372 GB | ❌ |
| Kimi K3 | ~1.6 TB | ❌ |

### The pick-two triangle

You cannot have all three at once on weak hardware:

```
        Good speed
           /\
          /  \
         /    \
        /______\
   Frontier    Low hardware
```

**Frontier + low hardware** works only with **sparsity** (MoE) — and even then Colibri's honest cold floor on a small box is **0.05–0.1 tok/s**.

---

## Training vs inference token speed

### Inference (chat)

**Token speed** = how fast the model produces **output tokens** you see in the reply (tokens per second during **decode**).

| Metric | Meaning |
|--------|---------|
| **Decode tok/s** | Steady generation speed — what we quote in tables |
| **TTFT** | Time to first token (prefill) — can be slow even when decode is fine |

### Training (Soup)

**Token speed** = training throughput: tokens processed per second including **forward + backward**. Not the same as chat speed.

| Workload | Relative speed |
|----------|----------------|
| SFT LoRA | Baseline |
| DPO / ORPO | ~½× SFT (reference pass reads layers again) |

---

## Theoretical speeds (unified combo)

A hypothetical stack combining Colibri I/O + AirLLM layer streaming + Soup streamed LoRA on **this laptop**.

### Bandwidth ceiling (layer-streamed dense)

```
tokens/sec ≈ PCIe_bandwidth / bytes_moved_per_token
```

PCIe 3.0 ×8 ≈ **6–7 GB/s** RAM → GPU.

| Model | ~4-bit size | Layers | Bytes/token (all layers) | I/O-only ceiling |
|-------|-------------|--------|--------------------------|------------------|
| 8B | ~4 GB | 32 | ~4 GB | ~1.5–2 tok/s (zero overlap) |
| 13B | ~7 GB | 40 | ~7 GB | ~0.8–1 tok/s |
| 70B | ~35 GB | 80 | ~35 GB | ~0.15–0.2 tok/s |

A perfect unified engine (C I/O, double-buffer, prefetch) might recover **3–8×** via overlap — not 100×.

### Inference (decode tok/s) — hypothetical combo

| Setup | Model | Range | Bottleneck |
|-------|-------|-------|------------|
| Resident on GPU | 3B Q4 | 25–50 tok/s | VRAM, KV cache |
| Resident on GPU | 7B Q4 | 12–30 tok/s | 4 GB tight |
| Layer stream + prefetch | 8B 4-bit | 4–12 tok/s | PCIe + 1650 |
| Optimistic unified combo | 8B 4-bit | 6–15 tok/s | ~20–30% over AirLLM alone |
| Layer stream | 13–32B | 1–4 tok/s | RAM + PCIe |
| Layer stream | 70B | 0.3–1.5 tok/s | Disk + I/O |
| Expert stream (Colibri) | OLMoE 7B | 2–8 tok/s | Disk cold → low; warm cache → higher |
| Expert stream | Qwen3.6 | 3–12 tok/s | ~3B active/token; VRAM tier helps |

*Soup reference: **119.6 tok/s** training on RTX 3050 4 GB. GTX 1650 Mobile ≈ **50–65%** of that compute.*

### Training (tok/s) — hypothetical combo

| Setup | Model | Range |
|-------|-------|-------|
| Soup layer stream + 4-bit LoRA | 8B | 40–85 tok/s |
| + unified C prefetch (hypothetical) | 8B | 50–100 tok/s |
| Streamed DPO / ORPO | 8B | 25–50 tok/s |
| Hypothetical MoE expert LoRA | 30B+ MoE | 5–20 tok/s (unproven) |

### Where time goes (8B layer-streamed inference)

```
One generated token:

  PCIe / RAM load layers  ████████████████░░░░  ~55–70%  ← combo optimizes here
  GPU matmul (1650)       ██████░░░░░░░░░░░░░░  ~20–30%
  CPU (router, decode)    ██░░░░░░░░░░░░░░░░░░  ~5–10%
  Python / overhead       █░░░░░░░░░░░░░░░░░░░  ~5–15%  ← C engine removes most
```

### Combo vs tools alone (8B inference)

| Layer | Alone | In combo | Why |
|-------|-------|----------|-----|
| AirLLM | 4–10 tok/s | — | Python + shard load |
| + Colibri C I/O | — | +20–40% | `O_DIRECT`, prefetch, batch-union |
| + MoE sparsity | — | +2–5× vs dense | Fewer active weights/token |
| + Speculative decode | — | +1.5–2.5× when acceptance high | MTP / draft head |
| + Shared weight format | — | +10–20% | No double split |

**Realistic on this laptop:** 8B inference **~6–12 tok/s**; 8B LoRA training **~45–80 tok/s**.

---

## Disk compression and I/O tricks

### The idea

Halve bytes on disk → halve read time → higher effective MB/s → better tok/s **when disk-bound**.

```
Effective throughput = min(
    disk_read_speed × compression_ratio,
    CPU_decompress_speed,
    GPU_compute_speed
)
```

### What already does this

| Format | Size vs FP16 | Effective I/O gain |
|--------|--------------|-------------------|
| FP16 | 1× | baseline |
| INT8 | ~½× | ~2× |
| INT4 (Q4 / NF4) | ~¼× | ~4× |
| Colibri int4-gs64 | ~¼× + tuned layout | ~4× + better prefetch |

AirLLM `compression='4bit'`, Colibri int4, Ollama Q4 — **already the "half size, double speed" play.**

Extra zstd/lz4 on top of int4 weights: often only **~10–30%** (weights are high-entropy).

### When extra compression helps

| Situation | Helps? |
|-----------|--------|
| Weights still FP16 on disk | ✅ **Quantize first** — biggest win |
| int4 + disk-bound (Colibri cold) | Maybe +10–30% with lz4/zstd-1 |
| Model mostly in RAM/VRAM | ❌ Disk irrelevant |
| 8B on 1650 layer-stream from RAM | ❌ PCIe caps you, not NVMe |

### Optimization priority (this machine)

```
150 GB NVMe @ ~1.5 GB/s
    │
    ├─► Quantize to int4 (biggest win)
    ├─► Pin hot experts/layers in 16 GB RAM
    ├─► Cache hottest weights in 4 GB VRAM
    └─► Optional: lz4/zstd-1 on shards (small extra if still disk-bound)
```

---

## Bottleneck decision tree

### Step 0 — Pick model + tool

| Goal | Model | Tool |
|------|-------|------|
| **A. Fast chat baseline** | Llama-3.2-3B or Mistral-7B Q4 | Ollama / llama.cpp |
| **B. 8B fine-tune** | Qwen2.5-7B or Llama-3.1-8B | Soup |
| **C. Streaming inference** | Qwen2.5-7B 4-bit | AirLLM |
| **D. MoE streaming** | OLMoE or Qwen3.6 | Colibri |

**Order:** A (baseline) → then B or C.

### Step 1 — Measure

```bash
# GPU visible?
nvidia-smi

# PyTorch sees CUDA?
python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# Soup environment
soup doctor

# Colibri readiness
COLI_MODEL=/path/to/model ./coli doctor
COLI_MODEL=/path/to/model ./coli plan
```

### Step 2 — Classify bottleneck

```
                    RUN timed generation / training step
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            GPU util high (>80%)              GPU util low (<50%)
            during generation                   during generation
                    │                               │
                    ▼                               ▼
            COMPUTE-BOUND                    I/O or CPU-BOUND
                    │                               │
        ┌───────────┼───────────┐       ┌───────────┼───────────┐
        ▼           ▼           ▼       ▼           ▼           ▼
   Smaller      Speculative   Accept   Disk      RAM/PCIe    CPU decode
   quant (Q4)   decoding      slower   bound     bound       bound
   or model     (MTP)         speed    │         │
                                       ▼         ▼
                                  int4 +     pin in RAM
                                  prefetch   + VRAM tier
                                  O_DIRECT   layer stream
                                  hot cache  overlap
```

| Symptom | Likely bottleneck | Fix (in order) |
|---------|-------------------|----------------|
| `nvidia-smi` GPU 90%+, disk idle | **GPU compute** | Smaller model / Q4 / shorter context |
| GPU 20–40%, disk 100% | **Disk I/O** | int4 weights, warm cache, `O_DIRECT`, dual SSD |
| GPU low, RAM bandwidth high | **PCIe / RAM** | Pin dense in RAM; VRAM tier; smaller model |
| First token slow, rest OK | **Prefill (TTFT)** | Shorter prompt, smaller model, KV tricks |
| Gets faster over time | **Cold cache** | Keep running; Colibri `.coli_usage` learning |
| Training loss OK but slow | **Training I/O** | `stream_layers`, 4-bit, batch 1, close apps |

### Step 3 — Apply fixes by goal

#### A. Fast chat (Ollama baseline)

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Pull and run
ollama pull llama3.2:3b
ollama run llama3.2:3b

# Expect: 25–50 tok/s (3B) or 12–25 tok/s (7B Q4) on 1650
```

If this is already slow → driver / GPU issue, not streaming.

#### B. Soup 8B fine-tune

```yaml
# soup.yaml
base: Qwen/Qwen2.5-7B-Instruct
task: sft

data:
  train: ./data/train.jsonl
  format: alpaca

training:
  stream_layers: true
  quantization: 4bit
  batch_size: 1
  epochs: 1
  lora:
    r: 16
    alpha: 32

output: ./output
```

```bash
pip install "soup-cli[train]"
soup doctor
soup train --config soup.yaml
```

Watch `nvidia-smi` during step 1. Expect **40–85 tok/s** training throughput.

#### C. AirLLM 7B inference

```python
from airllm import AutoModel

model = AutoModel.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    compression="4bit",
    profiling_mode=True,  # shows where time goes
)

# ... generate as usual
```

If profiling shows load >> compute → prefetch / RAM pin helps.  
If compute dominates → AirLLM won't beat resident Ollama for 7B.

#### D. Colibri OLMoE

```bash
# After build + model download
COLI_MODEL=/path/to/olmoe ./coli doctor
COLI_MODEL=/path/to/olmoe ./coli plan
COLI_MODEL=/path/to/olmoe ./coli chat

# Warm up 10+ turns, compare cold vs warm tok/s
```

### Step 4 — Record results

| Run | Tool | Model | Cold tok/s | Warm tok/s | GPU % | Disk MB/s | Notes |
|-----|------|-------|------------|------------|-------|-----------|-------|
| 1 | Ollama | llama3.2:3b | | | | | baseline |
| 2 | Soup | Qwen2.5-7B | | | | | training tok/s |
| 3 | AirLLM | Qwen2.5-7B | | | | | profiling_mode |
| 4 | Colibri | OLMoE | | | | | cold vs warm |

---

## Concrete test plans

### Plan 1 — Baseline day (2 hours)

1. Verify CUDA: `nvidia-smi`, PyTorch CUDA check
2. Ollama `llama3.2:3b` — record tok/s
3. Ollama `mistral:7b-instruct-q4_0` — record tok/s
4. **You now know the GPU ceiling for resident small models**

### Plan 2 — Soup fine-tune day (half day)

1. `pip install "soup-cli[train]"`
2. `soup init --template chat`
3. Add `stream_layers: true`, `quantization: 4bit`
4. Tiny dataset (100 rows), 1 epoch
5. Record training tok/s + peak VRAM from `nvidia-smi`

### Plan 3 — Streaming compare day (full day)

1. AirLLM 7B with `profiling_mode=True`
2. Colibri OLMoE cold → warm comparison
3. Fill bottleneck table above
4. Decide: resident (Ollama) vs stream (AirLLM) vs expert stream (Colibri)

---

## Setup commands

### CUDA + PyTorch (Soup / AirLLM)

```bash
# Check driver
nvidia-smi

# PyTorch with CUDA 12.1 (adjust to your driver)
pip install torch --index-url https://download.pytorch.org/whl/cu121

python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

### Soup

```bash
pip install "soup-cli[train]"
soup doctor
soup init --template chat
```

### AirLLM

```bash
pip install airllm bitsandbytes
```

### Colibri (OLMoE — fits 150 GB)

```bash
git clone https://github.com/JustVugg/colibri.git
cd colibri/c
./setup.sh
make -C c olmoe
```

### Ollama (fastest local chat)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
ollama run llama3.2:3b
```

---

## Open research directions

Things worth building; none are fully shipped as one stack today:

1. **Streamed LoRA on MoE** — Soup dense layers + Colibri expert I/O
2. **Distill frontier → small** — slow teacher (AirLLM/Colibri), fast student (Soup 7B)
3. **Domain expert pinning** — Colibri `.coli_usage` + LoRA on hot experts only
4. **Unified weight container** — one on-disk format for inference and training
5. **Shared C memory engine** — Colibri I/O + Soup training loop

The gap: **no unified engine does Colibri-speed inference and Soup-style streamed fine-tuning on the same weight format.**

---

## References

| Project | URL | License |
|---------|-----|---------|
| Soup | https://github.com/MakazhanAlpamys/Soup | Apache-2.0 |
| AirLLM | https://github.com/lyogavin/airllm | Apache-2.0 |
| Colibri | https://github.com/JustVugg/colibri | Apache-2.0 |
| Soup docs | https://trysoup.dev | — |
| Colibri GLM int4 weights | https://huggingface.co/mastouri/GLM-5.2-colibri-int4-g64-with-int8-mtp | — |

### Key Soup config (4 GB GPU training)

```yaml
training:
  stream_layers: true
  quantization: 4bit
  batch_size: 1
  stream_source: auto
```

### Key AirLLM init (compressed inference)

```python
model = AutoModel.from_pretrained("model-id", compression="4bit", prefetching=True)
```

### Key Colibri env

```bash
COLI_MODEL=/nvme/model ./coli plan    # inspect VRAM/RAM/disk placement
COLI_MODEL=/nvme/model ./coli doctor  # readiness check
COLI_MODEL=/nvme/model ./coli tune    # auto profile for this machine
```

---

*Lumen Stream Lab — named for streaming weights through the memory hierarchy, and for making the tradeoffs visible.*

*Last updated: August 2026 · Server laptop: Ryzen 5 5600H · 16 GB RAM · 150 GB NVMe · GTX 1650 4 GB*
