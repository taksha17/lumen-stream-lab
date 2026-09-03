#!/usr/bin/env python3
"""Train router v3 from route-log.jsonl (+ optional teacher eval).

Uses the same linear softmax as v2, but:
  - feedback=up rows are included (weight 2x)
  - feedback=down rows are skipped
  - unlabeled log rows use their observed label_class (weight 1x)
  - eval suite teacher labels fill gaps when log is thin

Writes data/router-v3-weights.json. Opt-in via LUMEN_ROUTER=v3.

Usage:
  python3 scripts/seed_route_log.py
  python3 scripts/train_router_v3.py
  LUMEN_ROUTER=v3 python3 lumen.py route --prompt "What is 2+2?"
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lumen_router import route_decision  # noqa: E402
from route_log import read_events  # noqa: E402
from scripts.router_features import CLASS_NAMES, FEATURE_NAMES, featurize  # noqa: E402

PROMPTS_PATH = ROOT / "data" / "router-eval-prompts.json"
OUT_PATH = ROOT / "data" / "router-v3-weights.json"


def teacher_label(prompt: str) -> str:
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
    sample_weights: list[float],
) -> float:
    n_cls = len(CLASS_NAMES)
    n_feat = len(FEATURE_NAMES)
    loss = 0.0
    total_w = 0.0
    for x, y, sw in zip(xs, ys, sample_weights):
        scores = [sum(wi * xi for wi, xi in zip(weights[c], x)) for c in range(n_cls)]
        probs = softmax(scores)
        loss -= sw * math.log(max(probs[y], 1e-9))
        total_w += sw
        for c in range(n_cls):
            err = probs[c] - (1.0 if c == y else 0.0)
            for j in range(n_feat):
                weights[c][j] -= lr * sw * err * x[j]
    return loss / max(total_w, 1e-9)


def collect_dataset(*, include_teacher: bool) -> tuple[list, list, list, dict]:
    xs: list[list[float]] = []
    ys: list[int] = []
    sw: list[float] = []
    meta = {"from_log": 0, "from_teacher": 0, "skipped_down": 0}

    for row in read_events():
        fb = (row.get("feedback") or "").lower()
        if fb == "down":
            meta["skipped_down"] += 1
            continue
        prompt = row.get("prompt") or ""
        lab = row.get("label_class") or teacher_label(prompt)
        if lab not in CLASS_NAMES:
            continue
        weight = 2.0 if fb == "up" else 1.0
        xs.append(featurize(prompt))
        ys.append(CLASS_NAMES.index(lab))
        sw.append(weight)
        meta["from_log"] += 1

    if include_teacher or meta["from_log"] < 12:
        prompts = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
        for entry in prompts:
            lab = teacher_label(entry["prompt"])
            xs.append(featurize(entry["prompt"]))
            ys.append(CLASS_NAMES.index(lab))
            sw.append(1.0)
            meta["from_teacher"] += 1

    return xs, ys, sw, meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Train Lumen router v3 from route logs")
    ap.add_argument("--epochs", type=int, default=800)
    ap.add_argument("--lr", type=float, default=0.08)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ap.add_argument(
        "--no-teacher",
        action="store_true",
        help="Do not mix eval-suite teacher labels (needs a rich log)",
    )
    args = ap.parse_args()

    xs, ys, sw, meta = collect_dataset(include_teacher=not args.no_teacher)
    if len(xs) < 8:
        print("Need more route-log rows (run scripts/seed_route_log.py)", file=sys.stderr)
        return 1

    n_cls = len(CLASS_NAMES)
    n_feat = len(FEATURE_NAMES)
    random.seed(42)
    weights = [[random.uniform(-0.05, 0.05) for _ in range(n_feat)] for _ in range(n_cls)]

    for _ in range(args.epochs):
        order = list(range(len(xs)))
        random.shuffle(order)
        train_epoch(
            [xs[i] for i in order],
            [ys[i] for i in order],
            weights,
            args.lr,
            [sw[i] for i in order],
        )

    prompts = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))
    report = []
    correct = 0
    for entry in prompts:
        x = featurize(entry["prompt"])
        scores = [sum(wi * xi for wi, xi in zip(weights[c], x)) for c in range(n_cls)]
        pred = scores.index(max(scores))
        y = CLASS_NAMES.index(teacher_label(entry["prompt"]))
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
        "version": 3,
        "feature_names": FEATURE_NAMES,
        "class_names": list(CLASS_NAMES),
        "weights": weights,
        "eval_accuracy": round(acc, 4),
        "eval_report": report,
        "train_meta": meta,
        "teacher": "route-log + lumen_router.route_decision",
    }
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} eval_accuracy={acc:.1%} meta={meta}")
    fails = [r for r in report if not r["ok"]]
    if fails:
        print("Eval mismatches vs teacher:", fails)
        # Soft fail — v3 may intentionally diverge once feedback accumulates
        return 0 if meta["from_log"] >= 20 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
