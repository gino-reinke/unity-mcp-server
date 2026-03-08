"""Unity Game Development MCP Server - main entry point (simplified)."""

import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

from config import Config
from storage.sqlite_store import SQLiteStorage
from tools import filesystem, git_tools, llm_tools, memory, search, tutor, unity_log

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
unity_log.register(mcp, config)
llm_tools.register(mcp, config)

logger.info(
    f"Unity MCP Server ready - "
    f"projects dir: {config.unity_projects_dir} "
    f"(source: {config.unity_projects_dir_source}, "
    f"exists: {config.unity_projects_dir.exists()})"
)

if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser(description="Unity MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Transport to use. 'stdio' for Claude/ChatGPT Desktop, 'streamable-http' for Claude Web (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind when using HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind when using HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--public-url",
        default=None,
        help=(
            "Public base URL for OAuth issuer (e.g. https://abc123.ngrok-free.app). "
            "Falls back to PUBLIC_URL env var, then http://{host}:{port}."
        ),
    )
    args = parser.parse_args()

    if args.transport in ("streamable-http", "sse"):
        from mcp.server.auth.provider import ProviderTokenVerifier
        from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
        from mcp.server.transport_security import TransportSecuritySettings

        from auth_provider import SimpleOAuthProvider

        public_url = (
            args.public_url
            or os.environ.get("PUBLIC_URL", "").strip()
            or f"http://{args.host}:{args.port}"
        )

        provider = SimpleOAuthProvider()
        auth_settings = AuthSettings(
            issuer_url=public_url,
            resource_server_url=public_url,
            client_registration_options=ClientRegistrationOptions(enabled=True),
        )

        # Mutate the module-level mcp object (tools already registered) before
        # streamable_http_app() is called — that method reads these lazily.
        mcp._auth_server_provider = provider
        mcp._token_verifier = ProviderTokenVerifier(provider)
        mcp.settings.auth = auth_settings
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )

        logger.info(f"Starting HTTP server on {args.host}:{args.port} ({args.transport}) — OAuth enabled")
        logger.info(f"OAuth issuer: {public_url}")

        import uvicorn

        uvicorn.run(mcp.streamable_http_app(), host=args.host, port=args.port, log_level="info")
    else:
        mcp.run(transport=args.transport)
