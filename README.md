# unity-mcp-server

MCP server focused on Unity game development workflows. It provides tools to inspect Unity projects, read/write files, query git history, store project memory, search the web via Brave Search, and switch to a tutor-oriented mode.

## What it does

- Exposes Unity-specific tooling through an MCP server (`stdio` or HTTP transport)
- Restricts file operations to a configured Unity projects directory
- Persists project memory in SQLite (`data/memory.db`)
- Supports web/documentation lookup via Brave Search API (optional)
- Supports Claude Web via HTTP transport with OAuth 2.0 (ngrok-friendly)

## Getting started

- [Installation](installation.md) — requirements, install, and environment variable reference
- [Usage](usage.md) — running the server, Claude Desktop, ChatGPT Desktop, and Claude Web setup

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
