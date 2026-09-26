#!/bin/bash
# Auto-restart supervisor for Nginx and Cloudflare Tunnel on Android PRoot
while true; do
    # Check and resurrect Nginx if stopped
    if ! pgrep -x "nginx" > /dev/null; then
        echo "[$(date)] Nginx not running. Starting Nginx..." >> /var/log/supervisor.log
        nginx 2>/dev/null || /usr/sbin/nginx 2>/dev/null
    fi

    # Run Cloudflare Tunnel over HTTP/2 (prevents Android QUIC/UDP socket drops)
    echo "[$(date)] Starting cloudflared tunnel over HTTP/2..." >> /var/log/supervisor.log
    cloudflared tunnel --protocol http2 run redmi-tunnel >> /var/log/cloudflared.log 2>&1

    echo "[$(date)] cloudflared exited. Respawning in 3 seconds..." >> /var/log/supervisor.log
    sleep 3
done
