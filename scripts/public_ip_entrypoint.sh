#!/bin/bash
# Wrapper entrypoint that reads a cached PUBLIC_IP provided by the dedicated
# detector sidecar. If the cache is unavailable the server still boots.
set -euo pipefail

log() {
    local level="$1"; shift
    printf '[public-ip][%s] %s\n' "$level" "$*"
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

PUBLIC_IP_FILE="${PUBLIC_IP_FILE:-/shared/public_ip.txt}"
PUBLIC_IP_WAIT_SECONDS=${PUBLIC_IP_WAIT_SECONDS:-30}
if ! [[ "$PUBLIC_IP_WAIT_SECONDS" =~ ^[0-9]+$ ]]; then
    PUBLIC_IP_WAIT_SECONDS=30
fi

read_cached_ip() {
    local file="$1"
    if [[ -f "$file" ]]; then
        local value
        value="$(head -n1 "$file" | tr -d '\r\n ')"
        if is_ipv4 "$value"; then
            echo "$value"
            return 0
        fi
    fi
    return 1
}

ensure_public_ip() {
    if [[ -n "${PUBLIC_IP:-}" && "${PUBLIC_IP}" != "auto" ]]; then
        export CS2_IP="$PUBLIC_IP"
        export IP="$PUBLIC_IP"
        log INFO "Using provided PUBLIC_IP=${PUBLIC_IP}"
        return
    fi

    local deadline=$(( $(date +%s) + PUBLIC_IP_WAIT_SECONDS ))
    while (( $(date +%s) <= deadline )); do
        if ip=$(read_cached_ip "$PUBLIC_IP_FILE"); then
            export PUBLIC_IP="$ip"
            export CS2_IP="$ip"
            export IP="$ip"
            log INFO "Using cached PUBLIC_IP=${PUBLIC_IP} from ${PUBLIC_IP_FILE}"
            return
        fi
        sleep 2
    done

    log WARN "PUBLIC_IP cache ${PUBLIC_IP_FILE} not ready. Continuing without it."
}

create_dig_shim() {
    local real_dig=""
    if command -v dig >/dev/null 2>&1; then
        real_dig="$(command -v dig)"
    fi

    # Create wrapper script that will be sourced, not executed
    local shim_dir="/tmp/public-ip-tools"
    mkdir -p "$shim_dir"
    
    # Move real dig to backup location
    if [[ -n "$real_dig" && -x "$real_dig" ]]; then
        local dig_backup="${shim_dir}/dig.real"
        if [[ ! -f "$dig_backup" ]]; then
            cp "$real_dig" "$dig_backup" 2>/dev/null || true
        fi
        real_dig="$dig_backup"
    fi
    
    # Create shim that intercepts dig calls
    local shim_path="${shim_dir}/dig"
    cat >"$shim_path" <<EOF
#!/bin/bash
TARGET_FILE="${PUBLIC_IP_FILE}"
REAL_DIG="${real_dig}"

read_cached_ip() {
    if [[ -f "\$TARGET_FILE" ]]; then
        local value
        value="\$(head -n1 "\$TARGET_FILE" 2>/dev/null | tr -d '\r\n ')"
        if [[ "\$value" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
            echo "\$value"
            return 0
        fi
    fi
    return 1
}

# Intercept public IP detection queries
if [[ "\$*" == *"myip.opendns.com"* ]] || [[ "\$*" == *"o-o.myaddr.l.google.com"* ]]; then
    if cached_ip=\$(read_cached_ip); then
        echo "\$cached_ip"
        exit 0
    fi
fi

# Fall back to real dig if available
if [[ -n "\$REAL_DIG" && -x "\$REAL_DIG" ]]; then
    exec "\$REAL_DIG" "\$@"
fi

# If no real dig, try to return cached IP as last resort
if cached_ip=\$(read_cached_ip); then
    echo "\$cached_ip"
    exit 0
fi

echo "dig: command not found and no cached IP available" >&2
exit 1
EOF
    chmod +x "$shim_path"
    
    # Prepend to PATH - this will be inherited by sudo -E
    export PATH="${shim_dir}:${PATH}"
}

# Allow the script to default to the image CMD if compose does not pass args
if [[ $# -eq 0 ]]; then
    set -- sudo -E bash /home/cs2-modded-server/install_docker.sh
fi

ensure_public_ip

# Debug: log what we're passing
log INFO "PUBLIC_IP is set to: ${PUBLIC_IP:-<not set>}"
log INFO "Command to execute: $*"

# Always create dig shim (it will return empty if file missing)
create_dig_shim

# Verify shim is in PATH
if command -v dig >/dev/null 2>&1; then
    log INFO "dig command found at: $(command -v dig)"
else
    log WARN "dig command not found in PATH"
fi

exec "$@"
