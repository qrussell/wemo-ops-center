import pywemo
import time
import json
import os
import datetime
import requests
import sys
import fcntl  # macOS file locking

# --- CONFIGURATION ---
VERSION = "v4.0-Mac-Service"
LOCK_FILE_NAME = "wemo_service.lock"

# --- PATH SETUP (macOS) ---
APP_DATA_DIR = os.path.expanduser("~/Library/Application Support/WemoOps")

if not os.path.exists(APP_DATA_DIR):
    try: os.makedirs(APP_DATA_DIR)
    except: pass

SCHEDULE_FILE = os.path.join(APP_DATA_DIR, "schedules.json")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")
LOCK_FILE_PATH = os.path.join(APP_DATA_DIR, LOCK_FILE_NAME)

# --- UTILS ---
def load_json(path, default_type=dict):
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
                if isinstance(data, default_type): return data
        except: pass
    return default_type()

def save_json(path, data):
    try:
        with open(path, 'w') as f: json.dump(data, f)
    except: pass

class SolarEngine:
    def __init__(self):
        self.lat = None
        self.lng = None
        self.solar_times = {}
        self.last_fetch = None
        
        settings = load_json(SETTINGS_FILE, dict)
        if "lat" in settings:
            self.lat = settings["lat"]
            self.lng = settings["lng"]

    def get_solar_times(self):
        today = datetime.date.today()
        if self.last_fetch == today and self.solar_times: return self.solar_times
        if not self.lat: return None

        try:
            url = f"https://api.sunrise-sunset.org/json?lat={self.lat}&lng={self.lng}&formatted=0"
            r = requests.get(url, timeout=10)
            data = r.json()
            if data["status"] == "OK":
                res = data["results"]
                
                # --- TIMEZONE FIX ---
                def to_local(utc_str):
                    try:
                        dt_utc = datetime.datetime.fromisoformat(utc_str)
                        # Mac astimezone() fix
                        dt_local = dt_utc.astimezone()
                        return dt_local.strftime("%H:%M")
                    except: return "00:00"
                # --------------------

                self.solar_times = {
                    "sunrise": to_local(res["sunrise"]),
                    "sunset": to_local(res["sunset"])
                }
                self.last_fetch = today
                return self.solar_times
        except: pass
        return None

# --- SINGLE INSTANCE LOCK (MACOS) ---
def acquire_lock():
    global lock_file
    lock_file = open(LOCK_FILE_PATH, 'w')
    try:
        # Try to acquire an exclusive lock on the file
        # LOCK_EX = Exclusive Lock, LOCK_NB = Non-Blocking (fail immediately)
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except IOError:
        return False

# --- SERVICE LOOP ---
def run_service():
    if not acquire_lock():
        print("Another instance is running. Quitting.")
        sys.exit(0)

    print(f"Wemo Ops Service {VERSION} Started...")
    solar = SolarEngine()
    known_devices = {}

    # Initial Scan
    try:
        devices = pywemo.discover_devices()
        for d in devices: known_devices[d.name] = d
    except: pass

    while True:
        try:
            schedules = load_json(SCHEDULE_FILE, list)
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            weekday = now.weekday()
            current_hhmm = now.strftime("%H:%M")
            solar_data = solar.get_solar_times()

            for job in schedules:
                if weekday not in job['days']: continue
                
                trigger_time = ""
                if job['type'] == "Time (Fixed)":
                    trigger_time = job['value']
                elif solar_data:
                    base_str = solar_data['sunrise'] if job['type'] == "Sunrise" else solar_data['sunset']
                    try:
                        dt = datetime.datetime.strptime(f"{today_str} {base_str}", "%Y-%m-%d %H:%M")
                        offset_mins = int(job['value']) * job['offset_dir']
                        trigger_dt = dt + datetime.timedelta(minutes=offset_mins)
                        trigger_time = trigger_dt.strftime("%H:%M")
                    except: continue

                if trigger_time == current_hhmm and job.get('last_run') != today_str:
                    
                    if job['device'] not in known_devices:
                        try:
                            devs = pywemo.discover_devices()
                            for d in devs: known_devices[d.name] = d
                        except: pass

                    if job['device'] in known_devices:
                        dev = known_devices[job['device']]
                        try:
                            if job['action'] == "Turn ON": dev.on()
                            elif job['action'] == "Turn OFF": dev.off()
                            elif job['action'] == "Toggle": dev.toggle()
                            
                            job['last_run'] = today_str
                            save_json(SCHEDULE_FILE, schedules)
                        except: pass
        except: pass
        
        time.sleep(30)

if __name__ == "__main__":
    run_service()