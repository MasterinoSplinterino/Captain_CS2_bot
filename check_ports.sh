#!/bin/bash
# ==============================================================================
# CS2 Server Port Check Script
# ==============================================================================
# Проверяет доступность портов CS2 сервера изнутри VPS и снаружи
# ==============================================================================

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_header() {
    echo ""
    echo -e "${BLUE}======================================"
    echo "$1"
    echo "======================================${NC}"
}

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

# Определяем внешний IP
get_external_ip() {
    # Пробуем несколько сервисов для получения внешнего IP
    IP=$(curl -s https://api.ipify.org 2>/dev/null || curl -s https://ifconfig.me 2>/dev/null || curl -s https://icanhazip.com 2>/dev/null)
    if [ -z "$IP" ]; then
        print_error "Не удалось определить внешний IP"
        return 1
    fi
    echo "$IP"
}

print_header "CS2 Server Port Check"

# Получаем внешний IP
print_info "Определяю внешний IP адрес..."
EXTERNAL_IP=$(get_external_ip)
if [ $? -eq 0 ]; then
    print_success "Внешний IP: $EXTERNAL_IP"
else
    print_warning "Не удалось определить внешний IP. Продолжаю проверку локальных портов..."
    EXTERNAL_IP=""
fi

# Проверка 1: Docker контейнеры
print_header "Проверка 1: Docker Контейнеры"
if command -v docker &> /dev/null; then
    if docker ps | grep -q "cs2-server"; then
        print_success "Контейнер cs2-server запущен"
        echo ""
        docker ps --filter "name=cs2" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        print_error "Контейнер cs2-server не найден или не запущен"
        echo ""
        print_info "Запустите сервер: docker-compose -f docker-compose.prod.yml up -d"
        exit 1
    fi
else
    print_error "Docker не установлен или не доступен"
    exit 1
fi

# Проверка 2: Прослушивающие порты
print_header "Проверка 2: Прослушивающие порты на хосте"
echo ""

check_port() {
    local PORT=$1
    local PROTO=$2
    local DESC=$3

    if command -v ss &> /dev/null; then
        if ss -${PROTO}ln | grep -q ":${PORT}"; then
            print_success "Порт ${PORT}/${PROTO} открыт - $DESC"
            return 0
        else
            print_error "Порт ${PORT}/${PROTO} НЕ открыт - $DESC"
            return 1
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -${PROTO}ln | grep -q ":${PORT}"; then
            print_success "Порт ${PORT}/${PROTO} открыт - $DESC"
            return 0
        else
            print_error "Порт ${PORT}/${PROTO} НЕ открыт - $DESC"
            return 1
        fi
    else
        print_warning "Утилиты ss/netstat не найдены"
        return 2
    fi
}

check_port 27015 "t" "RCON/SourceTV"
check_port 27015 "u" "Game Traffic (UDP)"
check_port 27020 "u" "SourceTV Relay"

# Проверка 3: Правила файрволла
print_header "Проверка 3: Правила файрволла"
echo ""

if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        print_info "UFW активен. Проверяю правила для CS2..."
        echo ""
        if ufw status | grep -E "27015|27020" | grep -q "ALLOW"; then
            print_success "Порты CS2 разрешены в UFW:"
            ufw status | grep -E "27015|27020"
        else
            print_error "Порты CS2 НЕ найдены в правилах UFW!"
            print_warning "Запустите: sudo ./setup_firewall.sh"
        fi
    else
        print_warning "UFW установлен, но отключен"
    fi
elif command -v firewall-cmd &> /dev/null; then
    if systemctl is-active --quiet firewalld; then
        print_info "firewalld активен. Проверяю правила для CS2..."
        echo ""
        if firewall-cmd --list-ports | grep -qE "27015|27020"; then
            print_success "Порты CS2 разрешены в firewalld:"
            firewall-cmd --list-ports | grep -E "27015|27020"
        else
            print_error "Порты CS2 НЕ найдены в правилах firewalld!"
            print_warning "Запустите: sudo ./setup_firewall.sh"
        fi
    else
        print_warning "firewalld установлен, но отключен"
    fi
elif command -v iptables &> /dev/null; then
    print_info "Проверяю правила iptables для CS2..."
    echo ""
    if iptables -L -n | grep -qE "27015|27020"; then
        print_success "Порты CS2 найдены в правилах iptables:"
        iptables -L -n -v | grep -E "27015|27020"
    else
        print_warning "Порты CS2 НЕ найдены в правилах iptables"
        print_warning "Запустите: sudo ./setup_firewall.sh"
    fi
else
    print_warning "Файрволл не обнаружен (UFW/firewalld/iptables)"
fi

# Проверка 4: Тест подключения к RCON (локально)
print_header "Проверка 4: RCON подключение (локально)"
echo ""

# Проверяем доступность порта через telnet/nc
if command -v nc &> /dev/null; then
    if timeout 2 nc -z localhost 27015 2>/dev/null; then
        print_success "Порт 27015 доступен локально (RCON)"
    else
        print_error "Порт 27015 НЕ доступен локально"
    fi
elif command -v telnet &> /dev/null; then
    if timeout 2 telnet localhost 27015 2>/dev/null | grep -q "Connected"; then
        print_success "Порт 27015 доступен локально (RCON)"
    else
        print_error "Порт 27015 НЕ доступен локально"
    fi
else
    print_warning "Утилиты nc/telnet не найдены. Устанвите: apt install netcat или yum install nc"
fi

# Проверка 5: Внешняя доступность (если есть внешний IP)
if [ -n "$EXTERNAL_IP" ]; then
    print_header "Проверка 5: Внешняя доступность портов"
    echo ""

    print_info "Тестирую внешнюю доступность с помощью nmap (если установлен)..."

    if command -v nmap &> /dev/null; then
        echo ""
        print_info "Сканирую порты 27015 и 27020 на $EXTERNAL_IP..."

        # Проверяем TCP 27015
        if nmap -Pn -p 27015 $EXTERNAL_IP 2>/dev/null | grep "27015/tcp" | grep -q "open"; then
            print_success "Порт 27015/TCP доступен снаружи"
        else
            print_warning "Порт 27015/TCP НЕ доступен снаружи (может быть заблокирован провайдером)"
        fi

        # Проверяем UDP 27015
        print_info "Проверка UDP портов (может занять время)..."
        if nmap -Pn -sU -p 27015 $EXTERNAL_IP 2>/dev/null | grep "27015/udp" | grep -qE "open|open\|filtered"; then
            print_success "Порт 27015/UDP доступен снаружи"
        else
            print_warning "Порт 27015/UDP НЕ доступен снаружи"
        fi
    else
        print_warning "nmap не установлен. Установите для проверки внешней доступности:"
        print_info "  Ubuntu/Debian: sudo apt install nmap"
        print_info "  CentOS/RHEL: sudo yum install nmap"
        echo ""
        print_info "Для быстрой проверки используйте онлайн-сервисы:"
        print_info "  https://www.yougetsignal.com/tools/open-ports/"
        print_info "  Проверьте порты: 27015 (TCP и UDP)"
    fi
fi

# Итоговая информация
print_header "Итоговая информация"
echo ""
print_info "Для подключения к серверу используйте:"
if [ -n "$EXTERNAL_IP" ]; then
    echo ""
    echo "  В консоли CS2:"
    echo "    connect ${EXTERNAL_IP}:27015; password ВАШ_ПАРОЛЬ"
    echo ""
    echo "  Или добавьте в избранное:"
    echo "    IP: ${EXTERNAL_IP}"
    echo "    Port: 27015"
fi
echo ""
print_info "Для проверки работы сервера в Telegram боте используйте:"
echo "    /start -> ☰ Menu -> 📊 Server Status"
echo ""

print_header "Проверка завершена"
