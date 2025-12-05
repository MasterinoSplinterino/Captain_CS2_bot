#!/bin/bash

# CS2 Server System Optimization Script
# Run this on the VPS host (not in Docker) for best performance

set -e

echo "========================================="
echo "CS2 Server System Optimization"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./optimize_system.sh)"
    exit 1
fi

# 1. Optimize sysctl for network performance
echo "[1/5] Optimizing kernel network parameters..."
cat >> /etc/sysctl.conf << 'EOF'

# CS2 Server Network Optimizations
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 30000
net.ipv4.tcp_max_syn_backlog = 8096
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_tw_reuse = 1
net.core.somaxconn = 65535

# Enable BBR congestion control
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# Reduce TIME_WAIT connections
net.ipv4.tcp_fin_timeout = 15
net.ipv4.ip_local_port_range = 1024 65535
EOF

sysctl -p
echo "✓ Network parameters optimized"
echo ""

# 2. Optimize ulimits
echo "[2/5] Optimizing ulimits..."
cat >> /etc/security/limits.conf << 'EOF'

# CS2 Server ulimits
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF
echo "✓ Ulimits optimized"
echo ""

# 3. Disable transparent huge pages (can cause latency)
echo "[3/5] Disabling transparent huge pages..."
if [ -f /sys/kernel/mm/transparent_hugepage/enabled ]; then
    echo never > /sys/kernel/mm/transparent_hugepage/enabled
    echo never > /sys/kernel/mm/transparent_hugepage/defrag
    echo "✓ Transparent huge pages disabled"
else
    echo "⚠ Transparent huge pages not available (might be in container)"
fi
echo ""

# 4. Optimize Docker daemon
echo "[4/5] Optimizing Docker daemon..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    },
    "nproc": {
      "Name": "nproc",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
EOF

# Restart Docker to apply changes
systemctl restart docker
echo "✓ Docker daemon optimized and restarted"
echo ""

# 5. Check and report system info
echo "[5/5] System information:"
echo "----------------------------------------"
echo "CPU Model:"
cat /proc/cpuinfo | grep "model name" | head -1 | cut -d: -f2
echo ""
echo "CPU Cores: $(nproc)"
echo "Total RAM: $(free -h | grep Mem | awk '{print $2}')"
echo "Available RAM: $(free -h | grep Mem | awk '{print $7}')"
echo ""
echo "TCP Congestion Control: $(sysctl net.ipv4.tcp_congestion_control | cut -d= -f2)"
echo "----------------------------------------"
echo ""

echo "========================================="
echo "✓ Optimization complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Run: docker-compose -f docker-compose.prod.yml down"
echo "2. Run: docker-compose -f docker-compose.prod.yml up -d"
echo "3. Check logs: docker logs cs2-server -f"
echo ""
