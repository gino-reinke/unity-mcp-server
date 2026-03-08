# Usage

## Run locally

### stdio (Claude Desktop / ChatGPT Desktop)

```bash
uv run python server.py
```

### HTTP (Claude Web)

```bash
uv run python server.py --transport streamable-http --host 127.0.0.1 --port 8000
```

The server binds to `http://127.0.0.1:8000/mcp` by default and exposes OAuth 2.0 endpoints for Claude Web.

---

## Claude Desktop setup

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

---

## ChatGPT Desktop setup

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

---

## Claude Web (claude.ai) setup

The server uses OAuth 2.0 (authorization code flow with PKCE) so Claude Web can authenticate automatically — no manual token setup required.

1. Create and configure a `.env` file:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `UNITY_PROJECTS_DIR` to the absolute path of your Unity Projects folder.

2. Expose the server publicly with [ngrok](https://ngrok.com/):

   ```bash
   ngrok http 8000
   ```

   Note the HTTPS forwarding URL (e.g. `https://abc123.ngrok-free.app`).

3. Start the server, passing the ngrok URL as `--public-url`:

   ```bash
   uv run python server.py --transport streamable-http --public-url https://abc123.ngrok-free.app
   ```

   The `--public-url` flag is required so the OAuth metadata points to the correct public address. Without it, Claude Web's browser redirect will fail.

4. In Claude.ai go to **Settings → Integrations → Add custom integration** and enter:
   - **URL:** `https://abc123.ngrok-free.app/mcp`
   - Leave OAuth fields blank — the server handles registration automatically.

5. Click **Add**. Claude Web will open a browser tab to complete the OAuth flow (auto-approved, no login required), then redirect back. The Unity tools are now available.

> **Note:** The ngrok URL changes each session on the free plan. Repeat steps 2–4 each time you restart ngrok, or use a paid ngrok account with a static domain and set `PUBLIC_URL` in `.env` instead.
>
> For permanent deployments, run the server on a VPS or cloud host instead of ngrok. Make sure the `/mcp` endpoint is reachable over HTTPS.
