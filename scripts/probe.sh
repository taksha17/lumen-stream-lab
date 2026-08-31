#!/usr/bin/env bash
# Lumen hardware probe — writes hardware.json to repo root
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/hardware.json"

echo "=== Lumen Probe ==="

CPU_MODEL=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs || echo "unknown")
CPU_CORES=$(nproc 2>/dev/null || echo "unknown")
RAM_GB=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo "unknown")

if command -v nvidia-smi &>/dev/null; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
  GPU_VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
  GPU_DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
else
  GPU_NAME="none"
  GPU_VRAM_MB=0
  GPU_DRIVER="none"
fi

DISK_FREE_GB=$(df -BG "${ROOT}" 2>/dev/null | awk 'NR==2{gsub(/G/,"",$4); print $4}' || echo "unknown")

# Quick NVMe sequential read hint (optional, requires dd + root)
NVME_MBPS="not_measured"

cat > "${OUT}" <<EOF
{
  "probed_at": "$(date -Iseconds)",
  "cpu": {
    "model": "${CPU_MODEL}",
    "cores": ${CPU_CORES}
  },
  "ram_gb": ${RAM_GB},
  "gpu": {
    "name": "${GPU_NAME}",
    "vram_mb": ${GPU_VRAM_MB},
    "driver": "${GPU_DRIVER}",
    "cuda_available": $(python3 -c "import torch; print(str(torch.cuda.is_available()).lower())" 2>/dev/null || echo "false")
  },
  "disk": {
    "free_gb": ${DISK_FREE_GB},
    "seq_read_mbps": "${NVME_MBPS}"
  },
  "notes": "Ryzen 5600H + GTX 1650 4GB reference machine"
}
EOF

echo "Wrote ${OUT}"
cat "${OUT}"
