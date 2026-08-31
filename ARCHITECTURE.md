# Architecture — Lumen Orchestration Layer

## System diagram

```
                    ┌─────────────────────────────────┐
                    │         lumen (orchestrator)     │
                    │  probe · bench · route · serve   │
                    │  hardware profile · lumen.yaml     │
                    └───────────────┬─────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
   ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
   │   RESIDENT  │          │ LAYER STREAM │          │EXPERT STREAM│
   │   (speed)   │          │  (AirLLM)    │          │  (Colibri)  │
   └──────┬──────┘          └──────┬──────┘          └──────┬──────┘
          │                         │                         │
   ┌──────┴──────┐                  │                         │
   ▼      ▼      ▼                  │                         │
 Ollama  llama  Soup                │                         │
 .cpp   serve                        │                         │
          │                         │                         │
          └────────────┬────────────┴────────────┬────────────┘
                       ▼                         ▼
              ┌─────────────────┐       ┌─────────────────┐
              │  SPEED STACK    │       │    I/O STACK      │
              │  (goal: +40%)   │       │  (fit, not speed) │
              └─────────────────┘       └─────────────────┘
```

## Hardware profiles

Orchestration logic is **not** tied to one GPU. Configuration layers:

| File | Role |
|------|------|
| `hardware.json` | Local probe output (contributor machine) |
| `hardware/reference-lab.json` | Checked-in CI reference (GTX 1650 baselines) |
| `lumen.yaml` | Tiers, paths, `target_improvement`, `vram_class` |

`vram_class` (`low` / `mid` / `high` / `auto`) selects Soup train recipes and sensible tier defaults. Reference lab = `low`. Contributors add profiles without changing router keyword logic.

## Routing logic

```python
# Pseudocode — lumen_router.py / win-router-lib.ps1

def route(model_config, hardware):
    vram_needed = estimate_vram(model_config)  # weights + kv + overhead

    if vram_needed <= hardware.vram_free * 0.85:
        backend = pick_fastest_resident(hardware.bench_results)
        stack = SpeedStack(
            speculative=model_config.allow_speculative,
            kv_cache_quant="q8_0",
            cuda_graphs=True,
            threads=hardware.cpu_threads,
        )
        return ResidentPath(backend, stack)

    if model_config.architecture == "moe":
        return StreamingPath(engine="colibri", stack=IOStack(prefetch=True))

    return StreamingPath(engine="airllm", stack=IOStack(compression="4bit"))
```

## Speed stack (resident path — this is where +40% lives)

Applied only when the model fits in VRAM.

| Layer | Action | Expected Δ |
|-------|--------|------------|
| L0 | Benchmark backends; pick winner | +10–20% |
| L1 | `n_gpu_layers=-1`, optimal `threads` | +5–10% |
| L2 | KV cache Q8 or smaller ctx if VRAM tight | +5–15% |
| L3 | Speculative: draft 1B → verify 7B | +25–50% |
| L4 | Sustained power / fan profile (laptop) | +5–10% |

Stacks are **multiplicative with diminishing returns**:

```
effective = baseline × (1 + L0) × (1 + L1) × ...
```

Example: 20 tok/s × 1.15 × 1.10 × 1.35 ≈ **34 tok/s** (+70%) — optimistic but possible with speculation.

## I/O stack (streaming path — for fit, not this speed goal)

Borrow from Colibri + AirLLM when model > VRAM:

- int4 weight container
- prefetch next layer/expert
- RAM pin for dense core
- VRAM tier for hot experts
- `.coli_usage` style hot cache

**Do not use I/O stack when chasing +40% on a model that already fits.**

## Config format (draft)

```yaml
# lumen.yaml
model: mistral-7b-instruct-q4_0
goal: speed          # speed | fit | train

hardware:
  profile: hardware.json   # from lumen probe

routing:
  prefer: auto             # auto | ollama | llamacpp | airllm | colibri
  force_stream: false      # true only for oversized models

speed_stack:
  speculative:
    enabled: true
    draft: llama-3.2-1b-q4
    min_acceptance: 0.60
  kv_cache:
    type: q8_0
  context: 2048
  gpu_layers: -1

benchmark:
  prompts: benchmarks/prompts.txt
  runs: 5
  warmup: 2
  target_improvement: 0.40   # 40% minimum
```

## Soup integration (train → deploy)

```
soup train (LoRA 8B)  →  soup merge  →  soup export --format gguf
                                              ↓
                                    lumen route (resident GGUF)
                                              ↓
                                    lumen serve (optimized)
```

Training uses Soup layer streaming.  
Inference uses Lumen resident path — **not** Soup streaming.

## File layout (this repo)

```
lumen-stream-lab/
├── README.md
├── VISION.md              ← goal and honest expectations
├── ARCHITECTURE.md        ← this file
├── PLAYBOOK.md            ← hardware + tool reference
├── RESULTS.md             ← your benchmark log
├── lumen.yaml.example     ← orchestrator config template
├── benchmarks/
│   ├── PROTOCOL.md        ← how to measure fairly
│   └── prompts.txt        ← fixed prompt suite
└── scripts/
    ├── probe.sh           ← hardware detection
    └── bench.sh           ← baseline runner
```

## What is NOT in v1

- Rewriting matmul kernels in C (use llama.cpp / Ollama first)
- Custom layer streaming engine (use existing tools)
- Training in the orchestrator (delegate to Soup)
- Frontier MoE at high speed on 4 GB VRAM (physics; fine on 24 GB+)

## Success criterion (automated)

```bash
./scripts/bench.sh --baseline -o results/baseline.json
./scripts/bench.sh --optimized -o results/optimized.json
python3 scripts/compare.py --min-gain 0.40
# exit 0 = PASS (≥40% improvement)
# exit 1 = FAIL (document why in RESULTS.md)
```
