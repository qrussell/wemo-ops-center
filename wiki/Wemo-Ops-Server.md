# Wemo Ops Server and Docker

**Wemo Ops Server** is the always-on part of Wemo Ops Center: it finds your devices, keeps their state up to date, runs your [schedules](Schedules.md), keeps device clocks in sync and serves the [mobile web app](Mobile-Web-App.md) on port **5050**. Run it on a Raspberry Pi, NAS, VM or home server and your schedules keep running when your computer is off.

It is the same program as the desktop app's background service, so everything here also applies to that service.

> **No login.** The server has no username or password and listens on all network interfaces. Keep it on your home network, never port-forward it, and use a VPN if you need it from outside. See [SECURITY.md](https://github.com/qrussell/wemo-ops-center/blob/main/SECURITY.md).

> This page replaces the old "Wemo Ops Server v1.0.2" page. That standalone server used port 5000 and the `wemo-web` service and is no longer maintained. If you still run it, switch to the `wemo-ops` package or Docker below.

## Ways to run it

| | Linux package | Docker |
|---|---|---|
| Install | `sudo apt install wemo-ops` / `sudo dnf install wemo-ops` from the [package repository](Installation.md#linux) | `docker compose up -d` |
| Also includes | The desktop app | Server only |
| Runs as | systemd service `wemo-ops-server` (as root) | Container `wemo-ops-server` (as `PUID`/`PGID`) |
| Data folder | `/var/lib/wemo-ops` | Volume `wemo-data`, mounted at `/data` |
| Updates | `apt upgrade` / `dnf upgrade` | `docker compose pull && docker compose up -d` |
| Architectures | x86-64, ARM64 | amd64, arm64 |

Both need to be on the **same network as your Wemo devices** (or able to route to their VLAN).

## Linux package

After installing, the service is already running:

```bash
systemctl status wemo-ops-server        # is it running?
sudo systemctl restart wemo-ops-server  # restart it
journalctl -u wemo-ops-server -f        # follow its log
```

Open `http://<server-ip>:5050` from any device on your network. The package opens the needed ports if `ufw` or `firewalld` is active:

| Port | Used for |
|---|---|
| 5050/tcp | Web app and API |
| 1900/udp | Device discovery (SSDP) |
| 49152–49155/tcp | Wemo device control |

To open them by hand:

```bash
# firewalld (Fedora, RHEL, Rocky)
sudo firewall-cmd --permanent --add-port=5050/tcp --add-port=1900/udp --add-port=49152-49155/tcp && sudo firewall-cmd --reload
# ufw (Ubuntu, Debian)
sudo ufw allow 5050/tcp && sudo ufw allow 1900/udp && sudo ufw allow 49152:49155/tcp
```

On a headless server you don't need the desktop app. To change the port or scan interval, add an override with `sudo systemctl edit wemo-ops-server`:

```ini
[Service]
Environment=PORT=5050
Environment=SCAN_INTERVAL=300
```

## Docker

```bash
curl -fsSLO https://raw.githubusercontent.com/qrussell/wemo-ops-center/main/universal-app/docker-compose.yml
docker compose up -d
```

The compose file:

```yaml
services:
  wemo-server:
    image: ghcr.io/qrussell/wemo-ops-server:latest
    container_name: wemo-ops-server
    restart: unless-stopped
    network_mode: host
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - PORT=5050
      - SCAN_INTERVAL=300
    volumes:
      - wemo-data:/data

volumes:
  wemo-data:
    name: wemo-data
```

* **`network_mode: host` is required.** Discovery uses broadcast and scans your subnets, which doesn't work through Docker's bridge network.
* **Linux host only.** Docker Desktop on Windows and macOS runs containers in a VM behind its own network, so devices aren't found. Use the desktop app on those systems.
* **Set `TZ`** to your [time zone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones), or schedules run in UTC.
* To pin a version instead of `latest`, use e.g. `ghcr.io/qrussell/wemo-ops-server:5.6.0`.
* Health check: the image checks `/api/status` every 30 seconds (`docker ps` shows `healthy`).
* Logs: `docker logs -f wemo-ops-server`, or `server.log` in the volume.
* Portainer, Unraid, Synology and similar: create the container with the same image, host networking, environment variables and a volume (or folder) mounted at `/data`.

## Settings

### Environment variables

| Variable | Default | What it does |
|---|---|---|
| `PORT` | `5050` | Port of the web app and API |
| `SCAN_INTERVAL` | `300` | Seconds between background scans of saved subnets |
| `TZ` | system time zone | Time zone for schedules (Docker) |
| `PUID`, `PGID` | `1000` | User and group the container runs as, and owner of `/data` (Docker) |
| `WEMO_OPS_SERVER_URL` | (none) | Desktop app only: use this server instead of the local service. Overrides the address in Settings |

### Settings in the web app

**Setup** in the [mobile web app](Mobile-Web-App.md) has the network list (add or delete saved subnets), **Deep-scan all connected networks every 5 min**, **Keep device clocks in sync (daily)** and **Sync Clocks Now**. The same settings are in the desktop app when it is connected to the server.

### Location for sunrise and sunset

A server on its own doesn't know where it is. Set its location once, or sunrise/sunset schedules won't run (see [Schedules](Schedules.md#sunrise-and-sunset)):

```bash
curl -X POST http://<server>:5050/api/settings -H "Content-Type: application/json" -d '{"lat": "40.71", "lng": "-74.01"}'
```

## Connect the desktop app to a server

Use your server's devices and schedules from the desktop app instead of running a second service on your computer.

1. In the desktop app, open **Settings → Background Service**.
2. Turn off **Use the background service on this computer**.
3. Enter the server's address, e.g. `homelab.local:5050` or `192.168.1.10` (`http://` and `:5050` are added if you leave them out).
4. Click **Save & Test**. The sidebar shows **CONNECTED** (or **UNREACHABLE** if it can't reach the server).

Now **Scan**, schedules, settings and the **Mobile App** QR code all use the server. Provisioning, Maintenance, schedules stored on the plug and Integrations still talk to devices directly from your computer, so the computer must be on the same network as the devices for those.

You can also start the app with the environment variable `WEMO_OPS_SERVER_URL=http://homelab.local:5050`.

## Data folders

Everything is stored as JSON files; there is no database.

| Where | Folder |
|---|---|
| Linux package service (root) | `/var/lib/wemo-ops` |
| Docker | `/data` (the `wemo-data` volume) |
| Windows (desktop app and its service) | `%APPDATA%\WemoOps` |
| macOS desktop app | `~/Library/Application Support/WemoOps` |
| macOS background service, and the server run by a normal user on Linux | `~/.local/share/WemoOps` |
| Linux desktop app | `~/.local/share/WemoOps` |

| File | What it holds | Written by |
|---|---|---|
| `settings.json` | Theme, scale, saved subnets, scan and clock options, remote server address, location (`lat`/`lng`) | Desktop app, service, web app (shared, merged) |
| `schedules.json` | Schedules run by Wemo Ops | Service / server |
| `devices.json` | Devices found, so they show up quickly after a restart | Service / server |
| `wifi_profiles.json` | Saved Wi-Fi profiles for the Provisioner, **including passwords** | Desktop app |
| `server.log` | Scans, schedule runs, errors | Service / server |
| `rules-backups/` | Zip backups of plug rules before every change | Desktop app |

### Back up and move to a new machine

1. Stop the server (`sudo systemctl stop wemo-ops-server`, `docker compose down`, or quit the app and service).
2. Copy `settings.json` and `schedules.json` (and `wifi_profiles.json` and `rules-backups/` from the desktop app if you want them). For Docker: `docker run --rm -v wemo-data:/data -v "$PWD":/backup alpine tar czf /backup/wemo-data.tgz -C /data .`
3. Put them in the data folder on the new machine and start it. Devices are found again by the first scan.

`wifi_profiles.json` holds your Wi-Fi password in plain text: keep backups private.

## Upgrading

* Linux package: `sudo apt update && sudo apt upgrade` or `sudo dnf upgrade`. The service restarts.
* Docker: `docker compose pull && docker compose up -d`. Your data stays in the volume.
* Settings and schedules are kept across upgrades. Read the [release notes](https://github.com/qrussell/wemo-ops-center/releases) for anything to do by hand.

## API

The web app talks to the server through a small HTTP API you can use too: [Server API](Server-API.md).
