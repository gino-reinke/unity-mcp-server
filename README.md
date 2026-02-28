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

If `UNITY_PROJECTS_DIR` is not set, the server tries common Windows locations like:

- `~/Unity Projects`
- `~/Documents/Unity Projects`
- `~/OneDrive/Documents/Unity Projects`

## Run locally

```bash
uv run python server.py
```

The server starts with `stdio` transport and registers all tools at startup.

## Claude Desktop MCP config example

Add a server entry in your `claude_desktop_config.json`:

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
