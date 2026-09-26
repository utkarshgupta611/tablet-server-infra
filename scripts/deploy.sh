#!/usr/bin/env bash
# ==============================================================================
# Deploy Script for Android Tablet Server (GitOps Deployment)
# Domain: chozzen.xyz
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== [1/5] Pulling latest repository updates ==="
cd "$REPO_DIR"
git pull origin master || git pull || echo "Warning: git pull failed or repository not backed by remote yet."

echo "=== [2/5] Setting permissions and syncing scripts ==="
chmod +x "$REPO_DIR"/scripts/*.sh 2>/dev/null || chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true
if [ -f "$REPO_DIR/scripts/run-tunnel.sh" ]; then
    cp "$REPO_DIR/scripts/run-tunnel.sh" /root/run-tunnel.sh 2>/dev/null || true
    chmod +x /root/run-tunnel.sh 2>/dev/null || true
    echo "Watchdog supervisor synced to /root/run-tunnel.sh with execution permissions."
fi

echo "=== [3/5] Syncing Nginx configuration ==="
if [ -f "$REPO_DIR/configs/nginx/default.conf" ]; then
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/conf.d /data/data/com.termux/files/usr/etc/nginx/conf.d 2>/dev/null || true
    cp "$REPO_DIR/configs/nginx/default.conf" /etc/nginx/sites-available/default 2>/dev/null || true
    cp "$REPO_DIR/configs/nginx/default.conf" /etc/nginx/conf.d/default.conf 2>/dev/null || true
    cp "$REPO_DIR/configs/nginx/default.conf" /data/data/com.termux/files/usr/etc/nginx/conf.d/default.conf 2>/dev/null || true
    ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default 2>/dev/null || true
    echo "Nginx site configuration updated."
fi

echo "=== [4/5] Syncing Dashboard Web UI assets ==="
if [ -d "$REPO_DIR/web" ]; then
    mkdir -p /var/www/dashboard /var/www/html /data/data/com.termux/files/home/www /data/data/com.termux/files/usr/share/nginx/html 2>/dev/null || true
    cp -r "$REPO_DIR/web/"* /var/www/dashboard/ 2>/dev/null || true
    cp -r "$REPO_DIR/web/"* /var/www/html/ 2>/dev/null || true
    cp -r "$REPO_DIR/web/"* /data/data/com.termux/files/home/www/ 2>/dev/null || true
    cp -r "$REPO_DIR/web/"* /data/data/com.termux/files/usr/share/nginx/html/ 2>/dev/null || true
    echo "Web dashboard assets updated across Termux host webroot (/data/data/com.termux/files/home/www) and Debian webroots."
fi

echo "=== [5/5] Validating & Restarting Services ==="
nginx -t || true
service nginx restart 2>/dev/null || service nginx start 2>/dev/null || {
    pkill -9 -f nginx 2>/dev/null || true
    nohup nginx >/dev/null 2>&1 &
}

# Ensure Cloudflare Tunnel Watchdog supervisor is running
pkill -f "run-tunnel.sh" 2>/dev/null || true
pkill -f "cloudflared" 2>/dev/null || true
RUN_TUNNEL="/root/run-tunnel.sh"
[ ! -f "$RUN_TUNNEL" ] && RUN_TUNNEL="$REPO_DIR/scripts/run-tunnel.sh"
if [ -f "$RUN_TUNNEL" ]; then
    chmod +x "$RUN_TUNNEL" 2>/dev/null || true
    nohup "$RUN_TUNNEL" > /dev/null 2>&1 &
    echo "Cloudflare Tunnel Watchdog supervisor restarted."
fi

pkill -f "sys_monitor.py" 2>/dev/null || true
if [ -f "$REPO_DIR/scripts/sys_monitor.py" ]; then
    nohup python3 "$REPO_DIR/scripts/sys_monitor.py" > /dev/null 2>&1 &
fi
sleep 1

echo "=============================================================================="
echo "Deployment successful! Live at https://chozzen.xyz"
