import customtkinter as ctk
import pywemo
import threading
from tkinter import messagebox

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class WemoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Wemo Manager & Info Tool")
        self.geometry("700x600")
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create Tabs
        self.tabview = ctk.CTkTabview(self, width=650, height=550)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_provision = self.tabview.add("Provision New Device")
        
        # --- DASHBOARD TAB ---
        self.setup_dashboard_tab()
        
        # --- PROVISION TAB ---
        self.setup_provision_tab()

    def setup_dashboard_tab(self):
        # Header
        header_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        header_frame.pack(fill="x", pady=10)
        
        self.dash_label = ctk.CTkLabel(header_frame, text="Network Devices", font=("Roboto", 20, "bold"))
        self.dash_label.pack(side="left", padx=10)

        # Refresh Button
        self.refresh_btn = ctk.CTkButton(header_frame, text="Scan Network", width=100, command=self.start_scan)
        self.refresh_btn.pack(side="right", padx=10)

        # Scrollable Area for Devices
        self.device_frame = ctk.CTkScrollableFrame(self.tab_dashboard, width=600, height=400)
        self.device_frame.pack(pady=10, fill="both", expand=True)
        
        # Status Bar
        self.status_label = ctk.CTkLabel(self.tab_dashboard, text="Ready to scan.", text_color="gray")
        self.status_label.pack(side="bottom", pady=5)

    def setup_provision_tab(self):
        # Instructions
        info_text = (
            "1. Factory reset your Wemo device (Hold button 5-10s).\n"
            "2. Connect THIS computer to the 'Wemo.Mini.XXX' Wi-Fi.\n"
            "3. Enter your Home Wi-Fi details below.\n"
            "4. Click 'Push Credentials'."
        )
        self.info_label = ctk.CTkLabel(self.tab_provision, text=info_text, justify="left", font=("Roboto", 14))
        self.info_label.pack(pady=20, padx=20)

        # Inputs
        self.ssid_entry = ctk.CTkEntry(self.tab_provision, placeholder_text="Home Wi-Fi Name (SSID)")
        self.ssid_entry.pack(pady=10, fill="x", padx=50)

        self.pass_entry = ctk.CTkEntry(self.tab_provision, placeholder_text="Home Wi-Fi Password", show="*")
        self.pass_entry.pack(pady=10, fill="x", padx=50)

        # Action Button
        self.prov_btn = ctk.CTkButton(self.tab_provision, text="Push Credentials to Wemo", fg_color="#28a745", hover_color="#218838", command=self.start_provision)
        self.prov_btn.pack(pady=20)
        
        self.prov_status = ctk.CTkLabel(self.tab_provision, text="Waiting...", text_color="gray")
        self.prov_status.pack(pady=5)

    # --- LOGIC: DASHBOARD ---
    def start_scan(self):
        self.refresh_btn.configure(state="disabled", text="Scanning...")
        self.status_label.configure(text="Scanning local network for WeMo devices (UDP Discovery)...")
        threading.Thread(target=self.scan_devices, daemon=True).start()

    def scan_devices(self):
        try:
            # Force a fresh discovery
            devices = pywemo.discover_devices()
            self.update_device_list(devices)
        except Exception as e:
            print(f"Error: {e}")
            self.status_label.configure(text=f"Scan Error: {e}")
        
        self.refresh_btn.configure(state="normal", text="Scan Network")
        if hasattr(self, 'scan_complete_msg'):
            self.status_label.configure(text=self.scan_complete_msg)

    def update_device_list(self, devices):
        # Clear old widgets
        for widget in self.device_frame.winfo_children():
            widget.destroy()

        if not devices:
            ctk.CTkLabel(self.device_frame, text="No devices found on this subnet.").pack(pady=20)
            self.scan_complete_msg = "No devices found."
            return

        self.scan_complete_msg = f"Found {len(devices)} device(s)."

        for dev in devices:
            self.create_device_row(dev)

    def create_device_row(self, dev):
        # Main Card Frame
        card = ctk.CTkFrame(self.device_frame, fg_color="#1a1a1a", border_width=1, border_color="#333")
        card.pack(fill="x", pady=5, padx=5)
        
        # --- Top Row: Name and Controls ---
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=5)
        
        name_lbl = ctk.CTkLabel(top_row, text=f"{dev.name}", font=("Roboto", 16, "bold"))
        name_lbl.pack(side="left")
        
        # Toggle Button
        toggle_btn = ctk.CTkButton(top_row, text="Toggle Power", width=100, height=25, 
                                 command=lambda d=dev: self.toggle_state(d))
        toggle_btn.pack(side="right")

        # --- Details Row: Technical Specs ---
        # We construct a formatted string with technical data
        try:
            mac_addr = dev.mac 
        except: 
            mac_addr = "Unknown"
            
        details_text = (
            f"IP: {dev.host}\n"
            f"MAC: {mac_addr}\n"
            f"Model: {dev.model_name}\n"
            f"Serial: {dev.serialnumber}\n"
            f"Firmware: {dev.firmware_version}\n"
            f"HomeKit Code: [See Physical Sticker]" 
        )

        # A read-only textbox allows the user to copy/paste the data
        details_box = ctk.CTkTextbox(card, height=110, fg_color="#111", text_color="#ccc", font=("Consolas", 12))
        details_box.insert("0.0", details_text)
        details_box.configure(state="disabled") # Make read-only
        details_box.pack(fill="x", padx=10, pady=(0, 10))

    def toggle_state(self, device):
        def _task():
            try:
                device.toggle()
                self.status_label.configure(text=f"Toggled {device.name}")
            except Exception as e:
                self.status_label.configure(text=f"Failed: {e}")
        threading.Thread(target=_task, daemon=True).start()

    # --- LOGIC: PROVISIONING (Same as before) ---
    def start_provision(self):
        ssid = self.ssid_entry.get()
        password = self.pass_entry.get()
        
        if not ssid:
            messagebox.showerror("Error", "Please enter a Wi-Fi SSID.")
            return

        self.prov_btn.configure(state="disabled")
        self.prov_status.configure(text="Looking for setup AP (10.22.22.1 / 192.168.49.1)...")
        threading.Thread(target=self.run_provision, args=(ssid, password), daemon=True).start()

    def run_provision(self, ssid, password):
        target_ips = ["10.22.22.1", "192.168.49.1", "192.168.1.1"]
        device = None
        
        for ip in target_ips:
            try:
                url = pywemo.setup_url_for_address(ip)
                device = pywemo.discovery.device_from_description(url)
                if device:
                    break
            except:
                continue
        
        if not device:
            self.prov_status.configure(text="Error: Could not find Wemo in setup mode.")
            self.prov_btn.configure(state="normal")
            return

        try:
            self.prov_status.configure(text=f"Found {device.name}. Sending credentials...")
            device.setup(ssid=ssid, password=password)
            self.prov_status.configure(text="Success! Device is rebooting.")
            messagebox.showinfo("Success", f"Sent credentials to {device.name}.\n\nIt will now reboot and join '{ssid}'.")
        except Exception as e:
            self.prov_status.configure(text=f"Error: {str(e)}")
        
        self.prov_btn.configure(state="normal")

if __name__ == "__main__":
    app = WemoApp()
    app.mainloop()