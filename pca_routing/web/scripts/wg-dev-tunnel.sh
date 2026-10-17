#!/usr/bin/env bash
# Temporarily exposes the Vite dev server (npm run dev, localhost:5173) to
# everyone on the WireGuard tunnel, for demoing the React PoC without a
# build/deploy step. Opens a scoped ufw rule on wg0 and socat-forwards the
# tunnel IP to the dev server's loopback port; 'down' removes both. Not a
# standing service - the dev server itself must already be running
# (npm run dev) before calling 'up'.
#
# Usage:
#   npm run dev &            # start the dev server first
#   sudo scripts/wg-dev-tunnel.sh up
#   sudo scripts/wg-dev-tunnel.sh down
set -euo pipefail

WG_IP="${WG_IP:-10.8.0.8}"
DEV_PORT="${DEV_PORT:-5173}"
PID_FILE="${PID_FILE:-/tmp/wg-dev-tunnel.pid}"

usage() { echo "usage: $0 {up|down}" >&2; exit 1; }
require_root() { [[ $EUID -eq 0 ]] || { echo "must run as root (sudo)" >&2; exit 1; }; }

up() {
  require_root
  ufw allow in on wg0 to any port "$DEV_PORT" proto tcp comment "React PoC dev server - temp tunnel access"
  socat TCP-LISTEN:"$DEV_PORT",bind="$WG_IP",fork,reuseaddr TCP:127.0.0.1:"$DEV_PORT" &
  echo "$!" > "$PID_FILE"
  echo "up: forwarding $WG_IP:$DEV_PORT to 127.0.0.1:$DEV_PORT (pid in $PID_FILE)"
}

down() {
  require_root
  if [[ -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
  ufw delete allow in on wg0 to any port "$DEV_PORT" proto tcp 2>/dev/null || true
  echo "down: tunnel forwarding and ufw rule removed"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *) usage ;;
esac
