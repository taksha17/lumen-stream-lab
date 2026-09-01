"""Learned router v2 — linear softmax over hand-crafted features."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from lumen_router import MODELS, domain_system_prompt, is_domain_model

ROOT = Path(__file__).resolve().parent
WEIGHTS_PATH = ROOT / "data" / "router-v2-weights.json"

CLASS_TO_TIER = {
    "fast": "fast",
    "balanced_lfm": "balanced",
    "balanced_domain": "balanced",
    "quality": "quality",
}

CLASS_TO_MODEL = {
    "fast": MODELS["fast"],
    "balanced_lfm": MODELS["balanced"],
    "balanced_domain": MODELS["balanced_domain"],
    "quality": MODELS["quality"],
}

CLASS_TO_REASON = {
    "fast": "router-v2/fast",
    "balanced_lfm": "router-v2/balanced/general",
    "balanced_domain": "router-v2/balanced/domain",
    "quality": "router-v2/quality",
}


def _load_weights() -> dict:
    if not WEIGHTS_PATH.exists():
        raise FileNotFoundError(f"missing {WEIGHTS_PATH}; run scripts/train_router_v2.py")
    return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))


def predict_class(prompt: str, weights_data: dict | None = None) -> str:
    from scripts.router_features import featurize

    data = weights_data or _load_weights()
    x = featurize(prompt)
    weights = data["weights"]
    class_names = data["class_names"]
    scores = [sum(wi * xi for wi, xi in zip(row, x)) for row in weights]
    return class_names[scores.index(max(scores))]


def route_decision_v2(prompt: str, tier_pref: str = "auto") -> dict[str, Any]:
    if tier_pref != "auto":
        from lumen_router import route_decision

        return route_decision(prompt, tier_pref)

    cls = predict_class(prompt)
    tier = CLASS_TO_TIER[cls]
    model = CLASS_TO_MODEL[cls]
    out: dict[str, Any] = {
        "tier": tier,
        "model": model,
        "reason": CLASS_TO_REASON[cls],
        "router": "v2",
    }
    if is_domain_model(model):
        out["system_prompt"] = domain_system_prompt()
    return out
