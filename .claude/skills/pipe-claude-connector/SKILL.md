---
name: pipe-claude-connector
description: Load when debugging or changing the Claude.ai web custom integration, Cloudflare tunnel, OAuth discovery, MCP Streamable HTTP startup, or remote connector tool discovery.
---

# pipe-claude-connector

## What This Skill Protects

This project has two clients for the same MCP server:

- Claude Code: direct local `http://localhost:8765/mcp`, no OAuth.
- Claude.ai web: public `https://<trycloudflare-host>/mcp`, OAuth discovery enabled.

The public connector can fail before any tool runs. Treat connector work as protocol
work, not as ordinary app debugging.

## Known-Good Startup

Run from the repository root:

```bash
bash pipeline/start.sh
```

The script must:

1. Start `cloudflared`.
2. Export `VIDPIPE_PUBLIC_URL=https://<trycloudflare-host>`.
3. Start `python main.py start`.
4. Health-check with JSON-RPC `initialize` sent by `POST /mcp`.
5. Print the public URL ending in `/mcp`.

Do not replace the health-check with `GET /mcp`. In stateful Streamable HTTP,
that can validly return:

```text
400 Bad Request: Missing session ID
```

## Required Public Discovery Endpoints

For Claude.ai web URL:

```text
https://<host>/mcp
```

these must be reachable through the tunnel:

```text
https://<host>/.well-known/oauth-protected-resource/mcp
https://<host>/.well-known/oauth-authorization-server
```

The protected resource metadata must contain:

```json
{"resource": "https://<host>/mcp"}
```

The authorization metadata must contain:

- `authorization_endpoint`
- `token_endpoint`
- `registration_endpoint`
- `code_challenge_methods_supported` including `S256`

## Host Handling Rule

`cloudflared` proxies public requests into uvicorn from loopback, so
`request.client.host` can be `127.0.0.1` for both direct local and public tunnel
traffic.

Distinguish clients by Host:

- Direct local Host (`localhost`, `127.0.0.1`, `::1`) should hide OAuth discovery.
- Public tunnel Host (`*.trycloudflare.com`) should expose OAuth discovery.

Never hide OAuth metadata based only on `request.client.host == "127.0.0.1"`.

## Server Configuration Rule

When `VIDPIPE_PUBLIC_URL` is set:

- `issuer_url` is the tunnel origin, for example `https://abc.trycloudflare.com`.
- `resource_server_url` is the full MCP endpoint, for example `https://abc.trycloudflare.com/mcp`.

Do not set `resource_server_url` to only the origin. That publishes protected
resource metadata at the wrong path and Claude.ai may report:

```text
Couldn't reach the MCP server
```

## Tool Discovery Rule

`This connector has no tools available` means Claude.ai connected far enough to
create the connector, but did not accept or receive the tool list.

Debug in this order:

1. Check server log for `Processing request of type ListToolsRequest`.
2. Run the official MCP Python SDK `initialize -> tools/list`.
3. If SDK sees tools but Claude.ai does not, simplify tool schemas and re-add the connector.
4. Do not debug this from a bare `GET /mcp`.

Current expected tool count: `12`.

## Claude.ai-Friendly Schemas

Hosted Claude may be stricter than the local SDK. Keep schemas conservative:

- descriptions on every argument
- string arguments where practical
- simple object schemas with required fields
- no arbitrary absolute filesystem paths
- no unserializable return values

`pipeline_set_state.step` is intentionally exposed as a numeric string and parsed
inside the tool.

## Verification Checklist

Before calling connector work complete:

- [ ] `bash -n pipeline/start.sh`
- [ ] `python -m py_compile main.py src/mcp/server.py` from `pipeline/`
- [ ] `/.well-known/oauth-protected-resource/mcp` returns `200` for public Host
- [ ] `/.well-known/oauth-authorization-server` returns `200` for public Host
- [ ] direct localhost OAuth discovery returns `404`
- [ ] SDK `initialize -> tools/list` returns count `12`
- [ ] Claude.ai custom integration was removed and re-added after auth/schema changes
