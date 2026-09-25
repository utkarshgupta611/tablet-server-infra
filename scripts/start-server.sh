#!/usr/bin/env bash
# ==============================================================================
# Start Script for Android Tablet Server (Debian PRoot)
# Domain: chozzen.xyz
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [1/4] Starting Nginx Gateway ==="
service nginx start || echo "Nginx status check complete."

echo "=== [2/4] Starting File Browser ==="
if pgrep -x "filebrowser" > /dev/null; then
    echo "FileBrowser is already running."
else
    nohup filebrowser -r /root/storage -p 8080 -b /files > /var/log/filebrowser.log 2>&1 &
    echo "FileBrowser started on http://127.0.0.1:8080/ (base path: /files)."
fi

echo "=== [3/4] Starting Cloudflare Tunnel Watchdog Supervisor ==="
chmod +x "$SCRIPT_DIR/run-tunnel.sh" 2>/dev/null || true
chmod +x /root/run-tunnel.sh 2>/dev/null || true
if pgrep -f "run-tunnel.sh" > /dev/null; then
    echo "Cloudflare Tunnel Watchdog (run-tunnel.sh) is already running."
else
    RUN_TUNNEL="$SCRIPT_DIR/run-tunnel.sh"
    [ -f "/root/run-tunnel.sh" ] && RUN_TUNNEL="/root/run-tunnel.sh"
    nohup "$RUN_TUNNEL" > /dev/null 2>&1 &
    echo "Cloudflare Tunnel Watchdog started."
fi

echo "=== [4/4] Starting System Health Monitor Daemon ==="
if pgrep -f "sys_monitor.py" > /dev/null; then
    echo "System Health Monitor (sys_monitor.py) is already running."
else
    nohup python3 "$SCRIPT_DIR/sys_monitor.py" > /dev/null 2>&1 &
    echo "System Health Monitor started."
fi

echo ""
echo "=== Server Status Check ==="
ps aux | grep -E 'nginx|filebrowser|cloudflared|run-tunnel' | grep -v grep
echo "=============================================================================="
echo "Server Startup Complete! Access globally at https://chozzen.xyz"
