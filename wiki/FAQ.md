# FAQ

### Do I need a Belkin account, the Wemo app or the internet?

No account and no Wemo app. Everything happens on your own network. The internet is only used to check for app updates (GitHub) and, for sunrise/sunset schedules, to look up your approximate location and the day's sunrise and sunset times. Fixed-time schedules and device control work fully offline.

### Is it free? Who makes it?

Free and open source under the [MIT license](https://github.com/qrussell/wemo-ops-center/blob/main/LICENSE), made by an independent developer. It isn't affiliated with or endorsed by Belkin.

### Which edition should I install?

Most people: the **desktop app** on the computer they use. If you want schedules to run 24/7 without leaving that computer on, add **Wemo Ops Server** on a Raspberry Pi, NAS or home server and [connect the desktop app to it](Wemo-Ops-Server.md#connect-the-desktop-app-to-a-server). See the table on [Home](Home.md).

### Which devices work?

Wemo Wi-Fi plugs, Insight plugs, light switches and dimmers. Thread-only models don't. Details and what has been tested: [Supported Devices](Supported-Devices.md).

### Can I set up a device without the Wemo app?

Yes, that is what the **Provisioner** is for: [Set Up a New Device](Provisioning.md).

### Can I use it from outside my home?

Not directly, and please don't port-forward port 5050: the web app and API have no login. Connect to your home network with a VPN (WireGuard, Tailscale, your router's VPN) and use the web app as if you were home.

### Do schedules run when my computer is off?

**Run by Wemo Ops** schedules need the computer or server running the service to be on. For always-on schedules, run [Wemo Ops Server](Wemo-Ops-Server.md) on a low-power device. Schedules stored on the plug itself would run without a computer, but many plugs no longer run them since the cloud shut down: see [Schedules](Schedules.md).

### Does it work with Alexa, Google Home, Apple Home or Home Assistant?

Yes, through Homebridge, the devices' built-in HomeKit, or Home Assistant's own Wemo integration. See [Smart Home Integrations](Integrations.md).

### Can it update my devices' firmware?

No. Belkin's firmware update servers are gone, and Wemo Ops Center doesn't install firmware.

### Can I still use the old Wemo app at the same time?

Wherever the old app still works locally, yes: Wemo devices accept commands from both. Schedules made in the Wemo app show up under **Automation → Stored on Device**, where you can copy them to Wemo Ops.

### Can I run the desktop app on several computers?

Yes. Each one runs its own background service and its own schedules, so a schedule created on two computers runs twice. To share one set of schedules, point every desktop app at one [Wemo Ops Server](Wemo-Ops-Server.md#connect-the-desktop-app-to-a-server).

### Will a factory reset lose my settings in Wemo Ops Center?

No. A factory reset clears the device (name, rules, Wi-Fi). Your Wemo Ops Center settings, Wi-Fi profiles and schedules are on your computer. After setting the device up again, check schedules that used its old name.

### Where are my settings stored? How do I back them up?

In the app data folder as JSON files: [Data folders](Wemo-Ops-Server.md#data-folders) and [Back up and move to a new machine](Wemo-Ops-Server.md#back-up-and-move-to-a-new-machine).

### Is my Wi-Fi password safe?

Saved Wi-Fi profiles (`wifi_profiles.json`) are stored in your user's app data folder, in plain text, and never leave your computer except when sent to a device during setup. Don't share that file.

### How does it compare to Home Assistant or pywemo?

[pywemo](https://github.com/pywemo/pywemo) is the Python library that Wemo Ops Center and Home Assistant both use to talk to Wemo devices. Home Assistant is a full smart-home hub; Wemo Ops Center is a focused Wemo tool that also sets up and resets devices and works with no hub at all. Many people use both.

### How do I report a bug or ask for a feature?

[Open an issue](https://github.com/qrussell/wemo-ops-center/issues/new/choose) using the forms. For questions and ideas, use [Discussions](https://github.com/qrussell/wemo-ops-center/discussions). Security problems go [privately](https://github.com/qrussell/wemo-ops-center/security/policy).

### Can I contribute?

Yes: see [CONTRIBUTING.md](https://github.com/qrussell/wemo-ops-center/blob/main/CONTRIBUTING.md). Improvements to these wiki pages are welcome too; they live in the repository's [`wiki/` folder](https://github.com/qrussell/wemo-ops-center/tree/main/wiki).
