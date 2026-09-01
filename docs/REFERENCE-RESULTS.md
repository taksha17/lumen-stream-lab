# Reference results (consolidated)

Single-page summary of **verified benchmarks** on the reference lab (GTX 1650 4GB). Full chronological log: [RESULTS.md](./RESULTS.md).  
Machine profile: [hardware/reference-lab.json](../hardware/reference-lab.json).  
CI fixture: [results/fixtures/router-eval-summary.json](../results/fixtures/router-eval-summary.json).

> **Important:** Absolute tok/s are **reference-lab only**. Your hardware will differ. The **+40% relative gain** is the portable claim.

---

## Primary success metric

| Metric | Baseline | Target | **Achieved** |
|--------|----------|--------|--------------|
| Mean decode tok/s (12-prompt hybrid auto-route) | `llama3.2:3b` @ **48.38** | ≥ **67.73** (+40%) | **69.78** (+44.2%) **PASS** |

Verification: `deploy/win-regression.ps1` / `deploy/win-orchestration-bench.ps1`

---

## Single-model baselines (always one model)

| ID | Model | Backend | Decode tok/s | Notes |
|----|-------|---------|--------------|-------|
| B01 | llama3.2:3b | Ollama | **48.38** | Primary baseline |
| B02 | llama3.2:1b | Ollama | **96.87** | Fast tier |
| B03 | mistral:7b-q4 | Ollama | 10.19 | Too slow for default route |
| B04 | qwen2.5-7b-lumen | Ollama | 9.62 | Quality tier (fine-tuned) |

---

## Hybrid orchestration (production router)

| Prompt class | Example | Tier | Model | ~tok/s |
|--------------|---------|------|-------|--------|
| Simple | "What is 2+2?" | fast | llama3.2:1b | **109** |
| General explain | "Explain TCP vs UDP" | balanced | lfm-balanced | **~65** |
| Domain | "What is Lumen Stream Lab?" | balanced | qwen2.5-3b-lumen | **~55** |
| Long essay | >50 words | quality | qwen2.5-7b-lumen | **~11** |

**12-prompt eval mean (auto-route):** **69.1–69.8 tok/s** (+42–44% vs always-3B)

---

## Router quality eval (E01–E12)

| Metric | Result |
|--------|--------|
| Routing accuracy | **12/12** |
| Median fast | 94.9 tok/s |
| Median LFM balanced | 63.7 tok/s |
| Median domain (qwen-lumen) | 54.6 tok/s |
| Median quality (7B) | 10.6 tok/s |

Script: `deploy/win-router-eval.ps1` | Report: `router-eval-20260831-180616.json` (on reference server)

---

## Domain quality gate

| Prompt | ID | Status |
|--------|-----|--------|
| Laravel Lumen disambiguation | E11 | **PASS** |
| "What is Lumen Stream Lab?" | E12 | **PASS** (system prompt + prefix) |
| 1B vs 3B vs 7B routing | E05 | **PASS** |

Script: `deploy/win-domain-smoke-gate.ps1`

---

## Backend shootout (same weights)

Model: `llama3.2:3b` | Prompt: standard explain | `num_predict=64`

| Backend | Median decode | Winner |
|---------|---------------|--------|
| **Ollama** | **~49.3 tok/s** | **Yes** (reference lab) |
| llama.cpp (`llama-cli`) | ~16.6 tok/s | No |

Script: `deploy/win-bench-llamacpp-vs-ollama.ps1`

---

## Phase D2 model families (balanced tier candidates)

| Model | ~tok/s | vs always-3B | Verdict |
|-------|--------|--------------|---------|
| LFM 2.5-2.6B | **~65** | +35% | **Production balanced (general)** |
| Qwen 2.5 3B (stock) | ~56 | +16% | Domain fine-tune base |
| Gemma 4 e2b-it-qat | ~54 | +12% | Fits 4GB; slower than LFM |
| Gemma 4 e4b | ~12 | −75% | Ruled out (speed) |
| Nemotron Lightning | ~2 | −96% | Ruled out (speed) |

---

## Phase D3 — recent models (re-bench 2026-09-01)

`deploy/win-bench-phase-d3.ps1` | Fixture: [results/fixtures/phase-d3-summary.json](../results/fixtures/phase-d3-summary.json)  
GTX 1650 4GB | Ollama 0.33.2 | `num_predict=128` | same prompt as D2

| ID | Model | Family | Median tok/s | vs always-3B (48.94) | Notes |
|----|-------|--------|--------------|----------------------|-------|
| BL-01 | llama3.2:1b | Meta | **98.56** | +101% | fast tier (unchanged) |
| BL-02 | llama3.2:3b | Meta | **48.94** | baseline | +40% reference |
| BL-03 | qwen2.5:3b-instruct-q4_K_M | Alibaba | **55.80** | +14% | stock 3B |
| D3-01 | phi4-mini | Microsoft | **29.46** | −40% | slower than 3B on 4GB |
| D3-02 | smollm2:1.7b-instruct-q4_K_M | HuggingFace | **98.69** | +102% | matches 1B speed; domain TBD |
| D3-03 | gemma3:1b-it-qat | Google | **82.27** | +68% | strong 1B; not yet in router |
| D3-04 | gemma3:4b-it-qat | Google | **12.14** | −75% | VRAM pressure |
| D3-05 | lfm-balanced | Liquid AI | **64.13** | +31% | production balanced |
| D3-06 | qwen2.5-3b-lumen | Qwen (Lumen) | **55.65** | +14% | domain tier |

**D3 takeaway:** SmolLM2 1.7B and Gemma3 1B are **fast** on this GPU, but **no single new model** beats +40% *and* passes Lumen domain gates. Hybrid routing still wins.

---

## Ecosystem comparison (re-bench 2026-09-01)

Fixture: [results/fixtures/ecosystem-comparison-20260901.json](../results/fixtures/ecosystem-comparison-20260901.json)

| Tool / policy | Median / mean tok/s | vs always-3B (48.38) |
|---------------|---------------------|----------------------|
| Ollama always `llama3.2:3b` | 48.2–49.1 | baseline |
| llama.cpp (same GGUF) | **16.49** | −66% |
| LFM alone | 64.13 | +33% (below +40%) |
| SmolLM2 1.7B alone | 98.69 | +104% (1B-class; quality/domain unproven) |
| **Lumen hybrid orchestration** | **68.10** mean | **+40.8% PASS** |

Full tool-by-tool write-up: [TOOL-COMPARISON.md](./TOOL-COMPARISON.md)

---

## Training milestones (Soup on 4GB)

| Run | Model | Result |
|-----|-------|--------|
| S05–S06 | Qwen2.5-7B stream_layers | **PASS** → `qwen2.5-7b-lumen` |
| S07 | Qwen2.5-3B domain | **PASS** → production `qwen2.5-3b-lumen` |
| S08 | 3B max_length 96 | Train PASS, domain regressed → rollback |
| S09 | Domain curriculum | E11 improved, E12 fail → rollback to S07 |
| S10 | Deferred | System prompt fixed E12 without retrain |

---

## What did NOT work

| Experiment | Result |
|------------|--------|
| Speculative decode (3B + 1B draft) | ~1% gain — not a +40% path |
| Same-model 3B kernel speedup | ~+35% (LFM alone), not +40% |
| llama.cpp over Ollama (ref. lab) | 3× slower than Ollama for resident 3B |
| Auto-route short prompts to 7B | Kills mean (~10 tok/s) |

---

## How to reproduce

```bash
# Interactive (recommended)
python3 lumen.py

# Or individual gates (Windows reference server)
powershell -File deploy/win-regression.ps1
powershell -File deploy/win-regression.ps1 -Full   # + router eval ~10 min
```

```bash
# Portable checks
python3 -m unittest discover -s tests -v
python3 scripts/compare.py --baseline 48.38 --optimized 69.78 --min-gain 0.40
```

Contributors: reproduce on **your** hardware and PR `hardware/<your-profile>.json` — see [HARDWARE-TESTING.md](./HARDWARE-TESTING.md).
