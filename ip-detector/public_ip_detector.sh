#!/bin/bash
set -euo pipefail

log() {
    local level="$1"; shift
    printf '[public-ip-detector][%s] %s\n' "$level" "$*"
}

is_ipv4() {
    local candidate="$1"
    # Validate format and octets are 0-255
    if [[ ! "$candidate" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        return 1
    fi
    local IFS='.'
    local -a octets=($candidate)
    for octet in "${octets[@]}"; do
        if (( octet > 255 )); then
            return 1
        fi
    done
    return 0
}

detect_public_ip() {
    local ip=""
    local attempts=(
        "dig +short myip.opendns.com @resolver1.opendns.com"
        "dig +short TXT o-o.myaddr.l.google.com @ns1.google.com | tr -d '\"'"
        "curl -4 -fsS https://api.ipify.org"
        "curl -4 -fsS https://ifconfig.me"
        "curl -4 -fsS https://icanhazip.com"
        "curl -4 -fsS https://ipinfo.io/ip"
    )

    for cmd in "${attempts[@]}"; do
        if ip=$(eval "$cmd" 2>/dev/null | tr -d '\r' | head -n1); then
            if is_ipv4 "$ip"; then
                echo "$ip"
                return 0
            fi
        fi
    done

    return 1
}

OUTPUT_TEXT="${PUBLIC_IP_TEXT_PATH:-/shared/public_ip.txt}"
OUTPUT_JSON="${PUBLIC_IP_JSON_PATH:-/shared/public_ip.json}"
REFRESH_SECONDS="${PUBLIC_IP_REFRESH_SECONDS:-60}"
SERVER_PORT="${PUBLIC_IP_PORT:-27015}"

declare -i REFRESH_SECONDS
if (( REFRESH_SECONDS < 10 )); then
    log WARN "PUBLIC_IP_REFRESH_SECONDS too low (${REFRESH_SECONDS}). Bumping to 10."
    REFRESH_SECONDS=10
fi

mkdir -p "$(dirname "$OUTPUT_TEXT")"
mkdir -p "$(dirname "$OUTPUT_JSON")"

touch "$OUTPUT_TEXT" "$OUTPUT_JSON"

while true; do
    if ip=$(detect_public_ip); then
        log INFO "Detected public IP: $ip"
        tmp_txt="${OUTPUT_TEXT}.tmp"
        tmp_json="${OUTPUT_JSON}.tmp"
        printf '%s\n' "$ip" >"$tmp_txt"
        cat >"$tmp_json" <<EOF
{
  "ip": "$ip",
  "port": ${SERVER_PORT},
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
        mv "$tmp_txt" "$OUTPUT_TEXT"
        mv "$tmp_json" "$OUTPUT_JSON"
    else
        log WARN "Unable to detect public IP right now. Will retry."
    fi
    sleep "$REFRESH_SECONDS"
done
