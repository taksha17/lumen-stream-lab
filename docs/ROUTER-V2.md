# Router v2 (learned linear model)

Experimental **learned router** trained to match the production keyword router on the E01–E12 eval suite.

## Status

- **Training data:** `data/router-eval-prompts.json` labels from `lumen_router.route_decision` (teacher)
- **Weights:** `data/router-v2-weights.json` (checked in after `scripts/train_router_v2.py`)
- **Eval accuracy:** 12/12 tier + model match vs teacher
- **Production default:** keyword router (`LUMEN_ROUTER` unset / `keyword`)
- **Opt-in:** `LUMEN_ROUTER=v2` (CLI, menu, gateway)

## Train / refresh weights

```bash
python3 scripts/train_router_v2.py
python3 -m unittest tests.test_router_v2 -v
```

## A/B (parity + holdout)

```bash
python3 scripts/ab_router_v2.py --holdout
```

Writes `results/router-v2-ab-last.json`. Promote v2 to default only after holdout divergences show a quality or speed win without breaking `win-regression.ps1`.

## Use v2

```bash
# Env (gateway / menu / lumen route)
export LUMEN_ROUTER=v2
python3 lumen.py route --prompt "What is Lumen Stream Lab?"

# Or one-shot CLI flag
python3 lumen.py route --prompt "What is Lumen Stream Lab?" --router v2
```

```python
from lumen_router import route_with_engine
print(route_with_engine("What is Lumen Stream Lab?", engine="v2"))
```

## Features

| Feature | Meaning |
|---------|---------|
| `words` | Word count |
| `domain_kw` | Lumen/Soup domain keyword hits |
| `quality_kw` | Long-form quality keyword hits |
| `complex_kw` | Explain/analyze/coding keywords |
| `simple_pattern` | Arithmetic / greeting regex |
| `has_lumen` | Contains "lumen" |
| `long_prompt` / `short_prompt` | Word count thresholds |

## Next steps for v3

See [ROUTER-V3.md](./ROUTER-V3.md) — log-trained weights via `results/route-log.jsonl`.
