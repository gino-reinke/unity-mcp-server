"""File system tools for browsing and editing Unity projects."""

import os
from pathlib import Path


UNITY_EXTENSIONS = {
    "scripts": {".cs", ".js"},
    "scenes": {".unity"},
    "prefabs": {".prefab"},
    "materials": {".mat"},
    "shaders": {".shader", ".cginc", ".hlsl"},
    "configs": {".asset", ".json", ".yaml", ".yml", ".xml"},
    "meta": {".meta"},
}


def register(mcp, config):
    """Register all filesystem tools onto the MCP server."""
    projects_dir = config.unity_projects_dir

    def _safe_resolve(path_str: str) -> Path:
        """Resolve a path and ensure it's within the allowed directory."""
        resolved = Path(path_str).resolve()
        if not str(resolved).startswith(str(projects_dir)):
            raise ValueError(
                f"Access denied: path{resolved} is outside "
                f"the Unity projects directory{projects_dir}"
            )
        return resolved

    @mcp.tool()
    def list_unity_projects() -> str:
        """List all Unity projects in the configured Unity Projects folder.
        Identifies projects by the presence of an Assets directory."""
        if not projects_dir.exists():
            return f"Unity projects directory not found:{projects_dir}"
        projects = []
        for item in sorted(projects_dir.iterdir()):
            if item.is_dir() and (item / "Assets").exists():
                has_git = (item / ".git").exists()
                scenes = list(item.rglob("*.unity"))
                scripts = list(item.rglob("*.cs"))
                projects.append(
                    f"{item.name}"
                    f"\n    Path:{item}"
                    f"\n    Git:{'Yes' if has_git else 'No'}"
                    f"\n    Scenes:{len(scenes)}"
                    f"\n    C# Scripts:{len(scripts)}"
                )
        if not projects:
            return f"No Unity projects found in{projects_dir}"
        header = f"Unity Projects in{projects_dir}:\n"
        return header + "\n".join(projects)

    @mcp.tool()
    def get_project_structure(project_name: str) -> str:
        """Get the top-level directory structure of a Unity project,
        showing Assets, Packages, ProjectSettings, etc."""
        project_path = _safe_resolve(str(projects_dir / project_name))
        if not project_path.exists():
            return f"Project not found:{project_name}"
        lines = [f"Project:{project_name}", f"Path:{project_path}", ""]
        for item in sorted(project_path.iterdir()):
            if item.name.startswith("."):
                prefix = "[hidden] "
            elif item.is_dir():
                child_count = sum(1 for _ in item.iterdir())
                prefix = f"[dir{child_count} items] "
            else:
                size_kb = item.stat().st_size / 1024
                prefix = f"[file{size_kb:.1f}KB] "
            lines.append(f"{prefix}{item.name}")
        return "\n".join(lines)

    @mcp.tool()
    def list_directory(path: str) -> str:
        """List the contents of any directory within the Unity projects folder.
        Use forward slashes or backslashes. Example: 'MyGame/Assets/Scripts'"""
        dir_path = _safe_resolve(str(projects_dir / path))
        if not dir_path.exists():
            return f"Directory not found:{path}"
        if not dir_path.is_dir():
            return f"Not a directory:{path}"
        lines = [f"Contents of{path}:", ""]
        for item in sorted(dir_path.iterdir()):
            if item.is_dir():
                lines.append(f"  [DIR]{item.name}/")
            else:
                size_kb = item.stat().st_size / 1024
                lines.append(f"  [FILE]{item.name} ({size_kb:.1f}KB)")
        return "\n".join(lines) if len(lines) > 2 else f"Directory is empty:{path}"

    @mcp.tool()
    def read_file(file_path: str) -> str:
        """Read the contents of a file within the Unity projects folder.
        Supports C# scripts, meta files, JSON, YAML, shaders, scene files, etc.
        Example: 'MyGame/Assets/Scripts/PlayerController.cs'"""
        full_path = _safe_resolve(str(projects_dir / file_path))
        if not full_path.exists():
            return f"File not found:{file_path}"
        if not full_path.is_file():
            return f"Not a file:{file_path}"
        size_mb = full_path.stat().st_size / (1024 * 1024)
        if size_mb > 5:
            return (
                f"File too large ({size_mb:.1f}MB). "
                "Only files under 5MB can be read."
            )
        try:
            content = full_path.read_text(encoding="utf-8")
            header = f"File:{file_path}\nSize:{len(content)} chars\n{'='*60}\n"
            return header + content
        except UnicodeDecodeError:
            return f"Cannot read binary file:{file_path}"

    @mcp.tool()
    def write_file(file_path: str, content: str) -> str:
        """Write or overwrite a file within the Unity projects folder.
        Creates parent directories if they don't exist.
        Example: write_file('MyGame/Assets/Scripts/NewScript.cs', '...')"""
        full_path = _safe_resolve(str(projects_dir / file_path))
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote{len(content)} chars to{file_path}"

    @mcp.tool()
    def create_script(
        project_name: str, script_name: str, script_content: str
    ) -> str:
        """Create a new C# script in a Unity project's Assets/Scripts folder.
        Automatically adds .cs extension if not present."""
        if not script_name.endswith(".cs"):
            script_name += ".cs"
        script_path = (
            projects_dir / project_name / "Assets" / "Scripts" / script_name
        )
        safe_path = _safe_resolve(str(script_path))
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(script_content, encoding="utf-8")
        relative = f"{project_name}/Assets/Scripts/{script_name}"
        return f"Created script:{relative}"

    @mcp.tool()
    def search_files(
        project_name: str,
        pattern: str = "*.cs",
        subdirectory: str = "",
    ) -> str:
        """Search for files matching a glob pattern within a Unity project.
        Examples: pattern='*.cs', pattern='*Controller*', pattern='*.unity'"""
        base = projects_dir / project_name
        if subdirectory:
            base = base / subdirectory
        base = _safe_resolve(str(base))
        if not base.exists():
            return f"Path not found:{project_name}/{subdirectory}"
        matches = sorted(base.rglob(pattern))
        if not matches:
            return f"No files matching '{pattern}' in{project_name}/{subdirectory}"
        lines = [f"Found{len(matches)} files matching '{pattern}':", ""]
        for match in matches[:100]:
            rel = match.relative_to(projects_dir)
            size_kb = match.stat().st_size / 1024
            lines.append(f"{rel} ({size_kb:.1f}KB)")
        if len(matches) > 100:
            lines.append(f"  ... and{len(matches) - 100} more")
        return "\n".join(lines)

    @mcp.tool()
    def get_file_info(file_path: str) -> str:
        """Get metadata about a file: size, modification date, extension type."""
        full_path = _safe_resolve(str(projects_dir / file_path))
        if not full_path.exists():
            return f"File not found:{file_path}"
        stat = full_path.stat()
        ext = full_path.suffix.lower()
        file_type = "unknown"
        for category, extensions in UNITY_EXTENSIONS.items():
            if ext in extensions:
                file_type = category
                break
        from datetime import datetime
        mod_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
        return (
            f"File:{file_path}\n"
            f"Size:{stat.st_size / 1024:.1f}KB\n"
            f"Type:{file_type} ({ext})\n"
            f"Modified:{mod_time}\n"
            f"Readable:{ext not in {'.prefab', '.unity', '.asset', '.mat'}}"
        )