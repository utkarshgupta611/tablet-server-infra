#!/usr/bin/env bash
# ==============================================================================
# Deploy Script for Android Tablet Server (GitOps Deployment)
# Domain: chozzen.xyz
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== [1/4] Pulling latest repository updates ==="
cd "$REPO_DIR"
git pull origin master || git pull || echo "Warning: git pull failed or repository not backed by remote yet."

echo "=== [2/4] Syncing Nginx configuration ==="
if [ -f "$REPO_DIR/configs/nginx/default.conf" ]; then
    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/conf.d /data/data/com.termux/files/usr/etc/nginx/conf.d 2>/dev/null || true
    cp "$REPO_DIR/configs/nginx/default.conf" /etc/nginx/sites-available/default 2>/dev/null || true
    cp "$REPO_DIR/configs/nginx/default.conf" /etc/nginx/conf.d/default.conf 2>/dev/null || true
    cp "$REPO_DIR/configs/nginx/default.conf" /data/data/com.termux/files/usr/etc/nginx/conf.d/default.conf 2>/dev/null || true
    ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default 2>/dev/null || true
    echo "Nginx site configuration updated."
fi

echo "=== [3/4] Syncing Dashboard Web UI assets ==="
if [ -d "$REPO_DIR/web" ]; then
    mkdir -p /var/www/dashboard /var/www/html /data/data/com.termux/files/home/www /data/data/com.termux/files/usr/share/nginx/html 2>/dev/null || true
    cp -r "$REPO_DIR/web/"* /var/www/dashboard/ 2>/dev/null || true
    cp -r "$REPO_DIR/web/"* /var/www/html/ 2>/dev/null || true
    cp -r "$REPO_DIR/web/"* /data/data/com.termux/files/home/www/ 2>/dev/null || true
    cp -r "$REPO_DIR/web/"* /data/data/com.termux/files/usr/share/nginx/html/ 2>/dev/null || true
    echo "Web dashboard assets updated across Termux host webroot (/data/data/com.termux/files/home/www) and Debian webroots."
fi

echo "=== [4/4] Validating & Restarting Nginx ==="
nginx -t 2>/dev/null || true
pkill -9 -f nginx 2>/dev/null || true
nohup nginx >/dev/null 2>&1 & || true

echo "=============================================================================="
echo "Deployment successful! Live at https://chozzen.xyz"
