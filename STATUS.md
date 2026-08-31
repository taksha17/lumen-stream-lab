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

## Next steps (in progress)

### Done this session — domain system prompt (no retrain)

- `data/domain-system-prompt.txt` — shared disambiguation prompt (OSS-friendly)
- Injected on **all** `qwen2.5-3b-lumen` Ollama calls: `win-route.ps1`, domain gate, orchestration bench, router eval, gateway
- `lumen_router.py`: `domain_system_prompt()`, `ollama_generate_payload()`, route plan includes `system_prompt`

**On server — verify E12 without training:**

```powershell
powershell -File D:\lumen-stream-lab\deploy\win-domain-smoke-gate.ps1
powershell -File D:\lumen-stream-lab\deploy\win-regression.ps1
```

### Ready to run — S10 E12 micro-train (if system prompt alone insufficient)

| Step | Script |
|------|--------|
| Train | `deploy\win-train-3b-s10.ps1` |
| Export + gate + rollback | `deploy\win-post-s10.ps1` |

Data: `data/train-s10-e12.jsonl` (30 rows, 25x canonical E12)

### Still queued

1. **`-Full` router eval** — `win-regression.ps1 -Full` (~30 min quality side-by-side)
2. **llama.cpp vs Ollama** resident bench on reference lab

Before training: `. D:\lumen-stream-lab\deploy\win-env-d.ps1`
