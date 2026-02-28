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
    import hmac
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
    args = parser.parse_args()

    if args.transport in ("streamable-http", "sse"):
        secret = os.environ.get("MCP_SECRET", "").strip()

        if not secret:
            logger.warning(
                "MCP_SECRET is not set — the HTTP server is unauthenticated. "
                "Set MCP_SECRET=<strong-random-token> before exposing publicly."
            )

        # Build the Starlette app manually so we can wrap it with auth middleware.
        os.environ.setdefault("FASTMCP_HOST", args.host)
        os.environ.setdefault("FASTMCP_PORT", str(args.port))

        base_app = mcp.streamable_http_app()

        if secret:
            from starlette.types import ASGIApp, Receive, Scope, Send

            class _BearerAuthMiddleware:
                """Lightweight ASGI middleware that enforces a shared Bearer token.

                Using a raw ASGI middleware (not BaseHTTPMiddleware) avoids
                buffering issues with streaming / SSE responses.
                """

                def __init__(self, app: ASGIApp, token: str) -> None:
                    self._app = app
                    self._token = token

                async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
                    if scope["type"] == "http":
                        headers = {k.lower(): v for k, v in scope.get("headers", [])}
                        auth = headers.get(b"authorization", b"").decode()
                        provided = auth[7:] if auth.startswith("Bearer ") else ""
                        if not hmac.compare_digest(provided, self._token):
                            body = b'{"error":"Unauthorized"}'
                            await send(
                                {
                                    "type": "http.response.start",
                                    "status": 401,
                                    "headers": [
                                        (b"content-type", b"application/json"),
                                        (b"content-length", str(len(body)).encode()),
                                        (b"www-authenticate", b"Bearer"),
                                    ],
                                }
                            )
                            await send({"type": "http.response.body", "body": body})
                            return
                    await self._app(scope, receive, send)

            asgi_app = _BearerAuthMiddleware(base_app, secret)
            logger.info(f"Starting HTTP server on {args.host}:{args.port} ({args.transport}) — bearer auth enabled")
        else:
            asgi_app = base_app
            logger.info(f"Starting HTTP server on {args.host}:{args.port} ({args.transport}) — no auth")

        import uvicorn

        uvicorn.run(asgi_app, host=args.host, port=args.port, log_level="info")
    else:
        mcp.run(transport=args.transport)
