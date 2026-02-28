"""Storage factory."""

from .base import StorageBackend


def create_storage(backend: str = "sqlite", **kwargs) -> StorageBackend:
    if backend == "sqlite":
        from .sqlite_store import SQLiteStorage
        return SQLiteStorage(kwargs.get("db_path", "data/memory.db"))
    elif backend == "chroma":
        # Future: from .chroma_store import ChromaStorage
        raise NotImplementedError("ChromaDB backend not yet implemented")
    raise ValueError(f"Unknown storage backend:{backend}")