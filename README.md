# Lumen Stream Lab

[![CI](https://github.com/taksha17/lumen-stream-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/taksha17/lumen-stream-lab/actions/workflows/ci.yml)

> **Hybrid LLM orchestration — route each prompt to the right model, measure everything, beat always-3B by ≥40% decode tok/s.**

Lumen is a thin **decision layer** between your app and inference backends (Ollama, llama.cpp, Soup, AirLLM, Colibri). It does not replace a model server — it answers: *which model, which backend, which speed stack* for this hardware and this prompt.

Open source and **hardware-agnostic**. We CI-test on a modest reference rig (GTX 1650 4GB); contributors on stronger GPUs probe locally and tune tiers. See [docs/SCALING.md](./docs/SCALING.md) and [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## Real-world use cases

Most teams running local LLMs hit the same wall: the model is fine, but **routing and tuning** are tribal. Lumen makes that **measured, reproducible, and auditable** — the same pattern used in production gateways (tiered routing, A/B, regression gates), scoped to one box or your fleet.

| Problem | What Lumen does |
|---------|-----------------|
| **"Ollama is slow for our 8B"** | Benchmark backends per model; route to the fastest path for *that* model on *this* GPU — not a blind tool swap |
| **"We need cheap + quality tiers"** | Route short/simple prompts to 1B (~110 tok/s); domain questions to a fine-tuned 3B; long/complex to 7B opt-in |
| **"Fine-tuned GGUF still feels slow"** | Orchestration wins by **picking the right model size per query**, not making one 3B kernel 2× faster |
| **"Agent loops need latency budgets"** | Plan JSON per request (`tier`, `model`, `reason`) — gateway or agent can force `fast` under deadline |
| **Train → serve pipeline** | Soup trains LoRA → export GGUF → Ollama deploy → Lumen routes and **proves** +40% vs always-3B baseline |

### Where it plugs in

```
   client / app
        │
        ▼
   API gateway (auth, rate limit)     ← your existing layer
        │
        ▼
   Lumen router (lumen.py route)     ← tier + model + speed stack plan
        │
        ▼
   Backend pool (Ollama / llama.cpp / stream path)
```

**Reference HTTP gateway in this repo:** [`scripts/lumen_gateway.py`](./scripts/lumen_gateway.py) — `POST /v1/chat`, `POST /v1/plan`, `GET /v1/health` (stdlib only).

**Full enterprise integration guide:** [docs/ENTERPRISE.md](./docs/ENTERPRISE.md) — gateway topology, agent frameworks, MLOps loop, tiered cost/quality, A/B routing, VRAM fall-back, CI regression gates.

---

## Proven results (reference lab)

**Hardware:** GTX 1650 4GB, Ollama 0.33.2 — [`hardware/reference-lab.json`](./hardware/reference-lab.json)  
**Re-bench date:** 2026-09-01 | Fixtures: [`results/fixtures/`](./results/fixtures/)  
**Your machine will differ** — the **+40% relative gain** is the portable claim. Full tables: [docs/REFERENCE-RESULTS.md](./docs/REFERENCE-RESULTS.md) | [docs/TOOL-COMPARISON.md](./docs/TOOL-COMPARISON.md)

### Primary metric (+40% gate)

| Metric | Baseline | Target | **Latest (2026-09-01)** |
|--------|----------|--------|-------------------------|
| Mean decode tok/s (12-prompt hybrid auto-route) | `llama3.2:3b` @ **48.38** | ≥ **67.73** (+40%) | **68.10** (+40.8%) **PASS** |

### Lumen vs other approaches

| Approach | tok/s | vs always-3B (48.38) |
|----------|-------|----------------------|
| Ollama always `llama3.2:3b` | 48.2–48.9 | baseline |
| llama.cpp (same 3B GGUF) | **16.49** | **−66%** |
| LFM 2.5 alone | 64.13 | +33% (below +40%) |
| SmolLM2 1.7B alone | 98.69 | +104% (speed only; domain unproven) |
| **Lumen hybrid orchestration** | **68.10** mean | **+40.8% PASS** |

| Quality gate | Result |
|--------------|--------|
| Router eval (E01–E12) | **12/12** routing accuracy |
| Domain smoke (E05/E11/E12) | **PASS** (system prompt + prefixes) |
| Median by tier (router eval) | fast **94.9** · LFM **63.7** · domain **54.6** · quality **10.6** tok/s |

### Production router tiers

| Tier | Model | When | ~tok/s (D3) |
|------|-------|------|-------------|
| `fast` | `llama3.2:1b` | Arithmetic, greetings, short facts | **98.6** |
| `balanced` | `lfm-balanced` | General explain/coding | **64.1** |
| `balanced` (domain) | `qwen2.5-3b-lumen` | Lumen / Soup / routing keywords | **55.7** |
| `quality` | `qwen2.5-7b-lumen` | Prompt >50 words or `-Tier quality` | **~10** |

Reproduce: `deploy/win-orchestration-bench.ps1` · `deploy/win-regression.ps1 -Full`

### Latest models bench — Phase D3 (2026-09-01)

`deploy/win-bench-phase-d3.ps1` · `num_predict=128` · median decode tok/s

| Model | Family | tok/s | vs always-3B (48.94) | Verdict |
|-------|--------|-------|----------------------|---------|
| **smollm2:1.7b-instruct-q4_K_M** | HuggingFace | **98.69** | +102% | Fast; candidate fast tier (domain TBD) |
| llama3.2:1b | Meta | **98.56** | +101% | Production fast tier |
| **gemma3:1b-it-qat** | Google | **82.27** | +68% | Strong 1B; not in router yet |
| lfm-balanced | Liquid AI | **64.13** | +31% | Production balanced (general) |
| qwen2.5:3b-instruct-q4_K_M | Alibaba | **55.80** | +14% | Stock 3B alternative |
| qwen2.5-3b-lumen | Qwen (fine-tuned) | **55.65** | +14% | Production domain tier |
| llama3.2:3b | Meta | **48.94** | — | +40% baseline |
| phi4-mini | Microsoft | **29.46** | −40% | Slower than 3B on 4GB |
| gemma3:4b-it-qat | Google | **12.14** | −75% | VRAM pressure |

### Phase D2 families (2026-08-31)

| Model | tok/s | Verdict |
|-------|-------|---------|
| LFM 2.5-2.6B | **65.2** | Best balanced speed; fails domain alone |
| Gemma 4 e2b-it-qat | 54.0 | Fits 4GB |
| Gemma 4 e4b | 12.2 | Ruled out |
| Nemotron 3.5 Lightning | 1.8 | Ruled out |

**Takeaway:** No single new model beats +40% *and* passes Lumen domain gates. **Hybrid routing** (1B + LFM + domain 3B + opt-in 7B) is what hits the gate.

---

## Quick start

```bash
git clone https://github.com/taksha17/lumen-stream-lab.git
cd lumen-stream-lab

# Interactive terminal UI (recommended)
python3 lumen.py
# or: ./lumen          (Linux/macOS)
# or: lumen.cmd        (Windows)

# One-shot CLI
python3 lumen.py probe
python3 lumen.py route --prompt "Explain TCP vs UDP"
```

**Full terminal UI walkthrough:** [docs/TERMINAL-UI.md](./docs/TERMINAL-UI.md) — prerequisites, every menu option, chat commands, troubleshooting.

### Interactive menu at a glance

```
==========================================
  LUMEN STREAM LAB
  interactive menu
==========================================
```

| Key | Action |
|-----|--------|
| **1** | Setup check — Ollama, GPU probe, list models |
| **2** | **Chat** — route each prompt + generate (mini agent loop) |
| **3** | Route one prompt (JSON plan only) |
| **4** | Bench a model (decode tok/s) |
| **5** | +40% compare (baseline vs orchestration mean) |
| **6** | HTTP gateway on `:8080` (Ctrl+C to stop) |
| **7** | Ollama vs llama.cpp shootout |
| **8** | Router parity tests (CI suite) |
| **9** | Documentation paths + GitHub link |
| **0** | Exit |

**Chat mode commands:** `/quit` to exit; `/tier fast`, `/tier balanced`, or `/tier quality` to force a tier.

**Before chatting:** start Ollama (`ollama serve`) and pull models — see [docs/MODELS.md](./docs/MODELS.md).

Copy [`lumen.yaml.example`](./lumen.yaml.example) → `lumen.yaml` for custom tiers and paths.

### HTTP gateway (optional)

```bash
python3 lumen.py probe   # once per machine
python3 scripts/lumen_gateway.py --port 8080
```

```bash
# Routing plan only
curl -s http://127.0.0.1:8080/v1/plan \
  -H 'content-type: application/json' \
  -d '{"prompt": "What is 2+2?"}'

# Route + generate (uses domain system prompt when needed)
curl -s http://127.0.0.1:8080/v1/chat \
  -H 'content-type: application/json' \
  -d '{"prompt": "What is Lumen Stream Lab?"}'
```

### Backend shootout (Ollama vs llama.cpp)

```bash
python3 scripts/bench_backends.py --backend ollama --model llama3.2:3b
python3 scripts/bench_backends.py --backend llamacpp --gguf /path/to/model.gguf
```

See [docs/MODELS.md](./docs/MODELS.md) and `deploy/win-bench-llamacpp-vs-ollama.ps1` on Windows.

---

## Agent integration (Hermes & custom loops)

Agent frameworks (e.g. [Hermes Agent](https://github.com/NousResearch/hermes-agent)) spend most wall time in **repeated LLM calls**. If every step uses `llama3.2:3b`, the whole loop stays at ~49 tok/s. Lumen routes **each step** to the right tier — measured **~68 tok/s mean (+41%)** on the reference lab.

```
Hermes / custom agent loop
        │
        ▼
  Lumen gateway :8080     ← /v1/plan or /v1/chat per step
        │
        ▼
  Ollama (1B / LFM / domain 3B / 7B)
```

| Agent step | Lumen tier | Typical model |
|------------|------------|---------------|
| Tool arg parsing, short classify | `fast` | `llama3.2:1b` (~99 tok/s) |
| General reasoning | `balanced` | `lfm-balanced` (~64 tok/s) |
| Project-specific / domain | `balanced` (domain) | `qwen2.5-3b-lumen` |
| Long analysis (opt-in) | `quality` | `qwen2.5-7b-lumen` |

**Quick setup:**

```bash
python3 lumen.py probe
python3 scripts/lumen_gateway.py --port 8080

# One agent turn — route + generate
curl -s http://127.0.0.1:8080/v1/chat \
  -H 'content-type: application/json' \
  -d '{"prompt": "Summarize this log and suggest the next tool call"}'
```

**Hermes on Windows (reference lab):**

```powershell
powershell -File deploy\win-setup-hermes.ps1 -InstallNative
```

Optional: `pip install hermes-ollama-native` and set `HERMES_OLLAMA_NATIVE=1` for correct Ollama tool-call streaming — Lumen is **orthogonal** and picks which local model each turn uses.

**Full guide:** [docs/AGENT-INTEGRATION.md](./docs/AGENT-INTEGRATION.md) — Python hook, gateway API, Hermes profiles, expected latency impact.

---

## Integration API

```bash
lumen probe                              # hardware.json
lumen bench --model llama3.2:3b          # benchmark a model
lumen route --prompt "..."               # hybrid tier plan (JSON)
lumen route --prompt "..." --router v2   # experimental learned router
lumen compare --baseline X --optimized Y # CI gate (+40%)
```

Example plan (`lumen route`):

```json
{
  "tier": "balanced",
  "model": "qwen2.5-3b-lumen",
  "reason": "balanced/domain (Lumen keywords)",
  "backend": "ollama",
  "path": "resident",
  "system_prompt": "..."
}
```

---

## Key idea

**Streaming fits oversized models — it does not speed up models that already fit in VRAM.**

Lumen wins by routing each prompt to the right model size (1B / LFM / fine-tuned 3B / 7B), not by making one 3B kernel 40% faster.

Soup: **train** → export GGUF → Lumen **serves** via hybrid router.

---

## Documentation

**Start here:** [**docs/README.md**](./docs/README.md) — full index with architecture diagrams, reference results, hardware limits, and enterprise case study.

| File | Contents |
|------|----------|
| [**docs/AGENT-INTEGRATION.md**](./docs/AGENT-INTEGRATION.md) | Hermes Agent + speed wins for agent loops |
| [**docs/TOOL-COMPARISON.md**](./docs/TOOL-COMPARISON.md) | Lumen vs Ollama, llama.cpp, LiteLLM, recent models |
| [**docs/TERMINAL-UI.md**](./docs/TERMINAL-UI.md) | **Terminal menu — full usage guide** |
| [**docs/REPO-LAYOUT.md**](./docs/REPO-LAYOUT.md) | Repository organization |
| [**docs/ARCHITECTURE.md**](./docs/ARCHITECTURE.md) | Detailed design + mermaid diagrams |
| [**docs/REFERENCE-RESULTS.md**](./docs/REFERENCE-RESULTS.md) | All benchmark numbers in one place |
| [**docs/HARDWARE-TESTING.md**](./docs/HARDWARE-TESTING.md) | 4GB lab limits + **contributor call** |
| [**docs/ENTERPRISE-CASE-STUDY.md**](./docs/ENTERPRISE-CASE-STUDY.md) | End-to-end enterprise narrative |
| [**CONTRIBUTING.md**](./CONTRIBUTING.md) | Collaborator onboarding |
| [**docs/ENTERPRISE.md**](./docs/ENTERPRISE.md) | Platform integration reference |
| [**docs/RESULTS.md**](./docs/RESULTS.md) | Chronological benchmark log |
| [**docs/MODELS.md**](./docs/MODELS.md) | Model setup |
| [**docs/SCALING.md**](./docs/SCALING.md) | OSS hardware profiles |
| [**docs/VISION.md**](./docs/VISION.md) | Goals and +40% thesis |
| [**docs/ROUTER-V2.md**](./docs/ROUTER-V2.md) | Learned linear router (experimental) |
| [**docs/HUGGINGFACE-PUBLISH.md**](./docs/HUGGINGFACE-PUBLISH.md) | Publish domain GGUF to HF Hub |
| [**docs/VLLM-BACKEND.md**](./docs/VLLM-BACKEND.md) | Optional vLLM backend (8GB+ GPUs) |
| [**benchmarks/PROTOCOL.md**](./benchmarks/PROTOCOL.md) | Fair measurement rules |

**Requirements:** Python 3.10+, [Ollama](https://ollama.com) for inference. Soup optional for training path.

MIT — see [LICENSE](./LICENSE).
