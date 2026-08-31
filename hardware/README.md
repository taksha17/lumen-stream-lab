# Hardware profiles

| File | Purpose |
|------|---------|
| `reference-lab.json` | Checked-in **reference CI rig** (GTX 1650). Numbers in README/RESULTS are from here. |
| `../hardware.json` | **Your machine** — from `python3 lumen.py probe` (local, typically gitignored). |

Contributors may add `hardware/<name>.json` with probed specs and measured baselines. Do not treat reference-lab tok/s as universal defaults in shared code.

See `SCALING.md`.
