"""Local LLM tools via Ollama — offload simple tasks without burning cloud tokens."""

import httpx

from tools.unity_log import _find_log, _default_log_paths, _ERROR_RE, _WARNING_RE


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _disabled_msg(config) -> str:
    return (
        "Local AI processing is currently DISABLED.\n"
        "Ask me to run 'toggle_local_ai(enable=true)' to turn it on."
    )


async def _ollama_chat(config, prompt: str, system: str = "") -> str:
    """Send a chat request to the Ollama API and return the response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    url = f"{config.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": config.ollama_model,
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
    except httpx.ConnectError:
        return (
            f"Could not connect to Ollama at {config.ollama_base_url}.\n"
            "Make sure Ollama is running: https://ollama.com"
        )
    except httpx.TimeoutException:
        return f"Ollama request timed out after 120 s (model: {config.ollama_model})."

    if resp.status_code != 200:
        return f"Ollama error {resp.status_code}: {resp.text[:400]}"

    data = resp.json()
    return data.get("message", {}).get("content", "").strip()


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register(mcp, config):
    """Register local LLM tools onto the MCP server."""

    # ------------------------------------------------------------------
    # Toggle / status
    # ------------------------------------------------------------------

    @mcp.tool()
    def toggle_local_ai(enable: bool = True) -> str:
        """Enable or disable local AI processing via Ollama.

        When enabled, tools like analyze_unity_errors and explain_code
        send work to your local Ollama model instead of using Claude tokens.

        Call toggle_local_ai(enable=true) to turn on.
        Call toggle_local_ai(enable=false) to turn off.
        """
        config.local_ai_enabled = enable
        if enable:
            return (
                f"Local AI processing ENABLED.\n"
                f"Model  : {config.ollama_model}\n"
                f"Ollama : {config.ollama_base_url}\n\n"
                "Ollama-powered tools (analyze_unity_errors, explain_code, "
                "query_local_llm) will now route to your local model."
            )
        return (
            "Local AI processing DISABLED.\n"
            "Ollama tools will return an informational message instead of "
            "calling the local model. Use toggle_local_ai(enable=true) to re-enable."
        )

    @mcp.tool()
    def get_local_ai_status() -> str:
        """Check the current status of local AI processing.

        Returns whether Ollama is enabled, which model is active,
        and the configured base URL.
        """
        status = "ENABLED" if config.local_ai_enabled else "DISABLED"
        return (
            f"Local AI status : {status}\n"
            f"Model           : {config.ollama_model}\n"
            f"Ollama URL      : {config.ollama_base_url}\n\n"
            "To change model use: set_ollama_model(model_name='<name>')\n"
            "To list installed models use: list_ollama_models()"
        )

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_ollama_models() -> str:
        """List all models currently installed in Ollama.

        Shows model name, size, and when it was last modified.
        Use this to see which models you can switch to with set_ollama_model().
        """
        url = f"{config.ollama_base_url.rstrip('/')}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
        except httpx.ConnectError:
            return (
                f"Could not reach Ollama at {config.ollama_base_url}.\n"
                "Make sure Ollama is running."
            )

        if resp.status_code != 200:
            return f"Ollama error {resp.status_code}: {resp.text[:300]}"

        models = resp.json().get("models", [])
        if not models:
            return (
                "No models installed in Ollama.\n"
                "Install one with: ollama pull llama3.2"
            )

        active = config.ollama_model
        lines = [f"Installed Ollama models (active: {active}):\n"]
        for m in models:
            name = m.get("name", "unknown")
            size_gb = m.get("size", 0) / 1_073_741_824
            marker = " ◀ active" if name == active or name.split(":")[0] == active else ""
            lines.append(f"  {name}  ({size_gb:.1f} GB){marker}")

        lines.append(
            "\nTo switch: set_ollama_model(model_name='<name>')\n"
            "To install: run  ollama pull <name>  in your terminal"
        )
        return "\n".join(lines)

    @mcp.tool()
    def set_ollama_model(model_name: str) -> str:
        """Switch the active Ollama model used for local AI processing.

        The change takes effect immediately for all subsequent local AI calls.
        Use list_ollama_models() first to see what is installed.

        Examples:
            set_ollama_model('llama3.2')
            set_ollama_model('mistral')
            set_ollama_model('codellama')
            set_ollama_model('phi3')
            set_ollama_model('gemma2:2b')
        """
        previous = config.ollama_model
        config.ollama_model = model_name.strip()
        return (
            f"Ollama model switched.\n"
            f"  Previous : {previous}\n"
            f"  Active   : {config.ollama_model}\n\n"
            "All local AI tools will now use this model.\n"
            "If the model is not installed, Ollama will return an error — "
            f"run  ollama pull {config.ollama_model}  to install it."
        )

    # ------------------------------------------------------------------
    # General-purpose query
    # ------------------------------------------------------------------

    @mcp.tool()
    async def query_local_llm(prompt: str, system: str = "") -> str:
        """Send any prompt to your local Ollama model and get a response.

        Use this to offload simple questions, explanations, or text tasks
        to the local model instead of using Claude tokens.

        Args:
            prompt: The question or instruction to send.
            system: Optional system prompt to set the model's persona/context.

        Examples:
            query_local_llm('What is the difference between Update and FixedUpdate in Unity?')
            query_local_llm('Summarize this error in one sentence: ...', system='You are a Unity expert.')
        """
        if not config.local_ai_enabled:
            return _disabled_msg(config)

        result = await _ollama_chat(config, prompt, system)
        return f"[{config.ollama_model}]\n\n{result}"

    # ------------------------------------------------------------------
    # Unity log analysis
    # ------------------------------------------------------------------

    @mcp.tool()
    async def analyze_unity_errors(lines: int = 150, previous_session: bool = False) -> str:
        """Read the Unity Editor log and use the local LLM to summarize errors.

        Filters the log down to errors and warnings, then asks the local
        Ollama model to explain what went wrong and suggest fixes.
        Much cheaper than sending raw logs to Claude.

        Args:
            lines: Max log lines to analyse (default 150).
            previous_session: If True, analyse Editor-prev.log instead.
        """
        if not config.local_ai_enabled:
            return _disabled_msg(config)

        log_path = _find_log(previous_session)
        if log_path is None:
            candidates = _default_log_paths()
            return (
                "Unity Editor log not found.\n"
                f"Searched: {candidates[1] if previous_session else candidates[0]}"
            )

        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Could not read log: {exc}"

        all_lines = content.splitlines()
        kept = [
            l for l in all_lines
            if _ERROR_RE.search(l.strip()) or _WARNING_RE.search(l.strip())
        ]

        if not kept:
            return "No errors or warnings found in the Unity Editor log."

        if len(kept) > lines:
            kept = kept[-lines:]

        log_text = "\n".join(kept)

        prompt = (
            "You are a Unity game development expert. "
            "Below are errors and warnings from a Unity Editor log.\n\n"
            "Please:\n"
            "1. List each distinct problem in plain English (one sentence each)\n"
            "2. Give the most likely cause for each\n"
            "3. Suggest a concrete fix\n\n"
            f"LOG:\n{log_text}"
        )

        result = await _ollama_chat(config, prompt)
        header = (
            f"Unity log analysis by {config.ollama_model} "
            f"({len(kept)} error/warning lines from {log_path.name}):\n"
            + "=" * 60 + "\n"
        )
        return header + result

    # ------------------------------------------------------------------
    # Code explanation
    # ------------------------------------------------------------------

    @mcp.tool()
    async def explain_code(file_path: str) -> str:
        """Read a C# script from your Unity project and explain it using the local LLM.

        Sends the file contents to Ollama and returns a plain-English
        explanation — useful for quickly understanding unfamiliar code
        without spending Claude tokens.

        Args:
            file_path: Absolute path or path relative to the Unity projects directory.
        """
        if not config.local_ai_enabled:
            return _disabled_msg(config)

        from pathlib import Path

        path = Path(file_path)
        if not path.is_absolute():
            path = config.unity_projects_dir / file_path

        if not path.exists():
            return f"File not found: {path}"

        size = path.stat().st_size
        if size > 50_000:
            return (
                f"File is too large ({size / 1024:.0f} KB) to send to a local model. "
                "Consider reading a specific section with read_file() first."
            )

        try:
            code = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Could not read file: {exc}"

        prompt = (
            f"You are a Unity C# expert. Explain the following script clearly:\n\n"
            f"File: {path.name}\n\n"
            f"```csharp\n{code}\n```\n\n"
            "Cover: what it does, how it works, any important Unity patterns used, "
            "and any potential issues or improvements."
        )

        result = await _ollama_chat(config, prompt)
        return f"[{config.ollama_model}] Explanation of {path.name}:\n\n{result}"
