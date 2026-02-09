import customtkinter as ctk
import pywemo
import threading
import sys
import os
import time
import json
import requests
import datetime
import socket
import ipaddress
import subprocess
import concurrent.futures
import webbrowser
import re
import tempfile
from tkinter import messagebox
import pyperclip

# --- QR Code & Image Support ---
try:
    import qrcode
    from PIL import Image, ImageTk 
    HAS_QR = True
except ImportError:
    HAS_QR = False

# --- CONFIGURATION ---
VERSION = "v5.1.6-Stable"
SERVER_URL = "http://localhost:5050"  # Port 5050 (Avoids AirPlay)
UPDATE_API_URL = "https://api.github.com/repos/qrussell/wemo-ops-center/releases/latest"
UPDATE_PAGE_URL = "https://github.com/qrussell/wemo-ops-center/releases"

# --- PATH SETUP ---
if sys.platform == "darwin":
    APP_DATA_DIR = os.path.expanduser("~/Library/Application Support/WemoOps")
elif sys.platform == "win32":
    APP_DATA_DIR = os.path.join(os.getenv('APPDATA'), "WemoOps")
else:
    APP_DATA_DIR = os.path.expanduser("~/.local/share/WemoOps")

if not os.path.exists(APP_DATA_DIR):
    try: os.makedirs(APP_DATA_DIR)
    except: pass

PROFILE_FILE = os.path.join(APP_DATA_DIR, "wifi_profiles.json")
SCHEDULE_FILE = os.path.join(APP_DATA_DIR, "schedules.json")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")

# --- SERVICE DETECTION ---
# Defines where the App looks for the background service binary
if sys.platform == "win32":
    SERVICE_EXE_PATH = os.path.join(APP_DATA_DIR, "wemo_service.exe")
else:
    possible_paths = [
        # 1. User Data Folder (Mac Installer Location)
        os.path.join(APP_DATA_DIR, "wemo_service"),
        # 2. Linux System Install
        "/opt/WemoOps/wemo_service",
        # 3. Standard Bin
        "/usr/bin/wemo_service"
    ]
    SERVICE_EXE_PATH = None
    for p in possible_paths:
        if os.path.exists(p):
            SERVICE_EXE_PATH = p
            break
    # Fallback if not found (default to Mac path for creation)
    if not SERVICE_EXE_PATH:
        SERVICE_EXE_PATH = os.path.join(APP_DATA_DIR, "wemo_service")

if getattr(sys, 'frozen', False):
    os.environ['PATH'] += os.pathsep + sys._MEIPASS

# --- STYLING CONSTANTS ---
COLOR_BG = ("#ebebeb", "#242424")           
COLOR_SIDEBAR = ("#d6d6d6", "#1a1a1a")      
COLOR_CARD = ("#ffffff", "#2b2b2b")         
COLOR_FRAME = ("#cccccc", "#333333")        
COLOR_TEXT = ("#1a1a1a", "#ffffff")         
COLOR_SUBTEXT = ("#404040", "#aaaaaa")      
COLOR_ACCENT = ("#1f6aa5", "#1f6aa5")       
COLOR_SUCCESS = ("#2d8a4e", "#28a745")      
COLOR_DANGER = ("#c0392b", "#aa3333")       
COLOR_UPDATE = ("#d35400", "#e67e22")       
COLOR_BTN_SECONDARY = ("#e0e0e0", "#3a3a3a") 
COLOR_BTN_TEXT = ("#1a1a1a", "#ffffff")
COLOR_MAINT_BTN_Y = ("#d68910", "#e6b800") 
COLOR_MAINT_BTN_B = ("#2874a6", "#5599ee")
COLOR_MAINT_BTN_R = ("#922b21", "#cc0000")

FONT_H1 = ("Roboto", 24, "bold")
FONT_H2 = ("Roboto", 18, "bold")
FONT_BODY = ("Roboto", 14)
FONT_MONO = ("Consolas", 13)

# ==============================================================================
#  API CLIENT
# ==============================================================================
class APIClient:
    def __init__(self):
        self.connected = False
        self.server_ip = "127.0.0.1"
        self.remote_scan_status = ""

    def check_connection(self):
        try:
            r = requests.get(f"{SERVER_URL}/api/status", timeout=0.5)
            if r.status_code == 200:
                self.connected = True
                data = r.json()
                self.remote_scan_status = data.get("scan_status", "")
                return True
        except: pass
        self.connected = False
        return False

    def trigger_scan(self):
        try: requests.post(f"{SERVER_URL}/api/scan", timeout=1)
        except: pass

    def set_server_subnet(self, subnet_cidr):
        """Pushes the target subnet to the server for deep scanning."""
        try:
            r = requests.post(f"{SERVER_URL}/api/config/subnet", json={"subnet": subnet_cidr}, timeout=2)
            return r.status_code == 200
        except: return False

    def get_devices(self):
        try: return requests.get(f"{SERVER_URL}/api/devices", timeout=2).json()
        except: return []

    def toggle_device(self, name):
        try: requests.post(f"{SERVER_URL}/api/toggle/{name}", timeout=1)
        except: pass

    def get_schedules(self):
        try: return requests.get(f"{SERVER_URL}/api/schedules", timeout=2).json()
        except: return []

    def add_schedule(self, data):
        try: 
            r = requests.post(f"{SERVER_URL}/api/schedules", json=data, timeout=2)
            return r.status_code == 200
        except: return False

    def delete_schedule(self, jid):
        try: requests.delete(f"{SERVER_URL}/api/schedules?id={jid}", timeout=2)
        except: pass

    def reset_device(self, name, code):
        try:
            r = requests.post(f"{SERVER_URL}/api/maintenance/reset", json={"device": name, "code": code}, timeout=3)
            return r.status_code == 200
        except: return False

# ==============================================================================
#  UPDATE MANAGER
# ==============================================================================
class UpdateManager:
    @staticmethod
    def check_for_updates(current_version_str, api_url):
        if not api_url: return False, None
        try:
            headers = {'User-Agent': 'WemoOps-Updater'}
            r = requests.get(api_url, headers=headers, timeout=3)
            if r.status_code == 200:
                data = r.json()
                remote_tag = data.get("tag_name", "").strip() 
                if not remote_tag: return False, None
                
                curr_clean = re.search(r'(\d+\.\d+\.\d+)', current_version_str)
                rem_clean = re.search(r'(\d+\.\d+\.\d+)', remote_tag)
                
                if curr_clean and rem_clean:
                    c_parts = [int(x) for x in curr_clean.group(1).split('.')]
                    r_parts = [int(x) for x in rem_clean.group(1).split('.')]
                    if r_parts > c_parts: return True, remote_tag
                elif remote_tag != current_version_str:
                    return True, remote_tag
        except: pass
        return False, None

# ==============================================================================
#  NETWORK UTILS
# ==============================================================================
class NetworkUtils:
    @staticmethod
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except: return "127.0.0.1"

    @staticmethod
    def get_subnet_cidr():
        try:
            if sys.platform.startswith("linux"):
                cmd = "ip -o -f inet addr show | awk '/scope global/ {print $4}'"
                output = subprocess.check_output(cmd, shell=True).decode().strip()
                return output.split('\n')[0]
            elif sys.platform == "darwin":
                local_ip = NetworkUtils.get_local_ip()
                return f"{local_ip}/24"
            elif sys.platform == "win32":
                local_ip = NetworkUtils.get_local_ip()
                return f"{local_ip}/24"
        except: pass
        ip = NetworkUtils.get_local_ip()
        return f"{ip}/24"

    @staticmethod
    def scan_wifi_networks():
        wemos = []
        try:
            if sys.platform.startswith("linux"):
                output = subprocess.check_output("nmcli -t -f SSID dev wifi", shell=True).decode('utf-8', errors='ignore')
                for line in output.split('\n'):
                    if line.strip(): wemos.append(line.strip())
            elif sys.platform == "darwin":
                airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
                if os.path.exists(airport_path):
                    output = subprocess.check_output(f"{airport_path} -s", shell=True).decode('utf-8', errors='ignore')
                    lines = output.split('\n')[1:] 
                    for line in lines:
                        parts = line.strip().split()
                        if parts: wemos.append(parts[0])
            elif sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                output = subprocess.check_output("netsh wlan show networks mode=bssid", startupinfo=si).decode('utf-8', errors='ignore')
                for line in output.split('\n'):
                    line = line.strip()
                    if line.startswith("SSID"):
                        ssid = line.split(":", 1)[1].strip()
                        if ssid: wemos.append(ssid)
        except Exception as e: pass
        return [ssid for ssid in list(set(wemos)) if "wemo" in ssid.lower() or "belkin" in ssid.lower()]

# ==============================================================================
#  WIFI AUTOMATOR
# ==============================================================================
class WifiAutomator:
    @staticmethod
    def can_automate():
        return sys.platform in ["win32", "linux", "darwin"]

    @staticmethod
    def connect_open_network(ssid):
        try:
            if sys.platform == "win32":
                hex_ssid = ssid.encode('utf-8').hex()
                xml_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <hex>{hex_ssid}</hex>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
        </security>
    </MSM>
</WLANProfile>"""
                fd, path = tempfile.mkstemp(suffix=".xml")
                with os.fdopen(fd, 'w') as tmp:
                    tmp.write(xml_content)
                subprocess.run(['netsh', 'wlan', 'add', 'profile', f'filename={path}'], check=True, creationflags=0x08000000)
                os.remove(path)
                subprocess.run(['netsh', 'wlan', 'connect', f'name={ssid}'], check=True, creationflags=0x08000000)
                return True
            elif sys.platform.startswith("linux"):
                subprocess.run(['nmcli', 'dev', 'wifi', 'connect', ssid], check=True)
                return True
            elif sys.platform == "darwin":
                subprocess.run(['networksetup', '-setairportnetwork', 'en0', ssid], check=True)
                return True
        except Exception as e:
            print(f"Connection Failed: {e}")
            return False
        return False

# ==============================================================================
#  DEEP SCANNER
# ==============================================================================
class DeepScanner:
    def probe_port(self, ip, port=49153, timeout=0.3):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((str(ip), port))
            s.close()
            return str(ip)
        except: return None

    def scan_subnet(self, target_cidr=None, status_callback=None):
        found_devices = []
        cidrs = [c.strip() for c in target_cidr.split(',')] if target_cidr else [NetworkUtils.get_subnet_cidr()]
        
        all_hosts = []
        for cidr in cidrs:
            if not cidr: continue
            try:
                if status_callback: status_callback(f"Preparing: {cidr}")
                network = ipaddress.ip_network(cidr, strict=False)
                all_hosts.extend(list(network.hosts()))
            except: pass

        if not all_hosts: return []

        active_ips = []
        if status_callback: status_callback(f"Probing {len(all_hosts)} IPs...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=150) as executor:
            futures = {executor.submit(self.probe_port, ip): ip for ip in all_hosts}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result: active_ips.append(result)

        if status_callback: status_callback(f"Verifying {len(active_ips)} hosts...")
        
        for ip in active_ips:
            try:
                url = f"http://{ip}:49153/setup.xml"
                dev = pywemo.discovery.device_from_description(url)
                if dev: found_devices.append(dev)
            except:
                try:
                    url_alt = f"http://{ip}:49152/setup.xml"
                    dev = pywemo.discovery.device_from_description(url_alt)
                    if dev: found_devices.append(dev)
                except: pass
        return found_devices

# ==============================================================================
#  SOLAR ENGINE
# ==============================================================================
class SolarEngine:
    def __init__(self):
        self.lat = None
        self.lng = None
        self.solar_times = {} 
        self.last_fetch = None

    def detect_location(self):
        try:
            r = requests.get("https://ipinfo.io/json", timeout=2)
            data = r.json()
            loc = data.get("loc", "").split(",")
            if len(loc) == 2:
                self.lat, self.lng = loc[0], loc[1]
                return True
        except: pass
        return False

    def get_solar_times(self):
        today = datetime.date.today()
        if self.last_fetch == today and self.solar_times: return self.solar_times
        if not self.lat:
            if not self.detect_location(): return None

        try:
            url = f"https://api.sunrise-sunset.org/json?lat={self.lat}&lng={self.lng}&formatted=0"
            r = requests.get(url, timeout=5)
            data = r.json()
            if data["status"] == "OK":
                res = data["results"]
                def to_local(utc_str):
                    try:
                        dt_utc = datetime.datetime.fromisoformat(utc_str)
                        dt_local = dt_utc.astimezone()
                        return dt_local.strftime("%H:%M")
                    except: return "00:00"
                self.solar_times = {
                    "sunrise": to_local(res["sunrise"]),
                    "sunset": to_local(res["sunset"])
                }
                self.last_fetch = today
                return self.solar_times
        except: pass
        return None

# ==============================================================================
#  MAIN APPLICATION
# ==============================================================================
class WemoOpsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Wemo Ops Center {VERSION}")
        self.geometry("1100x800") 
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- HYBRID STATE ---
        self.api = APIClient()
        self.use_api_mode = False  # If True, Server handles logic.

        self.settings = self.load_json(SETTINGS_FILE, dict)
        
        theme = self.settings.get("theme", "System")
        scale = self.settings.get("scale", "100%")
        ctk.set_appearance_mode(theme)
        self.set_ui_scale(scale)

        self.current_setup_ip = None 
        self.current_setup_port = None 
        self.manual_override_active = False 
        
        self.profiles = self.load_json(PROFILE_FILE, dict)
        self.schedules = self.load_json(SCHEDULE_FILE, list) or []
        self.saved_subnets = self.settings.get("subnets", [])
        
        self.known_devices_map = {} 
        self.solar = SolarEngine()
        self.scanner = DeepScanner()

        if "lat" in self.settings:
            self.solar.lat = self.settings["lat"]
            self.solar.lng = self.settings["lng"]

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="WEMO OPS", font=("Arial Black", 22), text_color=COLOR_TEXT)
        self.logo.pack(pady=25)
        
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "app_icon.ico")
        if sys.platform.startswith("win"):
            try: self.iconbitmap(icon_path)
            except: pass

        self.btn_dash = self.create_nav_btn("Dashboard", "dash")
        self.btn_prov = self.create_nav_btn("Provisioner", "prov")
        self.btn_sched = self.create_nav_btn("Automation", "sched")
        self.btn_maint = self.create_nav_btn("Maintenance", "maint")
        
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)
        
        # QR Code Button
        if HAS_QR:
            ctk.CTkButton(self.sidebar, text="📱 Mobile App", fg_color=COLOR_ACCENT, command=self.show_qr_code).pack(pady=5, padx=10)
        
        self.btn_settings = self.create_nav_btn("Settings", "settings")

        self.service_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.service_frame.pack(side="bottom", fill="x", pady=20, padx=10)
        self.svc_lbl = ctk.CTkLabel(self.service_frame, text="Server Connection:", font=("Arial", 12, "bold"), text_color=COLOR_TEXT)
        self.svc_lbl.pack(anchor="w")
        
        self.svc_status = ctk.CTkLabel(self.service_frame, text="Checking...", text_color="gray", font=FONT_BODY)
        self.svc_status.pack(anchor="w")

        # --- NEW START BUTTON ---
        # This button allows manual start if the background service fails
        self.btn_start_svc = ctk.CTkButton(
            self.service_frame, 
            text="▶ Start Server", 
            width=100, 
            height=24,
            fg_color="#2d8a4e", 
            command=self.start_local_server
        )
        self.btn_start_svc.pack(pady=(5,0), anchor="w")
        
        # --- UPDATE BUTTON ---
        self.btn_update = ctk.CTkButton(self.sidebar, text="⬇ Update Available", fg_color=COLOR_UPDATE, 
                                        font=FONT_BODY, command=lambda: webbrowser.open(UPDATE_PAGE_URL))
        self.btn_update.pack(side="bottom", padx=10, pady=(0, 10))
        self.btn_update.pack_forget()

        ctk.CTkLabel(self.sidebar, text=f"{VERSION}", text_color="gray", font=("Arial", 10)).pack(side="bottom", pady=5)

        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=20)

        self.frames = {}
        self.create_dashboard()
        self.create_provisioner()
        self.create_schedule_ui()
        self.create_maintenance_ui()
        self.create_settings_ui() 

        self.show_tab("dash")
        
        # Start Threads
        self.monitoring = True
        threading.Thread(target=self._connection_monitor, daemon=True).start()
        threading.Thread(target=self._scheduler_engine, daemon=True).start()
        threading.Thread(target=self.run_update_check, daemon=True).start()
        
        # Start Server Heartbeat (Kickoff)
        self.after(1000, self.heartbeat_loop)

    # --- SERVER MANAGEMENT (Restored Feature) ---
    def start_local_server(self):
        """Attempts to launch the backend server manually."""
        if self.api.check_connection():
            messagebox.showinfo("Status", "Server is already running!")
            return

        # 1. Locate the Binary
        binary_path = SERVICE_EXE_PATH
        
        # Fallback for Development (Running from source)
        if not binary_path or not os.path.exists(binary_path):
            if os.path.exists("wemo_server.py"):
                # Dev mode: run python script
                cmd = [sys.executable, "wemo_server.py"]
            else:
                messagebox.showerror("Error", f"Cannot find server binary at:\n{binary_path}\n\nPlease reinstall or check permissions.")
                return
        else:
            # Prod mode: run executable
            cmd = [binary_path]

        try:
            # 2. Launch in Background (Non-blocking)
            self.svc_status.configure(text="Starting...", text_color="orange")
            
            # Windows needs specific flags to hide the console window
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.Popen(cmd, startupinfo=startupinfo)
            
            # 3. Wait and Verify
            self.after(3000, self._force_heartbeat_check)
            
        except Exception as e:
            messagebox.showerror("Launch Error", str(e))

    def _force_heartbeat_check(self):
        if self.api.check_connection():
            self._update_heartbeat_ui(True)
            messagebox.showinfo("Success", "Server started successfully!")
        else:
            self.svc_status.configure(text="Start Failed", text_color="red")
            messagebox.showwarning("Timeout", "Server started but is not responding yet.\nIt might be initializing or blocked.")

    # --- HYBRID HEARTBEAT LOOP ---
    def heartbeat_loop(self):
        threading.Thread(target=self._heartbeat_task, daemon=True).start()
        self.after(3000, self.heartbeat_loop)

    def _heartbeat_task(self):
        is_online = self.api.check_connection()
        self.after(0, lambda: self._update_heartbeat_ui(is_online))

        if is_online:
            server_schedules = self.api.get_schedules()
            if server_schedules:
                self.schedules = server_schedules
        else:
            self.schedules = self.load_json(SCHEDULE_FILE, list) or []

    def _update_heartbeat_ui(self, is_online):
        self.use_api_mode = is_online
        if is_online:
            txt = "✅ CONNECTED"
            # Add scanning indicator if server is busy
            if "Scanning" in self.api.remote_scan_status:
                txt += "\n(Scanning...)"
            
            self.svc_status.configure(text=txt, text_color=COLOR_SUCCESS)
            # Hide button if connected
            self.btn_start_svc.pack_forget() 
        else:
            self.svc_status.configure(text="⚠️ STANDALONE", text_color="orange")
            # Show button if disconnected
            self.btn_start_svc.pack(pady=(5,0), anchor="w")

    # --- UPDATE CHECKER LOGIC ---
    def run_update_check(self):
        has_update, new_ver = UpdateManager.check_for_updates(VERSION, UPDATE_API_URL)
        if has_update:
            self.after(0, lambda: self.show_update_btn(new_ver))

    def show_update_btn(self, new_ver):
        self.btn_update.configure(text=f"⬇ Get {new_ver}")
        self.btn_update.pack(side="bottom", padx=10, pady=(0, 10))

    # --- UI HELPERS ---
    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def create_nav_btn(self, text, view_name):
        btn = ctk.CTkButton(self.sidebar, text=f"  {text}", anchor="w", 
                            font=FONT_BODY, height=40,
                            fg_color="transparent", text_color=COLOR_TEXT,
                            hover_color=COLOR_FRAME,
                            command=lambda: self.show_tab(view_name))
        btn.pack(pady=2, padx=10, fill="x")
        setattr(self, f"btn_{view_name}", btn)
        return btn

    def show_tab(self, name):
        for key, frame in self.frames.items(): frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        for key in ["dash", "prov", "sched", "maint", "settings"]:
            btn = getattr(self, f"btn_{key}")
            btn.configure(fg_color="transparent", text_color=COLOR_TEXT)
        active_btn = getattr(self, f"btn_{name}")
        active_btn.configure(fg_color=COLOR_FRAME, text_color=COLOR_TEXT)

    # --- SETTINGS TAB ---
    def create_settings_ui(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["settings"] = frame
        ctk.CTkLabel(frame, text="Application Settings", font=FONT_H1, text_color=COLOR_TEXT).pack(pady=(0, 20), anchor="w")
        card = ctk.CTkFrame(frame, fg_color=COLOR_CARD)
        card.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(card, text="Appearance & Display", font=FONT_H2, text_color=COLOR_TEXT).pack(padx=20, pady=(15,5), anchor="w")
        
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(r1, text="Theme Mode:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left")
        self.theme_var = ctk.StringVar(value=self.settings.get("theme", "System"))
        theme_menu = ctk.CTkComboBox(r1, values=["System", "Light", "Dark"], 
                                       command=self.change_theme, variable=self.theme_var,
                                       state="readonly", width=150, font=FONT_BODY)
        theme_menu.pack(side="right")

        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(r2, text="UI Scaling:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left")
        self.scale_var = ctk.StringVar(value=self.settings.get("scale", "100%"))
        scale_menu = ctk.CTkComboBox(r2, values=["80%", "90%", "100%", "110%", "120%", "150%"], 
                                       command=self.change_scaling, variable=self.scale_var,
                                       state="readonly", width=150, font=FONT_BODY)
        scale_menu.pack(side="right")

    def change_theme(self, new_theme):
        ctk.set_appearance_mode(new_theme)
        self.settings["theme"] = new_theme
        self.save_json(SETTINGS_FILE, self.settings)

    def change_scaling(self, new_scale):
        self.set_ui_scale(new_scale)
        self.settings["scale"] = new_scale
        self.save_json(SETTINGS_FILE, self.settings)

    def set_ui_scale(self, scale_str):
        scale_float = int(scale_str.replace("%", "")) / 100
        ctk.set_widget_scaling(scale_float)

    # --- DASHBOARD ---
    def create_dashboard(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["dash"] = frame
        
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(head, text="Network Overview", font=FONT_H1, text_color=COLOR_TEXT).pack(side="left")

        scan_ctrl = ctk.CTkFrame(head, fg_color="transparent")
        scan_ctrl.pack(side="right")
        self.subnet_combo = ctk.CTkComboBox(scan_ctrl, width=200, values=self.saved_subnets, font=FONT_BODY)
        self.subnet_combo.pack(side="left", padx=5)
        self.subnet_combo.set(NetworkUtils.get_subnet_cidr()) 
        ctk.CTkButton(scan_ctrl, text="Save", width=50, command=self.save_subnet, fg_color=COLOR_ACCENT).pack(side="left", padx=2)
        ctk.CTkButton(scan_ctrl, text="Del", width=50, fg_color=COLOR_DANGER, command=self.delete_subnet).pack(side="left", padx=(2, 10))
        ctk.CTkButton(scan_ctrl, text="Scan Network", width=120, command=self.refresh_network, fg_color=COLOR_ACCENT).pack(side="left", padx=5)
        self.scan_status = ctk.CTkLabel(scan_ctrl, text="", text_color="orange", font=FONT_BODY)
        self.scan_status.pack(side="left", padx=10)

        manual_frame = ctk.CTkFrame(frame, fg_color=COLOR_FRAME)
        manual_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(manual_frame, text="Direct Connect:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left", padx=10)
        self.ip_entry = ctk.CTkEntry(manual_frame, placeholder_text="192.168.1.x", width=150, font=FONT_BODY)
        self.ip_entry.pack(side="left", padx=5, pady=10)
        ctk.CTkButton(manual_frame, text="Add Device", width=100, fg_color=COLOR_BTN_SECONDARY, text_color=COLOR_BTN_TEXT, command=self.manual_add_device).pack(side="left", padx=5)
        
        self.dev_list = ctk.CTkScrollableFrame(frame, label_text="Discovered Devices", label_text_color=COLOR_TEXT, label_font=FONT_H2)
        self.dev_list.pack(fill="both", expand=True)

    def save_subnet(self):
        val = self.subnet_combo.get().strip()
        if val and val not in self.saved_subnets:
            self.saved_subnets.append(val)
            self.settings["subnets"] = self.saved_subnets
            self.save_json(SETTINGS_FILE, self.settings)
            self.subnet_combo.configure(values=self.saved_subnets)
        
        # --- SYNC TO SERVER ---
        if self.use_api_mode and val:
            threading.Thread(target=self._sync_subnet_task, args=(val,), daemon=True).start()

    def _sync_subnet_task(self, val):
        if self.api.set_server_subnet(val):
            # Optimistic update - nothing visual needed unless failure
            pass
        else:
            print("Warning: Failed to sync subnet to server.")

    def delete_subnet(self):
        val = self.subnet_combo.get().strip()
        if val in self.saved_subnets:
            self.saved_subnets.remove(val)
            self.settings["subnets"] = self.saved_subnets
            self.save_json(SETTINGS_FILE, self.settings)
            self.subnet_combo.configure(values=self.saved_subnets)
            if self.saved_subnets: self.subnet_combo.set(self.saved_subnets[0])
            else: self.subnet_combo.set("")

    def refresh_network(self):
        if self.use_api_mode:
            # --- FIX: Trigger Remote Scan ---
            self.scan_status.configure(text="Requesting Server Scan...")
            threading.Thread(target=self._trigger_remote_scan, daemon=True).start()
        else:
            self.known_devices_map.clear()
            for w in self.dev_list.winfo_children(): w.destroy()
            manual_subnet = self.subnet_combo.get().strip()
            self.scan_status.configure(text="Local Scanning...")
            threading.Thread(target=self._scan_thread, args=(manual_subnet,), daemon=True).start()

    def _trigger_remote_scan(self):
        # 1. Push config if available (ensure server has latest scan target)
        val = self.subnet_combo.get().strip()
        if val:
            self.api.set_server_subnet(val)
            
        # 2. Trigger Scan
        self.api.trigger_scan()
        
        # 3. Wait briefly for scan to initiate, then fetch whatever is currently known
        time.sleep(1)
        self._fetch_api_devices()

    def _fetch_api_devices(self):
        devs = self.api.get_devices()
        
        # Populate known devices (as dicts/structs) so dropdowns work
        self.known_devices_map.clear()
        for d in devs:
            # Create a simple object to mimic pywemo device for the UI
            vdev = type('VirtualDevice', (object,), {'name': d['name'], 'host': d['ip']})
            self.known_devices_map[d['name']] = vdev
            
        self.after(0, lambda: self.update_dashboard_api(devs))
        self.after(0, self.update_maint_dropdown)
        self.after(0, self.update_schedule_dropdown)
        self.after(0, lambda: self.scan_status.configure(text=""))

    def update_dashboard_api(self, devices):
        for w in self.dev_list.winfo_children(): w.destroy()
        if not devices: ctk.CTkLabel(self.dev_list, text="No devices found on Server.", text_color=COLOR_TEXT).pack(pady=20)
        
        for d in devices:
            self.build_device_card_api(d)

    def build_device_card_api(self, dev):
        card = ctk.CTkFrame(self.dev_list, fg_color=COLOR_CARD, border_width=1, border_color=COLOR_FRAME)
        card.pack(fill="x", pady=5, padx=5)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(top, text=f"{dev['name']}", font=FONT_H2, text_color=COLOR_TEXT).pack(side="left")
        
        def toggle(): threading.Thread(target=self.api.toggle_device, args=(dev['name'],), daemon=True).start()
        switch = ctk.CTkSwitch(top, text="Power", command=toggle, font=FONT_BODY, text_color=COLOR_TEXT)
        switch.pack(side="right")
        if dev.get('state', 0): switch.select()

        mid = ctk.CTkFrame(card, fg_color="transparent")
        mid.pack(fill="x", padx=10, pady=0)
        ctk.CTkLabel(mid, text=f"IP: {dev['ip']} (Managed by Server)", font=FONT_MONO, text_color=COLOR_SUBTEXT).pack(anchor="w")

    def _scan_thread(self, target_subnet):
        def update_status(msg): self.after(0, lambda: self.scan_status.configure(text=msg))
        try:
            update_status("Quick Scan (SSDP)...")
            devices = pywemo.discover_devices()
            for d in devices: 
                key = getattr(d, 'mac', d.name)
                self.known_devices_map[key] = d
            update_status("Deep Subnet Scan...")
            deep_devices = self.scanner.scan_subnet(target_cidr=target_subnet, status_callback=update_status)
            for d in deep_devices:
                key = getattr(d, 'mac', d.name)
                self.known_devices_map[key] = d
            update_status("")
            self.after(0, self.update_dashboard, list(self.known_devices_map.values()))
            self.after(0, self.update_maint_dropdown)
            self.after(0, self.update_schedule_dropdown)
        except Exception as e:
            update_status("Error")

    def update_dashboard(self, devices):
        for w in self.dev_list.winfo_children(): w.destroy()
        if not devices: ctk.CTkLabel(self.dev_list, text="No devices found.", text_color=COLOR_TEXT).pack(pady=20)
        devices.sort(key=lambda x: x.name)
        for dev in devices:
            self.build_device_card(dev)

    def build_device_card(self, dev):
        try: mac = getattr(dev, 'mac', "Unknown")
        except: mac = "Unknown"
        try: serial = getattr(dev, 'serial_number', "Unknown")
        except: serial = "Unknown"
        
        card = ctk.CTkFrame(self.dev_list, fg_color=COLOR_CARD, border_width=1, border_color=COLOR_FRAME)
        card.pack(fill="x", pady=5, padx=5)
        
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(top, text=f"{dev.name}", font=FONT_H2, text_color=COLOR_TEXT).pack(side="left")
        
        def toggle(): threading.Thread(target=dev.toggle, daemon=True).start()
        switch = ctk.CTkSwitch(top, text="Power", command=toggle, font=FONT_BODY, text_color=COLOR_TEXT)
        switch.pack(side="right")
        
        def fetch_state():
            try:
                state = dev.get_state()
                if state: self.after(0, switch.select)
            except: pass
        threading.Thread(target=fetch_state, daemon=True).start()

        mid = ctk.CTkFrame(card, fg_color="transparent")
        mid.pack(fill="x", padx=10, pady=0)
        ctk.CTkLabel(mid, text=f"IP: {dev.host} | MAC: {mac} | SN: {serial}", font=FONT_MONO, text_color=COLOR_SUBTEXT).pack(anchor="w")
        
        bot = ctk.CTkFrame(card, fg_color="transparent")
        bot.pack(fill="x", padx=10, pady=(5, 10))
        
        def rename_action():
            new_name = ctk.CTkInputDialog(text="Name:", title="Rename").get_input()
            if new_name: threading.Thread(target=self._rename_task, args=(dev, new_name), daemon=True).start()
        ctk.CTkButton(bot, text="> Rename", width=80, height=24, fg_color=COLOR_BTN_SECONDARY, text_color=COLOR_BTN_TEXT, command=rename_action).pack(side="left", padx=(0, 10))
        
        def extract_hk(): threading.Thread(target=self._extract_hk_task, args=(dev,), daemon=True).start()
        ctk.CTkButton(bot, text="Get HomeKit Code", width=120, height=24, fg_color=COLOR_BTN_SECONDARY, text_color=COLOR_BTN_TEXT, command=extract_hk).pack(side="left")

    def _rename_task(self, dev, new_name):
        try:
            if hasattr(dev, 'change_friendly_name'): dev.change_friendly_name(new_name)
            elif hasattr(dev, 'basicevent'): dev.basicevent.ChangeFriendlyName(FriendlyName=new_name)
            self.after(0, lambda: messagebox.showinfo("Success", "Renamed."))
            self.after(0, self.refresh_network)
        except: pass

    def _extract_hk_task(self, dev):
        try:
            if hasattr(dev, 'basicevent'):
                data = dev.basicevent.GetHKSetupInfo()
                code = data.get('HKSetupCode')
                if code:
                    self.after(0, lambda: messagebox.showinfo("Code", code))
                    try: pyperclip.copy(code)
                    except: pass
                else: self.after(0, lambda: messagebox.showwarning("Error", "No Code Found"))
        except: pass

    def manual_add_device(self):
        ip = self.ip_entry.get()
        if not ip: return
        threading.Thread(target=self._manual_add_task, args=(ip,), daemon=True).start()

    def _manual_add_task(self, ip):
        try:
            url = f"http://{ip}:49153/setup.xml"
            dev = pywemo.discovery.device_from_description(url)
            if dev:
                self.after(0, lambda: self.build_device_card(dev))
                self.after(0, lambda: messagebox.showinfo("Success", f"Added {dev.name}"))
            else: self.after(0, lambda: messagebox.showwarning("Failed", "No device found."))
        except Exception as e: self.after(0, lambda: messagebox.showerror("Error", str(e)))

    # --- PROVISIONER ---
    def create_provisioner(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["prov"] = frame
        frame.columnconfigure(0, weight=1); frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)
        
        left_col = ctk.CTkFrame(frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(left_col, text="Step 1: Locate Device", font=FONT_H2, text_color=COLOR_TEXT).pack(anchor="w", pady=(0,5))
        
        scan_frame = ctk.CTkFrame(left_col, fg_color=COLOR_FRAME)
        scan_frame.pack(fill="x", pady=(0, 20))
        self.btn_scan_setup = ctk.CTkButton(scan_frame, text="Scan Airwaves", command=self.scan_ssids, fg_color=COLOR_ACCENT)
        self.btn_scan_setup.pack(pady=10, padx=10, fill="x")
        self.ssid_list = ctk.CTkScrollableFrame(scan_frame, height=100, label_text="Nearby Networks", label_text_color=COLOR_TEXT)
        self.ssid_list.pack(fill="x", padx=10, pady=(0,10))
        
        ctk.CTkLabel(left_col, text="Step 2: Configuration", font=FONT_H2, text_color=COLOR_TEXT).pack(anchor="w", pady=(0,5))
        input_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        input_frame.pack(fill="x")
        prof_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        prof_row.pack(fill="x", pady=5)
        self.profile_combo = ctk.CTkComboBox(prof_row, values=["Select Saved Profile..."] + list(self.profiles.keys()), command=self.apply_profile, width=200)
        self.profile_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(prof_row, text="Save", width=50, command=self.save_current_profile, fg_color=COLOR_ACCENT).pack(side="left", padx=5)
        ctk.CTkButton(prof_row, text="Del", width=50, fg_color=COLOR_DANGER, hover_color="#882222", command=self.delete_profile).pack(side="left")
        
        self.name_entry = ctk.CTkEntry(input_frame, placeholder_text="Device Name (e.g. Office Fan)")
        self.name_entry.pack(fill="x", pady=5)
        self.ssid_entry = ctk.CTkEntry(input_frame, placeholder_text="SSID")
        self.ssid_entry.pack(fill="x", pady=5)
        self.pass_entry = ctk.CTkEntry(input_frame, placeholder_text="Password", show="*")
        self.pass_entry.pack(fill="x", pady=5)
        
        self.prov_btn = ctk.CTkButton(left_col, text="Push Configuration", fg_color=COLOR_SUCCESS, hover_color="#1e7e34", height=50, state="disabled", command=self.run_provision_thread)
        self.prov_btn.pack(fill="x", pady=20)
        
        right_col = ctk.CTkFrame(frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")
        self.status_frame = ctk.CTkFrame(right_col, fg_color=("#fadbd8", "#331111"), border_color="#ff5555", border_width=2)
        self.status_frame.pack(fill="x", pady=(0, 10))
        self.status_lbl_icon = ctk.CTkLabel(self.status_frame, text="X", font=("Arial", 30))
        self.status_lbl_icon.pack(side="left", padx=15, pady=15)
        stat_txt = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        stat_txt.pack(side="left", fill="x")
        self.status_lbl_text = ctk.CTkLabel(stat_txt, text="NOT CONNECTED", font=FONT_H2, text_color="#ff5555")
        self.status_lbl_text.pack(anchor="w")
        self.status_lbl_sub = ctk.CTkLabel(stat_txt, text="Connect Wi-Fi to 'Wemo.Mini.XXX'", font=FONT_BODY, text_color=COLOR_TEXT)
        self.status_lbl_sub.pack(anchor="w")
        
        self.override_link = ctk.CTkLabel(right_col, text="[Manual Override]", font=("Arial", 10, "underline"), text_color="gray", cursor="hand2")
        self.override_link.pack(anchor="e", pady=(0, 5))
        self.override_link.bind("<Button-1>", lambda e: self.force_unlock())
        
        ctk.CTkLabel(right_col, text="Live Operation Log", font=FONT_BODY, text_color=COLOR_TEXT).pack(anchor="w")
        self.prov_log = ctk.CTkTextbox(right_col, font=FONT_MONO, activate_scrollbars=True)
        self.prov_log.pack(fill="both", expand=True)

    def run_provision_thread(self):
        ssid = self.ssid_entry.get()
        pwd = self.pass_entry.get()
        name = self.name_entry.get()
        if not ssid: 
            messagebox.showwarning("Missing Data", "Enter SSID.")
            return
        target_ip = self.current_setup_ip or "10.22.22.1"
        target_port = self.current_setup_port 
        self.prov_btn.configure(state="disabled", text="Running...")
        self.prov_log.delete("1.0", "end")
        threading.Thread(target=self._provision_task, args=(ssid, pwd, name, target_ip, target_port), daemon=True).start()

    def _provision_task(self, ssid, pwd, friendly_name, ip_address, port):
        self.log_prov(f"--- Configuring Device at {ip_address} ---")
        try:
            if port: url = f"http://{ip_address}:{port}/setup.xml"
            else: url = f"http://{ip_address}:49153/setup.xml"
            self.log_prov(f"Targeting URL: {url}")
            dev = pywemo.discovery.device_from_description(url)
            if friendly_name and hasattr(dev, 'basicevent'):
                self.log_prov(f"Setting Name to: {friendly_name}")
                dev.basicevent.ChangeFriendlyName(FriendlyName=friendly_name)
                time.sleep(1) 
            self.log_prov("Starting Adaptive Encryption Loop (v3.1 Smart Loop)...")
            self._brute_force_provision(dev, ssid, pwd)
            self.log_prov("SUCCESS: Configuration Sent!")
            self.log_prov("Device is rebooting. Connect PC back to Home Wi-Fi.")
        except Exception as e: self.log_prov(f"Error: {e}")
        self.prov_btn.configure(state="normal", text="Push Configuration")

    def _brute_force_provision(self, dev, ssid, pwd):
        enc_modes = [2, 1, 0]
        len_opts = [True, False]
        for mode in enc_modes:
            for length in len_opts:
                try:
                    self.log_prov(f"Attempting: Method {mode}, Len={length}...")
                    dev.setup(ssid=ssid, password=pwd, _encrypt_method=mode, _add_password_lengths=length)
                    self.log_prov(f"  > Accepted!")
                    return
                except: pass
        raise Exception("All provisioning attempts failed.")

    # --- MAINTENANCE ---
    def create_maintenance_ui(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["maint"] = frame
        ctk.CTkLabel(frame, text="Device Maintenance Tools", font=FONT_H1, text_color=COLOR_TEXT).pack(pady=20)
        
        sel_frame = ctk.CTkFrame(frame, fg_color=COLOR_FRAME)
        sel_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(sel_frame, text="Select Target Device:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left", padx=10, pady=10)
        self.maint_dev_combo = ctk.CTkComboBox(sel_frame, values=["Scanning..."], width=300)
        self.maint_dev_combo.pack(side="left", padx=10)
        
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=20, pady=10)
        
        c1 = ctk.CTkFrame(grid, fg_color=("#fff8e1", "#332222"))
        c1.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c1, text="Clear Personal Info", font=FONT_H2, text_color=("#b38f00", "#ffcc00")).pack(pady=(15,5))
        ctk.CTkLabel(c1, text="Removes custom Name, Icon,\nand Rules. Keeps Wi-Fi.", text_color="gray").pack(pady=5)
        ctk.CTkButton(c1, text="Run (Reset=1)", fg_color=COLOR_MAINT_BTN_Y, text_color="#000000", font=FONT_BODY,
                      command=lambda: self.run_reset_command(1)).pack(pady=15)
                      
        c2 = ctk.CTkFrame(grid, fg_color=("#e3f2fd", "#222233"))
        c2.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c2, text="Clear Wi-Fi", font=FONT_H2, text_color=("#0055aa", "#66aaff")).pack(pady=(15,5))
        ctk.CTkLabel(c2, text="Resets Wi-Fi Credentials", text_color="gray").pack(pady=5)
        ctk.CTkButton(c2, text="Run (Reset=5)", fg_color=COLOR_MAINT_BTN_B, text_color="#ffffff", font=FONT_BODY,
                      command=lambda: self.run_reset_command(5)).pack(pady=15)

        c3 = ctk.CTkFrame(grid, fg_color=("#ffebee", "#330000"))
        c3.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c3, text="Factory Reset", font=FONT_H2, text_color=("#aa0000", "#ff4444")).pack(pady=(15,5))
        ctk.CTkLabel(c3, text="Full Wipe (Out of Box)", text_color="gray").pack(pady=5)
        ctk.CTkButton(c3, text="NUKE (Reset=2)", fg_color=COLOR_MAINT_BTN_R, text_color="#ffffff", font=FONT_BODY,
                      command=lambda: self.run_reset_command(2)).pack(pady=15)
        
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1); grid.columnconfigure(2, weight=1)

    def update_maint_dropdown(self):
        names = []
        for dev in self.known_devices_map.values(): 
            names.append(dev.name)
        names.sort()
        if names: 
            self.maint_dev_combo.configure(values=names)
            self.maint_dev_combo.set(names[0])
            
    def run_reset_command(self, reset_code):
        name = self.maint_dev_combo.get()
        
        # --- API MODE HANDLER ---
        if self.use_api_mode:
            confirm = messagebox.askyesno("Confirm Remote Reset", f"Are you sure you want to send Reset Code {reset_code} to '{name}' via SERVER?\n\nThis cannot be undone.")
            if not confirm: return
            
            def task():
                success = self.api.reset_device(name, reset_code)
                if success:
                    self.after(0, lambda: messagebox.showinfo("Success", "Command sent to Server."))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", "Server failed to execute command."))
            threading.Thread(target=task, daemon=True).start()
            return
        
        # --- LOCAL MODE HANDLER ---
        dev = None
        for d in self.known_devices_map.values():
            if d.name == name:
                dev = d
                break
        
        if not dev:
            messagebox.showerror("Error", "Device not found.")
            return
        
        confirm = messagebox.askyesno("Confirm Reset", f"Are you sure you want to send Reset Code {reset_code} to '{name}'?\n\nThis cannot be undone.")
        if not confirm: return

        def task():
            try:
                if hasattr(dev, 'basicevent'):
                    dev.basicevent.ReSetup(Reset=reset_code)
                    self.after(0, lambda: messagebox.showinfo("Success", f"Command Sent (Code {reset_code}).\nDevice should reboot shortly."))
                else:
                    self.after(0, lambda: messagebox.showerror("Error", "Device does not support 'ReSetup' action."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Failure", f"Command Failed:\n{e}"))
        threading.Thread(target=task, daemon=True).start()

    # --- SCHEDULER ---
    def create_schedule_ui(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["sched"] = frame
        
        ctk.CTkLabel(frame, text="Automation Scheduler", font=FONT_H1, text_color=COLOR_TEXT).pack(pady=20)
        
        loc_frame = ctk.CTkFrame(frame, fg_color=COLOR_FRAME)
        loc_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(loc_frame, text="Solar Location:", font=FONT_H2, text_color=COLOR_TEXT).pack(side="left", padx=10)
        self.loc_lbl = ctk.CTkLabel(loc_frame, text="Detecting...", text_color="orange")
        self.loc_lbl.pack(side="left")
        
        ctk.CTkButton(loc_frame, text="Update Solar Data", width=120, 
                      fg_color=COLOR_BTN_SECONDARY, text_color=COLOR_BTN_TEXT, 
                      command=self.update_solar_data).pack(side="right", padx=10, pady=5)
        
        creator_frame = ctk.CTkFrame(frame)
        creator_frame.pack(fill="x", pady=10)
        
        r1 = ctk.CTkFrame(creator_frame, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=5)
        self.sched_dev_combo = ctk.CTkComboBox(r1, values=["Scanning..."], width=200)
        self.sched_dev_combo.pack(side="left", padx=5)
        self.sched_action_combo = ctk.CTkComboBox(r1, values=["Turn ON", "Turn OFF", "Toggle"], width=100)
        self.sched_action_combo.pack(side="left", padx=5)
        self.sched_type_combo = ctk.CTkComboBox(r1, values=["Time (Fixed)", "Sunrise", "Sunset"], width=130, command=self.on_sched_type_change)
        self.sched_type_combo.pack(side="left", padx=5)
        
        r2 = ctk.CTkFrame(creator_frame, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=5)
        self.sched_val_lbl = ctk.CTkLabel(r2, text="Time (HH:MM):", text_color=COLOR_TEXT)
        self.sched_val_lbl.pack(side="left", padx=5)
        self.sched_val_entry = ctk.CTkEntry(r2, width=80, placeholder_text="18:00")
        self.sched_val_entry.pack(side="left", padx=5)
        self.sched_offset_combo = ctk.CTkComboBox(r2, values=["+ (After)", "- (Before)"], width=100)
        self.sched_offset_combo.pack(side="left", padx=5)
        self.sched_offset_combo.pack_forget()
        
        self.day_vars = []
        days = ["M", "T", "W", "Th", "F", "Sa", "Su"]
        day_frame = ctk.CTkFrame(r2, fg_color="transparent")
        day_frame.pack(side="left", padx=20)
        for i, d in enumerate(days):
            v = ctk.BooleanVar(value=True)
            self.day_vars.append(v)
            ctk.CTkCheckBox(day_frame, text=d, variable=v, width=40, text_color=COLOR_TEXT).pack(side="left", padx=2)
            
        ctk.CTkButton(r2, text="Create Job", width=100, fg_color=COLOR_SUCCESS, command=self.add_job).pack(side="right", padx=10)
        
        ctk.CTkLabel(frame, text="Active Schedules", font=FONT_H2, text_color=COLOR_TEXT).pack(anchor="w", pady=(10,0))
        self.job_list_frame = ctk.CTkScrollableFrame(frame, height=350)
        self.job_list_frame.pack(fill="both", expand=True, pady=5)
        self.render_jobs()
        self.update_solar_data() 

    def on_sched_type_change(self, choice):
        if choice == "Time (Fixed)":
            self.sched_val_lbl.configure(text="Time (HH:MM):")
            self.sched_val_entry.configure(placeholder_text="18:00")
            self.sched_offset_combo.pack_forget()
        else:
            self.sched_val_lbl.configure(text="Offset (Mins):")
            self.sched_val_entry.configure(placeholder_text="30")
            self.sched_offset_combo.pack(side="left", padx=5, after=self.sched_val_entry)

    def update_solar_data(self):
        def task():
            solar_data = self.solar.get_solar_times()
            if solar_data:
                txt = f"Lat: {self.solar.lat} | Rise: {solar_data['sunrise']} | Set: {solar_data['sunset']}"
                self.after(0, lambda: self.loc_lbl.configure(text=txt, text_color="gray"))
                self.settings["lat"] = self.solar.lat
                self.settings["lng"] = self.solar.lng
                self.save_json(SETTINGS_FILE, self.settings)
            else: self.after(0, lambda: self.loc_lbl.configure(text="Location Failed.", text_color="red"))
        threading.Thread(target=task, daemon=True).start()

    def add_job(self):
        dev = self.sched_dev_combo.get()
        action = self.sched_action_combo.get()
        sType = self.sched_type_combo.get()
        val = self.sched_val_entry.get()
        active_days = [i for i, v in enumerate(self.day_vars) if v.get()]
        if not active_days: messagebox.showwarning("Error", "Select at least one day."); return
        if sType == "Time (Fixed)":
            if not val: val = "00:00"
            try: datetime.datetime.strptime(val, "%H:%M")
            except ValueError: messagebox.showerror("Format Error", "HH:MM"); return
        else:
            if not val: val = "0"
            if not val.isdigit(): messagebox.showerror("Format Error", "Offset integer"); return
        offset_mod = 1
        if sType != "Time (Fixed)":
            if self.sched_offset_combo.get() == "- (Before)": offset_mod = -1
        job = {"id": int(time.time()), "device": dev, "action": action, "type": sType, "value": val, "offset_dir": offset_mod, "days": active_days, "last_run": ""}
        
        # Add to Server or Local (Threaded)
        threading.Thread(target=self._add_job_task, args=(job,), daemon=True).start()

    def _add_job_task(self, job):
        if self.use_api_mode:
            self.api.add_schedule(job)
            time.sleep(0.5) # Wait for server sync
        else:
            self.schedules.append(job)
            self.save_json(SCHEDULE_FILE, self.schedules)
        
        # Refresh UI
        self.after(0, self.render_jobs)

    def render_jobs(self):
        for w in self.job_list_frame.winfo_children(): w.destroy()
        
        current_data = self.schedules
        
        if not current_data: ctk.CTkLabel(self.job_list_frame, text="No schedules.", text_color="gray").pack(); return
        days_map = ["M", "T", "W", "Th", "F", "Sa", "Su"]
        for job in self.schedules:
            row = ctk.CTkFrame(self.job_list_frame, fg_color=COLOR_FRAME)
            row.pack(fill="x", pady=2)
            d_str = "".join([days_map[i] for i in job['days']])
            if len(job['days']) == 7: d_str = "Every Day"
            try:
                if job['type'] == "Time (Fixed)": time_desc = f"@{job['value']}"
                else:
                    off = int(job['value'])
                    dir_s = "+" if job['offset_dir'] == 1 else "-"
                    time_desc = f"{job['type']} {dir_s}{off}m"
            except: time_desc = "Error"
            desc = f"[{d_str}] {time_desc} -> {job['action']} '{job['device']}'"
            ctk.CTkLabel(row, text=desc, font=("Consolas", 12), text_color=COLOR_TEXT).pack(side="left", padx=10, pady=5)
            
            # Delete Button with Threading
            def delete_action(jid=job["id"]):
                threading.Thread(target=self._delete_job_task, args=(jid,), daemon=True).start()
                
            ctk.CTkButton(row, text="Del", width=30, fg_color=COLOR_DANGER, command=delete_action).pack(side="right", padx=5)

    def _delete_job_task(self, jid):
        if self.use_api_mode: 
            self.api.delete_schedule(jid)
            time.sleep(0.5)
        else: 
            self.schedules = [j for j in self.schedules if j["id"] != jid]
            self.save_json(SCHEDULE_FILE, self.schedules)
        self.after(0, self.render_jobs)

    def update_schedule_dropdown(self):
        names = []
        for dev in self.known_devices_map.values(): 
            names.append(dev.name)
        names.sort()
        if names: 
            self.sched_dev_combo.configure(values=names)
            self.sched_dev_combo.set(names[0])

    def _scheduler_engine(self):
        # The internal engine logic (runs only if API Mode is FALSE)
        while True:
            if self.use_api_mode:
                # If server is managing things, we sleep and skip logic
                time.sleep(10)
                continue

            try:
                now = datetime.datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                weekday = now.weekday()
                current_hhmm = now.strftime("%H:%M")
                solar = self.solar.get_solar_times()
                for job in self.schedules:
                    if weekday not in job['days']: continue
                    trigger_time = ""
                    if job['type'] == "Time (Fixed)": trigger_time = job['value']
                    elif solar:
                        base_str = solar['sunrise'] if job['type'] == "Sunrise" else solar['sunset']
                        try:
                            dt = datetime.datetime.strptime(f"{today_str} {base_str}", "%Y-%m-%d %H:%M")
                            offset_mins = int(job['value']) * job['offset_dir']
                            trigger_dt = dt + datetime.timedelta(minutes=offset_mins)
                            trigger_time = trigger_dt.strftime("%H:%M")
                        except: continue
                    if trigger_time == current_hhmm and job.get('last_run') != today_str:
                        self.execute_job(job)
                        job['last_run'] = today_str
                        self.save_json(SCHEDULE_FILE, self.schedules)
            except: pass
            time.sleep(30)

    def execute_job(self, job):
        dev_name = job['device']
        dev = None
        for d in self.known_devices_map.values():
            if d.name == dev_name:
                dev = d
                break
        if dev:
            try:
                if job['action'] == "Turn ON": dev.on()
                elif job['action'] == "Turn OFF": dev.off()
                elif job['action'] == "Toggle": dev.toggle()
            except: pass

    # --- UTILS ---
    def load_json(self, path, default_type=dict):
        if os.path.exists(path):
            try:
                with open(path) as f: return json.load(f)
            except: pass
        return default_type()

    def save_json(self, path, data):
        with open(path, 'w') as f: json.dump(data, f)

    def save_current_profile(self):
        ssid = self.ssid_entry.get()
        pwd = self.pass_entry.get()
        if not ssid or not pwd: return
        self.profiles[ssid] = pwd
        self.save_json(PROFILE_FILE, self.profiles)
        self.profile_combo.configure(values=["Select Saved Profile..."] + list(self.profiles.keys()))
        self.profile_combo.set(ssid)

    def apply_profile(self, choice):
        if choice in self.profiles:
            self.ssid_entry.delete(0, "end"); self.ssid_entry.insert(0, choice)
            self.pass_entry.delete(0, "end"); self.pass_entry.insert(0, self.profiles[choice])

    def delete_profile(self):
        curr = self.profile_combo.get()
        if curr in self.profiles:
            del self.profiles[curr]
            self.save_json(PROFILE_FILE, self.profiles)
            self.profile_combo.configure(values=["Select Saved Profile..."] + list(self.profiles.keys()))
            self.profile_combo.set("Select Saved Profile...")

    def scan_ssids(self):
        for w in self.ssid_list.winfo_children(): w.destroy()
        lbl = ctk.CTkLabel(self.ssid_list, text="Scanning...", text_color="yellow")
        lbl.pack()
        threading.Thread(target=self._scan_thread_logic, args=(lbl,), daemon=True).start()

    def _scan_thread_logic(self, status_lbl):
        wemos = NetworkUtils.scan_wifi_networks()
        status_lbl.destroy()
        if wemos:
            for ssid in list(set(wemos)): self.after(0, lambda s=ssid: self.build_ssid_card(s))
        else: self.after(0, lambda: ctk.CTkLabel(self.ssid_list, text="No Wemo networks found.", text_color="#ff5555").pack())

    def build_ssid_card(self, ssid):
        card = ctk.CTkFrame(self.ssid_list, fg_color=COLOR_FRAME)
        card.pack(fill="x", pady=2, padx=5)
        ctk.CTkLabel(card, text=ssid, font=("Arial", 12, "bold"), text_color=COLOR_TEXT).pack(side="left", padx=10)
        
        # --- SMART CONNECT BUTTON LOGIC ---
        if WifiAutomator.can_automate():
            def connect_action(s=ssid):
                self.prov_log.insert("end", f"Connecting to {s}...\n")
                self.prov_log.see("end")
                threading.Thread(target=self._connect_task, args=(s,), daemon=True).start()
                
            ctk.CTkButton(card, text="Connect", width=80, height=24, fg_color=COLOR_SUCCESS, command=connect_action).pack(side="right", padx=10)
        else:
            ctk.CTkLabel(card, text="> Connect Manually", text_color="gray", font=("Arial", 10)).pack(side="right", padx=10)

    def _connect_task(self, ssid):
        success = WifiAutomator.connect_open_network(ssid)
        if success:
            self.log_prov(f"Success: Connected to {ssid}")
        else:
            self.log_prov(f"Failed to connect to {ssid}")

    def log_prov(self, msg):
        self.prov_log.insert("end", f"{msg}\n")
        self.prov_log.see("end")

    def _connection_monitor(self):
        target_ips = ["10.22.22.1", "192.168.49.1"]
        target_ports = [49153, 49152, 49154] 
        while self.monitoring:
            if self.manual_override_active: 
                time.sleep(3)
                continue
            found_dev = None
            found_ip = None
            found_port = None
            for ip in target_ips:
                for port in target_ports:
                    try:
                        check_url = f"http://{ip}:{port}/setup.xml"
                        found_dev = pywemo.discovery.device_from_description(check_url)
                        if found_dev:
                            found_ip = ip
                            found_port = port
                            break
                    except: pass
                if found_dev: break
            if found_dev: 
                self.current_setup_ip = found_ip
                self.current_setup_port = found_port
                self.after(0, lambda: self.set_status_connected(found_dev, found_ip, found_port))
            else: 
                self.current_setup_ip = None
                self.after(0, self.set_status_disconnected)
            time.sleep(3)

    def set_status_connected(self, dev, ip, port):
        self.status_frame.configure(fg_color=("#d0f0c0", "#1a331a"), border_color="#28a745")
        self.status_lbl_icon.configure(text="OK")
        self.status_lbl_text.configure(text="CONNECTED", text_color="#28a745")
        self.status_lbl_sub.configure(text=f"Found: {dev.name} ({ip}:{port})", text_color=COLOR_TEXT)
        self.prov_btn.configure(state="normal", text="Push Configuration")
        self.override_link.pack_forget()

    def set_status_disconnected(self):
        self.status_frame.configure(fg_color=("#fadbd8", "#331111"), border_color="#ff5555")
        self.status_lbl_icon.configure(text="X")
        self.status_lbl_text.configure(text="NOT CONNECTED", text_color="#ff5555")
        self.status_lbl_sub.configure(text="Connect Wi-Fi to 'Wemo.Mini.XXX'", font=("Arial", 12), text_color=COLOR_TEXT)
        self.prov_btn.configure(state="disabled", text="Waiting for Connection...")
        self.override_link.pack(anchor="e", pady=(0, 5))

    def force_unlock(self):
        self.status_frame.configure(fg_color=("#fcf3cf", "#332200"), border_color="#FFA500")
        self.status_lbl_icon.configure(text="(!)")
        self.status_lbl_text.configure(text="MANUAL OVERRIDE", text_color="#FFA500")
        self.status_lbl_sub.configure(text="Forced Unlock. Assuming 10.22.22.1.", text_color=COLOR_TEXT)
        self.prov_btn.configure(state="normal", text="Push Configuration (Forced)")
        self.current_setup_ip = "10.22.22.1"
        self.log_prov("Manual Override engaged. Assuming IP 10.22.22.1.")

    def show_qr_code(self):
        try:
            # 1. Get correct URL
            if self.use_api_mode:
                try: ip = NetworkUtils.get_local_ip(); url = f"http://{ip}:5050" # Updated Port
                except: url = "http://localhost:5050"
            else:
                try: ip = NetworkUtils.get_local_ip(); url = f"http://{ip}:5050" # Updated Port
                except: url = "http://localhost:5050"

            # 2. Generate QR Data
            qr = qrcode.QRCode(box_size=10, border=4)
            qr.add_data(url)
            qr.make(fit=True)
            
            # --- FIX: Convert to RGB for CTkImage ---
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            
            # --- FIX: Use Native CTkImage Object ---
            qr_ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(250, 250))
            
            # 3. Create Window
            win = ctk.CTkToplevel(self) 
            win.title("Mobile App")
            win.geometry("400x480")
            
            # --- FIX: Linux Window Logic ---
            win.transient(self) # Keep on top of parent
            win.update()        # Force render calculation
            
            # Center on Main Window
            try:
                main_x = self.winfo_x(); main_y = self.winfo_y()
                main_w = self.winfo_width(); main_h = self.winfo_height()
                pos_x = main_x + (main_w // 2) - (400 // 2)
                pos_y = main_y + (main_h // 2) - (480 // 2)
                win.geometry(f"400x480+{pos_x}+{pos_y}")
            except: pass
            
            try: win.attributes('-topmost', True)
            except: pass
            
            win.focus_force()

            # 4. Content
            lbl_img = ctk.CTkLabel(win, image=qr_ctk_img, text="")
            lbl_img.pack(padx=20, pady=(30, 20))
            lbl_img.image = qr_ctk_img # Keep Reference!
            
            ctk.CTkLabel(win, text="Scan to Control on Mobile", font=("Arial", 16, "bold")).pack(pady=(0,5))
            
            link_lbl = ctk.CTkLabel(win, text=url, text_color="gray", cursor="hand2", font=("Consolas", 14, "underline"))
            link_lbl.pack(pady=(0,20))
            link_lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
            
            ctk.CTkButton(win, text="Close", command=win.destroy, fg_color="gray").pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("QR Error", f"Failed to show QR Code:\n{e}")

if __name__ == "__main__":
    app = WemoOpsApp()
    app.mainloop()