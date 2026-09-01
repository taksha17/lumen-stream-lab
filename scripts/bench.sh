#!/usr/bin/env bash
# Lumen baseline benchmark helper
# Usage:
#   ./scripts/bench.sh --backend ollama --model mistral:7b-instruct-q4_0
#   ./scripts/bench.sh --list-backends
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROMPTS="${ROOT}/benchmarks/prompts.txt"
WARMUP=2
RUNS=5
MAX_TOKENS=128
BACKEND=""
MODEL=""

usage() {
  cat <<EOF
Usage: $0 --backend <ollama|llamacpp> --model <name> [options]

Options:
  --backend   Backend to benchmark (required unless --list-backends)
  --model     Model name or path (required)
  --warmup    Warmup runs (default: ${WARMUP})
  --runs      Measured runs (default: ${RUNS})
  --tokens    max_new_tokens (default: ${MAX_TOKENS})
  --list-backends  Show available backends

Examples:
  $0 --backend ollama --model mistral:7b-instruct-q4_0
  $0 --backend ollama --model llama3.2:3b
EOF
}

list_backends() {
  echo "Available backends:"
  command -v ollama &>/dev/null && echo "  ollama  — $(ollama --version 2>/dev/null || echo 'installed')"
  command -v llama-cli &>/dev/null && echo "  llamacpp — llama-cli found"
  command -v llama-server &>/dev/null && echo "  llamacpp — llama-server found"
}

bench_ollama() {
  local prompt="$1"
  local run_label="$2"
  echo "--- Ollama | ${MODEL} | ${run_label} ---"
  # Ollama prints eval stats when verbose; timing via /usr/bin/time as fallback
  local out
  out=$(/usr/bin/time -f 'ELAPSED:%e' ollama run "${MODEL}" "${prompt}" --verbose 2>&1) || true
  echo "${out}" | tail -20
  local elapsed
  elapsed=$(echo "${out}" | grep -oP 'ELAPSED:\K[0-9.]+' | tail -1 || echo "?")
  local eval_rate
  eval_rate=$(echo "${out}" | grep -oiE '[0-9.]+[[:space:]]*tokens?/s' | tail -1 || echo "see verbose output")
  echo "RUN_SUMMARY elapsed=${elapsed}s rate=${eval_rate}"
  echo ""
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend) BACKEND="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --warmup) WARMUP="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --tokens) MAX_TOKENS="$2"; shift 2 ;;
    --list-backends) list_backends; exit 0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

[[ -n "${BACKEND}" ]] || { usage; exit 1; }
[[ -n "${MODEL}" ]] || { usage; exit 1; }
[[ -f "${PROMPTS}" ]] || { echo "Missing ${PROMPTS}"; exit 1; }

PROMPT=$(head -3 "${PROMPTS}" | tail -1)
echo "=== Lumen Bench ==="
echo "Backend: ${BACKEND}"
echo "Model:   ${MODEL}"
echo "Prompt:  ${PROMPT:0:60}..."
echo "Warmup:  ${WARMUP} | Runs: ${RUNS}"
echo ""

case "${BACKEND}" in
  ollama)
    command -v ollama &>/dev/null || { echo "ollama not installed"; exit 1; }
    for i in $(seq 1 "${WARMUP}"); do bench_ollama "${PROMPT}" "warmup-${i}"; done
    for i in $(seq 1 "${RUNS}"); do bench_ollama "${PROMPT}" "run-${i}"; done
    ;;
  llamacpp)
    echo "llamacpp bench: set -m path/to/model.gguf and use llama-cli manually for now."
    echo "See benchmarks/PROTOCOL.md"
    exit 1
    ;;
  *)
    echo "Unknown backend: ${BACKEND}"
    exit 1
    ;;
esac

echo "Record medians in docs/RESULTS.md"
echo "Compare optimized run using same model + prompts."
