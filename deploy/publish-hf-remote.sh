#!/usr/bin/env bash
# Publish domain GGUF to Hugging Face via the Windows reference lab (GGUF stays on server).
# Usage:
#   export HF_TOKEN=hf_...
#   ./deploy/publish-hf-remote.sh takshathosani17/qwen2.5-3b-lumen
#   ./deploy/publish-hf-remote.sh takshathosani17/qwen2.5-3b-lumen --dry-run
set -euo pipefail

REPO_ID="${1:?usage: $0 USER/repo [--dry-run]}"
DRY_RUN="${2:-}"
SSH_HOST="${LUMEN_SSH_HOST:-Taksha Thosani@192.168.4.31}"
LAB_ROOT="${LUMEN_LAB_ROOT:-D:\\lumen-stream-lab}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "HF_TOKEN not set. export HF_TOKEN=hf_..." >&2
  exit 1
fi

EXTRA=""
if [[ "$DRY_RUN" == "--dry-run" ]]; then
  EXTRA="-DryRun"
fi

ssh -o BatchMode=yes "$SSH_HOST" \
  "powershell -NoProfile -ExecutionPolicy Bypass -Command \"\$env:HF_TOKEN='$HF_TOKEN'; & '$LAB_ROOT\\deploy\\win-publish-hf.ps1' -RepoId '$REPO_ID' $EXTRA\""
