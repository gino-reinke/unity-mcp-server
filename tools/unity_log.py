"""Unity Editor log reader tools."""

import os
import re
import sys
from pathlib import Path


def _default_log_paths() -> list[Path]:
    """Return candidate Unity Editor log paths for the current platform."""
    if sys.platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        base = local / "Unity" / "Editor"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs" / "Unity"
    else:
        # Linux
        base = Path.home() / ".config" / "unity3d"

    return [base / "Editor.log", base / "Editor-prev.log"]


def _find_log(previous: bool) -> Path | None:
    """Return the path to the active (or previous) Unity Editor log, or None."""
    paths = _default_log_paths()
    target = paths[1] if previous else paths[0]
    return target if target.exists() else None


# Patterns that identify log severity
_ERROR_RE = re.compile(
    r"(^error\b|^exception\b|^unhandled exception|^failed|"
    r"Assets/.*\.cs\(\d+,\d+\):\s*error|"
    r"NullReferenceException|IndexOutOfRangeException|"
    r"MissingReferenceException|UnityException)",
    re.IGNORECASE,
)

_WARNING_RE = re.compile(
    r"(^warning\b|Assets/.*\.cs\(\d+,\d+\):\s*warning)",
    re.IGNORECASE,
)


def _classify(line: str) -> str:
    """Return 'error', 'warning', or 'info' for a log line."""
    stripped = line.strip()
    if _ERROR_RE.search(stripped):
        return "error"
    if _WARNING_RE.search(stripped):
        return "warning"
    return "info"


def register(mcp, config):
    """Register Unity log tools onto the MCP server."""

    @mcp.tool()
    def read_unity_log(
        lines: int = 200,
        filter_type: str = "all",
        search: str = "",
        previous_session: bool = False,
    ) -> str:
        """Read the Unity Editor log to help diagnose compiler errors and runtime exceptions.

        Unity writes its Editor log to a platform-specific location:
          Windows : %LOCALAPPDATA%\\Unity\\Editor\\Editor.log
          macOS   : ~/Library/Logs/Unity/Editor.log
          Linux   : ~/.config/unity3d/Editor.log

        Args:
            lines: Maximum number of lines to return from the end of the log (default 200).
            filter_type: One of 'all', 'errors', 'warnings', 'errors_and_warnings'.
                         Use 'errors' to focus on compiler errors and exceptions.
            search: Optional substring (case-insensitive) to filter lines.
            previous_session: If True, read Editor-prev.log (the last closed session).
        """
        log_path = _find_log(previous_session)
        if log_path is None:
            candidates = _default_log_paths()
            label = "Editor-prev.log" if previous_session else "Editor.log"
            return (
                f"Unity Editor log not found ({label}).\n"
                f"Searched: {candidates[1] if previous_session else candidates[0]}\n"
                "Make sure Unity Editor has been opened at least once."
            )

        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Could not read log file {log_path}: {exc}"

        all_lines = content.splitlines()
        total_lines = len(all_lines)

        # Apply filter_type
        filter_type = filter_type.lower().strip()
        if filter_type == "errors":
            kept = [l for l in all_lines if _classify(l) == "error"]
        elif filter_type == "warnings":
            kept = [l for l in all_lines if _classify(l) == "warning"]
        elif filter_type == "errors_and_warnings":
            kept = [l for l in all_lines if _classify(l) in ("error", "warning")]
        else:
            kept = all_lines

        # Apply search filter
        if search:
            needle = search.lower()
            kept = [l for l in kept if needle in l.lower()]

        # Tail to requested line count
        if len(kept) > lines:
            omitted = len(kept) - lines
            kept = kept[-lines:]
            tail_note = f"[Showing last {lines} of {len(kept) + omitted} matching lines]\n\n"
        else:
            tail_note = ""

        if not kept:
            filter_desc = filter_type if filter_type != "all" else ""
            search_desc = f" containing '{search}'" if search else ""
            return (
                f"No {filter_desc + ' ' if filter_desc else ''}log entries found"
                f"{search_desc} in {log_path.name}."
            )

        session_label = "Previous session" if previous_session else "Current session"
        size_kb = log_path.stat().st_size / 1024
        header = (
            f"Unity Editor Log — {session_label}\n"
            f"Path   : {log_path}\n"
            f"Size   : {size_kb:.1f} KB  |  Total lines: {total_lines}\n"
            f"Filter : {filter_type}"
            + (f"  |  Search: '{search}'" if search else "")
            + "\n"
            + "=" * 70
            + "\n"
        )

        return header + tail_note + "\n".join(kept)

    @mcp.tool()
    def get_unity_log_path() -> str:
        """Return the path(s) to the Unity Editor log files on this machine.

        Useful for confirming where Unity writes its logs before reading them.
        """
        paths = _default_log_paths()
        lines = ["Unity Editor log locations:\n"]
        labels = ["Current session (Editor.log)", "Previous session (Editor-prev.log)"]
        for label, path in zip(labels, paths):
            exists = path.exists()
            if exists:
                size_kb = path.stat().st_size / 1024
                status = f"EXISTS  ({size_kb:.1f} KB)"
            else:
                status = "not found"
            lines.append(f"  {label}\n    {path}\n    Status: {status}\n")
        return "\n".join(lines)
