#!/usr/bin/env bash
# setup-oracle.sh — Oracle Cloud Ubuntu 22.04 VPS setup for Unity MCP Server
#
# Run this ONCE on a fresh Oracle Cloud Always Free ARM instance:
#   chmod +x setup-oracle.sh && ./setup-oracle.sh
#
# After this script completes:
#   1. Open ports 80 and 443 in the Oracle Cloud Console (VCN Security List) — see step below
#   2. Edit /etc/caddy/Caddyfile and replace YOUR_DOMAIN with your DuckDNS domain
#   3. Restart Caddy: sudo systemctl restart caddy
#   4. Point your DuckDNS domain to this VPS's public IP
#   5. Set up an SSH reverse tunnel from your local machine (see deploy/tunnel/)

set -euo pipefail

echo "==> Updating system packages..."
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo "==> Installing prerequisites..."
sudo apt-get install -y curl gnupg apt-transport-https debian-keyring debian-archive-keyring netfilter-persistent iptables-persistent

echo "==> Installing Caddy from official repo..."
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update -y
sudo apt-get install -y caddy

echo "==> Opening OS firewall ports 80 and 443..."
# Oracle Cloud Ubuntu images ship with strict default iptables rules.
# These rules open HTTP and HTTPS at the OS level. You must ALSO open them
# in the Oracle Cloud Console → VCN → Security Lists (see instructions below).
sudo iptables  -I INPUT 6 -m state --state NEW -p tcp --dport 80  -j ACCEPT
sudo iptables  -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo ip6tables -I INPUT 6 -m state --state NEW -p tcp --dport 80  -j ACCEPT
sudo ip6tables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

echo "==> Allowing VPS to listen on 9000 on localhost for SSH reverse tunnel..."
# No extra firewall rule needed — 9000 is only bound to 127.0.0.1 on the VPS.

echo "==> Copying Caddyfile template..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/Caddyfile" ]; then
    sudo cp "$SCRIPT_DIR/Caddyfile" /etc/caddy/Caddyfile
    echo "    Copied $SCRIPT_DIR/Caddyfile → /etc/caddy/Caddyfile"
else
    echo "    WARNING: Caddyfile not found next to this script. Writing minimal template..."
    sudo tee /etc/caddy/Caddyfile > /dev/null <<'EOF'
YOUR_DOMAIN.duckdns.org {
    reverse_proxy localhost:9000
}
EOF
fi

echo "==> Enabling and starting Caddy..."
sudo systemctl enable caddy
sudo systemctl restart caddy

echo ""
echo "========================================================="
echo "  Setup complete! Manual steps remaining:"
echo "========================================================="
echo ""
echo "  1. OPEN ORACLE VCN PORTS (this script cannot do this):"
echo "     Oracle Cloud Console → Networking → Virtual Cloud Networks"
echo "     → Your VCN → Security Lists → Default Security List"
echo "     → Add Ingress Rules:"
echo "       Source CIDR: 0.0.0.0/0  Protocol: TCP  Port: 80"
echo "       Source CIDR: 0.0.0.0/0  Protocol: TCP  Port: 443"
echo ""
echo "  2. SET YOUR DOMAIN in /etc/caddy/Caddyfile:"
echo "     sudo nano /etc/caddy/Caddyfile"
echo "     Replace YOUR_DOMAIN.duckdns.org with your actual domain."
echo "     Then: sudo systemctl restart caddy"
echo ""
echo "  3. POINT YOUR DOMAIN to this VPS IP:"
echo "     Get this VPS's public IP: curl -s ifconfig.me"
echo "     Go to https://www.duckdns.org and set your subdomain to that IP."
echo ""
echo "  4. ON YOUR LOCAL MACHINE, set up the SSH reverse tunnel:"
echo "     See deploy/tunnel/autossh.service (Linux/WSL)"
echo "     or  deploy/tunnel/keep-tunnel.ps1  (Windows)"
echo ""
echo "  5. START your local MCP server:"
echo "     uv run python server.py --transport streamable-http --port 8000"
echo ""
echo "  6. TEST the public endpoint:"
echo "     curl -H 'Authorization: Bearer YOUR_MCP_SECRET' https://YOUR_DOMAIN.duckdns.org/mcp"
echo "========================================================="
