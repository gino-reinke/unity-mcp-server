"""File system tools for browsing and editing Unity projects."""

import os
import re
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

# ---- Unity scene/prefab inspector ----

UNITY_CLASS_IDS = {
    1: "GameObject", 4: "Transform", 20: "Camera", 23: "MeshRenderer",
    25: "Renderer", 33: "MeshFilter", 54: "Rigidbody", 64: "MeshCollider",
    65: "BoxCollider", 82: "AudioSource", 95: "Animator", 108: "Light",
    114: "MonoBehaviour", 136: "MeshCollider", 195: "NavMeshAgent",
    212: "SpriteRenderer", 224: "RectTransform", 225: "Canvas",
    226: "CanvasRenderer", 227: "CanvasGroup",
}

_DOC_RE = re.compile(r'^--- !u!(\d+) &(-?\d+)', re.MULTILINE)


def _re_str(text, pattern, default=""):
    m = re.search(pattern, text)
    return m.group(1).strip() if m else default


def _re_int(text, pattern, default=0):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else default


def _re_vec3(text, field):
    m = re.search(
        rf'{re.escape(field)}:\s*\{{x:\s*(-?[\d.eE+\-]+),\s*y:\s*(-?[\d.eE+\-]+),\s*z:\s*(-?[\d.eE+\-]+)\}}',
        text,
    )
    return tuple(float(v) for v in m.groups()) if m else None


def _fmt_f(n):
    r = round(n, 3)
    return str(int(r)) if r == int(r) else str(r)


def _fmt_v3(v):
    return f"({_fmt_f(v[0])}, {_fmt_f(v[1])}, {_fmt_f(v[2])})" if v else ""


def _nonzero_v3(v):
    return v is not None and any(abs(x) > 0.0001 for x in v)


def _non_unit_scale(v):
    return v is not None and any(abs(x - 1) > 0.0001 for x in v)


def _non_identity_quat(raw):
    m = re.search(
        r'm_LocalRotation:\s*\{x:\s*(-?[\d.eE+\-]+),\s*y:\s*(-?[\d.eE+\-]+),'
        r'\s*z:\s*(-?[\d.eE+\-]+),\s*w:\s*(-?[\d.eE+\-]+)\}',
        raw,
    )
    if not m:
        return False
    x, y, z, w = (float(v) for v in m.groups())
    return not (abs(x) < 0.0001 and abs(y) < 0.0001 and abs(z) < 0.0001 and abs(abs(w) - 1) < 0.0001)


def _inspect_unity_content(content: str, component_filter: str = "") -> str:
    """Parse Unity YAML and return a human-readable hierarchy."""
    splits = list(_DOC_RE.finditer(content))
    if not splits:
        return "No Unity objects found."

    # Parse all documents into (class_id, raw_text)
    docs = {}
    for i, m in enumerate(splits):
        class_id = int(m.group(1))
        file_id = int(m.group(2))
        start = m.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(content)
        docs[file_id] = (class_id, content[start:end])

    # Extract GameObjects (class 1)
    game_objects = {}
    for fid, (cid, raw) in docs.items():
        if cid != 1:
            continue
        comp_ids = [int(x) for x in re.findall(r'component:\s*\{fileID:\s*(\d+)\}', raw)]
        game_objects[fid] = {
            "name": _re_str(raw, r'm_Name:\s*(.+)') or f"<{fid}>",
            "tag": _re_str(raw, r'm_TagString:\s*(.+)', "Untagged"),
            "layer": _re_int(raw, r'm_Layer:\s*(\d+)'),
            "active": bool(_re_int(raw, r'm_IsActive:\s*(\d+)', 1)),
            "comp_ids": comp_ids,
        }

    # Extract Transforms (class 4) and RectTransforms (class 224)
    transforms = {}
    go_to_xform = {}
    for fid, (cid, raw) in docs.items():
        if cid not in (4, 224):
            continue
        go_id = _re_int(raw, r'm_GameObject:\s*\{fileID:\s*(\d+)\}')
        pos = _re_vec3(raw, 'm_LocalPosition')
        scale = _re_vec3(raw, 'm_LocalScale')
        euler = _re_vec3(raw, 'm_LocalEulerAnglesHint')
        has_rot = _non_identity_quat(raw)
        # Extract children fileIDs (between m_Children: and m_Father:)
        cm = re.search(r'm_Children:(.*?)m_Father:', raw, re.DOTALL)
        children = []
        if cm:
            children = [int(x) for x in re.findall(r'\{fileID:\s*(-?\d+)\}', cm.group(1)) if int(x) != 0]
        father = _re_int(raw, r'm_Father:\s*\{fileID:\s*(-?\d+)\}')
        transforms[fid] = {
            "go_id": go_id, "pos": pos, "scale": scale,
            "euler": euler, "has_rot": has_rot,
            "children": children, "father": father,
        }
        if go_id:
            go_to_xform[go_id] = fid

    def format_transform(tfid):
        t = transforms.get(tfid)
        if not t:
            return "  Transform"
        parts = ["Transform"]
        if _nonzero_v3(t["pos"]):
            parts.append(f"pos={_fmt_v3(t['pos'])}")
        if t["has_rot"] and t["euler"] and _nonzero_v3(t["euler"]):
            parts.append(f"rot={_fmt_v3(t['euler'])}°")
        elif t["has_rot"]:
            parts.append("rot=<non-zero>")
        if _non_unit_scale(t["scale"]):
            parts.append(f"scale={_fmt_v3(t['scale'])}")
        return "  " + "  ".join(parts)

    def format_component(comp_fid):
        if comp_fid not in docs:
            return None
        cid, raw = docs[comp_fid]
        name = UNITY_CLASS_IDS.get(cid, f"Component({cid})")
        if cid in (4, 224):
            return format_transform(comp_fid)
        if cid == 114:  # MonoBehaviour — show user-defined properties
            custom = {}
            for line in raw.splitlines():
                s = line.strip()
                m = re.match(r'^([a-zA-Z][a-zA-Z0-9_]*)\s*:\s*(.+)$', s)
                if m:
                    k, v = m.group(1), m.group(2).strip()
                    if (not k.startswith('m_') and v
                            and not v.startswith('{')
                            and not v.startswith('-')
                            and not v.startswith('[')
                            and k not in ('MonoBehaviour', 'serializedVersion')):
                        custom[k] = v[:50]
            suffix = ("  " + "  ".join(f"{k}={v}" for k, v in list(custom.items())[:6])) if custom else ""
            return f"  MonoBehaviour{suffix}"
        return f"  {name}"

    def render_go(go_fid, indent=""):
        go = game_objects.get(go_fid)
        if not go:
            return []
        lines = []
        active_str = "" if go["active"] else " [inactive]"
        tag_str = f" | Tag: {go['tag']}" if go["tag"] not in ("Untagged", "") else ""
        layer_str = f" | Layer: {go['layer']}" if go["layer"] != 0 else ""
        lines.append(f"{indent}{go['name']}{active_str}{tag_str}{layer_str}")
        for comp_fid in go["comp_ids"]:
            line = format_component(comp_fid)
            if line:
                lines.append(f"{indent}{line}")
        # Recurse into children via transform hierarchy
        tfid = go_to_xform.get(go_fid)
        if tfid:
            for child_tfid in transforms[tfid]["children"]:
                child_go = transforms.get(child_tfid, {}).get("go_id")
                if child_go and child_go in game_objects:
                    lines.append("")
                    lines.extend(render_go(child_go, indent + "  "))
        return lines

    # Root GameObjects: transforms whose father is 0 (no parent)
    root_fids = []
    for t in transforms.values():
        if t["father"] == 0 and t["go_id"] in game_objects:
            root_fids.append(t["go_id"])
    # Include any GameObjects that have no transform at all
    covered = {t["go_id"] for t in transforms.values() if t["go_id"]}
    for go_fid in game_objects:
        if go_fid not in covered and go_fid not in root_fids:
            root_fids.append(go_fid)

    total_comps = sum(len(go["comp_ids"]) for go in game_objects.values())
    header = f"GameObjects: {len(game_objects)}  |  Components: {total_comps}"

    if component_filter:
        filter_lower = component_filter.strip().lower()
        matching = []
        for go_fid, go in game_objects.items():
            for comp_fid in go["comp_ids"]:
                if comp_fid not in docs:
                    continue
                cid, _ = docs[comp_fid]
                cname = UNITY_CLASS_IDS.get(cid, f"Component({cid})")
                if filter_lower in cname.lower():
                    matching.append(go_fid)
                    break
        if not matching:
            return f"{header}\nNo GameObjects found with component matching '{component_filter}'."
        out = [header, f"Filter: component='{component_filter}' — {len(matching)} match(es)", ""]
        for go_fid in matching:
            go = game_objects[go_fid]
            active_str = "" if go["active"] else " [inactive]"
            tag_str = f" | Tag: {go['tag']}" if go["tag"] not in ("Untagged", "") else ""
            layer_str = f" | Layer: {go['layer']}" if go["layer"] != 0 else ""
            out.append(f"{go['name']}{active_str}{tag_str}{layer_str}")
            for comp_fid in go["comp_ids"]:
                line = format_component(comp_fid)
                if line:
                    out.append(line)
            out.append("")
        return "\n".join(out).rstrip()

    out = [header, ""]
    for i, go_fid in enumerate(root_fids):
        if i >= 100:
            out.append(f"... [{len(root_fids) - 100} more root objects not shown]")
            break
        out.extend(render_go(go_fid))
        out.append("")

    return "\n".join(out).rstrip()


def _inspect_asset_content(content: str) -> str:
    """Parse a Unity .asset (ScriptableObject) file and return readable data."""
    splits = list(_DOC_RE.finditer(content))
    if not splits:
        return "No Unity objects found."

    out_parts = []
    for i, m in enumerate(splits):
        class_id = int(m.group(1))
        start = m.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(content)
        raw = content[start:end]

        class_name = UNITY_CLASS_IDS.get(class_id, f"Object({class_id})")
        obj_name = _re_str(raw, r'm_Name:\s*(.+)', f'<{class_name}>')

        if class_id == 114:  # MonoBehaviour — used for ScriptableObjects
            fields = {}
            for line in raw.splitlines():
                s = line.strip()
                mm = re.match(r'^([a-zA-Z][a-zA-Z0-9_]*)\s*:\s*(.+)$', s)
                if mm:
                    k, v = mm.group(1), mm.group(2).strip()
                    if (not k.startswith('m_') and v
                            and not v.startswith('{')
                            and not v.startswith('-')
                            and not v.startswith('[')
                            and k not in ('MonoBehaviour', 'serializedVersion')):
                        fields[k] = v[:80]
            lines = [f"ScriptableObject: {obj_name}"]
            if fields:
                lines.append("  Fields:")
                for k, v in fields.items():
                    lines.append(f"    {k}: {v}")
            else:
                lines.append("  (no user-defined serialized fields found)")
            out_parts.append("\n".join(lines))
        else:
            out_parts.append(f"{class_name}: {obj_name}")

    return "\n\n".join(out_parts) if out_parts else "No objects parsed."


def _inspect_material_content(content: str) -> str:
    """Parse a Unity .mat (Material) file and return readable property data."""
    splits = list(_DOC_RE.finditer(content))
    if not splits:
        return "No Unity objects found."

    for i, m in enumerate(splits):
        class_id = int(m.group(1))
        if class_id != 21:  # Material
            continue
        start = m.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(content)
        raw = content[start:end]

        mat_name = _re_str(raw, r'm_Name:\s*(.+)', '<unnamed>')
        lines = [f"Material: {mat_name}"]

        keywords = _re_str(raw, r'm_ShaderKeywords:\s*(.+)', '').strip()
        if keywords:
            lines.append(f"Shader Keywords: {keywords}")

        render_queue = _re_str(raw, r'm_CustomRenderQueue:\s*(.+)', '').strip()
        if render_queue and render_queue != '-1':
            lines.append(f"Render Queue: {render_queue}")

        saved = re.search(r'm_SavedProperties:(.*)', raw, re.DOTALL)
        if saved:
            props = saved.group(1)

            tex_block = re.search(r'm_TexEnvs:(.*?)(?=m_Ints:|m_Floats:|m_Colors:|\Z)', props, re.DOTALL)
            if tex_block:
                tex_names = re.findall(r'^\s+- (\w+):', tex_block.group(1), re.MULTILINE)
                if tex_names:
                    lines.append(f"Texture slots: {', '.join(tex_names)}")

            float_block = re.search(r'm_Floats:(.*?)(?=m_Colors:|\Z)', props, re.DOTALL)
            if float_block:
                floats = re.findall(r'- (\w+):\s*(-?[\d.eE+\-]+)', float_block.group(1))
                if floats:
                    lines.append("Floats:")
                    for prop_name, val in floats[:15]:
                        lines.append(f"  {prop_name}: {val}")

            color_block = re.search(r'm_Colors:(.*)', props, re.DOTALL)
            if color_block:
                colors = re.findall(
                    r'- (\w+):\s*\{r:\s*(-?[\d.]+),\s*g:\s*(-?[\d.]+),\s*b:\s*(-?[\d.]+),\s*a:\s*(-?[\d.]+)\}',
                    color_block.group(1),
                )
                if colors:
                    lines.append("Colors:")
                    for prop_name, r, g, b, a in colors[:10]:
                        lines.append(f"  {prop_name}: rgba({r}, {g}, {b}, {a})")

        return "\n".join(lines)

    return "No Material (class 21) found in file."


def register(mcp, config):
    """Register all filesystem tools onto the MCP server."""
    projects_dir = config.unity_projects_dir

    def _safe_resolve(path_str: str) -> Path:
        """Resolve a path and ensure it's within the allowed directory."""
        resolved = Path(path_str).resolve()
        try:
            resolved.relative_to(projects_dir.resolve())
        except ValueError:
            raise ValueError(
                f"Access denied: path {resolved} is outside "
                f"the Unity projects directory {projects_dir}"
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
    def grep_in_project(
        query: str,
        project_name: str = "",
        pattern: str = "*.cs",
        case_sensitive: bool = False,
        use_regex: bool = False,
        max_matches: int = 200,
    ) -> str:
        """Search file contents within a Unity project for a string or regex pattern.
        Returns matching lines with file path and line number.
        Leave project_name empty to search across all projects.
        Examples:
          grep_in_project('Physics.Raycast', 'MyGame')
          grep_in_project('FindObjectOfType', pattern='*.cs')
          grep_in_project('Start|Awake', 'MyGame', use_regex=True)
          grep_in_project('Camera.main', pattern='*.cs', case_sensitive=True)"""
        base = _safe_resolve(str(projects_dir / project_name)) if project_name else projects_dir
        if not base.exists():
            return f"Path not found: {project_name or projects_dir}"

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(query if use_regex else re.escape(query), flags)
        except re.error as e:
            return f"Invalid regex pattern: {e}"

        files = sorted(f for f in base.rglob(pattern) if f.is_file())
        if not files:
            return f"No files matching '{pattern}' found in {project_name or 'all projects'}"

        results: dict = {}
        total_matches = 0
        files_searched = 0
        truncated = False

        for file_path in files:
            if file_path.stat().st_size > 2 * 1024 * 1024:  # skip files >2MB
                continue
            try:
                content_lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue

            files_searched += 1
            file_matches = []
            for line_num, line in enumerate(content_lines, 1):
                if regex.search(line):
                    file_matches.append((line_num, line.strip()))
                    total_matches += 1
                    if total_matches >= max_matches:
                        truncated = True
                        break

            if file_matches:
                results[file_path] = file_matches
            if truncated:
                break

        scope = project_name or "all projects"
        if not results:
            return (
                f"No matches for '{query}' in {scope} "
                f"({pattern} files, {files_searched} searched)"
            )

        match_word = "match" if total_matches == 1 else "matches"
        file_word = "file" if len(results) == 1 else "files"
        lines_out = [
            f"grep '{query}' in {scope} ({pattern}) — "
            f"{total_matches} {match_word} across {len(results)} {file_word}:"
        ]
        for file_path, matches in results.items():
            rel = file_path.relative_to(projects_dir)
            lines_out.append(f"\n{rel}:")
            for line_num, line in matches:
                if len(line) > 120:
                    line = line[:120] + "..."
                lines_out.append(f"  {line_num:4d}: {line}")

        if truncated:
            lines_out.append(
                f"\n... [stopped at {max_matches} matches — "
                "narrow your search or increase max_matches]"
            )
        return "\n".join(lines_out)

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
        inspectable = ext in {'.unity', '.prefab', '.asset', '.mat'}
        readable = True
        hint = "\nTip: Use inspect_unity_file to parse GameObjects, components, or material properties." if inspectable else ""
        return (
            f"File:{file_path}\n"
            f"Size:{stat.st_size / 1024:.1f}KB\n"
            f"Type:{file_type} ({ext})\n"
            f"Modified:{mod_time}\n"
            f"Readable:{readable}"
            f"{hint}"
        )

    @mcp.tool()
    def inspect_unity_file(file_path: str, component_filter: str = "") -> str:
        """Inspect a Unity scene, prefab, ScriptableObject asset, or material file.
        Parses the YAML structure and returns a readable summary.

        Supported types:
          .unity  — Scene hierarchy with GameObjects and components
          .prefab — Prefab hierarchy with GameObjects and components
          .asset  — ScriptableObject with its serialized fields
          .mat    — Material with shader keywords, textures, floats, and colors

        Args:
            file_path: Path relative to the Unity projects directory.
                       E.g. 'MyGame/Assets/Scenes/Main.unity'
                            'MyGame/Assets/Data/EnemyStats.asset'
                            'MyGame/Assets/Materials/Player.mat'
            component_filter: (.unity/.prefab only) Show only GameObjects whose
                              component list contains this string.
                              E.g. 'Rigidbody', 'Camera', 'MonoBehaviour', 'Light'
        """
        full_path = _safe_resolve(str(projects_dir / file_path))
        if not full_path.exists():
            return f"File not found: {file_path}"
        ext = full_path.suffix.lower()
        if ext not in {'.unity', '.prefab', '.asset', '.mat'}:
            return f"Unsupported type '{ext}'. Supported: .unity, .prefab, .asset, .mat"
        size_mb = full_path.stat().st_size / (1024 * 1024)
        if size_mb > 10:
            return f"File too large ({size_mb:.1f}MB). Only files under 10MB can be inspected."
        try:
            content = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Cannot read file (encoding issue): {file_path}"
        if ext == '.mat':
            label, summary = "Material", _inspect_material_content(content)
        elif ext == '.asset':
            label, summary = "Asset", _inspect_asset_content(content)
        else:
            label = "Scene" if ext == ".unity" else "Prefab"
            summary = _inspect_unity_content(content, component_filter)
        return f"{label}: {file_path}\n{'=' * 60}\n{summary}"