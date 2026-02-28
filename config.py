"""Centralized configuration for the Unity MCP server."""

import json
import os
from pathlib import Path


class Config:
    """Server configuration loaded from environment variables."""

    def __init__(self):
        self._claude_env = self._load_claude_desktop_env()

        self.unity_projects_dir_env_set = "UNITY_PROJECTS_DIR" in os.environ
        self.unity_projects_dir_config_set = "UNITY_PROJECTS_DIR" in self._claude_env
        self.unity_projects_dir, self.unity_projects_dir_source = (
            self._resolve_unity_projects_dir()
        )

        self.brave_api_key = self._get_config_value("BRAVE_API_KEY", "")
        self.storage_backend = self._get_config_value("STORAGE_BACKEND", "sqlite")

        # Ollama / local LLM settings
        self.ollama_base_url = self._get_config_value(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.ollama_model = self._get_config_value("OLLAMA_MODEL", "llama3.2")
        self.local_ai_enabled = self._get_config_value("LOCAL_AI_ENABLED", "true").lower() not in ("false", "0", "no")

        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        self.db_path = self.data_dir / "memory.db"
        self.learning_mode = False

    @staticmethod
    def _desktop_config_candidates():
        """Return possible locations of AI desktop app MCP config files."""
        home = Path(os.path.expanduser("~"))
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        local_appdata = Path(
            os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")
        )
        # Allow explicit override for Claude Desktop config
        configured = os.environ.get("CLAUDE_DESKTOP_CONFIG_PATH")
        configured_path = [Path(configured)] if configured else []
        return [
            *configured_path,
            # Claude Desktop (Windows store / portable)
            local_appdata
            / "Packages"
            / "Claude_pzs8sxrjxfjjc"
            / "LocalCache"
            / "Roaming"
            / "Claude"
            / "claude_desktop_config.json",
            appdata / "Claude" / "claude_desktop_config.json",
            home / ".claude" / "claude_desktop_config.json",
            Path.cwd() / "claude_desktop_config.json",
            # ChatGPT Desktop (Windows Store app)
            local_appdata
            / "Packages"
            / "OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0"
            / "LocalCache"
            / "Roaming"
            / "ChatGPT"
            / "mcp.json",
            # ChatGPT Desktop (non-Store / portable installs)
            appdata / "ChatGPT" / "mcp.json",
            local_appdata / "ChatGPT" / "mcp.json",
            # macOS paths (on Windows these simply won't exist)
            home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            home / "Library" / "Application Support" / "ChatGPT" / "mcp.json",
        ]

    def _load_claude_desktop_env(self):
        """Load env map from any supported desktop AI app MCP config file."""
        for path in self._desktop_config_candidates():
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue

            env = {}
            top_level_env = data.get("env", {})
            if isinstance(top_level_env, dict):
                for key, value in top_level_env.items():
                    if isinstance(key, str) and isinstance(value, str):
                        env[key] = value

            for server in data.get("mcpServers", {}).values():
                server_env = server.get("env", {})
                if isinstance(server_env, dict):
                    for key, value in server_env.items():
                        if isinstance(key, str) and isinstance(value, str):
                            env[key] = value
            if env:
                return env

        return {}

    def _get_config_value(self, key, default=""):
        """Return value from process env, then Claude Desktop config, then default."""
        return os.environ.get(key, self._claude_env.get(key, default))

    def _resolve_unity_projects_dir(self):
        """Resolve Unity project folder from env var or common defaults."""
        if self.unity_projects_dir_env_set:
            return Path(os.environ["UNITY_PROJECTS_DIR"]).resolve(), "env"
        if self.unity_projects_dir_config_set:
            return Path(self._claude_env["UNITY_PROJECTS_DIR"]).resolve(), "claude-config"

        home = Path(os.path.expanduser("~"))
        candidates = [
            home / "Unity Projects",
            home / "Documents" / "Unity Projects",
            home / "OneDrive" / "Documents" / "Unity Projects",
            home / "My Documents" / "Unity Projects",
        ]
        for path in candidates:
            resolved = path.resolve()
            if resolved.exists():
                return resolved, "auto-detected"

        return candidates[0].resolve(), "default"

    def validate(self):
        """Check configuration and return (level, message) records."""
        messages = []

        if not self.unity_projects_dir.exists():
            explicit_config = (
                self.unity_projects_dir_env_set or self.unity_projects_dir_config_set
            )
            level = "warning" if explicit_config else "info"
            messages.append(
                (
                    level,
                    (
                        f"Unity projects directory not found: "
                        f"{self.unity_projects_dir} "
                        f"(source: {self.unity_projects_dir_source}). "
                        "Set UNITY_PROJECTS_DIR or create this folder."
                    ),
                )
            )

        if not self.brave_api_key:
            messages.append(
                ("info", "BRAVE_API_KEY not set - search tools will not function")
            )

        return messages
