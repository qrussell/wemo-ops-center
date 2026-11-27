# Troubleshooting

Start with the section that matches what you see. If nothing here helps, ask in [Discussions](https://github.com/qrussell/wemo-ops-center/discussions) or [open a bug report](https://github.com/qrussell/wemo-ops-center/issues/new/choose) with your version, edition, operating system, device model and firmware, and the log.

## Where the logs are

| Edition | Log |
|---|---|
| Background service / server (Windows) | `%APPDATA%\WemoOps\server.log` |
| Background service (macOS) | `~/.local/share/WemoOps/server.log` |
| Linux package | `journalctl -u wemo-ops-server` and `/var/lib/wemo-ops/server.log` |
| Docker | `docker logs wemo-ops-server`, and `server.log` in the `wemo-data` volume |
| Desktop app, provisioning | The **Live Operation Log** on the Provisioner page |
| Homebridge | `sudo hb-service logs` (`hb-service logs` on Windows) |

Remove Wi-Fi passwords and anything personal before posting a log.

## Installing and starting

### "Windows protected your PC"

SmartScreen warns about apps without a paid code-signing certificate. Click **More info → Run anyway**. Check the download against `SHA256SUMS.txt` on the release page if you want to be sure it's the real file.

### Microsoft Defender says `Trojan:Win32/Bearfoos.A!ml`

A false positive from Defender's machine-learning check on unsigned Python apps ([#33](https://github.com/qrussell/wemo-ops-center/issues/33)). Install v5.5.0 or newer, which is built differently and passes Defender's scan. If Defender quarantined a file, restore it from **Windows Security → Protection history** after checking the hash.

### The Windows installer fails or is blocked

From v5.4.0 the installer installs to `C:\Program Files\WemoOps` and needs administrator rights ([#29](https://github.com/qrussell/wemo-ops-center/issues/29)). If your account isn't an administrator, choose "install for me only". Some company security policies block apps in your user folder; installing for all users avoids that.

### macOS says the app is damaged or from an unidentified developer

Run **Install_WemoOps.command** from the DMG; it removes the download quarantine flag. Or right-click **WemoOps** → **Open** → **Open**. If macOS still says it's damaged, run `xattr -r -d com.apple.quarantine /Applications/WemoOps.app` in Terminal. Use the DMG for your macOS version (15 or 26) and chip (Apple Silicon or Intel).

### The app window is tiny or huge

**Settings → UI Scaling**, from 80% to 200%.

### Linux: the app doesn't start or crashes on Fedora

Install from the package repository so the right system libraries are pulled in, and update to v5.3.1 or newer (fixes an emoji-font crash on Fedora). Start it from a terminal with `wemo-ops` to see the error.

## Devices are not found

1. **Same network?** Your computer or server must be on the same network as the devices, or able to route to their VLAN. Guest Wi-Fi networks usually block this.
2. **IoT network or VLAN:** on the Dashboard (or web app **Setup**), type the devices' subnet, e.g. `192.168.20.0/24`, and click **Save**. Saved subnets are deep-scanned too. Your router or firewall must allow traffic from your computer to ports 49152–49155 on that VLAN.
3. **Click Scan and wait.** Broadcast discovery shows most devices in seconds; the deep scan can take up to a minute on large networks.
4. **VPN:** VPN, virtual machine and container network adapters are skipped. A VPN that captures all traffic can hide your local network; disconnect it and scan again.
5. **Docker:** use `network_mode: host` on a Linux host. Docker Desktop on Windows and macOS can't find devices; use the desktop app there.
6. **Firewall on the computer or server:** allow 1900/udp (discovery) and 49152–49155/tcp. On Linux see the [firewall commands](Wemo-Ops-Server.md#linux-package).
7. **Is the device online?** Open `http://<device-IP>:49153/setup.xml` (or ports 49152, 49154, 49155) in a browser. If nothing answers on any port, the device isn't on the network: power-cycle it, or [set it up again](Provisioning.md).
8. **Devices with the same name** are all listed, with the end of their MAC address added, e.g. `Wemo Mini (3A4F)`.

### A device disappears after being set up

The app rescans 60 and 120 seconds after provisioning; make sure your computer is back on your normal Wi-Fi by then, then click **Scan**. If the device's light is still blinking, it didn't join your Wi-Fi (wrong password or a 5 GHz-only network); see [Set Up a New Device](Provisioning.md#if-it-doesnt-work).

## Setting up a device fails

See [Set Up a New Device → If it doesn't work](Provisioning.md#if-it-doesnt-work).

## The mobile web app won't open

1. Check that the service is running: the desktop app's sidebar shows **Service Status**; on Linux run `systemctl status wemo-ops-server`. Open `http://localhost:5050` on the computer itself.
2. **Windows:** the installer option "Allow phones on my home network to open the mobile web app" adds a firewall rule for **Private** networks. Make sure your Wi-Fi is set to *Private* in **Settings → Network & internet**, or rerun the installer with that option ([#26](https://github.com/qrussell/wemo-ops-center/issues/26)).
3. **Linux:** open 5050/tcp in `ufw` or `firewalld` ([commands](Wemo-Ops-Server.md#linux-package)).
4. **macOS:** allow incoming connections for `wemo_service` if the firewall asks (**System Settings → Network → Firewall**).
5. The phone must be on the same network, not on mobile data or a guest network. Use `http://`, not `https://`.
6. If the QR code shows the wrong address (a computer with several networks), type the address of the network your phone is on.

## Schedules

### A schedule didn't run

* **Run by Wemo Ops schedules** only run while the computer or server running the service is on and awake, at that exact minute. A sleeping laptop skips them. Use a [Wemo Ops Server](Wemo-Ops-Server.md) for schedules that must always run.
* Check `server.log` for `Executed Schedule` lines and errors.
* Check the days ticked on the schedule.
* **Sunrise/sunset** needs a location and internet access for the sunrise times. On a server without the desktop app, [set the location](Wemo-Ops-Server.md#location-for-sunrise-and-sunset).

### A schedule runs at the wrong time

* **Run by Wemo Ops:** times follow the computer or server's clock and time zone. In Docker, set `TZ`.
* **Stored on the device, or made in the old Wemo app:** the device uses its own clock. Sync it with **Maintenance → Sync All Devices**, and turn on **Keep device clocks in sync (daily)** ([#32](https://github.com/qrussell/wemo-ops-center/issues/32)).

### A schedule stored on the plug never runs

Some firmware stores rules but no longer runs them since Belkin's cloud shut down. On a Wemo Mini with firmware 2.00.11565 they never ran in tests. Use **Copy to Wemo Ops** to have Wemo Ops run it instead ([#28](https://github.com/qrussell/wemo-ops-center/issues/28)). More in [Schedules](Schedules.md#stored-on-device-experimental).

### Schedules stop when I close the app or turn off my laptop

Schedules run by Wemo Ops need the background service, which runs while the computer is on, even with the app window closed ([#19](https://github.com/qrussell/wemo-ops-center/issues/19)). Check that **Service Status** in the sidebar says it is running. For schedules that run 24/7, put [Wemo Ops Server](Wemo-Ops-Server.md) on an always-on device (Raspberry Pi, NAS, Docker) and [connect the desktop app to it](Wemo-Ops-Server.md#connect-the-desktop-app-to-a-server).

### I can't see my schedules

Schedules live in `schedules.json` on the machine running the service. If you switched the desktop app to a remote server, you see that server's schedules, not your computer's.

## Remote server

### The sidebar says UNREACHABLE

* Open `http://<server>:5050/api/status` in a browser on the same computer. If that fails, the server isn't running or a firewall blocks port 5050.
* Check the address in **Settings → Background Service**. If `WEMO_OPS_SERVER_URL` is set, it overrides that address (the Settings page says so).
* `.local` names need mDNS (Bonjour/Avahi); try the server's IP address instead.

## Homebridge

### Homebridge install stops after 3 minutes

The installer waits up to 3 minutes for the Homebridge service to come up ([#31](https://github.com/qrussell/wemo-ops-center/issues/31)). If it doesn't, it shows the command it would have run (e.g. `sudo hb-service install --user <you>`). Run it yourself, then check `sudo hb-service logs`. Common causes: port 8581 is already in use, or Node.js isn't installed for all users. On systems without systemd (some containers and WSL), Homebridge can't be installed as a service; run `homebridge` directly instead.

### Devices don't appear in the Home app

Check that the `BelkinWeMo` platform block is in Homebridge's `config.json` (**Integrations → Scan & Generate Config**), restart Homebridge, and look at its log for the homebridge-wemo plugin. Devices on another VLAN may need to be listed by address in the plugin's settings.

## Insight readings look wrong

Insight power readings were tested with a simulated Insight only. Please [send a device report](https://github.com/qrussell/wemo-ops-center/issues/new?template=device_report.yml) with what the app shows and what you expect.
