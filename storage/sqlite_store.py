"""SQLite implementation of the storage backend."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from .base import MemoryEntry, StorageBackend


class SQLiteStorage(StorageBackend):
    """SQLite-backed memory storage."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'note',
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_project
            ON memories(project)
        """)
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_category
            ON memories(category)
        """)
        await self.db.commit()

    async def store(self, entry: MemoryEntry) -> str:
        if not entry.id:
            entry.id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        entry.created_at = now
        entry.updated_at = now
        await self.db.execute(
            """INSERT OR REPLACE INTO memories
               (id, project, category, title, content, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.id,
                entry.project,
                entry.category,
                entry.title,
                entry.content,
                json.dumps(entry.tags),
                entry.created_at,
                entry.updated_at,
            ),
        )
        await self.db.commit()
        return entry.id

    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        cursor = await self.db.execute(
            "SELECT * FROM memories WHERE id = ?", (entry_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_entry(row)

    async def update(self, entry_id: str, **fields) -> bool:
        existing = await self.get(entry_id)
        if not existing:
            return False
        allowed = {"project", "category", "title", "content", "tags"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return False
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [entry_id]
        await self.db.execute(
            f"UPDATE memories SET{set_clause} WHERE id = ?", values
        )
        await self.db.commit()
        return True

    async def delete(self, entry_id: str) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM memories WHERE id = ?", (entry_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def search(
        self,
        query: str = "",
        project: str = "",
        category: str = "",
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        conditions = []
        params = []
        if query:
            conditions.append(
                "(title LIKE ? OR content LIKE ?)"
            )
            params.extend([f"%{query}%", f"%{query}%"])
        if project:
            conditions.append("project = ?")
            params.append(project)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        cursor = await self.db.execute(
            f"SELECT * FROM memories WHERE{where} ORDER BY updated_at DESC LIMIT ?",
            params,
        )
        rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]

    async def list_by_project(self, project: str) -> list[MemoryEntry]:
        return await self.search(project=project, limit=100)

    async def close(self) -> None:
        if self.db:
            await self.db.close()

    @staticmethod
    def _row_to_entry(row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            project=row["project"],
            category=row["category"],
            title=row["title"],
            content=row["content"],
            tags=json.loads(row["tags"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )