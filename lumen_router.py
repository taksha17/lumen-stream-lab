"""Hybrid router logic — mirrors deploy/win-router-lib.ps1."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
_DOMAIN_PROMPT_PATH = _ROOT / "data" / "domain-system-prompt.txt"
_DOMAIN_PROMPT_FALLBACK = (
    "You are the domain assistant for Lumen Stream Lab, an open-source local LLM "
    "orchestration research project. It is NOT Laravel Lumen, Liquid AI, telecom, "
    "or video streaming. Answer about this ML orchestration project only."
)

MODELS = {
    "fast": "llama3.2:1b",
    "balanced": "lfm-balanced",
    "balanced_domain": "qwen2.5-3b-lumen",
    "quality": "qwen2.5-7b-lumen",
}

QUALITY_MIN_WORDS = 50
QUALITY_KEYWORD_MIN_WORDS = 35

DOMAIN_KEYWORDS = (
    "lumen stream lab",
    "laravel lumen",
    "stream_layers",
    "soup train",
    "soup chat",
    "1b vs 3b",
    "3b vs 7b",
    "lumen stream",
)

QUALITY_KEYWORDS = (
    "detailed", "comprehensive", "thorough", "in-depth", "in depth",
    "essay", "write a story", "creative", "code review", "design a system",
    "best answer", "high quality", "expert", "research", "whitepaper",
    "proofread", "refactor", "production-grade",
)

COMPLEX_KEYWORDS = (
    "explain", "analyze", "compare", "describe", "why", "how does",
    "algorithm", "architecture", "implement", "debug", "step by step",
    "pros and cons", "summarize", "difference between", "route", "routing",
    "lumen", "model tier", "when should", "streaming", "fine-tune",
)

SIMPLE_PATTERNS = (
    r"^\s*what is \d+\s*[\+\-\*\/]\s*\d+",
    r"^\s*\d+\s*[\+\-\*\/]\s*\d+\s*\??\s*$",
    r"^(hi|hello|hey)\b",
    r"^(yes|no|thanks|thank you)\b",
    r"^\s*capital of\b",
)


def _kw_match(text: str, keywords: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def domain_system_prompt() -> str:
    if _DOMAIN_PROMPT_PATH.exists():
        return _DOMAIN_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return _DOMAIN_PROMPT_FALLBACK


def is_domain_model(model: str) -> bool:
    return model == MODELS["balanced_domain"]


def domain_context_prefix() -> str:
    return (
        "[Lumen Stream Lab = open-source local LLM orchestration research project. "
        "Hybrid router across Ollama models; Soup for training. "
        "NOT Laravel Lumen, NOT Liquid AI, NOT telecom, NOT video CDN.]\n\n"
    )


def wrap_domain_prompt(prompt: str) -> str:
    lower = prompt.lower()
    if "what is lumen stream lab" in lower:
        return domain_context_prefix() + prompt
    if "laravel lumen" in lower:
        return (
            "Answer starting with No. Lumen Stream Lab is NOT the Laravel PHP "
            "microframework — it is a separate ML orchestration project.\n\n"
            + prompt
        )
    return prompt


def ollama_generate_payload(
    model: str,
    prompt: str,
    *,
    stream: bool = False,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_prompt = wrap_domain_prompt(prompt) if is_domain_model(model) else prompt
    payload: dict[str, Any] = {
        "model": model,
        "prompt": user_prompt,
        "stream": stream,
        "options": options or {},
    }
    if is_domain_model(model):
        payload["system"] = domain_system_prompt()
    return payload


def is_lumen_domain(text: str) -> bool:
    if _kw_match(text, DOMAIN_KEYWORDS):
        return True
    lower = text.lower()
    if "lumen" in lower and any(
        x in lower for x in ("route", "router", "stream lab", "fine-tune")
    ):
        return True
    if "layer streaming" in lower and ("soup" in lower or "lumen" in lower):
        return True
    return False


def balanced_model(text: str) -> tuple[str, str]:
    if is_lumen_domain(text):
        return MODELS["balanced_domain"], "balanced/domain (Lumen keywords)"
    return MODELS["balanced"], "balanced/general (LFM speed)"


def is_quality_route(text: str, words: int) -> bool:
    if words > QUALITY_MIN_WORDS:
        return True
    return words > QUALITY_KEYWORD_MIN_WORDS and _kw_match(text, QUALITY_KEYWORDS)


def route_decision(prompt: str, tier_pref: str = "auto") -> dict[str, Any]:
    def _finish(tier: str, model: str, reason: str) -> dict[str, Any]:
        out: dict[str, Any] = {"tier": tier, "model": model, "reason": reason}
        if is_domain_model(model):
            out["system_prompt"] = domain_system_prompt()
        return out

    if tier_pref != "auto":
        if tier_pref == "balanced":
            model, reason = balanced_model(prompt)
            return _finish("balanced", model, f"forced tier=balanced ({reason})")
        model = MODELS[tier_pref]
        return _finish(tier_pref, model, f"forced tier={tier_pref}")

    words = len(prompt.split())
    for pat in SIMPLE_PATTERNS:
        if re.search(pat, prompt, re.IGNORECASE):
            return _finish("fast", MODELS["fast"], "simple pattern match")

    if is_quality_route(prompt, words):
        return _finish("quality", MODELS["quality"], f"quality/long ({words} words)")

    if words <= 12 and not _kw_match(prompt, COMPLEX_KEYWORDS):
        return _finish("fast", MODELS["fast"], f"short/simple ({words} words)")

    if _kw_match(prompt, COMPLEX_KEYWORDS) or words > 20:
        model, reason = balanced_model(prompt)
        return _finish("balanced", model, reason)

    model, reason = balanced_model(prompt)
    return _finish("balanced", model, f"default {reason}")
