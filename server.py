"""Unity Game Development MCP Server - main entry point (simplified)."""

import asyncio
import logging
import sys

from mcp.server.fastmcp import FastMCP

from config import Config
from storage.sqlite_store import SQLiteStorage
from tools import filesystem, git_tools, memory, search, tutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]%(name)s:%(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("unity-mcp")

config = Config()
messages = config.validate()
for level, message in messages:
    getattr(logger, level)(message)

# Initialize storage synchronously for tool registration
storage = SQLiteStorage(str(config.db_path))
asyncio.run(storage.initialize())
logger.info(f"Storage initialized at {config.db_path}")

# Create the MCP server
mcp = FastMCP("Unity Game Dev Agent")

# Register all tool modules
filesystem.register(mcp, config)
git_tools.register(mcp, config)
search.register(mcp, config)
memory.register(mcp, config, storage)
tutor.register(mcp, config)

logger.info(
    f"Unity MCP Server ready - "
    f"projects dir: {config.unity_projects_dir} "
    f"(source: {config.unity_projects_dir_source}, "
    f"exists: {config.unity_projects_dir.exists()})"
)

if __name__ == "__main__":
    mcp.run(transport="stdio")
