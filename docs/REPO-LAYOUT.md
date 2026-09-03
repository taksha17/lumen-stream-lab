# Repository layout

How the Lumen Stream Lab repo is organized.

## Top level

| Path | Purpose |
|------|---------|
| `lumen.py` | Main CLI — no args opens the interactive menu |
| `lumen_menu.py` | Terminal UI implementation |
| `lumen_router.py` | Hybrid routing logic (sync with `deploy/win-router-lib.ps1`) |
| `lumen` | **Bash launcher** — `#!/usr/bin/env bash` script; runs `python3 lumen.py menu` |
| `lumen.cmd` | **Windows batch launcher** — runs `python lumen.py menu` |
| `lumen.yaml.example` | Optional orchestrator config template |
| `AGENTS.md.example` | Template for local Cursor/agent rules (copy → `AGENTS.md`, gitignored) |
| `README.md` | Landing page and quick start |
| `UPGRADES.md` | Model / capability / backend changelog (proposals → shipped / rolled back) |
| `CONTRIBUTING.md` | Contributor onboarding |
| `LICENSE` | MIT |

**Not in git (local only):** `AGENTS.md`, `docs/internal/`, `lumen.yaml`, `hardware.json`

## `config/`

| Path | Purpose |
|------|---------|
| `config/soup/` | **Active** Soup training YAML configs (S06, S07, 7B baseline, smoke) |
| `config/archive/` | Deprecated experiments (S08–S10 train configs, data, deploy scripts) |

Production domain model: train with `config/soup/soup-3b-stream-s07.yaml`, dataset `data/train-s07.jsonl`.

## `data/`

| Path | Purpose |
|------|---------|
| `domain-system-prompt.txt` | Injected for domain-tier answers |
| `router-eval-prompts.json` | E01–E12 routing eval suite |
| `train.jsonl`, `train-s06.jsonl`, `train-s07.jsonl` | Active training datasets |

## `deploy/`

Windows PowerShell scripts for the reference lab: regression gates, benches, Ollama deploy, router eval. See `deploy/DEPLOY.md`.

## `docs/`

All long-form documentation. Start at [`docs/README.md`](./README.md).

| Path | Purpose |
|------|---------|
| `ARCHITECTURE.md` | System design and diagrams |
| `REFERENCE-RESULTS.md` | Consolidated benchmark numbers |
| `TOOL-COMPARISON.md` | vs Ollama, llama.cpp, LiteLLM, Phase D3 models |
| `AGENT-INTEGRATION.md` | Hermes Agent and other agent frameworks |
| `TERMINAL-UI.md` | Full guide to the interactive menu |
| `MODELS.md`, `HARDWARE-TESTING.md`, etc. | Topic-specific guides |

## `hardware/`

`reference-lab.json` — CI reference rig profile. `contributor-template.json` — copy for your machine.

## `scripts/`

| Script | Purpose |
|--------|---------|
| `lumen_gateway.py` | Stdlib HTTP gateway (`/v1/plan`, `/v1/chat`) |
| `bench_backends.py` | Ollama vs llama.cpp benchmark |
| `compare.py` | +40% gate helper |
| `bench.sh`, `probe.sh` | Linux/macOS helpers |

## `tests/`

Router parity tests run in CI (`.github/workflows/ci.yml`).

## `results/`

Gitignored runtime output except `results/fixtures/` (sanitized CI fixtures).
