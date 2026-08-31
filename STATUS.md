# Session Status — updated 2026-08-31 17:00

## OSS scaling (2026-08-31)

Project framed for open source: **reference lab** (`hardware/reference-lab.json`) for CI; contributors probe locally. See `SCALING.md`, `CONTRIBUTING.md`, updated `lumen.yaml.example`.

## Production: hybrid router + S07 domain model

| Step | Result |
|------|--------|
| Hybrid router | **+42% PASS** (68.69 tok/s with S07 domain model) |
| Domain model | `qwen2.5-3b-lumen` = **S07 GGUF** |
| Regression | `win-regression.ps1` ALL PASS |

```powershell
powershell -File D:\lumen-stream-lab\deploy\win-regression.ps1
powershell -File D:\lumen-stream-lab\deploy\win-domain-smoke-gate.ps1
```

## S09 curriculum — partial win, not promoted

| Step | Result |
|------|--------|
| Approach | 54 domain rows + 35% S07 replay, lr 8e-5, 6 min train |
| E11 Laravel | **Improved** (gate PASS) |
| E12 definition | **Still FAIL** (telecom Lumen) |
| Action | Auto-rollback to S07 via `win-post-s09.ps1` |

## Domain system prompt + context prefix (2026-08-31) — **PASS on server**

| Check | Result |
|-------|--------|
| Domain gate (E11/E12/E05) | **PASS** with `domain-system-prompt.txt` + targeted prompt prefixes |
| Orchestration +40% | **PASS** — 69.59 tok/s mean (+43.8%) after E05 transient retry |
| S10 train | **Not needed** — prompt injection fixed E12 without retrain |

**On server:**

```powershell
powershell -File D:\lumen-stream-lab\deploy\win-domain-smoke-gate.ps1
powershell -File D:\lumen-stream-lab\deploy\win-regression.ps1
```

### Still queued

_None — see AGENTS.md for future ideas (HF model release, learned router)._

## Tooling shipped (2026-08-31)

| Item | Path |
|------|------|
| Backend shootout | `scripts/bench_backends.py`, `deploy/win-bench-llamacpp-vs-ollama.ps1` |
| Model setup guide | `docs/MODELS.md` |
| CI | `.github/workflows/ci.yml` |
| Bench fixture | `results/fixtures/router-eval-summary.json` |

## Full router eval (2026-08-31) — **PASS**

`win-regression.ps1 -Full` (~8.7 min on server):

| Metric | Result |
|--------|--------|
| Routing accuracy | **12/12** |
| Median decode | fast **94.9** \| LFM **63.7** \| domain **54.6** \| quality **10.6** tok/s |
| Orchestration (live gate) | **69.78 tok/s** (+44.2%) **PASS** |
| Regression summary | **ALL PASS** |

Report: `results/router-eval-20260831-180616.json` (on server)

Before training: `. D:\lumen-stream-lab\deploy\win-env-d.ps1`
