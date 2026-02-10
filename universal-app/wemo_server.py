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
from waitress import serve

# --- CONFIGURATION ---
VERSION = "v5.2.3"
PORT = int(os.environ.get("PORT", 5050)) # Custom port option, mainly for Docker at this time.
HOST = "0.0.0.0"
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", 300)) # Time in seconds between automatic scans (default 5 minutes). Mainly for Docker at this time.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

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
DEVICES_FILE = os.path.join(APP_DATA_DIR, "devices.json")

# --- LOGGING ---
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(APP_DATA_DIR, "server.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WemoServer")

class ScanNoiseFilter(logging.Filter):
    """Filter out expected connection errors during subnet device scanning."""
    NOISE = ("Failed to fetch description", "Failed to parse description")
    def filter(self, record):
        msg = record.getMessage()
        return not any(n in msg for n in self.NOISE)

for handler in logging.root.handlers:
    handler.addFilter(ScanNoiseFilter())

app = Flask(__name__)

# --- GLOBAL STATE ---
device_registry = {}
scan_status = "Idle"
scan_event = threading.Event()
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

def save_device_cache():
    cache_data = {}
    for name, data in device_registry.items():
        cache_data[name] = {
            "ip": data.get("ip"),
            "mac": data.get("mac"),
            "serial": data.get("serial"),
            "state": data.get("state", 0),
            "last_seen": data.get("last_seen", 0)
        }
    save_json(DEVICES_FILE, cache_data)

def load_device_cache():
    global device_registry
    cache = load_json(DEVICES_FILE, {})
    for name, data in cache.items():
        device_registry[name] = {
            "obj": None,
            "ip": data.get("ip"),
            "mac": data.get("mac"),
            "serial": data.get("serial"),
            "state": data.get("state", 0),
            "last_seen": data.get("last_seen", 0)
        }

def get_solar_times():
    global solar_times
    if solar_times and solar_times.get('date') == datetime.date.today().isoformat():
        return solar_times
    
    lat = settings.get('lat')
    lng = settings.get('lng')
    
    if not lat: 
        try:
            r = requests.get("https://ipinfo.io/json", timeout=2)
            loc = r.json().get("loc", "").split(",")
            lat, lng = loc[0], loc[1]
            settings['lat'] = lat; settings['lng'] = lng
            save_json(SETTINGS_FILE, settings)
        except: return None
        
    try:
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
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
            futures = {executor.submit(self.probe_port, ip): ip for ip in all_hosts}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result: found_ips.append(result)

        devices = []
        for ip in found_ips:
            for port in [49152, 49153, 49154, 49155]:
                try:
                    url = f"http://{ip}:{port}/setup.xml"
                    try:
                        dev = pywemo.discovery.device_from_description(url)
                        if dev: 
                            devices.append(dev)
                            break
                    except: pass
                except: pass
        return devices

# --- BACKGROUND TASKS ---
def register_device(dev):
    global device_registry
    try:
        mac = getattr(dev, 'mac', 'Unknown')
        serial = getattr(dev, 'serial_number', 'Unknown')
        device_registry[dev.name] = {
            "obj": dev,
            "ip": dev.host,
            "mac": mac,
            "serial": serial,
            "state": 0,
            "last_seen": time.time()
        }
    except Exception as e:
        logger.error(f"Error registering device {dev}: {e}")

def scanner_loop():
    global scan_status
    import pywemo
    ds = DeepScanner()
    load_device_cache()
    
    while True:
        try:
            logger.info("Scan started")
            scan_status = "Scanning..."
            devices = pywemo.discover_devices()
            for dev in devices: register_device(dev)
            
            subs = settings.get("subnets", [])
            if subs:
                scan_status = f"Deep Scanning..."
                deep_devs = ds.scan_subnet(subs)
                for dev in deep_devs: register_device(dev)
            
            now = time.time()
            to_remove = [n for n, d in device_registry.items() if (now - d.get("last_seen", 0)) > 900]
            for name in to_remove: del device_registry[name]

            save_device_cache()
            scan_status = "Idle"
            logger.info(f"Scan complete — {len(device_registry)} devices, next in {SCAN_INTERVAL}s")

        except Exception:
            scan_status = "Error"

        scan_event.wait(timeout=SCAN_INTERVAL)
        scan_event.clear()

def poller_loop():
    """Polls devices for status updates."""
    while True:
        keys = list(device_registry.keys())
        for name in keys:
            entry = device_registry[name]
            dev = entry.get("obj")
            if dev:
                try:
                    # [FIX] Force update to see external changes (Desktop App / Physical)
                    state = dev.get_state(force_update=True)
                    entry['state'] = state
                    entry['last_seen'] = time.time()
                except: pass
            else:
                ip = entry.get("ip")
                if ip:
                    for p in [49153, 49152, 49154, 49155]:
                        try:
                            url = f"http://{ip}:{p}/setup.xml"
                            import pywemo
                            new_dev = pywemo.discovery.device_from_description(url)
                            if new_dev: 
                                register_device(new_dev)
                                break
                        except: pass
        time.sleep(2)

def scheduler_loop():
    while True:
        try:
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            weekday = now.weekday()
            current_hhmm = now.strftime("%H:%M")
            solar = get_solar_times()
            
            current_schedules = load_json(SCHEDULE_FILE, [])
            schedule_modified = False

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
                    entry = device_registry.get(job['device'])
                    if entry and entry.get("obj"):
                        dev = entry["obj"]
                        try:
                            if job['action'] == "Turn ON": dev.on()
                            elif job['action'] == "Turn OFF": dev.off()
                            elif job['action'] == "Toggle": dev.toggle()
                            # Immediate state update after action
                            entry['state'] = dev.get_state(force_update=True)
                        except: pass
                    job['last_run'] = today_str
                    schedule_modified = True
            
            if schedule_modified:
                save_json(SCHEDULE_FILE, current_schedules)

        except Exception as e: logger.error(f"Scheduler error: {e}")
        time.sleep(30)

# --- ROUTES ---
@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE, version=VERSION)

@app.route('/api/status')
def api_status():
    return jsonify({
        "status": "online",
        "scan_status": scan_status, 
        "device_count": len(device_registry),
        "version": VERSION,
        "threads": threading.active_count() # Simple thread count for basic monitoring.
    })

@app.route('/api/devices')
def api_devices():
    devs_out = []
    for name, data in device_registry.items():
        devs_out.append({
            "name": name, 
            "ip": data.get("ip"), 
            "state": data.get("state", 0),
            "mac": data.get("mac"),
            "serial": data.get("serial")
        })
    return jsonify(devs_out)

@app.route('/api/toggle/<name>', methods=['POST'])
def api_toggle(name):
    entry = device_registry.get(name)
    if entry and entry.get("obj"):
        dev = entry["obj"]
        def toggle_task():
            try: 
                dev.toggle()
                entry['state'] = dev.get_state(force_update=True)
            except: pass
        threading.Thread(target=toggle_task).start()
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
    if "Scanning" in scan_status: return jsonify({"status": "busy"})
    scan_event.set()
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

# --- FRONTEND ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Wemo Ops</title>
    <style>
        :root { 
            --bg: #121212; --card: #1e1e1e; --text: #e0e0e0; --subtext: #a0a0a0; --border: #333;
            --accent: #3b82f6; --green: #10b981; --danger: #ef4444; 
        }
        :root.light {
            --bg: #f3f4f6; --card: #ffffff; --text: #1f2937; --subtext: #6b7280; --border: #e5e7eb;
        }
        
        body { background-color: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding-bottom: 90px; transition: background 0.3s; }
        
        .app-bar { background: #000; padding: 15px 20px; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
        .brand { font-weight: 800; font-size: 1.4rem; background: linear-gradient(to right, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .container { max-width: 1200px; margin: 0 auto; padding: 15px; }
        
        .device-grid { display: grid; grid-template-columns: 1fr; gap: 15px; }
        @media (min-width: 768px) {
            .device-grid { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
            .container { padding-top: 30px; }
        }

        .card { background: var(--card); padding: 15px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: transform 0.1s; }
        .flex { display: flex; justify-content: space-between; align-items: center; }
        
        .btn { padding: 10px 18px; border: none; border-radius: 8px; cursor: pointer; color: white; font-weight: 600; font-size: 0.9rem; }
        .btn-toggle { background-color: #374151; width: 80px; height: 40px; transition: background 0.2s; }
        .btn-toggle.on { background-color: var(--green); }
        .btn-primary { background-color: var(--accent); width: 100%; margin-top: 10px; }
        .btn-danger { background-color: var(--danger); }
        
        input, select { background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 12px; border-radius: 8px; width: 100%; box-sizing: border-box; margin-bottom: 10px; font-size: 1rem; }
        
        .bottom-nav { position: fixed; bottom: 0; width: 100%; background: #000; display: flex; justify-content: space-around; padding: 15px 0; z-index: 100; border-top: 1px solid #333; box-shadow: 0 -2px 10px rgba(0,0,0,0.3); }
        .nav-item { color: #6b7280; font-size: 0.9rem; text-align: center; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 4px; width: 33%; }
        .nav-item span { font-size: 1.5rem; }
        .nav-item.active { color: var(--accent); }
        
        .view { display: none; }
        .view.active { display: block; animation: fadein 0.2s; }
        @keyframes fadein { from { opacity: 0; } to { opacity: 1; } }
        
        .status-badge { font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: #333; color: #aaa; }
    </style>
</head>
<body>
    <div class="app-bar">
        <div class="brand">WEMO OPS</div>
        <div style="display:flex; gap:10px; align-items:center;">
            <span id="scan-status" class="status-badge">Idle</span>
            <span style="cursor:pointer; font-size:1.2rem;" onclick="toggleTheme()">🌗</span>
        </div>
    </div>

    <div class="container">
        <div id="view-dash" class="view active">
            <div style="display:flex; justify-content:space-between; margin-bottom:15px; align-items:center;">
                <h2 style="margin:0;">Dashboard</h2>
                <button class="btn" style="background:var(--card); border:1px solid var(--border); color:var(--text);" onclick="triggerScan()">📡 Scan</button>
            </div>
            <div id="device-list" class="device-grid">
                <div style="text-align:center; padding:40px; opacity:0.6; grid-column:1/-1;">Connecting...</div>
            </div>
        </div>
        
        <div id="view-auto" class="view">
            <h2>Automation</h2>
            <div class="card">
                <h3>New Rule</h3>
                <select id="s-dev"></select>
                <div style="display:flex; gap:10px;">
                    <select id="s-action"><option>Turn ON</option><option>Turn OFF</option><option>Toggle</option></select>
                    <select id="s-type"><option>Time (Fixed)</option><option>Sunrise</option><option>Sunset</option></select>
                </div>
                <input type="text" id="s-val" placeholder="HH:MM (e.g. 18:30) or Offset (e.g. -30)">
                <button class="btn btn-primary" onclick="addSchedule()">+ Add Schedule</button>
            </div>
            <h3 style="margin-top:20px;">Active Schedules</h3>
            <div id="sched-list" class="device-grid"></div>
        </div>

        <div id="view-set" class="view">
            <h2>Settings</h2>
            <div class="card">
                <h3>Network Configuration</h3>
                <label style="font-size:0.9rem; color:var(--subtext); display:block; margin-bottom:5px;">Managed Subnets</label>
                
                <div style="display:flex; gap:10px; margin-bottom:10px;">
                    <select id="subnet-select" onchange="selectSubnet()" style="flex:1; margin-bottom:0;"></select>
                    <button class="btn btn-danger" style="width:auto; padding:10px 15px;" onclick="deleteSubnet()">🗑️</button>
                </div>
                
                <div style="display:flex; gap:10px;">
                    <input type="text" id="subnet-input" placeholder="192.168.1.0/24" style="flex:1; margin:0;">
                    <button class="btn btn-primary" style="width:auto; margin:0;" onclick="saveSubnet()">💾 Save</button>
                </div>
            </div>
            
            <div style="text-align:center; margin-top:30px; color:var(--subtext);">
                {{ version }}<br>Server Online
            </div>
        </div>
    </div>

    <div class="bottom-nav">
        <div class="nav-item active" onclick="nav('dash')"><span>🏠</span>Home</div>
        <div class="nav-item" onclick="nav('auto')"><span>⏰</span>Rules</div>
        <div class="nav-item" onclick="nav('set')"><span>⚙️</span>Setup</div>
    </div>

    <script>
        // --- THEME ---
        if(localStorage.getItem('theme') === 'light') document.documentElement.classList.add('light');
        function toggleTheme() {
            document.documentElement.classList.toggle('light');
            localStorage.setItem('theme', document.documentElement.classList.contains('light') ? 'light' : 'dark');
        }

        // --- NAVIGATION ---
        function nav(id) {
            document.querySelectorAll('.view').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
            document.getElementById('view-'+id).classList.add('active');
            event.currentTarget.classList.add('active');
        }

        // --- API & DATA ---
        const API = {
            get: async (ep) => (await fetch('/api/'+ep)).json(),
            post: async (ep, d) => (await fetch('/api/'+ep, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)})).json(),
            del: async (ep) => (await fetch('/api/'+ep, {method:'DELETE'})).json()
        };

        let cachedDevices = [];
        let cachedSchedules = [];
        let currentSettings = { subnets: [] };

        // --- DASHBOARD LOGIC ---
        async function updateDashboard() {
            try {
                const data = await API.get('devices');
                const list = document.getElementById('device-list');
                const sel = document.getElementById('s-dev');
                
                if (data.length === 0 && list.children.length > 1) {
                    list.innerHTML = '<div style="text-align:center; padding:40px; opacity:0.6; grid-column:1/-1;">No devices found.</div>';
                    return;
                }

                if (data.length !== cachedDevices.length) {
                    list.innerHTML = '';
                    sel.innerHTML = '';
                    data.sort((a,b) => a.name.localeCompare(b.name)).forEach(d => {
                        sel.add(new Option(d.name, d.name));
                        let div = document.createElement('div');
                        div.className = 'card flex';
                        div.id = 'card-' + d.name.replace(/\s+/g, '-');
                        div.innerHTML = `
                            <div>
                                <div style="font-weight:bold; font-size:1.1rem;">${d.name}</div>
                                <div style="font-size:0.8rem; color:var(--subtext);">${d.ip}</div>
                            </div>
                            <button id="btn-${d.name.replace(/\s+/g, '-')}" class="btn btn-toggle ${d.state ? 'on' : ''}" onclick="toggle('${d.name}')">
                                ${d.state ? 'ON' : 'OFF'}
                            </button>`;
                        list.appendChild(div);
                    });
                } else {
                    data.forEach(d => {
                        const btn = document.getElementById('btn-' + d.name.replace(/\s+/g, '-'));
                        if (btn) {
                            const isOn = d.state === 1 || d.state === true;
                            if (btn.classList.contains('on') !== isOn) {
                                btn.className = `btn btn-toggle ${isOn ? 'on' : ''}`;
                                btn.innerText = isOn ? 'ON' : 'OFF';
                            }
                        }
                    });
                }
                cachedDevices = data;
            } catch(e) { console.log("Poll error", e); }
        }

        async function toggle(n) { 
            const btn = document.getElementById('btn-' + n.replace(/\s+/g, '-'));
            if(btn) {
                const isNowOn = btn.innerText === 'OFF';
                btn.className = `btn btn-toggle ${isNowOn ? 'on' : ''}`;
                btn.innerText = isNowOn ? 'ON' : 'OFF';
            }
            await API.post('toggle/'+n); 
            setTimeout(updateDashboard, 500); 
        }

        // --- SCHEDULE LOGIC ---
        async function updateSchedules() {
            try {
                const data = await API.get('schedules');
                if (JSON.stringify(data) === JSON.stringify(cachedSchedules)) return;
                
                const list = document.getElementById('sched-list');
                list.innerHTML = '';
                if(data.length === 0) list.innerHTML = '<div style="opacity:0.6; text-align:center; padding:20px;">No active rules.</div>';
                
                data.forEach(s => {
                    let div = document.createElement('div');
                    div.className = 'card flex';
                    div.innerHTML = `
                        <div>
                            <div style="font-weight:bold; color:var(--accent);">${s.action} ${s.device}</div>
                            <div style="font-size:0.9rem; color:var(--subtext);">${s.type} ${s.value}</div>
                        </div>
                        <button class="btn btn-danger" style="padding:8px 12px;" onclick="delSched(${s.id})">🗑️</button>`;
                    list.appendChild(div);
                });
                cachedSchedules = data;
            } catch(e) {}
        }
        
        async function addSchedule() {
            await API.post('schedules', {
                device: document.getElementById('s-dev').value,
                action: document.getElementById('s-action').value,
                type: document.getElementById('s-type').value,
                value: document.getElementById('s-val').value,
                days: [0,1,2,3,4,5,6]
            });
            updateSchedules();
            alert('Schedule Added');
        }
        
        async function delSched(id) { 
            if(confirm('Delete this rule?')) { 
                await API.del('schedules?id='+id); 
                updateSchedules(); 
            } 
        }

        // --- SUBNET MANAGER LOGIC ---
        async function loadSettings() {
            const s = await API.get('settings');
            currentSettings = s;
            if (!currentSettings.subnets) currentSettings.subnets = [];
            renderSubnetList();
        }

        function renderSubnetList() {
            const sel = document.getElementById('subnet-select');
            sel.innerHTML = '<option value="">-- Select Saved Subnet --</option>';
            currentSettings.subnets.forEach(sub => {
                sel.add(new Option(sub, sub));
            });
        }

        function selectSubnet() {
            const sel = document.getElementById('subnet-select');
            if (sel.value) {
                document.getElementById('subnet-input').value = sel.value;
            }
        }

        async function saveSubnet() {
            const val = document.getElementById('subnet-input').value.trim();
            if (!val) return;
            
            // Add if unique
            if (!currentSettings.subnets.includes(val)) {
                currentSettings.subnets.push(val);
                await API.post('settings', { subnets: currentSettings.subnets });
                renderSubnetList();
                document.getElementById('subnet-select').value = val; // Select it
                alert('Subnet Saved');
            } else {
                alert('Subnet already in list');
            }
        }

        async function deleteSubnet() {
            const sel = document.getElementById('subnet-select');
            const val = sel.value;
            
            if (!val) {
                alert('Please select a subnet from the dropdown to delete.');
                return;
            }
            
            if (confirm('Delete saved subnet: ' + val + '?')) {
                currentSettings.subnets = currentSettings.subnets.filter(s => s !== val);
                await API.post('settings', { subnets: currentSettings.subnets });
                renderSubnetList();
                document.getElementById('subnet-input').value = '';
            }
        }

        function triggerScan() { API.post('scan'); alert('Scanning Network...'); }

        // --- POLLING LOOP ---
        async function poller() {
            const s = await API.get('status');
            document.getElementById('scan-status').innerText = s.scan_status;
            
            await updateDashboard();
            await updateSchedules();
        }

        // Init
        loadSettings();
        updateDashboard();
        updateSchedules();
        
        // Fast Polling for Responsive UI
        setInterval(poller, 2000); 
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    settings = load_json(SETTINGS_FILE, {})
    
    # Start background threads
    threading.Thread(target=scanner_loop, daemon=True).start()
    threading.Thread(target=poller_loop, daemon=True).start()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    
    print("----------------------------------------------------------------")
    print(f"   WEMO OPS SERVER - LISTENING ON PORT {PORT}")
    print("----------------------------------------------------------------")
    
    # Production-ready server
    serve(app, host=HOST, port=PORT, threads=6)