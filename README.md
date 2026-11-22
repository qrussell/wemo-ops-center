# Wemo Ops Center
Welcome to Wemo Ops. We offer three ways to manage your smart home, depending on your needs. You can run the Desktop App for instant control on your workstation, deploy the Server for always-on automation, or use the MCP Server for AI assistant integration.

![Wemo Ops Center Dashboard](assets/wemo-ops.png)

![Version](https://img.shields.io/badge/version-v5.5.0-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Raspberry%20Pi-lightgrey)
[![MCP](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![AI Integration](https://img.shields.io/badge/AI-Integration-purple)](https://modelcontextprotocol.io)
![License](https://img.shields.io/badge/license-MIT-green)
---
**Resurrect your hardware.** The Wemo Cloud is dead, but your devices don't have to be.

Wemo Ops Center is a completely local, offline provisioning and automation suite for Belkin Wemo devices. It allows you to set up, control, automate, and factory reset Wemo plugs and switches without needing the official app or a cloud account.
* Alternative to the official Wemo App
* Provision Wemo devices with Python
* Belkin Wemo local control setup
* Wemo troubleshooting and Wi-Fi provisioning

> **New in v5.5.0:** device clock sync (fixes schedules stored on the plug running at the wrong time), a Windows build that no longer trips Microsoft Defender's machine-learning check, and a Homebridge installer that no longer hangs at "Starting Homebridge Service". See the [v5.5.0 release notes](release-notes/v5.5.0.md).
>
> v5.4.0 added a remote server option for the desktop app, Insight power readings, a Program Files installer for Windows and 175%/200% UI scaling ([release notes](release-notes/v5.4.0.md)).

## 🚀 Choose Your Edition

| Feature | 🖥️ Desktop App (GUI) | ⚙️ Server App (Headless) | 🤖 MCP Server (AI) |
| :--- | :--- | :--- | :--- |
| **Best For** | Casual users, quick toggling, setup | Power users, Home Labs, 24/7 automation | AI assistant users, MCP developers |
| **Interface** | Native Window (Python/Tkinter) | Web Dashboard (Browser-based) | AI Assistant (Natural language) |
| **Running State** | Runs only when open (its background service keeps schedules running) | Runs 24/7 as a background service | Launched on-demand by AI |
| **OS Support** | Windows, macOS (15+, Apple Silicon & Intel), Linux (Fedora/RHEL/Rocky, Ubuntu/Debian, Raspberry Pi OS) | Linux server, Raspberry Pi, Docker | Python 3.10+ (Any OS) |
| **Repository** | This repo | This repo | [apiarya/wemo-mcp-server](https://github.com/apiarya/wemo-mcp-server) |
| **Installation** | [Releases page](../../releases) or [`apt`/`dnf` repository](#-installation-linux) | [`apt`/`dnf` repository](#-installation-linux) or [Docker](#-docker) | `pip install wemo-mcp-server` |
| **Version** | v5.5.0 | v5.5.0 | v1.1.0 (Latest) |
| **Key Benefit** | **Zero Setup.** Just launch and click. | **Set & Forget.** Automation never stops. | **Universal Protocol.** Works with any MCP host. |

> **Note:** The MCP Server has been moved to its own dedicated repository at [apiarya/wemo-mcp-server](https://github.com/apiarya/wemo-mcp-server) for better discoverability and to follow MCP ecosystem best practices.

# Wemo Ops Center (Desktop)
## 📥 Download & Run

No Python installation required.

1. **Download:** Go to the [Releases Page](../../releases) and download the file for your system:

   | System | File |
   |---|---|
   | Windows 10/11 | `WemoOps_Setup_v5.5.0.exe` |
   | macOS 15 (Sequoia) or newer, Apple Silicon (M1–M4) | `WemoOps_5.5.0-1_macos15-apple-silicon.dmg` |
   | macOS 15 (Sequoia) or newer, Intel | `WemoOps_5.5.0-1_macos15-intel.dmg` |
   | macOS 26 (Tahoe), Apple Silicon | `WemoOps_5.5.0-1_macos26-apple-silicon.dmg` |
   | macOS 26 (Tahoe), Intel | `WemoOps_5.5.0-1_macos26-intel.dmg` |
   | Linux | Use the [package repository](#-installation-linux) (recommended), or download the `.deb` / `.rpm` |

2. **Provisioner:** Follow the on-screen instructions to scan for and configure your Wemo devices.
3. **Dashboard:** Scan your network, switch devices on and off, dim Dimmers, rename devices and get HomeKit codes. Each device shows its IP, MAC address and serial number; Insight plugs also show their power use.

Each release includes `SHA256SUMS.txt`. Verify a download with:
```bash
sha256sum -c SHA256SUMS.txt --ignore-missing
```

## ⚠️ "Windows protected your PC" Warning
When you launch `WemoOps.exe` for the first time, you may see a blue warning from Microsoft Defender SmartScreen.

**This is normal.** Because this is a free, open-source tool created by an independent developer, it does not have a paid digital signature (which costs hundreds of dollars a year).

**To run the app:**
1. Click **More info**.
2. Click **Run anyway**.

From v5.4.0 the installer asks for administrator rights and installs to `C:\Program Files\WemoOps` (you can pick another folder, or "install for me only"). Your settings and schedules stay in `%APPDATA%\WemoOps`. It also adds a Windows Firewall rule so phones on your home network can open the mobile web app.

If Microsoft Defender reports `Trojan:Win32/Bearfoos.A!ml` or a similar `!ml` detection, that is a false positive from its machine-learning model on unsigned Python apps (see [#33](https://github.com/qrussell/wemo-ops-center/issues/33)). Check your download against `SHA256SUMS.txt` on the release page. From v5.5.0 the Windows app is built as a folder of files instead of self-extracting `.exe` files, which is what that check reacted to; a Defender scan of the installed app comes back clean.

## 🍎 First Launch on macOS
Open the DMG and run **Install_WemoOps.command**, or drag **WemoOps** to Applications. If macOS asks whether to open an app from an unidentified developer, right-click (or Control-click) **WemoOps** → **Open** → **Open**. You only need to do this once.

# Screenshots of the Wemo Ops Center Desktop App

_Screenshots use simulated devices._

<table>
  <tr>
    <th width="50%">Light Mode</th>
    <th width="50%">Dark Mode</th>
  </tr>
  <tr>
    <td colspan="2"><b>Dashboard:</b> Every device on your networks, with power switches, a brightness slider for Dimmers and power readings for Insight plugs.</td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/desktop-dashboard-light.png" alt="Dashboard, light mode" width="100%"></td>
    <td><img src="assets/screenshots/desktop-dashboard-dark.png" alt="Dashboard, dark mode" width="100%"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Provisioner:</b> Find Wemo devices in setup mode and send them your Wi-Fi settings, no cloud needed.</td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/desktop-provisioner-light.png" alt="Provisioner, light mode" width="100%"></td>
    <td><img src="assets/screenshots/desktop-provisioner-dark.png" alt="Provisioner, dark mode" width="100%"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Automation:</b> Fixed-time and sunrise/sunset schedules, run by the background service.</td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/desktop-automation-light.png" alt="Automation, light mode" width="100%"></td>
    <td><img src="assets/screenshots/desktop-automation-dark.png" alt="Automation, dark mode" width="100%"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Maintenance:</b> Reset a device's data or Wi-Fi, factory reset it, or set its clock.</td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/desktop-maintenance-light.png" alt="Maintenance, light mode" width="100%"></td>
    <td><img src="assets/screenshots/desktop-maintenance-dark.png" alt="Maintenance, dark mode" width="100%"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Integrations:</b> Generate a Homebridge/HOOBS config and install the Homebridge compatibility layer.</td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/desktop-integrations-light.png" alt="Integrations, light mode" width="100%"></td>
    <td><img src="assets/screenshots/desktop-integrations-dark.png" alt="Integrations, dark mode" width="100%"></td>
  </tr>
  <tr>
    <td colspan="2"><b>Settings:</b> Appearance, UI scaling up to 200%, network scanning, daily clock sync and a remote server.</td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/desktop-settings-light.png" alt="Settings, light mode" width="100%"></td>
    <td><img src="assets/screenshots/desktop-settings-dark.png" alt="Settings, dark mode" width="100%"></td>
  </tr>
</table>

# Screenshots of the Wemo Ops Mobile App

The mobile web app is served by the background service (desktop app) or Wemo Ops Server. Open it from the **Mobile App** QR code in the desktop app, or at `http://<computer-or-server-ip>:5050`.

<table>
  <tr>
    <th width="33%">Home</th>
    <th width="33%">Rules</th>
    <th width="33%">Setup</th>
  </tr>
  <tr>
    <td><img src="assets/screenshots/web-devices-light.png" alt="Mobile web app, devices, light mode" width="100%"></td>
    <td><img src="assets/screenshots/web-rules-light.png" alt="Mobile web app, rules, light mode" width="100%"></td>
    <td><img src="assets/screenshots/web-setup-light.png" alt="Mobile web app, setup, light mode" width="100%"></td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/web-devices-dark.png" alt="Mobile web app, devices, dark mode" width="100%"></td>
    <td><img src="assets/screenshots/web-rules-dark.png" alt="Mobile web app, rules, dark mode" width="100%"></td>
    <td><img src="assets/screenshots/web-setup-dark.png" alt="Mobile web app, setup, dark mode" width="100%"></td>
  </tr>
</table>

---
**Go to the [Releases Page](../../releases) and download.**
## 🚀 Key Features

### 1. 📡 Universal Provisioner
* **No Cloud Required:** Connect directly to a new or reset Wemo device's Wi-Fi (`Wemo.Mini.xxx`) and push your Wi-Fi credentials instantly.
* **Smart Encryption Loop:** Automatically detects and applies the correct encryption method (old vs. new firmware) to ensure successful setup.
* **Profile Manager:** Save your Wi-Fi SSID and Password to quickly provision multiple devices in seconds.
* **Automatic Pick-up:** After a successful setup, the app rescans so the device appears on the Dashboard once it joins your network.

### 2. 🎛️ Network Dashboard & VLAN Support
* **Fast, Complete Discovery:** Broadcast (SSDP) discovery shows devices within seconds; a deep scan then finds devices broadcast can't reach.
* **All Your Networks:** Every network your computer is connected to (e.g. Ethernet and an IoT Wi-Fi) is detected and scanned automatically. VPN, virtual machine and container adapters are skipped.
* **VLAN/Subnet Support:** Perfect for IoT setups. Save additional subnets (e.g. `192.168.20.0/23`) with the **Save** button and they are scanned too; the selected subnet is scanned first.
* **Smart Deduplication:** Tracks devices by their unique device ID, so devices that share a name (e.g. several "Wemo Mini") are all listed, labelled with the end of their MAC address.
* **Insight Power Readings:** Insight plugs show their current draw (W) and today's energy use (kWh), on the Dashboard and in the mobile web app.

### 3. 🛠️ Maintenance Tools
Advanced tools to manage device health directly from the app:
* **Clear Personal Info:** Removes custom names, icons, and rules.
* **Clear Wi-Fi:** Wipes network credentials to return the device to "Setup Mode" (Flashing Amber/Blue).
* **Factory Reset:** Performs a full "Out of Box" wipe.
* **Device Clock:** Sets a device's clock and time zone from your computer. Use it when schedules or away mode stored on the device itself (for example, made in the old Wemo app) run at the wrong time. Pick a device in the **Device** list and click **Sync Selected Device**, or click **Sync All Devices**. To keep clocks right, turn on **Settings → Keep device clocks in sync (daily)**.

Choose the device in the **Device** list at the top of the page; all the buttons act on it. If no Wemo devices have been found yet, the app says so instead of acting.

### 4. ☀️ Solar Automation Scheduler
* **Local Automation:** Runs on your computer as a background service.
* **Solar Engine:** Automatically detects your latitude/longitude to trigger lights at **Sunrise** or **Sunset**.
* **Fixed Schedules:** Set standard time-based schedules (e.g., "Turn ON at 18:00").
* **Pick the Days:** Each schedule runs on the days you tick, with an optional offset before or after sunrise/sunset.

### 5. 📱 Mobile Web App
* **Scan the QR Code:** Connect to the mobile web app with your phone or tablet and control your Wemo devices.
* **Local Control:** The app runs on your local network and connects directly to Wemo devices without the cloud.
* **Manage Schedules:** Manage schedules from the mobile web app, solar automation, or time-based schedules.
* **Dimmers and Insight Plugs:** Set brightness with a slider; see an Insight plug's current draw and today's energy use.
* **Device Clocks:** **Setup → Sync Clocks Now** sets the clock on every device, and **Keep device clocks in sync (daily)** does it once a day.
* **Remote Server:** Already running Wemo Ops Server on a Raspberry Pi, NAS or in Docker? In the desktop app, go to **Settings → Background Service**, turn off "Use the background service on this computer" and enter the server's address (e.g. `homelab.local:5050`). Schedules, scans and the QR code then use that server. The server has no login: keep it on your home network and don't port-forward it.

### 6. 🏠 Homebridge & HOOBS Integration
* **Config Generator:** Click **Scan & Generate Config** to get the `BelkinWeMo` platform block for your Homebridge/HOOBS `config.json`, listing the devices the app found.
* **Compatibility Layer Installer:** **Install Compatibility Layer** installs Homebridge with its web UI (port `8581`) and the `homebridge-wemo` and `homebridge-alexa` plugins, and sets Homebridge up as a service, so Alexa and Google Home can reach your Wemo devices. If the Homebridge service doesn't start within 3 minutes, the installer stops waiting and tells you how to check its log instead of hanging.

### 7. ⚙️ Settings
* **Appearance:** Light, Dark or System mode, and UI scaling from 80% to 200% for high-resolution screens.
* **Network Scanning:** Optionally deep-scan all connected networks every 5 minutes.
* **Device Clock Sync:** Keep every device's clock in sync, once a day.
* **Background Service:** Use the service on this computer, or a Wemo Ops Server elsewhere (see *Remote Server* above).

### ⚠️ Disclaimer
This project is an independent open-source tool and is not affiliated with, endorsed by, or associated with Belkin International, Inc. "Wemo" is a trademark of Belkin International, Inc.

## 🖥️ Option 1: The Desktop App
(Recommended for most users)

* **Wemo Ops Center (Desktop)** is a native application that lives on your computer. It allows you to scan your network, toggle devices on/off instantly, and manage device firmware without needing a dedicated server.

### Why use this?

* **Instant Control:** No web browser needed; just open the app.

* **Portable:** Run it on your laptop and control devices wherever you are on the network.

* **Visual Setup:** Easy-to-use interface for renaming and configuring devices.

* **Multi-Platform Support:** Run the app on Windows, macOS, or Linux (including Raspberry Pi).

## 📦 Installation (Linux)

The recommended way to install on Linux is the **qrussell package repository**. Add it once, and `apt` / `dnf` install and update Wemo Ops like any other package. It provides x86-64 packages and, from v5.3.1, ARM64 packages (Raspberry Pi 4/5 with 64-bit Raspberry Pi OS).

The `wemo-ops` package contains the **Desktop App and the Automation Server**. The server is installed as the `wemo-ops-server` systemd service and starts automatically, with the web dashboard on port `5050`.

### Ubuntu / Debian / Linux Mint / Raspberry Pi OS (`apt`)

**1. Add the repository** (signed; you only do this once):
```bash
sudo curl -fsSL https://qrussell.github.io/qrussell-repo/deb/qrussell-repo.gpg -o /usr/share/keyrings/qrussell-repo.gpg
```
```bash
echo "deb [signed-by=/usr/share/keyrings/qrussell-repo.gpg] https://qrussell.github.io/qrussell-repo/deb ./" | sudo tee /etc/apt/sources.list.d/qrussell.list
```
Optional: check that the key's fingerprint is `9994A9EB39EB3C101C949FB2012BA14E0FE3A355`:
```bash
gpg --show-keys /usr/share/keyrings/qrussell-repo.gpg
```

**2. Install:**
```bash
sudo apt update && sudo apt install wemo-ops
```

### Fedora / RHEL / Rocky / AlmaLinux (`dnf`)

**1. Add the repository** (you only do this once). Use the command for your `dnf` version:

Fedora 41 and newer (dnf5):
```bash
sudo dnf config-manager addrepo --from-repofile=https://qrussell.github.io/qrussell-repo/qrussell.repo
```
RHEL / Rocky / AlmaLinux 9 and Fedora 40 or older (dnf 4):
```bash
sudo dnf install -y 'dnf-command(config-manager)' && sudo dnf config-manager --add-repo https://qrussell.github.io/qrussell-repo/qrussell.repo
```
<details>
<summary>Or add the repository file by hand (any dnf version)</summary>

```bash
sudo tee /etc/yum.repos.d/qrussell.repo <<'EOF'
[qrussell-tools]
name=Quentin Russell's Tools
baseurl=https://qrussell.github.io/qrussell-repo/rpm/
enabled=1
gpgcheck=0
EOF
```
</details>

**2. Install:**
```bash
sudo dnf install wemo-ops
```

### Updating
Updates arrive with your normal system updates. A new release reaches the repository within a few hours of being published:
```bash
sudo apt update && sudo apt upgrade   # Ubuntu / Debian
```
```bash
sudo dnf upgrade                      # Fedora / RHEL / Rocky
```

### Without the repository
Download the `.deb` or `.rpm` for your architecture from the [Releases Page](../../releases) and install it with `sudo apt install ./wemo-ops_*.deb` or `sudo dnf install ./wemo-ops-*.rpm` (dependencies are installed automatically). You won't receive updates automatically this way.

Repository details and other packages: [qrussell-repo](https://github.com/qrussell/qrussell-repo).

## ⚙️ Option 2: The Automation Server
(For Homelabs & Always-On Automation)

Wemo Ops Server is a lightweight, headless service designed to run on a Raspberry Pi, VM, or Home Server. It provides a Web UI accessible from any device on your network and executes automation schedules even when your computer is turned off.

### Supported deployments:
* **Linux package (recommended):** install `wemo-ops` from the [package repository](#-installation-linux). It includes the always-on server as the `wemo-ops-server` systemd service. Open `http://<server-ip>:5050` from any device on your network.
* **Docker:** see [Docker](#-docker) below.
* More details: [Wemo Ops Server Wiki Page](https://github.com/qrussell/wemo-ops-center/wiki/Wemo-Ops-Server)

The repository also has a separate, headless-only `wemo-ops-server` package (v1.0.2, from the older standalone server). It does not include the v5.3.x discovery improvements; prefer the `wemo-ops` package or Docker.

<table>
  <tr>
    <th width="33%">Dashboard</th>
    <th width="33%">Automation</th>
    <th width="33%">Settings</th>
  </tr>
  <tr>
    <td><img src="assets/screenshots/web-devices-dark.png" alt="Server web dashboard" width="100%"></td>
    <td><img src="assets/screenshots/web-rules-dark.png" alt="Server automation rules" width="100%"></td>
    <td><img src="assets/screenshots/web-setup-dark.png" alt="Server settings" width="100%"></td>
  </tr>
</table>

### Why use this?

* **24/7 Reliability:** Your automation schedules (e.g., "Lights on at sunset") run even if your laptop is asleep.

* **Any Device Access:** Control your home from your phone, tablet, or another PC via the Web Dashboard.

* **Low Resource Usage:** Optimized to run silently in the background.

* **Device Clocks Kept Right:** Turn on *Keep device clocks in sync (daily)* in Settings and the server sets each device's clock and time zone once a day, so schedules stored on the devices themselves run on time.

* **Network Scanning Your Way:** Connected networks are deep-scanned at startup and when you press **Scan**; saved subnets are re-scanned every 5 minutes. Turn on *Deep-scan all connected networks every 5 min* in Settings for continuous scanning of every network.

### 🐳 Docker

The server image `ghcr.io/qrussell/wemo-ops-server` is published with every release for **amd64 and arm64** (Raspberry Pi).

```bash
curl -fsSLO https://raw.githubusercontent.com/qrussell/wemo-ops-center/main/universal-app/docker-compose.yml
```
```bash
docker compose up -d
```

Then open `http://<host-ip>:5050`. Settings, schedules and the device cache are kept in the `wemo-data` volume. Edit `TZ` in `docker-compose.yml` to your time zone so schedules fire at local time.

**Run it on a Linux host** (Raspberry Pi, NAS, VM, server) with `network_mode: host`, as in the compose file: discovery needs direct access to your network. Docker Desktop on Windows/macOS routes container traffic through its own proxy and misses devices; use the desktop app there.

## 🤖 Option 3: MCP Server
(For AI Assistant Integration)

> **🏠 New Home:** The MCP Server now lives in a dedicated repository at [apiarya/wemo-mcp-server](https://github.com/apiarya/wemo-mcp-server)

[![PyPI version](https://badge.fury.io/py/wemo-mcp-server.svg)](https://pypi.org/project/wemo-mcp-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

The **WeMo MCP Server** (v1.1.0) enables natural language control of your WeMo devices through any application that supports the Model Context Protocol (MCP). Works with AI assistants like Claude Desktop, VS Code with GitHub Copilot, Cursor, and other MCP-compatible tools.

![Claude Desktop controlling WeMo devices](mcp/assets/claude-example.png)

### Why use this?

* **Talk to Your Devices:** Just say "Turn on the office light" or "What devices are on my network?"

* **No GUI Needed:** Control everything through your AI assistant conversations.

* **Universal Protocol:** Works with any MCP host application, not limited to specific tools.

* **Production Ready:** v1.1.0 stable release with comprehensive documentation.

See the **[Wemo MCP Server Documentation](https://github.com/apiarya/wemo-mcp-server)** for full setup and features.

## 🤝 Better Together: The Hybrid Approach
"Can I use multiple options?" Yes! All three work together seamlessly.

* Use the **Server** to handle the "boring stuff": keeping schedules running, monitoring device health, and providing a dashboard for your phone.

* Use the **Desktop App** on your workstation for rapid control while you work, or for deep configuration tasks like firmware updates or bulk provisioning.

* Use the **MCP Server** with your AI assistant for quick natural language queries and control during development or daily work.

* All applications can run on the same network and control the same devices simultaneously without conflict.

## 🛠️ For Maintainers
Releases are built automatically by GitHub Actions. See [RELEASING.md](RELEASING.md).
