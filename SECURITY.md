# Security Policy

Wemo Ops Center is a free, local-only tool maintained by one person in their spare time. Security reports are welcome and taken seriously. This page explains what is supported, how to report a problem privately, and what the app is (and isn't) designed to protect against.

## Supported versions

Only the latest release gets security fixes. Fixes ship in a new release rather than being backported.

| Version | Supported |
|---|---|
| Latest 5.x release ([Releases](https://github.com/qrussell/wemo-ops-center/releases/latest)) | Yes |
| Older releases | No, please update |
| `universal-server/` (old standalone server) | No |

The app's update check (Settings) tells you when a newer release is available.

## Reporting a vulnerability

**Please don't open a public issue for a security problem.**

Report it privately on GitHub instead:

1. Go to the [Security tab](https://github.com/qrussell/wemo-ops-center/security) of this repository.
2. Click **Report a vulnerability**.
3. Describe the problem, the version and edition you used (desktop app, background service, Docker image, HOOBS helper), your operating system, and the steps to reproduce it. A proof of concept helps a lot.

Only the maintainer can see the report. What to expect:

- An acknowledgement within **7 days**.
- An assessment (accepted or declined, and why) within **30 days**.
- For accepted reports, a fix in a new release, followed by a published GitHub security advisory that credits you (unless you'd rather stay anonymous). A CVE is requested through GitHub where it makes sense.

This is a one-person project, so timelines are best effort. Please give a reasonable chance to release a fix before you disclose publicly; 90 days is the default.

## Security model and scope

Wemo Ops Center is built for a **trusted home or office network (LAN)**. Please read this before reporting, because some behaviour is by design.

### By design (not vulnerabilities on their own)

- **The background service has no login.** The server (`wemo_service` / `wemo-ops-server` / Docker image) listens on port **5050** on all network interfaces so phones on the same network can use the web app. Anyone who can reach that port on your LAN can see and control your devices, change schedules and settings.
- **Wemo devices themselves have no authentication.** Belkin's local UPnP/SOAP protocol lets anyone on the LAN control a plug. Wemo Ops Center can't add security that the hardware doesn't have.
- **Local data is stored as plain JSON** in your user profile (`%APPDATA%\WemoOps`, `~/Library/Application Support/WemoOps`, `~/.local/share/WemoOps`, or `/data` in Docker). This includes saved Wi-Fi profiles used for provisioning. Protect it like any other file in your profile.
- **Release binaries are not code-signed**, so Windows SmartScreen and macOS Gatekeeper warn on first launch. Only download from this repository's [Releases](https://github.com/qrussell/wemo-ops-center/releases) page, the project's apt/dnf repository, or `ghcr.io/qrussell/wemo-ops-server`.

**Never expose port 5050 to the internet** (port forwarding, a public reverse proxy, a cloud VM with an open port). If you need remote access, use a VPN into your home network. The Windows installer's firewall rule only allows the Private network profile.

### In scope

We especially want to hear about:

- Anything that lets someone **outside your LAN** read or control devices, or reach the service, while it's set up as documented.
- Code execution, command injection or path traversal in the desktop app, the service, the Docker image or the HOOBS helper, including through device names, SSIDs or other data a device or network can supply.
- Cross-site scripting or cross-site request forgery in the web app (for example, a web page on the internet making your browser change your devices or settings).
- Ways a malicious Wemo device or a hostile network could crash, take over or corrupt data in the app.
- Wi-Fi credentials or other secrets leaking beyond your local data folder (logs, network traffic to third parties, crash output).
- Problems in how releases are built and published (GitHub Actions workflows, packages, Docker image, update check).
- Changes the app makes to a device's stored data (rules, Wi-Fi, firmware) that could damage it without the confirmation the app promises.

### Out of scope

- Reports that only say "the API has no authentication" or "the service binds to 0.0.0.0" for an attacker already on your LAN (see above).
- Weaknesses in Belkin Wemo firmware or its protocol that Wemo Ops Center doesn't make worse. Please report those to Belkin or, for the Python library, to [pywemo](https://github.com/pywemo/pywemo).
- Missing code signing, SmartScreen or Gatekeeper warnings.
- Problems that need an attacker who already controls your computer or your user account.
- Denial of service by flooding your LAN, and automated scanner output without a working example.
- The Wemo MCP server, which now lives at [apiarya/wemo-mcp-server](https://github.com/apiarya/wemo-mcp-server).

## Automated checks

This repository uses GitHub's Dependabot alerts, CodeQL code scanning and secret scanning with push protection. Alerts are reviewed by the maintainer; fixes go out in the next release.

Thank you for helping keep Wemo Ops Center users safe.
