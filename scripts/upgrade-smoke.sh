#!/usr/bin/env bash
# Local upgrade smoke (Linux/macOS). Pulls coder if Ollama is up.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CODER="${LUMEN_CODER_MODEL:-qwen2.5-coder:3b}"
GPU_MODEL="${LUMEN_GPU_BENCH_MODEL:-llama3.2:3b}"

python3 -m unittest tests.test_router_parity tests.test_code_tier tests.test_gpu_metrics -q
E07='Write a Python function to compute median decode tok/s from a list of benchmark runs.'
python3 lumen.py route --prompt "$E07"
python3 lumen.py route --tier code --prompt "$E07"
python3 scripts/probe_upgrade_models.py || true

if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  ollama pull "$CODER" || true
  python3 lumen.py gpu --model "$GPU_MODEL" --num-predict 64 || true
else
  echo "Ollama not running — skip pull/gpu. Start ollama serve on the NVIDIA box."
fi
echo "Done. LUMEN_CODE_TIER still unset (production default)."
