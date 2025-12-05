#!/bin/bash
# ==============================================================================
# CS2 Bot Entrypoint Script
# ==============================================================================
# Запускается при старте контейнера бота
# Настраивает файрволл на хосте и проверяет доступность портов
# ==============================================================================

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo "======================================"
echo "CS2 Bot Starting..."
echo "======================================"
echo ""

# Проверка 1: Ждем запуска CS2 сервера
print_info "Waiting for CS2 server to start..."

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if nc -z ${RCON_HOST:-cs2} ${RCON_PORT:-27015} 2>/dev/null; then
        print_success "CS2 server is ready at ${RCON_HOST:-cs2}:${RCON_PORT:-27015}"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_warning "CS2 server not responding yet, but starting bot anyway..."
fi

# Проверка 2: Настройка файрволла на хосте (если есть доступ)
print_info "Checking firewall configuration on host..."

# Проверяем, есть ли скрипт настройки файрволла
if [ -f "/scripts/setup_firewall.sh" ]; then
    print_info "Found firewall setup script. Attempting to configure..."

    # Пытаемся выполнить на хосте через docker exec или nsenter
    # Это работает только если контейнер запущен с привилегиями
    if command -v nsenter &> /dev/null; then
        # Получаем PID init процесса хоста
        HOST_PID=1

        # Пытаемся выполнить скрипт на хосте
        if nsenter -t $HOST_PID -m -u -n -i /bin/bash /scripts/setup_firewall.sh 2>/dev/null; then
            print_success "Firewall configured successfully"
        else
            print_warning "Could not configure firewall automatically (requires privileged mode)"
            print_info "Please run manually: sudo ./setup_firewall.sh"
        fi
    else
        print_warning "nsenter not available. Firewall must be configured manually."
        print_info "Please run on host: sudo ./setup_firewall.sh"
    fi
else
    print_warning "Firewall setup script not found at /scripts/setup_firewall.sh"
    print_info "Firewall must be configured manually"
fi

echo ""

# Проверка 3: Определяем внешний IP
print_info "Detecting external IP..."

EXTERNAL_IP=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || curl -s --max-time 5 https://ifconfig.me 2>/dev/null || echo "")

if [ -n "$EXTERNAL_IP" ]; then
    print_success "External IP detected: $EXTERNAL_IP"

    # Экспортируем IP для использования в боте (если нужно)
    export DETECTED_EXTERNAL_IP="$EXTERNAL_IP"

    echo ""
    print_info "Server connection info:"
    echo "  connect ${EXTERNAL_IP}:27015"
else
    print_warning "Could not detect external IP"
fi

echo ""
echo "======================================"
print_success "Starting Telegram Bot..."
echo "======================================"
echo ""

# Запускаем бота
exec python main.py
