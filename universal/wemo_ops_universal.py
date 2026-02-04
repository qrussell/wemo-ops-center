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
from tkinter import messagebox
import pyperclip

# --- CONFIGURATION ---
VERSION = "v4.1.0 (Service Control)"

# --- PATH SETUP (Cross-Platform) ---
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
SERVICE_EXE_PATH = os.path.join(APP_DATA_DIR, "wemo_service.exe")

# --- PYINSTALLER FIX ---
if getattr(sys, 'frozen', False):
    os.environ['PATH'] += os.pathsep + sys._MEIPASS

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ==============================================================================
#  UNIVERSAL NETWORK UTILS
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
        except Exception as e: 
            print(f"Wifi Scan Error: {e}")
        return [ssid for ssid in list(set(wemos)) if "wemo" in ssid.lower() or "belkin" in ssid.lower()]

# ==============================================================================
#  SERVICE MANAGER (NEW)
# ==============================================================================
class ServiceManager:
    @staticmethod
    def is_running():
        """Checks if wemo_service is running."""
        try:
            if sys.platform == "win32":
                # Check for the specific EXE name
                output = subprocess.check_output('tasklist /FI "IMAGENAME eq wemo_service.exe"', shell=True).decode()
                return "wemo_service.exe" in output
            else:
                # Linux/Mac check
                try:
                    subprocess.check_output('pgrep -f "wemo_service"', shell=True)
                    return True
                except: return False
        except: return False

    @staticmethod
    def start_service():
        """Attempts to launch the service executable."""
        if os.path.exists(SERVICE_EXE_PATH):
            try:
                if sys.platform == "win32":
                    subprocess.Popen([SERVICE_EXE_PATH], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    subprocess.Popen([SERVICE_EXE_PATH], shell=True)
                return True
            except: pass
        return False

# ==============================================================================
#  DEEP SCANNER
# ==============================================================================
class DeepScanner:
    def probe_port(self, ip, port=49153, timeout=0.5):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((str(ip), port))
            s.close()
            return str(ip)
        except: return None

    def scan_subnet(self, target_cidr=None, status_callback=None):
        found_devices = []
        cidr = target_cidr if target_cidr else NetworkUtils.get_subnet_cidr()
        
        if status_callback: status_callback(f"Scanning Subnet: {cidr}")
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            hosts = list(network.hosts())
            active_ips = []
            
            if status_callback: status_callback(f"Probing {len(hosts)} IPs...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                futures = {executor.submit(self.probe_port, ip): ip for ip in hosts}
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result: active_ips.append(result)

            if status_callback: status_callback(f"Found {len(active_ips)} active hosts. Verifying...")
            
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
        except Exception as e:
            print(f"Scan Error: {e}")
            if status_callback: status_callback(f"Invalid Subnet: {cidr}")
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

        self.current_setup_ip = None 
        self.current_setup_port = None 
        
        self.profiles = self.load_json(PROFILE_FILE, dict)
        self.settings = self.load_json(SETTINGS_FILE, dict)
        self.schedules = self.load_json(SCHEDULE_FILE, list) or []
        
        self.known_devices_map = {} 
        self.solar = SolarEngine()
        self.scanner = DeepScanner()

        if "lat" in self.settings:
            self.solar.lat = self.settings["lat"]
            self.solar.lng = self.settings["lng"]

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.logo = ctk.CTkLabel(self.sidebar, text="WEMO OPS", font=("Arial Black", 20))
        self.logo.pack(pady=20)
        
        # Icon Logic
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

        # --- NEW: SERVICE CONTROL ---
        self.service_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.service_frame.pack(side="bottom", fill="x", pady=20, padx=10)
        
        self.svc_lbl = ctk.CTkLabel(self.service_frame, text="Service Status:", font=("Arial", 12, "bold"))
        self.svc_lbl.pack(anchor="w")
        
        self.svc_status = ctk.CTkLabel(self.service_frame, text="Checking...", text_color="gray")
        self.svc_status.pack(anchor="w")

        self.svc_btn = ctk.CTkButton(self.service_frame, text="▶ Start Service", 
                                     fg_color="#28a745", hover_color="#1e7e34", height=24,
                                     command=self.start_service_manually)
        # Button starts hidden
        self.svc_btn.pack_forget()

        ctk.CTkLabel(self.sidebar, text=f"{VERSION}", text_color="gray", font=("Arial", 10)).pack(side="bottom", pady=5)

        # Main Area
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.frames = {}
        self.create_dashboard()
        self.create_provisioner()
        self.create_schedule_ui()

        self.show_tab("dash")
        self.after(500, self.refresh_network)
        
        self.monitoring = True
        threading.Thread(target=self._connection_monitor, daemon=True).start()
        threading.Thread(target=self._scheduler_engine, daemon=True).start()
        
        # Start Service Monitoring Loop
        self.check_service_loop()

    # --- SERVICE CONTROL METHODS ---
    def check_service_loop(self):
        is_running = ServiceManager.is_running()
        
        if is_running:
            self.svc_status.configure(text="✅ RUNNING", text_color="#28a745")
            self.svc_btn.pack_forget() # Hide start button if running
        else:
            self.svc_status.configure(text="❌ STOPPED", text_color="#ff5555")
            self.svc_btn.pack(fill="x", pady=(5,0)) # Show start button
            
        self.after(3000, self.check_service_loop) # Check every 3 seconds

    def start_service_manually(self):
        self.svc_btn.configure(state="disabled", text="Starting...")
        success = ServiceManager.start_service()
        if success:
            self.svc_status.configure(text="⏳ STARTING...", text_color="orange")
            # Loop will pick up the running state shortly
        else:
            messagebox.showerror("Error", f"Could not find service executable at:\n{SERVICE_EXE_PATH}\n\nIs the app installed properly?")
            self.svc_btn.configure(state="normal", text="▶ Start Service")

    def create_nav_btn(self, text, view_name):
        btn = ctk.CTkButton(self.sidebar, text=f"  {text}", anchor="w", command=lambda: self.show_tab(view_name))
        btn.pack(pady=5, padx=10, fill="x")
        return btn

    def show_tab(self, name):
        for key, frame in self.frames.items(): frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        self.btn_dash.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_prov.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_sched.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        if name == "dash": self.btn_dash.configure(fg_color=("gray75", "gray25"), text_color="white")
        elif name == "prov": self.btn_prov.configure(fg_color=("gray75", "gray25"), text_color="white")
        elif name == "sched": self.btn_sched.configure(fg_color=("gray75", "gray25"), text_color="white")

    # --- DASHBOARD ---
    def create_dashboard(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["dash"] = frame
        
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(head, text="Network Overview", font=("Roboto", 24)).pack(side="left")

        scan_ctrl = ctk.CTkFrame(head, fg_color="transparent")
        scan_ctrl.pack(side="right")
        
        self.subnet_entry = ctk.CTkEntry(scan_ctrl, width=140, placeholder_text="192.168.1.0/24")
        self.subnet_entry.pack(side="left", padx=5)
        try: self.subnet_entry.insert(0, NetworkUtils.get_subnet_cidr())
        except: pass

        ctk.CTkButton(scan_ctrl, text="↻ Deep Scan", width=100, command=self.refresh_network).pack(side="left", padx=5)
        
        self.scan_status = ctk.CTkLabel(scan_ctrl, text="", text_color="orange")
        self.scan_status.pack(side="left", padx=10)

        manual_frame = ctk.CTkFrame(frame, fg_color="#222")
        manual_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(manual_frame, text="Direct Connect:", font=("Arial", 12)).pack(side="left", padx=10)
        self.ip_entry = ctk.CTkEntry(manual_frame, placeholder_text="192.168.1.x", width=150)
        self.ip_entry.pack(side="left", padx=5, pady=10)
        ctk.CTkButton(manual_frame, text="Add Device", width=100, fg_color="#444", 
                      command=self.manual_add_device).pack(side="left", padx=5)
        
        self.dev_list = ctk.CTkScrollableFrame(frame, label_text="Discovered Devices")
        self.dev_list.pack(fill="both", expand=True)

    def refresh_network(self):
        for w in self.dev_list.winfo_children(): w.destroy()
        manual_subnet = self.subnet_entry.get().strip()
        self.scan_status.configure(text="Initializing...")
        threading.Thread(target=self._scan_thread, args=(manual_subnet,), daemon=True).start()

    def _scan_thread(self, target_subnet):
        def update_status(msg): self.after(0, lambda: self.scan_status.configure(text=msg))
        try:
            update_status("Quick Scan (SSDP)...")
            devices = pywemo.discover_devices()
            for d in devices: self.known_devices_map[d.name] = d
            
            update_status("Deep Subnet Scan...")
            deep_devices = self.scanner.scan_subnet(target_cidr=target_subnet, status_callback=update_status)
            for d in deep_devices:
                self.known_devices_map[d.name] = d
                if d not in devices: devices.append(d)

            update_status("")
            self.after(0, self.update_dashboard, list(self.known_devices_map.values()))
            self.after(0, self.update_schedule_dropdown)
        except Exception as e:
            print(e)
            update_status("Error")

    def update_dashboard(self, devices):
        for w in self.dev_list.winfo_children(): w.destroy()
        if not devices: ctk.CTkLabel(self.dev_list, text="No devices found.").pack(pady=20)
        for dev in devices: self.build_device_card(dev)

    def build_device_card(self, dev):
        try: mac = getattr(dev, 'mac', "Unknown")
        except: mac = "Unknown"
        try: serial = getattr(dev, 'serial_number', "Unknown")
        except: serial = "Unknown"
        
        card = ctk.CTkFrame(self.dev_list, fg_color="#1a1a1a")
        card.pack(fill="x", pady=5, padx=5)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(top, text="⚡", font=("Arial", 20)).pack(side="left", padx=(0,10))
        ctk.CTkLabel(top, text=f"{dev.name}", font=("Roboto", 16, "bold")).pack(side="left")
        def toggle(): threading.Thread(target=dev.toggle, daemon=True).start()
        switch = ctk.CTkSwitch(top, text="Power", command=toggle)
        switch.pack(side="right")
        try: 
            if dev.get_state(): switch.select()
        except: pass
        mid = ctk.CTkFrame(card, fg_color="transparent")
        mid.pack(fill="x", padx=10, pady=0)
        ctk.CTkLabel(mid, text=f"IP: {dev.host} | MAC: {mac} | SN: {serial}", font=("Consolas", 11), text_color="#aaa").pack(anchor="w")
        bot = ctk.CTkFrame(card, fg_color="transparent")
        bot.pack(fill="x", padx=10, pady=(5, 10))
        def rename_action():
            new_name = ctk.CTkInputDialog(text="Name:", title="Rename").get_input()
            if new_name: threading.Thread(target=self._rename_task, args=(dev, new_name), daemon=True).start()
        ctk.CTkButton(bot, text="✎ Rename", width=80, height=24, fg_color="#444", command=rename_action).pack(side="left", padx=(0, 10))
        def extract_hk(): threading.Thread(target=self._extract_hk_task, args=(dev,), daemon=True).start()
        ctk.CTkButton(bot, text="Get HomeKit Code", width=120, height=24, fg_color="#555", command=extract_hk).pack(side="left")

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
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["prov"] = frame
        frame.columnconfigure(0, weight=1) 
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)
        left_col = ctk.CTkFrame(frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(left_col, text="Step 1: Locate Device", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))
        scan_frame = ctk.CTkFrame(left_col, fg_color="#222")
        scan_frame.pack(fill="x", pady=(0, 20))
        self.btn_scan_setup = ctk.CTkButton(scan_frame, text="🔍 Scan Airwaves", command=self.scan_ssids)
        self.btn_scan_setup.pack(pady=10, padx=10, fill="x")
        self.ssid_list = ctk.CTkScrollableFrame(scan_frame, height=100, label_text="Nearby Networks")
        self.ssid_list.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkLabel(left_col, text="Step 2: Configuration", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))
        input_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        input_frame.pack(fill="x")
        prof_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        prof_row.pack(fill="x", pady=5)
        self.profile_combo = ctk.CTkComboBox(prof_row, values=["Select Saved Profile..."] + list(self.profiles.keys()), command=self.apply_profile, width=200)
        self.profile_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(prof_row, text="💾", width=40, command=self.save_current_profile).pack(side="left", padx=5)
        ctk.CTkButton(prof_row, text="🗑️", width=40, fg_color="#aa3333", hover_color="#882222", command=self.delete_profile).pack(side="left")
        self.name_entry = ctk.CTkEntry(input_frame, placeholder_text="Device Name (e.g. Office Fan)")
        self.name_entry.pack(fill="x", pady=5)
        self.ssid_entry = ctk.CTkEntry(input_frame, placeholder_text="SSID")
        self.ssid_entry.pack(fill="x", pady=5)
        self.pass_entry = ctk.CTkEntry(input_frame, placeholder_text="Password", show="*")
        self.pass_entry.pack(fill="x", pady=5)
        self.prov_btn = ctk.CTkButton(left_col, text="Push Configuration", fg_color="#28a745", hover_color="#1e7e34", height=50, state="disabled", command=self.run_provision_thread)
        self.prov_btn.pack(fill="x", pady=20)
        right_col = ctk.CTkFrame(frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")
        self.status_frame = ctk.CTkFrame(right_col, fg_color="#331111", border_color="#ff5555", border_width=2)
        self.status_frame.pack(fill="x", pady=(0, 10))
        self.status_lbl_icon = ctk.CTkLabel(self.status_frame, text="❌", font=("Arial", 30))
        self.status_lbl_icon.pack(side="left", padx=15, pady=15)
        stat_txt = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        stat_txt.pack(side="left", fill="x")
        self.status_lbl_text = ctk.CTkLabel(stat_txt, text="NOT CONNECTED", font=("Arial", 16, "bold"), text_color="#ff5555")
        self.status_lbl_text.pack(anchor="w")
        self.status_lbl_sub = ctk.CTkLabel(stat_txt, text="Connect Wi-Fi to 'Wemo.Mini.XXX'", font=("Arial", 12))
        self.status_lbl_sub.pack(anchor="w")
        self.override_link = ctk.CTkLabel(right_col, text="[Manual Override]", font=("Arial", 10, "underline"), text_color="gray", cursor="hand2")
        self.override_link.pack(anchor="e", pady=(0, 5))
        self.override_link.bind("<Button-1>", lambda e: self.force_unlock())
        ctk.CTkLabel(right_col, text="Live Operation Log", font=("Arial", 12)).pack(anchor="w")
        self.prov_log = ctk.CTkTextbox(right_col, font=("Consolas", 12), activate_scrollbars=True)
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

    # --- SCHEDULER (Shortened for brevity but functional) ---
    def create_schedule_ui(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["sched"] = frame
        loc_frame = ctk.CTkFrame(frame, fg_color="#222")
        loc_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(loc_frame, text="Solar Location:", font=("Arial", 12, "bold")).pack(side="left", padx=10)
        self.loc_lbl = ctk.CTkLabel(loc_frame, text="Detecting...", text_color="orange")
        self.loc_lbl.pack(side="left")
        ctk.CTkButton(loc_frame, text="Update Solar Data", width=120, fg_color="#444", command=self.update_solar_data).pack(side="right", padx=10, pady=5)
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
        self.sched_val_lbl = ctk.CTkLabel(r2, text="Time (HH:MM):")
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
            ctk.CTkCheckBox(day_frame, text=d, variable=v, width=40).pack(side="left", padx=2)
        ctk.CTkButton(r2, text="Create Job", width=100, fg_color="#28a745", command=self.add_job).pack(side="right", padx=10)
        ctk.CTkLabel(frame, text="Active Schedules", font=("Arial", 16, "bold")).pack(anchor="w", pady=(10,0))
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
        self.schedules.append(job)
        self.save_json(SCHEDULE_FILE, self.schedules)
        self.render_jobs()

    def render_jobs(self):
        for w in self.job_list_frame.winfo_children(): w.destroy()
        if not self.schedules: ctk.CTkLabel(self.job_list_frame, text="No schedules.").pack(); return
        days_map = ["M", "T", "W", "Th", "F", "Sa", "Su"]
        for job in self.schedules:
            row = ctk.CTkFrame(self.job_list_frame, fg_color="#333")
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
            ctk.CTkLabel(row, text=desc, font=("Consolas", 12)).pack(side="left", padx=10, pady=5)
            ctk.CTkButton(row, text="❌", width=30, fg_color="#c0392b", command=lambda j=job: self.delete_job(j["id"])).pack(side="right", padx=5)

    def delete_job(self, jid):
        self.schedules = [j for j in self.schedules if j["id"] != jid]
        self.save_json(SCHEDULE_FILE, self.schedules)
        self.render_jobs()

    def update_schedule_dropdown(self):
        names = list(self.known_devices_map.keys())
        if names: self.sched_dev_combo.configure(values=names); self.sched_dev_combo.set(names[0])

    def _scheduler_engine(self):
        while True:
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
        if dev_name in self.known_devices_map:
            dev = self.known_devices_map[dev_name]
            try:
                if job['action'] == "Turn ON": dev.on()
                elif job['action'] == "Turn OFF": dev.off()
                elif job['action'] == "Toggle": dev.toggle()
            except: pass

    # --- UTILS & SCANNER ---
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
        card = ctk.CTkFrame(self.ssid_list, fg_color="#333")
        card.pack(fill="x", pady=2, padx=5)
        ctk.CTkLabel(card, text=ssid, font=("Arial", 12, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(card, text="⬅ Connect Manually", text_color="#aaa", font=("Arial", 10)).pack(side="right", padx=10)

    def log_prov(self, msg):
        self.prov_log.insert("end", f"{msg}\n")
        self.prov_log.see("end")

    def _connection_monitor(self):
        target_ips = ["10.22.22.1", "192.168.49.1"]
        target_ports = [49153, 49152, 49154] 
        while self.monitoring:
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
        self.status_frame.configure(fg_color="#1a331a", border_color="#28a745")
        self.status_lbl_icon.configure(text="✅")
        self.status_lbl_text.configure(text="CONNECTED", text_color="#28a745")
        self.status_lbl_sub.configure(text=f"Found: {dev.name} ({ip}:{port})")
        self.prov_btn.configure(state="normal", text="Push Configuration")
        self.override_link.pack_forget()

    def set_status_disconnected(self):
        self.status_frame.configure(fg_color="#331111", border_color="#ff5555")
        self.status_lbl_icon.configure(text="❌")
        self.status_lbl_text.configure(text="NOT CONNECTED", text_color="#ff5555")
        self.status_lbl_sub.configure(text="Connect Wi-Fi to 'Wemo.Mini.XXX'", font=("Arial", 12))
        self.prov_btn.configure(state="disabled", text="Waiting for Connection...")
        self.override_link.pack(anchor="e", pady=(0, 5))

    def force_unlock(self):
        self.status_frame.configure(fg_color="#332200", border_color="#FFA500")
        self.status_lbl_icon.configure(text="⚠️")
        self.status_lbl_text.configure(text="MANUAL OVERRIDE", text_color="#FFA500")
        self.status_lbl_sub.configure(text="Forced Unlock. Assuming 10.22.22.1.")
        self.prov_btn.configure(state="normal", text="Push Configuration (Forced)")
        self.current_setup_ip = "10.22.22.1"
        self.log_prov("Manual Override engaged. Assuming IP 10.22.22.1.")

if __name__ == "__main__":
    app = WemoOpsApp()
    app.mainloop()