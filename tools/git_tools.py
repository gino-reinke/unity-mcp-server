"""Git read-only tools for Unity project repositories."""

import os
from pathlib import Path

from git import Repo, InvalidGitRepositoryError, GitCommandNotFound


def register(mcp, config):
    """Register read-only git tools onto the MCP server."""
    projects_dir = config.unity_projects_dir

    def _get_repo(project_name: str) -> Repo:
        """Get a git Repo object for a Unity project."""
        project_path = (projects_dir / project_name).resolve()
        if not str(project_path).startswith(str(projects_dir)):
            raise ValueError("Access denied: path outside Unity projects directory")
        if not project_path.exists():
            raise FileNotFoundError(f"Project not found:{project_name}")
        try:
            return Repo(project_path)
        except InvalidGitRepositoryError:
            raise ValueError(f"Not a git repository:{project_name}")

    @mcp.tool()
    def detect_git_repos() -> str:
        """Scan the Unity Projects folder and list which projects
        are git repositories, along with their current branch."""
        if not projects_dir.exists():
            return f"Unity projects directory not found:{projects_dir}"
        results = []
        for item in sorted(projects_dir.iterdir()):
            if item.is_dir() and (item / ".git").exists():
                try:
                    repo = Repo(item)
                    branch = repo.active_branch.name if not repo.head.is_detached else "DETACHED"
                    dirty = " (uncommitted changes)" if repo.is_dirty() else ""
                    results.append(f"{item.name} [{branch}]{dirty}")
                except Exception as e:
                    results.append(f"{item.name} [error:{e}]")
        if not results:
            return "No git repositories found in Unity projects folder."
        return "Git-enabled Unity projects:\n" + "\n".join(results)

    @mcp.tool()
    def git_status(project_name: str) -> str:
        """Get the full git status for a Unity project repository.
        Shows staged, unstaged, and untracked files."""
        repo = _get_repo(project_name)
        lines = [f"Git Status for{project_name}:"]
        lines.append(f"Branch:{repo.active_branch.name if not repo.head.is_detached else 'DETACHED HEAD'}")
        lines.append(f"Clean:{not repo.is_dirty()}")
        lines.append("")
        # Staged changes
        staged = repo.index.diff("HEAD")
        if staged:
            lines.append("Staged changes:")
            for diff in staged:
                lines.append(f"{diff.change_type}:{diff.a_path}")
        # Unstaged changes
        unstaged = repo.index.diff(None)
        if unstaged:
            lines.append("Unstaged changes:")
            for diff in unstaged:
                lines.append(f"{diff.change_type}:{diff.a_path}")
        # Untracked
        untracked = repo.untracked_files
        if untracked:
            lines.append(f"Untracked files ({len(untracked)}):")
            for f in untracked[:30]:
                lines.append(f"{f}")
            if len(untracked) > 30:
                lines.append(f"  ... and{len(untracked) - 30} more")
        if not staged and not unstaged and not untracked:
            lines.append("Working tree clean.")
        return "\n".join(lines)

    @mcp.tool()
    def git_log(project_name: str, max_count: int = 15) -> str:
        """Show recent git commit history for a Unity project.
        Returns commit hash, author, date, and message."""
        repo = _get_repo(project_name)
        lines = [f"Git Log for{project_name} (last{max_count} commits):", ""]
        for commit in repo.iter_commits(max_count=max_count):
            short_hash = commit.hexsha[:8]
            date = commit.committed_datetime.strftime("%Y-%m-%d %H:%M")
            msg = commit.message.strip().split("\n")[0][:80]
            lines.append(f"{short_hash} |{date} |{commit.author.name} |{msg}")
        return "\n".join(lines)

    @mcp.tool()
    def git_diff(project_name: str, target: str = "") -> str:
        """Show git diff for a Unity project.
        If target is empty, shows unstaged changes.
        If target is a branch or commit hash, shows diff against it."""
        repo = _get_repo(project_name)
        try:
            if target:
                diff_text = repo.git.diff(target, "--stat")
                full_diff = repo.git.diff(target)
            else:
                diff_text = repo.git.diff("--stat")
                full_diff = repo.git.diff()
        except Exception as e:
            return f"Git diff error:{e}"
        if not full_diff.strip():
            return f"No differences found{' against ' + target if target else ' (unstaged)'}."
        # Truncate very large diffs
        if len(full_diff) > 15000:
            full_diff = full_diff[:15000] + "\n\n... [truncated — diff too large]"
        return f"Git Diff for{project_name}:\n\nSummary:\n{diff_text}\n\nFull diff:\n{full_diff}"

    @mcp.tool()
    def git_branch_list(project_name: str) -> str:
        """List all local and remote branches for a Unity project."""
        repo = _get_repo(project_name)
        lines = [f"Branches for{project_name}:", ""]
        current = repo.active_branch.name if not repo.head.is_detached else None
        lines.append("Local branches:")
        for branch in repo.branches:
            marker = " *" if branch.name == current else "  "
            lines.append(f"{marker}{branch.name}")
        if repo.remotes:
            lines.append("\nRemote branches:")
            for remote in repo.remotes:
                for ref in remote.refs:
                    lines.append(f"{ref.name}")
        return "\n".join(lines)