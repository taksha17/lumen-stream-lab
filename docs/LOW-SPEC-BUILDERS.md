# Low-spec builders & enterprise scale — who Lumen is for

Lumen was **built and proven on a GTX 1650 4GB laptop** — not on a datacenter. The same orchestration pattern scales from that box to a team fleet. This doc balances two audiences:

| Audience | Primary need | Lumen's job |
|----------|--------------|-------------|
| **Individuals** (limited GPU, offline, privacy) | Usable AI on hardware you already own | Route each prompt to the smallest model that works |
| **Enterprises** (many users, cost pressure, compliance) | Cut per-seat cloud spend without losing quality on hard tasks | Hybrid local + cloud routing with measured tiers and audit |

**Related:** [HARDWARE-TESTING.md](./HARDWARE-TESTING.md) · [ENTERPRISE.md](./ENTERPRISE.md) · [ENTERPRISE-CASE-STUDY.md](./ENTERPRISE-CASE-STUDY.md) · [SCALING.md](./SCALING.md)

---

## Part 1 — Individuals on limited hardware

### You are the reference design, not an afterthought

Our CI reference rig is a **4GB consumer GPU** ([`hardware/reference-lab.json`](../hardware/reference-lab.json)). The +40% orchestration gate was measured there. Enterprise topology docs describe *where the same router plugs in at scale* — they are not saying you need a workstation to start.

### The trap on low specs

Most people do this:

```
every prompt → one 3B or 7B model → slow, hot, frustrating
```

On 4GB VRAM, always using `llama3.2:3b` caps you at ~49 tok/s for **everything** — arithmetic, greetings, and long essays alike. Always using 7B drops to ~10 tok/s and can OOM.

### What Lumen does instead

```
"What is 2+2?"              → fast (1B)      ~99 tok/s
"Explain TCP vs UDP"        → balanced (LFM)  ~64 tok/s
"What is Lumen Stream Lab?" → domain (3B)     ~56 tok/s
800-word analysis           → quality (7B)    ~10 tok/s (opt-in)
```

**Mean ~68 tok/s vs always-3B at ~49** — same GPU, no new hardware. You are not making one kernel faster; you are **not using the wrong model for the job**.

### Offline and secure (no cloud required)

| Component | Leaves your machine? |
|-----------|-------------------|
| Ollama + local GGUF | No — inference on your box |
| `lumen.py` / terminal menu | No — stdlib Python, no telemetry |
| `scripts/lumen_gateway.py` | No — binds `localhost` by default |
| Soup training → GGUF → Ollama | No — full loop can stay air-gapped |
| Hugging Face | **Optional** — only if you choose to publish or pull models |

For builders who need **privacy, air-gap, or "no API keys"**, Lumen is a routing layer on top of local inference — not a SaaS wrapper.

### 30-minute playbook (low VRAM)

```bash
git clone https://github.com/taksha17/lumen-stream-lab.git
cd lumen-stream-lab

# Routing demo — no Ollama required
./scripts/demo.sh

# Your machine profile
python3 lumen.py probe          # → hardware.json
cp lumen.yaml.example lumen.yaml
# set vram_class: low

# Minimal model set (see MODELS.md)
ollama pull llama3.2:1b
ollama pull llama3.2:3b
# optional domain: hf download + ollama create (see MODELS.md)

python3 lumen.py                # menu → chat (option 2)
```

**Target:** measure +40% vs **your** always-3B baseline on **your** hardware — not our reference 48.38 tok/s.

### What you can realistically build

| Project | 4GB feasible? | Notes |
|---------|---------------|-------|
| Local Q&A / domain bot | Yes | Fine-tuned 3B + router |
| CLI assistant | Yes | `lumen.py` menu or gateway |
| Simple agent loop | Yes | Gateway routes each step ([AGENT-INTEGRATION.md](./AGENT-INTEGRATION.md)) |
| Short-doc summarizer | Yes | Chunk input; force `fast` or `balanced` |
| Private coding helper (offline) | Partial | Good for explain/refactor; not GPT-4 class |
| Always-on 7B default | No | ~10 tok/s — quality tier only |
| Train your own domain model | Yes | Soup `stream_layers`, `max_length: 64` on 4GB |

### Honest limits (4GB class)

| Expectation | Reality |
|-------------|---------|
| Run any model resident | No — tier by VRAM |
| Match frontier cloud models | No — smaller local models, domain-tuned where it matters |
| Faster without routing | Unlikely on our lab — llama.cpp lost to Ollama on same GGUF |
| Build useful things offline | **Yes** — hybrid routing is the lever |

See [HARDWARE-TESTING.md](./HARDWARE-TESTING.md) for the full can/cannot matrix.

---

## Part 2 — Teams and enterprises at scale

### Same router, bigger box

The integration contract does not change when you scale:

```
client → gateway (auth, rate limit) → Lumen route → backend pool
```

On a laptop that is Ollama on `localhost`. On a team fleet it is the same `lumen_gateway.py` (or your gateway) behind SSO, pointing at a **pool** of Ollama / vLLM nodes. Routing logic, plan JSON, and regression gates stay identical.

**Reference topology:** [ENTERPRISE.md](./ENTERPRISE.md) §4 · **Narrative walkthrough:** [ENTERPRISE-CASE-STUDY.md](./ENTERPRISE-CASE-STUDY.md)

### Why not "just buy Claude Enterprise"?

Cloud subscriptions (Claude Team, Claude Enterprise, ChatGPT Enterprise, etc.) solve a different problem well:

- Zero GPU ops
- Frontier reasoning on the hardest tasks
- Vendor-managed uptime and safety

They also create **structural cost** when every employee query — including "what is 2+2?" and "reformat this JSON" — hits the same expensive API or per-seat bundle.

Lumen does not replace frontier cloud for **everything**. It replaces **blind routing** — paying cloud prices for work a 1B or 3B local model handles fine.

### Illustrative cost model (not a quote — run your own numbers)

> **Disclaimer:** Cloud list prices and enterprise contracts vary by region, volume, and negotiation. Treat the table below as **order-of-magnitude planning math**, not a guarantee.

| Line item | All-cloud pattern | Lumen hybrid pattern |
|-----------|-------------------|----------------------|
| **200 knowledge workers** | e.g. $40–80/user/mo list → **$8k–16k/mo** recurring | Smaller cloud budget + local inference capex |
| **Workload split** | 100% to vendor API | **60–85% local** (short, structured, domain) · **15–40% cloud** (hard reasoning, long context) |
| **Infra** | $0 capex | 1–4 GPU nodes (amortized) + electricity + 0.5–1 FTE platform |
| **Data residency** | Contract + DPA dependent | Sensitive prompts stay on-prem by default |
| **Audit** | Vendor logs | Per-request `tier`, `model`, `reason` in plan JSON |
| **Regression** | Manual "model feels worse" | `lumen compare` + router CI gates |

**Example sketch (200 users, illustrative only):**

```
All-cloud:     200 × $60/mo  ≈ $12,000/mo  ≈ $144,000/year

Hybrid:
  Local:       2× mid GPU servers ≈ $12k–24k one-time (24–36 mo amortize)
  Cloud:       25% of queries to frontier API ≈ $2k–4k/mo (volume-dependent)
  Ops:         part-time platform engineer

Year-1 hybrid total (rough): $40k–80k all-in vs $144k all-cloud
```

Savings grow with **query volume** and **repetitive internal tasks** (support macros, log triage, doc lookup, code explain). Savings shrink if every user needs frontier reasoning all day.

### How orchestration reduces spend

| Mechanism | Cost effect |
|-----------|-------------|
| **Tiered routing** | Bulk traffic at ~1B/3B local cost ≈ electricity, not per-token |
| **Domain fine-tune on-prem** | Stop paying cloud to relearn your product every session |
| **Agent loops** | 10-step agent × cloud = 10× billing; Lumen routes cheap steps to 1B ([AGENT-INTEGRATION.md](./AGENT-INTEGRATION.md)) |
| **Quality opt-in** | 7B / cloud only when prompt length or keywords justify it |
| **Backend shootout** | Pick Ollama vs vLLM vs llama.cpp per GPU — avoid slow expensive misconfig |
| **Regression gates** | Catch "we swapped models and got slower" before production rollouts |

### Hybrid architecture (enterprise)

```
                    ┌─────────────────────────────────┐
  Employees / apps  │  SSO + API gateway + rate limit │
                    └───────────────┬─────────────────┘
                                    ▼
                    ┌─────────────────────────────────┐
                    │  Lumen router                   │
                    │  - route 70% locally            │
                    │  - escalate 30% to cloud        │
                    │  - plan JSON for audit          │
                    └───────┬─────────────┬───────────┘
                            ▼             ▼
              ┌──────────────────┐  ┌──────────────────┐
              │ Local pool       │  │ Cloud API        │
              │ Ollama / vLLM    │  │ Claude / GPT / … │
              │ 1B / LFM / 3B    │  │ hard tasks only  │
              │ domain fine-tune │  │                  │
              └──────────────────┘  └──────────────────┘
```

**Escalation rules** (examples — tune per org):

- Local: token count &lt; 500, no "legal review" / "architecture" keywords, internal doc RAG hit
- Cloud: novel reasoning, cross-doc synthesis, policy edge cases, user explicitly requests "best quality"

Lumen's keyword + length router is the **starting policy**; production teams often add a learned router ([ROUTER-V2.md](./ROUTER-V2.md)) or rules from their own logs.

### Pairing with other resources (not Lumen alone)

Lumen orchestrates **inference**. Enterprises still combine it with:

| Resource | Role with Lumen |
|----------|-----------------|
| **Existing GPU fleet / K8s** | Lumen plan → vLLM endpoint ([VLLM-BACKEND.md](./VLLM-BACKEND.md)) |
| **Vector DB / RAG** | Retrieve context → Lumen routes *generation* tier by prompt shape |
| **IdP / SSO** | Gateway auth before `lumen route` |
| **Observability** | Log `lumen_plan` per request; SLO on p95 latency by tier |
| **Soup / fine-tune pipeline** | Train domain 3B once → route internally forever |
| **Cloud API (Claude, etc.)** | Fallback backend for escalated tier — not default for all traffic |

**Cost reduction comes from the split**, not from deleting cloud entirely.

### When cloud enterprise still wins

| Situation | Recommendation |
|-----------|----------------|
| &lt; 20 users, low volume | Cloud may be cheaper than GPU + ops |
| No compliance need for on-prem | Hybrid optional |
| Work is 90%+ frontier reasoning | Pay for cloud; use Lumen only for pre/post processing |
| No one to run inference | Managed SaaS is rational |
| Burst to 10k concurrent users | Cloud autoscale + local cache tier |

### When Lumen hybrid wins

| Situation | Recommendation |
|-----------|----------------|
| Code / PII cannot leave LAN | Local default + cloud escalation |
| High daily query volume per seat | Tiered local routing |
| Repetitive internal support / dev tools | 1B + domain 3B |
| Agent workflows (many LLM calls per task) | Per-step routing ([AGENT-INTEGRATION.md](./AGENT-INTEGRATION.md)) |
| Leadership wants unit economics | Measured tok/s and `$ / 1M tokens` by tier |

---

## One sentence for each audience

**Individual:** *"Get the most out of the GPU you already have — offline, measured, without buying a new card."*

**Enterprise:** *"Stop paying frontier prices for frontier-easy work — route locally by default, cloud by exception, audit every decision."*

---

## Next steps

| If you are… | Start here |
|-------------|------------|
| Solo builder, 4–8GB GPU | `./scripts/demo.sh` → `python3 lumen.py` → [MODELS.md](./MODELS.md) |
| Team evaluating hybrid | [ENTERPRISE-CASE-STUDY.md](./ENTERPRISE-CASE-STUDY.md) → `scripts/lumen_gateway.py` |
| Stronger GPU contributor | [HARDWARE-TESTING.md](./HARDWARE-TESTING.md) contributor call |
| Cost / procurement stakeholder | Build a 2-week pilot: measure % local-routable traffic + bench tok/s by tier |

Questions: [GitHub issues](https://github.com/taksha17/lumen-stream-lab/issues/new/choose) with `hardware-profile` or `enterprise` label.
