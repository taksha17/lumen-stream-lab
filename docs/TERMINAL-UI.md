# Terminal UI guide

Lumen Stream Lab includes an **interactive terminal menu** so you can probe hardware, chat with hybrid routing, benchmark models, and run the HTTP gateway without memorizing CLI flags.

## Prerequisites

1. **Python 3.10+** — stdlib only for the menu; no extra pip packages required for basic use.
2. **[Ollama](https://ollama.com)** installed and running:
   ```bash
   ollama serve          # if not already running as a service
   ollama pull llama3.2:1b
   ollama pull llama3.2:3b
   ```
3. **Optional tier models** — see [MODELS.md](./MODELS.md) for `lfm-balanced`, `qwen2.5-3b-lumen`, `qwen2.5-7b-lumen`.
4. Clone the repo and `cd` into it.

## Launch the menu

From the repo root:

```bash
python3 lumen.py
```

Equivalent commands:

```bash
python3 lumen.py menu
./lumen              # Linux/macOS
lumen.cmd            # Windows (double-click or from cmd)
```

You should see:

```
==========================================
  LUMEN STREAM LAB
  interactive menu
==========================================
```

Type a number and press Enter. After most actions, press Enter again to return to the menu.

---

## Menu options (step by step)

### 1) Setup check

Verifies your environment before you chat or bench.

- Prints OS, repo path, whether `ollama` is on `PATH`
- Pings `http://127.0.0.1:11434` (Ollama API)
- Checks for `hardware.json` (from `lumen probe`); offers to run probe if missing
- Lists up to 12 Ollama models
- Notes whether `lumen.yaml` exists

**If Ollama is not reachable:** start `ollama serve` in another terminal.

**First time on a machine:** run option **1**, accept the probe prompt, then pull models per [MODELS.md](./MODELS.md).

---

### 2) Chat (route + generate)

A **mini agent loop**: each message is routed to the best tier/model, then Ollama generates a reply.

Example session:

```
you> What is 2+2?

[tier=fast model=llama3.2:1b]
[reason: fast (arithmetic)]

4

--- 112.3 tok/s ---

you> What is Lumen Stream Lab?

[tier=balanced model=qwen2.5-3b-lumen]
[reason: balanced/domain (Lumen keywords)]

Lumen Stream Lab is a hybrid LLM orchestration layer...
```

**Chat commands**

| Command | Effect |
|---------|--------|
| `/quit`, `/exit`, `/q` | Leave chat and return to main menu |
| `/tier fast` | Force `fast` tier for following prompts |
| `/tier balanced` | Force `balanced` tier |
| `/tier quality` | Force `quality` tier (7B when available) |
| `/tier code` | Force experimental coder (opt-in; auto-route stays off) |
| `/tier auto` | Clear forced tier |

Routing logic lives in `lumen_router.py` (same rules as `lumen route` and the gateway).

---

### 3) Route one prompt (plan JSON only)

Prompts for a single user message and prints a **routing plan** as JSON — no generation.

Use this to debug tier selection or pipe into your own gateway:

```bash
# Same as menu option 3, but non-interactive:
python3 lumen.py route --prompt "Explain TCP vs UDP"
```

---

### 4) Bench a model

Runs one Ollama **generate** and samples **nvidia-smi** CUDA util + VRAM during decode (default `llama3.2:3b`, `num_predict=128`). Writes `results/bench-last.json` (gitignored).

Windows Task Manager **GPU 3D** often stays at 0% while CUDA is busy. Use this bench, `python3 lumen.py gpu`, or `deploy/win-gpu-check.ps1`.

Use this to establish your machine's baseline before claiming +40% orchestration gains.

---

### 5) +40% compare

Compares **baseline** (always 3B) vs **orchestration mean** tok/s against the 40% gate.

Defaults are pre-filled from `hardware/reference-lab.json` if present; you can enter your own numbers from option **4** and orchestration benches.

Runs `scripts/compare.py` and prints PASS/FAIL.

---

### 6) HTTP gateway

Starts the stdlib gateway on `http://127.0.0.1:8080` (port is configurable).

**Stays running** until you press Ctrl+C — you will not return to the menu until it stops.

Example (another terminal):

```bash
curl -s http://127.0.0.1:8080/v1/plan \
  -H 'content-type: application/json' \
  -d '{"prompt": "What is 2+2?"}'

curl -s http://127.0.0.1:8080/v1/chat \
  -H 'content-type: application/json' \
  -d '{"prompt": "What is Lumen Stream Lab?"}'
```

---

### 7) Backend shootout (Ollama vs llama.cpp)

- **Windows:** runs `deploy/win-bench-llamacpp-vs-ollama.ps1` if present.
- **Linux/macOS:** benches Ollama for a model you name, then optionally benches a local GGUF with llama.cpp and compares JSON outputs under `results/`.

On 4GB GPUs, Ollama usually wins for resident 3B models — see [REFERENCE-RESULTS.md](./REFERENCE-RESULTS.md).

---

### 8) Run router tests

Runs the CI parity suite:

```bash
python3 -m unittest discover -s tests -v
```

Verifies Python router matches expected tier/model for fixture prompts.

---

### 9) Open docs

Prints paths to key documentation files and the GitHub repo URL. Open the listed `.md` files in your editor or on GitHub.

---

### 0) Exit

Leaves the menu.

---

## One-shot CLI (without the menu)

| Command | Purpose |
|---------|---------|
| `lumen probe` | Write `hardware.json` |
| `lumen bench --model NAME` | Single-model bench |
| `lumen route --prompt "..."` | JSON routing plan |
| `lumen compare --baseline X --optimized Y` | +40% gate |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Ollama is not running` | `ollama serve` |
| Generate fails / model not found | `ollama pull <model>` — see [MODELS.md](./MODELS.md) |
| Domain answers generic | Ensure `qwen2.5-3b-lumen` is installed; domain system prompt is applied automatically for domain tier |
| Slow first reply | Model cold-load; second prompt is faster |
| Menu shows wrong title | Banner should read **LUMEN STREAM LAB** (equals signs, no box-drawing pipes) |

---

## Related docs

- [README.md](../README.md) — project overview
- [MODELS.md](./MODELS.md) — required Ollama models
- [ARCHITECTURE.md](./ARCHITECTURE.md) — how routing works
- [REPO-LAYOUT.md](./REPO-LAYOUT.md) — where files live
