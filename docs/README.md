# Lumen Stream Lab — Documentation

Start here for the full picture. The root [README](../README.md) is the landing page; this folder is the **deep dive**.

## Read in this order

| # | Document | What you get |
|---|----------|--------------|
| 1 | [**TERMINAL-UI.md**](./TERMINAL-UI.md) | **Interactive menu** — setup, chat, bench, gateway |
| 2 | [**ARCHITECTURE.md**](./ARCHITECTURE.md) | System design, routing flow, training vs inference, diagrams |
| 3 | [**AGENT-INTEGRATION.md**](./AGENT-INTEGRATION.md) | Hermes Agent + other agent frameworks |
| 4 | [**TOOL-COMPARISON.md**](./TOOL-COMPARISON.md) | Lumen vs Ollama, llama.cpp, LiteLLM, Phase D3 models |
| 5 | [**REFERENCE-RESULTS.md**](./REFERENCE-RESULTS.md) | All benchmark numbers, gates, and fixtures in one place |
| 6 | [**HARDWARE-TESTING.md**](./HARDWARE-TESTING.md) | What our 4GB lab can prove, what it cannot, **call for collaborators** |
| 7 | [**ENTERPRISE-CASE-STUDY.md**](./ENTERPRISE-CASE-STUDY.md) | End-to-end enterprise narrative with metrics and topology |
| 8 | [**MODELS.md**](./MODELS.md) | Ollama models, aliases, fine-tune deploy |
| 9 | [**../CONTRIBUTING.md**](../CONTRIBUTING.md) | How to contribute benches, profiles, and code |

## Also in this folder

| Document | Purpose |
|----------|---------|
| [VISION.md](./VISION.md) | Goals and honest expectations (+40% thesis) |
| [ENTERPRISE.md](./ENTERPRISE.md) | Integration reference for platform engineers |
| [SCALING.md](./SCALING.md) | OSS scaling model, hardware classes |
| [PLAYBOOK.md](./PLAYBOOK.md) | Soup / AirLLM / Colibri limits |
| [RESULTS.md](./RESULTS.md) | Chronological benchmark log (source of truth) |
| [REPO-LAYOUT.md](./REPO-LAYOUT.md) | Where everything lives in the repo |
| [benchmarks/PROTOCOL.md](../benchmarks/PROTOCOL.md) | Fair measurement rules |

## Interactive tooling

```bash
python3 lumen.py          # terminal menu: chat, bench, gateway, setup
python3 lumen.py route --prompt "..."
```

See [**TERMINAL-UI.md**](./TERMINAL-UI.md) for the full guide.

## Reference hardware profile

Checked-in baseline: [`hardware/reference-lab.json`](../hardware/reference-lab.json)  
Sanitized CI fixture: [`results/fixtures/router-eval-summary.json`](../results/fixtures/router-eval-summary.json)
