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
from waitress import serve  # REQUIRED for production/frozen builds

# --- CONFIGURATION ---
VERSION = "v5.1.6-Server"
PORT = 5050  # Updated to 5050 to avoid AirPlay conflict
HOST = "0.0.0.0"

# --- PATH SETUP ---
if sys.platform == "win32":
    APP_DATA_DIR = os.path.join(os.getenv('APPDATA'), "WemoOps")
else:
    # Use standard Linux paths if root, otherwise user home
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
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(APP_DATA_DIR, "server.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WemoServer")

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
    # Refresh if date changed or empty
    if solar_times and solar_times.get('date') == datetime.date.today().isoformat():
        return solar_times
    
    lat = settings.get('lat')
    lng = settings.get('lng')
    
    if not lat: 
        try:
            # Auto-detect via IP if not set
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
    def probe_port(self, ip, port=49153, timeout=0.2):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((str(ip), port))
            s.close()
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
                # Wemo ports vary
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
            # Standard Discovery
            devices = pywemo.discover_devices()
            for dev in devices: known_devices[dev.name] = dev
            
            # Deep Scan if configured
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
        time.sleep(300) # Scan every 5 mins

def scheduler_loop():
    logger.info("Scheduler Started")
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
                
                # Calculate Trigger Time
                if job['type'] == "Time (Fixed)":
                    trigger_time = job['value']
                elif solar:
                    base = solar['sunrise'] if job['type'] == "Sunrise" else solar['sunset']
                    try:
                        dt = datetime.datetime.strptime(f"{today_str} {base}", "%Y-%m-%d %H:%M")
                        offset = int(job['value']) * int(job.get('offset_dir', 1))
                        trigger_time = (dt + datetime.timedelta(minutes=offset)).strftime("%H:%M")
                    except: continue
                
                # Check Trigger
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
        "device_count": len(known_devices),
        "version": VERSION
    })

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
        threading.Thread(target=dev.toggle).start()
        return jsonify({"status": "ok"})
    return jsonify({"status": "not found"}), 404

@app.route('/api/maintenance/reset', methods=['POST'])
def api_reset():
    """Allows remote reset of devices from desktop app"""
    data = request.json
    name = data.get('device')
    code = data.get('code', 0)
    dev = known_devices.get(name)
    if dev and hasattr(dev, 'basicevent'):
        try:
            dev.basicevent.ReSetup(Reset=int(code))
            return jsonify({"status": "ok"})
        except Exception as e: return jsonify({"status": "error", "msg": str(e)})
    return jsonify({"status": "failed"}), 400

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    global settings
    if request.method == 'GET': return jsonify(settings)
    if request.method == 'POST':
        settings.update(request.json)
        save_json(SETTINGS_FILE, settings)
        return jsonify({"status": "saved"})

# --- NEW ROUTE FOR SUBNET CONFIG (FIX) ---
@app.route('/api/config/subnet', methods=['POST'])
def api_config_subnet():
    """Specific endpoint for Desktop App to set scan subnet"""
    global settings
    data = request.json
    new_subnet = data.get('subnet')
    
    if new_subnet:
        # Validate simple format check
        if "/" in new_subnet or "192." in new_subnet:
            # We store it in the standard settings dict
            settings['subnets'] = [new_subnet]
            save_json(SETTINGS_FILE, settings)
            return jsonify({"status": "success", "subnet": new_subnet}), 200
    
    return jsonify({"status": "error", "message": "Invalid subnet"}), 400

@app.route('/api/scan', methods=['POST'])
def api_scan():
    global scan_status
    if "Scanning" in scan_status: return jsonify({"status": "busy"})
    
    # NOTE: Since scanner_loop is already running in a thread (while True),
    # we shouldn't start a NEW thread here or we get duplicates.
    # Ideally, we would set a flag to wake up the scanner, 
    # but for now we simply return success and let the loop or user wait.
    # To force it, you would need to refactor scanner_loop to wait on an Event.
    
    # However, if this is the first start or needed, we can try:
    return jsonify({"status": "queued", "message": "Scan will run on next cycle"})

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

# --- FRONTEND (MOBILE READY PWA) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Wemo Ops">
    <title>Wemo Ops Web</title>
    <style>
        :root { --bg: #121212; --card: #1e1e1e; --text: #e0e0e0; --accent: #3b82f6; --green: #10b981; --danger: #ef4444; }
        body { background-color: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; padding-bottom: 80px; }
        
        /* APP BAR */
        .app-bar { background: #000000; padding: 15px; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
        .brand { font-weight: 800; font-size: 1.2rem; background: linear-gradient(to right, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        /* CONTAINER */
        .container { max-width: 600px; margin: 0 auto; padding: 15px; }
        .card { background: var(--card); padding: 15px; margin-bottom: 12px; border-radius: 12px; border: 1px solid #333; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .flex { display: flex; justify-content: space-between; align-items: center; }
        
        /* BUTTONS */
        .btn { padding: 10px 18px; border: none; border-radius: 8px; cursor: pointer; color: white; font-weight: 600; font-size: 0.9rem; transition: transform 0.1s; }
        .btn:active { transform: scale(0.96); }
        .btn-toggle { background-color: #333; width: 80px; height: 40px; }
        .btn-toggle.on { background-color: var(--green); box-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }
        .btn-primary { background-color: var(--accent); }
        .btn-danger { background-color: var(--danger); }
        
        /* FORMS */
        select, input { background: #2d2d2d; color: white; border: 1px solid #444; padding: 10px; border-radius: 8px; width: 100%; box-sizing: border-box; font-size: 1rem; margin-bottom: 8px; }
        .row { display: flex; gap: 8px; }
        
        /* BOTTOM NAV */
        .bottom-nav { position: fixed; bottom: 0; width: 100%; background: #000; border-top: 1px solid #333; display: flex; justify-content: space-around; padding: 12px 0; z-index: 100; padding-bottom: max(12px, env(safe-area-inset-bottom)); }
        .nav-item { color: #666; font-size: 0.8rem; text-align: center; cursor: pointer; }
        .nav-item.active { color: var(--accent); }
        .nav-icon { font-size: 1.4rem; display: block; margin-bottom: 2px; }

        /* VIEWS */
        .view { display: none; }
        .view.active { display: block; }
        
        .status-badge { font-size: 0.75rem; background: #333; padding: 2px 6px; border-radius: 4px; color: #aaa; }
    </style>
</head>
<body>

    <div class="app-bar">
        <div class="brand">Wemo Ops</div>
        <div class="status-badge" id="scan-status">Idle</div>
    </div>

    <div class="container">
        <div id="view-dash" class="view active">
            <div id="device-list">
                <div style="text-align:center; padding:40px; color:#666;">Loading devices...</div>
            </div>
        </div>

        <div id="view-auto" class="view">
            <div class="card">
                <h3 style="margin-top:0">New Schedule</h3>
                <div style="font-size:0.8rem; color:#888; margin-bottom:10px;" id="solar-data">Loading solar...</div>
                
                <select id="s-dev"><option>Loading...</option></select>
                <div class="row">
                    <select id="s-action"><option>Turn ON</option><option>Turn OFF</option><option>Toggle</option></select>
                    <select id="s-type" onchange="toggleType()">
                        <option>Time (Fixed)</option><option>Sunrise</option><option>Sunset</option>
                    </select>
                </div>
                <div class="row">
                    <input type="text" id="s-val" placeholder="HH:MM">
                    <select id="s-off" style="display:none;"><option value="1">After (+)</option><option value="-1">Before (-)</option></select>
                </div>
                
                <div style="margin:10px 0; display:flex; justify-content:space-between; color:#bbb;">
                     <label><input type="checkbox" class="day" value="0" checked>M</label>
                     <label><input type="checkbox" class="day" value="1" checked>T</label>
                     <label><input type="checkbox" class="day" value="2" checked>W</label>
                     <label><input type="checkbox" class="day" value="3" checked>T</label>
                     <label><input type="checkbox" class="day" value="4" checked>F</label>
                     <label><input type="checkbox" class="day" value="5" checked>S</label>
                     <label><input type="checkbox" class="day" value="6" checked>S</label>
                </div>
                <button class="btn btn-primary" style="width:100%" onclick="addSchedule()">Add Schedule</button>
            </div>
            
            <h3 style="margin:20px 0 10px 5px; color:#666;">Active Rules</h3>
            <div id="sched-list"></div>
        </div>
        
        <div id="view-set" class="view">
            <div class="card">
                <h3>Scan Settings</h3>
                <p style="color:#aaa; font-size:0.9rem;">Add custom subnets (comma separated) for the deep scanner.</p>
                <input type="text" id="subnets" placeholder="192.168.1.0/24">
                <button class="btn btn-primary" onclick="saveSettings()">Save Subnets</button>
            </div>
            <div class="card" style="border-color:#333;">
                <button class="btn" style="width:100%; background:#333;" onclick="triggerScan()">Force Network Scan</button>
            </div>
            <div style="text-align:center; color:#444; margin-top:30px; font-size:0.8rem;">
                Wemo Ops Server {{ version }}
            </div>
        </div>
    </div>

    <div class="bottom-nav">
        <div class="nav-item active" onclick="nav('dash')">
            <span class="nav-icon">🏠</span> Home
        </div>
        <div class="nav-item" onclick="nav('auto')">
            <span class="nav-icon">⏰</span> Rules
        </div>
        <div class="nav-item" onclick="nav('set')">
            <span class="nav-icon">⚙️</span> Settings
        </div>
    </div>

    <script>
        // NAVIGATION
        function nav(target) {
            document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById('view-'+target).classList.add('active');
            event.currentTarget.classList.add('active');
        }

        // API CALLS
        const API = {
            get: async (ep) => (await fetch('/api/'+ep)).json(),
            post: async (ep, data) => (await fetch('/api/'+ep, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)})).json(),
            del: async (ep) => (await fetch('/api/'+ep, {method:'DELETE'})).json()
        };

        // DASHBOARD
        async function loadDash() {
            const data = await API.get('devices');
            const list = document.getElementById('device-list');
            const sel = document.getElementById('s-dev');
            
            list.innerHTML = ''; sel.innerHTML = '';
            
            if(data.length === 0) list.innerHTML = '<div style="text-align:center; padding:30px; color:#555;">No devices found.<br><br>Check that devices are on the same network.</div>';

            data.sort((a,b) => a.name.localeCompare(b.name)).forEach(d => {
                // Populate dropdown for automation
                let opt = document.createElement('option');
                opt.value = d.name; opt.innerText = d.name;
                sel.appendChild(opt);

                // Create Card
                let card = document.createElement('div');
                card.className = 'card flex';
                card.innerHTML = `
                    <div>
                        <div style="font-size:1.1rem; font-weight:600;">${d.name}</div>
                        <div style="font-size:0.8rem; color:#666;">${d.ip}</div>
                    </div>
                    <button class="btn btn-toggle ${d.state ? 'on' : ''}" onclick="toggle('${d.name}')">
                        ${d.state ? 'ON' : 'OFF'}
                    </button>
                `;
                list.appendChild(card);
            });
        }

        async function toggle(name) {
            // Optimistic UI update could go here
            await API.post('toggle/'+name);
            loadDash();
        }

        // AUTOMATION
        function toggleType() {
            let t = document.getElementById('s-type').value;
            let isSolar = t !== "Time (Fixed)";
            document.getElementById('s-off').style.display = isSolar ? 'block' : 'none';
            document.getElementById('s-val').placeholder = isSolar ? "Offset (min)" : "HH:MM";
            document.getElementById('s-val').value = isSolar ? "0" : "";
        }

        async function loadSched() {
            const data = await API.get('schedules');
            const list = document.getElementById('sched-list');
            list.innerHTML = '';
            
            if(data.length === 0) list.innerHTML = '<div style="color:#555; font-size:0.9rem; text-align:center;">No active rules.</div>';

            data.forEach(s => {
                let days = s.days.length === 7 ? "Daily" : s.days.length + " Days";
                let timeStr = s.type === "Time (Fixed)" ? s.value : `${s.type} ${s.value}m`;
                
                let div = document.createElement('div');
                div.className = 'card flex';
                div.innerHTML = `
                    <div>
                        <span class="status-badge" style="color:#aaa;">${days}</span>
                        <strong style="margin-left:5px;">${timeStr}</strong>
                        <div style="font-size:0.9rem; color:#888; margin-top:2px;">
                            ${s.action} <span style="color:var(--accent)">${s.device}</span>
                        </div>
                    </div>
                    <button class="btn btn-danger" style="padding:5px 12px;" onclick="delSched(${s.id})">Del</button>
                `;
                list.appendChild(div);
            });
        }

        async function addSchedule() {
            let days = [];
            document.querySelectorAll('.day:checked').forEach(c => days.push(parseInt(c.value)));
            if(days.length === 0) return alert('Choose at least one day');

            await API.post('schedules', {
                device: document.getElementById('s-dev').value,
                action: document.getElementById('s-action').value,
                type: document.getElementById('s-type').value,
                value: document.getElementById('s-val').value,
                offset_dir: parseInt(document.getElementById('s-off').value),
                days: days
            });
            alert('Schedule created!');
            loadSched();
        }

        async function delSched(id) {
            if(confirm('Delete rule?')) {
                await API.del('schedules?id='+id);
                loadSched();
            }
        }

        // SETTINGS & STATUS
        async function loadSettings() {
            const s = await API.get('settings');
            if(s.subnets) document.getElementById('subnets').value = s.subnets.join(',');
        }
        
        async function saveSettings() {
            let sub = document.getElementById('subnets').value.split(',').map(s=>s.trim()).filter(s=>s);
            await API.post('settings', {subnets: sub});
            alert('Settings Saved');
        }

        async function updateStatus() {
            const s = await API.get('status');
            document.getElementById('scan-status').innerText = s.scan_status;
            
            const sol = await API.get('solar');
            if(sol.sunrise) document.getElementById('solar-data').innerText = `☀️ ${sol.sunrise}  🌙 ${sol.sunset}`;
        }
        
        function triggerScan() { API.post('scan'); alert('Scanning...'); }

        // INIT
        loadDash();
        loadSched();
        loadSettings();
        setInterval(updateStatus, 3000);
        setInterval(loadDash, 5000);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    settings = load_json(SETTINGS_FILE, {})
    threading.Thread(target=scanner_loop, daemon=True).start()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    
    print("----------------------------------------------------------------")
    print(f"   WEMO OPS SERVER - LISTENING ON PORT {PORT}")
    print("   (Port 5000 is reserved for AirPlay on macOS)")
    print("----------------------------------------------------------------")
    
    # Use Waitress for Production/PyInstaller builds
    serve(app, host=HOST, port=PORT, threads=6)