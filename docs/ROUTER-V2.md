# Router v2 (learned linear model)

Experimental **learned router** trained to match the production keyword router on the E01–E12 eval suite.

## Status

- **Training data:** `data/router-eval-prompts.json` labels from `lumen_router.route_decision` (teacher)
- **Weights:** `data/router-v2-weights.json` (checked in after `scripts/train_router_v2.py`)
- **Eval accuracy:** 12/12 tier + model match vs teacher

Production default remains **keyword router** (`lumen_router.py`). v2 is opt-in for experimentation and future prompt-log training.

## Train / refresh weights

```bash
python3 scripts/train_router_v2.py
python3 -m unittest tests.test_router_v2 -v
```

## Use v2 in CLI (experimental)

```bash
python3 -c "
from lumen_router_v2 import route_decision_v2
import json
print(json.dumps(route_decision_v2('What is Lumen Stream Lab?'), indent=2))
"
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

- Train on real prompt logs (tier + latency + quality feedback)
- Replace linear model with small sklearn/onnx classifier
- A/B in gateway: `routing.mode: learned_v2`
