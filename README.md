# Android Tablet Server Infrastructure (`tablet-server-infra`)

GitOps infrastructure repository for the ARM64 Android Tablet Home Server hosting [`https://chozzen.xyz`](https://chozzen.xyz).

---

## 1. Directory Structure

```text
d:\server/
├── .gitignore               # Security exclusions (*.json secrets, cert.pem, *.db, *.log)
├── README.md                # Infrastructure documentation & runbook
├── configs/
│   ├── nginx/
│   │   └── default.conf     # Nginx reverse proxy & static site config (:8085)
│   └── cloudflare/
│       └── config.yml       # Cloudflare Tunnel ingress configuration template
├── scripts/
│   ├── start-server.sh      # Debian PRoot service startup script
│   ├── termux-boot-start-all.sh # Termux host boot hook (~/.termux/boot/start-all.sh)
│   └── deploy.sh            # GitOps sync, nginx config check & service reload
└── web/
    ├── index.html           # Main dashboard UI
    └── about.html           # Architecture & specs page
```

---

## 2. Security Rules

> [!CAUTION]
> **NEVER** commit secret key files or runtime database state to Git!

The following files are strictly ignored by `.gitignore`:
- `/root/.cloudflared/*.json` (Cloudflare Tunnel credentials)
- `/root/.cloudflared/cert.pem` (Origin certificate)
- `filebrowser.db` / `fb_internal.db` (FileBrowser sqlite databases)
- `*.log` (Service execution logs)

---

## 3. Quick Runbook & Boot Automation

### A. Termux Host Auto-Boot Setup
Copy or symlink the boot script to your Termux boot hooks:
```bash
mkdir -p ~/.termux/boot
cp /path/to/tablet-server-infra/scripts/termux-boot-start-all.sh ~/.termux/boot/start-all.sh
chmod +x ~/.termux/boot/start-all.sh
```

### B. Manual Service Execution (Debian PRoot)
```bash
proot-distro login debian
bash /path/to/tablet-server-infra/scripts/start-server.sh
```

### C. Deploying Updates (GitOps)
When you push changes to GitHub, deploy them on the server with:
```bash
bash /path/to/tablet-server-infra/scripts/deploy.sh
```

---

## 4. Architecture Overview

```text
[ Client Request (https://chozzen.xyz) ]
                │
                ▼
  [ Cloudflare Global Edge ]
                │
                │ (Outbound QUIC Tunnel)
                ▼
   [ Android Tablet (Termux) ]
                │
                ▼
     [ Debian PRoot Container ]
        ├── cloudflared (Tunnel Daemon)
        ├── Nginx Gateway (:8085)
        │     ├── /       ──> /var/www/dashboard/index.html
        │     ├── /about  ──> /var/www/dashboard/about.html
        │     └── /files/ ──> Reverse Proxy to 127.0.0.1:8080
        └── FileBrowser Binary (:8080)
```
