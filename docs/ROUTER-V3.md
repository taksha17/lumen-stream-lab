# Router v3 (log-trained)

Learned router trained from **local route logs** plus the keyword teacher on E01–E12.

## Status

- **Log file:** `results/route-log.jsonl` (gitignored)
- **Weights:** `data/router-v3-weights.json` (checked in after train)
- **Production default:** still **keyword**
- **Opt-in:** `LUMEN_ROUTER=v3`

## Collect logs

Logging is **on by default** for menu chat and the gateway (`LUMEN_ROUTE_LOG=0` to disable).

```bash
# Seed trusted eval labels (once)
python3 scripts/seed_route_log.py
# or
python3 lumen.py route-log seed

# Chat — each turn appends a row; rate the last reply
python3 lumen.py menu
# you> Explain TCP vs UDP
# you> /up

# Or rate last event from CLI
python3 lumen.py route-log feedback up
python3 lumen.py route-log stats
```

Optional HTTP: send chat through `scripts/lumen_gateway.py` — rows get `source=gateway`.

## Train / use

```bash
python3 scripts/train_router_v3.py
python3 -m unittest tests.test_router_v3 -v

export LUMEN_ROUTER=v3
python3 lumen.py route --prompt "What is Lumen Stream Lab?"
```

## Feedback rules

| feedback | Effect in train |
|----------|-----------------|
| `up` / `good` | Include label at **2×** weight |
| `down` / `bad` | **Skip** row |
| (none) | Include at 1× (observed tier/model) |

Prompts are truncated to 800 chars; logs stay local under `results/`.

## Promote only when

1. `win-regression.ps1` still **PASS** with `LUMEN_ROUTER=v3`
2. Holdout / real chat shows fewer bad tiers than keyword (use `/up` `/down`)
3. Orchestration mean stays **≥ +40%**

Until then keep default keyword; use v3 for experiments only.
