# Redmi Tablet Server Documentation: `chozzen.xyz`

Comprehensive technical documentation and runbook for the mobile home server hosted on an Android tablet using Termux, Debian PRoot, Nginx, File Browser, and Cloudflare Tunnels.

---

## 1. High-Level Architecture Overview

```
                        [ Internet / Any Browser ]
                                    │
                                    │ (HTTPS Port 443)
                                    ▼
                         [ Cloudflare Global Edge ]
                      (Nameservers: carol & howard)
                                    │
                                    │ (Encrypted QUIC / HTTP2 Tunnel)
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │ Android Tablet (Termux + Debian PRoot Environment)       │
       │                                                          │
       │  cloudflared tunnel daemon (Tunnel: redmi-tunnel)        │
       │                            │                             │
       │                            ▼                             │
       │              Nginx Gateway (127.0.0.1:8085)             │
       │                      │                 │                 │
       │                      ▼                 ▼                 │
       │            Static Sites            File Browser          │
       │      • /      -> Dashboard     (127.0.0.1:8080)          │
       │      • /about -> About Page       (/files/*)             │
       └──────────────────────────────────────────────────────────┘
```

---

## 2. Domain & Cloudflare Configuration

* **Domain Name:** `chozzen.xyz`
* **Registrar:** Hostingial (`manage.hostingial.com` / IntronNexus)
* **Nameserver Delegation (Required):**
  * `carol.ns.cloudflare.com`
  * `howard.ns.cloudflare.com`
* **Cloudflare Tunnel Name:** `redmi-tunnel`
* **Cloudflare Tunnel UUID:** `a80246c7-82b8-48fc-8324-1a5055dc0d1d`
* **Cloudflare DNS Records:**
  * **Type:** `CNAME`
  * **Name:** `chozzen.xyz` (or `@`)
  * **Target:** `a80246c7-82b8-48fc-8324-1a5055dc0d1d.cfargotunnel.com`
  * **Proxy Status:** `Proxied` (Orange Cloud enabled)

---

## 3. Network Ports & Internal Routing

| Component | Host / IP | Port | Scope | Description |
|---|---|---|---|---|
| **File Browser** | `127.0.0.1` | `8080` | Internal (Localhost) | Backend file management service |
| **Nginx Web Gateway** | `127.0.0.1` | `8085` | Internal (Localhost) | Unified reverse proxy & static site host |
| **Cloudflare Tunnel** | Outbound | 7844 / 443 | Outbound Only | Connects locally to `127.0.0.1:8085` and proxies traffic outbound via QUIC (No port forwarding needed) |

### Public Endpoints Routing (`https://chozzen.xyz`)

* `https://chozzen.xyz/` $\rightarrow$ Nginx root (`/var/www/dashboard`)
* `https://chozzen.xyz/about` $\rightarrow$ Nginx route (`/var/www/dashboard/about.html`)
* `https://chozzen.xyz/files/` $\rightarrow$ Reverse proxied to `http://127.0.0.1:8080` (File Browser)

---

## 4. Installed Packages & Software Stack

### Termux (Host Android Layer)
* `proot-distro` (Debian chroot/PRoot layer)
* `termux-boot` (Automatic startup on device power on)
* `curl`, `tar`, `git`

### Debian PRoot (Guest Environment)
* `nginx` (Reverse proxy and web server)
* `filebrowser` (Web-based file manager binary)
* `cloudflared` (Cloudflare Tunnel daemon, `arm64` deb/binary)
* `bind9-dnsutils` (`dig`, `nslookup` tools for DNS diagnosis)
* `whois` (Domain registry lookup)
* `procps` (`ps`, `pgrep`, `pkill`)

---

## 5. Important File Paths & Directory Locations

### Debian PRoot Root Filesystem (`/`)

* **Cloudflare Tunnel Configuration:**
  * `/root/.cloudflared/config.yml` (Tunnel routing configuration)
  * `/root/.cloudflared/a80246c7-82b8-48fc-8324-1a5055dc0d1d.json` (Tunnel credentials & secrets)
  * `/root/.cloudflared/cert.pem` (Origin certificate generated during `cloudflared login`)
  * `/root/.cloudflared/tunnel.log` (Runtime execution logs)

* **Nginx Configuration & Webroots:**
  * Configuration: `/etc/nginx/sites-available/default` (or `/etc/nginx/conf.d/chozzen.conf`)
  * Main Dashboard Root: `/var/www/dashboard/`
    * `/var/www/dashboard/index.html` (Dark themed dashboard UI)
    * `/var/www/dashboard/about.html` (About page)
  * Nginx Logs: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`

* **File Browser Storage & Data:**
  * Binary Location: `/usr/local/bin/filebrowser`
  * Database Path: `/root/.filebrowser/filebrowser.db`
  * Served Directory Root: Storage directory exposed via web (e.g. `/sdcard` or `/root/storage`)

### Termux Host Layer (`~`)

* **Boot Startup Script:**
  * `~/.termux/boot/start-all.sh`

---

## 6. Key Configuration Files

### A. Cloudflare Tunnel Configuration (`/root/.cloudflared/config.yml`)
```yaml
tunnel: a80246c7-82b8-48fc-8324-1a5055dc0d1d
credentials-file: /root/.cloudflared/a80246c7-82b8-48fc-8324-1a5055dc0d1d.json

ingress:
  - hostname: chozzen.xyz
    service: http://127.0.0.1:8085
  - service: http_status:404
```

### B. Nginx Virtual Host Configuration (`/etc/nginx/sites-available/default`)
```nginx
server {
    listen 8085;
    server_name chozzen.xyz 127.0.0.1 localhost;

    root /var/www/dashboard;
    index index.html;

    # Static Dashboard
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static About Page
    location /about {
        try_files /about.html =404;
    }

    # File Browser Reverse Proxy
    location /files/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 7. Service Management & Run Commands

### Entering the Environment
```bash
# From Termux shell into Debian:
proot-distro login debian
```

### Starting Services Manually (Inside Debian)
```bash
# 1. Start Nginx
service nginx start

# 2. Start File Browser (Background)
nohup filebrowser -r /root/storage -p 8080 -b /files > /var/log/filebrowser.log 2>&1 &

# 3. Start Cloudflare Tunnel (Background)
nohup cloudflared tunnel run redmi-tunnel > /root/.cloudflared/tunnel.log 2>&1 &
```

### Checking Running Processes
```bash
ps aux | grep -E 'nginx|filebrowser|cloudflared'
```

### Checking Tunnel Connectivity
```bash
cat /root/.cloudflared/tunnel.log | grep -i "registered"
```

---

## 8. Current Status & Action Required

* **Tablet & Local Stack:** 100% configured, listening, and validated.
* **Cloudflare Tunnel:** Active and registered to Cloudflare edge nodes (`bom` data centers).
* **Pending Blocker:** 
  * Registrar (`manage.hostingial.com`) failed to push the domain registration upstream to the CentralNic registry (`There is no external domain ID in mapping for internal domain ID 3563`).
  * Once the registrar support team completes the registrant profile verification and triggers provisioning, the nameservers (`carol.ns.cloudflare.com`, `howard.ns.cloudflare.com`) can be saved, and the domain will immediately become reachable globally.