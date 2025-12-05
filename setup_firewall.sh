#!/bin/bash
# ==============================================================================
# CS2 Server Firewall Setup Script
# ==============================================================================
# Этот скрипт настраивает файрволл для CS2 сервера
# Поддерживает: UFW (Ubuntu/Debian) и firewalld (CentOS/RHEL)
# ==============================================================================

set -e

echo "======================================"
echo "CS2 Server Firewall Setup"
echo "======================================"
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    print_error "Этот скрипт должен запускаться с правами root (sudo)"
    exit 1
fi

# Определение системы файрволла
detect_firewall() {
    if command -v ufw &> /dev/null; then
        echo "ufw"
    elif command -v firewall-cmd &> /dev/null; then
        echo "firewalld"
    elif command -v iptables &> /dev/null; then
        echo "iptables"
    else
        echo "none"
    fi
}

FIREWALL=$(detect_firewall)

echo "Обнаружен файрволл: $FIREWALL"
echo ""

# Настройка UFW (Ubuntu/Debian)
setup_ufw() {
    print_warning "Настройка UFW..."

    # Включаем UFW, если он отключен
    if ! ufw status | grep -q "Status: active"; then
        print_warning "UFW отключен. Включаю..."
        # Сначала разрешаем SSH, чтобы не потерять доступ
        ufw allow ssh
        ufw --force enable
        print_success "UFW включен"
    fi

    # Открываем порты для CS2
    echo ""
    echo "Открываю порты для CS2 сервера..."

    # Порт 27015 TCP (RCON и Source TV)
    ufw allow 27015/tcp comment 'CS2 Server - TCP'
    print_success "Порт 27015/TCP открыт (RCON/SourceTV)"

    # Порт 27015 UDP (основной игровой трафик)
    ufw allow 27015/udp comment 'CS2 Server - UDP'
    print_success "Порт 27015/UDP открыт (игровой трафик)"

    # Порт 27020 UDP (Source TV relay)
    ufw allow 27020/udp comment 'CS2 Server - SourceTV'
    print_success "Порт 27020/UDP открыт (SourceTV relay)"

    # Опционально: порт для Steam мастер-сервера (если нужен)
    # ufw allow 27005/udp comment 'CS2 Server - Steam'

    echo ""
    print_success "UFW настроен успешно!"
    echo ""
    echo "Текущие правила UFW:"
    ufw status numbered
}

# Настройка firewalld (CentOS/RHEL)
setup_firewalld() {
    print_warning "Настройка firewalld..."

    # Включаем firewalld, если он отключен
    if ! systemctl is-active --quiet firewalld; then
        print_warning "firewalld отключен. Включаю..."
        systemctl start firewalld
        systemctl enable firewalld
        print_success "firewalld включен"
    fi

    # Открываем порты для CS2
    echo ""
    echo "Открываю порты для CS2 сервера..."

    # Порт 27015 TCP
    firewall-cmd --permanent --add-port=27015/tcp
    print_success "Порт 27015/TCP открыт (RCON/SourceTV)"

    # Порт 27015 UDP
    firewall-cmd --permanent --add-port=27015/udp
    print_success "Порт 27015/UDP открыт (игровой трафик)"

    # Порт 27020 UDP
    firewall-cmd --permanent --add-port=27020/udp
    print_success "Порт 27020/UDP открыт (SourceTV relay)"

    # Применяем изменения
    firewall-cmd --reload

    echo ""
    print_success "firewalld настроен успешно!"
    echo ""
    echo "Текущие правила firewalld:"
    firewall-cmd --list-all
}

# Настройка iptables (базовая)
setup_iptables() {
    print_warning "Настройка iptables..."

    echo ""
    echo "Открываю порты для CS2 сервера..."

    # Порт 27015 TCP
    iptables -A INPUT -p tcp --dport 27015 -j ACCEPT
    print_success "Порт 27015/TCP открыт (RCON/SourceTV)"

    # Порт 27015 UDP
    iptables -A INPUT -p udp --dport 27015 -j ACCEPT
    print_success "Порт 27015/UDP открыт (игровой трафик)"

    # Порт 27020 UDP
    iptables -A INPUT -p udp --dport 27020 -j ACCEPT
    print_success "Порт 27020/UDP открыт (SourceTV relay)"

    # Сохраняем правила (зависит от дистрибутива)
    if command -v iptables-save &> /dev/null; then
        if [ -f /etc/iptables/rules.v4 ]; then
            iptables-save > /etc/iptables/rules.v4
        elif [ -f /etc/sysconfig/iptables ]; then
            iptables-save > /etc/sysconfig/iptables
        fi
        print_success "Правила iptables сохранены"
    fi

    echo ""
    print_success "iptables настроен успешно!"
    echo ""
    echo "Текущие правила iptables:"
    iptables -L -n -v | grep -E "27015|27020"
}

# Выполнение настройки в зависимости от типа файрволла
case $FIREWALL in
    ufw)
        setup_ufw
        ;;
    firewalld)
        setup_firewalld
        ;;
    iptables)
        setup_iptables
        ;;
    none)
        print_error "Файрволл не обнаружен!"
        print_warning "Установите один из: ufw, firewalld, или iptables"
        exit 1
        ;;
esac

echo ""
echo "======================================"
print_success "Настройка файрволла завершена!"
echo "======================================"
echo ""
echo "Следующие шаги:"
echo "1. Проверьте, что Docker запущен: docker ps"
echo "2. Проверьте порты: ./check_ports.sh"
echo "3. Проверьте подключение из CS2: connect <ВАШ_IP>:27015"
echo ""
