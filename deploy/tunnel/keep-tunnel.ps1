# keep-tunnel.ps1 — persistent SSH reverse tunnel for Unity MCP Server (Windows)
#
# Uses plink.exe from PuTTY to maintain an SSH reverse tunnel to the Oracle Cloud VPS.
# The script runs in an infinite loop, reconnecting automatically if the tunnel drops.
#
# PREREQUISITES:
#   1. Install PuTTY: https://www.putty.org
#      After install, plink.exe is at C:\Program Files\PuTTY\plink.exe
#      Or install via winget: winget install PuTTY.PuTTY
#
#   2. Set up SSH key auth (no password):
#      a. Generate a key in PuTTYgen (RSA 4096 bits), save the private key (.ppk)
#      b. Copy the public key text from PuTTYgen
#      c. On the VPS: echo "YOUR_PUBLIC_KEY" >> ~/.ssh/authorized_keys
#
#   3. First-run host key acceptance — run this once manually so plink saves the host key:
#        & "C:\Program Files\PuTTY\plink.exe" -ssh ubuntu@YOUR_VPS_IP "echo connected"
#      Type "y" when prompted to accept the host key.
#
#   4. Edit this script: replace YOUR_VPS_IP and YOUR_KEY_FILE below.
#
#   5. Run at Windows logon via Task Scheduler:
#      - Open Task Scheduler → Create Task
#      - Trigger: At log on
#      - Action: Start a program
#        Program: powershell.exe
#        Arguments: -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\path\to\keep-tunnel.ps1"
#      - Settings: Uncheck "Stop the task if it runs longer than"
#
# HOW IT WORKS:
#   plink opens an SSH connection to YOUR_VPS_IP and requests the VPS to listen on port 9000
#   (loopback). Connections to VPS:9000 are forwarded back through the tunnel to localhost:8000
#   on this machine where the MCP server runs.
#
#   Traffic flow:
#     Claude.ai → HTTPS → VPS Caddy (:443) → localhost:9000 → tunnel → local MCP (:8000)

# ── Configuration ─────────────────────────────────────────────────────────────

# Public IP or DuckDNS domain of your Oracle Cloud VPS.
$VPS_HOST = "YOUR_VPS_IP"

# SSH username on the VPS (Oracle Cloud Ubuntu default is "ubuntu").
$VPS_USER = "ubuntu"

# Path to your PuTTY private key file (.ppk).
$KEY_FILE  = "$env:USERPROFILE\.ssh\oracle-vps.ppk"

# Local MCP server port (must match --port in server.py startup command).
$LOCAL_PORT = 8000

# Port on the VPS that Caddy will proxy to (must match Caddyfile reverse_proxy port).
$VPS_PORT = 9000

# Path to plink.exe — adjust if PuTTY is installed elsewhere.
$PLINK = "C:\Program Files\PuTTY\plink.exe"

# Seconds to wait before reconnecting after a disconnect.
$RETRY_DELAY = 15

# ── Tunnel loop ───────────────────────────────────────────────────────────────

Write-Host "Unity MCP tunnel starting: $VPS_USER@$VPS_HOST  VPS:$VPS_PORT → local:$LOCAL_PORT"

while ($true) {
    Write-Host "$(Get-Date -Format 'HH:mm:ss') Connecting SSH tunnel..."
    & $PLINK -ssh `
        -i $KEY_FILE `
        -N `
        -R "${VPS_PORT}:127.0.0.1:${LOCAL_PORT}" `
        "${VPS_USER}@${VPS_HOST}"

    $exit = $LASTEXITCODE
    Write-Host "$(Get-Date -Format 'HH:mm:ss') Tunnel exited (code $exit). Retrying in ${RETRY_DELAY}s..."
    Start-Sleep -Seconds $RETRY_DELAY
}
