# Wemo Ops Center
Welcome to Wemo Ops. We offer two ways to manage your smart home, depending on your needs. You can run the Desktop App for instant control on your workstation, or deploy the Server for always-on automation.

![Wemo Ops Center Dashboard](assets/wemo-ops.png)

![Version](https://img.shields.io/badge/version-v4.2.6-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
---
**Resurrect your hardware.** The Wemo Cloud is dead, but your devices don't have to be.

Wemo Ops Center is a completely local, offline provisioning and automation suite for Belkin Wemo devices. It allows you to setup, control, automate, and factory reset Wemo plugs and switches without needing the official app or a cloud account.

## 🚀 Choose Your Edition

| Feature | 🖥️ Desktop App (GUI) | ⚙️ Server App (Headless) |
| :--- | :--- | :--- |
| **Best For** | Casual users, quick toggling, setup | Power users, Home Labs, 24/7 automation |
| **Interface** | Native Window (Python/Tkinter) | Web Dashboard (Browser-based) |
| **Running State** | Runs only when open | Runs 24/7 as a background service |
| **OS Support** | Linux (Fedora/Ubuntu), Windows | Linux Server, Raspberry Pi, Docker |
| **Key Benefit** | **Zero Setup.** Just launch and click. | **Set & Forget.** Automation never stops. |

# Wemo Ops Center (Desktop)
## 📥 Download & Run

No Python installation required.

1.  **Download:** Go to the [Releases Page](../../releases) and download.
2.  **Provisioner** Follow the on-screen instructions to scan for and configure your Wemo devices.
3.  **Dashboard** Scan Network, Control Devices, and Rename Devices.  IP, MAC, FW ver, SN, and HomeKit code are displayed.

## ⚠️ "Windows protected your PC" Warning
When you launch `WemoOps.exe` for the first time, you may see a blue warning from Microsoft Defender SmartScreen.

**This is normal.** Because this is a free, open-source tool created by an independent developer, it does not have a paid digital signature (which costs hundreds of dollars a year).

**To run the app:**
1. Click **More info**.
2. Click **Run anyway**.
The complete control plane for Belkin Wemo devices.

<table>
  <tr>
    <th width="50%">Light Mode</th>
    <th width="50%">Dark Mode</th>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/49891678-733e-4e44-8eb0-19661c2dce62" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/8a25e527-f515-4a51-97ea-d25c4fb0d557" width="100%"></td>
</tr>
<tr>    
<td><img src="https://github.com/user-attachments/assets/43b87dba-e946-4632-855c-d8cd7a24defc" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/881892f1-87a7-4e4d-ba61-f5cc9e827f5d" width="100%"></td>
</tr>
<tr>    
<td><img src="https://github.com/user-attachments/assets/28a7b09e-2a53-4dcf-87f1-18032ffd3cac" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/cc1fb6dd-a89e-4bbb-b3bd-45b8ee7474c5" width="100%"></td>
</tr>
<tr>    
<td><img src="https://github.com/user-attachments/assets/65850734-de0c-4fda-b6a6-94af1e3957b4" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/e0d28c95-8533-4ab4-9b60-9795a650e527" width="100%"></td>
</tr>
<tr>    
<td><img src="https://github.com/user-attachments/assets/4d01992e-378c-403f-ba28-b6f4582ba96e" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/056196f0-e118-41d6-83ce-fd59fa9bc61c" width="100%"></td>
  </tr>
</table>

---
**Go to the [Releases Page](../../releases) and download.**
## 🚀 Key Features (v4.2.6)

### 1. 📡 Universal Provisioner
* **No Cloud Required:** Connect directly to a new or reset Wemo device's Wi-Fi (`Wemo.Mini.xxx`) and push your Wi-Fi credentials instantly.
* **Smart Encryption Loop:** Automatically detects and applies the correct encryption method (old vs. new firmware) to ensure successful setup.
* **Profile Manager:** Save your Wi-Fi SSID and Password to quickly provision multiple devices in seconds.

### 2. 🎛️ Network Dashboard & VLAN Support
* **Scan Network:** Deep scans your local network to find provisioned devices.
* **VLAN/Subnet Support:** Perfect for IoT setups. You can scan multiple subnets by entering them in a comma-separated list (e.g., `192.168.1.0/24, 10.0.0.0/24`).
* **Smart Deduplication:** Tracks devices by MAC address to prevent ghost entries when IP addresses change.
* **Direct Connect:** Manually add a device by IP address if SSDP discovery fails.

### 3. 🛠️ Maintenance Tools (New)
Advanced tools to manage device health directly from the app:
* **Clear Personal Info:** Removes custom names, icons, and rules.
* **Clear Wi-Fi:** Wipes network credentials to return the device to "Setup Mode" (Flashing Amber/Blue).
* **Factory Reset:** Performs a full "Out of Box" wipe.

### 4. ☀️ Solar Automation Scheduler
* **Local Automation:** Runs on your computer as a background service.
* **Solar Engine:** Automatically detects your latitude/longitude to trigger lights at **Sunrise** or **Sunset**.
* **Fixed Schedules:** Set standard time-based schedules (e.g., "Turn ON at 18:00").

### ⚠️ Disclaimer
This project is an independent open-source tool and is not affiliated with, endorsed by, or associated with Belkin International, Inc. "Wemo" is a trademark of Belkin International, Inc.

## 🖥️ Option 1: The Desktop App
(Recommended for most users)

* **Wemo Ops Center (Desktop)** is a native application that lives on your computer. It allows you to scan your network, toggle devices on/off instantly, and manage device firmware without needing a dedicated server.

### Why use this?

* **Instant Control:** No web browser needed; just open the app.

* **Portable:** Run it on your laptop and control devices wherever you are on the network.

* **Visual Setup:** Easy-to-use interface for renaming and configuring devices.

## 📦 Installation (Linux):

```bash
sudo dnf install wemo-ops       # Fedora / Rocky
```
### OR
```bash
sudo apt install wemo-ops       # Ubuntu / Debian
```
## ⚙️ Option 2: The Automation Server
(For Homelabs & Always-On Automation)

Wemo Ops Server is a lightweight, headless service designed to run on a Raspberry Pi, VM, or Home Server. It provides a Web UI accessible from any device on your network and executes automation schedules even when your computer is turned off.  

Visit the Wemo Ops Server wiki page [Wemo Ops Server Wiki Page](https://github.com/qrussell/wemo-ops-center/wiki/Wemo-Ops-Server)
<table>
  <tr>
    <th width="50%">Dashboard</th>
    <th width="50%">Settings</th>
  </tr>
  <tr>
    <td><img width="981" height="1137" alt="dashboard-dark" src="https://github.com/user-attachments/assets/e946d2c9-af92-4304-b8dd-d9f3108d7497" /></td>
    <td><img width="975" height="1135" alt="settings-dark" src="https://github.com/user-attachments/assets/73c6ac96-6ffb-46f8-b0b3-f97b843223e5" /></td>
  </tr>
  <tr>
    <th width="50%">Automation Time</th>
    <th width="50%">Automation Sunrise/Sunset</th>
  </tr>
  <tr>
    <td><img width="977" height="1137" alt="automation-dark" src="https://github.com/user-attachments/assets/5b5a59fc-6272-43fd-81f6-d601dec3efd2" /></td>
    <td><img width="1005" height="1136" alt="automation2-dark" src="https://github.com/user-attachments/assets/5eb25162-c369-456c-a7ff-eb303857fde4" /></td>
</td>
</tr>
</table>

### Why use this?

* 24/7 Reliability: Your automation schedules (e.g., "Lights on at sunset") run even if your laptop is asleep.

* Any Device Access: Control your home from your phone, tablet, or another PC via the Web Dashboard.

* Low Resource Usage: Optimized to run silently in the background.

## 📦 Installation (Linux):

```bash
sudo dnf install wemo-ops-server  # Fedora / Rocky
```
### OR
```bash
sudo apt install wemo-ops-server  # Ubuntu / Debian
```
## Installation instructions for Wemo Ops Server 
### Debian/Ubuntu or RHEL/Rocky/Fedora Instructions on the Wiki Page:
* Visit the Wemo Ops Server wiki page [Wemo Ops Server Wiki Page](https://github.com/qrussell/wemo-ops-center/wiki/Wemo-Ops-Server)
## 🤝 Better Together: The Hybrid Approach
"Can I use both?" Yes! In fact, this is the most powerful way to use Wemo Ops.

* Use the Server to handle the "boring stuff"—keeping schedules running, monitoring device health, and providing a dashboard for your phone.

* Use the Desktop App on your workstation for rapid control while you work, or for deep configuration tasks like firmware updates or bulk provisioning.

* Both applications can run on the same network and control the same devices simultaneously without conflict.
