# AGENTS.md — Lumen Stream Lab

Project-specific instructions for AI agents working in this repository.

## Project overview

**Lumen Stream Lab** is an **open-source** orchestration layer that routes inference across Ollama models to beat the “always use one 3B-class model” baseline on decode throughput, while keeping Lumen-domain answers on a fine-tuned model.

**Reference lab** (where we CI-test): AMD Ryzen 5 5600H, 16 GB RAM, **NVIDIA GTX 1650 4 GB** — see `hardware/reference-lab.json`. This is **not** the only supported configuration. Contributors on 8–24 GB+ GPUs should probe locally, document profiles, and tune tiers without changing shared routing logic to assume 4 GB VRAM.

Read **`SCALING.md`** and **`CONTRIBUTING.md`** before hardcoding paths, tok/s, or model choices.

Stack roles:

| Tool | Role here |
|------|-----------|
| **Ollama** | Primary inference backend (resident path) |
| **Soup** | Training (LoRA + `stream_layers` on 4 GB GPU) |
| **AirLLM / Colibri** | Fit oversized models — **not** the speed path when a model already fits in VRAM |
| **Lumen router** | Hybrid tier selection (1B / LFM / qwen-lumen / 7B opt-in) |

**Do not confuse** “Lumen Stream Lab” (this ML orchestration project) with Laravel Lumen (PHP microframework).

---

## Primary success metric

**Relative gain (+40%)** is universal — measure baseline and orchestration mean **on your hardware**. Absolute tok/s below are **reference-lab only** (CI regression).

| Metric | Baseline (reference lab) | Target | Current on reference lab (2026-08-31) |
|--------|----------|--------|----------------------|
| Mean decode tok/s (12-prompt eval suite, hybrid auto-route) | `llama3.2:3b` @ **48.38** | **≥ 67.73** (+40%) | **70.02** (+44.7%) **PASS** |

Verification script (run on server after router changes):

```powershell
powershell -File D:\lumen-stream-lab\deploy\win-regression.ps1
```

Gate must pass before claiming a routing win. Use `-Full` to also run `win-router-eval.ps1` (~30 min).

Python check (Linux dev):

```bash
python3 scripts/compare.py --baseline 48.38 --optimized 70.02 --min-gain 0.40
```

**Same-model +40%** (one 3B class model faster in isolation) is **not** achieved — LFM alone is ~+35%. The lab win is **orchestration**, not kernel speed.

---

## Paths and environments

**Portable:** repo root + `lumen.yaml` + `hardware.json` (from probe). Use `LUMEN_LAB_ROOT` / `OLLAMA_MODELS` env vars — see `lumen.yaml.example`.

**Reference lab only** (do not require for OSS users):

| Location | Path |
|----------|------|
| Linux dev | `/media/taksha/New Volume1/lumen-stream-lab/` |
| Windows server | `D:\lumen-stream-lab` @ `192.168.4.31` (SSH user: `Taksha Thosani`) |
| Ollama models | `D:\ollama\models` |
| Soup/HF cache | `D:\lumen-stream-lab\cache\` |

**Before any Soup training on the server:**

```powershell
. D:\lumen-stream-lab\deploy\win-env-d.ps1
```

Deploy from Linux:

```bash
./deploy/push-to-server.sh   # or scp deploy/* to 192.168.4.31
```

Ollama over SSH: use `deploy/win-bench-with-serve.ps1` pattern (start `ollama serve` in the same session).

---

## Hybrid router (current production logic)

| Tier | Model | When |
|------|-------|------|
| `fast` | `llama3.2:1b` | Arithmetic, greetings, short facts (~110 tok/s) |
| `balanced` | `lfm-balanced` | General explain/coding (~66 tok/s) |
| `balanced` (domain) | `qwen2.5-3b-lumen` | Lumen Stream Lab / Soup / routing keywords (~56 tok/s) |
| `quality` | `qwen2.5-7b-lumen` | Prompt **>50 words** or forced `-Tier quality` (~11 tok/s) |

### Routing source of truth (keep in sync)

When changing routing rules, update **both**:

1. `deploy/win-router-lib.ps1` — Windows/PowerShell (server runtime)
2. `lumen_router.py` — Python (`lumen.py route`, gateway)

Test locally:

```bash
python3 lumen_router.py   # or: python3 -c "from lumen_router import route_decision; ..."
python3 lumen.py route --prompt "What is Lumen Stream Lab?"
```

Domain keywords are **strict** — do not re-add broad triggers like `decode tok/s`, `gtx 1650`, or bare `layer streaming` (causes false positives and hurts the +40% mean).

---

## Key commands

### Server (PowerShell)

```powershell
.\deploy\win-route.ps1 -Prompt "your question"
.\deploy\win-route.ps1 -Prompt "..." -Tier quality

powershell -File D:\lumen-stream-lab\deploy\win-orchestration-bench.ps1
powershell -File D:\lumen-stream-lab\deploy\win-regression.ps1
powershell -File D:\lumen-stream-lab\deploy\win-regression.ps1 -Full

.\deploy\win-s07-domain-smoke.ps1
.\deploy\win-create-lfm-alias.ps1
```

### Linux dev

```bash
./scripts/probe.sh
./scripts/bench.sh --backend ollama --model llama3.2:3b
python3 lumen.py probe
python3 lumen.py route --prompt "Explain TCP vs UDP"
```

---

## Reference lab training constraints (Soup, 4 GB VRAM)

**One profile, not a global limit.** Documented in `RESULTS.md` and `hardware/reference-lab.json` — violations cause OOM or BF16 amp crashes on the reference rig:

| Issue | Fix |
|-------|-----|
| 4-bit QLoRA on 7B | Use `quantization: none` |
| 7B/3B `stream_layers` OOM | `max_length: 64`, `stream_source: disk`, LoRA `r: 8` |
| 7B inference via `soup chat` | Use Ollama GGUF instead (full resident load fails on 4 GB) |
| `max_length: 128` on 3B stream | OOM at step 0 — stick to 64 unless re-tested |

Winning configs: `soup-7b-stream.yaml`, `soup-3b-stream-s07.yaml`, dataset `data/train-s07.jsonl` (184 rows).

---

## What to do / what not to do

### Do

- Run `win-regression.ps1` after any router or keyword change
- Record benchmarks in `RESULTS.md` with date, model, median tok/s
- Prefer **new model families** (Phase D2 style) over another Qwen LoRA loop
- Use hybrid routing: LFM for speed, `qwen2.5-3b-lumen` for Lumen domain
- Keep PowerShell scripts ASCII-only (no Unicode em-dashes — caused issues before)
- Source `win-env-d.ps1` before training

### Do not

- Loop on Qwen/Llama fine-tunes without a clear quality gap and eval plan
- Auto-route short prompts to 7B quality (kills throughput — ~10 tok/s)
- Use Nemotron Lightning or Gemma e4b for speed on 4 GB (bench results: unusable or marginal)
- Use speculative decode expecting +40% (measured ~1% on 3B — see `RESULTS.md` O01)
- Use AirLLM/Colibri streaming as baseline for models that fit in VRAM
- Commit secrets (`.env`, API keys)
- Edit `ENTERPRISE.md` for lab routing work — another agent owns that doc

---

## Documentation map

| File | Use when |
|------|----------|
| `STATUS.md` | Latest session state (start here) |
| `RESULTS.md` | Benchmark numbers and training log |
| `README.md` | Quick start and router tiers |
| `VISION.md` | +40% goal and honest expectations |
| `ARCHITECTURE.md` | Orchestrator design, speed vs I/O stack |
| `PLAYBOOK.md` | Soup / AirLLM / Colibri reference |
| `benchmarks/PROTOCOL.md` | Fair measurement rules |
| `lumen.yaml.example` | Orchestrator config template |
| `SCALING.md` | Hardware profiles, OSS scaling |
| `CONTRIBUTING.md` | Contributor workflow |
| `hardware/reference-lab.json` | Reference CI rig profile |
| `ENTERPRISE.md` | Enterprise narrative — **separate track, ignore for lab work** |

---

## Completed phases (do not re-litigate)

- **Baselines:** llama3.2:1b/3b, mistral 7B, speculative decode (no gain)
- **S06:** Qwen2.5-7B stream_layers train + Ollama export
- **S07:** Qwen2.5-3B domain fine-tune (`qwen2.5-3b-lumen`) — **production domain model**
- **S08:** 3B re-train max_length 96 — train PASS, domain quality **regressed**; rolled back to S07
- **Phase D2:** LFM, Gemma 4, Nemotron family bench — LFM wins balanced speed
- **Hybrid router:** +44.7% orchestration PASS, regression gate in place

---

## Open work (prioritized)

1. **Domain E12** — system prompt injected on domain route (implemented); run `win-domain-smoke-gate.ps1` on server. S10 micro-train scaffold ready if needed.
2. **Router eval with `-Full`**
3. **llama.cpp vs Ollama** resident bench

---

## File layout (agent-relevant)

```
lumen-stream-lab/
├── AGENTS.md                 ← this file
├── STATUS.md                 ← current state
├── RESULTS.md                ← benchmark log
├── lumen_router.py           ← Python routing (sync with win-router-lib.ps1)
├── lumen.py                  ← probe / bench / compare / route CLI
├── lumen.yaml.example
├── data/
│   ├── router-eval-prompts.json   ← E01–E12 eval suite
│   ├── domain-system-prompt.txt   ← injected on qwen2.5-3b-lumen calls
│   ├── train-s07.jsonl
│   └── train-s10-e12.jsonl        ← S10 E12 micro-curriculum
├── deploy/
│   ├── win-router-lib.ps1        ← PowerShell routing (primary on server)
│   ├── win-route.ps1             ← route + generate one prompt
│   ├── win-orchestration-bench.ps1
│   ├── win-regression.ps1        ← CI gate
│   ├── win-router-eval.ps1
│   ├── win-env-d.ps1
│   └── win-create-lfm-alias.ps1
├── results/
│   └── orchestration-bench-*.json
└── scripts/
    ├── compare.py
    └── lumen_gateway.py
```

---

## Agent workflow checklist

When making changes:

1. Read `STATUS.md` and relevant section of `RESULTS.md`
2. If touching routing: edit `win-router-lib.ps1` **and** `lumen_router.py`
3. Push to server (`deploy/` + `data/` if prompts changed)
4. Run `win-regression.ps1` on server — must PASS (+40%)
5. Update `RESULTS.md` / `STATUS.md` with numbers and date
6. Do not create git commits unless the user asks
