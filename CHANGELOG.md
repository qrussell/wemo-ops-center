# Changelog

A short history of Wemo Ops Center releases. Full notes for each version, with downloads, are on the [Releases page](https://github.com/qrussell/wemo-ops-center/releases); from v5.3.1 they are also in [`release-notes/`](release-notes/). Numbers like #28 are [GitHub issues](https://github.com/qrussell/wemo-ops-center/issues).

## Unreleased

- Documentation: the GitHub wiki is rewritten and now published from the [`wiki/`](wiki/) folder (installation, provisioning, desktop app guide, schedules, server and Docker, integrations, server API, supported devices, troubleshooting, FAQ, uninstall). Issue forms, a pull request template, this changelog, a code of conduct and a support page were added.

## 5.6.0 (23 Nov 2026)

- Experimental schedules stored on the plug itself (#28): **Automation** has two tabs, **Run by Wemo Ops** and **Stored on Device (experimental)**. Push to Device, Copy to Wemo Ops, Clear All and Restore Backup, with a backup before every change. Desktop app only. On Wemo Mini firmware 2.00.11565 stored rules didn't run in tests. [Notes](release-notes/v5.6.0.md)

## 5.5.0 (22 Nov 2026)

- Device clock sync (#32): **Maintenance → Sync Selected Device / Sync All Devices**, a daily option, and **Sync Clocks Now** in the web app.
- Windows app built as a folder of files, ending the Microsoft Defender `Trojan:Win32/Bearfoos.A!ml` false positive (#33).
- Homebridge installer stops waiting after 3 minutes instead of hanging (#31).
- Maintenance has a **Device** picker and says when no devices have been found. [Notes](release-notes/v5.5.0.md)

## 5.4.0 (22 Nov 2026)

- The desktop app can use a Wemo Ops Server on another machine (#22).
- Insight plugs show power (W) and today's energy (kWh) (#27).
- Windows installer installs to Program Files with administrator rights (#29) and adds a firewall rule so phones can open the mobile web app (#26).
- 175% and 200% UI scaling (#2). [Notes](release-notes/v5.4.0.md)

## 5.3.1 (15 Nov 2026)

- Much faster discovery on Windows (#25); devices with the same name are all found, told apart by MAC address (#24); every connected network is scanned (#30).
- macOS "damaged app" fix and builds for macOS 15 and 26, Apple Silicon and Intel (#21).
- Linux ARM64 packages (Raspberry Pi 4/5) and a fix for the Fedora emoji-font crash.
- The update check only offers newer stable releases. [Notes](release-notes/v5.3.1.md)

## 5.3.0 (18 Feb 2026)

- Wemo Dimmer support with a 0–100% brightness slider, in the desktop and web app.
- New **Integrations** page: Homebridge/HOOBS config generator and installer.

## 5.2.3 (10 Feb 2026)

- Deep scan of ports 49152–49155 finds devices on VLANs and with moved ports.
- Live state sync every 2 seconds between the desktop app, web app and physical switches.
- The desktop app uses the server's device list when the server is running; subnet manager in the desktop and web app.

## 5.1.6 (8 Feb 2026)

- Mobile web app for phones and tablets.
- One "universal" app for Windows, macOS (Intel and Apple Silicon), Debian/Ubuntu and Fedora/RHEL.
- Docker support, contributed in #3.

## 4.2.6 (7 Feb 2026)

- Wemo Ops Server with a web dashboard, for always-on Linux servers (the older standalone server, now retired).
- Fixes for RHEL/Rocky/Alma installs and virtual machine displays.

## 4.1.7 (5 Feb 2026)

- Non-blocking UI, faster discovery, RHEL/Fedora font fix.

## 4.1.6 (4 Feb 2026)

- Saved subnets and multi-subnet scanning for VLANs.
- **Maintenance** page with Clear Personal Info, Clear Wi-Fi and Factory Reset.
- Devices tracked by MAC address to avoid duplicates.

## 4.1.0 (4 Feb 2026)

- Windows installer with the background service; Linux `.deb` packages; macOS DMG with `Install_WemoOps.command`.

## 4.0 (3 Feb 2026)

- Automation: fixed-time and sunrise/sunset schedules with offsets, run by a background service.

## 3.1 (3 Feb 2026)

- "Smart loop" provisioning that tries each Wi-Fi encryption method until the device accepts one.

## 3.0 (2 Feb 2026)

- First macOS version; Dashboard-first layout; device details (IP, MAC, serial, firmware); manual override in the Provisioner.

## 2.0 (2 Feb 2026)

- Stability fixes for provisioning and Windows 11 timeouts.

## 1.0 (1 Feb 2026)

- First release: Dashboard, Provisioner and HomeKit code extraction.

## MCP server

The Wemo MCP Server (mcp-v0.1.0 to mcp-v1.0.1, Feb 2026) started in this repository and now lives at [apiarya/wemo-mcp-server](https://github.com/apiarya/wemo-mcp-server).
