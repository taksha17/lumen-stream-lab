#!/usr/bin/env bash
# Non-interactive Lumen demo (no Hermes). Safe to run without Ollama — routing + gate only.
# Usage: ./scripts/demo.sh
# Record: vhs docs/demo.tape  -> docs/demo.gif
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CYAN='\033[36m'
GREEN='\033[32m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

section() {
  echo ""
  echo -e "${CYAN}${BOLD}==> $1${RESET}"
  echo ""
}

route_one() {
  local prompt="$1"
  echo -e "${DIM}prompt:${RESET} $prompt"
  python3 lumen.py route --prompt "$prompt" | python3 -c "
import json, sys
p = json.load(sys.stdin)
print(f\"  tier:   {p['tier']}\")
print(f\"  model:  {p['model']}\")
print(f\"  reason: {p['reason']}\")
"
  echo ""
}

echo -e "${BOLD}"
cat <<'BANNER'
==========================================
  LUMEN STREAM LAB
  hybrid routing demo (no Hermes)
==========================================
BANNER
echo -e "${RESET}"

section "1) Route three prompts (fast / balanced / domain)"
route_one "What is 2+2?"
route_one "Explain TCP vs UDP in one sentence."
route_one "What is Lumen Stream Lab?"

section "2) +40% orchestration gate (reference lab)"
python3 lumen.py compare --baseline 48.38 --optimized 68.1

section "3) Router parity (12-prompt CI suite)"
python3 -m unittest tests.test_router_parity -q

section "4) Gateway shape (plan JSON — start Ollama for live chat)"
echo -e "${DIM}curl -s localhost:8080/v1/plan -d '{\"prompt\":\"What is 2+2?\"}'${RESET}"
python3 lumen.py route --prompt "What is 2+2?" | python3 -c "
import json, sys
p = json.load(sys.stdin)
plan = {k: p[k] for k in ('tier', 'model', 'reason', 'backend', 'path') if k in p}
print(json.dumps(plan, indent=2))
"

echo ""
echo -e "${GREEN}Demo complete.${RESET} Interactive UI: ${BOLD}python3 lumen.py${RESET}"
echo -e "${DIM}Models: https://huggingface.co/takshathosani17/qwen2.5-3b-lumen${RESET}"
