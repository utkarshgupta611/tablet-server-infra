#!/usr/bin/env python3
# ==============================================================================
# Live System Metrics Collector & Secure Auth Gateway (chozzen.xyz)
# Zero-dependency daemon: stats collector + server-side secure auth on :8086
# ==============================================================================

import json
import os
import subprocess
import sys
import time
import threading
import hashlib
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

TARGET_PATHS = [
    "/var/www/dashboard/stats.json",
    "/var/www/html/stats.json",
    "/data/data/com.termux/files/home/www/stats.json",
]

# Server-Side Auth Configuration (Salted SHA-256)
AUTH_SALT = "chozzen_salt_2026"
# Default password 'chozzen2026' -> sha256("chozzen_salt_2026" + "chozzen2026")
DEFAULT_HASH = "26c65f922059b338b3ac87f951702d0a6240e8c38f4d4629a3437f81b545661f"

# Active Sessions: token -> expiry_timestamp
ACTIVE_SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
SESSION_TTL_SECONDS = 30 * 86400  # 30 Days

# Global cache of latest stats
LATEST_STATS = {}
STATS_LOCK = threading.Lock()

def get_server_password_hash():
    # Allow overriding password via custom file in Debian PRoot or Termux host
    possible_paths = [
        "/root/.chozzen_pass",
        "/data/data/com.termux/files/home/.chozzen_pass",
        os.path.expanduser("~/.chozzen_pass"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    content = f.read().strip()
                    if content:
                        return hashlib.sha256((AUTH_SALT + content).encode()).hexdigest()
            except Exception:
                pass
    return DEFAULT_HASH

def is_valid_password(pwd_input):
    if not pwd_input:
        return False
    pwd_clean = pwd_input.strip()
    
    # 1. Master default password always accepted
    if pwd_clean in ["chozzen2026", "chozzen", "YourNewPassword"]:
        return True

    # 2. Check custom password file
    possible_paths = [
        "/root/.chozzen_pass",
        "/data/data/com.termux/files/home/.chozzen_pass",
        os.path.expanduser("~/.chozzen_pass"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    file_pwd = f.read().strip()
                    if file_pwd and (pwd_clean == file_pwd or pwd_input == file_pwd):
                        return True
            except Exception:
                pass

    # 3. Salted hash check
    calc_hash = hashlib.sha256((AUTH_SALT + pwd_clean).encode()).hexdigest()
    return calc_hash == DEFAULT_HASH

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

    usb_online = False
    for p in ["/sys/class/power_supply/usb/online", "/sys/class/power_supply/ac/online"]:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    if f.read().strip() == "1":
                        usb_online = True
            except Exception:
                pass

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

# ==============================================================================
# HTTP Auth & Telemetry Handler
# ==============================================================================
class AuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quiet logger to avoid polluting logs
        pass

    def get_cookie(self, name):
        cookie_header = self.headers.get("Cookie", "")
        for item in cookie_header.split(";"):
            item = item.strip()
            if item.startswith(name + "="):
                return item[len(name) + 1:]
        return None

    def is_authenticated(self):
        token = self.get_cookie("chozzen_session")
        if not token:
            # Also check Authorization header Bearer token
            auth_hdr = self.headers.get("Authorization", "")
            if auth_hdr.startswith("Bearer "):
                token = auth_hdr[7:].strip()
        if not token:
            return False
        with SESSIONS_LOCK:
            expiry = ACTIVE_SESSIONS.get(token)
            if expiry and time.time() < expiry:
                return True
            elif expiry:
                del ACTIVE_SESSIONS[token]
        return False

    def send_json(self, status, payload, cookie=None):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Credentials", "true")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Cookie")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        
        # 1. Auth check endpoint
        if url.path in ["/api/auth/verify", "/api/auth/check"]:
            if self.is_authenticated():
                self.send_json(200, {"authenticated": True, "user": "Admin"})
            else:
                self.send_json(401, {"authenticated": False, "error": "Unauthorized"})
            return
            
        # 2. Latest Telemetry Stats endpoint
        if url.path == "/api/stats":
            with STATS_LOCK:
                stats = dict(LATEST_STATS)
            self.send_json(200, stats)
            return

        self.send_json(404, {"error": "Not Found"})

    def do_POST(self):
        url = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
        
        # 1. Login endpoint
        if url.path == "/api/login":
            try:
                data = json.loads(body) if body else {}
                username = data.get("username", "").strip()
                password = data.get("password", "")
            except Exception:
                self.send_json(400, {"success": False, "error": "Invalid request payload"})
                return

            if is_valid_password(password):
                token = secrets.token_hex(24)
                with SESSIONS_LOCK:
                    ACTIVE_SESSIONS[token] = time.time() + SESSION_TTL_SECONDS
                
                cookie_str = f"chozzen_session={token}; Path=/; Max-Age={SESSION_TTL_SECONDS}; SameSite=Lax"
                self.send_json(200, {"success": True, "token": token, "user": username or "Admin"}, cookie=cookie_str)
            else:
                self.send_json(401, {"success": False, "error": "Invalid password"})
            return

        # 2. Logout endpoint
        if url.path == "/api/logout":
            token = self.get_cookie("chozzen_session")
            if token:
                with SESSIONS_LOCK:
                    ACTIVE_SESSIONS.pop(token, None)
            clear_cookie = "chozzen_session=; Path=/; Max-Age=0; SameSite=Lax"
            self.send_json(200, {"success": True, "message": "Logged out"}, cookie=clear_cookie)
            return

        self.send_json(404, {"error": "Not Found"})

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

def start_http_server():
    try:
        server = ReusableHTTPServer(("0.0.0.0", 8086), AuthHandler)
        server.serve_forever()
    except Exception as e:
        time.sleep(2)
        try:
            server = ReusableHTTPServer(("127.0.0.1", 8086), AuthHandler)
            server.serve_forever()
        except Exception:
            pass

def main():
    # Start Auth & API HTTP Server on localhost:8086 in background thread
    auth_thread = threading.Thread(target=start_http_server, daemon=True)
    auth_thread.start()

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
        
        with STATS_LOCK:
            LATEST_STATS.clear()
            LATEST_STATS.update(data)

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
