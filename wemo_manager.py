import customtkinter as ctk
import pywemo
import threading
from tkinter import messagebox

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class WemoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Wemo Local Manager")
        self.geometry("600x500")
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create Tabs
        self.tabview = ctk.CTkTabview(self, width=550, height=450)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_provision = self.tabview.add("Provision New Device")
        
        # --- DASHBOARD TAB ---
        self.setup_dashboard_tab()
        
        # --- PROVISION TAB ---
        self.setup_provision_tab()

    def setup_dashboard_tab(self):
        # Header
        self.dash_label = ctk.CTkLabel(self.tab_dashboard, text="Network Devices", font=("Roboto", 20, "bold"))
        self.dash_label.pack(pady=10)

        # Refresh Button
        self.refresh_btn = ctk.CTkButton(self.tab_dashboard, text="Scan Network", command=self.start_scan)
        self.refresh_btn.pack(pady=5)

        # Scrollable Area for Devices
        self.device_frame = ctk.CTkScrollableFrame(self.tab_dashboard, width=500, height=300)
        self.device_frame.pack(pady=10, fill="both", expand=True)
        
        # Status Bar
        self.status_label = ctk.CTkLabel(self.tab_dashboard, text="Ready", text_color="gray")
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
        self.status_label.configure(text="Scanning local network for WeMo devices...")
        
        # Run in thread to prevent freezing GUI
        threading.Thread(target=self.scan_devices, daemon=True).start()

    def scan_devices(self):
        try:
            devices = pywemo.discover_devices()
            self.update_device_list(devices)
        except Exception as e:
            print(f"Error: {e}")
        
        # Reset UI
        self.refresh_btn.configure(state="normal", text="Scan Network")
        self.status_label.configure(text=f"Scan complete.")

    def update_device_list(self, devices):
        # Clear old widgets
        for widget in self.device_frame.winfo_children():
            widget.destroy()

        if not devices:
            ctk.CTkLabel(self.device_frame, text="No devices found.").pack(pady=20)
            return

        for dev in devices:
            # Create a Row for each device
            row = ctk.CTkFrame(self.device_frame)
            row.pack(fill="x", pady=5, padx=5)
            
            # Icon/Name
            ctk.CTkLabel(row, text=f"{dev.name}", font=("Roboto", 14, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=f"({dev.host})", text_color="gray").pack(side="left")
            
            # Toggle Button logic
            def toggle(d=dev):
                self.toggle_state(d)

            btn = ctk.CTkButton(row, text="Toggle", width=80, command=toggle)
            btn.pack(side="right", padx=10, pady=10)

    def toggle_state(self, device):
        try:
            device.toggle()
            self.status_label.configure(text=f"Toggled {device.name}")
        except:
            self.status_label.configure(text=f"Failed to toggle {device.name}")

    # --- LOGIC: PROVISIONING ---
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
        
        # 1. Find Device
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

        # 2. Setup
        try:
            self.prov_status.configure(text=f"Found {device.name}. Sending credentials...")
            device.setup(ssid=ssid, password=password)
            self.prov_status.configure(text="Success! Device is rebooting.")
            messagebox.showinfo("Success", f"Credentials sent to {device.name}.\nConnect back to your main Wi-Fi and check the Dashboard.")
        except Exception as e:
            self.prov_status.configure(text=f"Error: {str(e)}")
        
        self.prov_btn.configure(state="normal")

if __name__ == "__main__":
    app = WemoApp()
    app.mainloop()