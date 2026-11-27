# Uninstall

Uninstalling removes the app but keeps your settings and schedules, so a reinstall picks up where you left off. To remove everything, also delete the data folder listed for your system. Your Wemo devices keep working and keep their Wi-Fi settings.

## Windows

1. **Settings → Apps → Installed apps → WemoOps → Uninstall** (or **Control Panel → Programs and Features**). The uninstaller closes the app and the background service, and removes the firewall rule and the startup shortcut.
2. To remove your data: delete `%APPDATA%\WemoOps` (paste it into File Explorer's address bar).

## macOS

1. Quit WemoOps.
2. Stop and remove the background service:

   ```bash
   launchctl unload ~/Library/LaunchAgents/com.qrussell.wemoops.plist
   rm ~/Library/LaunchAgents/com.qrussell.wemoops.plist
   ```

3. Drag **WemoOps** from Applications to the Bin.
4. To remove your data: delete `~/Library/Application Support/WemoOps` (also holds the service program) and `~/.local/share/WemoOps`.

## Linux (package)

```bash
sudo apt remove wemo-ops          # Ubuntu / Debian / Raspberry Pi OS
sudo dnf remove wemo-ops          # Fedora / RHEL / Rocky
```

This stops and removes the `wemo-ops-server` service. To remove your data: `sudo rm -rf /var/lib/wemo-ops` and `rm -rf ~/.local/share/WemoOps`.

To also remove the package repository:

```bash
sudo rm /etc/apt/sources.list.d/qrussell.list /usr/share/keyrings/qrussell-repo.gpg   # apt
sudo rm /etc/yum.repos.d/qrussell.repo                                                 # dnf
```

Firewall ports opened by the package stay open; close them with `ufw delete allow 5050/tcp` or `firewall-cmd --permanent --remove-port=5050/tcp && firewall-cmd --reload` (and the same for 1900/udp and 49152–49155/tcp) if you like.

## Docker

```bash
docker compose down               # stop and remove the container
docker volume rm wemo-data        # delete settings and schedules
docker image rm ghcr.io/qrussell/wemo-ops-server
```

## Homebridge

Uninstalling Wemo Ops Center doesn't remove Homebridge. To remove it: `sudo hb-service uninstall` (`hb-service uninstall` on Windows), then `npm uninstall -g homebridge homebridge-config-ui-x homebridge-wemo homebridge-alexa`.
