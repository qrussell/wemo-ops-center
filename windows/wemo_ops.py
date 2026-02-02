import customtkinter as ctk
import pywemo
import threading
import sys
import os
import subprocess
import time
import json
from tkinter import messagebox
import pyperclip
import requests

# --- CONFIGURATION ---
VERSION = "v3.1-DEV"

# --- PATH SETUP ---
APP_DATA_DIR = os.path.join(os.getenv('APPDATA'), "WemoOps")
if not os.path.exists(APP_DATA_DIR):
    try: os.makedirs(APP_DATA_DIR)
    except: pass
PROFILE_FILE = os.path.join(APP_DATA_DIR, "wifi_profiles.json")

# --- PYINSTALLER RESOURCE PATH FIX ---
if getattr(sys, 'frozen', False):
    os.environ['PATH'] += os.pathsep + sys._MEIPASS

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class WemoOpsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Wemo Ops Center {VERSION} | Development Build")
        self.geometry("1100x850") 
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.current_setup_ip = None 
        self.current_setup_port = None 

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="WEMO OPS\nDEV MODE", font=("Arial Black", 20))
        self.logo.pack(pady=20)
        
        self.btn_dash = ctk.CTkButton(self.sidebar, text="  Dashboard", anchor="w", 
                                      command=lambda: self.show_tab("dash"))
        self.btn_dash.pack(pady=5, padx=10, fill="x")
        
        self.btn_prov = ctk.CTkButton(self.sidebar, text="  Provisioner", anchor="w", 
                                      command=lambda: self.show_tab("prov"))
        self.btn_prov.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkLabel(self.sidebar, text=f"{VERSION}", text_color="orange", font=("Arial", 10)).pack(side="bottom", pady=10)

        # --- Main Area ---
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.frames = {}
        self.create_dashboard()
        self.create_provisioner()

        # START ON DASHBOARD
        self.show_tab("dash")
        self.refresh_network()
        
        self.monitoring = True
        threading.Thread(target=self._connection_monitor, daemon=True).start()

    # ---------------------------------------------------------
    # UI CONSTRUCTION
    # ---------------------------------------------------------
    def create_dashboard(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["dash"] = frame
        
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(head, text="Network Overview", font=("Roboto", 24)).pack(side="left")
        
        manual_frame = ctk.CTkFrame(frame, fg_color="#222")
        manual_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(manual_frame, text="Direct Connect:", font=("Arial", 12)).pack(side="left", padx=10)
        self.ip_entry = ctk.CTkEntry(manual_frame, placeholder_text="192.168.1.x", width=150)
        self.ip_entry.pack(side="left", padx=5, pady=10)
        ctk.CTkButton(manual_frame, text="Add Device", width=100, fg_color="#444", 
                      command=self.manual_add_device).pack(side="left", padx=5)
        
        ctk.CTkButton(head, text="↻ Scan Network", width=120, command=self.refresh_network).pack(side="right")
        
        self.dev_list = ctk.CTkScrollableFrame(frame, label_text="Discovered Devices")
        self.dev_list.pack(fill="both", expand=True)

    def create_provisioner(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["prov"] = frame
        
        frame.columnconfigure(0, weight=1) 
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(0, weight=1)

        # --- LEFT COLUMN ---
        left_col = ctk.CTkFrame(frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # 1. Scanner
        ctk.CTkLabel(left_col, text="Step 1: Locate Device", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))
        scan_frame = ctk.CTkFrame(left_col, fg_color="#222")
        scan_frame.pack(fill="x", pady=(0, 20))
        self.btn_scan_setup = ctk.CTkButton(scan_frame, text="🔍 Scan Airwaves", command=self.scan_ssids)
        self.btn_scan_setup.pack(pady=10, padx=10, fill="x")
        self.ssid_list = ctk.CTkScrollableFrame(scan_frame, height=100, label_text="Nearby Networks")
        self.ssid_list.pack(fill="x", padx=10, pady=(0,10))

        # 2. Configuration
        ctk.CTkLabel(left_col, text="Step 2: Configuration", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))
        input_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        input_frame.pack(fill="x")

        # Profile Manager
        self.profiles = self.load_profiles()
        profile_names = list(self.profiles.keys())
        
        prof_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        prof_row.pack(fill="x", pady=5)
        self.profile_combo = ctk.CTkComboBox(prof_row, values=["Select Saved Profile..."] + profile_names, 
                                             command=self.apply_profile, width=200)
        self.profile_combo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(prof_row, text="💾", width=40, command=self.save_current_profile).pack(side="left", padx=5)
        ctk.CTkButton(prof_row, text="🗑️", width=40, fg_color="#aa3333", hover_color="#882222", 
                      command=self.delete_profile).pack(side="left")

        self.name_entry = ctk.CTkEntry(input_frame, placeholder_text="Device Name (e.g. Office Fan)")
        self.name_entry.pack(fill="x", pady=5)
        self.ssid_entry = ctk.CTkEntry(input_frame, placeholder_text="SSID")
        self.ssid_entry.pack(fill="x", pady=5)
        self.pass_entry = ctk.CTkEntry(input_frame, placeholder_text="Password", show="*")
        self.pass_entry.pack(fill="x", pady=5)

        # 3. DEV / ADVANCED OPTIONS
        ctk.CTkLabel(left_col, text="Step 3: Encryption Backend (Dev)", font=("Arial", 14, "bold"), text_color="orange").pack(anchor="w", pady=(15,5))
        adv_frame = ctk.CTkFrame(left_col, fg_color="#2b2b2b")
        adv_frame.pack(fill="x", pady=(0, 10))

        # Encryption Mode Selection
        # UPDATED LABELS: Reflecting the backend Library logic (ARC4 vs AES)
        ctk.CTkLabel(adv_frame, text="Payload Encryption:", font=("Arial", 11)).pack(anchor="w", padx=10, pady=(5,0))
        self.enc_mode_combo = ctk.CTkComboBox(adv_frame, values=["Auto (Smart Loop)", "Method 2 (AES/OpenSSL)", "Method 1 (ARC4/Legacy)", "Method 0 (None)"])
        self.enc_mode_combo.pack(fill="x", padx=10, pady=5)
        self.enc_mode_combo.set("Auto (Smart Loop)")

        # Append Length Selection
        ctk.CTkLabel(adv_frame, text="Padding (Append Length):", font=("Arial", 11)).pack(anchor="w", padx=10, pady=(5,0))
        self.append_len_combo = ctk.CTkComboBox(adv_frame, values=["Auto", "True (Append)", "False (Standard)"])
        self.append_len_combo.pack(fill="x", padx=10, pady=5)
        self.append_len_combo.set("Auto")

        # 4. Action Button
        self.prov_btn = ctk.CTkButton(left_col, text="Push Configuration", fg_color="#28a745", hover_color="#1e7e34", 
                                      height=50, state="disabled", command=self.run_provision_thread)
        self.prov_btn.pack(fill="x", pady=20)

        # --- RIGHT COLUMN ---
        right_col = ctk.CTkFrame(frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew")

        # Status Monitor
        self.status_frame = ctk.CTkFrame(right_col, fg_color="#331111", border_color="#ff5555", border_width=2)
        self.status_frame.pack(fill="x", pady=(0, 10))
        
        self.status_lbl_icon = ctk.CTkLabel(self.status_frame, text="❌", font=("Arial", 30))
        self.status_lbl_icon.pack(side="left", padx=15, pady=15)
        
        stat_txt = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        stat_txt.pack(side="left", fill="x")
        self.status_lbl_text = ctk.CTkLabel(stat_txt, text="NOT CONNECTED", font=("Arial", 16, "bold"), text_color="#ff5555")
        self.status_lbl_text.pack(anchor="w")
        self.status_lbl_sub = ctk.CTkLabel(stat_txt, text="Connect Windows Wi-Fi to 'Wemo.Mini.XXX'", font=("Arial", 12))
        self.status_lbl_sub.pack(anchor="w")

        # Override Link
        self.override_link = ctk.CTkLabel(right_col, text="[Manual Override: Click to Unlock]", font=("Arial", 10, "underline"), 
                                          text_color="gray", cursor="hand2")
        self.override_link.pack(anchor="e", pady=(0, 5))
        self.override_link.bind("<Button-1>", lambda e: self.force_unlock())

        # Log
        ctk.CTkLabel(right_col, text="Live Operation Log", font=("Arial", 12)).pack(anchor="w")
        self.prov_log = ctk.CTkTextbox(right_col, font=("Consolas", 12), activate_scrollbars=True)
        self.prov_log.pack(fill="both", expand=True)

    # ---------------------------------------------------------
    # PROVISIONING (ENHANCED V3.1)
    # ---------------------------------------------------------
    def run_provision_thread(self):
        ssid = self.ssid_entry.get()
        pwd = self.pass_entry.get()
        name = self.name_entry.get()
        
        # Get Manual Options
        enc_choice = self.enc_mode_combo.get()
        len_choice = self.append_len_combo.get()

        if not ssid: 
            messagebox.showwarning("Missing Data", "Enter SSID.")
            return
        
        target_ip = self.current_setup_ip or "10.22.22.1"
        target_port = self.current_setup_port 
        
        self.prov_btn.configure(state="disabled", text="Running...")
        self.prov_log.delete("1.0", "end")
        
        # Pass manual options to the thread
        threading.Thread(target=self._provision_task, args=(ssid, pwd, name, target_ip, target_port, enc_choice, len_choice), daemon=True).start()

    def _provision_task(self, ssid, pwd, friendly_name, ip_address, port, enc_mode_str, append_len_str):
        self.log_prov(f"--- Configuring Device at {ip_address} ---")
        try:
            # 1. Resolve URL
            if port:
                url = f"http://{ip_address}:{port}/setup.xml"
            else:
                url = pywemo.setup_url_for_address(ip_address)
            
            self.log_prov(f"Targeting URL: {url}")
            dev = pywemo.discovery.device_from_description(url)
            
            # 2. Set Name First
            if friendly_name and hasattr(dev, 'basicevent'):
                self.log_prov(f"Setting Name to: {friendly_name}")
                dev.basicevent.ChangeFriendlyName(FriendlyName=friendly_name)
                time.sleep(1) 

            # 3. Determine Encryption Logic
            # Map GUI Labels to Internal Integers
            manual_enc = None
            if "Method 2" in enc_mode_str: manual_enc = 2
            elif "Method 1" in enc_mode_str: manual_enc = 1
            elif "Method 0" in enc_mode_str: manual_enc = 0
            
            # Parse User Selection for Append Length
            manual_len = None
            if "True" in append_len_str: manual_len = True
            elif "False" in append_len_str: manual_len = False

            # 4. Execute Provisioning
            if "Auto" in enc_mode_str:
                self.log_prov("Mode: Auto (Smart Loop)")
                self._brute_force_provision(dev, ssid, pwd)
            else:
                # Manual Mode
                # If Auto length is selected in Manual Enc mode, we still loop length options
                if manual_len is None:
                    self.log_prov(f"Mode: Manual {enc_mode_str} / Length: Auto")
                    self._manual_loop_length(dev, ssid, pwd, manual_enc)
                else:
                    self.log_prov(f"Mode: Manual {enc_mode_str} / Length: {manual_len}")
                    # v3.1 Fix: Use internal arguments to bypass TypeError
                    try:
                        dev.setup(ssid=ssid, password=pwd, _encrypt_method=manual_enc, _add_password_lengths=manual_len)
                    except TypeError:
                         # Double-fallback: If even the underscore method fails, try standard arg (just in case)
                         dev.setup(ssid=ssid, password=pwd, encrypt=manual_enc, append_length=manual_len)
                    
                    self.log_prov("Setup command sent (Manual).")

            self.log_prov("SUCCESS: Configuration Sent!")
            self.log_prov("Device is rebooting. Connect PC back to Home Wi-Fi.")
        except Exception as e:
            self.log_prov(f"Error: {e}")

        self.prov_btn.configure(state="normal", text="Push Configuration")

    def _brute_force_provision(self, dev, ssid, pwd):
        """
        Iterates through all encryption combinations using internal _encrypt_method
        to bypass 'unexpected keyword' errors in older/mixed lib versions.
        """
        # Order: Method 2 (AES/OpenSSL), Method 1 (ARC4), Method 0 (None)
        enc_modes = [2, 1, 0]
        # Order: True (Most common for new FW), False (Old FW)
        len_opts = [True, False]

        for mode in enc_modes:
            for length in len_opts:
                try:
                    self.log_prov(f"Attempting: Method {mode}, Len={length}...")
                    
                    # Try using internal arguments first (safest for Bleeding Edge)
                    dev.setup(ssid=ssid, password=pwd, _encrypt_method=mode, _add_password_lengths=length)
                    
                    self.log_prov(f"  > Accepted! (Method {mode}, Len {length})")
                    return # Exit on success

                except TypeError:
                    # If the library is VERY old and doesn't know _encrypt_method either,
                    # fall back to the basic setup (which defaults to Method 2 internally)
                    self.log_prov("  > Library Mismatch: '_encrypt_method' missing.")
                    self.log_prov("  > Fallback: Attempting Legacy Standard Setup...")
                    try:
                        dev.setup(ssid=ssid, password=pwd)
                        self.log_prov("  > Legacy Setup Accepted!")
                        return
                    except Exception as e:
                        self.log_prov(f"  > Legacy Setup Failed: {e}")
                        # Don't break, just continue to next option (though it might be futile)
                        time.sleep(1)
                        continue

                except Exception as e:
                    self.log_prov(f"  > Failed: {str(e)}")
                    time.sleep(0.5)
        
        raise Exception("All provisioning attempts failed.")

    def _manual_loop_length(self, dev, ssid, pwd, fixed_mode):
        """Helper for Manual Mode but Auto Length"""
        len_opts = [True, False]
        for length in len_opts:
            try:
                self.log_prov(f"Attempting Fixed Method {fixed_mode} with AppendLen={length}...")
                try:
                    dev.setup(ssid=ssid, password=pwd, _encrypt_method=fixed_mode, _add_password_lengths=length)
                except TypeError:
                    dev.setup(ssid=ssid, password=pwd) # Last ditch legacy
                
                self.log_prov("  > Accepted!")
                return
            except: pass
        raise Exception("Failed with selected mode.")

    # ---------------------------------------------------------
    # UTILITY METHODS (Standard from v3.0)
    # ---------------------------------------------------------
    def load_profiles(self):
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, 'r') as f: return json.load(f)
            except: return {}
        return {}

    def save_current_profile(self):
        ssid = self.ssid_entry.get()
        pwd = self.pass_entry.get()
        if not ssid or not pwd:
            messagebox.showwarning("Error", "Enter SSID and Password first.")
            return
        try:
            self.profiles[ssid] = pwd
            with open(PROFILE_FILE, 'w') as f: json.dump(self.profiles, f)
            self.profile_combo.configure(values=["Select Saved Profile..."] + list(self.profiles.keys()))
            self.profile_combo.set(ssid)
            messagebox.showinfo("Saved", f"Profile saved.")
        except Exception as e:
            messagebox.showerror("Save Failed", f"Permission Error:\n{e}")

    def apply_profile(self, choice):
        if choice in self.profiles:
            self.ssid_entry.delete(0, "end")
            self.ssid_entry.insert(0, choice)
            self.pass_entry.delete(0, "end")
            self.pass_entry.insert(0, self.profiles[choice])

    def delete_profile(self):
        curr = self.profile_combo.get()
        if curr in self.profiles:
            try:
                del self.profiles[curr]
                with open(PROFILE_FILE, 'w') as f: json.dump(self.profiles, f)
                self.profile_combo.configure(values=["Select Saved Profile..."] + list(self.profiles.keys()))
                self.profile_combo.set("Select Saved Profile...")
                self.ssid_entry.delete(0, "end")
                self.pass_entry.delete(0, "end")
            except Exception as e:
                messagebox.showerror("Delete Failed", f"Error:\n{e}")

    def show_tab(self, name):
        for key, frame in self.frames.items(): frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        self.btn_dash.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        self.btn_prov.configure(fg_color="transparent", text_color=("gray10", "gray90"))
        if name == "dash": self.btn_dash.configure(fg_color=("gray75", "gray25"), text_color="white")
        elif name == "prov": self.btn_prov.configure(fg_color=("gray75", "gray25"), text_color="white")

    def log_prov(self, msg):
        self.prov_log.insert("end", f"{msg}\n")
        self.prov_log.see("end")

    def _connection_monitor(self):
        target_ips = ["10.22.22.1", "192.168.49.1", "192.168.1.1"]
        target_ports = [49152, 49153, 49154, 49155, 49151] 
        while self.monitoring:
            found_dev = None
            found_ip = None
            found_port = None
            for ip in target_ips:
                for port in target_ports:
                    try:
                        check_url = f"http://{ip}:{port}/setup.xml"
                        requests.get(check_url, timeout=0.2)
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
        self.status_lbl_sub.configure(text="Connect Wi-Fi. If connected, click Override below.")
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

    def scan_ssids(self):
        for w in self.ssid_list.winfo_children(): w.destroy()
        lbl = ctk.CTkLabel(self.ssid_list, text="Scanning...", text_color="yellow")
        lbl.pack()
        threading.Thread(target=self._scan_thread_logic, args=(lbl,), daemon=True).start()

    def _scan_thread_logic(self, status_lbl):
        wemos = []
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output("netsh wlan show networks mode=bssid", startupinfo=si).decode('utf-8', errors='ignore')
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith("SSID"):
                    ssid = line.split(":", 1)[1].strip()
                    if "wemo" in ssid.lower() or "belkin" in ssid.lower(): wemos.append(ssid)
        except: pass
        status_lbl.destroy()
        if wemos:
            for ssid in list(set(wemos)): self.after(0, lambda s=ssid: self.build_ssid_card(s))
        else: self.after(0, lambda: ctk.CTkLabel(self.ssid_list, text="No Wemo networks found.", text_color="#ff5555").pack())

    def build_ssid_card(self, ssid):
        card = ctk.CTkFrame(self.ssid_list, fg_color="#333")
        card.pack(fill="x", pady=2, padx=5)
        ctk.CTkLabel(card, text=ssid, font=("Arial", 12, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(card, text="⬅ Connect Manually", text_color="#aaa", font=("Arial", 10)).pack(side="right", padx=10)

    def manual_add_device(self):
        ip = self.ip_entry.get()
        if not ip: return
        threading.Thread(target=self._manual_add_task, args=(ip,), daemon=True).start()

    def _manual_add_task(self, ip):
        try:
            url = pywemo.setup_url_for_address(ip)
            dev = pywemo.discovery.device_from_description(url)
            if dev:
                self.after(0, lambda: self.build_device_card(dev))
                self.after(0, lambda: messagebox.showinfo("Success", f"Added {dev.name}"))
            else: self.after(0, lambda: messagebox.showwarning("Failed", "No device found."))
        except Exception as e: self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def refresh_network(self):
        for w in self.dev_list.winfo_children(): w.destroy()
        ctk.CTkLabel(self.dev_list, text="Scanning...", text_color="yellow").pack(pady=20)
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            devices = pywemo.discover_devices()
            self.after(0, self.update_dashboard, devices)
        except: pass

    def update_dashboard(self, devices):
        for w in self.dev_list.winfo_children(): w.destroy()
        if not devices: ctk.CTkLabel(self.dev_list, text="No devices found.").pack(pady=20)
        for dev in devices: self.build_device_card(dev)

    def build_device_card(self, dev):
        try: mac = getattr(dev, 'mac', "Unknown")
        except: mac = "Unknown"
        try: serial = getattr(dev, 'serial_number', "Unknown")
        except: serial = "Unknown"
        try: fw = getattr(dev, 'firmware_version', "Unknown")
        except: fw = "Unknown"
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
        meta_str = f"IP: {dev.host} | MAC: {mac} | SN: {serial} | FW: {fw}"
        ctk.CTkLabel(mid, text=meta_str, font=("Consolas", 11), text_color="#aaa").pack(anchor="w")
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
                    pyperclip.copy(code)
                else: self.after(0, lambda: messagebox.showwarning("Error", "No Code Found"))
        except: pass

if __name__ == "__main__":
    app = WemoOpsApp()
    app.mainloop()