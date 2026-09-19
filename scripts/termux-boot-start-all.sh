#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Boot Hook Script (Place in ~/.termux/boot/start-all.sh)
# Android Host Layer Boot Automation
# ==============================================================================

# Prevent CPU sleep state on Android
termux-wake-lock

echo "=== [1/5] Starting OpenSSH Daemon ==="
pgrep -x sshd > /dev/null || sshd

echo "=== [2/5] Starting Mosquitto MQTT Broker ==="
if ! pgrep -x mosquitto > /dev/null; then
    mosquitto -c ~/.config/mosquitto/mosquitto.conf -d 2>/dev/null || true
fi

echo "=== [3/5] Starting FileBrowser (External Drive - Port 8080) ==="
if ! pgrep -f "filebrowser.db" > /dev/null; then
    nohup filebrowser -d ~/.config/filebrowser/filebrowser.db > /dev/null 2>&1 &
fi

echo "=== [4/5] Starting FileBrowser (Internal Storage - Port 8082) ==="
if ! pgrep -f "fb_internal.db" > /dev/null; then
    nohup filebrowser -d ~/.config/filebrowser/fb_internal.db > /dev/null 2>&1 &
fi

echo "=== [5/5] Launching Debian PRoot Server Stack (Nginx + Tunnel + AdGuard + Health Monitor) ==="
nohup proot-distro login debian -- bash -c "
    service nginx start
    if ! pgrep -x cloudflared > /dev/null; then
        nohup cloudflared tunnel run redmi-tunnel > /root/.cloudflared/tunnel.log 2>&1 &
    fi
    if [ -d /root/AdGuardHome ] && ! pgrep -f 'AdGuardHome' > /dev/null; then
        cd /root/AdGuardHome && nohup ./AdGuardHome -c AdGuardHome.yaml > /dev/null 2>&1 &
    fi
    if ! pgrep -f 'sys_monitor.py' > /dev/null; then
        nohup python3 /root/tablet-server-infra/scripts/sys_monitor.py > /dev/null 2>&1 &
    fi
" > /dev/null 2>&1 &

echo "Termux Host Startup Sequence Dispatched Successfully."
