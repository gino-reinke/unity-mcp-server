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

4. Expose the server publicly with ngrok (or any reverse proxy / cloud deployment):

   ```bash
   ngrok http 8000
   ```

5. In Claude.ai go to **Settings → Integrations → Add custom integration** and fill in:
   - **URL:** `https://<your-ngrok-subdomain>.ngrok-free.app/mcp`
   - **Authentication:** Bearer token → paste your secret from step 1

6. Save and start chatting — Claude will automatically discover and use the Unity tools.

> **Note:** For permanent deployments, run the server on a VPS or cloud host instead of using ngrok. Make sure the `/mcp` endpoint is reachable over HTTPS.

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
