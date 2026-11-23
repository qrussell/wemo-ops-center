"""Schedules stored on the Wemo device itself (GitHub issue 28).

Wemo firmware keeps its rules in a small SQLite database on the plug. The
"rules" UPnP service hands out its URL and version (FetchRules), serves it as a
zip, and accepts a replacement (StoreRules). This module reads that database,
backs it up, and writes simple on/off schedules to it, with safety guards:

* every write is preceded by a backup of the plug's current rules;
* nothing is written if the existing rules can't be downloaded (pywemo itself
  would start from an empty database and erase them);
* nothing is written if the rules changed since they were read;
* the rules are read back after each write to check the plug kept them;
* only one write per device at a time.

Firmware without the cloud: plugs accept and keep these rules, but on a Wemo Mini
with firmware 2.00.11565 (tested 22 Nov 2026) they never ran. One report on
pywemo issue 773 has an F7C027 on 2.00.11851 running them. Treat on-device
schedules as experimental and keep the Wemo Ops scheduler as the reliable path.
"""

import base64
import datetime
import io
import os
import sqlite3
import tempfile
import threading
import time
import zipfile

from pywemo.exceptions import HTTPNotOkException

WOC_PREFIX = "WOC: "          # marks rules created by Wemo Ops Center
NO_DATE_START = "12201982"    # Wemo app's "no date range" values
NO_DATE_END = "07301982"
DAY_LETTERS = ["M", "T", "W", "Th", "F", "Sa", "Su"]  # app day index 0 = Monday
DB_NAME_IN_ZIP = "temppluginRules.db"

# Tables as the firmware and pywemo's rules_db.py define them.
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS RULES (RuleID PRIMARY KEY, Name TEXT NOT NULL, Type TEXT NOT NULL,
       RuleOrder INTEGER, StartDate TEXT, EndDate TEXT, State TEXT, Sync INTEGER)""",
    """CREATE TABLE IF NOT EXISTS RULEDEVICES (RuleDevicePK INTEGER PRIMARY KEY AUTOINCREMENT, RuleID INTEGER,
       DeviceID TEXT, GroupID INTEGER, DayID INTEGER, StartTime INTEGER, RuleDuration INTEGER,
       StartAction REAL, EndAction REAL, SensorDuration INTEGER, Type INTEGER, Value INTEGER, Level INTEGER,
       ZBCapabilityStart TEXT, ZBCapabilityEnd TEXT, OnModeOffset INTEGER, OffModeOffset INTEGER,
       CountdownTime INTEGER, EndTime INTEGER)""",
    """CREATE TABLE IF NOT EXISTS DEVICECOMBINATION (DeviceCombinationPK INTEGER PRIMARY KEY AUTOINCREMENT,
       RuleID INTEGER, SensorID TEXT, SensorGroupID INTEGER, DeviceID TEXT, DeviceGroupID INTEGER)""",
    """CREATE TABLE IF NOT EXISTS GROUPDEVICES (GroupDevicePK INTEGER PRIMARY KEY AUTOINCREMENT,
       GroupID INTEGER, DeviceID TEXT)""",
    """CREATE TABLE IF NOT EXISTS LOCATIONINFO (LocationPk INTEGER PRIMARY KEY AUTOINCREMENT, cityName TEXT,
       countryName TEXT, latitude TEXT, longitude TEXT, countryCode TEXT, region TEXT)""",
    """CREATE TABLE IF NOT EXISTS BLOCKEDRULES (Primarykey INTEGER PRIMARY KEY AUTOINCREMENT, ruleId TEXT)""",
    """CREATE TABLE IF NOT EXISTS RULESNOTIFYMESSAGE (RuleID INTEGER PRIMARY KEY AUTOINCREMENT,
       NotifyRuleID INTEGER, Message TEXT, Frequency INTEGER)""",
    """CREATE TABLE IF NOT EXISTS SENSORNOTIFICATION (SensorNotificationPK INTEGER PRIMARY KEY AUTOINCREMENT,
       RuleID INTEGER, NotifyRuleID INTEGER, NotificationMessage TEXT, NotificationDuration INTEGER)""",
    """CREATE TABLE IF NOT EXISTS TARGETDEVICES (TargetDevicesPK INTEGER PRIMARY KEY AUTOINCREMENT,
       RuleID INTEGER, DeviceID TEXT, DeviceIndex INTEGER)""",
]

EXPERIMENTAL_NOTE = (
    "Because they live on the plug, they don't need this computer or the "
    "Wemo Ops service. Since Belkin's cloud shut down, some firmware keeps these schedules but never runs "
    "them (a Wemo Mini on firmware 2.00.11565 didn't). Watch the plug the first time a schedule is due, and "
    "use the Automation tab if it doesn't switch.")

_locks = {}
_locks_guard = threading.Lock()


class RulesError(Exception):
    """A rules operation was refused or failed; the message is meant for the user."""


def _lock_for(dev):
    key = getattr(dev, "udn", None) or f"{dev.host}:{dev.port}"
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def supports_rules(dev):
    svc = getattr(dev, "rules", None)
    actions = getattr(svc, "actions", {}) if svc is not None else {}
    return "FetchRules" in actions and "StoreRules" in actions


# --- Day and time helpers -------------------------------------------------

def day_index_to_dayid(i):
    """App day index (0 = Monday ... 6 = Sunday) -> firmware DayID (1 = Sunday ... 7 = Saturday)."""
    return (int(i) + 1) % 7 + 1


def dayid_to_day_index(d):
    return (int(d) + 5) % 7


def parse_hhmm(text):
    """'18:30' -> seconds after midnight. Empty -> None. Raises ValueError if invalid."""
    text = (text or "").strip()
    if not text: return None
    h, m = text.split(":")
    h, m = int(h), int(m)
    if not (0 <= h < 24 and 0 <= m < 60): raise ValueError(text)
    return h * 3600 + m * 60


def secs_to_hhmm(s):
    if s is None or s < 0 or s >= 86400: return None
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}"


# --- Database packaging ---------------------------------------------------

def _unzip_db(content):
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        names = [n for n in z.namelist() if n.endswith(".db")] or z.namelist()
        if not names: raise RulesError("The plug's rules file is empty.")
        return names[0], z.read(names[0])


def _zip_db(db_bytes, inner_name):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(inner_name or DB_NAME_IN_ZIP, db_bytes)
    return buf.getvalue()


def _open_db(db_bytes=None):
    """Open a writable copy of a rules DB (or a new empty one) in a temp file."""
    fd, path = tempfile.mkstemp(prefix="wemorules_", suffix=".db"); os.close(fd)
    if db_bytes:
        with open(path, "wb") as f: f.write(db_bytes)
    con = sqlite3.connect(path)
    for stmt in SCHEMA: con.execute(stmt)
    con.commit()
    return con, path


def _close_db(con, path):
    con.commit(); con.close()
    with open(path, "rb") as f: data = f.read()
    try: os.remove(path)
    except OSError: pass
    return data


def rules_from_db(db_bytes):
    """List the rules in a DB as dicts: id, name, type, enabled, ours, on, off, days, devices."""
    con, path = _open_db(db_bytes)
    try:
        out = []
        for rid, name, rtype, state in con.execute("SELECT RuleID, Name, Type, State FROM RULES ORDER BY RuleID"):
            rows = con.execute("SELECT DeviceID, DayID, StartTime, EndTime, StartAction, EndAction "
                               "FROM RULEDEVICES WHERE RuleID=?", (rid,)).fetchall()
            days = sorted({dayid_to_day_index(r[1]) for r in rows if r[1] is not None and 1 <= int(r[1]) <= 7})
            first = rows[0] if rows else None
            on = off = None
            if first:
                start, end, sa, ea = first[2], first[3], first[4], first[5]
                if sa == 1: on = secs_to_hhmm(start)
                elif sa == 0: off = secs_to_hhmm(start)
                if ea == 0: off = secs_to_hhmm(end)
                elif ea == 1: on = secs_to_hhmm(end)
            out.append({"id": rid, "name": str(name), "type": str(rtype), "enabled": str(state) == "1",
                        "ours": str(name).startswith(WOC_PREFIX), "on": on, "off": off, "days": days,
                        "devices": sorted({r[0] for r in rows if r[0]})})
        return out
    finally:
        _close_db(con, path)


def describe_rule(r):
    days = "Every day" if len(r["days"]) == 7 else "".join(DAY_LETTERS[i] for i in r["days"]) or "No days"
    parts = []
    if r["on"]: parts.append(f"on {r['on']}")
    if r["off"]: parts.append(f"off {r['off']}")
    what = ", ".join(parts) if parts else r["type"]
    name = r["name"][len(WOC_PREFIX):] if r["ours"] else r["name"]
    src = "Wemo Ops" if r["ours"] else "other app"
    state = "" if r["enabled"] else " (disabled)"
    return f"[{days}] {what}  {name}  ({src}){state}"


# --- Talking to the device ------------------------------------------------

def fetch(dev):
    """Read the plug's rules. Returns {"version", "db" (bytes or None), "inner", "zip"}.
    version 0 / no file means the plug has no rules. Raises RulesError if a rules
    file exists but can't be downloaded, so callers never mistake it for empty."""
    try:
        info = dev.rules.FetchRules()
        version = int(info.get("ruleDbVersion") or 0)
        url = info.get("ruleDbPath") or ""
    except Exception as e:
        raise RulesError(f"The plug didn't answer the rules request: {e}")
    if not url.startswith("http"):
        url = f"http://{dev.host}:{dev.port}/{url.lstrip('/')}" if url else ""
    content = None
    if url:
        try:
            content = dev.session.get(url).content
        except HTTPNotOkException as e:
            # Plugs with no rules answer 404. With a version above 0 a rules file
            # should exist, so a failure there must never be read as "no rules".
            if version > 0:
                raise RulesError(f"Couldn't download the plug's rules (version {version}): {e}. Nothing was changed.")
        except Exception as e:
            raise RulesError(f"Couldn't download the plug's rules: {e}. Nothing was changed.")
    if not content:
        return {"version": version, "db": None, "inner": DB_NAME_IN_ZIP, "zip": None}
    try:
        inner, db = _unzip_db(content)
    except zipfile.BadZipFile:
        raise RulesError("The plug's rules file isn't a valid zip. Nothing was changed.")
    return {"version": version, "db": db, "inner": inner, "zip": content}


def list_rules(dev):
    state = fetch(dev)
    return state, (rules_from_db(state["db"]) if state["db"] else [])


def backup(dev, state, backup_dir):
    """Save the plug's current rules zip. Returns the path, or None if it has no rules."""
    if not state.get("zip"): return None
    os.makedirs(backup_dir, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in (getattr(dev, "name", "") or "device"))
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(backup_dir, f"{safe}_v{state['version']}_{stamp}.zip")
    with open(path, "wb") as f: f.write(state["zip"])
    return path


def _sync_clock(dev, timesync_args):
    try:
        if timesync_args and "TimeSync" in getattr(getattr(dev, "timesync", None), "actions", {}):
            dev.timesync.TimeSync(**timesync_args())
    except Exception:
        pass  # a failed clock sync shouldn't block saving


def _store(dev, read_state, db_bytes, inner, expect_rules):
    """Upload db_bytes as the next version, after checking nobody changed the rules
    since read_state, then read back and check the plug kept what we sent."""
    now = fetch(dev)
    if now["version"] != read_state["version"] or now["db"] != read_state["db"]:
        raise RulesError("The plug's rules changed since they were read (another app?). Refresh and try again.")
    body = base64.b64encode(_zip_db(db_bytes, inner)).decode("ascii")
    try:
        resp = dev.rules.StoreRules(ruleDbVersion=now["version"] + 1, processDb=1,
                                    ruleDbBody="&lt;![CDATA[" + body + "]]&gt;")
    except Exception as e:
        raise RulesError(f"The plug refused the rules: {e}")
    info = str((resp or {}).get("errorInfo", "")).lower()
    if info and "success" not in info:
        raise RulesError(f"The plug refused the rules: {info.strip()}")
    time.sleep(2)
    after = fetch(dev)
    got = rules_from_db(after["db"]) if after["db"] else []
    if sorted(r["name"] for r in got) != sorted(expect_rules):
        raise RulesError("The plug answered, but reading its rules back didn't show the change. "
                         "Refresh to see what it holds; a backup was saved first.")
    return after


def add_schedule(dev, name, on_time, off_time, days, backup_dir, timesync_args=None):
    """Add an on/off schedule. on_time/off_time are 'HH:MM' or '' (at least one);
    days are app day indexes (0 = Monday). Returns the backup path (or None)."""
    on_s, off_s = parse_hhmm(on_time), parse_hhmm(off_time)
    if on_s is None and off_s is None: raise RulesError("Enter an ON time, an OFF time, or both.")
    if not days: raise RulesError("Select at least one day.")
    if on_s is not None and off_s is not None and off_s == on_s: raise RulesError("ON and OFF can't be the same time.")
    name = (name or "").strip() or "Schedule"
    full_name = WOC_PREFIX + name
    with _lock_for(dev):
        state = fetch(dev)
        existing = rules_from_db(state["db"]) if state["db"] else []
        if any(r["name"] == full_name for r in existing):
            raise RulesError(f"This plug already has a schedule called '{name}'. Pick another name.")
        path = backup(dev, state, backup_dir)
        _sync_clock(dev, timesync_args)
        con, tmp = _open_db(state["db"])
        try:
            rid = (con.execute("SELECT COALESCE(MAX(CAST(RuleID AS INTEGER)), 0) FROM RULES").fetchone()[0] or 0) + 1
            con.execute("INSERT INTO RULES (RuleID,Name,Type,RuleOrder,StartDate,EndDate,State,Sync) "
                        "VALUES (?,?,'Time Interval',2,?,?,'1','NOSYNC')", (rid, full_name, NO_DATE_START, NO_DATE_END))
            if on_s is not None:
                start, sa = on_s, 1.0
                end, ea = (off_s, 0.0) if off_s is not None else (86340, -1.0)
            else:
                start, sa, end, ea = off_s, 0.0, 86340, -1.0
            for i in sorted(set(days)):
                con.execute("INSERT INTO RULEDEVICES (RuleID,DeviceID,GroupID,DayID,StartTime,RuleDuration,"
                            "StartAction,EndAction,SensorDuration,Type,Value,Level,ZBCapabilityStart,"
                            "ZBCapabilityEnd,OnModeOffset,OffModeOffset,CountdownTime,EndTime) "
                            "VALUES (?,?,0,?,?,0,?,?,2,-1,-1,-1,'','',0,0,0,?)",
                            (rid, dev.udn, day_index_to_dayid(i), start, sa, ea, end))
            new_db = _close_db(con, tmp)
        except Exception:
            con.close(); raise
        _store(dev, state, new_db, state["inner"], [r["name"] for r in existing] + [full_name])
        return path


def delete_schedule(dev, rule_id, backup_dir):
    """Delete one rule that Wemo Ops Center created. Returns the backup path."""
    with _lock_for(dev):
        state = fetch(dev)
        existing = rules_from_db(state["db"]) if state["db"] else []
        rule = next((r for r in existing if str(r["id"]) == str(rule_id)), None)
        if not rule: raise RulesError("That schedule is no longer on the plug. Refresh the list.")
        if not rule["ours"]: raise RulesError("Only schedules made by Wemo Ops Center can be deleted one by one. "
                                              "Use Clear All to remove the others.")
        path = backup(dev, state, backup_dir)
        con, tmp = _open_db(state["db"])
        for table in ("RULES", "RULEDEVICES", "TARGETDEVICES"):
            con.execute(f"DELETE FROM {table} WHERE RuleID=?", (rule["id"],))
        new_db = _close_db(con, tmp)
        _store(dev, state, new_db, state["inner"], [r["name"] for r in existing if r["id"] != rule["id"]])
        return path


def clear_all(dev, backup_dir):
    """Remove every rule on the plug (backup first). Returns the backup path."""
    with _lock_for(dev):
        state = fetch(dev)
        if not state["db"]: return None
        path = backup(dev, state, backup_dir)
        if not path: raise RulesError("Couldn't save a backup, so nothing was cleared.")
        con, tmp = _open_db(None)
        new_db = _close_db(con, tmp)
        _store(dev, state, new_db, state["inner"], [])
        return path


def restore(dev, zip_path, backup_dir):
    """Put a saved backup back on the plug (the current rules are backed up first)."""
    with open(zip_path, "rb") as f: content = f.read()
    try:
        inner, db = _unzip_db(content)
        names = [r["name"] for r in rules_from_db(db)]
    except Exception as e:
        raise RulesError(f"That file isn't a Wemo rules backup: {e}")
    with _lock_for(dev):
        state = fetch(dev)
        path = backup(dev, state, backup_dir)
        _store(dev, state, db, inner, names)
        return path
