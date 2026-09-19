# Context & Handover Document: Android Tablet Home Server

**Domain:** `chozzen.xyz`  
**Host Hardware:** Android Tablet (ARM64)  
**Primary Execution Layer:** Termux (`$`) + Debian PRoot (`root@localhost:~#`)  
**Networking / Edge:** Cloudflare Tunnel (`redmi-tunnel`) + Cloudflare DNS  

---

## 1. Executive Summary & Current Status

- **Status:** **LIVE & WORKING** (HTTPS active via Cloudflare edge).
- **Public Entrypoint:** `https://chozzen.xyz`
- **DNS / Registry Delegation:** Successfully delegated from registrar (**Hostingial** / CentralNic) to Cloudflare Nameservers:
  - `carol.ns.cloudflare.com`
  - `howard.ns.cloudflare.com`
- **Local Origin Services:**
  - **Nginx** listening on `127.0.0.1:8085` (serves landing page & acts as reverse proxy).
  - **FileBrowser** listening on `127.0.0.1:8080` (mounted at subpath `/files/`).
  - **cloudflared** running outbound tunnel `redmi-tunnel` (`a80246c7-82b8-48fc-8324-1a5055dc0d1d`), proxying incoming Cloudflare requests directly to `127.0.0.1:8085`.
- **Current Objective / Work-in-Progress:** 
  Setting up a **GitOps / GitHub-managed repository** workflow to track, version, and deploy all configuration files (Nginx, Cloudflare ingress configs, static UI/HTML, startup scripts, and Termux boot hooks) with auto-reload capabilities.

---

## 2. Infrastructure & Architectural Blueprint

```
[ Internet Client ]
       │ (HTTPS 443)
       ▼
[ Cloudflare Global Anycast Edge ]
  • carol.ns.cloudflare.com / howard.ns.cloudflare.com
  • CNAME chozzen.xyz -> <tunnel-uuid>.cfargotunnel.com
       │
       │ (Outbound QUIC Tunnel - No open router ports / no NAT issues)
       ▼
[ Android Tablet - Termux Layer ]
  • Wake lock enabled (`termux-wake-lock`)
  • OpenSSH server on port `8022`
       │
       ▼
[ Debian PRoot Container (`proot-distro login debian`) ]
  ├── cloudflared daemon (tunnel: `redmi-tunnel`)
  │         │ (proxies HTTP traffic)
  │         ▼
  ├── Nginx Gateway (:8085)
  │     ├── Path `/`      ──> Static UI (`/var/www/html` or `/var/www/dashboard`)
  │     ├── Path `/about` ──> `/about.html`
  │     └── Path `/files/`──> Reverse proxy to `http://127.0.0.1:8080/`
  └── FileBrowser binary (:8080)
```

---

## 3. Environment & Runtime Peculiarities

When issuing commands or writing scripts in this environment, follow these runtime constraints:

1. **PRoot Netlink Socket Restriction:**  
   Standard networking tools like `ss -tulpn`, `netstat`, and `cat /proc/net/tcp` fail with `Permission denied` due to Android non-root security boundaries.  
   - **How to test ports:** Use application-level testing:
     - `curl -I http://127.0.0.1:8085` (Nginx)
     - `curl -I http://127.0.0.1:8080` (FileBrowser)
     - `ps aux | grep -E 'nginx|filebrowser|cloudflared'`

2. **Termux vs Debian Separation:**
   - **Termux (Host):** Manages Android wake lock, battery lifecycle, and OpenSSH on port `8022`.
   - **Debian PRoot (Guest):** Contains `nginx`, `cloudflared`, `filebrowser`, `git`, and Python/Node if installed.

3. **Background Daemon Persistence:**  
   There is no `systemd` in PRoot. Services must be managed via SysV init (`service nginx start`) or `nohup` background jobs.

---

## 4. Key Paths, Files, and Identifiers

| Item | Path / Value | Notes |
| :--- | :--- | :--- |
| **Domain** | `chozzen.xyz` | SSL termination handled at Cloudflare Edge |
| **Tunnel Name** | `redmi-tunnel` | Active Cloudflare Named Tunnel |
| **Tunnel UUID** | `a80246c7-82b8-48fc-8324-1a5055dc0d1d` | Target for CNAME record |
| **Tunnel Ingress Config** | `/root/.cloudflared/config.yml` | Maps `chozzen.xyz` to `http://127.0.0.1:8085` |
| **Tunnel Credentials** | `/root/.cloudflared/<UUID>.json` | **SECRET** - Do NOT commit to Git |
| **Tunnel Cert** | `/root/.cloudflared/cert.pem` | **SECRET** - Origin certificate |
| **Nginx Main Config** | `/etc/nginx/sites-available/default` | Proxies static web + `/files/` |
| **Web Root** | `/var/www/html/` (or `/var/www/dashboard/`) | Contains `index.html`, UI assets |
| **FileBrowser DB** | `/data/data/com.termux/files/home/.config/filebrowser/filebrowser.db` | Local state database |
| **Tunnel Logs** | `/var/log/cloudflared.log` | Check via `tail -f` for diagnostics |

---

## 5. Ongoing Activity: GitOps Repository Plan

The immediate task is structuring a Git repository (`tablet-server-infra`) on GitHub to maintain configs and enable one-command updates.

### Target Directory Layout
```text
tablet-server-infra/
├── .gitignore               # Excludes *.json, cert.pem, *.db, *.log
├── README.md
├── scripts/
│   ├── start-server.sh      # Starts nginx, filebrowser, and cloudflared
│   └── deploy.sh            # Runs `git pull`, checks `nginx -t`, reloads nginx
├── configs/
│   ├── nginx/
│   │   └── default.conf     # Virtual host configuration
│   └── cloudflare/
│       └── config.yml       # Ingress rules template (sanitized)
└── web/
    ├── index.html           # Dashboard UI
    └── about.html           # About page
```

### Critical Security Rule
Never push `.json` credentials or `cert.pem` to the GitHub repository.

---

## 6. Standard Runbook / Quick Commands

```bash
# 1. Enter the Debian container
proot-distro login debian

# 2. Check running server processes
ps aux | grep -E 'nginx|filebrowser|cloudflared'

# 3. Quick test local endpoints
curl -I http://127.0.0.1:8085
curl -I http://127.0.0.1:8080

# 4. Restart Cloudflare Tunnel manually if disconnected
nohup cloudflared tunnel run redmi-tunnel > /var/log/cloudflared.log 2>&1 &

# 5. Check tunnel status
tail -n 20 /var/log/cloudflared.log
```