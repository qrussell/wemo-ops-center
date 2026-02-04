import time
import json
import os
import sys
import datetime
import requests
import pywemo
import threading
import logging
from PIL import Image
import pystray

# --- CONFIGURATION ---
VERSION = "v4.1.0 (Tray Service)"

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

SCHEDULE_FILE = os.path.join(APP_DATA_DIR, "schedules.json")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")
LOG_FILE = os.path.join(APP_DATA_DIR, "service.log")

# --- LOGGING ---
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- SOLAR ENGINE ---
class SolarEngine:
    def __init__(self):
        self.lat = None
        self.lng = None
        self.solar_times = {} 
        self.last_fetch = None

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.lat = data.get("lat")
                    self.lng = data.get("lng")
            except: pass

    def get_solar_times(self):
        today = datetime.date.today()
        if self.last_fetch == today and self.solar_times: return self.solar_times
        self.load_settings()
        if not self.lat: return None

        try:
            url = f"https://api.sunrise-sunset.org/json?lat={self.lat}&lng={self.lng}&formatted=0"
            r = requests.get(url, timeout=10)
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

# --- SERVICE RUNNER ---
class WemoService:
    def __init__(self):
        self.known_devices = {}
        self.solar = SolarEngine()
        self.running = True
        logging.info(f"--- Wemo Service {VERSION} Started ---")

    def discover_devices(self):
        try:
            devices = pywemo.discover_devices()
            for d in devices: self.known_devices[d.name] = d
        except: pass

    def load_schedules(self):
        if os.path.exists(SCHEDULE_FILE):
            try:
                with open(SCHEDULE_FILE, 'r') as f: return json.load(f)
            except: pass
        return []

    def save_schedules(self, data):
        try:
            with open(SCHEDULE_FILE, 'w') as f: json.dump(data, f)
        except: pass

    def execute_job(self, job):
        dev_name = job['device']
        if dev_name in self.known_devices:
            dev = self.known_devices[dev_name]
            action = job['action']
            try:
                logging.info(f"EXECUTE: {action} -> {dev_name}")
                if action == "Turn ON": dev.on()
                elif action == "Turn OFF": dev.off()
                elif action == "Toggle": dev.toggle()
            except Exception as e:
                logging.error(f"Execution Failed: {e}")

    def loop(self):
        # Initial Discovery
        self.discover_devices()
        last_discovery = time.time()
        
        while self.running:
            try:
                if time.time() - last_discovery > 900:
                    self.discover_devices()
                    last_discovery = time.time()

                schedules = self.load_schedules()
                if not schedules:
                    time.sleep(30); continue

                now = datetime.datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                weekday = now.weekday()
                current_hhmm = now.strftime("%H:%M")
                solar_data = self.solar.get_solar_times()
                schedule_updated = False
                
                for job in schedules:
                    if weekday not in job['days']: continue
                    trigger_time = ""
                    if job['type'] == "Time (Fixed)": trigger_time = job['value']
                    elif solar_data:
                        base_str = solar_data['sunrise'] if job['type'] == "Sunrise" else solar_data['sunset']
                        try:
                            dt_base = datetime.datetime.strptime(f"{today_str} {base_str}", "%Y-%m-%d %H:%M")
                            offset_mins = int(job['value']) * job['offset_dir']
                            trigger_dt = dt_base + datetime.timedelta(minutes=offset_mins)
                            trigger_time = trigger_dt.strftime("%H:%M")
                        except: continue

                    if trigger_time == current_hhmm and job.get('last_run') != today_str:
                        self.execute_job(job)
                        job['last_run'] = today_str
                        schedule_updated = True
                
                if schedule_updated: self.save_schedules(schedules)

            except Exception as e: logging.error(f"Loop Error: {e}")
            
            # Check stop flag frequently
            for _ in range(30):
                if not self.running: break
                time.sleep(1)

    def stop(self):
        self.running = False

# --- TRAY ICON SETUP ---
def run_tray():
    service = WemoService()
    
    # Start automation loop in background thread
    t = threading.Thread(target=service.loop)
    t.daemon = True
    t.start()

    def on_exit(icon, item):
        service.stop()
        icon.stop()

    # Load Icon
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, "icon.ico")
    else:
        icon_path = "icon.ico"
    
    try:
        image = Image.open(icon_path)
    except:
        # Fallback: Create a simple colored block if icon missing
        image = Image.new('RGB', (64, 64), color = (73, 109, 137))

    menu = pystray.Menu(
        pystray.MenuItem("Wemo Ops Service (Running)", lambda: None, enabled=False),
        pystray.MenuItem("Exit", on_exit)
    )

    icon = pystray.Icon("WemoOps", image, "Wemo Ops Service", menu)
    icon.run()

if __name__ == "__main__":
    run_tray()