"""Hybrid router logic — mirrors deploy/win-router-lib.ps1."""

from __future__ import annotations

import os
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
    # Experimental — auto-route only when code_tier_enabled()
    "code": "qwen2.5-coder:3b",
    # Experimental — auto-route only when reason_tier_enabled()
    "reason": "phi4-mini",
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

CODE_KEYWORDS = (
    "write a python",
    "write a function",
    "python function",
    "def ",
    "leetcode",
    "typescript",
    "javascript function",
    "fix this code",
    "stack trace",
    "compile error",
    "unit test",
)

REASON_KEYWORDS = (
    "how many",
    "calculate",
    "compute",
    "solve",
    "step by step",
    "show your work",
    "math problem",
    "word problem",
    "prove that",
    "logic puzzle",
)


def code_tier_enabled() -> bool:
    """Opt-in so the 12-prompt eval suite stays unchanged by default."""
    return os.environ.get("LUMEN_CODE_TIER", "").strip().lower() in ("1", "true", "yes", "on")


def reason_tier_enabled() -> bool:
    """Opt-in phi4 reasoning; never on by default (slower than LFM)."""
    return os.environ.get("LUMEN_REASON_TIER", "").strip().lower() in ("1", "true", "yes", "on")


def is_code_prompt(text: str) -> bool:
    return _kw_match(text, CODE_KEYWORDS)


def is_reason_prompt(text: str) -> bool:
    return _kw_match(text, REASON_KEYWORDS)


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


def is_code_model(model: str) -> bool:
    return model == MODELS["code"]


def is_reason_model(model: str) -> bool:
    return model == MODELS["reason"]


# Tuned for 4GB resident decode (reference lab). Override via LUMEN_CODE_* env.
CODE_DEFAULT_OPTIONS: dict[str, Any] = {
    "temperature": 0.1,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "num_ctx": 2048,
    "num_batch": 512,
}

CODE_SYSTEM_PROMPT = (
    "You are a concise coding assistant. Prefer correct, runnable code with minimal "
    "prose. Use fenced code blocks. Do not invent APIs."
)

REASON_SYSTEM_PROMPT = (
    "You are a careful reasoning assistant. Show brief steps, then the final answer. "
    "Prefer correct arithmetic and logic over long prose."
)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def generation_options_for_tier(
    tier: str,
    *,
    num_predict: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ollama options per tier. Code defaults favor low temperature + modest ctx."""
    if tier == "code":
        opts: dict[str, Any] = {
            "temperature": _env_float("LUMEN_CODE_TEMPERATURE", float(CODE_DEFAULT_OPTIONS["temperature"])),
            "top_p": float(CODE_DEFAULT_OPTIONS["top_p"]),
            "top_k": int(CODE_DEFAULT_OPTIONS["top_k"]),
            "repeat_penalty": float(CODE_DEFAULT_OPTIONS["repeat_penalty"]),
            "num_ctx": _env_int("LUMEN_CODE_NUM_CTX", int(CODE_DEFAULT_OPTIONS["num_ctx"])),
            "num_batch": _env_int("LUMEN_CODE_NUM_BATCH", int(CODE_DEFAULT_OPTIONS["num_batch"])),
        }
    elif tier == "reason":
        opts = {"temperature": 0.2, "num_predict": _env_int("LUMEN_REASON_NUM_PREDICT", 160)}
    elif tier == "fast":
        opts = {"temperature": 0.5, "num_ctx": 1024}
    elif tier == "quality":
        opts = {"temperature": 0.7, "num_ctx": 4096}
    elif tier == "balanced":
        # Extra headroom so LFM can finish the answer after its think block.
        opts = {"temperature": 0.5, "num_predict": _env_int("LUMEN_BALANCED_NUM_PREDICT", 192)}
    else:
        opts = {"temperature": 0.7}
    if num_predict is not None:
        opts["num_predict"] = max(1, int(num_predict))
    if extra:
        opts.update(extra)
    return opts


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
            "microframework - it is a separate ML orchestration project.\n\n"
            + prompt
        )
    if re.search(r"1b vs 3b|3b vs 7b|route to a 1b", lower):
        return (
            "[Lumen hybrid router tiers: fast=llama3.2:1b for short/simple; "
            "balanced=lfm-balanced or qwen2.5-3b-lumen for domain; "
            "quality=qwen2.5-7b-lumen for long prompts or forced quality.]\n\n"
            + prompt
        )
    return prompt


def resolve_keep_alive(
    override: str | int | None = None,
) -> str | int | None:
    """Ollama keep_alive for generate payloads.

    - unset override + unset LUMEN_KEEP_ALIVE → "10m" (resident after generate)
    - LUMEN_KEEP_ALIVE=off / none / default → omit (server default, usually 5m)
    - LUMEN_KEEP_ALIVE=0 → unload immediately after generate
    """
    if override is not None:
        return override
    raw = (os.environ.get("LUMEN_KEEP_ALIVE") or "").strip()
    if not raw:
        return "10m"
    lower = raw.lower()
    if lower in ("off", "none", "default", "omit"):
        return None
    if lower in ("0", "false"):
        return 0
    try:
        return int(raw)
    except ValueError:
        return raw


def resolve_think(override: bool | None = None) -> bool | None:
    """Ollama think flag. Default False so Qwen3-class models return answer text.

    LUMEN_THINK=1/true enables thinking. LUMEN_THINK=off omits the field.
    """
    if override is not None:
        return override
    raw = (os.environ.get("LUMEN_THINK") or "").strip().lower()
    if not raw:
        return False
    if raw in ("off", "omit", "default", "none"):
        return None
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return False


_THINK_CLOSE = re.compile(r"</\s*think\s*>", re.IGNORECASE)
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_BOXED = re.compile(r"\\boxed\{([^{}]+)\}")
_META_PREFIXES = (
    "the user wants",
    "the user asked",
    "let me ",
    "i need to",
    "okay,",
    "ok,",
    "looking at",
    "analyzing",
    "we are to",
    "first,",
)


def _strip_meta_lead(text: str) -> str:
    """Drop leading self-talk paragraphs; keep first non-meta block."""
    chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
    if not chunks:
        return text.strip()
    kept: list[str] = []
    for chunk in chunks:
        low = chunk.lower().lstrip("*-• \t")
        if any(low.startswith(p) for p in _META_PREFIXES):
            continue
        kept.append(chunk)
    if kept:
        return "\n\n".join(kept).strip()
    return text.strip()


def visible_response(data: dict[str, Any] | str) -> str:
    """Prefer user-visible answer over chain-of-thought / empty think shells."""
    if isinstance(data, str):
        text = data
        thinking = ""
    else:
        text = str(data.get("response") or data.get("message", {}).get("content") or "")
        thinking = str(data.get("thinking") or "")
        msg = data.get("message")
        if isinstance(msg, dict) and not thinking:
            thinking = str(msg.get("thinking") or "")

    boxed = _BOXED.search(text) or _BOXED.search(thinking)
    if boxed:
        return boxed.group(1).strip()

    if text.strip():
        parts = _THINK_CLOSE.split(text, maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            return _strip_meta_lead(parts[1])
        cleaned = _THINK_BLOCK.sub("", text).strip()
        if cleaned:
            return _strip_meta_lead(cleaned)
        return _strip_meta_lead(text)

    if thinking.strip():
        parts = _THINK_CLOSE.split(thinking, maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            return _strip_meta_lead(parts[1])
        return _strip_meta_lead(thinking)
    return ""


def ollama_generate_payload(
    model: str,
    prompt: str,
    *,
    stream: bool = False,
    options: dict[str, Any] | None = None,
    tier: str | None = None,
    keep_alive: str | int | None = None,
    think: bool | None = None,
) -> dict[str, Any]:
    user_prompt = wrap_domain_prompt(prompt) if is_domain_model(model) else prompt
    resolved = dict(options or {})
    if not resolved and tier:
        resolved = generation_options_for_tier(tier)
    elif tier == "code" and "temperature" not in resolved:
        # Merge code defaults under any partial options from callers.
        base = generation_options_for_tier("code")
        base.update(resolved)
        resolved = base
    payload: dict[str, Any] = {
        "model": model,
        "prompt": user_prompt,
        "stream": stream,
        "options": resolved,
    }
    ka = resolve_keep_alive(keep_alive)
    if ka is not None:
        payload["keep_alive"] = ka
    think_flag = resolve_think(think)
    if think_flag is not None:
        payload["think"] = think_flag
    if is_domain_model(model):
        payload["system"] = domain_system_prompt()
    elif is_code_model(model):
        payload["system"] = CODE_SYSTEM_PROMPT
    elif is_reason_model(model):
        payload["system"] = REASON_SYSTEM_PROMPT
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
        if tier == "code" or is_code_model(model):
            out["system_prompt"] = CODE_SYSTEM_PROMPT
            out["options"] = generation_options_for_tier("code")
        if tier == "reason" or is_reason_model(model):
            out["system_prompt"] = REASON_SYSTEM_PROMPT
            out["options"] = generation_options_for_tier("reason")
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

    if code_tier_enabled() and is_code_prompt(prompt):
        return _finish("code", MODELS["code"], "code-tier (experimental)")

    if reason_tier_enabled() and is_reason_prompt(prompt):
        return _finish("reason", MODELS["reason"], "reason-tier (experimental)")

    if words <= 12 and not _kw_match(prompt, COMPLEX_KEYWORDS):
        return _finish("fast", MODELS["fast"], f"short/simple ({words} words)")

    if _kw_match(prompt, COMPLEX_KEYWORDS) or words > 20:
        model, reason = balanced_model(prompt)
        return _finish("balanced", model, reason)

    model, reason = balanced_model(prompt)
    return _finish("balanced", model, f"default {reason}")


def resolve_router_engine(override: str | None = None) -> str:
    """Select routing engine: keyword (default) or v2 via LUMEN_ROUTER."""
    raw = (override or os.environ.get("LUMEN_ROUTER") or "keyword").strip().lower()
    if raw in ("v2", "learned", "learned_v2"):
        return "v2"
    return "keyword"


def route_with_engine(
    prompt: str,
    tier_pref: str = "auto",
    *,
    engine: str | None = None,
) -> dict[str, Any]:
    """Route using keyword or learned v2. Default remains keyword."""
    eng = resolve_router_engine(engine)
    if eng == "v2":
        from lumen_router_v2 import route_decision_v2

        out = route_decision_v2(prompt, tier_pref)
        out["router"] = "v2"
        return out
    out = route_decision(prompt, tier_pref)
    out["router"] = "keyword"
    return out
