import os
import sys
import json
import time
import threading
import datetime
import socket
import logging
import ipaddress
import concurrent.futures
import requests
from flask import Flask, render_template_string, jsonify, request

# --- CONFIGURATION ---
VERSION = "v1.0.1-Tabs"
PORT = int(os.environ.get("PORT", 5000))
HOST = "0.0.0.0"
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", 300))

# --- PATH SETUP ---
if sys.platform == "win32":
    APP_DATA_DIR = os.path.join(os.getenv('APPDATA'), "WemoOps")
else:
    if os.geteuid() == 0:
        APP_DATA_DIR = "/var/lib/wemo-ops"
    else:
        APP_DATA_DIR = os.path.expanduser("~/.local/share/WemoOps")

if not os.path.exists(APP_DATA_DIR):
    try: os.makedirs(APP_DATA_DIR)
    except: pass

SCHEDULE_FILE = os.path.join(APP_DATA_DIR, "schedules.json")
SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WemoServer")
logging.getLogger("pywemo").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.WARNING)

app = Flask(__name__)

# --- GLOBAL STATE ---
known_devices = {}
scan_status = "Idle"
settings = {}
solar_times = {}

# --- UTILS ---
def load_json(path, default=None):
    if default is None: default = {}
    if os.path.exists(path):
        try:
            with open(path, 'r') as f: return json.load(f)
        except: pass
    return default

def save_json(path, data):
    try:
        with open(path, 'w') as f: json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")

def get_solar_times():
    global solar_times
    # Basic caching to avoid spamming the API
    if solar_times and solar_times.get('date') == datetime.date.today().isoformat():
        return solar_times
    
    lat = settings.get('lat')
    lng = settings.get('lng')
    
    # Auto-detect IP location if missing
    if not lat: 
        try:
            r = requests.get("https://ipinfo.io/json", timeout=2)
            loc = r.json().get("loc", "").split(",")
            lat, lng = loc[0], loc[1]
            settings['lat'] = lat; settings['lng'] = lng
            save_json(SETTINGS_FILE, settings)
        except: return None
        
    try:
        # Use sunrise-sunset.org API
        url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&formatted=0"
        r = requests.get(url, timeout=5)
        res = r.json()["results"]
        
        def to_local(utc_str):
            dt_utc = datetime.datetime.fromisoformat(utc_str)
            return dt_utc.astimezone().strftime("%H:%M")

        solar_times = {
            "date": datetime.date.today().isoformat(),
            "sunrise": to_local(res["sunrise"]),
            "sunset": to_local(res["sunset"])
        }
        return solar_times
    except: return None

# --- DEEP SCANNER ---
class DeepScanner:
    def probe_port(self, ip, port=49153, timeout=0.2):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((str(ip), port))
                return str(ip)
        except: return None

    def scan_subnet(self, subnets):
        import pywemo
        found_ips = []
        all_hosts = []
        for subnet in subnets:
            try:
                if "/" not in subnet: subnet += "/24"
                net = ipaddress.ip_network(subnet.strip(), strict=False)
                all_hosts.extend([str(ip) for ip in net.hosts()])
            except: pass

        if not all_hosts: return []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(self.probe_port, ip): ip for ip in all_hosts}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result: found_ips.append(result)

        devices = []
        for ip in found_ips:
            try:
                for port in [49153, 49152, 49154]:
                    url = f"http://{ip}:{port}/setup.xml"
                    try:
                        dev = pywemo.discovery.device_from_description(url)
                        if dev: devices.append(dev); break
                    except: pass
            except: pass
        return devices

# --- BACKGROUND TASKS ---
def scanner_loop():
    global scan_status
    import pywemo
    ds = DeepScanner()
    while True:
        try:
            scan_status = "Scanning (SSDP)..."
            devices = pywemo.discover_devices()
            for dev in devices: known_devices[dev.name] = dev
            
            subs = settings.get("subnets", [])
            if subs:
                scan_status = f"Deep Scanning..."
                deep_devs = ds.scan_subnet(subs)
                for dev in deep_devs: known_devices[dev.name] = dev
            
            scan_status = "Idle"
            logger.info(f"Scan Complete. Devices found: {len(known_devices)}")
        except Exception as e:
            logger.error(f"Scan error: {e}")
            scan_status = "Error"
        time.sleep(SCAN_INTERVAL)

def scheduler_loop():
    while True:
        try:
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            weekday = now.weekday()
            current_hhmm = now.strftime("%H:%M")
            solar = get_solar_times()
            
            current_schedules = load_json(SCHEDULE_FILE, [])
            
            for job in current_schedules:
                if weekday not in job.get('days', []): continue
                trigger_time = ""
                if job['type'] == "Time (Fixed)":
                    trigger_time = job['value']
                elif solar:
                    base = solar['sunrise'] if job['type'] == "Sunrise" else solar['sunset']
                    try:
                        dt = datetime.datetime.strptime(f"{today_str} {base}", "%Y-%m-%d %H:%M")
                        offset = int(job['value']) * int(job.get('offset_dir', 1))
                        trigger_time = (dt + datetime.timedelta(minutes=offset)).strftime("%H:%M")
                    except: continue
                
                if trigger_time == current_hhmm and job.get('last_run') != today_str:
                    logger.info(f"Executing Job: {job['action']} -> {job['device']}")
                    dev = known_devices.get(job['device'])
                    if dev:
                        try:
                            if job['action'] == "Turn ON": dev.on()
                            elif job['action'] == "Turn OFF": dev.off()
                            elif job['action'] == "Toggle": dev.toggle()
                        except: pass
                    job['last_run'] = today_str
                    save_json(SCHEDULE_FILE, current_schedules)
        except Exception as e: logger.error(f"Scheduler error: {e}")
        time.sleep(30)

# --- ROUTES ---
@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE, version=VERSION)

@app.route('/api/status')
def api_status():
    return jsonify({"scan_status": scan_status, "device_count": len(known_devices)})

@app.route('/api/devices')
def api_devices():
    devs_out = []
    for name, dev in known_devices.items():
        try: state = dev.get_state()
        except: state = 0
        devs_out.append({"name": name, "ip": dev.host, "state": state})
    return jsonify(devs_out)

@app.route('/api/toggle/<name>', methods=['POST'])
def api_toggle(name):
    dev = known_devices.get(name)
    if dev:
        dev.toggle()
        return jsonify({"status": "ok"})
    return jsonify({"status": "not found"}), 404

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    global settings
    if request.method == 'GET': return jsonify(settings)
    if request.method == 'POST':
        settings.update(request.json)
        save_json(SETTINGS_FILE, settings)
        return jsonify({"status": "saved"})

@app.route('/api/scan', methods=['POST'])
def api_scan():
    global scan_status
    if "Scanning" in scan_status: return jsonify({"status": "busy"})
    scan_status = "Starting..."
    threading.Thread(target=scanner_loop, daemon=True).start()
    return jsonify({"status": "started"})

@app.route('/api/schedules', methods=['GET', 'POST', 'DELETE'])
def api_schedules():
    current = load_json(SCHEDULE_FILE, [])
    if request.method == 'GET': return jsonify(current)
    if request.method == 'POST':
        data = request.json
        data['id'] = int(time.time())
        data['last_run'] = ""
        current.append(data)
        save_json(SCHEDULE_FILE, current)
        return jsonify({"status": "added", "id": data['id']})
    if request.method == 'DELETE':
        jid = int(request.args.get('id'))
        new_list = [x for x in current if x['id'] != jid]
        save_json(SCHEDULE_FILE, new_list)
        return jsonify({"status": "deleted"})
        
@app.route('/api/solar')
def api_solar():
    return jsonify(get_solar_times() or {})

# --- FRONTEND ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wemo Ops Web</title>
    <style>
        :root { --bg: #1a1a1a; --card: #2b2b2b; --text: #ffffff; --accent: #1f6aa5; --green: #28a745; --danger: #c0392b; }
        body { background-color: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }
        
        /* NAVBAR */
        .navbar { background: #111; padding: 15px 20px; border-bottom: 2px solid #333; display: flex; align-items: center; justify-content: space-between; }
        .nav-links button { background: none; border: none; color: #aaa; font-size: 1.1em; margin-left: 20px; cursor: pointer; padding: 5px 10px; border-radius: 4px; }
        .nav-links button:hover { color: white; background: #333; }
        .nav-links button.active { color: white; background: var(--accent); }
        .brand { font-weight: bold; font-size: 1.2em; }

        .container { max-width: 900px; margin: 20px auto; padding: 0 15px; }
        .card { background: var(--card); padding: 15px; margin-bottom: 15px; border-radius: 8px; border: 1px solid #333; }
        .flex { display: flex; justify-content: space-between; align-items: center; }
        
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; color: white; font-weight: bold; }
        .btn-toggle { background-color: #555; width: 80px; }
        .btn-toggle.on { background-color: var(--green); }
        .btn-primary { background-color: var(--accent); }
        .btn-danger { background-color: var(--danger); }
        
        input, select { padding: 8px; background: #333; color: white; border: 1px solid #555; border-radius: 4px; }
        .row { display: flex; gap: 10px; margin-top: 10px; align-items: center; }
        .badge { background: #444; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; font-family: monospace; }
        
        /* TABS */
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        #scan-status { font-size: 0.9em; color: #f39c12; margin-right: 15px; }
        .solar-info { font-size: 0.9em; color: gray; margin-bottom: 10px; }
    </style>
</head>
<body>

    <nav class="navbar">
        <div class="brand">Wemo Ops <small style="color:gray; font-size:0.6em;">{{ version }}</small></div>
        <div class="nav-links">
            <span id="scan-status">Idle</span>
            <button class="nav-btn active" onclick="showTab('dashboard')">Dashboard</button>
            <button class="nav-btn" onclick="showTab('automation')">Automation</button>
            <button class="nav-btn" onclick="showTab('settings')">Settings</button>
        </div>
    </nav>

    <div class="container">
        
        <div id="dashboard" class="tab-content active">
            <div class="flex" style="margin-bottom:15px;">
                <h2>My Devices</h2>
                <button class="btn btn-primary" onclick="triggerScan()">Refresh / Scan</button>
            </div>
            <div id="device-list">Loading...</div>
        </div>

        <div id="automation" class="tab-content">
            <h2>Automation Rules</h2>
            <div class="card">
                <h3>Create New Schedule</h3>
                <div class="solar-info" id="solar-data">Loading solar times...</div>
                
                <div class="row">
                    <select id="s-dev" style="flex:2"></select>
                    <select id="s-action" style="flex:1"><option>Turn ON</option><option>Turn OFF</option><option>Toggle</option></select>
                </div>
                
                <div class="row">
                    <select id="s-type" style="flex:1" onchange="toggleType()">
                        <option>Time (Fixed)</option><option>Sunrise</option><option>Sunset</option>
                    </select>
                    <input type="text" id="s-val" placeholder="HH:MM" style="width: 100px;">
                    <select id="s-off" style="display:none; width:60px;"><option value="1">+</option><option value="-1">-</option></select>
                </div>

                <div class="row" style="justify-content:space-between; margin-top:15px;">
                    <div style="color:#ddd;">
                        <label><input type="checkbox" class="day" value="0" checked> Mon</label>
                        <label><input type="checkbox" class="day" value="1" checked> Tue</label>
                        <label><input type="checkbox" class="day" value="2" checked> Wed</label>
                        <label><input type="checkbox" class="day" value="3" checked> Thu</label>
                        <label><input type="checkbox" class="day" value="4" checked> Fri</label>
                        <label><input type="checkbox" class="day" value="5" checked> Sat</label>
                        <label><input type="checkbox" class="day" value="6" checked> Sun</label>
                    </div>
                    <button class="btn btn-primary" onclick="addSchedule()">+ Add Rule</button>
                </div>
            </div>
            
            <h3>Active Schedules</h3>
            <div id="sched-list"></div>
        </div>

        <div id="settings" class="tab-content">
            <h2>Server Settings</h2>
            <div class="card">
                <h3>Network Configuration</h3>
                <p>Enter subnets to scan (comma separated).</p>
                <input type="text" id="subnets" placeholder="192.168.1.0/24">
                <br><br>
                <button class="btn btn-primary" onclick="saveSettings()">Save Configuration</button>
            </div>
        </div>

    </div>

    <script>
        // --- TABS LOGIC ---
        function showTab(id) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.target.classList.add('active');
        }

        // --- DASHBOARD ---
        function fetchDevices() {
            fetch('/api/devices').then(r => r.json()).then(data => {
                const list = document.getElementById('device-list');
                const sel = document.getElementById('s-dev');
                
                // Only redraw list if we are on dashboard to save resources? No, redraw always for state updates.
                list.innerHTML = ''; 
                sel.innerHTML = '';
                
                if(data.length === 0) list.innerHTML = '<div style="color:gray; padding:20px; text-align:center;">No devices found. Check Settings tab.</div>';

                data.forEach(d => {
                    // Dropdown population
                    let opt = document.createElement('option');
                    opt.value = d.name; opt.innerText = d.name;
                    sel.appendChild(opt);

                    // Dashboard Card
                    let div = document.createElement('div');
                    div.className = 'card flex';
                    div.innerHTML = `<div><strong style="font-size:1.1em">${d.name}</strong><br><small style='color:gray'>${d.ip}</small></div>
                                     <button class="btn btn-toggle ${d.state ? 'on' : ''}" onclick="toggle('${d.name}')">
                                     ${d.state ? 'ON' : 'OFF'}</button>`;
                    list.appendChild(div);
                });
            });
        }

        function toggle(name) {
            fetch('/api/toggle/'+name, {method:'POST'}).then(() => fetchDevices());
        }

        function triggerScan() {
            fetch('/api/scan', {method:'POST'});
            alert('Scan started in background.');
        }

        function fetchStatus() {
            fetch('/api/status').then(r=>r.json()).then(d => {
                document.getElementById('scan-status').innerText = d.scan_status;
            });
        }

        // --- AUTOMATION ---
        function fetchSolar() {
            fetch('/api/solar').then(r=>r.json()).then(d => {
                if(d.sunrise) document.getElementById('solar-data').innerText = `Today's Solar Data: Sunrise ${d.sunrise} | Sunset ${d.sunset}`;
            });
        }

        function toggleType() {
            let t = document.getElementById('s-type').value;
            let isSolar = t !== "Time (Fixed)";
            document.getElementById('s-off').style.display = isSolar ? 'block' : 'none';
            document.getElementById('s-val').placeholder = isSolar ? "Offset (min)" : "HH:MM";
            document.getElementById('s-val').value = isSolar ? "0" : "";
        }

        function fetchSched() {
            fetch('/api/schedules').then(r => r.json()).then(data => {
                const list = document.getElementById('sched-list');
                list.innerHTML = '';
                const daysMap = ['M','T','W','Th','F','Sa','Su'];
                
                if(data.length === 0) list.innerHTML = '<div style="color:gray; padding:20px;">No active schedules.</div>';

                data.forEach(s => {
                    let dStr = s.days.length === 7 ? "Daily" : s.days.map(i => daysMap[i]).join('');
                    let timeStr = s.type === "Time (Fixed)" ? "@ " + s.value : `${s.type} ${s.value > 0 ? '+' : ''}${s.value}m`;
                    
                    let div = document.createElement('div');
                    div.className = 'card flex';
                    div.innerHTML = `<div><span class="badge">${dStr}</span> <strong>${timeStr}</strong> ➔ ${s.action} <span style="color:var(--accent)">${s.device}</span></div>
                                     <button class="btn btn-danger" onclick="delSched(${s.id})">Delete</button>`;
                    list.appendChild(div);
                });
            });
        }

        function addSchedule() {
            let days = [];
            document.querySelectorAll('.day:checked').forEach(c => days.push(parseInt(c.value)));
            if(days.length === 0) { alert('Select at least one day'); return; }
            
            let payload = {
                device: document.getElementById('s-dev').value,
                action: document.getElementById('s-action').value,
                type: document.getElementById('s-type').value,
                value: document.getElementById('s-val').value,
                offset_dir: parseInt(document.getElementById('s-off').value),
                days: days
            };
            fetch('/api/schedules', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(() => { fetchSched(); alert('Schedule Added'); });
        }

        function delSched(id) {
            if(confirm('Delete this schedule?')) {
                fetch('/api/schedules?id='+id, {method:'DELETE'}).then(() => fetchSched());
            }
        }

        // --- SETTINGS ---
        function loadSettings() {
            fetch('/api/settings').then(r=>r.json()).then(d => {
                if(d.subnets) document.getElementById('subnets').value = d.subnets.join(', ');
            });
        }
        function saveSettings() {
            let txt = document.getElementById('subnets').value;
            let subs = txt.split(',').map(s => s.trim()).filter(s => s.length > 0);
            fetch('/api/settings', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({subnets: subs})
            }).then(() => alert('Settings Saved!'));
        }

        // --- INIT ---
        loadSettings();
        fetchDevices();
        fetchSched();
        fetchSolar();
        
        setInterval(fetchStatus, 2000);
        setInterval(fetchDevices, 5000); // Live update status
    </script>
</body>
</html>
"""

# --- STARTUP ---
settings = load_json(SETTINGS_FILE, {})

def _start_background():
    threading.Thread(target=scanner_loop, daemon=True).start()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    logger.info("Background threads started (scanner, scheduler)")

# Gunicorn (Docker) — __main__ is never reached, so start threads at import time
if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
    _start_background()

# Flask dev server (native install)
if __name__ == "__main__":
    _start_background()
    app.run(host=HOST, port=PORT, debug=False)