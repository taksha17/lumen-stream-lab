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

Numbers from [`hardware/reference-lab.json`](./hardware/reference-lab.json) — **your machine will differ**; measure your own baseline.

| Metric | Result |
|--------|--------|
| Baseline (always `llama3.2:3b`) | **48.38 tok/s** |
| **Lumen hybrid orchestration** | **~68–70 tok/s** mean (**+40–45% PASS**) |
| vs llama.cpp (same 3B GGUF) | Ollama **48.2** vs llama.cpp **16.5** tok/s |
| Router eval routing accuracy | **12/12** prompts |
| Domain quality (E11/E12) | PASS with domain system prompt |

| Tier | Model | When |
|------|-------|------|
| `fast` | `llama3.2:1b` | Arithmetic, greetings, short facts |
| `balanced` | `lfm-balanced` | General explain/coding (~65 tok/s) |
| `balanced` (domain) | `qwen2.5-3b-lumen` | Lumen / Soup / routing keywords |
| `quality` | `qwen2.5-7b-lumen` | Prompt >50 words or `-Tier quality` |

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

## Integration API

```bash
lumen probe                              # hardware.json
lumen bench --model llama3.2:3b          # benchmark a model
lumen route --prompt "..."               # hybrid tier plan (JSON)
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
| [**benchmarks/PROTOCOL.md**](./benchmarks/PROTOCOL.md) | Fair measurement rules |

**Requirements:** Python 3.10+, [Ollama](https://ollama.com) for inference. Soup optional for training path.

MIT — see [LICENSE](./LICENSE).
