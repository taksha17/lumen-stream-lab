# Tool & ecosystem comparison

How **Lumen Stream Lab** compares to other open-source LLM tools on GitHub — with **measured numbers** from our reference lab (GTX 1650 4GB, Ollama 0.33.2).

> **Fair comparison rule:** Compare tools on what each is designed to do. Lumen is a **local hybrid router** for models that already fit in VRAM. It is not a replacement for cloud API gateways or for streaming 70B models off disk.

Hardware profile: [hardware/reference-lab.json](../hardware/reference-lab.json)  
Raw numbers: [REFERENCE-RESULTS.md](./REFERENCE-RESULTS.md) | Fixtures: [results/fixtures/](../results/fixtures/)

**Last full re-bench:** 2026-09-01 (`deploy/win-bench-ecosystem.ps1`, `deploy/win-bench-phase-d3.ps1`)

---

## At a glance

| Approach | GitHub / tool | Role | Ref. lab tok/s | vs always-3B (48.38) |
|----------|---------------|------|----------------|----------------------|
| **Always one 3B** | [Ollama](https://github.com/ollama/ollama) | Inference server | **48.94** (D3 re-bench) | baseline |
| **Same weights, different backend** | [llama.cpp](https://github.com/ggerganov/llama.cpp) | Low-level inference | **16.49** | **−66%** |
| **Faster single small model** | LFM 2.5 via Ollama | Model swap only | **64.13** | +33% (below +40%) |
| **Newest 1.7B swap** | SmolLM2 1.7B via Ollama | Model swap only | **98.69** | +104% (1B-class; domain unproven) |
| **Layer-streaming inference** | [AirLLM](https://github.com/lyogavin/airllm) | Run HF models > VRAM | ~8–15 est. (7B) | Slower when model already fits |
| **Expert streaming (MoE)** | [Colibri](https://github.com/JustVugg/colibri) | Frontier MoE on disk | N/A on 4GB | Different problem |
| **Training on 4GB** | [Soup](https://github.com/MakazhanAlpamys/Soup) | Fine-tune w/ layer streaming | N/A (training) | Complements Lumen |
| **Multi-provider API router** | [LiteLLM](https://github.com/BerriAI/litellm) | Cloud + API keys | N/A (local) | Different category |
| **Lumen hybrid orchestration** | **this repo** | Route 1B / LFM / domain 3B / 7B | **68.10 mean** | **+40.8% PASS** |

**Takeaway:** Swapping to a faster **single** 3B-class model (LFM) still misses +40%. Swapping to a **1.7B** model (SmolLM2) beats +40% on speed alone but is not a drop-in for domain/quality tiers. **Routing** across tier-appropriate models hits the gate with quality preserved.

---

## 1. Inference backends (same `llama3.2:3b` weights)

Re-bench 2026-09-01 | `deploy/win-bench-llamacpp-vs-ollama.ps1` | `num_predict=128`

| Backend | Median decode tok/s | vs Ollama |
|---------|---------------------|-----------|
| **Ollama** | **48.20** | — |
| llama.cpp (`llama-cli`, same GGUF blob) | 16.49 | **−66%** |

Portable: `python3 scripts/bench_backends.py --backend ollama --model llama3.2:3b`

---

## 2. Recent model families

### Phase D2 (2026-08-31)

| Model | Median tok/s | Verdict |
|-------|--------------|---------|
| LFM 2.5-2.6B | **65.20** | Best 2–3B balanced speed; domain fails alone |
| Gemma 4 e2b-it-qat | 54.01 | Fits 4GB |
| Gemma 4 e4b | 12.21 | Too slow |
| Nemotron 3.5 Lightning | 1.76 | Not viable |

### Phase D3 (2026-09-01) — Phi-4, SmolLM2, Gemma 3

| Model | Median tok/s | vs always-3B | Router note |
|-------|--------------|--------------|-------------|
| llama3.2:1b | 98.56 | +101% | fast tier |
| llama3.2:3b | 48.94 | baseline | +40% reference |
| qwen2.5:3b-instruct-q4_K_M | 55.80 | +14% | stock alternative |
| **phi4-mini** | **29.46** | **−40%** | Slower than 3B on GTX 1650 |
| **smollm2:1.7b** | **98.69** | **+102%** | Candidate fast tier (needs domain eval) |
| **gemma3:1b-it-qat** | **82.27** | **+68%** | Candidate fast tier |
| gemma3:4b-it-qat | 12.14 | −75% | Ruled out |
| lfm-balanced | 64.13 | +33% | production balanced |
| qwen2.5-3b-lumen | 55.65 | +14% | production domain |

Fixture: [results/fixtures/phase-d3-summary.json](../results/fixtures/phase-d3-summary.json)

---

## 3. Lumen vs “use one faster model everywhere”

Re-bench 2026-09-01 orchestration: `orchestration-bench-20260901-003509.json`

| Policy | Mean tok/s (12-prompt suite) | +40% vs 48.38? |
|--------|------------------------------|----------------|
| Always `llama3.2:3b` | 48.38–48.94 | — |
| Always LFM 2.5 | 64.13 | No (+33%) |
| Always SmolLM2 1.7B | 98.69 | Yes on speed only; quality/domain unproven |
| Always phi4-mini | 29.46 | No (−40%) |
| **Lumen hybrid auto-route** | **68.10** | **Yes (+40.8%)** |

---

## 4. Lumen vs other GitHub “routers”

| Project | What it routes | Local 4GB? | Comparable metric |
|---------|----------------|------------|-------------------|
| **Lumen** | 1B / LFM / domain 3B / 7B by prompt | Yes | +40.8% vs always-3B |
| [LiteLLM](https://github.com/BerriAI/litellm) | OpenAI/Anthropic/etc. APIs | Optional | Cost/latency across *cloud* providers |
| [RouteLLM](https://github.com/lm-sys/RouteLLM) | Strong vs weak *cloud* models | No | Quality-cost tradeoff |
| [Ollama](https://github.com/ollama/ollama) | No routing (one model per request) | Yes | Simplicity |

---

## 5. Lumen vs streaming inference tools

| Tool | Solves | Good when | Ref. lab for resident 3B |
|------|--------|-----------|----------------------------|
| [AirLLM](https://github.com/lyogavin/airllm) | Layer-at-a-time HF inference | Model **does not fit** VRAM | Slower than Ollama when 3B fits (~est. 8–15 tok/s for 7B) |
| [Colibri](https://github.com/JustVugg/colibri) | MoE expert streaming | Huge MoE on NVMe | Not tested; disk budget blocks frontier models |
| [Soup](https://github.com/MakazhanAlpamys/Soup) | Train with layer streaming | Fine-tune 7B on 4GB | Training → export → Lumen serves |

See [PLAYBOOK.md](./PLAYBOOK.md) for AirLLM/Colibri/Soup depth.

---

## 6. How to reproduce

```powershell
# Reference Windows lab:
powershell -File deploy\win-bench-phase-d3.ps1
powershell -File deploy\win-bench-ecosystem.ps1
powershell -File deploy\win-bench-llamacpp-vs-ollama.ps1
powershell -File deploy\win-orchestration-bench.ps1
powershell -File deploy\win-regression.ps1 -Full
```

```bash
# Portable:
python3 scripts/bench_backends.py --backend ollama --model llama3.2:3b
python3 lumen.py   # menu options 4, 5, 7
```

---

## 7. Honest limits

- Numbers are **reference-lab only** — re-bench on your GPU.
- Lumen does **not** make one kernel 2× faster; it **reduces average work per token** via routing.
- SmolLM2/Gemma3 1B beat +40% as *single-model* swaps but have **not** passed Lumen domain gates (E05/E11/E12).
- Cloud routers solve **cost/API** problems, not local VRAM orchestration.
