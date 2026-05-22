# Pipeline MCP Server — Connection Guide

MCP server: `http://localhost:8765/mcp`
Public tunnel: `https://XXXX.trycloudflare.com/mcp` (generated each run)
Transport: Streamable HTTP (MCP spec 2025-03-26)
SDK: mcp 1.27.1

---

## One-time setup

### Install pipeline

```bash
cd pipeline
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cd ..
```

### Install cloudflared

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /tmp/cloudflared && chmod +x /tmp/cloudflared && sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
cloudflared --version
```

### Register Claude Code

```bash
claude mcp add --transport http --scope user vidpipe http://localhost:8765/mcp
```

Run once. Stored permanently in `~/.claude.json`.

---

## Every session — one command

```bash
bash pipeline/start.sh
```

What it does:
1. Kills any stuck process on port 8765
2. Starts cloudflared tunnel → waits for URL
3. Starts MCP server with OAuth enabled for that URL
4. Prints a status panel with both connection URLs
5. Ctrl+C stops everything cleanly

---

## Connect Claude.ai web

After `start.sh` prints the panel, copy the tunnel URL and open Claude.ai web:

**Settings → Integrations → Add custom integration → paste URL → Save**

The URL looks like `https://some-words.trycloudflare.com/mcp`.

Claude.ai web goes through a one-click OAuth flow (auto-approved) on first connect.
After that it stays connected until the tunnel is restarted.

> The tunnel URL changes every restart. Remove the old integration and add the new URL.

---

## Two interfaces, one server

Both connect to the same server simultaneously.

| Interface | URL | Auth | Role |
|---|---|---|---|
| Claude Code CLI | `http://localhost:8765/mcp` | None (localhost) | Code, files, debug |
| Claude.ai web | `https://XXXX.trycloudflare.com/mcp` | OAuth (auto) | Orchestration, extended tools |

---

## Available MCP tools

| Tool | Description |
|---|---|
| `pipeline_check_project` | Check if channel/scenario directories exist |
| `pipeline_create_project` | Create full directory structure |
| `pipeline_get_state` | Read current `state.json` |
| `pipeline_set_state` | Advance or reset pipeline step (Claude only) |
| `pipeline_read_file` | Read a file inside the scenario workspace |
| `pipeline_write_file` | Write a file inside the scenario workspace |
| `pipeline_list_files` | List files in a workspace directory |
| `pipeline_submit_scenario` | Accept scenario text and write `md/tts_input.json` |
| `pipeline_start_voiceover` | Start voiceover generation |
| `pipeline_get_voiceover_status` | Read scenario/voiceover status |
| `pipeline_stop_voiceover` | Request cancellation of voiceover generation |

---

## Verify connection

**Claude Code** (while server is running):
```bash
claude mcp list
# vidpipe: http://localhost:8765/mcp (HTTP) - ✓ Connected
```

**Claude.ai web** — ask Claude:
> Call `pipeline_check_project` with channel `"test"` and scenario `"demo"`

Expected:
```json
{"ok": true, "data": {"channel_exists": false, "scenario_exists": false, "workspace": null}}
```

---

## Troubleshooting

**"address already in use"** — `start.sh` kills stuck processes automatically. If it persists:
```bash
kill $(lsof -ti:8765)
```

**Tunnel URL not appearing** — cloudflared takes up to 15s on slow networks. Wait for "OK".

**Claude.ai web — "Couldn't reach the MCP server"** — tunnel URL changed. Remove the old
integration in Claude.ai web and add the new URL printed by `start.sh`.

**Claude Code shows `✗ Failed`** — server is not running. Start it with `bash pipeline/start.sh`.
