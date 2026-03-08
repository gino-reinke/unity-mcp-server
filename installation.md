# Installation

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
- `PUBLIC_URL` (required for ngrok/remote access): public HTTPS base URL used as the OAuth issuer (e.g. `https://abc123.ngrok-free.app`). Can also be passed as `--public-url` on the command line.

If `UNITY_PROJECTS_DIR` is not set, the server tries common Windows locations like:

- `~/Unity Projects`
- `~/Documents/Unity Projects`
- `~/OneDrive/Documents/Unity Projects`

### `.env` file

Copy the example and fill in your values:

```bash
cp .env.example .env
```
