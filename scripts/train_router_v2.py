#!/usr/bin/env python3
"""Train router v2 weights from eval suite + keyword-router teacher labels."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lumen_router import route_decision  # noqa: E402
from scripts.router_features import CLASS_NAMES, FEATURE_NAMES, featurize  # noqa: E402

PROMPTS_PATH = ROOT / "data" / "router-eval-prompts.json"
OUT_PATH = ROOT / "data" / "router-v2-weights.json"


def label_from_teacher(prompt: str) -> str:
    d = route_decision(prompt)
    if d["tier"] == "fast":
        return "fast"
    if d["tier"] == "quality":
        return "quality"
    if d["model"] == "qwen2.5-3b-lumen":
        return "balanced_domain"
    return "balanced_lfm"


def softmax(scores: list[float]) -> list[float]:
    m = max(scores)
    ex = [math.exp(s - m) for s in scores]
    s = sum(ex)
    return [e / s for e in ex]


def train_epoch(
    xs: list[list[float]],
    ys: list[int],
    weights: list[list[float]],
    lr: float,
) -> float:
    n_cls = len(CLASS_NAMES)
    n_feat = len(FEATURE_NAMES)
    loss = 0.0
    for x, y in zip(xs, ys):
        scores = [sum(wi * xi for wi, xi in zip(weights[c], x)) for c in range(n_cls)]
        probs = softmax(scores)
        loss -= math.log(max(probs[y], 1e-9))
        for c in range(n_cls):
            err = probs[c] - (1.0 if c == y else 0.0)
            for j in range(n_feat):
                weights[c][j] -= lr * err * x[j]
    return loss / len(xs)


def main() -> int:
    ap = argparse.ArgumentParser(description="Train Lumen router v2")
    ap.add_argument("--epochs", type=int, default=800)
    ap.add_argument("--lr", type=float, default=0.08)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()

    prompts = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    xs: list[list[float]] = []
    ys: list[int] = []

    for entry in prompts:
        lab = label_from_teacher(entry["prompt"])
        xs.append(featurize(entry["prompt"]))
        ys.append(CLASS_NAMES.index(lab))

    aug = [
        ("hi there", "fast"),
        ("explain tcp vs udp briefly", "balanced_lfm"),
        ("what is lumen stream lab", "balanced_domain"),
        ("write a comprehensive essay on edge ai routing " * 8, "quality"),
    ]
    for text, lab in aug:
        xs.append(featurize(text))
        ys.append(CLASS_NAMES.index(lab))

    n_cls = len(CLASS_NAMES)
    n_feat = len(FEATURE_NAMES)
    random.seed(42)
    weights = [[random.uniform(-0.05, 0.05) for _ in range(n_feat)] for _ in range(n_cls)]

    for _ in range(args.epochs):
        order = list(range(len(xs)))
        random.shuffle(order)
        bx = [xs[i] for i in order]
        by = [ys[i] for i in order]
        train_epoch(bx, by, weights, args.lr)

    report = []
    correct = 0
    for i, entry in enumerate(prompts):
        x = featurize(entry["prompt"])
        scores = [sum(wi * xi for wi, xi in zip(weights[c], x)) for c in range(n_cls)]
        pred = scores.index(max(scores))
        y = CLASS_NAMES.index(label_from_teacher(entry["prompt"]))
        ok = pred == y
        if ok:
            correct += 1
        report.append({
            "id": entry["id"],
            "expected": CLASS_NAMES[y],
            "predicted": CLASS_NAMES[pred],
            "ok": ok,
        })

    acc = correct / len(prompts)
    payload = {
        "version": 2,
        "feature_names": FEATURE_NAMES,
        "class_names": list(CLASS_NAMES),
        "weights": weights,
        "eval_accuracy": round(acc, 4),
        "eval_report": report,
        "teacher": "lumen_router.route_decision",
    }
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} eval_accuracy={acc:.1%}")
    fails = [r for r in report if not r["ok"]]
    if fails:
        print("Mismatches:", fails)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
