# Set Up a New Device

The desktop app's **Provisioner** connects a new or reset Wemo device to your Wi-Fi without the Wemo app or a Belkin account. Use it for a brand-new device, after a factory reset, or after **Reset Wi-Fi**.

You need a computer with Wi-Fi (Windows, macOS or Linux) running the desktop app. The Docker image and the mobile web app can't provision devices.

## Before you start

* **Put the device in setup mode.** A new or reset Wemo blinks (orange/amber and white or blue, depending on the model) and broadcasts its own Wi-Fi network named like `Wemo.Mini.XXX` (the middle part depends on the model).
  * If it isn't blinking: hold the reset button for about 5 seconds until the light flashes, or use **Maintenance → Reset Wi-Fi** in the app if the device is still on your network.
* **Use 2.4 GHz Wi-Fi.** Wemo devices can't join 5 GHz-only networks. If your router uses one name for both bands and setup fails, try a separate 2.4 GHz network name.
* **Know your Wi-Fi name (SSID) and password.** Names and passwords are case-sensitive.

## Steps

1. Open **Provisioner** in the desktop app.
2. **Step 1: Locate Device.** Click **Scan Airwaves** to list nearby Wemo setup networks, then click **Connect** next to yours. The app joins that network (on Linux through NetworkManager, on macOS through `networksetup`).
   * You can also join the `Wemo.xxx` network yourself in your computer's Wi-Fi menu. The status box turns green (**CONNECTED**) when the app finds the device.
   * If the status stays **NOT CONNECTED** even though you are on the device's network, click **[Manual Override]**. The app then assumes the device is at `10.22.22.1`, its usual setup address.
3. **Step 2: Configuration.** Enter a **Device Name** (optional, e.g. "Porch light"), your Wi-Fi **SSID** and **Password**.
   * Click **Save** to keep this Wi-Fi as a profile, so the next device takes one click. Profiles are stored in `wifi_profiles.json` in the app data folder (see [Wemo Ops Server and Docker](Wemo-Ops-Server.md#data-folders)).
4. Click **Push Configuration**. The app tries each of the Wi-Fi encryption methods Wemo firmware uses (newer and older firmware differ) until the device accepts one. The **Live Operation Log** shows each try.
5. When the log says **SUCCESS! Rebooting...**, reconnect your computer to your normal Wi-Fi. The device restarts and joins your network; its light stops blinking.
6. The app scans again after 60 and 120 seconds, so the device appears on the **Dashboard** by itself. You can also click **Scan** on the Dashboard.

## If it doesn't work

* **The device never shows up on the Dashboard:** check that your computer is back on your normal Wi-Fi. If your Wemo devices are on a separate IoT network or VLAN, add that subnet on the Dashboard (**Save**) so it's scanned too. See [Troubleshooting](Troubleshooting.md#devices-are-not-found).
* **Every encryption method fails:** double-check the password, and that the network is 2.4 GHz. Very old firmware sometimes only accepts WPA2 (not WPA3 or mixed WPA2/WPA3).
* **The device keeps blinking after "SUCCESS":** it couldn't join your Wi-Fi, usually a wrong password or a 5 GHz-only network. Reset it (hold the button) and try again.
* Please [open an issue](https://github.com/qrussell/wemo-ops-center/issues/new/choose) with the device model, firmware version ([how to find it](Supported-Devices.md#finding-your-firmware-version)) and the text of the Live Operation Log.
