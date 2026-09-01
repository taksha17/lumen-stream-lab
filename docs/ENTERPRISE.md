# Lumen Stream Lab — Enterprise Integration Reference

> **Audience:** platform / infra / ML-platform engineers wiring a local LLM stack into a real production system.  
> **Narrative case study:** [docs/ENTERPRISE-CASE-STUDY.md](./docs/ENTERPRISE-CASE-STUDY.md) — end-to-end "Acme Platform" walkthrough with metrics.  
> **Numbers:** [REFERENCE-RESULTS.md](./REFERENCE-RESULTS.md) on reference lab (GTX 1650 4GB). The *shape* of integration applies on bigger hardware.

---

## 1. What Lumen actually is (one paragraph)

`lumen.py` is a **decision layer** that sits *between* an inference client and the inference engines (Ollama, llama.cpp, AirLLM, Colibri). Its only job is to answer three questions per request:

1. **Fit** — will this model load at all on this box, or do we have to stream layers/experts? (`probe` → `hardware.json` + model VRAM estimator)
2. **Path** — given the answer to (1), which backend is fastest *for that model on that hardware right now*? (`bench` → `results/baseline.json` → `route`)
3. **Stack** — which orthogonal optimizations should we layer on top of the chosen backend? (`speed_stack` from `lumen.yaml`: speculative decode, KV quant, ctx size, gpu_layers, threads, power profile)

It is **not** a model server, **not** a finetune runner (that's Soup), **not** a vector store. It's a thin router + config applier that produces a *plan* the calling service executes.

That thinness is the whole product.

---

## 2. The enterprise gap it fills

Most teams running local LLMs hit the same wall:

| Stage | Symptom | What they try | Why it fails |
|-------|---------|---------------|--------------|
| 1 | "Ollama is slow for our 8B" | Switch to vLLM, AirLLM, etc. | Wrong baseline — they were already on the fastest tool, just for the wrong model |
| 2 | "AirLLM is slow for our 3B" | Cache layers, switch quant | Streaming tax on a model that fits resident — kills speed |
| 3 | "Fine-tuning the model would help" | Train on Soup | Now they have a fine-tuned GGUF that *still* runs at the same 9 tok/s because nothing above changed |
| 4 | "We need tiered responses" | Hand-roll a router | Hardcoded rules, no measurement, no rollback when a model regresses |

Lumen is the missing layer between **"we have models"** and **"we ship responses"**. It makes the *routing + tuning* decision **data-driven, reproducible, and benchmarked** instead of tribal.

The orchestrator pattern itself is identical to what Frontier companies do internally (think vLLM's `router` for multi-LoRA, Anyscale's `LLMRouter`, OpenAI's model-routing in their gateway). Lumen is the same pattern, scoped to *one box, one model class, one decision*.

---

## 3. The integration contract

Anything that wants to use Lumen calls exactly four things. This is the public API:

```bash
lumen probe                            # one-time per host: write hardware.json
lumen bench --model <name> --backend <b>   # one-time per (model, backend): write results/bench-<m>-<b>.json
lumen route --model <name>                 # per request: returns JSON plan
lumen compare --baseline X --optimized Y   # CI gate: pass if >= +40%
```

The **plan schema** is the integration contract. Current shape (from `lumen.py::cmd_route`):

```json
{
  "model": "qwen2.5-7b-instruct-q4_0",
  "vram_mb": 4096,
  "path": "stream",          // resident | stream
  "backend": "airllm",       // ollama | llamacpp | airllm | colibri
  "speed_stack": {
    "speculative_draft": "llama3.2:1b",
    "note": "Use resident path for speed; streaming only if model exceeds VRAM"
  }
}
```

**Everything downstream is built on that plan.** You can swap Ollama for vLLM, swap the planner for a learned router, swap the YAML for a remote config — the *contract* is the same.

---

## 4. Where it plugs in — real enterprise topologies

### 4.1 Inference gateway (most common)

```
                    ┌──────────────────────────┐
   client / app ──▶ │  API gateway / proxy      │  ← auth, rate limit, logging
                    └─────────────┬────────────┘
                                  ▼
                    ┌──────────────────────────┐
                    │  Lumen router service    │  ← calls `lumen route` per request
                    │  - reads hardware.json   │
                    │  - reads bench results   │
                    │  - reads lumen.yaml      │
                    │  - emits plan JSON       │
                    └─────────────┬────────────┘
                                  ▼
                    ┌──────────────────────────┐
                    │  Backend pool            │
                    │  - ollama (resident)     │
                    │  - llamacpp (resident)   │
                    │  - airllm (stream)       │
                    │  - colibri (MoE stream)  │
                    └──────────────────────────┘
```

**Reference impl in this repo:** `scripts/lumen_gateway.py` (added in §7). HTTP server on `:8080`, POST `/v1/chat`, plan emitted per request, response proxied to the chosen backend.

### 4.2 Agent framework backend

If you run an agent framework (LangChain, LlamaIndex, custom), the typical pattern is one LLM client per agent. Lumen replaces the *factory* that creates that client:

```python
# before
from langchain_community.llms import Ollama
llm = Ollama(model="qwen2.5-7b-instruct-q4_0")

# after
from lumen_client import LumenLLM
llm = LumenLLM.from_request({"task": "code_review", "max_quality": True})
# LumenLLM internally: lumen route → open Ollama client with speed_stack applied
```

This is the way you get **per-task model selection** (cheap model for summarization, expensive model for code review) without hardcoding it in the agent.

### 4.3 MLOps training → serving pipeline

This is the **train → export → route** path already in `docs/internal/STATUS.md` and `docs/RESULTS.md`:

```
   data.jsonl
      │
      ▼
   Soup train (stream_layers, 4bit, LoRA)   ← 7B on 4GB box
      │  output: <run>/merged/
      ▼
   GGUF export (q4_k_m)                    ← 4.4 GB
      │
      ▼
   Ollama deploy (ollama create qwen2.5-7b-lumen)   ← 9.62 tok/s baseline
      │
      ▼
   Lumen route + speed_stack               ← target ≥ +40%
      │
      ▼
   serve
```

Lumen's job in this loop is the **last step**: when the freshly-exported GGUF comes out, route it, stack optimizations on it, and *prove* it ships faster than the upstream baseline. Without Lumen that step is folklore.

### 4.4 Cost / capacity planner

Because `bench` writes structured JSON with `(model, backend, tok_s, vram_mb)`, the same data feeds:

- **Capacity planning:** "if we add N concurrent users at 30 tok/s, we need M GPUs"
- **Cost model:** $/1M tokens by routing tier (fast 1B vs balanced 3B vs quality 7B)
- **Regression detection:** compare today's `bench` JSON to last week's; alert on >5% drop

A reference consumer is `scripts/bench_history.py` (added below) — append-only JSONL of every bench run, with `git diff`-style review.

---

## 5. The complex tasks it actually unlocks

These are not hypothetical. They fall out of the architecture above:

### 5.1 Tiered cost/quality routing

You have a fine-tuned 7B (your domain expert) and a stock 1B. Same prompt, different cost.

```python
plan = lumen_route("summarize this 2000-word legal doc")
# returns { tier: "fast", backend: "ollama", model: "llama3.2:1b" }
# for short, low-stakes queries → 1B is enough

plan = lumen_route("draft a counter-claim citing precedent")
# returns { tier: "quality", backend: "ollama", model: "qwen2.5-7b-lumen" }
# for high-stakes, domain-specific → must use fine-tuned 7B
```

**What this gives you:** a single API that does both, with the routing decision **measured** (not vibe-coded). Your support team gets cheap responses by default, with an explicit opt-in for quality. The router is auditable.

### 5.2 Latency-bounded agent loops

Agents often have hard latency budgets (e.g. tool-use must respond in <2s). Lumen's plan includes the cost:

```python
plan = lumen_route("classify intent", deadline_ms=2000)
if plan.estimated_ttft_ms > 2000:
    plan = lumen_route("classify intent", force_tier="fast")
```

A simple extension to `lumen.py` adds `estimated_ttft_ms` and `estimated_tok_s` fields from `bench` history. The agent's executor now has a *budget* not just a model name.

### 5.3 Cross-model A/B at the gateway

```python
# 1% of traffic mirrored to candidate model
if random.random() < 0.01:
    plan = lumen_route(prompt, force="qwen2.5-7b-instruct-q4_0")
else:
    plan = lumen_route(prompt)

# log both, compare on quality eval set offline
```

Standard practice. The point is: **Lumen is the place that decides the model name**, so this A/B lives in one file, not scattered across the app.

### 5.4 Adaptive fall-back when VRAM is contested

If the box is shared and a co-tenant has pinned VRAM, Ollama falls back to CPU. A Lumen-aware gateway can detect this and re-route:

```python
plan = lumen_route(model)
try:
    response = call(plan.backend, plan.model, prompt)
except VRAMExhausted:
    plan = lumen_route(model, force_path="stream", force_backend="airllm")
    response = call(plan.backend, plan.model, prompt)
```

Single point of failure handling. Without Lumen, every caller reimplements it.

### 5.5 Speculative decode on the cheap

`lumen.yaml.example` already has `speed_stack.speculative`. With a 1B draft verifying a 3B target and a 0.60 acceptance rate, published numbers (and the speed-stack math in `ARCHITECTURE.md` §"Speed stack") show **+25–50%** on resident 3B/7B. Lumen makes this a config flag, not a kernel project.

### 5.6 A *real* +40% claim (the one in RESULTS.md)

From `RESULTS.md`:

- B01 baseline: `llama3.2:3b` @ 48.38 tok/s
- R03 after Lumen router + fast tier: 109.12 tok/s on "What is 2+2?"
- That's **+125%** for that prompt class.

The orchestrator's claim is *not* "the 3B is now 2x faster" — it's "**we picked a smaller model for the right query, and the speed of the wrong-sized model on every query is what was leaving the +40% on the table**." That's an enterprise-level finding: most "slow LLM" problems are *routing* problems.

---

## 6. What Lumen is **not** — and what to use instead

| Need | Use this, not Lumen |
|------|---------------------|
| Production auth + rate limiting + audit log | API gateway (Kong, Envoy, custom FastAPI) |
| Token streaming, SSE, WebSocket | Ollama / llama.cpp / vLLM directly |
| Conversation memory / RAG | Vector store + agent framework |
| Training | Soup (already in pipeline) |
| Distributed inference across boxes | vLLM, SGLang, Ray Serve |
| GPU sharing / MIG | NVIDIA runtime, vLLM PagedAttention |
| Frontier 100B+ at usable speed | Not on a 4GB box, period |

Lumen is the **decision layer** above these. It does not replace them.

---

## 7. Reference implementation (added in this repo)

### 7.1 `scripts/lumen_gateway.py`

Tiny HTTP gateway that uses `lumen route` per request. Demonstrates the §4.1 topology without any extra dependencies.

- POST `/v1/chat` → `lumen route --model X` → proxy to Ollama
- POST `/v1/plan` → returns the plan only (useful for debugging and agents that want to choose)
- GET  `/v1/health` → probe + bench freshness
- Streams SSE if `Accept: text/event-stream`

See file for full code (~150 lines, stdlib only).

### 7.2 `scripts/bench_history.py`

Appends every `bench` JSON to `results/bench-history.jsonl` and prints a markdown table comparing newest to the previous N runs. Lets you spot regressions the same way you'd spot them in a CI dashboard.

### 7.3 `lumen.yaml.example` (already present, copy to `lumen.yaml`)

The config that drives `route` and the speed stack. Comments call out which knob is **per-host** vs **per-model** vs **per-request** — important when you have multiple boxes with different VRAM.

---

## 8. How this maps to the +40% goal

The +40% in `VISION.md` is the *lab metric* — same model, same quant, faster on this box. The **enterprise value** is broader:

| Lab goal | Enterprise value |
|----------|------------------|
| Measure baselines (`bench`) | Capacity / cost model |
| Route to fastest backend | Per-request cost optimization |
| Stack speculative + KV + threads | Latency-bounded serving |
| Compare with `compare.py` | Regression gate in CI |
| Train → export → route loop | MLOps pipeline integration |

A team that adopts Lumen doesn't just get "1.4x faster" on one model. They get a **measurement-driven inference layer** that they can extend, audit, and reason about — which is what "enterprise AI layer" usually means when the procurement team writes the requirements doc.

---

## 9. Where to go next

1. **Run the gateway** (`scripts/lumen_gateway.py`) and point your existing app at it. No app changes beyond the base URL.
2. **Add `bench_history.py` to cron** so you always know what each model is doing on this box.
3. **Wire `lumen compare` into CI** as the regression gate for any change to `lumen.yaml`, model GGUF, or backend version.
4. **Replace the static `lumen route` with a learned router** (small classifier) trained on your actual `bench` + request log. The orchestrator's plan schema stays the same; only the planner changes.

The investment to get going is small. The payoff is that "which model should we use" stops being a Slack thread and starts being a measured, reproducible decision.
