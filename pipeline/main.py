import anyio
import uvicorn
import typer
import yaml
from pathlib import Path
from rich.console import Console
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

app = typer.Typer(
    name="vidpipe",
    help="Video production pipeline — MCP server for Claude.ai",
    no_args_is_help=True,
)
console = Console()

_OAUTH_WELL_KNOWN = frozenset([
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-authorization-server",
])


class _LocalNoOAuthMiddleware(BaseHTTPMiddleware):
    """Return 404 for OAuth discovery endpoints on localhost connections.

    Claude Code CLI connects from 127.0.0.1 and must NOT see OAuth metadata —
    otherwise it tries to run the browser OAuth flow and fails.
    Cloudflare tunnel requests are proxied from 127.0.0.1 too, but keep the
    public trycloudflare Host header, so they still receive OAuth metadata.
    """

    async def dispatch(self, request: Request, call_next):
        client_host = request.client.host if request.client else ""
        request_host = request.url.hostname or ""
        is_direct_localhost = (
            client_host in ("127.0.0.1", "::1")
            and request_host in ("localhost", "127.0.0.1", "::1", "[::1]")
        )
        is_oauth_discovery = (
            request.url.path in _OAUTH_WELL_KNOWN
            or request.url.path.startswith("/.well-known/oauth-protected-resource/")
        )
        if is_direct_localhost and is_oauth_discovery:
            return Response(status_code=404)
        return await call_next(request)


def _load_config() -> dict:
    cfg_path = Path(__file__).parent / "config" / "pipeline.yaml"
    return yaml.safe_load(cfg_path.read_text())


@app.command()
def start():
    """Start the MCP server. Keep it running while using Claude.ai or Claude Code."""
    from src.mcp.server import mcp

    cfg = _load_config()

    async def _run():
        starlette_app = mcp.streamable_http_app()
        starlette_app = _LocalNoOAuthMiddleware(starlette_app)
        cors_app = CORSMiddleware(
            app=starlette_app,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        config = uvicorn.Config(
            cors_app,
            host=cfg["server"]["host"],
            port=cfg["server"]["port"],
            log_level="info",
        )
        await uvicorn.Server(config).serve()

    anyio.run(_run)


@app.command()
def info():
    """Show server configuration and connection URLs."""
    cfg = _load_config()
    _host = cfg["server"]["host"]
    _port = cfg["server"]["port"]
    _path = cfg["server"]["path"]
    url = f"http://localhost:{_port}{_path}"

    console.print(f"[bold]Server name:[/bold]  {cfg['server']['name']}")
    console.print(f"[bold]URL:[/bold]           {url}")
    console.print(f"[bold]Projects dir:[/bold]  {cfg['projects']['base_dir']}")


if __name__ == "__main__":
    app()
