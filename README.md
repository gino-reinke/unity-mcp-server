# unity-mcp-server

MCP server focused on Unity game development workflows. It provides tools to inspect Unity projects, read/write files, query git history, store project memory, search the web via Brave Search, and switch to a tutor-oriented mode.

## What it does

- Exposes Unity-specific tooling through an MCP server (`stdio` transport)
- Restricts file operations to a configured Unity projects directory
- Persists project memory in SQLite (`data/memory.db`)
- Supports web/documentation lookup via Brave Search API (optional)

## Requirements

- Python 3.11+
- `uv` (recommended) or `pip`
- Optional: Brave Search API key for search tools

## Install

```bash
uv sync
```

If you prefer `pip`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Configuration

The server reads configuration from:

1. Process environment variables
2. `claude_desktop_config.json` environment entries (if present)
3. Built-in defaults

### Environment variables

- `UNITY_PROJECTS_DIR` (recommended): absolute path to your Unity Projects folder
- `BRAVE_API_KEY` (optional): enables `brave_search` and `search_unity_docs`
- `STORAGE_BACKEND` (optional): currently defaults to `sqlite`
- `CLAUDE_DESKTOP_CONFIG_PATH` (optional): custom path to `claude_desktop_config.json`
- `MCP_SECRET` (recommended when using HTTP transport): shared Bearer token that must be sent by the client — the server rejects any request that omits or mismatches it

If `UNITY_PROJECTS_DIR` is not set, the server tries common Windows locations like:

- `~/Unity Projects`
- `~/Documents/Unity Projects`
- `~/OneDrive/Documents/Unity Projects`

## Run locally

### stdio (Claude Desktop)

```bash
uv run python server.py
```

### HTTP / Claude Web

```bash
uv run python server.py --transport streamable-http --host 127.0.0.1 --port 8000
```

The server binds to `http://127.0.0.1:8000/mcp` by default.

To expose it publicly (required for Claude Web), use a tunnelling tool such as [ngrok](https://ngrok.com/):

```bash
ngrok http 8000
```

Then use the forwarded HTTPS URL (e.g. `https://abc123.ngrok-free.app/mcp`) when adding the integration in Claude.

## Claude Desktop MCP config example

Add a server entry in your `claude_desktop_config.json`
(`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "unity-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "C:/Repos/unity-mcp-server/server.py"
      ],
      "env": {
        "UNITY_PROJECTS_DIR": "C:/Users/your-user/Documents/Unity Projects",
        "BRAVE_API_KEY": "your_brave_api_key_here"
      }
    }
  }
}
```

Adjust paths to match your machine.

## ChatGPT Desktop MCP config example

The ChatGPT desktop app supports MCP via the same stdio transport.
Create (or edit) the following file on Windows (ChatGPT is a Store app):

```
%LOCALAPPDATA%\Packages\OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0\LocalCache\Roaming\ChatGPT\mcp.json
```

```json
{
  "mcpServers": {
    "unity-mcp-server": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "C:/Repos/unity-mcp-server/server.py"
      ],
      "env": {
        "UNITY_PROJECTS_DIR": "C:/Users/your-user/Documents/Unity Projects",
        "BRAVE_API_KEY": "your_brave_api_key_here"
      }
    }
  }
}
```

After saving, restart ChatGPT Desktop. The Unity tools will appear exactly as they do in Claude Desktop — type `@unity-mcp-server` or reference any tool by name in the chat.

> **Note:** If ChatGPT Desktop stores its config in a different location on your machine, check **Settings → MCP** inside the app for the exact path.

## Claude Web (claude.ai) setup

1. Generate a strong random secret:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Save the output — you'll need it in steps 2 and 5.

2. Create and configure a `.env` file:

  ```bash
  cp .env.example .env
  ```

  Then edit `.env` and set:
  - `MCP_SECRET`: a strong random secret (use the output from step 1)
  - `UNITY_PROJECTS_DIR`: absolute path to your Unity Projects folder


3. Start the server:

   ```bash
   uv run python server.py --transport streamable-http --port 8000
   ```

4. Expose the server publicly — choose one option:

   **Option A — ngrok (quick, no account required for testing):**
   ```bash
   ngrok http 8000
   ```
   Then use the forwarded URL (e.g. `https://abc123.ngrok-free.app/mcp`) in step 5.
   Note: the free ngrok tier gives a random subdomain that changes on each restart.

   **Option B — Self-hosted VPS (permanent URL, free forever):**
   See [Self-Hosted VPS (Oracle Cloud Free Tier)](#self-hosted-vps-oracle-cloud-free-tier) below.

5. In Claude.ai go to **Settings → Integrations → Add custom integration** and fill in:
   - **URL:** `https://<your-public-url>/mcp`
   - **Authentication:** Bearer token → paste your secret from step 1

6. Save and start chatting — Claude will automatically discover and use the Unity tools.

## Self-Hosted VPS (Oracle Cloud Free Tier)

This is a permanent, zero-cost alternative to ngrok for exposing the server to Claude Web.

**Architecture:** the MCP server stays on your local machine (so it retains access to your Unity
project files). A free Oracle Cloud VM acts as a stable HTTPS entry point, and a persistent SSH
reverse tunnel connects the two.

```
Claude.ai → HTTPS → Oracle VM (Caddy) → SSH reverse tunnel → your machine (MCP server :8000)
```

**What you need (all free):**

| Resource | Purpose | Cost |
|----------|---------|------|
| [Oracle Cloud Always Free](https://www.oracle.com/cloud/free/) | ARM VM (1 vCPU, 6 GB RAM) | Free forever |
| [DuckDNS](https://www.duckdns.org) | Free subdomain (e.g. `myserver.duckdns.org`) | Free |
| Caddy | HTTPS reverse proxy + auto TLS (Let's Encrypt) | Free |
| autossh / PuTTY plink | Persistent SSH tunnel from local machine to VPS | Free |

### Step 1 — Create an Oracle Cloud Always Free VM

1. Sign up at <https://www.oracle.com/cloud/free/> (requires a credit card for identity, but you won't be charged for Always Free resources).
2. In the Console go to **Compute → Instances → Create Instance**.
3. Choose **Ubuntu 22.04 (aarch64)** as the image and select the **VM.Standard.A1.Flex** shape (ARM Ampere — part of Always Free).
4. Under **Add SSH keys** upload your public key (`~/.ssh/id_rsa.pub` or generate a new one).
5. Note the **Public IP address** once the VM is running.

### Step 2 — Open firewall ports in Oracle Cloud Console

Oracle has two independent firewall layers. Both must allow ports 80 and 443.

In the Console: **Networking → Virtual Cloud Networks → your VCN → Security Lists → Default Security List → Add Ingress Rules:**

| Source CIDR | Protocol | Port |
|------------|---------|------|
| `0.0.0.0/0` | TCP | 80 |
| `0.0.0.0/0` | TCP | 443 |

The OS-level firewall is handled automatically by the setup script in Step 3.

### Step 3 — Run the VPS setup script

SSH into your Oracle VM, clone this repo (or just copy the `deploy/` folder), then run:

```bash
chmod +x deploy/setup-oracle.sh
./deploy/setup-oracle.sh
```

This installs Caddy, opens iptables ports 80/443, and copies the Caddyfile template.

### Step 4 — Configure your free DuckDNS domain

1. Sign in at <https://www.duckdns.org> and create a subdomain (e.g. `myunity.duckdns.org`).
2. Set its IP to your Oracle VM public IP.
3. On the VPS, edit `/etc/caddy/Caddyfile` and replace `YOUR_DOMAIN.duckdns.org` with your actual subdomain:

   ```
   myunity.duckdns.org {
       reverse_proxy localhost:9000
   }
   ```

4. Restart Caddy: `sudo systemctl restart caddy`

Caddy will automatically obtain a Let's Encrypt TLS certificate. Check with:
```bash
curl https://myunity.duckdns.org/mcp
```
You should get a response (even a 401 Unauthorized is fine — it means Caddy and TLS are working).

### Step 5 — Set up the SSH reverse tunnel (local machine)

The tunnel forwards VPS port `9000` to your local MCP server port `8000`.

**Windows (PuTTY plink):**

1. Install PuTTY: `winget install PuTTY.PuTTY`
2. Edit `deploy/tunnel/keep-tunnel.ps1` — set `$VPS_HOST` and `$KEY_FILE`.
3. Accept the host key on first run: `plink -ssh ubuntu@YOUR_VPS_IP "echo ok"`
4. Run the script (stays alive in a loop, auto-reconnects):
   ```powershell
   powershell -ExecutionPolicy Bypass -File deploy\tunnel\keep-tunnel.ps1
   ```
5. To run automatically at logon, add a Task Scheduler task:
   - Trigger: At log on
   - Action: `powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\path\to\keep-tunnel.ps1"`

**Linux / WSL (autossh):**

1. Install autossh: `sudo apt-get install autossh`
2. Edit `deploy/tunnel/autossh.service` — replace `YOUR_VPS_IP`.
3. Install and enable:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp deploy/tunnel/autossh.service ~/.config/systemd/user/unity-mcp-tunnel.service
   systemctl --user enable --now unity-mcp-tunnel.service
   ```

**Verify the tunnel is active on the VPS:**
```bash
ssh ubuntu@YOUR_VPS_IP "ss -tlnp | grep 9000"
# Expected output: LISTEN ... 127.0.0.1:9000
```

### Step 6 — Start the local MCP server and connect Claude.ai

Start the server locally:
```bash
uv run python server.py --transport streamable-http --port 8000
```

In Claude.ai go to **Settings → Integrations → Add custom integration:**
- **URL:** `https://myunity.duckdns.org/mcp`
- **Authentication:** Bearer token → your `MCP_SECRET` value

### Troubleshooting

- **Caddy 502 Bad Gateway** — the SSH tunnel is not connected. Check the tunnel script/service is running and the VPS shows port 9000 listening.
- **Caddy returns a self-signed cert error** — DuckDNS domain not yet propagated or Caddy hasn't issued the cert. Wait a minute and try again.
- **Connection refused on port 443** — Oracle VCN Security List ports not opened (Step 2).
- **SSH tunnel disconnects frequently** — add `ServerAliveInterval 30` to `~/.ssh/config` for the VPS host.

## Available tools

### Filesystem tools

- `list_unity_projects`
- `get_project_structure(project_name)`
- `list_directory(path)`
- `read_file(file_path)`
- `write_file(file_path, content)`
- `create_script(project_name, script_name, script_content)`
- `search_files(project_name, pattern="*.cs", subdirectory="")`
- `get_file_info(file_path)`

### Git tools (read-only)

- `detect_git_repos`
- `git_status(project_name)`
- `git_log(project_name, max_count=15)`
- `git_diff(project_name, target="")`
- `git_branch_list(project_name)`

### Memory tools

- `store_memory(project, title, content, category="note", tags="")`
- `recall_memories(query="", project="", category="", tags="", limit=10)`
- `get_memory(memory_id)`
- `update_memory(memory_id, title="", content="", category="", tags="")`
- `delete_memory(memory_id)`
- `list_project_memories(project)`

### Search tools

- `brave_search(query, count=5)`
- `search_unity_docs(query, count=5)`
- `fetch_url(url, max_length=10000)`

### Tutor mode tools/prompts

- `toggle_learning_mode(enable=True)`
- `get_learning_status()`
- `explain_unity_concept(concept)`
- Prompt: `unity_tutor(topic="general Unity development")`
- Prompt: `unity_code_review(script_path="")`

## Storage

- Default database: `data/memory.db`
- Memory records include: project, category, title, content, tags, created/updated timestamps

## Notes

- `main.py` is a placeholder and not used as the server entrypoint.
- Large diffs and fetched web content are truncated for safety/readability.
- Search tools require `BRAVE_API_KEY`; without it, they return a configuration error message.
