"""Abstract storage interface for the memory system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MemoryEntry:
    """A single memory record."""

    id: str
    project: str
    category: str  # e.g., "architecture", "bug", "convention", "note"
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class StorageBackend(ABC):
    """Abstract interface — implement this for each backend."""

    @abstractmethod
    async def initialize(self) -> None:
        """Create tables/collections. Called once at startup."""
        ...

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        """Store or upsert a memory entry. Returns the entry ID."""
        ...

    @abstractmethod
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a single memory by ID."""
        ...

    @abstractmethod
    async def update(self, entry_id: str, **fields) -> bool:
        """Update specific fields of a memory. Returns success."""
        ...

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory by ID. Returns success."""
        ...

    @abstractmethod
    async def search(
        self,
        query: str = "",
        project: str = "",
        category: str = "",
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Search memories by text, project, category, or tags."""
        ...

    @abstractmethod
    async def list_by_project(self, project: str) -> list[MemoryEntry]:
        """List all memories for a specific project."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up connections."""
        ...