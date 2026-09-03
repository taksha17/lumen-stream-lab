#!/usr/bin/env bash
# Upload only model-card README.md files (no GGUF). Requires HF_TOKEN.
# Uses a repo-local .venv (PEP 668 — no system pip).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "export HF_TOKEN=hf_..." >&2
  exit 1
fi

VENV="$ROOT/.venv"
PY="$VENV/bin/python"
if [[ ! -x "$PY" ]]; then
  python3 -m venv "$VENV"
fi
"$PY" -m pip install -q -U huggingface_hub

export LUMEN_ROOT="$ROOT"
"$PY" - <<'PY'
import os
from pathlib import Path
from huggingface_hub import HfApi

root = Path(os.environ["LUMEN_ROOT"])
api = HfApi(token=os.environ["HF_TOKEN"])
cards = [
    ("takshathosani17/qwen2.5-3b-lumen", root / "docs/hf/README-3b.md"),
    ("takshathosani17/qwen2.5-7b-lumen", root / "docs/hf/README-7b.md"),
]
for repo, path in cards:
    if not path.is_file():
        raise SystemExit(f"missing {path}")
    api.upload_file(
        path_or_fileobj=str(path),
        path_in_repo="README.md",
        repo_id=repo,
        repo_type="model",
    )
    print(f"updated https://huggingface.co/{repo}")
PY
