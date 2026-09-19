#!/usr/bin/env bash
# ==============================================================================
# Start Script for Android Tablet Server (Debian PRoot)
# Domain: chozzen.xyz
# ==============================================================================

echo "=== [1/3] Starting Nginx Gateway ==="
service nginx start || echo "Nginx status check complete."

echo "=== [2/3] Starting File Browser ==="
if pgrep -x "filebrowser" > /dev/null; then
    echo "FileBrowser is already running."
else
    nohup filebrowser -r /root/storage -p 8080 -b /files > /var/log/filebrowser.log 2>&1 &
    echo "FileBrowser started on http://127.0.0.1:8080/ (base path: /files)."
fi

echo "=== [3/4] Starting Cloudflare Tunnel (redmi-tunnel) ==="
if pgrep -x "cloudflared" > /dev/null; then
    echo "Cloudflare Tunnel (cloudflared) is already running."
else
    nohup cloudflared tunnel run redmi-tunnel > /root/.cloudflared/tunnel.log 2>&1 &
    echo "Cloudflare Tunnel started."
fi

echo "=== [4/4] Starting System Health Monitor Daemon ==="
if pgrep -f "sys_monitor.py" > /dev/null; then
    echo "System Health Monitor (sys_monitor.py) is already running."
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    nohup python3 "$SCRIPT_DIR/sys_monitor.py" > /dev/null 2>&1 &
    echo "System Health Monitor started."
fi

echo ""
echo "=== Server Status Check ==="
ps aux | grep -E 'nginx|filebrowser|cloudflared' | grep -v grep
echo "=============================================================================="
echo "Server Startup Complete! Access globally at https://chozzen.xyz"
