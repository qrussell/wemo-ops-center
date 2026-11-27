# Installation

Wemo Ops Center runs on **Windows 10/11**, **macOS 15 (Sequoia) or newer** (Apple Silicon and Intel), **Linux** (Ubuntu/Debian/Mint/Raspberry Pi OS, Fedora/RHEL/Rocky/AlmaLinux, x86-64 and ARM64) and in **Docker** (server only). No Python installation is needed for the packaged versions.

Download everything from the [latest release](https://github.com/qrussell/wemo-ops-center/releases/latest). Each release has a `SHA256SUMS.txt`; check a download with:

```bash
sha256sum -c SHA256SUMS.txt --ignore-missing
```

On Windows PowerShell: `Get-FileHash .\WemoOps_Setup_v5.6.0.exe` and compare it with the line in `SHA256SUMS.txt`.

## Windows

1. Download `WemoOps_Setup_vX.Y.Z.exe` and run it.
2. If you see **"Windows protected your PC"** (SmartScreen), click **More info → Run anyway**. The app is free and unsigned, so Windows doesn't recognise the publisher.
3. The installer asks for administrator rights and installs to `C:\Program Files\WemoOps`. You can choose another folder or "install for me only".
4. Options in the installer:
   * **Automatically start background service** (on by default): starts the service that runs your schedules and the mobile web app when you sign in.
   * **Allow phones on my home network to open the mobile web app**: adds a Windows Firewall rule for private networks. Without it, phones can't reach port 5050.
   * **Desktop icon** (off by default).
5. Your settings, Wi-Fi profiles and schedules are kept in `%APPDATA%\WemoOps`, so upgrading or reinstalling keeps them.

To upgrade, run the new installer over the old one. Installs from before v5.4.0 (in your user folder) are moved to Program Files automatically.

If Microsoft Defender reports `Trojan:Win32/Bearfoos.A!ml` or another `!ml` detection on an old version, that is a false positive ([issue #33](https://github.com/qrussell/wemo-ops-center/issues/33)). From v5.5.0 the app is built in a way that Defender's scan passes.

## macOS

1. Download the DMG that matches your Mac:

   | Mac | File |
   |---|---|
   | macOS 15 or newer, Apple Silicon (M1 and later) | `WemoOps_X.Y.Z-1_macos15-apple-silicon.dmg` |
   | macOS 15 or newer, Intel | `WemoOps_X.Y.Z-1_macos15-intel.dmg` |
   | macOS 26 (Tahoe), Apple Silicon | `WemoOps_X.Y.Z-1_macos26-apple-silicon.dmg` |
   | macOS 26 (Tahoe), Intel | `WemoOps_X.Y.Z-1_macos26-intel.dmg` |

2. Open the DMG and double-click **Install_WemoOps.command**. It copies the app to Applications, installs the background service to `~/Library/Application Support/WemoOps` and registers it to start when you log in (`~/Library/LaunchAgents/com.qrussell.wemoops.plist`).
   You can also just drag **WemoOps** to Applications, but then the background service isn't installed and schedules only run while the app is open.
3. If macOS says the app is from an unidentified developer, right-click (or Control-click) **WemoOps** → **Open** → **Open**. You only need to do this once.

## Linux

The recommended way is the signed **qrussell package repository**: add it once and `apt`/`dnf` keep Wemo Ops up to date with the rest of your system. The `wemo-ops` package contains the desktop app and the server, which runs as the `wemo-ops-server` systemd service on port 5050 and starts automatically.

### Ubuntu / Debian / Linux Mint / Raspberry Pi OS

```bash
sudo curl -fsSL https://qrussell.github.io/qrussell-repo/deb/qrussell-repo.gpg -o /usr/share/keyrings/qrussell-repo.gpg
echo "deb [signed-by=/usr/share/keyrings/qrussell-repo.gpg] https://qrussell.github.io/qrussell-repo/deb ./" | sudo tee /etc/apt/sources.list.d/qrussell.list
sudo apt update && sudo apt install wemo-ops
```

The key's fingerprint is `9994A9EB39EB3C101C949FB2012BA14E0FE3A355` (check with `gpg --show-keys /usr/share/keyrings/qrussell-repo.gpg`). Raspberry Pi needs a 64-bit OS (Pi 4 or 5).

### Fedora / RHEL / Rocky / AlmaLinux

Fedora 41 and newer:

```bash
sudo dnf config-manager addrepo --from-repofile=https://qrussell.github.io/qrussell-repo/qrussell.repo
sudo dnf install wemo-ops
```

RHEL / Rocky / AlmaLinux 9 and Fedora 40 or older:

```bash
sudo dnf install -y 'dnf-command(config-manager)' && sudo dnf config-manager --add-repo https://qrussell.github.io/qrussell-repo/qrussell.repo
sudo dnf install wemo-ops
```

### After installing

* Start the desktop app from your applications menu, or run `wemo-ops`.
* The server is already running: open `http://<this-computer's-IP>:5050` from your phone.
* If `ufw` or `firewalld` is active, the package opens port 5050/tcp (web app), 1900/udp (discovery) and 49152–49155/tcp (Wemo control). If you use another firewall, open those yourself.
* Updates come with your normal `sudo apt upgrade` / `sudo dnf upgrade`. A new release reaches the repository within a few hours.

Without the repository: download the `.deb` or `.rpm` for your architecture from the release and run `sudo apt install ./wemo-ops_*.deb` or `sudo dnf install ./wemo-ops-*.rpm`. You won't get automatic updates this way.

> The repository also has an older `wemo-ops-server` package (v1.0.2, from the retired standalone server). Use `wemo-ops` or Docker instead.

## Docker (server only)

The image `ghcr.io/qrussell/wemo-ops-server` is published for amd64 and arm64 with every release. It runs the server and mobile web app, not the desktop app.

```bash
curl -fsSLO https://raw.githubusercontent.com/qrussell/wemo-ops-center/main/universal-app/docker-compose.yml
docker compose up -d
```

Then open `http://<host-ip>:5050`. Edit `TZ` in `docker-compose.yml` to your time zone first, so schedules run at local time. Run it on a **Linux host** with `network_mode: host` (as in the compose file); Docker Desktop on Windows and macOS can't discover devices. All options are on [Wemo Ops Server and Docker](Wemo-Ops-Server.md).

## Run from source

For development or an unsupported platform, with Python 3.10 or newer:

```bash
git clone https://github.com/qrussell/wemo-ops-center.git
cd wemo-ops-center/universal-app
python -m pip install "pywemo>=2.1.1" requests customtkinter Pillow pyperclip qrcode pystray flask waitress
python wemo_server.py            # the background service and web app, port 5050
python wemo_ops_universal.py     # the desktop app (in a second terminal)
```

On Linux you may also need your distribution's Tk package (`python3-tk` or `python3-tkinter`).

## Next steps

* [Set Up a New Device](Provisioning.md)
* [Desktop App Guide](Wemo-Ops-Center.md)
* [Schedules](Schedules.md)
