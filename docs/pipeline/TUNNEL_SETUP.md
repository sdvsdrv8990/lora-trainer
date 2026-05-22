# Stable Tunnel Setup — One-Time Configuration for Claude.ai

## The Problem

By default `start.sh` uses a temporary Cloudflare tunnel (`trycloudflare.com`).
The URL changes every restart → the Claude.ai integration becomes invalid → you have
to remove it and add it again with the new URL.

## The Fix

A **named Cloudflare Tunnel** routes your traffic through a fixed subdomain on your
own domain. The URL never changes. You configure Claude.ai once and never touch it
again — new MCP tools appear automatically on the next conversation.

```
bash start.sh        →  https://abc123-random.trycloudflare.com/mcp  ← changes every restart
bash start.sh (named) →  https://pipeline.yourdomain.com/mcp          ← permanent
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| A domain | Any registrar. ~$10/year. Can be a cheap `.xyz` or `.dev`. |
| Domain on Cloudflare DNS | Free. Move nameservers to Cloudflare in your registrar. |
| `cloudflared` installed | Already required by `start.sh`. |

---

## One-Time Setup (do this once)

### Step 1 — Authenticate cloudflared with your Cloudflare account

```bash
cloudflared tunnel login
```

A browser window opens. Select your domain and authorize. A credentials file is saved
to `~/.cloudflared/`.

### Step 2 — Create a named tunnel

```bash
cloudflared tunnel create vidpipe
```

Output shows a tunnel UUID like `a1b2c3d4-...`. Cloudflared saves credentials at
`~/.cloudflared/<uuid>.json`.

### Step 3 — Route a DNS subdomain to the tunnel

```bash
cloudflared tunnel route dns vidpipe pipeline.yourdomain.com
```

This creates a CNAME record `pipeline.yourdomain.com → <uuid>.cfargotunnel.com` in
Cloudflare DNS. You can verify it in the Cloudflare dashboard under DNS.

Replace `pipeline.yourdomain.com` with any subdomain you want.

### Step 4 — Configure start.sh

Copy `.env.example` to `.env` in the `pipeline/` directory:

```bash
cp pipeline/.env.example pipeline/.env
```

Edit `pipeline/.env` and uncomment + fill in:

```bash
CLOUDFLARE_TUNNEL_NAME=vidpipe
CLOUDFLARE_TUNNEL_HOSTNAME=pipeline.yourdomain.com
```

### Step 5 — Start for the first time with the stable URL

```bash
bash pipeline/start.sh
```

The output now shows:

```
┌──────────────────────────────────────────────────────────────┐
│  vidpipe MCP server                                          │
│                                                              │
│  Claude Code    http://localhost:8765/mcp                    │
│  Claude.ai web  https://pipeline.yourdomain.com/mcp          │
│                                                              │
│  Tunnel: STABLE (named: vidpipe)                             │
│                                                              │
│  Claude.ai web setup:                                        │
│  Settings -> Integrations -> Add custom integration          │
│  URL: https://pipeline.yourdomain.com/mcp                    │
│                                                              │
│  Ctrl+C to stop                                              │
└──────────────────────────────────────────────────────────────┘
```

### Step 6 — Add to Claude.ai (last time you'll ever do this)

In Claude.ai web:
`Settings → Integrations → Add custom integration`

Paste `https://pipeline.yourdomain.com/mcp`.

That's it. From now on, every restart of `start.sh` connects to the same URL.
New tools are picked up automatically at the start of each conversation.

---

## What Happens When You Add New Tools

1. Add tools to `server.py`
2. `Ctrl+C` and `bash pipeline/start.sh`
3. Open a **new conversation** in Claude.ai

Claude.ai runs `initialize → tools/list` at the start of each conversation.
It always sees the current tool set from the live server.
No removal, no re-addition, no URL to copy.

---

## Troubleshooting

**Tunnel fails to start with "failed to sufficiently increase receive buffer size"**

```bash
sudo sysctl -w net.core.rmem_max=7500000
```

**`cloudflared tunnel run` errors with "failed to connect to Cloudflare edge"**

Check your internet connection and that the credentials file exists:
```bash
ls ~/.cloudflared/*.json
```

**Tunnel starts but Claude.ai says "could not reach integration"**

1. Verify DNS propagated: `dig pipeline.yourdomain.com`
   Should show a CNAME ending in `.cfargotunnel.com`.
2. Wait 1–2 minutes for DNS to propagate globally.
3. Check that `pipeline.yourdomain.com` is proxied (orange cloud) in Cloudflare DNS.

**Named tunnel connects but OAuth discovery fails**

The server needs `VIDPIPE_PUBLIC_URL` to be exactly `https://pipeline.yourdomain.com`
(no trailing slash). `start.sh` sets this from `CLOUDFLARE_TUNNEL_HOSTNAME` automatically.
Check that `.env` has no extra spaces or quotes around the value.

---

## Notes

- The `.env` file is gitignored. Never commit it — it contains nothing secret (tunnel
  name and hostname are not credentials), but it's machine-specific.
- You can have multiple tunnels for multiple environments (dev/staging/prod) by using
  different tunnel names and hostnames.
- The tunnel credentials (`~/.cloudflared/<uuid>.json`) are secret. Do not share them.
- Cloudflare named tunnels are free on all Cloudflare plans.
