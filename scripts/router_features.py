#!/usr/bin/env python3
"""Feature extraction for learned router v2 (stdlib only)."""

from __future__ import annotations

import re

from lumen_router import (
    COMPLEX_KEYWORDS,
    DOMAIN_KEYWORDS,
    QUALITY_KEYWORDS,
    SIMPLE_PATTERNS,
    is_lumen_domain,
    is_quality_route,
)


def _kw_hits(text: str, keywords: tuple[str, ...]) -> int:
    lower = text.lower()
    return sum(1 for kw in keywords if kw in lower)


def featurize(prompt: str) -> list[float]:
    words = len(prompt.split())
    lower = prompt.lower()
    simple = 1.0 if any(re.search(p, prompt, re.IGNORECASE) for p in SIMPLE_PATTERNS) else 0.0
    domain = float(_kw_hits(prompt, DOMAIN_KEYWORDS))
    if is_lumen_domain(prompt):
        domain = max(domain, 2.0)
    quality = float(_kw_hits(prompt, QUALITY_KEYWORDS))
    if is_quality_route(prompt, words):
        quality = max(quality, 2.0)
    complex_k = float(_kw_hits(prompt, COMPLEX_KEYWORDS))
    has_lumen = 1.0 if "lumen" in lower else 0.0
    qmark = 1.0 if "?" in prompt else 0.0
    return [
        1.0,
        float(words),
        domain,
        quality,
        complex_k,
        simple,
        has_lumen,
        qmark,
        float(words > 50),
        float(words <= 12),
    ]


FEATURE_NAMES = [
    "bias",
    "words",
    "domain_kw",
    "quality_kw",
    "complex_kw",
    "simple_pattern",
    "has_lumen",
    "question_mark",
    "long_prompt",
    "short_prompt",
]

CLASS_NAMES = ("fast", "balanced_lfm", "balanced_domain", "quality")
