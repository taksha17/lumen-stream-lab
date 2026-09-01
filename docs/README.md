# Lumen Stream Lab — Documentation

Start here for the full picture. The root [README](../README.md) is the landing page; this folder is the **deep dive**.

## Read in this order

| # | Document | What you get |
|---|----------|--------------|
| 1 | [**ARCHITECTURE.md**](./ARCHITECTURE.md) | System design, routing flow, training vs inference, diagrams |
| 2 | [**REFERENCE-RESULTS.md**](./REFERENCE-RESULTS.md) | All benchmark numbers, gates, and fixtures in one place |
| 3 | [**HARDWARE-TESTING.md**](./HARDWARE-TESTING.md) | What our 4GB lab can prove, what it cannot, **call for collaborators** |
| 4 | [**ENTERPRISE-CASE-STUDY.md**](./ENTERPRISE-CASE-STUDY.md) | End-to-end enterprise narrative with metrics and topology |
| 5 | [**MODELS.md**](./MODELS.md) | Ollama models, aliases, fine-tune deploy |
| 6 | [**../CONTRIBUTING.md**](../CONTRIBUTING.md) | How to contribute benches, profiles, and code |

## Also in the repo

| Document | Purpose |
|----------|---------|
| [VISION.md](../VISION.md) | Goals and honest expectations (+40% thesis) |
| [ENTERPRISE.md](../ENTERPRISE.md) | Integration reference for platform engineers |
| [SCALING.md](../SCALING.md) | OSS scaling model, hardware classes |
| [PLAYBOOK.md](../PLAYBOOK.md) | Soup / AirLLM / Colibri limits |
| [RESULTS.md](../RESULTS.md) | Chronological benchmark log (source of truth) |
| [benchmarks/PROTOCOL.md](../benchmarks/PROTOCOL.md) | Fair measurement rules |

## Interactive tooling

```bash
python3 lumen.py          # terminal menu: chat, bench, gateway, setup
python3 lumen.py route --prompt "..."
```

## Reference hardware profile

Checked-in baseline: [`hardware/reference-lab.json`](../hardware/reference-lab.json)  
Sanitized CI fixture: [`results/fixtures/router-eval-summary.json`](../results/fixtures/router-eval-summary.json)
