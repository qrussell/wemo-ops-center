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
from flask import Flask, render_template, jsonify, request
from waitress import serve
from pywemo.ouimeaux_device.dimmer import Dimmer
from pywemo.ouimeaux_device.insight import Insight

# --- CONFIGURATION ---
VERSION = "v5.3.1-Server"
PORT = int(os.environ.get("PORT", 5050)) 
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
DEVICES_FILE = os.path.join(APP_DATA_DIR, "devices.json")

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

class ScanNoiseFilter(logging.Filter):
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
settings = {}
solar_times = {}

# --- UTILS ---
def load_json(path, default=None):
    if default is None: 
        default = {}
    if os.path.exists(path):
        try: 
            with open(path, 'r') as f: 
                return json.load(f)
        except: 
            pass
    return default

def save_json(path, data):
    try: 
        with open(path, 'w') as f: 
            json.dump(data, f, indent=2)
    except Exception as e: 
        logger.error(f"Failed to save JSON: {e}")

def save_device_cache():
    cache_data = {}
    for uid, data in list(device_registry.items()):
        cache_data[uid] = {
            "name": data.get("name"),
            "ip": data.get("ip"),
            "mac": data.get("mac"),
            "serial": data.get("serial"),
            "state": data.get("state", 0),
            "type": data.get("type", "switch"),
            "last_seen": data.get("last_seen", 0)
        }
    save_json(DEVICES_FILE, cache_data)

def load_device_cache():
    """Seed the registry with placeholders for cached devices. Never overwrites
    live entries. Old caches were keyed by friendly name (no "name" field)."""
    global device_registry
    cache = load_json(DEVICES_FILE, {})
    for key, data in cache.items():
        uid = key if "name" in data else f"cache:{key}"
        if uid in device_registry: continue
        device_registry[uid] = {
            "obj": None,
            "name": data.get("name") or key,
            "ip": data.get("ip"),
            "mac": data.get("mac"),
            "serial": data.get("serial"),
            "state": data.get("state", 0),
            "type": data.get("type", "switch"),
            "last_seen": data.get("last_seen", 0)
        }

def get_solar_times():
    global solar_times
    if solar_times and solar_times.get('date') == datetime.date.today().isoformat():
        return solar_times
    lat = settings.get('lat'); lng = settings.get('lng')
    if not lat: return None
    try:
        url = f"https://api.sunrise-sunset.org/json?lat={lat}&lng={lng}&formatted=0"
        r = requests.get(url, timeout=5)
        res = r.json()["results"]
        def to_local(utc_str):
            return datetime.datetime.fromisoformat(utc_str).astimezone().strftime("%H:%M")
        solar_times = {
            "date": datetime.date.today().isoformat(),
            "sunrise": to_local(res["sunrise"]),
            "sunset": to_local(res["sunset"])
        }
        return solar_times
    except: return None

# --- DEEP SCANNER ---
WEMO_PORTS = (49153, 49152, 49154, 49155)

def _raise_fd_limit():
    """macOS apps launched from Finder start with a 256 open-file limit (some Linux
    setups too). The scanner's parallel sockets would exhaust it, and each failed
    connect would silently look like 'no Wemo here'. Raise it; report what we got."""
    try:
        import resource
    except ImportError:
        return None  # Windows: no per-process open-file limit for sockets
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        want = 4096 if hard == resource.RLIM_INFINITY else min(4096, hard)
        if soft != resource.RLIM_INFINITY and soft < want:
            try: resource.setrlimit(resource.RLIMIT_NOFILE, (want, hard)); soft = want
            except (ValueError, OSError): pass
        return None if soft == resource.RLIM_INFINITY else soft
    except Exception:
        return 256

_FD_LIMIT = _raise_fd_limit()
# Each worker holds ~1 socket at a time; leave headroom for the GUI/server/pywemo.
SCAN_WORKERS = 256 if _FD_LIMIT is None else max(16, min(256, (_FD_LIMIT - 64) // 2))

# Adapters that are VPNs, VMs or containers. Their subnets are not the home LAN,
# and probing e.g. a corporate VPN can trip security monitoring. Users can still
# add any of these subnets by hand.
VIRTUAL_ADAPTER_WORDS = ("vmware", "virtualbox", "vbox", "hyper-v", "vethernet", "parallels", "docker",
    "wsl", "wintun", "openvpn", "tap-windows", "tap adapter", "wireguard", "tailscale", "zerotier",
    "vpn", "anyconnect", "fortinet", "forticlient", "globalprotect", "pangp", "nordlynx", "npcap",
    "loopback", "wi-fi direct", "bluetooth")
VIRTUAL_IFACE_PREFIXES = ("docker", "veth", "br-", "virbr", "vmnet", "vboxnet", "tun", "tap", "wg",
    "tailscale", "zt", "utun", "awdl", "llw", "lxc", "lxd", "cni", "flannel", "cali", "podman", "bridge1", "anpi", "ipsec", "ppp")

def is_virtual_adapter(adapter):
    nice = (getattr(adapter, "nice_name", "") or "").lower()
    name = str(getattr(adapter, "name", "") or "").lower()
    return any(w in nice for w in VIRTUAL_ADAPTER_WORDS) or name.startswith(VIRTUAL_IFACE_PREFIXES) or nice.startswith(VIRTUAL_IFACE_PREFIXES)

def get_local_subnets():
    """Every IPv4 LAN subnet this machine is connected to (VPN/VM adapters
    skipped). Skips
    loopback/link-local; very large networks are clamped to the host's /24."""
    nets = []
    try:
        import ifaddr
        for adapter in ifaddr.get_adapters():
            if is_virtual_adapter(adapter): continue
            for ip in adapter.ips:
                if not isinstance(ip.ip, str): continue  # IPv6 entries are tuples
                addr = ipaddress.ip_address(ip.ip)
                if addr.is_loopback or addr.is_link_local: continue
                prefix = ip.network_prefix if 22 <= ip.network_prefix <= 30 else 24
                nets.append(str(ipaddress.ip_network(f"{ip.ip}/{prefix}", strict=False)))
    except Exception as e:
        logger.warning(f"Subnet detection failed: {e}")
    return list(dict.fromkeys(nets))

class DeepScanner:
    PROBE_TIMEOUT = 0.8   # TCP connect per ip:port
    VERIFY_TIMEOUT = 3.0  # quick HTTP check that the host really is a Wemo
    VERIFY_WORKERS = 32   # HTTP checks run after the connect sweep, with modest parallelism

    def tcp_open(self, ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(self.PROBE_TIMEOUT)
        try:
            s.connect((ip, port)); return (ip, port)
        except Exception:
            return None
        finally:
            s.close()

    def is_wemo(self, ip, port):
        """Hosts like Windows PCs have 49152+ open (RPC) but never answer HTTP;
        rejecting them here avoids pywemo's 10s-per-port timeouts. A dropped
        connection (not a timeout) is retried once."""
        for attempt in range(2):
            try:
                r = requests.get(f"http://{ip}:{port}/setup.xml", timeout=self.VERIFY_TIMEOUT)
                return "urn:Belkin" in r.text
            except requests.exceptions.Timeout:
                return False
            except Exception:
                if attempt == 0: time.sleep(0.3)
        return False

    def probe_port(self, ip, port):
        """(ip, port) if the port is open AND serves a Belkin setup.xml, else None."""
        ip = str(ip)
        return (ip, port) if self.tcp_open(ip, port) and self.is_wemo(ip, port) else None

    def find_wemo_hosts(self, hosts, known_ips=()):
        """ip -> port of every Wemo among hosts, in two steps:
        1. TCP connect sweep of all ip:port pairs, highly parallel;
        2. HTTP check of only the open ports, with few workers.
        Doing the HTTP check during the sweep missed devices: with hundreds of
        connects in flight (Docker Desktop NAT, busy routers) the Wemo's small
        HTTP server timed out. 6 of 7 devices were lost at 256 workers."""
        open_ports = []
        def sweep(targets, workers):
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                open_ports.extend(r for r in executor.map(lambda a: self.tcp_open(*a), targets) if r)
        # Devices already known (last scan / cache) are checked first, before the
        # connect burst, so a congested network can't make them disappear.
        hosts = list(hosts); in_scope = set(hosts)
        known = [ip for ip in dict.fromkeys(known_ips) if ip in in_scope]
        if known: sweep([(ip, p) for ip in known for p in WEMO_PORTS], self.VERIFY_WORKERS)
        known_set = set(known)
        sweep([(ip, p) for ip in hosts if ip not in known_set for p in WEMO_PORTS], SCAN_WORKERS)
        wemo_hosts = {}
        if open_ports:
            open_ports.sort(key=lambda a: WEMO_PORTS.index(a[1]))  # preferred port first per host
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.VERIFY_WORKERS) as executor:
                for (ip, port), ok in zip(open_ports, executor.map(lambda a: self.is_wemo(*a), open_ports)):
                    if ok: wemo_hosts.setdefault(ip, port)
        return wemo_hosts

    def scan_subnet(self, subnets, known_ips=()):
        import pywemo
        all_hosts = []
        for subnet in subnets:
            try:
                if "/" not in subnet: subnet += "/24"
                net = ipaddress.ip_network(subnet.strip(), strict=False)
                all_hosts.extend([str(ip) for ip in net.hosts()])
            except: pass
        all_hosts = list(dict.fromkeys(all_hosts))  # overlapping subnets: probe once
        if not all_hosts: return []
        wemo_hosts = self.find_wemo_hosts(all_hosts, known_ips)
        if not wemo_hosts: return []
        def load(item):
            try: return pywemo.discovery.device_from_description(f"http://{item[0]}:{item[1]}/setup.xml")
            except Exception: return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            return [d for d in executor.map(load, wemo_hosts.items()) if d]

# --- BACKGROUND TASKS ---
def device_uid(dev):
    """Stable unique id for a device (friendly names are NOT unique)."""
    for attr in ("udn", "serial_number", "mac"):
        try:
            v = getattr(dev, attr)
            if v and str(v).lower() != "unknown": return str(v)
        except Exception: pass
    return f"{dev.host}:{dev.port}"

def labeled_registry():
    """label -> entry. Labels are the friendly name, plus a short MAC/serial
    suffix when several devices share a name (e.g. un-renamed 'Wemo Mini')."""
    by_name = {}
    for uid, e in list(device_registry.items()): by_name.setdefault(e.get("name") or uid, []).append((uid, e))
    out = {}
    for name, items in by_name.items():
        if len(items) == 1: out[name] = items[0][1]; continue
        for uid, e in items:
            ident = next((str(e.get(k)) for k in ("mac", "serial") if e.get(k) and str(e.get(k)).lower() != "unknown"), uid)
            out[f"{name} ({ident.replace(':', '').replace('-', '')[-4:].upper()})"] = e
    return out

def find_device(label):
    return labeled_registry().get(label)

def find_schedule_targets(device_ref):
    """Devices a schedule should act on. Exact label first. Schedules made by older
    versions stored the bare friendly name; if several devices share that name the
    labels now carry a suffix, so fall back to every device with that name rather
    than silently doing nothing (older versions acted on one arbitrary match)."""
    entry = find_device(device_ref)
    if entry: return [entry]
    matches = [e for e in list(device_registry.values()) if e.get("name") == device_ref]
    if len(matches) > 1:
        logger.warning(f"Schedule device '{device_ref}' matches {len(matches)} devices with that name; "
                       f"running on all of them. Recreate the schedule to target one.")
    return matches

def register_device(dev):
    global device_registry
    try:
        mac = getattr(dev, 'mac', 'Unknown')
        serial = getattr(dev, 'serial_number', 'Unknown')
        # [NEW] Check if device is a dimmer
        is_dimmer = isinstance(dev, Dimmer)
        uid = device_uid(dev)
        # Drop cache placeholders for this same physical device
        for k, e in list(device_registry.items()):
            if k != uid and e.get("obj") is None and (e.get("ip") == dev.host or (mac != 'Unknown' and e.get("mac") == mac) or (serial != 'Unknown' and e.get("serial") == serial)):
                device_registry.pop(k, None)
        prev = device_registry.get(uid, {})
        device_registry[uid] = {
            "obj": dev,
            "name": dev.name,
            "ip": dev.host,
            "mac": mac,
            "serial": serial,
            "state": prev.get("state", 0),
            "type": "dimmer" if is_dimmer else "switch",
            "last_seen": time.time()
        }
    except Exception as e:
        logger.error(f"Error registering device {dev}: {e}")

def run_scan_cycle(full=False):
    """full=True (startup, manual Scan): deep-scan saved subnets + every connected
    LAN subnet. Periodic cycles only deep-scan saved subnets, unless the user turned
    on settings["periodic_full_scan"] (off by default)."""
    global scan_status, device_registry, settings
    if scan_status not in ("Idle", "Error"): return  # a failed scan must not block later ones
    try:
        scan_status = "Scanning..."
        import pywemo
        ds = DeepScanner()
        load_device_cache()
        devices = pywemo.discover_devices()
        for dev in devices: register_device(dev)
        settings.update(load_json(SETTINGS_FILE, {}))  # pick up changes saved by the desktop app
        subs = list(settings.get("subnets", []))
        if full or settings.get("periodic_full_scan", False):
            subs = list(dict.fromkeys(subs + get_local_subnets()))
        if subs:
            scan_status = "Deep Scanning..."
            known_ips = [e.get("ip") for e in list(device_registry.values()) if e.get("ip")]
            deep_devs = ds.scan_subnet(subs, known_ips=known_ips)
            for dev in deep_devs: register_device(dev)
        now = time.time()
        to_remove = [k for k, d in list(device_registry.items()) if (now - d.get("last_seen", 0)) > 900]
        for k in to_remove: device_registry.pop(k, None)
        save_device_cache()
        scan_status = "Idle"
    except Exception as e:
        logger.error(f"Scan Error: {e}"); scan_status = "Error"

def scanner_loop():
    run_scan_cycle(full=True)  # find everything once at startup
    while True:
        time.sleep(SCAN_INTERVAL)
        run_scan_cycle(full=False)

def poller_loop():
    while True:
        keys = list(device_registry.keys())
        for key in keys:
            entry = device_registry.get(key)
            if entry is None: continue
            dev = entry.get("obj")
            if dev:
                try:
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
                            if new_dev: register_device(new_dev); break
                        except: pass
        time.sleep(2)

def scheduler_loop():
    while True:
        try:
            now = datetime.datetime.now(); today_str = now.strftime("%Y-%m-%d"); weekday = now.weekday(); current_hhmm = now.strftime("%H:%M")
            solar = get_solar_times()
            current_schedules = load_json(SCHEDULE_FILE, []); schedule_modified = False
            for job in current_schedules:
                job_days = job.get('days', [])
                if not job_days or weekday not in job_days: continue
                trigger_time = ""
                if job['type'] == "Time (Fixed)": trigger_time = job['value']
                elif solar:
                    base = solar['sunrise'] if job['type'] == "Sunrise" else solar['sunset']
                    try:
                        dt = datetime.datetime.strptime(f"{today_str} {base}", "%Y-%m-%d %H:%M")
                        trigger_time = (dt + datetime.timedelta(minutes=int(job['value']) * int(job.get('offset_dir', 1)))).strftime("%H:%M")
                    except: continue
                if trigger_time == current_hhmm and job.get('last_run') != today_str:
                    for entry in find_schedule_targets(job['device']):
                        if not entry.get("obj"): continue
                        dev = entry["obj"]
                        try:
                            action = job['action']
                            if action == "Turn ON": dev.on()
                            elif action == "Turn OFF": dev.off()
                            elif action == "Toggle": dev.toggle()
                            entry['state'] = dev.get_state(force_update=True)
                            logger.info(f"Executed Schedule: {job['device']} ({entry.get('ip')}) -> {action}")
                        except Exception as e: logger.error(f"Failed to execute schedule for {job['device']} ({entry.get('ip')}): {e}")
                    job['last_run'] = today_str; schedule_modified = True
            if schedule_modified: save_json(SCHEDULE_FILE, current_schedules)
        except Exception as e: logger.error(f"Scheduler error: {e}")
        time.sleep(30)

# --- ROUTES ---
@app.route('/')
def index(): return render_template("index.html", version=VERSION)

@app.route('/api/status')
def api_status():
    return jsonify({"status": "online", "scan_status": scan_status, "device_count": len(device_registry), "version": VERSION})

def insight_readings(dev):
    """Power readings for Insight plugs (GitHub issue 27), from the values the
    poller already fetched: no extra network call. {} for other devices."""
    if not isinstance(dev, Insight): return {}
    try:
        return {"power_w": round(dev.current_power_watts, 1),
                "today_kwh": round(dev.today_kwh, 3)}
    except Exception:
        return {}

@app.route('/api/devices')
def api_devices():
    devs_out = []
    for name, data in labeled_registry().items():
        devs_out.append({
            "name": name, 
            "ip": data.get("ip"), 
            "state": data.get("state", 0),
            "mac": data.get("mac"),
            "serial": data.get("serial"),
            "type": data.get("type", "switch"), # [NEW] Return device type
            **insight_readings(data.get("obj"))
        })
    return jsonify(devs_out)

@app.route('/api/toggle/<name>', methods=['POST'])
def api_toggle(name):
    entry = find_device(name)
    if entry and entry.get("obj"):
        dev = entry["obj"]
        def toggle_task():
            try: dev.toggle(); entry['state'] = dev.get_state(force_update=True)
            except: pass
        threading.Thread(target=toggle_task).start()
        return jsonify({"status": "ok"})
    return jsonify({"status": "not found"}), 404

# [NEW] Brightness Route
@app.route('/api/brightness/<name>', methods=['POST'])
def api_brightness(name):
    entry = find_device(name)
    if entry and entry.get("obj"):
        dev = entry["obj"]
        try:
            level = int(request.json.get('level', 0))
            def dim_task():
                try: 
                    dev.set_brightness(level)
                    entry['state'] = level
                except: pass
            threading.Thread(target=dim_task).start()
            return jsonify({"status": "ok"})
        except Exception as e: return jsonify({"status": "error", "error": str(e)}), 400
    return jsonify({"status": "not found"}), 404

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    global settings
    if request.method == 'GET':
        # connected_subnets is informational (auto-detected, never saved), so the
        # web UI can show the same network list as the desktop app.
        return jsonify({**settings, "connected_subnets": get_local_subnets()})
    if request.method == 'POST':
        # Merge onto the file, not our in-memory copy, so keys the desktop app
        # saved since we last read it (theme, scale, ...) are not reverted.
        update = dict(request.json or {}); update.pop("connected_subnets", None)
        disk = load_json(SETTINGS_FILE, {}); disk.update(update)
        save_json(SETTINGS_FILE, disk); settings.update(disk)
        return jsonify({"status": "saved"})

@app.route('/api/scan', methods=['POST'])
def api_scan():
    global scan_status
    if scan_status not in ("Idle", "Error"): return jsonify({"status": "busy"})
    threading.Thread(target=run_scan_cycle, kwargs={"full": True}, daemon=True).start()
    return jsonify({"status": "started"})

@app.route('/api/schedules', methods=['GET', 'POST', 'DELETE'])
def api_schedules():
    current = load_json(SCHEDULE_FILE, [])
    if request.method == 'GET': return jsonify(current)
    if request.method == 'POST':
        data = request.json
        new_job = {
            "id": int(time.time()),
            "device": data.get('device'),
            "type": data.get('type'),
            "action": data.get('action'),
            "value": data.get('value'),
            "offset_dir": data.get('offset_dir', 1),
            "days": data.get('days', [0,1,2,3,4,5,6]),
            "last_run": ""
        }
        current.append(new_job); save_json(SCHEDULE_FILE, current)
        return jsonify({"status": "added", "id": new_job['id']})
    if request.method == 'DELETE':
        jid = int(request.args.get('id')); current = [x for x in current if x['id'] != jid]; save_json(SCHEDULE_FILE, current)
        return jsonify({"status": "deleted"})

if __name__ == "__main__":
    settings = load_json(SETTINGS_FILE, {})
    threading.Thread(target=scanner_loop, daemon=True).start()
    threading.Thread(target=poller_loop, daemon=True).start()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    print(f"   WEMO OPS SERVER - LISTENING ON PORT {PORT}")
    serve(app, host=HOST, port=PORT, threads=6)