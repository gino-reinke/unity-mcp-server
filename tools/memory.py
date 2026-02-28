"""Memory persistence tools — stores project knowledge across sessions."""

import json

from storage.base import MemoryEntry


# Module-level storage reference, set during registration
_storage = None


def register(mcp, config, storage_backend):
    """Register memory tools. Receives the initialized storage backend."""
    global _storage
    _storage = storage_backend

    @mcp.tool()
    async def store_memory(
        project: str,
        title: str,
        content: str,
        category: str = "note",
        tags: str = "",
    ) -> str:
        """Store a new memory about a Unity project or general information.
        Categories: 'architecture', 'convention', 'bug', 'system', 'note'
        Tags: comma-separated strings, e.g. 'player,movement,physics'
        Use this to remember architecture decisions, naming conventions,
        known bugs, which systems have been built, and project notes.

        Project assignment rules (follow in this exact order of priority):
        1. If the user explicitly names a project in their message, use that exact project name.
        2. If the memory is clearly about a specific project based on context, use that project name.
        3. Use project="general" ONLY when the memory genuinely applies to multiple projects or
           is not tied to any single project (e.g. broad game dev goals, general Unity tips,
           cross-project conventions, personal workflow preferences).
        4. If none of the above apply and you are unsure, DO NOT guess or default to "general" —
           ask the user which project to store it under, then store it based on their answer.

        Additional rules:
        - Project names do NOT need to match folders in the Unity projects directory. A project
          name can be any label the user uses — including courses, experiments, or ideas that
          have no folder yet.
        - Before storing, use recall_memories to check if this project already exists in the
          database. If it does, use the exact same project name already stored to keep naming
          consistent. Only introduce a new project name if no close match is found."""
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        entry = MemoryEntry(
            id="",
            project=project,
            category=category,
            title=title,
            content=content,
            tags=tag_list,
        )
        entry_id = await _storage.store(entry)
        return f"Memory stored with ID:{entry_id}\nProject:{project}\nCategory:{category}\nTags:{tag_list}"

    @mcp.tool()
    async def recall_memories(
        query: str = "",
        project: str = "",
        category: str = "",
        tags: str = "",
        limit: int = 10,
    ) -> str:
        """Search stored memories by text query, project name, category, or tags.
        At least one search parameter should be provided.
        Returns matching memories sorted by most recently updated."""
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
        results = await _storage.search(
            query=query,
            project=project,
            category=category,
            tags=tag_list,
            limit=limit,
        )
        if not results:
            return "No memories found matching the search criteria."
        lines = [f"Found{len(results)} memories:", ""]
        for m in results:
            lines.append(
                f"ID:{m.id}\n"
                f"  Project:{m.project} | Category:{m.category}\n"
                f"  Title:{m.title}\n"
                f"  Tags:{', '.join(m.tags)}\n"
                f"  Updated:{m.updated_at}\n"
                f"  Content:{m.content[:200]}{'...' if len(m.content) > 200 else ''}\n"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def get_memory(memory_id: str) -> str:
        """Retrieve a specific memory by its ID. Returns the full content."""
        entry = await _storage.get(memory_id)
        if not entry:
            return f"Memory not found with ID:{memory_id}"
        return (
            f"Memory:{entry.title}\n"
            f"ID:{entry.id}\n"
            f"Project:{entry.project}\n"
            f"Category:{entry.category}\n"
            f"Tags:{', '.join(entry.tags)}\n"
            f"Created:{entry.created_at}\n"
            f"Updated:{entry.updated_at}\n"
            f"{'='*60}\n"
            f"{entry.content}"
        )

    @mcp.tool()
    async def update_memory(
        memory_id: str,
        title: str = "",
        content: str = "",
        category: str = "",
        tags: str = "",
    ) -> str:
        """Update an existing memory. Only provided fields are changed.
        Pass empty string to leave a field unchanged."""
        updates = {}
        if title:
            updates["title"] = title
        if content:
            updates["content"] = content
        if category:
            updates["category"] = category
        if tags:
            updates["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
        if not updates:
            return "No fields to update. Provide at least one of: title, content, category, tags."
        success = await _storage.update(memory_id, **updates)
        if not success:
            return f"Memory not found or update failed for ID:{memory_id}"
        return f"Memory{memory_id} updated successfully. Fields changed:{list(updates.keys())}"

    @mcp.tool()
    async def delete_memory(memory_id: str) -> str:
        """Delete a memory by its ID. This action is permanent."""
        success = await _storage.delete(memory_id)
        if success:
            return f"Memory{memory_id} deleted successfully."
        return f"Memory not found with ID:{memory_id}"

    @mcp.tool()
    async def list_project_memories(project: str) -> str:
        """List all stored memories for a specific Unity project.
        Great for getting an overview of what's been recorded about a project."""
        results = await _storage.list_by_project(project)
        if not results:
            return f"No memories stored for project:{project}"
        lines = [f"All memories for project '{project}' ({len(results)} total):", ""]
        by_category = {}
        for m in results:
            by_category.setdefault(m.category, []).append(m)
        for cat, entries in sorted(by_category.items()):
            lines.append(f"\n[{cat.upper()}] ({len(entries)} entries)")
            for m in entries:
                tag_str = f" [{', '.join(m.tags)}]" if m.tags else ""
                lines.append(f"  -{m.title}{tag_str}  (ID:{m.id[:8]}...)")
        return "\n".join(lines)