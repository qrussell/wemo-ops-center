import customtkinter as ctk
import pywemo
from pywemo.ouimeaux_device.dimmer import Dimmer
import threading
import sys
import os
import shutil
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
import platform
from tkinter import messagebox
import pyperclip

# --- QR Code & Image Support (CRASH FIX) ---
HAS_QR = False
try:
    import qrcode
    from PIL import Image, ImageTk 
    HAS_QR = True
except Exception as e:
    print(f"QR Support Disabled: {e}")
    HAS_QR = False

# --- CONFIGURATION ---
VERSION = "v5.3.0"
SERVER_PORT = 5050
HOOBS_PORT = 8581
SERVER_URL = f"http://localhost:{SERVER_PORT}"
HOOBS_URL = f"http://localhost:{HOOBS_PORT}"
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

# --- SERVICE & INSTALLER DETECTION ---
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

SERVICE_EXE_PATH = None
local_service = os.path.join(BASE_DIR, "wemo_service.exe")
mac_service = os.path.join(BASE_DIR, "wemo_service")

if os.path.exists(local_service):
    SERVICE_EXE_PATH = local_service
elif os.path.exists(mac_service):
    SERVICE_EXE_PATH = mac_service
elif sys.platform == "win32":
    appdata_service = os.path.join(APP_DATA_DIR, "wemo_service.exe")
    if os.path.exists(appdata_service):
        SERVICE_EXE_PATH = appdata_service
else:
    possible_paths = [
        os.path.join(APP_DATA_DIR, "wemo_service"),
        "/opt/WemoOps/wemo_service",
        "/usr/bin/wemo_service"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            SERVICE_EXE_PATH = p
            break

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
#  UPDATE MANAGER
# ==============================================================================
class UpdateManager:
    @staticmethod
    def check_for_updates(current_version, api_url):
        try:
            response = requests.get(api_url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "").strip()
                if latest_tag and latest_tag != current_version:
                    return True, latest_tag
        except: pass
        return False, None

# ==============================================================================
#  API CLIENT
# ==============================================================================
class APIClient:
    def __init__(self):
        self.connected = False

    def check_connection(self):
        try:
            r = requests.get(f"{SERVER_URL}/api/status", timeout=0.5)
            if r.status_code == 200:
                self.connected = True
                return True
        except: pass
        self.connected = False
        return False

    def get_devices(self):
        try: return requests.get(f"{SERVER_URL}/api/devices", timeout=1).json()
        except: return []

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
            ip = NetworkUtils.get_local_ip()
            return f"{ip}/24"
        except: return "192.168.1.0/24"

    @staticmethod
    def scan_wifi_networks():
        wemos = []
        try:
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                output = subprocess.check_output("netsh wlan show networks mode=bssid", startupinfo=si).decode('utf-8', errors='ignore')
                for line in output.split('\n'):
                    if "SSID" in line:
                        ssid = line.split(":", 1)[1].strip()
                        if ssid: wemos.append(ssid)
            elif sys.platform == "darwin":
                 airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
                 if os.path.exists(airport):
                     output = subprocess.check_output(f"{airport} -s", shell=True).decode('utf-8', errors='ignore')
                     for line in output.split('\n')[1:]:
                         parts = line.strip().split()
                         if parts: wemos.append(parts[0])
            elif sys.platform.startswith("linux"):
                output = subprocess.check_output("nmcli -t -f SSID dev wifi", shell=True).decode('utf-8', errors='ignore')
                for line in output.split('\n'):
                    if line.strip(): wemos.append(line.strip())
        except: pass
        return [ssid for ssid in list(set(wemos)) if "wemo" in ssid.lower() or "belkin" in ssid.lower()]

    @staticmethod
    def check_hoobs_status():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex(('localhost', HOOBS_PORT))
            s.close()
            return result == 0
        except: return False

class DeepScanner:
    def probe_port(self, ip, ports=[49152, 49153, 49154, 49155], timeout=0.6):
        for port in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try: 
                s.connect((str(ip), port))
                s.close()
                return str(ip)
            except: pass
            finally: s.close()
        return None

    def scan_subnet(self, target_cidr, status_callback=None):
        found_devices = []
        try:
            network = ipaddress.ip_network(target_cidr, strict=False)
            all_hosts = list(network.hosts())
        except: return []

        if status_callback: status_callback(f"Probing {len(all_hosts)} IPs (Deep)...")
        
        active_ips = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
            futures = {executor.submit(self.probe_port, ip): ip for ip in all_hosts}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result: active_ips.append(result)

        if status_callback: status_callback(f"Verifying {len(active_ips)} hosts...")
        
        for ip in active_ips:
            for port in [49152, 49153, 49154, 49155]:
                try:
                    url = f"http://{ip}:{port}/setup.xml"
                    dev = pywemo.discovery.device_from_description(url)
                    if dev: 
                        found_devices.append(dev)
                        break 
                except: pass
        return found_devices

# ==============================================================================
#  WIFI AUTOMATOR
# ==============================================================================
class WifiAutomator:
    @staticmethod
    def can_automate(): return sys.platform in ["win32", "linux", "darwin"]
    
    @staticmethod
    def connect_open_network(ssid):
        try:
            if sys.platform == "win32":
                hex_ssid = ssid.encode('utf-8').hex()
                xml = f"""<?xml version="1.0"?><WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1"><name>{ssid}</name><SSIDConfig><SSID><hex>{hex_ssid}</hex><name>{ssid}</name></SSID></SSIDConfig><connectionType>ESS</connectionType><connectionMode>manual</connectionMode><MSM><security><authEncryption><authentication>open</authentication><encryption>none</encryption><useOneX>false</useOneX></authEncryption></security></MSM></WLANProfile>"""
                fd, path = tempfile.mkstemp(suffix=".xml")
                with os.fdopen(fd, 'w') as tmp: tmp.write(xml)
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
        except: return False
        return False

# ==============================================================================
#  SOLAR ENGINE
# ==============================================================================
class SolarEngine:
    def __init__(self):
        self.lat = None; self.lng = None; self.solar_times = {}; self.last_fetch = None
    
    def get_solar_times(self):
        today = datetime.date.today()
        if self.last_fetch == today: return self.solar_times
        if not self.lat:
            try:
                r = requests.get("https://ipinfo.io/json", timeout=2)
                loc = r.json().get("loc", "").split(",")
                self.lat, self.lng = loc[0], loc[1]
            except: return None
        try:
            url = f"https://api.sunrise-sunset.org/json?lat={self.lat}&lng={self.lng}&formatted=0"
            r = requests.get(url, timeout=5)
            res = r.json()["results"]
            def to_local(utc_str):
                return datetime.datetime.fromisoformat(utc_str).astimezone().strftime("%H:%M")
            self.solar_times = {"sunrise": to_local(res["sunrise"]), "sunset": to_local(res["sunset"])}
            self.last_fetch = today
            return self.solar_times
        except: return None

# ==============================================================================
#  MAIN APP
# ==============================================================================
class WemoOpsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Wemo Ops Center {VERSION}")
        self.geometry("1100x800")
        
        self.set_icon(self)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.api = APIClient() 
        self.settings = self.load_json(SETTINGS_FILE, dict)
        self.profiles = self.load_json(PROFILE_FILE, dict)
        self.schedules = self.load_json(SCHEDULE_FILE, list) or []
        self.saved_subnets = self.settings.get("subnets", [])
        
        self.known_devices_map = {}
        self.device_switches = {} 
        self.last_rendered_device_names = [] 
        self.solar = SolarEngine()
        self.scanner = DeepScanner()
        self.current_setup_ip = None
        self.current_setup_port = None
        self.manual_override_active = False
        self.hoobs_online = False

        if "lat" in self.settings:
            self.solar.lat = self.settings["lat"]
            self.solar.lng = self.settings["lng"]

        ctk.set_appearance_mode(self.settings.get("theme", "System"))
        self.set_ui_scale(self.settings.get("scale", "100%"))

        # --- UI SETUP ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="WEMO OPS", font=("Arial Black", 22), text_color=COLOR_TEXT)
        self.logo.pack(pady=25)

        self.btn_dash = self.create_nav_btn("Dashboard", "dash")
        self.btn_prov = self.create_nav_btn("Provisioner", "prov")
        self.btn_sched = self.create_nav_btn("Automation", "sched")
        self.btn_maint = self.create_nav_btn("Maintenance", "maint")
        self.btn_bridge = self.create_nav_btn("Integrations", "bridge")
        self.btn_settings = self.create_nav_btn("Settings", "settings") 
        
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)
        
        if HAS_QR:
            ctk.CTkButton(self.sidebar, text="📱 Mobile App", fg_color=COLOR_ACCENT, command=self.show_qr_code).pack(pady=5, padx=10)

        self.service_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.service_frame.pack(side="bottom", fill="x", pady=20, padx=10)
        self.svc_lbl = ctk.CTkLabel(self.service_frame, text="Service Status:", font=("Arial", 12, "bold"), text_color=COLOR_TEXT)
        self.svc_lbl.pack(anchor="w")
        self.svc_status = ctk.CTkLabel(self.service_frame, text="Checking...", text_color="gray", font=FONT_BODY)
        self.svc_status.pack(anchor="w")
        
        self.btn_start_svc = ctk.CTkButton(self.service_frame, text="▶ Start Service", width=100, fg_color="#2d8a4e", command=self.start_local_server)
        self.btn_start_svc.pack(pady=(5,0), anchor="w")

        self.btn_update = ctk.CTkButton(self.sidebar, text="⬇ Update Available", fg_color=COLOR_UPDATE, 
                                        font=FONT_BODY, command=lambda: webbrowser.open(UPDATE_PAGE_URL))
        self.btn_update.pack(side="bottom", padx=10, pady=(0, 10))
        self.btn_update.pack_forget()

        ctk.CTkLabel(self.sidebar, text=f"{VERSION}", text_color="gray", font=("Arial", 10)).pack(side="bottom", pady=5)

        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_BG)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.content = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=20)

        self.frames = {}
        self.create_dashboard()
        self.create_provisioner()
        self.create_schedule_ui()
        self.create_maintenance_ui()
        self.create_settings_ui()
        self.create_bridges_ui()
        
        self.show_tab("dash")
        self.after(500, self.refresh_network)
        
        self.monitoring = True
        threading.Thread(target=self._connection_monitor, daemon=True).start()
        threading.Thread(target=self._scheduler_engine, daemon=True).start()
        threading.Thread(target=self.run_update_check, daemon=True).start()
        threading.Thread(target=self._state_poller, daemon=True).start()
        threading.Thread(target=self._hoobs_monitor, daemon=True).start()
        
        self.server_heartbeat()

    # --- HELPERS ---
    def load_json(self, p, t): 
        if os.path.exists(p): 
            try: 
                with open(p) as f: return json.load(f)
            except: pass
        return t()
        
    def save_json(self, p, d):
        with open(p, 'w') as f: json.dump(d, f)
        
    def set_ui_scale(self, s):
        try: ctk.set_widget_scaling(int(str(s).replace("%", ""))/100)
        except: pass

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
        for key in ["dash", "prov", "sched", "maint", "settings", "bridge"]:
            btn = getattr(self, f"btn_{key}")
            btn.configure(fg_color="transparent", text_color=COLOR_TEXT)
        active_btn = getattr(self, f"btn_{name}")
        active_btn.configure(fg_color=COLOR_FRAME, text_color=COLOR_TEXT)

    def server_heartbeat(self):
        self.api.check_connection()
        try:
            if self.api.connected:
                self.svc_status.configure(text="✅ RUNNING", text_color="#28a745")
                self.btn_start_svc.pack_forget()
            else:
                self.svc_status.configure(text="⚠️ STOPPED", text_color="orange")
                self.btn_start_svc.pack(pady=(5,0), anchor="w")
        except: pass
        self.after(5000, self.server_heartbeat)

    def set_icon(self, window=None):
        target = window if window else self
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.join(sys._MEIPASS, "images")
            else:
                base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
            icon_path = os.path.join(base_path, "app_icon.ico")
            if os.path.exists(icon_path) and sys.platform == "win32":
                target.iconbitmap(icon_path)
        except Exception: pass

    # --- DASHBOARD ---
    def create_dashboard(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["dash"] = f
        head = ctk.CTkFrame(f, fg_color="transparent"); head.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(head, text="Network Overview (Local)", font=FONT_H1, text_color=COLOR_TEXT).pack(side="left", anchor="n")
        
        ctrl = ctk.CTkFrame(head, fg_color="transparent"); ctrl.pack(side="right", anchor="e")
        r1 = ctk.CTkFrame(ctrl, fg_color="transparent"); r1.pack(side="top", anchor="e")
        
        self.subnet_combo = ctk.CTkComboBox(r1, width=180, values=self.saved_subnets)
        self.subnet_combo.pack(side="left", padx=2)
        self.subnet_combo.set(NetworkUtils.get_subnet_cidr())
        
        ctk.CTkButton(r1, text="Save", width=50, fg_color=COLOR_ACCENT, command=self.save_subnet).pack(side="left", padx=2)
        ctk.CTkButton(r1, text="Del", width=50, fg_color=COLOR_DANGER, command=self.delete_subnet).pack(side="left", padx=(2, 10))
        ctk.CTkButton(r1, text="Scan", width=80, command=self.run_local_scan, fg_color=COLOR_ACCENT).pack(side="left", padx=5)
        
        self.scan_status = ctk.CTkLabel(ctrl, text="Ready", text_color="orange", font=("Arial", 11))
        self.scan_status.pack(side="top", anchor="e", padx=10, pady=(2, 0))
        
        self.dev_list = ctk.CTkScrollableFrame(f, label_text="Devices", label_text_color=COLOR_TEXT); self.dev_list.pack(fill="both", expand=True)

    def save_subnet(self):
        s = self.subnet_combo.get().strip()
        if s and s not in self.saved_subnets:
            self.saved_subnets.append(s)
            self.settings["subnets"] = self.saved_subnets
            self.save_json(SETTINGS_FILE, self.settings)
            self.subnet_combo.configure(values=self.saved_subnets)
            self.scan_status.configure(text="Subnet Saved")
            
    def delete_subnet(self):
        s = self.subnet_combo.get().strip()
        if s in self.saved_subnets:
            self.saved_subnets.remove(s)
            self.settings["subnets"] = self.saved_subnets
            self.save_json(SETTINGS_FILE, self.settings)
            self.subnet_combo.configure(values=self.saved_subnets)
            self.subnet_combo.set(NetworkUtils.get_subnet_cidr()) 
            self.scan_status.configure(text="Subnet Deleted")

    def run_local_scan(self):
        subnet = self.subnet_combo.get().strip()
        self.scan_status.configure(text="Scanning...")
        threading.Thread(target=self._scan_task, args=(subnet,), daemon=True).start()

    def _scan_task(self, subnet):
        def log(m): self.after(0, lambda: self.scan_status.configure(text=m))
        try:
            log("SSDP Scan...")
            new_map = {}
            for d in pywemo.discover_devices(): 
                new_map[d.name] = d
            
            if subnet:
                log(f"Scanning {subnet}...")
                deep_devs = self.scanner.scan_subnet(subnet)
                for d in deep_devs:
                    new_map[d.name] = d
            
            self.known_devices_map = new_map
            log("Scan Complete") 
            self.after(0, self.render_devices)
            self.after(0, self.update_maint_dropdown)
            self.after(0, self.update_schedule_dropdown)
        except Exception as e: log(f"Error: {e}")

    def refresh_network(self):
        self.run_local_scan()

    def render_devices(self):
        self.device_switches = {}
        current_names = sorted(list(self.known_devices_map.keys()))
        if current_names == self.last_rendered_device_names: return 
        self.last_rendered_device_names = current_names
        
        for w in self.dev_list.winfo_children(): w.destroy()
        devs = list(self.known_devices_map.values())
        if not devs: 
            ctk.CTkLabel(self.dev_list, text="No devices found.", text_color=COLOR_TEXT).pack(pady=20)
            return
        
        for dev in sorted(devs, key=lambda x: x.name):
            self.build_device_card(dev)

    def build_device_card(self, dev):
        try: mac = getattr(dev, 'mac', "Unknown")
        except: mac = "Unknown"
        try: serial = getattr(dev, 'serial_number', "Unknown")
        except: serial = "Unknown"

        c = ctk.CTkFrame(self.dev_list, fg_color=COLOR_CARD, border_width=1, border_color=COLOR_FRAME); c.pack(fill="x", pady=5, padx=5)
        t = ctk.CTkFrame(c, fg_color="transparent"); t.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(t, text=dev.name, font=FONT_H2, text_color=COLOR_TEXT).pack(side="left")
        
        def tog(d=dev): threading.Thread(target=d.toggle, daemon=True).start()
        sw = ctk.CTkSwitch(t, text="Power", command=tog, text_color=COLOR_TEXT)
        sw.pack(side="right")
        self.device_switches[dev.name] = sw
        
        try:
            state = dev.get_state(force_update=False)
            if state > 0: sw.select()
        except: pass

        if isinstance(dev, Dimmer):
            dim_frame = ctk.CTkFrame(c, fg_color="transparent")
            dim_frame.pack(fill="x", padx=10, pady=(0, 10))
            
            ctk.CTkLabel(dim_frame, text="Brightness:", font=("Arial", 12), text_color=COLOR_SUBTEXT).pack(side="left")
            
            def set_brightness(val, d=dev):
                def t():
                    try: d.set_brightness(int(val))
                    except: pass
                threading.Thread(target=t, daemon=True).start()
                if int(val) > 0: self.device_switches[d.name].select()
                else: self.device_switches[d.name].deselect()

            slider = ctk.CTkSlider(dim_frame, from_=0, to=100, command=set_brightness)
            try: slider.set(state if state else 0)
            except: slider.set(0)
            slider.pack(side="right", fill="x", expand=True, padx=10)

        m = ctk.CTkFrame(c, fg_color="transparent"); m.pack(fill="x", padx=10)
        ctk.CTkLabel(m, text=f"IP: {dev.host} | MAC: {mac} | SN: {serial}", font=FONT_MONO, text_color=COLOR_SUBTEXT).pack(anchor="w")
        
        bot = ctk.CTkFrame(c, fg_color="transparent"); bot.pack(fill="x", padx=10, pady=(5, 10))
        
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
            self.after(0, self.run_local_scan)
        except Exception as e: self.after(0, lambda: messagebox.showerror("Error", str(e)))

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

    # --- INTEGRATIONS (HOOBS) ---
    def create_bridges_ui(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["bridge"] = f
        
        h_frame = ctk.CTkFrame(f, fg_color="transparent"); h_frame.pack(fill="x", pady=20)
        ctk.CTkLabel(h_frame, text="HOOBS & Homebridge Integration", font=FONT_H1, text_color=COLOR_TEXT).pack(side="left")
        self.hoobs_status_lbl = ctk.CTkLabel(h_frame, text="Checking...", font=("Arial", 12, "bold"), text_color="gray"); self.hoobs_status_lbl.pack(side="right", padx=10)

        c = ctk.CTkFrame(f, fg_color=COLOR_CARD); c.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(c, text="1. Configuration Generator", font=FONT_H2, text_color=COLOR_TEXT).pack(pady=(20, 5), anchor="w", padx=20)
        ctk.CTkLabel(c, text="Use this JSON block in your Homebridge/HOOBS 'config.json' file.", font=FONT_BODY, text_color=COLOR_SUBTEXT).pack(pady=0, anchor="w", padx=20)
        
        ctk.CTkButton(c, text="Scan & Generate Config", height=30, fg_color=COLOR_ACCENT, command=self.generate_hoobs_config).pack(pady=10, padx=20, anchor="w")
        self.hoobs_text = ctk.CTkTextbox(c, font=FONT_MONO, height=120); self.hoobs_text.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkButton(c, text="Copy Config", fg_color=COLOR_BTN_SECONDARY, text_color=COLOR_BTN_TEXT, width=100, command=lambda: pyperclip.copy(self.hoobs_text.get("1.0", "end"))).pack(pady=5, padx=20, anchor="e")

        self.install_frame = ctk.CTkFrame(c, fg_color="transparent"); self.install_frame.pack(fill="x", padx=20, pady=20)
        
        self.lbl_install_header = ctk.CTkLabel(self.install_frame, text="2. Software Installation", font=FONT_H2, text_color=COLOR_TEXT, anchor="w")
        
        # --- OS SPECIFIC INSTALLER UI ---
        if sys.platform == "darwin":
            # Mac UI (Manual Instructions)
            self.lbl_mac_install_desc = ctk.CTkLabel(self.install_frame, text="Homebridge is not running. macOS requires manual installation via Terminal.", font=FONT_BODY, text_color=COLOR_SUBTEXT, anchor="w")
            mac_inst = (
                "1. Install Node.js (v20 LTS)\n"
                "   - macOS 12+ (Monterey+): Run 'brew install node' or use the official installer.\n"
                "   - macOS 11 (Big Sur): Download the v20 .pkg from https://nodejs.org\n\n"
                "2. Open Terminal and run these commands one by one:\n"
                "   sudo npm install -g --unsafe-perm homebridge homebridge-config-ui-x\n"
                "   sudo npm install -g homebridge-wemo homebridge-alexa\n"
                "   mkdir -p ~/.homebridge\n"
                "   sudo hb-service install\n"
            )
            self.mac_install_text = ctk.CTkTextbox(self.install_frame, height=180, font=FONT_MONO, fg_color=COLOR_BG)
            self.mac_install_text.insert("1.0", mac_inst)
            self.mac_install_text.configure(state="disabled")
        else:
            # Windows / Linux UI (Auto-Installer Button)
            self.lbl_install_desc = ctk.CTkLabel(self.install_frame, text="Homebridge is not running. Install the compatibility layer to enable Alexa/Google Home.", font=FONT_BODY, text_color=COLOR_SUBTEXT, anchor="w")
            self.btn_install_hoobs = ctk.CTkButton(self.install_frame, text="Install Compatibility Layer", height=40, fg_color=COLOR_SUCCESS, command=self.run_hoobs_installer)
        
        # Connected UI
        self.lbl_connect_header = ctk.CTkLabel(self.install_frame, text="2. Connection & Setup", font=FONT_H2, text_color=COLOR_TEXT, anchor="w")
        self.lbl_connect_desc = ctk.CTkLabel(self.install_frame, text="Homebridge is running! Follow these steps to finish setup:", font=FONT_BODY, text_color=COLOR_SUBTEXT, anchor="w")
        self.connect_steps = ctk.CTkTextbox(self.install_frame, height=120, font=FONT_BODY, fg_color=COLOR_BG)
        self.connect_steps.insert("1.0", "1. Click 'Launch Dashboard' below.\n2. Login with admin / admin.\n3. Go to Plugins -> Search 'homebridge-wemo' -> Install.\n4. Go to Config -> Paste the JSON from above into 'platforms'.\n5. Restart Homebridge (Top Right Icon).")
        self.connect_steps.configure(state="disabled")
        self.btn_open_hoobs = ctk.CTkButton(self.install_frame, text="Launch Dashboard (localhost:8581)", height=40, fg_color=COLOR_ACCENT, command=lambda: webbrowser.open(HOOBS_URL))

        self._update_hoobs_ui(False)

    def _hoobs_monitor(self):
        last_state = None
        while self.monitoring:
            is_running = NetworkUtils.check_hoobs_status()
            self.hoobs_online = is_running
            if is_running != last_state:
                self.after(0, lambda: self._update_status_label(is_running))
                self.after(0, lambda: self._update_hoobs_ui(is_running))
                last_state = is_running
            time.sleep(5)

    def _update_status_label(self, is_running):
        if is_running: self.hoobs_status_lbl.configure(text="✅ SERVICE ONLINE", text_color=COLOR_SUCCESS)
        else: self.hoobs_status_lbl.configure(text="⚠️ SERVICE OFFLINE", text_color="orange")

    def _update_hoobs_ui(self, is_running):
        for widget in self.install_frame.winfo_children(): widget.pack_forget()
        
        if is_running:
            self.lbl_connect_header.pack(fill="x", pady=(0,5))
            self.lbl_connect_desc.pack(fill="x", pady=(0,10))
            self.connect_steps.pack(fill="x", pady=(0,10))
            self.btn_open_hoobs.pack(fill="x")
        else:
            self.lbl_install_header.pack(fill="x", pady=(0,5))
            if sys.platform == "darwin":
                self.lbl_mac_install_desc.pack(fill="x", pady=(0,5))
                self.mac_install_text.pack(fill="x", pady=(0,10))
            else:
                self.lbl_install_desc.pack(fill="x", pady=(0,10))
                self.btn_install_hoobs.pack(fill="x")

    def generate_hoobs_config(self):
        devices = []
        for dev in self.known_devices_map.values():
            try:
                mac = getattr(dev, 'mac', 'UNKNOWN').replace(':', '')
                devices.append(f'"{mac}"')
            except: pass
        json_str = "{\n    \"platform\": \"BelkinWeMo\",\n    \"name\": \"WeMo Platform\",\n    \"noMotionTimer\": 60,\n    \"discovery\": false,\n    \"manual_devices\": [\n        " + ",\n        ".join(devices) + "\n    ]\n}"
        self.hoobs_text.delete("1.0", "end"); self.hoobs_text.insert("1.0", json_str)

    def run_hoobs_installer(self):
        # This function is now only called on Windows / Linux
        target = None
        is_script = False
        
        # Determine executable path
        if sys.platform == "win32":
            target = os.path.join(BASE_DIR, "Wemo_HOOBS_Integration_Setup.exe")
        else:
            bin_name = "wemo_hoobs_setup"
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(sys.executable)
                possible = os.path.join(base, bin_name)
                if os.path.exists(possible): target = possible
            if not target:
                script = os.path.join(BASE_DIR, "hoobs_installer.py")
                if os.path.exists(script): target = script; is_script = True
        
        if not target or not os.path.exists(target):
             if os.path.exists("wemo_hoobs_setup"): target = "wemo_hoobs_setup"
        
        if not target or not os.path.exists(target):
            messagebox.showerror("Error", "Installer component not found in application directory.")
            return
        
        # Execute Installer Securely
        try:
            if sys.platform == "win32":
                import ctypes
                if is_script: ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, target, None, 1)
                else: ctypes.windll.shell32.ShellExecuteW(None, "runas", target, "", None, 1)
            else:
                # Add quotes around the target path to handle spaces safely
                cmd = f'sudo python3 "{target}"' if is_script else f'sudo "{target}"'
                
                # Check for standard Linux terminal emulators and launch visible terminal
                term_launched = False
                
                # Wrap command to keep terminal open if there's an immediate failure
                bash_wrapper = f"{cmd}; echo; read -p 'Press Enter to exit...'"
                
                terminals = {
                    'ptyxis': ['--', 'bash', '-c'],          # Fedora 40+ GNOME
                    'kgx': ['-e', 'bash', '-c'],             # Fedora 39/GNOME Console
                    'gnome-terminal': ['--', 'bash', '-c'],  # Ubuntu/Older GNOME
                    'konsole': ['-e', 'bash', '-c'],         # KDE (Fedora Spin / Kubuntu)
                    'xfce4-terminal': ['-x', 'bash', '-c'],  # XFCE
                    'mate-terminal': ['-x', 'bash', '-c'],   # MATE
                    'lxterminal': ['-e', 'bash', '-c'],      # LXDE
                    'tilix': ['-e', 'bash', '-c'],           # Tilix
                    'terminator': ['-x', 'bash', '-c'],      # Terminator
                    'xterm': ['-e', 'bash', '-c']            # Universal Fallback
                }
                
                for term, flags in terminals.items():
                    if shutil.which(term):
                        try:
                            # Wrap command in bash to ensure sudo prompts function correctly in popup window
                            subprocess.Popen([term] + flags + [bash_wrapper])
                            term_launched = True
                            break
                        except Exception:
                            pass
                
                # Fallback if no known terminal emulator is found
                if not term_launched:
                    subprocess.Popen(cmd.split())
                    
        except Exception as e: messagebox.showerror("Launch Error", str(e))

    # --- STATE POLLER ---
    def _state_poller(self):
        while self.monitoring:
            try:
                if not self.frames["dash"].winfo_ismapped(): time.sleep(2); continue
                for name, dev in self.known_devices_map.items():
                    if name in self.device_switches:
                        try:
                            state = dev.get_state(force_update=True)
                            self.after(0, lambda n=name, s=state: self._update_switch_safe(n, s))
                        except: pass
            except: pass
            time.sleep(2) 

    def _update_switch_safe(self, name, state):
        if name in self.device_switches:
            try:
                sw = self.device_switches[name]
                if state > 0: sw.select()
                else: sw.deselect()
            except: pass

    # --- PROVISIONER ---
    def create_provisioner(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["prov"] = f
        f.columnconfigure(0, weight=1); f.columnconfigure(1, weight=2); f.rowconfigure(0, weight=1)
        lc = ctk.CTkFrame(f, fg_color="transparent"); lc.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(lc, text="Step 1: Locate Device", font=FONT_H1, text_color=COLOR_TEXT).pack(anchor="w", pady=(0,5))
        sf = ctk.CTkFrame(lc, fg_color=COLOR_FRAME); sf.pack(fill="x", pady=(0, 20))
        self.btn_scan_setup = ctk.CTkButton(sf, text="Scan Airwaves", command=self.scan_ssids, fg_color=COLOR_ACCENT); self.btn_scan_setup.pack(pady=10, padx=10, fill="x")
        self.ssid_list = ctk.CTkScrollableFrame(sf, height=100, label_text="Nearby Networks", label_text_color=COLOR_TEXT); self.ssid_list.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(lc, text="Step 2: Configuration", font=FONT_H2, text_color=COLOR_TEXT).pack(anchor="w", pady=(0,5))
        inf = ctk.CTkFrame(lc, fg_color="transparent"); inf.pack(fill="x")
        pr = ctk.CTkFrame(inf, fg_color="transparent"); pr.pack(fill="x", pady=5)
        self.profile_combo = ctk.CTkComboBox(pr, values=["Select Saved Profile..."] + list(self.profiles.keys()), command=self.apply_profile, width=200); self.profile_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(pr, text="Save", width=50, command=self.save_current_profile, fg_color=COLOR_ACCENT).pack(side="left", padx=5)
        ctk.CTkButton(pr, text="Del", width=50, fg_color=COLOR_DANGER, command=self.delete_profile).pack(side="left")
        self.name_entry = ctk.CTkEntry(inf, placeholder_text="Device Name"); self.name_entry.pack(fill="x", pady=5)
        self.ssid_entry = ctk.CTkEntry(inf, placeholder_text="SSID"); self.ssid_entry.pack(fill="x", pady=5)
        self.pass_entry = ctk.CTkEntry(inf, placeholder_text="Password", show="*"); self.pass_entry.pack(fill="x", pady=5)
        self.prov_btn = ctk.CTkButton(lc, text="Push Configuration", fg_color=COLOR_SUCCESS, height=50, state="disabled", command=self.run_provision_thread); self.prov_btn.pack(fill="x", pady=20)
        rc = ctk.CTkFrame(f, fg_color="transparent"); rc.grid(row=0, column=1, sticky="nsew")
        self.status_frame = ctk.CTkFrame(rc, fg_color=("#fadbd8", "#331111"), border_color="#ff5555", border_width=2); self.status_frame.pack(fill="x", pady=(0, 10))
        self.status_lbl_icon = ctk.CTkLabel(self.status_frame, text="X", font=("Arial", 30)); self.status_lbl_icon.pack(side="left", padx=15, pady=15)
        stxt = ctk.CTkFrame(self.status_frame, fg_color="transparent"); stxt.pack(side="left", fill="x")
        self.status_lbl_text = ctk.CTkLabel(stxt, text="NOT CONNECTED", font=FONT_H2, text_color="#ff5555"); self.status_lbl_text.pack(anchor="w")
        self.status_lbl_sub = ctk.CTkLabel(stxt, text="Connect Wi-Fi to 'Wemo.Mini.XXX'", font=FONT_BODY, text_color=COLOR_TEXT); self.status_lbl_sub.pack(anchor="w")
        self.override_link = ctk.CTkLabel(rc, text="[Manual Override]", font=("Arial", 10, "underline"), text_color="gray", cursor="hand2"); self.override_link.pack(anchor="e", pady=(0, 5)); self.override_link.bind("<Button-1>", lambda e: self.force_unlock())
        ctk.CTkLabel(rc, text="Live Operation Log", font=FONT_BODY, text_color=COLOR_TEXT).pack(anchor="w")
        self.prov_log = ctk.CTkTextbox(rc, font=FONT_MONO, activate_scrollbars=True); self.prov_log.pack(fill="both", expand=True)

    def run_provision_thread(self):
        ssid = self.ssid_entry.get(); pwd = self.pass_entry.get(); name = self.name_entry.get()
        if not ssid: return messagebox.showwarning("Missing Data", "Enter SSID.")
        self.prov_btn.configure(state="disabled", text="Running..."); self.prov_log.delete("1.0", "end")
        threading.Thread(target=self._provision_task, args=(ssid, pwd, name, self.current_setup_ip or "10.22.22.1", self.current_setup_port), daemon=True).start()

    def _provision_task(self, s, p, n, ip, pt):
        self.log_prov(f"--- Configuring {ip} ---")
        try:
            url = f"http://{ip}:{pt or 49153}/setup.xml"
            dev = pywemo.discovery.device_from_description(url)
            if n and hasattr(dev, 'basicevent'): dev.basicevent.ChangeFriendlyName(FriendlyName=n); time.sleep(1)
            for m in [2,1,0]:
                try: dev.setup(ssid=s, password=p, _encrypt_method=m); self.log_prov("SUCCESS! Rebooting..."); break
                except: pass
        except Exception as e: self.log_prov(f"Error: {e}")
        self.prov_btn.configure(state="normal", text="Push Configuration")

    def log_prov(self, m): self.prov_log.insert("end", f"{m}\n"); self.prov_log.see("end")
    
    def scan_ssids(self):
        for w in self.ssid_list.winfo_children(): w.destroy()
        threading.Thread(target=self._scan_thread_logic, args=(ctk.CTkLabel(self.ssid_list, text="Scanning...", text_color="yellow"),), daemon=True).start()
    
    def _scan_thread_logic(self, l):
        l.pack(); w = NetworkUtils.scan_wifi_networks(); l.destroy()
        if w: 
            for s in set(w): self.after(0, lambda x=s: self.build_ssid_card(x))
        else: self.after(0, lambda: ctk.CTkLabel(self.ssid_list, text="No Wemo networks found.", text_color="#ff5555").pack())
    
    def build_ssid_card(self, s):
        c = ctk.CTkFrame(self.ssid_list, fg_color=COLOR_FRAME); c.pack(fill="x", pady=2, padx=5)
        ctk.CTkLabel(c, text=s, font=("Arial", 12, "bold"), text_color=COLOR_TEXT).pack(side="left", padx=10)
        if WifiAutomator.can_automate(): 
            def connect_action(ssid=s):
                self.log_prov(f"Connecting to {ssid}...")
                threading.Thread(target=lambda: self._connect_task(ssid), daemon=True).start()
            ctk.CTkButton(c, text="Connect", width=80, height=24, fg_color=COLOR_SUCCESS, command=connect_action).pack(side="right", padx=10)
        else: ctk.CTkLabel(c, text="> Connect Manually", text_color="gray", font=("Arial", 10)).pack(side="right", padx=10)

    def _connect_task(self, ssid):
        success = WifiAutomator.connect_open_network(ssid)
        if success: self.log_prov(f"Success: Connected to {ssid}")
        else: self.log_prov(f"Failed to connect to {ssid}. Try manual connection.")

    def apply_profile(self, c):
        if c in self.profiles: self.ssid_entry.delete(0, "end"); self.ssid_entry.insert(0, c); self.pass_entry.delete(0, "end"); self.pass_entry.insert(0, self.profiles[c])
    def save_current_profile(self):
        s, p = self.ssid_entry.get(), self.pass_entry.get()
        if s and p: self.profiles[s] = p; self.save_json(PROFILE_FILE, self.profiles); self.profile_combo.configure(values=["Select Saved Profile..."] + list(self.profiles.keys())); self.profile_combo.set(s)
    def delete_profile(self):
        c = self.profile_combo.get()
        if c in self.profiles: del self.profiles[c]; self.save_json(PROFILE_FILE, self.profiles); self.profile_combo.configure(values=["Select Saved Profile..."] + list(self.profiles.keys())); self.profile_combo.set("Select Saved Profile...")

    def _connection_monitor(self):
        while self.monitoring:
            if self.manual_override_active: time.sleep(3); continue
            found = False
            for ip in ["10.22.22.1", "192.168.49.1"]:
                for p in [49153, 49152, 49154]:
                    try: 
                        d = pywemo.discovery.device_from_description(f"http://{ip}:{p}/setup.xml")
                        if d: self.current_setup_ip=ip; self.current_setup_port=p; self.after(0, lambda: self.set_status_connected(d, ip, p)); found=True; break
                    except: pass
                if found: break
            if not found: self.current_setup_ip=None; self.after(0, self.set_status_disconnected)
            time.sleep(5)

    def set_status_connected(self, d, i, p):
        self.status_frame.configure(fg_color=("#d0f0c0", "#1a331a"), border_color="#28a745"); self.status_lbl_icon.configure(text="OK"); self.status_lbl_text.configure(text="CONNECTED", text_color="#28a745"); self.status_lbl_sub.configure(text=f"Found: {d.name} ({i}:{p})", text_color=COLOR_TEXT); self.prov_btn.configure(state="normal", text="Push Configuration"); self.override_link.pack_forget()
    def set_status_disconnected(self):
        self.status_frame.configure(fg_color=("#fadbd8", "#331111"), border_color="#ff5555"); self.status_lbl_icon.configure(text="X"); self.status_lbl_text.configure(text="NOT CONNECTED", text_color="#ff5555"); self.status_lbl_sub.configure(text="Connect Wi-Fi to 'Wemo.Mini.XXX'", font=("Arial", 12), text_color=COLOR_TEXT); self.prov_btn.configure(state="disabled", text="Waiting for Connection..."); self.override_link.pack(anchor="e", pady=(0, 5))
    def force_unlock(self):
        self.status_frame.configure(fg_color=("#fcf3cf", "#332200"), border_color="#FFA500"); self.status_lbl_icon.configure(text="(!)"); self.status_lbl_text.configure(text="MANUAL OVERRIDE", text_color="#FFA500"); self.status_lbl_sub.configure(text="Forced Unlock. Assuming 10.22.22.1.", text_color=COLOR_TEXT); self.prov_btn.configure(state="normal", text="Push Configuration (Forced)"); self.current_setup_ip="10.22.22.1"; self.manual_override_active=True

    def create_schedule_ui(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["sched"] = frame
        head = ctk.CTkFrame(frame, fg_color="transparent"); head.pack(fill="x", pady=20)
        ctk.CTkLabel(head, text="Automation Scheduler", font=FONT_H1, text_color=COLOR_TEXT).pack(side="left")
        self.sched_mode_lbl = ctk.CTkLabel(head, text="MODE: CHECKING...", font=("Arial", 12, "bold"), text_color="gray"); self.sched_mode_lbl.pack(side="right", padx=10)
        loc_frame = ctk.CTkFrame(frame, fg_color=COLOR_FRAME); loc_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(loc_frame, text="Solar Location:", font=FONT_H2, text_color=COLOR_TEXT).pack(side="left", padx=10)
        self.loc_lbl = ctk.CTkLabel(loc_frame, text="Detecting...", text_color="orange"); self.loc_lbl.pack(side="left")
        ctk.CTkButton(loc_frame, text="Update Solar Data", width=120, fg_color=COLOR_BTN_SECONDARY, text_color=COLOR_BTN_TEXT, command=self.update_solar_data).pack(side="right", padx=10, pady=5)
        creator_frame = ctk.CTkFrame(frame); creator_frame.pack(fill="x", pady=10)
        r1 = ctk.CTkFrame(creator_frame, fg_color="transparent"); r1.pack(fill="x", padx=10, pady=5)
        self.sched_dev_combo = ctk.CTkComboBox(r1, values=["Scanning..."], width=200); self.sched_dev_combo.pack(side="left", padx=5)
        self.sched_action_combo = ctk.CTkComboBox(r1, values=["Turn ON", "Turn OFF", "Toggle"], width=100); self.sched_action_combo.pack(side="left", padx=5)
        self.sched_type_combo = ctk.CTkComboBox(r1, values=["Time (Fixed)", "Sunrise", "Sunset"], width=130, command=self.on_sched_type_change); self.sched_type_combo.pack(side="left", padx=5)
        r2 = ctk.CTkFrame(creator_frame, fg_color="transparent"); r2.pack(fill="x", padx=10, pady=5)
        self.sched_val_lbl = ctk.CTkLabel(r2, text="Time (HH:MM):", text_color=COLOR_TEXT); self.sched_val_lbl.pack(side="left", padx=5)
        self.sched_val_entry = ctk.CTkEntry(r2, width=80, placeholder_text="18:00"); self.sched_val_entry.pack(side="left", padx=5)
        self.sched_offset_combo = ctk.CTkComboBox(r2, values=["+ (After)", "- (Before)"], width=100); self.sched_offset_combo.pack(side="left", padx=5); self.sched_offset_combo.pack_forget()
        self.day_vars = []; days = ["M", "T", "W", "Th", "F", "Sa", "Su"]; day_frame = ctk.CTkFrame(r2, fg_color="transparent"); day_frame.pack(side="left", padx=20)
        for i, d in enumerate(days):
            v = ctk.BooleanVar(value=True); self.day_vars.append(v); ctk.CTkCheckBox(day_frame, text=d, variable=v, width=40, text_color=COLOR_TEXT).pack(side="left", padx=2)
        ctk.CTkButton(r2, text="Create Job", width=100, fg_color=COLOR_SUCCESS, command=self.add_job).pack(side="right", padx=10)
        ctk.CTkLabel(frame, text="Active Schedules", font=FONT_H2, text_color=COLOR_TEXT).pack(anchor="w", pady=(10,0))
        self.job_list_frame = ctk.CTkScrollableFrame(frame, height=350, label_text="Scheduled Jobs"); self.job_list_frame.pack(fill="both", expand=True, pady=5)
        self.render_jobs(); self.update_solar_data()

    def on_sched_type_change(self, choice):
        if choice == "Time (Fixed)": self.sched_val_lbl.configure(text="Time (HH:MM):"); self.sched_val_entry.configure(placeholder_text="18:00"); self.sched_offset_combo.pack_forget()
        else: self.sched_val_lbl.configure(text="Offset (Mins):"); self.sched_val_entry.configure(placeholder_text="30"); self.sched_offset_combo.pack(side="left", padx=5, after=self.sched_val_entry)

    def update_solar_data(self):
        def task():
            solar_data = self.solar.get_solar_times()
            if solar_data:
                txt = f"Lat: {self.solar.lat} | Rise: {solar_data['sunrise']} | Set: {solar_data['sunset']}"
                self.after(0, lambda: self.loc_lbl.configure(text=txt, text_color="gray"))
                self.settings["lat"] = self.solar.lat; self.settings["lng"] = self.solar.lng; self.save_json(SETTINGS_FILE, self.settings)
            else: self.after(0, lambda: self.loc_lbl.configure(text="Location Failed.", text_color="red"))
        threading.Thread(target=task, daemon=True).start()

    def update_schedule_dropdown(self):
        names = sorted([d.name for d in self.known_devices_map.values()])
        if names: self.sched_dev_combo.configure(values=names); self.sched_dev_combo.set(names[0])

    def add_job(self):
        if os.path.exists(SCHEDULE_FILE): self.schedules = self.load_json(SCHEDULE_FILE, list)
        dev = self.sched_dev_combo.get(); action = self.sched_action_combo.get(); sType = self.sched_type_combo.get(); val = self.sched_val_entry.get()
        active_days = [i for i, v in enumerate(self.day_vars) if v.get()]
        if not active_days: messagebox.showwarning("Error", "Select at least one day."); return
        offset_mod = 1
        if sType != "Time (Fixed)":
            if self.sched_offset_combo.get() == "- (Before)": offset_mod = -1
        job = {"id": int(time.time()), "device": dev, "action": action, "type": sType, "value": val, "offset_dir": offset_mod, "days": active_days, "last_run": ""}
        self.schedules.append(job); self.save_json(SCHEDULE_FILE, self.schedules); self.render_jobs()

    def render_jobs(self):
        for w in self.job_list_frame.winfo_children(): w.destroy()
        if not self.schedules: ctk.CTkLabel(self.job_list_frame, text="No schedules active.", text_color="gray").pack(pady=20); return
        days_map = ["M", "T", "W", "Th", "F", "Sa", "Su"]
        for job in self.schedules:
            row = ctk.CTkFrame(self.job_list_frame, fg_color=COLOR_FRAME); row.pack(fill="x", pady=2)
            d_str = "".join([days_map[i] for i in job['days']])
            if len(job['days']) == 7: d_str = "Every Day"
            ctk.CTkLabel(row, text=f"[{d_str}] {job['type']} -> {job['action']} '{job['device']}'", font=("Consolas", 12), text_color=COLOR_TEXT).pack(side="left", padx=10, pady=5)
            ctk.CTkButton(row, text="Del", width=40, fg_color=COLOR_DANGER, command=lambda j=job: self.delete_job(j["id"])).pack(side="right", padx=5)

    def delete_job(self, jid):
        self.api.delete_schedule(jid); self.schedules = [j for j in self.schedules if j["id"] != jid]; self.save_json(SCHEDULE_FILE, self.schedules); self.render_jobs()

    def _scheduler_engine(self):
        last_mtime = 0
        while self.monitoring:
            try:
                if os.path.exists(SCHEDULE_FILE):
                    current_mtime = os.path.getmtime(SCHEDULE_FILE)
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        self.schedules = self.load_json(SCHEDULE_FILE, list)
                        if self.frames["sched"].winfo_ismapped(): self.after(0, self.render_jobs)
                if self.api.connected: self.sched_mode_lbl.configure(text="MODE: SERVER", text_color=COLOR_ACCENT); time.sleep(2); continue
                else: self.sched_mode_lbl.configure(text="MODE: LOCAL", text_color="orange")
            except Exception as e: pass
            time.sleep(2) 

    def create_maintenance_ui(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["maint"] = f
        ctk.CTkLabel(f, text="Device Maintenance Tools", font=FONT_H1, text_color=COLOR_TEXT).pack(pady=20)
        sel = ctk.CTkFrame(f, fg_color=COLOR_FRAME); sel.pack(fill="x", padx=20, pady=10)
        self.maint_dev_combo = ctk.CTkComboBox(sel, values=["Scanning..."], width=300); self.maint_dev_combo.pack(side="left", padx=10)
        grid = ctk.CTkFrame(f, fg_color="transparent"); grid.pack(fill="both", expand=True, padx=20, pady=10)
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1); grid.columnconfigure(2, weight=1)
        
        c1 = ctk.CTkFrame(grid, fg_color=("#fff8e1", "#332222")); c1.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c1, text="Personal Data", font=FONT_H2, text_color=("#b38f00", "#ffcc00")).pack(pady=(15,5))
        ctk.CTkLabel(c1, text="Clears Name, Icon, Rules.\nKeeps Wi-Fi Connection.", text_color="gray", font=("Arial", 11)).pack(pady=5)
        ctk.CTkButton(c1, text="Reset Data (1)", fg_color=COLOR_MAINT_BTN_Y, text_color="#000000", command=lambda: self.run_reset_command(1)).pack(pady=15)
        
        c2 = ctk.CTkFrame(grid, fg_color=("#e3f2fd", "#222233")); c2.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c2, text="Wi-Fi Setup", font=FONT_H2, text_color=("#0055aa", "#66aaff")).pack(pady=(15,5))
        ctk.CTkLabel(c2, text="Clears Wi-Fi Credentials.\nReturns to Setup Mode.", text_color="gray", font=("Arial", 11)).pack(pady=5)
        ctk.CTkButton(c2, text="Reset Wi-Fi (5)", fg_color=COLOR_MAINT_BTN_B, text_color="#ffffff", command=lambda: self.run_reset_command(5)).pack(pady=15)
        
        c3 = ctk.CTkFrame(grid, fg_color=("#ffebee", "#330000")); c3.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c3, text="Factory Default", font=FONT_H2, text_color=("#aa0000", "#ff4444")).pack(pady=(15,5))
        ctk.CTkLabel(c3, text="Wipes Everything.\nLike New Out-of-Box.", text_color="gray", font=("Arial", 11)).pack(pady=5)
        ctk.CTkButton(c3, text="Factory Reset (2)", fg_color=COLOR_MAINT_BTN_R, text_color="#ffffff", command=lambda: self.run_reset_command(2)).pack(pady=15)

    def update_maint_dropdown(self):
        names = sorted([d.name for d in self.known_devices_map.values()])
        if names: self.maint_dev_combo.configure(values=names); self.maint_dev_combo.set(names[0])
            
    def run_reset_command(self, reset_code):
        name = self.maint_dev_combo.get()
        dev = next((d for d in self.known_devices_map.values() if d.name == name), None)
        if not dev: return messagebox.showerror("Error", "Device not found.")
        if not messagebox.askyesno("Confirm Reset", f"Reset '{name}' (Code {reset_code})?"): return
        def task():
            try: dev.basicevent.ReSetup(Reset=reset_code); self.after(0, lambda: messagebox.showinfo("Success", "Command Sent"))
            except Exception as e: self.after(0, lambda: messagebox.showerror("Failure", str(e)))
        threading.Thread(target=task, daemon=True).start()

    def create_settings_ui(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["settings"] = f
        ctk.CTkLabel(f, text="Application Settings", font=FONT_H1, text_color=COLOR_TEXT).pack(pady=(0, 20), anchor="w")
        c = ctk.CTkFrame(f, fg_color=COLOR_CARD); c.pack(fill="x", pady=10, padx=5)
        
        # [NEW] Added explicit labels for the settings
        r1 = ctk.CTkFrame(c, fg_color="transparent"); r1.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(r1, text="Appearance Mode:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left")
        ctk.CTkComboBox(r1, values=["System", "Light", "Dark"], command=self.change_theme, variable=ctk.StringVar(value=self.settings.get("theme", "System")), width=150).pack(side="right")
        
        r2 = ctk.CTkFrame(c, fg_color="transparent"); r2.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(r2, text="UI Scaling:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left")
        ctk.CTkComboBox(r2, values=["80%", "90%", "100%", "110%", "120%", "150%"], command=self.change_scaling, variable=ctk.StringVar(value=self.settings.get("scale", "100%")), width=150).pack(side="right")

    def change_theme(self, m): ctk.set_appearance_mode(m); self.settings["theme"]=m; self.save_json(SETTINGS_FILE, self.settings)
    def change_scaling(self, s): self.set_ui_scale(s); self.settings["scale"]=s; self.save_json(SETTINGS_FILE, self.settings)

    def show_qr_code(self):
        try:
            ip = NetworkUtils.get_local_ip(); url = f"http://{ip}:{SERVER_PORT}"
            qr = qrcode.QRCode(box_size=10, border=4); qr.add_data(url); qr.make(fit=True)
            img = ctk.CTkImage(light_image=qr.make_image(fill_color="black", back_color="white").convert("RGB"), dark_image=qr.make_image(fill_color="black", back_color="white").convert("RGB"), size=(250, 250))
            win = ctk.CTkToplevel(self); win.title("Mobile App"); win.geometry("400x480"); win.transient(self); win.focus_force(); self.set_icon(win)
            ctk.CTkLabel(win, image=img, text="").pack(padx=20, pady=(30, 20))
            ctk.CTkLabel(win, text="Scan to Control on Mobile", font=("Arial", 16, "bold")).pack(pady=(0,5))
            l=ctk.CTkLabel(win, text=url, text_color="gray", cursor="hand2", font=("Consolas", 14, "underline")); l.pack(pady=(0,20)); l.bind("<Button-1>", lambda e: webbrowser.open(url))
            ctk.CTkButton(win, text="Close", command=win.destroy, fg_color="gray").pack(pady=10)
        except Exception as e: messagebox.showerror("QR Error", str(e))

    def run_update_check(self):
        h, n = UpdateManager.check_for_updates(VERSION, UPDATE_API_URL)
        if h: self.after(0, lambda: self.btn_update.configure(text=f"⬇ Get {n}") or self.btn_update.pack(side="bottom", padx=10, pady=(0, 10)))

    def start_local_server(self):
        cmd = [SERVICE_EXE_PATH] if SERVICE_EXE_PATH and os.path.exists(SERVICE_EXE_PATH) else [sys.executable, "wemo_server.py"]
        try:
            startupinfo = subprocess.STARTUPINFO() if sys.platform == "win32" else None
            if startupinfo: startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen(cmd, startupinfo=startupinfo)
            self.svc_status.configure(text="Starting...", text_color="orange")
        except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = WemoOpsApp()
    app.mainloop()