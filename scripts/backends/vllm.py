"""vLLM OpenAI-compatible backend (optional).

Requires a running vLLM server, e.g.:
  vllm serve qwen2.5-3b-instruct --port 8000

Set in lumen.yaml:
  backends:
    vllm:
      enabled: true
      url: http://127.0.0.1:8000
"""

from __future__ import annotations

import json
from urllib import request as urlrequest
from urllib.error import URLError

DEFAULT_URL = "http://127.0.0.1:8000"


def generate(
    model: str,
    prompt: str,
    *,
    base_url: str = DEFAULT_URL,
    timeout: int = 300,
) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 512,
    }).encode()
    req = urlrequest.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=body,
        headers={"content-type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except URLError as e:
        raise RuntimeError(f"vLLM backend failed: {e}") from e

    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = data.get("usage") or {}
    return {
        "response": message.get("content", ""),
        "eval_count": usage.get("completion_tokens"),
        "prompt_eval_count": usage.get("prompt_tokens"),
        "backend": "vllm",
    }


def health(base_url: str = DEFAULT_URL) -> bool:
    try:
        with urlrequest.urlopen(f"{base_url.rstrip('/')}/health", timeout=3) as resp:
            return resp.status == 200
    except URLError:
        return False
