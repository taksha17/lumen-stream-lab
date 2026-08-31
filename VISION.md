# Vision — Lumen Stream Lab

## The goal in one sentence

**Build a thin orchestration layer on top of Soup, AirLLM, and Colibri that automatically picks the fastest path for your hardware — and stack software optimizations until we beat the best single tool by at least 40–50%.**

## Open source and scaling

Lumen is meant to **grow with contributors**, not stay bound to one GTX 1650 laptop.

- **Reference lab** (`hardware/reference-lab.json`) — where we prove +40% on modest hardware and run regression gates.
- **Your hardware** — probe, bench, set `lumen.yaml` tiers; absolute tok/s will exceed the lab on stronger GPUs.
- **Shared logic** — routing, bench protocol, and relative gain targets are hardware-agnostic; only defaults and Soup recipes are profile-specific.

See `SCALING.md` and `CONTRIBUTING.md`.

---

## What success looks like

| Metric | Baseline (best existing tool today) | Target (Lumen orchestration) |
|--------|-------------------------------------|------------------------------|
| **Decode tok/s** | e.g. 30 tok/s | **≥ 42 tok/s** (+40%) |
| **Or** | e.g. 40 tok/s | **≥ 56–60 tok/s** (+40–50%) |
| **Same model, same quant, same GPU** | — | Required for fair comparison |
| **Quality** | Bit-identical or within measured tolerance | No silent precision drops |

We are **not** trying to run a 744B model at 50 tok/s on a 1650.  
We **are** trying to make the **best already-fast setup on this machine** meaningfully faster through smarter orchestration.

---

## The key insight (read this first)

Soup, AirLLM, and Colibri solve **fit** (run models bigger than VRAM).

Your speed goal solves **throughput** (run the chosen model faster).

Those are **different problems**. Mixing them blindly makes you slower.

```
┌─────────────────────────────────────────────────────────────┐
│  BIGGER model than VRAM  →  streaming (AirLLM / Colibri)     │
│                             Speed goes DOWN, fit goes UP     │
├─────────────────────────────────────────────────────────────┤
│  FASTER chat on this GPU →  resident model + optimizations   │
│                             Soup/AirLLM streaming OFF        │
└─────────────────────────────────────────────────────────────┘
```

**Lumen's job:** know which mode you're in, never stream when you don't have to, and apply the right speed stack when the model already fits.

---

## Where the +40–50% actually comes from

Streaming layers/experts is the wrong lever for speed on a 7B Q4 model that can mostly fit a 4 GB GPU. The gains come from stacking **orthogonal** optimizations:

| Optimization | Expected gain | Source inspiration |
|--------------|---------------|-------------------|
| **Hardware-aware backend pick** | 10–20% | Run llama.cpp vs Ollama vs vLLM; pick winner per GPU |
| **Speculative decoding** (draft + verify) | 25–50% | Colibri MTP; small draft model |
| **KV cache tuning** (layout, quant, size) | 5–15% | Less VRAM pressure → more batch/ctx headroom |
| **CUDA graph / kernel fusion** | 5–15% | Reduce launch overhead per token |
| **Prefill/decode split tuning** | 5–10% | Different paths for TTFT vs steady decode |
| **Zero-copy weight load** (mmap, pin once) | 5–10% | Colibri `O_DIRECT` / contiguous reads |
| **Thermal-aware clock hold** | 5–10% | Laptop GPUs throttle; sustained vs burst |

**Realistic stacked target:** if baseline is 30 tok/s, **42–45 tok/s** is achievable without inventing new silicon. **50+ tok/s** needs a strong speculative path or a smaller model (3B).

**Not counted toward the goal:** switching from 7B to 3B (that's a different model, not orchestration).

---

## What we are building (Lumen Runtime)

A small orchestrator — working name **`lumen`** — that does four things:

### 1. Profile once (`lumen probe`)

```bash
lumen probe
# → GPU model, VRAM, RAM, NVMe speed, PCIe gen
# → writes hardware.json
```

Borrow ideas from `soup doctor`, `coli doctor`, `coli plan`.

### 2. Benchmark baselines (`lumen bench`)

Run the **same** fixed prompt suite through each backend:

- Ollama (GGUF)
- llama.cpp CLI
- AirLLM (only if model doesn't fit resident — otherwise skip)
- Soup serve (if installed)

Record decode tok/s, TTFT, VRAM peak. Write `results/baseline.json`.

### 3. Pick the winning path (`lumen route`)

```
if model fits in VRAM (with KV headroom):
    use fastest resident backend from bench
    enable speed stack (speculative, kv tuning, ...)
else:
    use streaming backend (AirLLM or Colibri by architecture)
    enable I/O stack (prefetch, hot cache, int4)
```

### 4. Measure improvement (`lumen bench --optimized`)

Same prompts, same model. Compare to baseline. **Ship only if ≥ +40%.**

---

## Phase roadmap

| Phase | Deliverable | Target gain |
|-------|-------------|-------------|
| **0 — Measure** | Baseline numbers on server laptop | Know true ceiling (probably 15–35 tok/s for 7B Q4 on 1650) |
| **1 — Route** | Script picks fastest existing backend | +10–20% vs using wrong tool |
| **2 — Tune** | KV cache, context, GPU power, threads | +10–15% |
| **3 — Speculate** | Draft model (1B) + verify (7B) | +25–40% when acceptance > 65% |
| **4 — Unify** | Shared weight path, one config YAML | +5–10% overhead reduction |
| **5 — Integrate** | Soup train → Lumen infer pipeline | End-to-end workflow, not speed per se |

**Minimum viable win:** Phase 0 + 1 + 2 should get you close to +40% if baseline was measured on a suboptimal backend (e.g. AirLLM streaming when Ollama resident is faster).

---

## Honest expectations on the server laptop

GTX 1650 Mobile 4 GB is **not** a 30–40 tok/s card for 7B in most published benches. Typical ranges:

| Model | Realistic baseline (best tool) | +40% target |
|-------|-------------------------------|-------------|
| Llama 3.2 **3B** Q4 | 25–40 tok/s | **35–56 tok/s** |
| Mistral **7B** Q4 | 12–25 tok/s | **17–35 tok/s** |
| Qwen2.5 **7B** Q4 | 12–22 tok/s | **17–31 tok/s** |

If your measured baseline is **20 tok/s** on 7B, +40% = **28 tok/s** — that's the honest target.

If you need **40–50 tok/s sustained**, the orchestration should route to **3B Q4** or aggressive speculative decode on 7B — and document that trade openly.

---

## Principles (non-negotiable)

1. **Same model, same quant** for any speed claim.
2. **Measure cold and warm** — report both; warm is what users feel after turn 3.
3. **No silent quality loss** — log quant format, temperature, seed.
4. **Streaming only when required** — never pay I/O tax for speed runs.
5. **Negative results count** — publish what didn't beat baseline.

---

## One-line pitch

> **Lumen doesn't replace Soup, AirLLM, or Colibri — it stops you from using the wrong one, then stacks the optimizations each tool keeps in its own silo.**
