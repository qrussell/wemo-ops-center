# Wemo Ops Center Wiki

**Keep your Belkin Wemo devices working without the cloud.** Wemo Ops Center sets up, controls, schedules and resets Wemo plugs, switches and dimmers on your own network. No Belkin account, no cloud, no subscription.

These pages are for Wemo Ops Center **v5.6.0**. For what changed in each version, see the [Changelog](https://github.com/qrussell/wemo-ops-center/blob/main/CHANGELOG.md).

## Which edition do I need?

| You want to... | Use |
|---|---|
| Set up, control and reset devices from your Windows, Mac or Linux computer | The **desktop app**. It includes a background service that runs your schedules and the mobile web app while the computer is on. |
| Run schedules 24/7 without leaving a computer on | **Wemo Ops Server** on a Raspberry Pi, NAS, VM or home server (Linux package or Docker). The desktop app can connect to it. |
| Control devices by talking to an AI assistant | The [Wemo MCP Server](https://github.com/apiarya/wemo-mcp-server), a separate project. |
| Use Apple Home, Alexa or Google Home | The desktop app's **Integrations** page sets up Homebridge. See [Smart Home Integrations](Integrations.md). |

## Start here

1. [Installation](Installation.md): Windows, macOS, Linux and Docker.
2. [Set Up a New Device](Provisioning.md): connect a new or reset Wemo to your Wi-Fi without the Wemo app.
3. [Desktop App Guide](Wemo-Ops-Center.md): what each page of the app does.
4. [Schedules](Schedules.md): fixed-time and sunrise/sunset schedules, and the experimental schedules stored on the plug.
5. [Mobile Web App](Mobile-Web-App.md): control devices from your phone and add it to your home screen.

## Going further

* [Wemo Ops Server and Docker](Wemo-Ops-Server.md): always-on server, settings, data folders, backups and connecting the desktop app to it.
* [Smart Home Integrations](Integrations.md): Homebridge/HOOBS (HomeKit, Alexa, Google Home), Home Assistant, MCP.
* [Server API](Server-API.md): the HTTP API the web app uses, for your own scripts.

## Help

* [Supported Devices](Supported-Devices.md): which models and firmware are known to work.
* [Troubleshooting](Troubleshooting.md): devices not found, the mobile app won't open, schedules at the wrong time, installer warnings.
* [FAQ](FAQ.md)
* [Uninstall](Uninstall.md)
* Still stuck? Ask in [Discussions](https://github.com/qrussell/wemo-ops-center/discussions) or [open an issue](https://github.com/qrussell/wemo-ops-center/issues/new/choose).

## Security in one line

The background service and server on port **5050 have no login**. They are made for your home network: never port-forward them or expose them to the internet. To reach them from outside, use a VPN to your home network. See [SECURITY.md](https://github.com/qrussell/wemo-ops-center/blob/main/SECURITY.md).
