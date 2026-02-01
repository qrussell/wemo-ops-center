import customtkinter as ctk
import pywemo
import threading
import time
from tkinter import messagebox
import pyperclip  # pip install pyperclip

# --- THEME SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class WemoOpsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Config ---
        self.title("Wemo Ops Center | HomeKit Extractor Edition")
        self.geometry("950x700")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="WEMO OPS", font=("Arial Black", 20))
        self.logo.pack(pady=20)
        
        self.btn_dash = ctk.CTkButton(self.sidebar, text="  Dashboard", anchor="w", command=lambda: self.show_tab("dash"))
        self.btn_dash.pack(pady=5, padx=10, fill="x")
        
        self.btn_prov = ctk.CTkButton(self.sidebar, text="  Provisioner", anchor="w", fg_color="#444", command=lambda: self.show_tab("prov"))
        self.btn_prov.pack(pady=5, padx=10, fill="x")

        self.btn_manual = ctk.CTkButton(self.sidebar, text="  Manual IP", anchor="w", fg_color="#444", command=lambda: self.show_tab("manual"))
        self.btn_manual.pack(pady=5, padx=10, fill="x")

        # --- Main Area ---
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # --- TABS ---
        self.frames = {}
        self.create_dashboard()
        self.create_provisioner()
        self.create_manual_add()

        self.show_tab("dash")
        self.refresh_network()

    # ---------------------------------------------------------
    # UI CONSTRUCTION
    # ---------------------------------------------------------
    def create_dashboard(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["dash"] = frame
        
        # Header
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(head, text="Network Overview", font=("Roboto", 24)).pack(side="left")
        ctk.CTkButton(head, text="↻ Refresh Scan", width=120, command=self.refresh_network).pack(side="right")

        # Device List
        self.dev_list = ctk.CTkScrollableFrame(frame, label_text="Discovered Devices")
        self.dev_list.pack(fill="both", expand=True)

    def create_provisioner(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["prov"] = frame
        
        ctk.CTkLabel(frame, text="Device Provisioning", font=("Roboto", 24)).pack(anchor="w", pady=(0, 20))
        
        steps = (
            "1. Factory Reset Device (Hold button 10s)\n"
            "2. Connect PC to 'Wemo.Mini.XXX'\n"
            "3. Enter Home Wi-Fi details below\n"
            "4. Click Push Config"
        )
        ctk.CTkLabel(frame, text=steps, justify="left", font=("Consolas", 14), 
                     fg_color="#222", corner_radius=6, padx=15, pady=15).pack(fill="x", pady=10)

        self.ssid_entry = ctk.CTkEntry(frame, placeholder_text="SSID")
        self.ssid_entry.pack(fill="x", pady=10)
        self.pass_entry = ctk.CTkEntry(frame, placeholder_text="Password", show="*")
        self.pass_entry.pack(fill="x", pady=10)
        
        self.prov_btn = ctk.CTkButton(frame, text="Push Configuration", 
                                      fg_color="#28a745", hover_color="#1e7e34", height=50,
                                      command=self.run_provision_thread)
        self.prov_btn.pack(fill="x", pady=20)
        
        self.prov_log = ctk.CTkTextbox(frame, height=200)
        self.prov_log.pack(fill="x")

    def create_manual_add(self):
        frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["manual"] = frame
        ctk.CTkLabel(frame, text="Manual Direct Add", font=("Roboto", 24)).pack(anchor="w", pady=(0, 10))
        self.manual_ip = ctk.CTkEntry(frame, placeholder_text="e.g. 192.168.1.50")
        self.manual_ip.pack(fill="x", pady=10)
        ctk.CTkButton(frame, text="Probe IP Address", command=self.probe_manual_ip).pack(pady=10)

    # ---------------------------------------------------------
    # LOGIC & THREADING
    # ---------------------------------------------------------
    def show_tab(self, name):
        for key, frame in self.frames.items():
            frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    def log_prov(self, msg):
        self.prov_log.insert("end", f"> {msg}\n")
        self.prov_log.see("end")

    def refresh_network(self):
        for widget in self.dev_list.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.dev_list, text="Scanning...", text_color="yellow").pack(pady=20)
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            devices = pywemo.discover_devices()
            self.after(0, self.update_dashboard, devices)
        except Exception as e:
            print(e)

    def update_dashboard(self, devices):
        for widget in self.dev_list.winfo_children():
            widget.destroy()

        if not devices:
            ctk.CTkLabel(self.dev_list, text="No devices found via UPnP.").pack(pady=20)
            return

        for dev in devices:
            self.build_device_card(dev)

    def build_device_card(self, dev):
        try: mac = dev.mac
        except: mac = "Unknown"
        try: fw = dev.firmware_version
        except: fw = "Unknown"
        
        card = ctk.CTkFrame(self.dev_list, fg_color="#1a1a1a", border_width=1, border_color="#333")
        card.pack(fill="x", pady=5, padx=5)
        
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(top, text="⚡", font=("Arial", 20)).pack(side="left", padx=(0,10))
        ctk.CTkLabel(top, text=dev.name, font=("Roboto", 16, "bold")).pack(side="left")
        
        switch = ctk.CTkSwitch(top, text="Power", command=lambda d=dev: self.toggle_device(d))
        switch.pack(side="right")
        try:
            if dev.get_state(): switch.select()
        except: pass

        info_text = f"IP: {dev.host}  |  MAC: {mac}  |  FW: {fw}"
        
        bot = ctk.CTkFrame(card, fg_color="#111", corner_radius=4)
        bot.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(bot, text=info_text, font=("Consolas", 11), text_color="#aaa").pack(side="left", padx=10, pady=5)
        
        # --- NEW: Extract HomeKit Code Button ---
        def extract_hk():
            threading.Thread(target=self._extract_hk_task, args=(dev,), daemon=True).start()

        ctk.CTkButton(bot, text="Get HomeKit Code", width=120, height=20, font=("Arial", 10), 
                      fg_color="#555", hover_color="#666", command=extract_hk).pack(side="right", padx=5)

    def _extract_hk_task(self, dev):
        # The secret sauce: Querying the BasicEvent service
        try:
            if hasattr(dev, 'basicevent'):
                # This specific action is supported on some V2/V3 firmware
                data = dev.basicevent.GetHKSetupInfo()
                code = data.get('HKSetupCode')
                
                if code:
                    self.after(0, lambda: messagebox.showinfo("Success", f"HomeKit Code Found:\n\n{code}"))
                    pyperclip.copy(code)
                else:
                    self.after(0, lambda: messagebox.showwarning("Not Found", "Device returned empty HomeKit data."))
            else:
                self.after(0, lambda: messagebox.showerror("Error", "Device does not support BasicEvent service."))
        except Exception as e:
             self.after(0, lambda: messagebox.showerror("Failed", f"Could not retrieve HomeKit code.\n\nLikely unsupported firmware.\nError: {e}"))

    def toggle_device(self, dev):
        def _t(): dev.toggle()
        threading.Thread(target=_t, daemon=True).start()

    # --- PROVISIONING ---
    def run_provision_thread(self):
        ssid = self.ssid_entry.get()
        pwd = self.pass_entry.get()
        if not ssid: return
        self.prov_btn.configure(state="disabled", text="Running...")
        self.prov_log.delete("1.0", "end")
        threading.Thread(target=self._provision_task, args=(ssid, pwd), daemon=True).start()

    def _provision_task(self, ssid, pwd):
        self.log_prov("Scanning default gateways...")
        target_ips = ["10.22.22.1", "192.168.49.1", "192.168.1.1"]
        dev = None
        for ip in target_ips:
            try:
                url = pywemo.setup_url_for_address(ip)
                dev = pywemo.discovery.device_from_description(url)
                if dev: break
            except: pass
        
        if not dev:
            self.log_prov("ERROR: No device found in Setup Mode.")
            self.prov_btn.configure(state="normal", text="Push Configuration")
            return

        try:
            self.log_prov(f"Sending credentials for '{ssid}'...")
            dev.setup(ssid=ssid, password=pwd)
            self.log_prov("SUCCESS: Config sent. Device rebooting.")
        except Exception as e:
            self.log_prov(f"ERROR: {e}")
        self.prov_btn.configure(state="normal", text="Push Configuration")

    # --- MANUAL PROBE ---
    def probe_manual_ip(self):
        ip = self.manual_ip.get()
        if not ip: return
        def _probe():
            try:
                url = pywemo.setup_url_for_address(ip)
                dev = pywemo.discovery.device_from_description(url)
                if dev: self.after(0, self.build_device_card, dev)
            except Exception as e: messagebox.showerror("Failed", str(e))
        threading.Thread(target=_probe, daemon=True).start()

if __name__ == "__main__":
    app = WemoOpsApp()
    app.mainloop()