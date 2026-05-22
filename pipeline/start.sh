#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SERVER_LOG=$(mktemp)
TUNNEL_LOG=$(mktemp)
TAIL_PID=""
cleanup() {
    echo ""
    echo "Stopping..."
    kill "$SERVER_PID" "$TUNNEL_PID" "${TAIL_PID:-}" 2>/dev/null || true
    rm -f "$SERVER_LOG" "$TUNNEL_LOG"
    exit 0
}
trap cleanup INT TERM

# ── Load .env (if present) ─────────────────────────────────────────────────────
# Create .env from .env.example and fill in CLOUDFLARE_TUNNEL_NAME +
# CLOUDFLARE_TUNNEL_HOSTNAME to get a stable URL that never requires
# re-adding the integration in Claude.ai.

if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

# ── Preflight ──────────────────────────────────────────────────────────────────

if [[ ! -f venv/bin/activate ]]; then
    echo "ERROR: venv not found."
    echo "  cd pipeline && python3 -m venv venv && source venv/bin/activate && pip install -e '.[dev]'"
    exit 1
fi

if ! command -v cloudflared &>/dev/null; then
    echo "ERROR: cloudflared not installed."
    echo "  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared"
    echo "  chmod +x /tmp/cloudflared && sudo mv /tmp/cloudflared /usr/local/bin/cloudflared"
    exit 1
fi

# ── Kill stuck server ──────────────────────────────────────────────────────────

if lsof -ti:8765 &>/dev/null; then
    kill "$(lsof -ti:8765)" 2>/dev/null || true
    sleep 1
fi

# ── Determine tunnel mode ─────────────────────────────────────────────────────
# Named tunnel (stable URL):   set CLOUDFLARE_TUNNEL_NAME + CLOUDFLARE_TUNNEL_HOSTNAME
# Ephemeral tunnel (random URL): leave both unset

TUNNEL_MODE="ephemeral"
if [[ -n "$CLOUDFLARE_TUNNEL_NAME" && -n "$CLOUDFLARE_TUNNEL_HOSTNAME" ]]; then
    TUNNEL_MODE="named"
fi

# ── Start tunnel ───────────────────────────────────────────────────────────────

if [[ "$TUNNEL_MODE" == "named" ]]; then
    # ── Named tunnel: stable URL, no re-configuration in Claude.ai ever ─────────
    PUBLIC_URL="https://$CLOUDFLARE_TUNNEL_HOSTNAME"
    printf "Starting named tunnel (%s)..." "$CLOUDFLARE_TUNNEL_HOSTNAME"

    cloudflared tunnel --no-autoupdate run \
        --url http://localhost:8765 \
        "$CLOUDFLARE_TUNNEL_NAME" >"$TUNNEL_LOG" 2>&1 &
    TUNNEL_PID=$!

    # Wait for cloudflared to register at least one connection to Cloudflare edge
    TUNNEL_READY=0
    for i in $(seq 1 30); do
        if grep -qE 'Registered tunnel connection|Connection registered|connection established' \
                "$TUNNEL_LOG" 2>/dev/null; then
            TUNNEL_READY=1
            break
        fi
        if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
            break
        fi
        printf "."
        sleep 0.5
    done

    if [[ "$TUNNEL_READY" -ne 1 ]]; then
        echo " FAILED"
        cat "$TUNNEL_LOG"
        kill "$TUNNEL_PID" 2>/dev/null || true
        rm -f "$SERVER_LOG" "$TUNNEL_LOG"
        exit 1
    fi
    echo " OK"

else
    # ── Ephemeral tunnel: random URL, must re-add in Claude.ai after each restart ─
    printf "Starting ephemeral tunnel..."

    cloudflared tunnel --url http://localhost:8765 --no-autoupdate >"$TUNNEL_LOG" 2>&1 &
    TUNNEL_PID=$!

    PUBLIC_URL=""
    for i in $(seq 1 30); do
        PUBLIC_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" 2>/dev/null | head -1)
        [[ -n "$PUBLIC_URL" ]] && break
        printf "."
        sleep 0.5
    done

    if [[ -z "$PUBLIC_URL" ]]; then
        echo " FAILED"
        cat "$TUNNEL_LOG"
        kill "$TUNNEL_PID" 2>/dev/null
        rm -f "$SERVER_LOG" "$TUNNEL_LOG"
        exit 1
    fi
    echo " OK"
fi

# ── Start server ───────────────────────────────────────────────────────────────

printf "Starting server..."
source venv/bin/activate
export VIDPIPE_PUBLIC_URL="$PUBLIC_URL"
PYTHONUNBUFFERED=1 python main.py start >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

HEALTH_PAYLOAD='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"vidpipe-start-healthcheck","version":"0.1.0"}}}'
SERVER_READY=0
for i in $(seq 1 20); do
    if curl -sf http://localhost:8765/mcp \
        -X POST \
        -H "Accept: application/json, text/event-stream" \
        -H "Content-Type: application/json" \
        --data "$HEALTH_PAYLOAD" \
        -o /dev/null --max-time 1 2>/dev/null; then
        SERVER_READY=1
        break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        break
    fi
    printf "."
    sleep 0.5
done

if [[ "$SERVER_READY" -ne 1 ]]; then
    echo " FAILED"
    cat "$SERVER_LOG"
    kill "$SERVER_PID" "$TUNNEL_PID" 2>/dev/null || true
    rm -f "$SERVER_LOG" "$TUNNEL_LOG"
    exit 1
fi
echo " OK"

# ── Print status ───────────────────────────────────────────────────────────────

MCP_URL="${PUBLIC_URL}/mcp"
CONTENT_WIDTH=61
if [[ "$TUNNEL_MODE" == "named" ]]; then
    MODE_LINE="Tunnel: STABLE (named: $CLOUDFLARE_TUNNEL_NAME)"
else
    MODE_LINE="Tunnel: EPHEMERAL — URL changes on restart"
fi
WEB_LINE="Claude.ai web  $MCP_URL"
URL_LINE="URL: $MCP_URL"
for line in "$WEB_LINE" "$URL_LINE" "$MODE_LINE"; do
    if (( ${#line} + 2 > CONTENT_WIDTH )); then
        CONTENT_WIDTH=$((${#line} + 2))
    fi
done

print_border() {
    local left="$1"
    local fill="$2"
    local right="$3"
    printf "%s" "$left"
    for _ in $(seq 1 "$CONTENT_WIDTH"); do
        printf "%s" "$fill"
    done
    printf "%s\n" "$right"
}

print_line() {
    printf "│  %-*s│\n" "$((CONTENT_WIDTH - 2))" "$1"
}

echo ""
print_border "┌" "─" "┐"
print_line "vidpipe MCP server"
print_line ""
print_line "Claude Code    http://localhost:8765/mcp"
print_line "$WEB_LINE"
print_line ""
print_line "$MODE_LINE"
if [[ "$TUNNEL_MODE" == "ephemeral" ]]; then
    print_line "  -> See docs/pipeline/TUNNEL_SETUP.md for stable URL"
fi
print_line ""
print_line "Claude.ai web setup:"
print_line "Settings -> Integrations -> Add custom integration"
print_line "$URL_LINE"
print_line ""
print_line "Ctrl+C to stop"
print_border "└" "─" "┘"
echo ""

# ── Stream server logs ─────────────────────────────────────────────────────────

echo "── server log ──────────────────────────────────────────────────────"
tail -f "$SERVER_LOG" &
TAIL_PID=$!

# ── Wait ───────────────────────────────────────────────────────────────────────

wait "$SERVER_PID"
cleanup
