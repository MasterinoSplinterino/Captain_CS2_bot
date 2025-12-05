#!/bin/bash
# Wrapper entrypoint that ensures the CS2 container always starts with a valid
# PUBLIC_IP value. Falls back to multiple providers if the first lookup fails.
set -euo pipefail

log() {
    local level="$1"; shift
    printf '[public-ip][%s] %s\n' "$level" "$*"
}

is_ipv4() {
    local candidate="$1"
    [[ "$candidate" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]
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

# Allow the script to default to the image CMD if compose does not pass args
if [[ $# -eq 0 ]]; then
    set -- sudo -E bash /home/cs2-modded-server/install_docker.sh
fi

if [[ -z "${PUBLIC_IP:-}" || "${PUBLIC_IP}" == "auto" ]]; then
    if ip=$(detect_public_ip); then
        export PUBLIC_IP="$ip"
        log INFO "Auto-detected public IP: ${PUBLIC_IP}"
    else
        log ERROR "Unable to detect public IP. Set PUBLIC_IP manually or ensure outbound DNS/HTTPS is allowed."
        exit 1
    fi
else
    log INFO "Using existing PUBLIC_IP=${PUBLIC_IP}"
fi

# Some upstream scripts always call `dig` to determine the public IP and exit if it fails.
# When we already know the IP (environment variable or auto detection above) we shim `dig`
# so that specific lookups for `myip.opendns.com` and `o-o.myaddr.l.google.com` simply
# return the detected value. All other dig queries fall back to the original binary.
if command -v dig >/dev/null 2>&1; then
    REAL_DIG_PATH="$(command -v dig)"
    SHIM_PATH="/usr/local/bin/dig"
    if [[ -n "${PUBLIC_IP:-}" ]]; then
        cat >"${SHIM_PATH}" <<EOF
#!/bin/bash
PUBLIC_IP_VALUE="${PUBLIC_IP}"
REAL_DIG="${REAL_DIG_PATH}"
if [[ "\$*" == *"myip.opendns.com"* ]] || [[ "\$*" == *"o-o.myaddr.l.google.com"* ]]; then
    if [[ -n "\${PUBLIC_IP_VALUE}" ]]; then
        echo "\${PUBLIC_IP_VALUE}"
        exit 0
    fi
fi
exec "\${REAL_DIG}" "\$@"
EOF
        chmod +x "${SHIM_PATH}"
    fi
fi

exec "$@"
