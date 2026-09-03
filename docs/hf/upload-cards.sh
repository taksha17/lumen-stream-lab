#!/usr/bin/env bash
# Upload only model-card README.md files (no GGUF). Requires HF_TOKEN.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "export HF_TOKEN=hf_..." >&2
  exit 1
fi
hf upload takshathosani17/qwen2.5-3b-lumen "$ROOT/docs/hf/README-3b.md" README.md --repo-type model
hf upload takshathosani17/qwen2.5-7b-lumen "$ROOT/docs/hf/README-7b.md" README.md --repo-type model
echo "Cards updated."
