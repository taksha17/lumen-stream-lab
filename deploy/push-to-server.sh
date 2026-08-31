#!/usr/bin/env bash
# Push lumen-stream-lab to Windows server via SCP + remote setup
# Usage: ./deploy/push-to-server.sh [user@host]
set -euo pipefail

REMOTE="${1:-user@your-server}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_DIR="D:/lumen-stream-lab"
SSH_OPTS=(-F "${HOME}/.ssh/config" -o ConnectTimeout=15)

echo "=== Lumen deploy → ${REMOTE}:${REMOTE_DIR} ==="

# Test SSH
if ! ssh "${SSH_OPTS[@]}" "${REMOTE}" "echo SSH_OK" 2>/dev/null; then
  echo ""
  echo "ERROR: SSH auth failed."
  echo "Fix: see deploy/DEPLOY.md — add id_ed25519_amdopt.pub to server authorized_keys"
  echo ""
  echo "Manual fallback:"
  echo "  1. Zip: cd '$(dirname "$ROOT")' && zip -r lumen-stream-lab.zip lumen-stream-lab"
  echo "  2. Copy zip to server D:\\"
  echo "  3. Run: powershell -ExecutionPolicy Bypass -File D:\\lumen-stream-lab\\deploy\\win-setup.ps1"
  exit 1
fi

echo "Creating remote directory..."
ssh "${SSH_OPTS[@]}" "${REMOTE}" "powershell -Command \"New-Item -ItemType Directory -Force -Path 'D:\\lumen-stream-lab' | Out-Null\""

echo "Syncing files (rsync or scp)..."
if command -v rsync &>/dev/null; then
  rsync -avz --delete \
    --exclude '.git' \
    -e "ssh ${SSH_OPTS[*]}" \
    "${ROOT}/" "${REMOTE}:${REMOTE_DIR}/"
else
  scp "${SSH_OPTS[@]}" -r "${ROOT}/"* "${REMOTE}:${REMOTE_DIR}/"
fi

echo "Running remote setup..."
ssh "${SSH_OPTS[@]}" "${REMOTE}" "powershell -ExecutionPolicy Bypass -File D:\\lumen-stream-lab\\deploy\\win-setup.ps1"

echo ""
echo "=== Deploy complete ==="
echo "SSH in: ssh ${REMOTE}"
echo "Probe:  powershell -File D:\\lumen-stream-lab\\deploy\\win-probe.ps1"
