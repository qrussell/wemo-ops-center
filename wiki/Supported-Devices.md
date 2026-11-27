# Supported Devices

Wemo Ops Center works with Belkin Wemo **Wi-Fi** devices that use Wemo's local network protocol (UPnP), through the [pywemo](https://github.com/pywemo/pywemo) library. It is maintained by one person with a handful of devices, so "tested" below means tested on real hardware by the maintainer; everything else comes from user reports or simulated devices.

**Please help fill this in:** if you use a model that isn't listed, or a feature works differently on your firmware, send a [device report](https://github.com/qrussell/wemo-ops-center/issues/new?template=device_report.yml).

## Device types

| Type | Examples (model numbers) | On/off | Extra | Status |
|---|---|---|---|---|
| Wemo Mini Smart Plug | F7C063 | Yes | | **Tested** (firmware `WeMo_WW_2.00.11565.PVT-OWRT-SNSV2`) |
| Wemo Smart Plug, Outdoor Plug and other plugs | F7C027, WSP080, WSP090 | Yes | | Expected to work (supported by pywemo); not tested by the maintainer |
| Wemo Insight Smart Plug | F7C029 | Yes | Power now (W) and today's energy (kWh) | Power readings tested with a **simulated** Insight only; please report |
| Wemo Light Switch, 3-Way Light Switch | F7C030, WLS040, WLS0403 | Yes | | Expected to work (supported by pywemo); not tested by the maintainer |
| Wemo Dimmer | F7C059, WDS060 | Yes | Brightness 0–100% | Supported since v5.3.0; not tested on real hardware by the maintainer. Min/max brightness can't be set (see below) |
| Wemo Smart Plug with Thread, other Thread or HomeKit-only devices | WSP100 | No | | **Not supported**: they don't use Wi-Fi. Add them to Apple Home directly |
| Wemo Link / LED bulbs, Maker, Humidifier, Coffee Maker, Crock-Pot | | Unknown | | Not tested. Discovery may find them; please report |

## Features by device

| Feature | Plugs | Insight | Light switches | Dimmers |
|---|---|---|---|---|
| Find and control | Yes | Yes | Yes | Yes |
| Set up Wi-Fi (Provisioner) | Yes | Yes | Yes | Yes |
| Rename, resets | Yes | Yes | Yes | Yes |
| HomeKit setup code | Models with built-in HomeKit | Models with built-in HomeKit | Models with built-in HomeKit | Models with built-in HomeKit |
| Schedules run by Wemo Ops | Yes | Yes | Yes | On/off only (no brightness schedules) |
| Clock sync | Yes | Yes | Yes | Yes |
| [Schedules stored on the device](Schedules.md#stored-on-device-experimental) | Experimental, see below | Experimental | Experimental | Dimmer V2 (WDS060) on newer firmware has no rules support |

"Yes" means the app supports it for that type; the Status column above says what has been tested on real hardware.

## Known firmware behaviour

| Firmware | Model | What we know |
|---|---|---|
| `WeMo_WW_2.00.11565.PVT-OWRT-SNSV2` | Wemo Mini | Control, provisioning and clock sync work. The device clock can't be read (the app can set it but not show it). Rules **can be stored but never ran** in tests, with a correct clock, after a power cycle, local-time and UTC rules (Nov 2026). Use schedules run by Wemo Ops. |
| `2.00.11851` | F7C027 | A user reported stored rules still running without the cloud ([pywemo #773](https://github.com/pywemo/pywemo/issues/773)). Not confirmed with Wemo Ops Center. |

Dimmers: the minimum and maximum brightness range can't be changed from Wemo Ops Center; the slider always covers 0–100%.

## Finding your firmware version

Open `http://<device-IP>:49153/setup.xml` in a browser (if that doesn't load, try ports 49152, 49154 or 49155). Look for:

* `<modelName>` and `<modelDescription>`: the model.
* `<firmwareVersion>`: the firmware, e.g. `WeMo_WW_2.00.11565.PVT-OWRT-SNSV2`.

The device's IP address is on its card on the Dashboard. The model number (e.g. F7C063) is also printed on the device.

## Firmware updates

Wemo Ops Center **doesn't update device firmware**. Belkin's update servers went away with the cloud, so the firmware your device has now is the one it keeps.
