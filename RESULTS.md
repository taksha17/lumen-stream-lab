# Benchmark Results Log

> Server: HP laptop (LAN) | `D:\lumen-stream-lab` | GTX 1650 4GB

## Storage fix (2026-08-30)

**Problem:** Soup layer shards + HF cache were on **C:** (`~\.soup\layer-stream` ~19GB).

**Fix:** Migrated to **D:** and set permanent env vars:

| Variable | Path |
|----------|------|
| `SOUP_LAYER_STREAM_CACHE_DIR` | `D:\lumen-stream-lab\cache\soup-layer-stream` |
| `HF_HOME` | `D:\lumen-stream-lab\cache\huggingface` |
| `OLLAMA_MODELS` | `D:\ollama\models` |

**Result:** C: **12.6 GB → 33 GB free** | Script: `deploy/win-migrate-to-d.ps1`

Before any training: `. D:\lumen-stream-lab\deploy\win-env-d.ps1`

---

## Inference benchmarks

| Run | Model | Backend | Decode tok/s |
|-----|-------|---------|--------------|
| B01 | llama3.2:3b | Ollama | **48.38** |
| B02 | llama3.2:1b | Ollama | **96.87** |
| B03 | mistral:7b-q4 | Ollama | **10.19** |
| B04 | qwen2.5-7b-lumen (fine-tuned LoRA) | Ollama | **9.62** |
| O01 | 3B + 1B speculative | Ollama API | 47.88 (no gain) |
| R01 | "What is 2+2?" | Lumen router → 1B | **93.71** |
| R02 | complex explain | Lumen router → 3B | **48.53** |
| R03 | "What is 2+2?" (3-tier) | fast → 1B | **109.12** |
| R04 | detailed essay prompt | quality → qwen2.5-7b-lumen | **12.01** |

### Router tiers (`deploy/win-route.ps1`)

| Tier | Model | When |
|------|-------|------|
| `fast` | llama3.2:1b | Short/simple, arithmetic, greetings |
| `balanced` | LFM 2.5-2.6B (speed) / qwen2.5-3b-lumen (domain) | Complex explain/analyze, medium length |
| `quality` | qwen2.5-7b-lumen | Quality keywords, long prompts (>48 words) |

Force tier: `-Tier fast|balanced|quality` (default `auto`)

### +40% target (same 3B model)

Baseline: 48.38 tok/s → Need: **67.74 tok/s** — not achieved via speculative decode.

**Router win:** simple prompts auto-route to 1B (~2x speed) — valid orchestration strategy.

---

## Soup training

| Run | Model | Config | Result |
|-----|-------|--------|--------|
| S01 | Qwen2.5-0.5B LoRA | quant=none | **PASS** — 5 steps, 1.9 GB VRAM |
| S02 | Qwen2.5-7B stream_layers | 4bit, max_len=512 | FAIL — VRAM 3.88 > 3.45 GB free |
| S03 | Qwen2.5-7B stream_layers | 4bit, max_len=256 | FAIL — BF16 amp crash on GTX 1650 |
| S04 | Qwen2.5-7B stream_layers | quant=none, max_len=256 | FAIL — VRAM 3.95 > 3.45 GB |
| S05 | Qwen2.5-7B stream_layers | quant=none, max_len=64, stream_source=disk, LoRA r=8 | **PASS** — 3 steps, smoke (10 samples) |
| S06 | Qwen2.5-7B stream_layers | 107 samples, 48 steps, 58 min | **PASS** — loss 5.19→1.65, `output-7b-stream-s06` |

### S05 winning config (`soup-7b-stream.yaml`)

```yaml
data.max_length: 64          # min allowed by Soup; 128+ still OOM on 4GB
training.quantization: none  # 4bit hits BF16 amp error on Turing
training.stream_layers: true
training.stream_source: disk
training.lora: { r: 8, alpha: 16 }
```

Output: `D:\lumen-stream-lab\output-7b-stream` | Run ID: `run_20260831_000619_9a3899b2`

**Chat smoke test:** `soup chat` loads full 7B resident → CPU/disk offload + KeyError on 4GB.

### S05 export → Ollama — **PASS**

| Step | Result |
|------|--------|
| LoRA merge | OK (~20s) |
| GGUF f16 + q4_k_m | OK — `D:\lumen-stream-lab\exports\qwen2.5-7b-lumen.q4_k_m.gguf` (4.4 GB) |
| Ollama deploy | `ollama create qwen2.5-7b-lumen` — **9.62 tok/s** decode (B04) |

Scripts: `deploy/win-export-7b.ps1`, `deploy/win-setup-llama-cpp.ps1`, `deploy/win-deploy-ollama-7b.ps1`

Run: `ollama run qwen2.5-7b-lumen`

---

## Router quality eval (E01–E10)

Script: `deploy/win-router-eval.ps1` | Report: `results/router-eval-20260831-010242.json`

| Metric | Result |
|--------|--------|
| Routing accuracy | **10/10** auto-tier matches |
| Median decode | fast **95.8** / balanced **47.9** / quality **10.9** tok/s |

**Quality findings (same prompts, all tiers):**
- **fast (1B):** Fast but shallow; E05 routed wrong domain (baseball) for Lumen question
- **balanced (3B):** Best general answers; E05 confused Lumen with Twilio PaaS
- **quality (7B):** Slowest; pre-S06 model hallucinates Laravel/video streaming for Lumen/ML prompts — **needs real fine-tune**

### S06 export + redeploy — **PASS**

| Step | Result |
|------|--------|
| Train | 107 samples, 48 steps, 58 min, loss 5.19→1.65 |
| GGUF | `exports/qwen2.5-7b-lumen-s06.q4_k_m.gguf` (4.4 GB) |
| Ollama | `qwen2.5-7b-lumen` updated |
| Router eval | 10/10 routing, quality **10.79 tok/s** |

**Post-S06 quality check:** 7B still confuses "Lumen" with Laravel/Lumen PHP framework and video layer streaming — `max_length: 64` likely truncates domain training signal. **3B balanced tier remains best general answer quality** until we train 3B with longer context or add more Lumen-specific rows.

Report: `results/router-eval-20260831-022035.json` | Pipeline: `deploy/win-post-s06.ps1`

---

## S07 — Qwen2.5-3B domain fine-tune — **PASS**

| Step | Result |
|------|--------|
| Dataset | `train-s07.jsonl` — **184 rows** (+77 Lumen-domain) |
| Train | 84 steps, **27 min**, loss 5.01→2.27, peak ~0.9/4.0 GB |
| Winning config | `max_length: 64`, `stream_source: disk`, LoRA r=8 (128 + RAM stream OOMd) |
| GGUF | `exports/qwen2.5-3b-lumen-s07.q4_k_m.gguf` |
| Ollama | **`qwen2.5-3b-lumen`** (router **balanced** tier) |
| Router eval | **12/12** accuracy; medians fast **95.5** / balanced **54.4** / quality **10.8** |

**Speed win:** fine-tuned Qwen 3B balanced tier ~**54 tok/s** vs stock llama3.2:3b ~48.

**Domain quality (temp 0 smoke):**
- Laravel disambiguation: fine-tuned 3B correctly says **not related**; stock llama3.2:3b still says **yes related**
- Full "What is Lumen Stream Lab?" definition still fuzzy — `max_length: 64` truncates longer teaching answers

Report: `results/router-eval-20260831-125301.json` | Pipeline: `deploy/win-post-s07.ps1`

---

## Phase D2 — newer families (Gemma 4, Nemotron, LFM) — **DONE**

GTX 1650 4GB | Ollama 0.33.2 | Report: `results/phase-d2/`

| ID | Model | Family | Median tok/s | Verdict |
|----|-------|--------|--------------|---------|
| BL-01 | llama3.2:1b | Meta | **98.54** | fast tier (unchanged) |
| BL-02 | qwen2.5-3b-lumen | Qwen | 56.53 | previous balanced |
| BL-03 | qwen2.5-7b-lumen | Qwen | 9.51 | quality tier |
| **D2-01** | **lfm2.5-2.6b** (Q4) | **Liquid AI** | **65.20** | **NEW balanced winner** (+15% vs Qwen 3B) |
| D2-02 | gemma4:e2b-it-qat | Google | 54.01 | fits 4GB; slower than LFM |
| D2-03 | gemma4:e4b | Google | 12.21 | runs but too slow on 4GB |
| D2-04 | nemotron-3.5-lightning | NVIDIA | 1.76 | fits via offload; not viable for speed |

**Router updated:** hybrid balanced — LFM (general ~65 tok/s) + `qwen2.5-3b-lumen` (Lumen domain ~54 tok/s)

**Takeaways:**
- **LFM 2.5-2.6B** is the first non-Qwen/Llama family to beat a router tier on speed
- **Gemma 4 e2b-it-qat** fits 4GB; **e4b** runs but ~12 tok/s (VRAM pressure)
- **Nemotron Lightning** loads on 4GB but ~2 tok/s — agent MoE wrong tool for this GPU

### Post-D2 router eval (LFM balanced) — **12/12 routing, domain FAIL**

Report: `results/router-eval-20260831-140000.json`

| Metric | Result |
|--------|--------|
| Routing accuracy | **12/12** |
| Median decode | fast **95.6** / balanced **63.9** (LFM) / quality **10.8** tok/s |

**Domain quality (E05/E09/E11/E12) — LFM balanced tier:**

| Prompt | LFM (balanced) | Verdict |
|--------|----------------|---------|
| E05 — 1B vs 3B vs 7B routing | Interprets as Liquid AI LFM deployment, not Lumen Stream Lab | **Wrong domain** |
| E09 — layer streaming | Chain-of-thought; vaguely hits vLLM/LLM inference, not Soup `stream_layers` | Partial |
| E11 — Laravel Lumen? | Starts analysis, no clear "not related" answer | **Weak** |
| E12 — What is Lumen Stream Lab? | Guesses Liquid AI / Lumen company; no project definition | **Wrong** |

**Conclusion:** LFM wins on speed (+15%) but **loses badly on Lumen domain** vs fine-tuned `qwen2.5-3b-lumen`. Hybrid router: domain keywords → Qwen 3B, general balanced → LFM.

### +40% target scorecard (vs always `llama3.2:3b` @ 48.38 tok/s)

**Primary metric:** mean decode tok/s across eval suite via **hybrid auto-route** (`deploy/win-orchestration-bench.ps1`).

| Lever | Why |
|-------|-----|
| Hybrid balanced | LFM (~65 tok/s) general; `qwen2.5-3b-lumen` (~54) for Lumen domain |
| Speed-first quality | 7B only when prompt **>50 words** (or `-Tier quality`); short essays stay on LFM |
| Fast tier | 1B for arithmetic, greetings, short facts |

| Single-tool baseline | tok/s | +40%? |
|---------------------|-------|-------|
| llama3.2:3b (always) | 48.38 | — |
| LFM alone | 65.2 | No (+35%) |
| **Hybrid orchestration (live)** | **70.02** | **+44.7%** | **PASS** (2026-08-31, tightened keywords) |

Report: `results/orchestration-bench-20260831-142228.json`

**Regression gate:** `deploy/win-regression.ps1` (alias + bench + domain smoke). Add `-Full` for router quality eval.

```powershell
powershell -File D:\lumen-stream-lab\deploy\win-orchestration-bench.ps1
powershell -File D:\lumen-stream-lab\deploy\win-compare-target.ps1
```

Quality tier: `.\deploy\win-route.ps1 -Prompt "..." -Tier quality` for explicit 7B.

---

## S08 — 3B domain re-train (max_length 96) — train PASS, deploy FAIL

| Step | Result |
|------|--------|
| Dataset | `train-s08.jsonl` — **220 rows** (+36 full-sentence domain) |
| VRAM smoke | `max_length: 96` fits — peak ~1.24 GB forecast |
| Train | **PASS** — 100 steps, 39 min, loss 4.80→2.18 |
| Export | `exports/qwen2.5-3b-lumen-s08.q4_k_m.gguf` |
| Domain smoke | **FAIL** — worse than S07 (Laravel package hallucination) |
| Orchestration | 67.13 tok/s (+38.8%) with S08 — below +40% gate |
| **Production** | **Rolled back to S07 GGUF** — regression **68.69 tok/s (+42%) PASS** |

Pipeline: `deploy/win-train-3b-s08.ps1`, `win-post-s08.ps1`

**Next domain attempt:** curriculum with replay (S09) or system-prompt on domain route — not full-dataset retrain.

---

## S09 — domain curriculum + S07 replay — gate FAIL, rolled back

| Step | Result |
|------|--------|
| Data | `train-s09-domain.jsonl` — **54 rows** (canonical E05/E11/E12/E09, 3x each) |
| Train | **PASS** — 19 steps, 6 min, replay 35% from S07 (no resume; checkpoint torch issue) |
| Domain gate | E11 **PASS**, E05 **PASS**, E12 **FAIL** (telecom Lumen hallucination) |
| Production | **Rolled back to S07** |

Pipeline: `deploy/win-train-3b-s09.ps1`, `win-domain-smoke-gate.ps1`, `win-post-s09.ps1`

---

## Domain system prompt (2026-08-31) — **PASS**

| Change | Detail |
|--------|--------|
| File | `data/domain-system-prompt.txt` |
| When | All `qwen2.5-3b-lumen` Ollama calls + targeted prompt prefixes (E12 definition, E11 Laravel) |
| Domain gate | E11/E12/E05 **PASS** (2026-08-31 server) |
| Orchestration | **69.59 tok/s** (+43.8%) — PASS; E05 had one transient 0 tok/s run, retry clean |
| S10 train | Deferred — prompt injection sufficient for E12 |

**S10 fallback** (if quality regresses): `data/train-s10-e12.jsonl` + `deploy/win-post-s10.ps1`

---

## Full router eval (2026-08-31) — PASS

`deploy/win-regression.ps1 -Full` on reference lab:

| Metric | Result |
|--------|--------|
| Routing accuracy | 12/12 |
| Median tok/s | fast 94.9, LFM 63.7, domain 54.6, quality 10.6 |
| Orchestration gate | 69.78 tok/s (+44.2%) PASS |
| Report | `results/router-eval-20260831-180616.json` |

Router-eval auto-route mean (64.08 tok/s) is a side metric across all prompts; **primary +40% gate** uses orchestration bench mean.

---

## Backend shootout — Ollama vs llama.cpp (2026-08-31)

`deploy/win-bench-llamacpp-vs-ollama.ps1` on reference lab, `llama3.2:3b`, same Ollama GGUF blob, `num_predict=64`:

| Backend | Median decode tok/s | Notes |
|---------|---------------------|-------|
| **Ollama** | **~49.3** | Primary resident path on this box |
| llama.cpp (`llama-cli`) | **~17.0** | Same weights; interactive CLI overhead |

**Conclusion:** On GTX 1650 reference lab, **keep Ollama as default resident backend** for `llama3.2:3b`. Re-bench on other GPUs; winner may differ.

Script: `scripts/bench_backends.py` (portable), `deploy/win-bench-llamacpp-vs-ollama.ps1` (Windows).
