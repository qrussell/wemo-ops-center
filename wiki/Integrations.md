# Smart Home Integrations

Wemo Ops Center keeps your Wemo devices on your network and working. To use them alongside other smart home gear, pick the route that fits your setup. Share yours in [Discussions](https://github.com/qrussell/wemo-ops-center/discussions).

| You use | Route |
|---|---|
| Apple Home (HomeKit) | Built-in HomeKit on newer Wemo models, or Homebridge |
| Amazon Alexa, Google Home | Homebridge with the `homebridge-alexa` plugin, or the hub's own Wemo support where it still works |
| Home Assistant | Home Assistant's own Wemo integration, side by side with Wemo Ops Center |
| Node-RED, scripts, other hubs | The [Server API](Server-API.md) |
| An AI assistant (Claude, Copilot, Cursor) | The [Wemo MCP Server](https://github.com/apiarya/wemo-mcp-server) |

## Apple Home (HomeKit)

**Built-in HomeKit:** some newer Wemo devices support HomeKit directly. On the Dashboard, click **Get HomeKit Code** on the device's card. If a code appears (it's also copied), add the device in the Home app with **Add Accessory → More options** and enter the code. No Homebridge needed.

**Older devices:** use Homebridge (below), which makes any Wemo device show up in the Home app.

## Homebridge and HOOBS

[Homebridge](https://homebridge.io) (and HOOBS, which is built on it) bridges devices to Apple Home, and with plugins to Alexa and Google Home. The desktop app's **Integrations** page helps in two ways.

### 1. Configuration Generator

Click **Scan & Generate Config**, then **Copy Config**. You get the `BelkinWeMo` platform block, with the devices found, for your Homebridge/HOOBS `config.json` (used by the [homebridge-wemo](https://github.com/homebridge-plugins/homebridge-wemo) plugin). Paste it into the `platforms` list in the Homebridge UI's **Config** editor and restart Homebridge.

### 2. Install Compatibility Layer

If you don't have Homebridge yet, **Install Compatibility Layer** installs it on this computer:

1. Installs Node.js (v20, from nodejs.org) if `npm` is missing.
2. Installs Homebridge and its web UI (`homebridge`, `homebridge-config-ui-x`) and the `homebridge-wemo` and `homebridge-alexa` plugins with `npm`.
3. Sets Homebridge up as a service with `hb-service install`, so it starts with the computer.
4. Opens the Homebridge UI at `http://localhost:8581` (**Launch Dashboard**). Follow its steps to pair with the Home app.

It needs administrator rights (on Linux and macOS it uses `sudo`). If the Homebridge service doesn't start within 3 minutes, the installer stops waiting and shows the command to check its log (`sudo hb-service logs`, or `hb-service logs` on Windows). See [Troubleshooting](Troubleshooting.md#homebridge-install-stops-after-3-minutes).

The computer running Homebridge must stay on, like for schedules. A Raspberry Pi running both Homebridge and [Wemo Ops Server](Wemo-Ops-Server.md) is a good always-on setup.

## Amazon Alexa and Google Home

* **Alexa:** the `homebridge-alexa` plugin (installed above) exposes your Homebridge devices to Alexa. It needs a free account with the plugin's author and the "Homebridge" Alexa skill; see the [plugin's instructions](https://github.com/NorthernMan54/homebridge-alexa).
* **Google Home:** use the [homebridge-gsh](https://github.com/oznu/homebridge-gsh) plugin, installed from the Homebridge UI.
* Some Alexa devices could find Wemo devices on the local network directly in the past. Whether that still works depends on the Echo model and the Wemo firmware.

## Home Assistant

Home Assistant has its own [Belkin Wemo integration](https://www.home-assistant.io/integrations/wemo/), built on the same pywemo library. It finds and controls Wemo devices locally and works well with Wemo Ops Center:

* Use **Wemo Ops Center** to set up (provision) new or reset devices, rename them, reset them and sync their clocks: things Home Assistant can't do without the Wemo app.
* Use **Home Assistant** for automations that involve your other devices.
* Both can run at the same time; Wemo devices accept commands from both.
* If your Wemo devices are on another VLAN, Home Assistant may need them added by IP address under the integration's `static` option.

To use Wemo Ops Center schedules from Home Assistant, or trigger a scan, call the [Server API](Server-API.md) with a `rest_command`:

```yaml
rest_command:
  wemo_ops_scan:
    url: "http://192.168.1.10:5050/api/scan"
    method: POST
```

## Other hubs and tools

Anything that can send an HTTP request (Node-RED, openHAB, Hubitat, a cron job) can use the [Server API](Server-API.md) to read device states, toggle devices, set Dimmer brightness and manage schedules. Keep in mind that the API has no login: use it on your home network only.

## AI assistants (MCP)

The [Wemo MCP Server](https://github.com/apiarya/wemo-mcp-server) (`pip install wemo-mcp-server`) lets AI assistants that support the Model Context Protocol, such as Claude Desktop, VS Code with Copilot and Cursor, find and control Wemo devices in plain language. It is a separate project that grew out of this repository.
