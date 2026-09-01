# Deploy to server laptop (Windows)

Target: **D:\lumen-stream-lab** (Windows, free space on D:)

---

## SSH status (from dev machine)

| Check | Result |
|-------|--------|
| Host reachable (SSH port) | Yes — server responds |
| Ping (ICMP) | Blocked — normal on Windows |
| Auth (`~/.ssh/id_ed25519_amdopt`) | **Permission denied** — key not accepted yet |

### Fix SSH (one-time, on server laptop locally)

**Option A — Add your public key (recommended)**

On the **dev machine**, show the key:

```bash
cat ~/.ssh/id_ed25519_amdopt.pub
```

On the **server laptop** (PowerShell):

```powershell
# Create .ssh folder if missing
mkdir $env:USERPROFILE\.ssh -Force
notepad $env:USERPROFILE\.ssh\authorized_keys
# Paste the public key line, save

# Or if OpenSSH server uses different path for taksha user:
icacls $env:USERPROFILE\.ssh\authorized_keys /inheritance:r
icacls $env:USERPROFILE\.ssh\authorized_keys /grant "${env:USERNAME}:R"
```

Restart SSH service (Admin PowerShell):

```powershell
Restart-Service sshd
```

**Option B — Copy files manually**

1. Zip `lumen-stream-lab` from the dev machine
2. Copy to `D:\` on the server (USB, shared folder, etc.)
3. Run `D:\lumen-stream-lab\deploy\win-setup.ps1`

---

## Auto-deploy (once SSH works)

From the dev machine:

```bash
cd "/media/taksha/New Volume1/lumen-stream-lab"
./deploy/push-to-server.sh user@your-server
```

This copies the repo to `D:/lumen-stream-lab` and runs setup.

---

## Manual setup on server (D: drive)

```powershell
cd D:\lumen-stream-lab
powershell -ExecutionPolicy Bypass -File .\deploy\win-setup.ps1
```

---

## Verify after setup

```powershell
cd D:\lumen-stream-lab
.\deploy\win-probe.ps1
nvidia-smi
```

Fill in `docs/RESULTS.md` after running Ollama benchmark.
