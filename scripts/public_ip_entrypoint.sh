#!/bin/bash
# Reads cached PUBLIC_IP before upstream install_docker.sh runs
# If cache unavailable, uses fallback value to prevent server restart loop
set -euo pipefail

PUBLIC_IP_FILE="${PUBLIC_IP_FILE:-/shared/public_ip.txt}"

echo "[cs2-entrypoint] Reading cached IP from ${PUBLIC_IP_FILE}"

# Try to read cached IP
if [[ -f "$PUBLIC_IP_FILE" ]]; then
    CACHED_IP="$(head -n1 "$PUBLIC_IP_FILE" 2>/dev/null | tr -d '\r\n ')"
    if [[ "$CACHED_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        export PUBLIC_IP="$CACHED_IP"
        echo "[cs2-entrypoint] Using cached PUBLIC_IP=${PUBLIC_IP}"
    fi
fi

# Fallback if no cache: use dummy IP to prevent loop
if [[ -z "${PUBLIC_IP:-}" ]]; then
    export PUBLIC_IP="0.0.0.0"
    echo "[cs2-entrypoint] WARNING: No cached IP found, using fallback PUBLIC_IP=${PUBLIC_IP}"
    echo "[cs2-entrypoint] Server will start but may show incorrect IP in logs"
fi

# Allow the script to default to the image CMD if compose does not pass args
if [[ $# -eq 0 ]]; then
    set -- sudo -E bash /home/cs2-modded-server/install_docker.sh
fi

exec "$@"
