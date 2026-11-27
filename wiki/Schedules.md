# Schedules

Wemo Ops Center has two kinds of schedule. In the desktop app they are the two tabs of **Automation**, and every schedule is labelled with where it runs: **WEMO OPS** or **PLUG**.

| | Run by Wemo Ops (recommended) | Stored on Device (experimental) |
|---|---|---|
| Who runs it | The background service on your computer, or your Wemo Ops Server | The plug's own firmware |
| Must a computer stay on? | Yes, the one running the service or server | No |
| Fixed times | Yes | Yes |
| Sunrise / sunset | Yes, with an offset | Only rules made in the old Wemo app (Wemo Ops can't create them) |
| Devices | Every Wemo device, including Dimmers | Plugs whose firmware supports rules |
| Where to manage it | Desktop app and mobile web app | Desktop app only |
| Works reliably? | Yes | **Depends on firmware. On a Wemo Mini with firmware 2.00.11565 stored rules never ran in our tests** ([#28](https://github.com/qrussell/wemo-ops-center/issues/28)) |

If you're not sure, use **Run by Wemo Ops**.

## Run by Wemo Ops

### Create a schedule

**Desktop app:** **Automation → Run by Wemo Ops**.

1. Pick the **device**.
2. Pick the **action**: Turn ON, Turn OFF or Toggle.
3. Pick the **type**:
   * **Time (Fixed):** enter a 24-hour time, e.g. `18:00`.
   * **Sunrise** or **Sunset:** enter an offset in minutes (e.g. `30`) and choose before or after.
4. Tick the **days** it should run.
5. Click **Create Job**. It appears under **Active Schedules**.

**Mobile web app:** **Rules → New Rule**, with the same options. Both show the same list, because both use the same service or server.

### How they run

* The service checks the list every 30 seconds and runs a schedule in the minute it is due, once per day.
* **If the computer is off or asleep at that minute, the schedule is skipped** (it doesn't catch up later). For lights that must always switch, run a [Wemo Ops Server](Wemo-Ops-Server.md) on an always-on device.
* Times are the local time of the computer or server running the service. In Docker, set `TZ` in `docker-compose.yml`.
* A schedule for a name that several devices share (e.g. three "Wemo Mini") switches all of them.
* Every run is written to `server.log` in the [data folder](Wemo-Ops-Server.md#data-folders), e.g. `Executed Schedule: Porch light (192.168.1.40) -> Turn ON`.

### Sunrise and sunset

* The desktop app finds your approximate location from your internet address (`ipinfo.io`) and gets the day's sunrise and sunset from `api.sunrise-sunset.org`. The location and times are shown at the top of the tab; click **Update Solar Data** to refresh them.
* Sunrise/sunset schedules need internet access for those two lookups. Fixed-time schedules don't need the internet at all.
* **Server without the desktop app** (Docker, or a Linux server, or a desktop app connected to a remote server): the server uses the `lat` and `lng` values in its `settings.json`, which the desktop app only saves on its own computer. Set them on the server once, for example:

  ```bash
  curl -X POST http://<server>:5050/api/settings -H "Content-Type: application/json" -d '{"lat": "40.71", "lng": "-74.01"}'
  ```

  Without a location, sunrise/sunset schedules on that server don't run (fixed-time schedules still do).

### Edit or delete

To change a schedule, delete it (**Del** in the desktop app, 🗑️ in the web app) and create it again.

## Stored on Device (experimental)

Wemo plugs can keep schedules ("rules") in their own memory and run them without any computer. This is how the old Wemo app worked. Since Belkin's cloud shut down, some firmware keeps the rules but never runs them, so treat this as an experiment.

**Desktop app only:** **Automation → Stored on Device (experimental)**.

### See and change a plug's schedules

1. Pick the device and click **Refresh**. The app lists the rules stored on it, including ones made in the old Wemo app.
2. To add one, enter an **ON at** time, an **OFF at** time or both (24-hour; leave one empty for ON only or OFF only), tick the days and click **Save to Device**.
3. You can turn a rule off or on, delete a rule that Wemo Ops made, or **Clear All**.

### Move schedules between the two

* **Push to Device** (on a Wemo Ops schedule): stores a fixed-time Turn ON or Turn OFF schedule on the plug. Sunrise/sunset and Toggle schedules can't be pushed.
* **Copy to Wemo Ops** (on a plug rule): has Wemo Ops run it instead, including sunrise/sunset rules from the old Wemo app. Use this if the plug doesn't switch by itself.
* After either, the app asks whether to turn off the original, so the schedule doesn't run twice.

### Safety

* **Backup before every change.** The plug's rules are saved as a zip in `rules-backups` in the [data folder](Wemo-Ops-Server.md#data-folders), named `<device>_v<version>_<date-time>.zip`. **Restore Backup...** puts one back.
* The app won't write if it can't read the plug's current rules, or if they changed since it read them, and it reads them back after saving ("Stored on the device and read back OK.").
* It sets the plug's clock before saving, because the plug runs rules by its own clock.
* **Maintenance → Reset Data** and **Factory Reset** also erase the plug's rules.

### Check that it works on your plug

Create a rule a few minutes ahead and watch the plug. If it doesn't switch, use **Copy to Wemo Ops**. Please tell us on [issue #28](https://github.com/qrussell/wemo-ops-center/issues/28) or with the [device report form](https://github.com/qrussell/wemo-ops-center/issues/new?template=device_report.yml) whether it worked, with the model and [firmware version](Supported-Devices.md#finding-your-firmware-version).

## Device clocks

Schedules stored on a device (and away mode from the old Wemo app) use the device's own clock. If it is wrong, they run at the wrong time.

* **Desktop app:** **Maintenance → Sync Selected Device** or **Sync All Devices**.
* **Mobile web app:** **Setup → Sync Clocks Now**.
* **Daily:** turn on **Keep device clocks in sync (daily)** in Settings (desktop or web).

The clock and time zone, including daylight saving time, come from the computer or server. Wemo devices can't report their clock back, so the app can't show the device time. Schedules run by Wemo Ops don't depend on device clocks.
