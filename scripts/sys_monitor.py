#!/usr/bin/env python3
# ==============================================================================
# Live System Metrics Collector for Android Tablet Server (chozzen.xyz)
# Zero-dependency daemon writing stats.json every 3 seconds
# ==============================================================================

import json
import os
import subprocess
import sys
import time

TARGET_PATHS = [
    "/var/www/dashboard/stats.json",
    "/var/www/html/stats.json",
    "/data/data/com.termux/files/home/www/stats.json",
]

def get_cpu_times():
    try:
        with open("/proc/stat", "r") as f:
            first_line = f.readline()
        parts = [float(x) for x in first_line.split()[1:]]
        idle_time = parts[3] + parts[4]
        total_time = sum(parts)
        return idle_time, total_time
    except Exception:
        return 0, 0

def get_cpu_usage(prev_idle, prev_total):
    idle, total = get_cpu_times()
    diff_idle = idle - prev_idle
    diff_total = total - prev_total
    if diff_total == 0:
        return 0.0, idle, total
    usage = (1.0 - (diff_idle / diff_total)) * 100.0
    return round(max(0.0, min(100.0, usage)), 1), idle, total

def get_ram_usage():
    try:
        mem = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].split()[0].strip()
                    mem[key] = int(val)
        
        total_kb = mem.get("MemTotal", 0)
        avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0) + mem.get("Buffers", 0) + mem.get("Cached", 0))
        used_kb = max(0, total_kb - avail_kb)
        
        total_mb = round(total_kb / 1024, 0)
        used_mb = round(used_kb / 1024, 0)
        percent = round((used_kb / total_kb) * 100.0, 1) if total_kb > 0 else 0.0
        return {"total_mb": int(total_mb), "used_mb": int(used_mb), "percent": percent}
    except Exception:
        return {"total_mb": 0, "used_mb": 0, "percent": 0.0}

def get_battery_info():
    capacity = 100
    status = "Discharging"
    
    # 1. Try termux-battery-status command with full paths
    termux_cmds = [
        "/data/data/com.termux/files/usr/bin/termux-battery-status",
        "termux-battery-status"
    ]
    for cmd in termux_cmds:
        try:
            proc = subprocess.run([cmd], capture_output=True, text=True, timeout=2)
            if proc.returncode == 0 and proc.stdout:
                b_data = json.loads(proc.stdout)
                capacity = b_data.get("percentage", 100)
                plugged = b_data.get("plugged", "UNPLUGGED")
                raw_status = b_data.get("status", "DISCHARGING")
                if plugged != "UNPLUGGED" or raw_status == "CHARGING":
                    status = "Charging"
                else:
                    status = "Discharging"
                return {"capacity": capacity, "status": status}
        except Exception:
            pass

    # 2. Check power_supply USB / AC online states
    usb_online = False
    for p in ["/sys/class/power_supply/usb/online", "/sys/class/power_supply/ac/online"]:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    if f.read().strip() == "1":
                        usb_online = True
            except Exception:
                pass

    # 3. Read battery capacity & status files (support bms & battery nodes)
    cap_paths = ["/sys/class/power_supply/battery/capacity", "/sys/class/power_supply/bms/capacity"]
    stat_paths = ["/sys/class/power_supply/battery/status", "/sys/class/power_supply/bms/status"]
    
    for p in cap_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    capacity = int(f.read().strip())
                    break
            except Exception:
                pass

    for p in stat_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    raw_stat = f.read().strip().capitalize()
                    if raw_stat in ["Charging", "Full"]:
                        status = "Charging"
                    elif raw_stat == "Discharging":
                        status = "Discharging"
                    elif usb_online:
                        status = "Charging"
                    break
            except Exception:
                pass
        
    return {"capacity": capacity, "status": status}

def get_disk_usage():
    try:
        st = os.statvfs("/")
        total_bytes = st.f_blocks * st.f_frsize
        free_bytes = st.f_bavail * st.f_frsize
        used_bytes = total_bytes - free_bytes
        
        total_gb = round(total_bytes / (1024**3), 1)
        used_gb = round(used_bytes / (1024**3), 1)
        percent = round((used_bytes / total_bytes) * 100.0, 1) if total_bytes > 0 else 0.0
        return {"total_gb": total_gb, "used_gb": used_gb, "percent": percent}
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "percent": 0.0}

def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            seconds = float(f.readline().split()[0])
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except Exception:
        return "Online"

def main():
    prev_idle, prev_total = get_cpu_times()
    
    while True:
        time.sleep(2)
        cpu_pct, prev_idle, prev_total = get_cpu_usage(prev_idle, prev_total)
        ram = get_ram_usage()
        battery = get_battery_info()
        disk = get_disk_usage()
        uptime_str = get_uptime()
        
        data = {
            "timestamp": int(time.time()),
            "cpu": {"percent": cpu_pct},
            "ram": ram,
            "battery": battery,
            "disk": disk,
            "uptime": uptime_str,
        }
        
        json_str = json.dumps(data)
        
        for path in TARGET_PATHS:
            try:
                parent = os.path.dirname(path)
                if os.path.exists(parent):
                    tmp_path = path + ".tmp"
                    with open(tmp_path, "w") as f:
                        f.write(json_str)
                    os.replace(tmp_path, path)
            except Exception:
                pass

if __name__ == "__main__":
    main()
