# Agent framework integration

How to plug **Lumen** into agentic tools (Hermes Agent, custom loops) so each LLM step uses the **fastest appropriate model** instead of always hitting one 3B model.

Measured gain on reference lab: **+40.8%** mean decode tok/s vs always `llama3.2:3b` ([TOOL-COMPARISON.md](./TOOL-COMPARISON.md)).

---

## What Lumen adds to an agent

Agent frameworks spend most wall time in **repeated LLM calls** (plan → tool → observe → reply). If every call uses `llama3.2:3b`:

| Step type | Example | Better tier |
|-----------|---------|-------------|
| Tool arg parsing | "extract JSON from …" | `fast` (1B) |
| General reasoning | "summarize this log" | `balanced` (LFM) |
| Project-specific | "What is Lumen Stream Lab?" | domain 3B |
| Long analysis | 800-word paste | `quality` (7B, opt-in) |

Lumen picks the tier **per message** before Ollama generates — same pattern as a production API gateway, local on your GPU.

---

## Architecture

```
Hermes Agent (tool loop)
        │
        ▼
  Lumen gateway :8080          ← routes each prompt
        │
        ▼
  Ollama (1B / LFM / 3B / 7B)
```

Hermes does **not** need to know about tiers — point it at Lumen’s HTTP surface or call `lumen route` before each Ollama request.

---

## Option A — Lumen HTTP gateway (recommended)

Start the gateway (from repo root):

```bash
python3 lumen.py probe   # once
python3 scripts/lumen_gateway.py --port 8080
```

**Endpoints:** `/v1/plan`, `/v1/chat`, **`/v1/chat/completions`** (OpenAI shape for Hermes/LiteLLM), `/v1/models`, `/v1/health`

### Hermes / OpenAI-compatible clients

Point `base_url` at `http://127.0.0.1:8080/v1`:

```bash
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"lumen-hybrid","messages":[{"role":"user","content":"What is 2+2?"}]}'
```

Response includes `choices[0].message.content` plus `lumen_plan` (tier, model, reason).

### Simple agent loop (curl)

```bash
# One agent turn: route + generate
curl -s http://127.0.0.1:8080/v1/chat \
  -H 'content-type: application/json' \
  -d '{"prompt": "List files in the current directory and suggest next step"}'
```

Response includes `plan` (tier, model, reason) and `response` text — log `plan` for audit.

### Routing plan only (you call Ollama)

```bash
curl -s http://127.0.0.1:8080/v1/plan \
  -H 'content-type: application/json' \
  -d '{"prompt": "What is 2+2?"}'
```

Use returned `model` in your agent’s Ollama client for that step.

---

## Option B — [Hermes Agent](https://github.com/NousResearch/hermes-agent) + Ollama

Hermes is a local agent framework (tools, memory, profiles). By default it uses one Ollama model per profile — often `llama3.2:3b` for everything.

### Speed win without changing Hermes code

1. **Run Lumen gateway** on `:8080` (Option A).
2. In Hermes, for **lightweight steps** (title generation, compression, short classifiers), use a separate profile pointing at `llama3.2:1b` or call `/v1/plan` and switch models per step.
3. Keep a **domain profile** on `qwen2.5-3b-lumen` for project-specific tools.

### Native Ollama transport

Hermes + Ollama users often install [`hermes-ollama-native`](https://pypi.org/project/hermes-ollama-native/) so tool calls stream correctly via `/api/chat` instead of the broken `/v1` compat path. Lumen is **orthogonal** — it sits **above** Ollama and picks which model Hermes should target each turn.

```bash
pip install hermes-ollama-native
set HERMES_OLLAMA_NATIVE=1   # Windows
# export HERMES_OLLAMA_NATIVE=1  # Linux
```

### Windows reference lab setup script

```powershell
powershell -File deploy\win-setup-hermes.ps1
```

This checks Python, optionally installs `hermes-ollama-native`, and prints a sample Hermes `config.yaml` snippet using Lumen-routed models.

---

## Option C — Python agent hook (minimal)

```python
from lumen_router import route_decision
import json, urllib.request

def agent_llm(prompt: str) -> str:
    decision = route_decision(prompt, "auto")
    model = decision["model"]
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    return data["response"]
```

Use in any agent loop (LangChain, AutoGen, custom) where you control the LLM call site.

---

## Expected impact on agent latency

Reference lab (GTX 1650), single decode step:

| Policy | ~tok/s | Agent impact |
|--------|--------|----------------|
| Always 3B | 49 | Baseline step latency |
| Lumen hybrid (typical mix) | **68** mean | **~30% faster** per routed step |
| Always 1B | 99 | Fastest; quality risk on hard steps |

Multi-step agents compound the win: 10 steps × 30% faster decode ≈ noticeably snappier sessions, without rewriting tool code.

---

## Limits

- Lumen routes **local Ollama models** — not a replacement for cloud APIs Hermes may use for frontier models.
- Tool-calling correctness is Hermes + Ollama’s job; Lumen only picks **which** local model runs.
- Re-bench on your GPU; see `deploy/win-bench-phase-d3.ps1` and [REFERENCE-RESULTS.md](./REFERENCE-RESULTS.md).

---

## Related

- [ENTERPRISE.md](./ENTERPRISE.md) — gateway topology for platform teams
- [TERMINAL-UI.md](./TERMINAL-UI.md) — menu option 6 starts the gateway
- [TOOL-COMPARISON.md](./TOOL-COMPARISON.md) — vs other OSS tools
