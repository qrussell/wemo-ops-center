# Wemo Ops Center
Welcome to Wemo Ops. We offer three ways to manage your smart home, depending on your needs. You can run the Desktop App for instant control on your workstation, deploy the Server for always-on automation, or use the MCP Server for AI assistant integration.

![Wemo Ops Center Dashboard](assets/wemo-ops.png)

![Version](https://img.shields.io/badge/version-v5.2.3-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)![Model Context Protocol](https://img.shields.io/badge/Model%20Context%20Protocol-1.0-green)
![License](https://img.shields.io/badge/license-MIT-green)
---
**Resurrect your hardware.** The Wemo Cloud is dead, but your devices don't have to be.

Wemo Ops Center is a completely local, offline provisioning and automation suite for Belkin Wemo devices. It allows you to setup, control, automate, and factory reset Wemo plugs and switches without needing the official app or a cloud account.
* Alternative to official Wemo App
* Provision Wemo Devices with Python
* Belkin Wemo local control setup
* Wemo troubleshooting and Wi-Fi profision

## 🚀 Choose Your Edition

| Feature | 🖥️ Desktop App (GUI) | ⚙️ Server App (Headless) | 🤖 MCP Server (AI) |
| :--- | :--- | :--- | :--- |
| **Best For** | Casual users, quick toggling, setup | Power users, Home Labs, 24/7 automation | AI assistant users, MCP developers |
| **Interface** | Native Window (Python/Tkinter) | Web Dashboard (Browser-based) | AI Assistant (Natural language) |
| **Running State** | Runs only when open | Runs 24/7 as a background service | Launched on-demand by AI |
| **OS Support** | Linux (Fedora/Ubuntu), Windows | Linux Server, Raspberry Pi, Docker | Python 3.10+ (Any OS) |
| **Key Benefit** | **Zero Setup.** Just launch and click. | **Set & Forget.** Automation never stops. | **Universal Protocol.** Works with any MCP host. |

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

# Screenshots of the Wemo Ops Center Desktop App
<table>
  <tr>
    <th width="50%">Light Mode</th>
    <th width="50%">Dark Mode</th>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/f27064bc-6aea-49b5-8c86-c4b3d711cfe3" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/c82bc543-431c-4ab3-aec9-286bbdd85fcb" width="100%"></td>
</tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/36bc246b-f470-4049-ab14-1b2b1934baf9" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/b938e228-f0b1-462a-b3a5-38f1cb567306" width="100%"></td>
</tr>
<tr>    
    <td><img src="https://github.com/user-attachments/assets/c5660483-e082-46c3-8290-3c16320a23a9" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/0b09e4e7-12eb-46bc-b669-085fbbf18225" width="100%"></td>
</tr>
<tr>    
    <td><img src="https://github.com/user-attachments/assets/e404b585-71c5-41be-8794-dc484d909e1c" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/03ab35aa-f8e7-4a53-93e5-658d1d689e64" width="100%"></td>
</tr>
<tr>    
<td><img src="https://github.com/user-attachments/assets/dfbe3950-311b-4791-a306-8fb8d40087ab" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/574d2e02-a732-4ae1-9daf-749493197ea1" width="100%"></td>
</tr>
<tr>    
    <td><img src="https://github.com/user-attachments/assets/aa54231a-037e-43ed-8592-b7b0bc751f99" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/c1c62088-b9e9-4116-afe5-838a8fc420dd" width="100%"></td>
  </tr>
</table>

# Screenshots of the Wemo Ops Mobile App

<table>
  <tr>
    <th width="50%">Light Mode</th>
    <th width="50%">Dark Mode</th>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/b78f4831-b7c2-44aa-8a7f-0bcf336652e6" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/c0083f30-aa40-4941-a0a8-884c2bcdcb45" width="100%"></td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/2a4a1471-2138-4c85-9a88-9dbe1e25718d" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/a1d1c3c0-5767-4757-80c9-e9166b73b590" width="100%"></td>
  </tr>
  <tr>    
    <td><img src="https://github.com/user-attachments/assets/3a13f18e-cfbe-4a2c-be1a-63f13c274019" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/18f26f83-a645-485f-bd51-a984cfc99169" width="100%"></td>
  </tr>
</table>>

---
**Go to the [Releases Page](../../releases) and download.**
## 🚀 Key Features (v5.2.3)

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

### 5. Mobile Web App
* **Scan the QR Code:** connect to the mobile web app with your phone or tablet and control your Wemo devices.
* **Local Control:** The app runs on your local network and connects directly to Wemo devices without the cloud.
* **Manage Schedules:** Manage schedules from the mobile web app, solar automation, or time-based schedules.

### ⚠️ Disclaimer
This project is an independent open-source tool and is not affiliated with, endorsed by, or associated with Belkin International, Inc. "Wemo" is a trademark of Belkin International, Inc.

## 🖥️ Option 1: The Desktop App
(Recommended for most users)

* **Wemo Ops Center (Desktop)** is a native application that lives on your computer. It allows you to scan your network, toggle devices on/off instantly, and manage device firmware without needing a dedicated server.

### Why use this?

* **Instant Control:** No web browser needed; just open the app.

* **Portable:** Run it on your laptop and control devices wherever you are on the network.

* **Visual Setup:** Easy-to-use interface for renaming and configuring devices.

* **Multi-Platform Support:** run the app on Windows, macOS, Linux, or Docker. 

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

### Supported deployments:
* RHEL/Rocky/Fedora [Wemo Ops Server Wiki Page](https://github.com/qrussell/wemo-ops-center/wiki/Wemo-Ops-Server)
* Debian/Ubuntu [Wemo Ops Server Wiki Page](https://github.com/qrussell/wemo-ops-center/wiki/Wemo-Ops-Server)
* Docker (see code section [universal-server](https://github.com/qrussell/wemo-ops-center/tree/main/universal-server) )

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

## 🤖 Option 3: MCP Server
(For AI Assistant Integration)

The **WeMo MCP Server** enables natural language control of your WeMo devices through any application that supports the Model Context Protocol (MCP). Works with AI assistants like Claude Desktop, VS Code with GitHub Copilot, and other MCP-compatible tools.

![Claude Desktop controlling WeMo devices](mcp/assets/claude-example.png)

### Why use this?

* **Talk to Your Devices:** Just say "Turn on the office light" or "What devices are on my network?"

* **No GUI Needed:** Control everything through your AI assistant conversations.

* **Universal Protocol:** Works with any MCP host application, not limited to specific tools.

See the **[MCP Server Documentation](mcp/README.md)** for full setup and features.

## 🤝 Better Together: The Hybrid Approach
"Can I use multiple options?" Yes! All three work together seamlessly.

* Use the **Server** to handle the "boring stuff"—keeping schedules running, monitoring device health, and providing a dashboard for your phone.

* Use the **Desktop App** on your workstation for rapid control while you work, or for deep configuration tasks like firmware updates or bulk provisioning.

* Use the **MCP Server** with your AI assistant for quick natural language queries and control during development or daily work.

* All applications can run on the same network and control the same devices simultaneously without conflict.
