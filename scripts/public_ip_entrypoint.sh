#!/bin/bash
# Simple entrypoint that disables PUBLIC_IP detection in upstream cs2-modded-server
# The IP detector sidecar handles detection independently, bot reads from cache
set -euo pipefail

echo "[cs2-entrypoint] Disabling PUBLIC_IP auto-detection (PUBLIC_IP_FETCH=0)"
echo "[cs2-entrypoint] Server will start without IP validation"

# Disable IP detection in upstream install_docker.sh
export PUBLIC_IP_FETCH=0

# Allow the script to default to the image CMD if compose does not pass args
if [[ $# -eq 0 ]]; then
    set -- sudo -E bash /home/cs2-modded-server/install_docker.sh
fi

exec "$@"
