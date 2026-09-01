# Benchmark fixtures

Sanitized reference-lab summaries for contributors to compare against without running the full eval suite.

| File | Contents |
|------|----------|
| `router-eval-summary.json` | Routing 12/12, tier medians, +44% orchestration mean |
| `phase-d3-summary.json` | Phase D3 model bench (Phi-4, SmolLM2, Gemma 3, etc.) — 2026-09-01 |
| `ecosystem-comparison-20260901.json` | Lumen vs always-3B vs llama.cpp re-bench — 2026-09-01 |

Regenerate on reference lab:

```powershell
powershell -File deploy\win-bench-phase-d3.ps1
powershell -File deploy\win-bench-ecosystem.ps1
powershell -File deploy\win-regression.ps1 -Full
```

Copy summary JSON fields here for CI/contributor fixtures.
