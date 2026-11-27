# Server API

The background service and Wemo Ops Server expose a small JSON API on port 5050. The mobile web app and the desktop app use it; you can use it from scripts, Home Assistant `rest_command`s, Node-RED and similar tools.

> **No authentication.** Anyone who can reach port 5050 can switch your devices and change schedules. Only use the API on your home network. See [SECURITY.md](https://github.com/qrussell/wemo-ops-center/blob/main/SECURITY.md).

This API is not versioned and may change between releases; check the [release notes](https://github.com/qrussell/wemo-ops-center/releases) when you upgrade. Devices are addressed by the **name shown in the app** (e.g. `Porch light`, or `Wemo Mini (3A4F)` when names clash). URL-encode names with spaces.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/` | The mobile web app |
| GET | `/api/status` | Server status |
| GET | `/api/devices` | List devices |
| POST | `/api/toggle/<name>` | Toggle a device on/off |
| POST | `/api/brightness/<name>` | Set a Dimmer's brightness |
| POST | `/api/scan` | Start a full scan |
| GET / POST | `/api/settings` | Read or change settings |
| POST | `/api/sync_clocks` | Set every device's clock now |
| GET / POST / DELETE | `/api/schedules` | List, add or delete schedules run by Wemo Ops |

### `GET /api/status`

```json
{"status": "online", "scan_status": "Idle", "device_count": 7, "version": "5.6.0"}
```

### `GET /api/devices`

```json
[
  {"name": "Porch light", "ip": "192.168.1.40", "state": 1, "mac": "...", "serial": "...", "type": "switch"},
  {"name": "Living room", "ip": "192.168.1.41", "state": 60, "mac": "...", "serial": "...", "type": "dimmer"},
  {"name": "Heater", "ip": "192.168.1.42", "state": 1, "mac": "...", "serial": "...", "type": "switch", "power_w": 812.4, "today_kwh": 3.215}
]
```

* `state`: `0` off, `1` on; for Dimmers, the brightness (0–100).
* `type`: `switch` or `dimmer`.
* `power_w` and `today_kwh` appear only for Insight plugs.

### `POST /api/toggle/<name>`

```bash
curl -X POST "http://192.168.1.10:5050/api/toggle/Porch%20light"
```

Returns `{"status": "ok"}`, or `404` with `{"status": "not found"}`. The switch happens in the background; read `/api/devices` a second later for the new state. There is no separate "on" or "off" call: check `state` first if you need a specific state.

### `POST /api/brightness/<name>`

```bash
curl -X POST "http://192.168.1.10:5050/api/brightness/Living%20room" -H "Content-Type: application/json" -d '{"level": 60}'
```

`level` is 0–100. Returns `{"status": "ok"}`, `400` if `level` isn't a number, or `404`.

### `POST /api/scan`

Starts a full scan of all networks. Returns `{"status": "started"}`, or `{"status": "busy"}` if one is already running. Watch `scan_status` in `/api/status`.

### `GET /api/settings` and `POST /api/settings`

`GET` returns `settings.json` plus `connected_subnets` (the networks the server is connected to, detected automatically).

`POST` merges the keys you send into `settings.json`, keeping the rest:

```bash
curl -X POST http://192.168.1.10:5050/api/settings -H "Content-Type: application/json" -d '{"sync_device_clocks": true, "lat": "40.71", "lng": "-74.01"}'
```

Useful keys: `subnets` (list of saved subnets, e.g. `["192.168.20.0/23"]`), `periodic_full_scan` (true/false), `sync_device_clocks` (true/false), `lat` and `lng` (location for sunrise/sunset).

### `POST /api/sync_clocks`

Sets every device's clock and time zone from the server now. Returns `{"status": "ok", "synced": [...], "failed": [...]}`.

### `/api/schedules`

`GET` returns the list:

```json
[{"id": 1764300000, "device": "Porch light", "type": "Sunset", "action": "Turn ON", "value": "15", "offset_dir": -1, "days": [0,1,2,3,4,5,6], "last_run": "2026-11-26"}]
```

`POST` adds one:

```bash
curl -X POST http://192.168.1.10:5050/api/schedules -H "Content-Type: application/json" \
  -d '{"device": "Porch light", "type": "Time (Fixed)", "action": "Turn OFF", "value": "23:00", "days": [0,1,2,3,4]}'
```

| Field | Values |
|---|---|
| `device` | Device name |
| `type` | `Time (Fixed)`, `Sunrise` or `Sunset` |
| `action` | `Turn ON`, `Turn OFF` or `Toggle` |
| `value` | `HH:MM` (24-hour) for fixed times; offset in minutes for sunrise/sunset |
| `offset_dir` | `1` after, `-1` before sunrise/sunset (default `1`) |
| `days` | `0` Monday to `6` Sunday (default every day) |

Returns `{"status": "added", "id": ...}`.

`DELETE /api/schedules?id=<id>` deletes one and returns `{"status": "deleted"}`.
