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
VERSION = "v5.2.3-Stable"
SERVER_PORT = 5050
SERVER_URL = f"http://localhost:{SERVER_PORT}"
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

    def check_connection(self):
        try:
            r = requests.get(f"{SERVER_URL}/api/status", timeout=0.5)
            if r.status_code == 200:
                self.connected = True
                return True
        except: pass
        self.connected = False
        return False

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

# ==============================================================================
#  DEEP SCANNER
# ==============================================================================
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

class SolarEngine:
    def __init__(self):
        self.lat = None; self.lng = None; self.solar_times = {}; self.last_fetch = None
    
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
                return True, remote_tag
        except: pass
        return False, None

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
#  MAIN APP
# ==============================================================================
class WemoOpsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Wemo Ops Center {VERSION}")
        self.geometry("1100x800")
        
        # Icon setup
        self.set_icon(self)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.api = APIClient() 
        self.settings = self.load_json(SETTINGS_FILE, dict)
        self.profiles = self.load_json(PROFILE_FILE, dict)
        self.schedules = self.load_json(SCHEDULE_FILE, list) or []
        self.saved_subnets = self.settings.get("subnets", [])
        
        self.known_devices_map = {}
        self.device_switches = {} # [NEW] Track switches for live updates
        self.last_rendered_device_names = [] 
        self.solar = SolarEngine()
        self.scanner = DeepScanner()
        self.current_setup_ip = None
        self.current_setup_port = None
        self.manual_override_active = False

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
        
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True)
        
        if HAS_QR:
            ctk.CTkButton(self.sidebar, text="📱 Mobile App", fg_color=COLOR_ACCENT, command=self.show_qr_code).pack(pady=5, padx=10)

        self.btn_settings = self.create_nav_btn("Settings", "settings")

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
        
        self.show_tab("dash")
        self.after(500, self.refresh_network)
        
        self.monitoring = True
        threading.Thread(target=self._connection_monitor, daemon=True).start()
        threading.Thread(target=self._scheduler_engine, daemon=True).start()
        threading.Thread(target=self.run_update_check, daemon=True).start()
        
        # [NEW] Start State Poller for Live Updates
        threading.Thread(target=self._state_poller, daemon=True).start()
        
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
    def set_icon(self, window):
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(base_path, "images", "app_icon.ico")
            
            if os.path.exists(icon_path):
                window.iconbitmap(icon_path)
        except Exception:
            pass

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

    def server_heartbeat(self):
        self.api.check_connection()
        try:
            if self.api.connected:
                self.sched_mode_lbl.configure(text="MODE: SERVER (Remote)", text_color=COLOR_ACCENT)
            else:
                self.sched_mode_lbl.configure(text="MODE: LOCAL (PC)", text_color="orange")
        except: pass
        self.after(5000, self.server_heartbeat)

    # --- DASHBOARD (LIVE UPDATE SUPPORT) ---
    def create_dashboard(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["dash"] = f
        
        # Main Header Frame
        head = ctk.CTkFrame(f, fg_color="transparent"); head.pack(fill="x", pady=(0, 20))
        
        # Title (Left)
        ctk.CTkLabel(head, text="Network Overview", font=FONT_H1, text_color=COLOR_TEXT).pack(side="left", anchor="n")
        
        # Right Side Panel (Vertical Stack to prevent jitter)
        right_panel = ctk.CTkFrame(head, fg_color="transparent")
        right_panel.pack(side="right", anchor="e")
        
        # -- Row 1: Controls --
        ctrl_row = ctk.CTkFrame(right_panel, fg_color="transparent")
        ctrl_row.pack(side="top", anchor="e")
        
        # Subnet Dropdown
        self.subnet_combo = ctk.CTkComboBox(ctrl_row, width=180, values=self.saved_subnets)
        self.subnet_combo.pack(side="left", padx=(0, 5))
        self.subnet_combo.set(NetworkUtils.get_subnet_cidr())
        
        # Save/Del Buttons
        ctk.CTkButton(ctrl_row, text="Save", width=50, command=self.save_subnet, fg_color=COLOR_ACCENT).pack(side="left", padx=2)
        ctk.CTkButton(ctrl_row, text="Del", width=50, command=self.delete_subnet, fg_color=COLOR_DANGER).pack(side="left", padx=(2, 10))
        
        # Deep Scan & Scan Button
        self.use_deep_scan = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ctrl_row, text="Deep Scan", variable=self.use_deep_scan, width=80).pack(side="left", padx=5)
        ctk.CTkButton(ctrl_row, text="Scan", width=100, command=self.run_local_scan, fg_color=COLOR_ACCENT).pack(side="left", padx=5)
        
        # -- Row 2: Status Label (Fixed Underneath) --
        self.scan_status = ctk.CTkLabel(right_panel, text="Ready", text_color="orange", font=("Arial", 12))
        self.scan_status.pack(side="top", anchor="e", padx=10, pady=(2, 0))
        
        # Device List
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
        is_deep = self.use_deep_scan.get() 
        self.scan_status.configure(text="Initializing...")
        threading.Thread(target=self._scan_task, args=(subnet, is_deep), daemon=True).start()

    def _scan_task(self, subnet, use_deep):
        def log(m): self.after(0, lambda: self.scan_status.configure(text=m))
        try:
            log("Quick Scan (SSDP)...")
            new_map = {}
            for d in pywemo.discover_devices(): 
                new_map[d.name] = d
            
            if use_deep and subnet:
                log(f"Deep Probing {subnet}...")
                deep_devs = self.scanner.scan_subnet(subnet, status_callback=log) 
                for d in deep_devs:
                    new_map[d.name] = d
            
            self.known_devices_map = new_map
            log("Done.")
            self.after(0, self.render_devices)
            self.after(0, self.update_maint_dropdown)
            self.after(0, self.update_schedule_dropdown)
        except Exception as e: log(f"Error: {e}")

    def refresh_network(self):
        self.run_local_scan()

    def render_devices(self):
        # [NEW] Clear switch registry on redraw
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
        sw = ctk.CTkSwitch(t, text="Power", command=tog, text_color=COLOR_TEXT); sw.pack(side="right")
        
        # [NEW] Register Switch for Live Updates
        self.device_switches[dev.name] = sw
        
        try:
            state = dev.get_state(force_update=False) 
            if state: sw.select()
        except: pass

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

    # --- STATE POLLER (NEW) ---
    def _state_poller(self):
        while self.monitoring:
            try:
                # Don't poll if dashboard isn't visible (save resources)
                try:
                    if not self.frames["dash"].winfo_ismapped():
                        time.sleep(2)
                        continue
                except: pass

                # Cycle through known devices
                for name, dev in self.known_devices_map.items():
                    if name in self.device_switches:
                        try:
                            # FORCE UPDATE from physical device
                            state = dev.get_state(force_update=True)
                            
                            # Safe UI Update on Main Thread
                            self.after(0, lambda n=name, s=state: self._update_switch_safe(n, s))
                        except: pass
            except: pass
            time.sleep(2) # 2 Second Refresh Rate

    def _update_switch_safe(self, name, state):
        if name in self.device_switches:
            try:
                sw = self.device_switches[name]
                if state: sw.select()
                else: sw.deselect()
            except: pass

    # --- PROVISIONER ---
    def create_provisioner(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["prov"] = f
        f.columnconfigure(0, weight=1); f.columnconfigure(1, weight=2); f.rowconfigure(0, weight=1)
        lc = ctk.CTkFrame(f, fg_color="transparent"); lc.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(lc, text="Step 1: Locate Device", font=FONT_H2, text_color=COLOR_TEXT).pack(anchor="w", pady=(0,5))
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
        ssid = self.ssid_entry.get()
        pwd = self.pass_entry.get()
        name = self.name_entry.get()
        if not ssid: return messagebox.showwarning("Missing Data", "Enter SSID.")
        self.prov_btn.configure(state="disabled", text="Running..."); self.prov_log.delete("1.0", "end")
        threading.Thread(target=self._provision_task, args=(ssid, pwd, name, self.current_setup_ip or "10.22.22.1", self.current_setup_port), daemon=True).start()

    def _provision_task(self, s, p, n, ip, pt):
        self.log_prov(f"--- Configuring {ip} ---")
        try:
            url = f"http://{ip}:{pt or 49153}/setup.xml"
            self.log_prov(f"Targeting URL: {url}")
            dev = pywemo.discovery.device_from_description(url)
            
            if n and hasattr(dev, 'basicevent'): 
                self.log_prov(f"Setting Name to: {n}")
                dev.basicevent.ChangeFriendlyName(FriendlyName=n)
                time.sleep(1)
            
            self.log_prov("Starting Adaptive Encryption Loop (Smart Loop)...")
            success = False
            for m in [2,1,0]:
                for length in [True, False]:
                    try: 
                        self.log_prov(f"Attempting: Method {m}, Len={length}...")
                        dev.setup(ssid=s, password=p, _encrypt_method=m, _add_password_lengths=length)
                        self.log_prov("SUCCESS! Credentials Accepted.")
                        success = True
                        break
                    except: pass
                if success: break
            
            if success: self.log_prov("Device is rebooting. Connect PC back to Home Wi-Fi.")
            else: self.log_prov("FAILED: All attempts rejected by device.")
            
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
        else:
            ctk.CTkLabel(c, text="> Connect Manually", text_color="gray", font=("Arial", 10)).pack(side="right", padx=10)

    def _connect_task(self, ssid):
        success = WifiAutomator.connect_open_network(ssid)
        if success: self.log_prov(f"Success: Connected to {ssid}")
        else: self.log_prov(f"Failed to connect to {ssid}. Try manual connection.")

    # --- MISSING PROFILE METHODS ---
    def apply_profile(self, c):
        if c in self.profiles:
            self.ssid_entry.delete(0, "end")
            self.ssid_entry.insert(0, c)
            self.pass_entry.delete(0, "end")
            self.pass_entry.insert(0, self.profiles[c])

    def save_current_profile(self):
        s, p = self.ssid_entry.get(), self.pass_entry.get()
        if s and p:
            self.profiles[s] = p
            self.save_json(PROFILE_FILE, self.profiles)
            self.profile_combo.configure(values=["Select Saved Profile..."] + list(self.profiles.keys()))
            self.profile_combo.set(s)

    def delete_profile(self):
        c = self.profile_combo.get()
        if c in self.profiles:
            del self.profiles[c]
            self.save_json(PROFILE_FILE, self.profiles)
            self.profile_combo.configure(values=["Select Saved Profile..."] + list(self.profiles.keys()))
            self.profile_combo.set("Select Saved Profile...")

    # --- AUTOMATION / SCHEDULER (Hybrid Engine) ---
    def create_schedule_ui(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["sched"] = frame
        
        # Header with Mode Indicator
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", pady=20)
        ctk.CTkLabel(head, text="Automation Scheduler", font=FONT_H1, text_color=COLOR_TEXT).pack(side="left")
        self.sched_mode_lbl = ctk.CTkLabel(head, text="MODE: CHECKING...", font=("Arial", 12, "bold"), text_color="gray")
        self.sched_mode_lbl.pack(side="right", padx=10)
        
        # Location / Solar Panel
        loc_frame = ctk.CTkFrame(frame, fg_color=COLOR_FRAME)
        loc_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(loc_frame, text="Solar Location:", font=FONT_H2, text_color=COLOR_TEXT).pack(side="left", padx=10)
        self.loc_lbl = ctk.CTkLabel(loc_frame, text="Detecting...", text_color="orange")
        self.loc_lbl.pack(side="left")
        ctk.CTkButton(loc_frame, text="Update Solar Data", width=120, fg_color=COLOR_BTN_SECONDARY, text_color=COLOR_BTN_TEXT, command=self.update_solar_data).pack(side="right", padx=10, pady=5)
        
        # Creator Panel
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
        self.job_list_frame = ctk.CTkScrollableFrame(frame, height=350, label_text="Scheduled Jobs")
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

    def update_schedule_dropdown(self):
        names = sorted([d.name for d in self.known_devices_map.values()])
        if names: 
            self.sched_dev_combo.configure(values=names)
            self.sched_dev_combo.set(names[0])

    def add_job(self):
        # [SAFETY] Reload latest data from disk before modifying
        if os.path.exists(SCHEDULE_FILE):
            self.schedules = self.load_json(SCHEDULE_FILE, list)

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
        self.schedules.append(job)
        self.save_json(SCHEDULE_FILE, self.schedules)
        self.render_jobs()

    def render_jobs(self):
        for w in self.job_list_frame.winfo_children(): w.destroy()
        if not self.schedules: ctk.CTkLabel(self.job_list_frame, text="No schedules active.", text_color="gray").pack(pady=20); return
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
            ctk.CTkButton(row, text="Del", width=40, fg_color=COLOR_DANGER, command=lambda j=job: self.delete_job(j["id"])).pack(side="right", padx=5)

    def delete_job(self, jid):
        self.schedules = [j for j in self.schedules if j["id"] != jid]
        self.save_json(SCHEDULE_FILE, self.schedules)
        self.render_jobs()

    def _scheduler_engine(self):
        last_mtime = 0
        while self.monitoring:
            try:
                if os.path.exists(SCHEDULE_FILE):
                    current_mtime = os.path.getmtime(SCHEDULE_FILE)
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        new_data = self.load_json(SCHEDULE_FILE, list)
                        if new_data != self.schedules:
                            self.schedules = new_data
                            if self.frames["sched"].winfo_ismapped():
                                self.after(0, self.render_jobs)
                
                if self.api.connected:
                    time.sleep(2) 
                    continue

                now = datetime.datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                weekday = now.weekday()
                current_hhmm = now.strftime("%H:%M")
                solar = self.solar.get_solar_times()
                
                dirty = False
                for job in self.schedules:
                    if weekday not in job['days']: continue
                    
                    trigger_time = ""
                    if job['type'] == "Time (Fixed)": 
                        trigger_time = job['value']
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
                        dirty = True
                
                if dirty:
                    self.save_json(SCHEDULE_FILE, self.schedules)
                    last_mtime = os.path.getmtime(SCHEDULE_FILE)

            except Exception as e: pass
            time.sleep(2) 

    def execute_job(self, job):
        dev_name = job['device']
        dev = next((d for d in self.known_devices_map.values() if d.name == dev_name), None)
        if dev:
            try:
                if job['action'] == "Turn ON": dev.on()
                elif job['action'] == "Turn OFF": dev.off()
                elif job['action'] == "Toggle": dev.toggle()
            except: pass

    # --- MAINTENANCE (Local) ---
    def create_maintenance_ui(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["maint"] = f
        ctk.CTkLabel(f, text="Device Maintenance Tools", font=FONT_H1, text_color=COLOR_TEXT).pack(pady=20)
        sel = ctk.CTkFrame(f, fg_color=COLOR_FRAME); sel.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(sel, text="Select Target Device:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left", padx=10, pady=10)
        self.maint_dev_combo = ctk.CTkComboBox(sel, values=["Scanning..."], width=300); self.maint_dev_combo.pack(side="left", padx=10)
        grid = ctk.CTkFrame(f, fg_color="transparent"); grid.pack(fill="both", expand=True, padx=20, pady=10)
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1); grid.columnconfigure(2, weight=1)
        c1 = ctk.CTkFrame(grid, fg_color=("#fff8e1", "#332222")); c1.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c1, text="Clear Personal Info", font=FONT_H2, text_color=("#b38f00", "#ffcc00")).pack(pady=(15,5))
        ctk.CTkLabel(c1, text="Removes custom Name, Icon,\nand Rules. Keeps Wi-Fi.", text_color="gray").pack(pady=5)
        ctk.CTkButton(c1, text="Run (Reset=1)", fg_color=COLOR_MAINT_BTN_Y, text_color="#000000", command=lambda: self.run_reset_command(1)).pack(pady=15)
        c2 = ctk.CTkFrame(grid, fg_color=("#e3f2fd", "#222233")); c2.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c2, text="Clear Wi-Fi", font=FONT_H2, text_color=("#0055aa", "#66aaff")).pack(pady=(15,5))
        ctk.CTkLabel(c2, text="Resets Wi-Fi Credentials", text_color="gray").pack(pady=5)
        ctk.CTkButton(c2, text="Run (Reset=5)", fg_color=COLOR_MAINT_BTN_B, text_color="#ffffff", command=lambda: self.run_reset_command(5)).pack(pady=15)
        c3 = ctk.CTkFrame(grid, fg_color=("#ffebee", "#330000")); c3.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(c3, text="Factory Reset", font=FONT_H2, text_color=("#aa0000", "#ff4444")).pack(pady=(15,5))
        ctk.CTkLabel(c3, text="Full Wipe (Out of Box)", text_color="gray").pack(pady=5)
        ctk.CTkButton(c3, text="NUKE (Reset=2)", fg_color=COLOR_MAINT_BTN_R, text_color="#ffffff", command=lambda: self.run_reset_command(2)).pack(pady=15)

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

    # --- SETTINGS (Local) ---
    def create_settings_ui(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent"); self.frames["settings"] = f
        ctk.CTkLabel(f, text="Application Settings", font=FONT_H1, text_color=COLOR_TEXT).pack(pady=(0, 20), anchor="w")
        c = ctk.CTkFrame(f, fg_color=COLOR_CARD); c.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(c, text="Appearance & Display", font=FONT_H2, text_color=COLOR_TEXT).pack(padx=20, pady=(15,5), anchor="w")
        r1 = ctk.CTkFrame(c, fg_color="transparent"); r1.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(r1, text="Theme Mode:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left")
        ctk.CTkComboBox(r1, values=["System", "Light", "Dark"], command=self.change_theme, variable=ctk.StringVar(value=self.settings.get("theme", "System")), width=150).pack(side="right")
        r2 = ctk.CTkFrame(c, fg_color="transparent"); r2.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(r2, text="UI Scaling:", font=FONT_BODY, text_color=COLOR_TEXT).pack(side="left")
        ctk.CTkComboBox(r2, values=["80%", "90%", "100%", "110%", "120%", "150%"], command=self.change_scaling, variable=ctk.StringVar(value=self.settings.get("scale", "100%")), width=150).pack(side="right")

    def change_theme(self, m): ctk.set_appearance_mode(m); self.settings["theme"]=m; self.save_json(SETTINGS_FILE, self.settings)
    def change_scaling(self, s): self.set_ui_scale(s); self.settings["scale"]=s; self.save_json(SETTINGS_FILE, self.settings)

    # --- QR CODE ---
    def show_qr_code(self):
        try:
            # Generate QR for Local IP + Server Port
            ip = NetworkUtils.get_local_ip()
            url = f"http://{ip}:{SERVER_PORT}"
            
            qr = qrcode.QRCode(box_size=10, border=4)
            qr.add_data(url)
            qr.make(fit=True)
            
            # Use native RGB conversion for CTkImage
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            qr_ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(250, 250))
            
            # Create Window
            win = ctk.CTkToplevel(self)
            win.title("Mobile App")
            
            # [FIX 1] Apply Icon Immediately
            self.set_icon(win)
            
            # [FIX 2] Force Icon again after 200ms (Fixes "Missing Icon" on Windows Popups)
            win.after(200, lambda: self.set_icon(win))
            
            # Center Window Logic
            self.update_idletasks()
            w = 400
            h = 480
            x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
            y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
            win.geometry(f"{w}x{h}+{x}+{y}")
            
            win.transient(self)
            win.focus_force()

            # Content
            lbl_img = ctk.CTkLabel(win, image=qr_ctk_img, text="")
            lbl_img.pack(padx=20, pady=(30, 20))
            
            ctk.CTkLabel(win, text="Scan to Control on Mobile", font=("Arial", 16, "bold")).pack(pady=(0,5))
            
            link = ctk.CTkLabel(win, text=url, text_color="gray", cursor="hand2", font=("Consolas", 14, "underline"))
            link.pack(pady=(0,20))
            link.bind("<Button-1>", lambda e: webbrowser.open(url))
            
            ctk.CTkButton(win, text="Close", command=win.destroy, fg_color="gray").pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("QR Error", f"Failed to show QR Code:\n{e}")

    # --- UPDATER ---
    def run_update_check(self):
        h, n = UpdateManager.check_for_updates(VERSION, UPDATE_API_URL)
        if h: self.after(0, lambda: self.btn_update.configure(text=f"⬇ Get {n}") or self.btn_update.pack(side="bottom", padx=10, pady=(0, 10)))

    # [REPLACE] existing _connection_monitor with this throttled version:

    def _connection_monitor(self):
        while self.monitoring:
            # OPTIMIZATION: Pause monitoring if we aren't in the Provisioner tab
            try:
                if not self.frames["prov"].winfo_ismapped():
                    time.sleep(2)
                    continue
            except: pass

            if self.manual_override_active: time.sleep(5); continue
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

    def apply_profile(self, c):
        if c in self.profiles: self.ssid_entry.delete(0, "end"); self.ssid_entry.insert(0, c); self.pass_entry.delete(0, "end"); self.pass_entry.insert(0, self.profiles[c])
    def save_current_profile(self):
        s, p = self.ssid_entry.get(), self.pass_entry.get()
        if s and p: self.profiles[s]=p; self.save_json(PROFILE_FILE, self.profiles); self.profile_combo.configure(values=["Select Saved Profile..."]+list(self.profiles.keys())); self.profile_combo.set(s)
    def delete_profile(self):
        c = self.profile_combo.get()
        if c in self.profiles: del self.profiles[c]; self.save_json(PROFILE_FILE, self.profiles); self.profile_combo.configure(values=["Select Saved Profile..."]+list(self.profiles.keys())); self.profile_combo.set("Select Saved Profile...")

if __name__ == "__main__":
    app = WemoOpsApp()
    app.mainloop()