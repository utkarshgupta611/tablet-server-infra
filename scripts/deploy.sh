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
git pull origin main || echo "Warning: git pull failed or repository not backed by remote yet."

echo "=== [2/4] Syncing Nginx configuration ==="
if [ -f "$REPO_DIR/configs/nginx/default.conf" ]; then
    cp "$REPO_DIR/configs/nginx/default.conf" /etc/nginx/sites-available/default
    echo "Nginx site configuration updated."
fi

echo "=== [3/4] Syncing Dashboard Web UI assets ==="
if [ -d "$REPO_DIR/web" ]; then
    mkdir -p /var/www/dashboard
    cp -r "$REPO_DIR/web/"* /var/www/dashboard/
    echo "Web dashboard assets updated in /var/www/dashboard/."
fi

echo "=== [4/4] Validating & Reloading Nginx ==="
nginx -t
service nginx reload

echo "=============================================================================="
echo "Deployment successful! Live at https://chozzen.xyz"
