import sys
import os
import subprocess
import platform
import shutil
import time

def print_header():
    print("=======================================================")
    print("   HOOBS / Homebridge Compatibility Layer Installer    ")
    print("   For Wemo Ops Center v5.2.5+                         ")
    print("=======================================================")

def check_command(command):
    """Check if a command exists in the system path."""
    return shutil.which(command) is not None

def run_command(command, shell=False, sudo=False):
    """Run a shell command and handle errors."""
    if sudo and sys.platform != "win32":
        command = ["sudo"] + command
    
    cmd_str = " ".join(command) if isinstance(command, list) else command
    print(f"--> Running: {cmd_str}")
    
    try:
        subprocess.check_call(command, shell=shell)
        return True
    except subprocess.CalledProcessError:
        print(f"XXX Error running: {cmd_str}")
        return False

def install_node_warning():
    print("\n[!] Node.js is NOT installed.")
    print("    This is required to run the Homebridge layer.")
    
    system = platform.system()
    if system == "Windows":
        print("    Please download and install the LTS version from:")
        print("    https://nodejs.org/en/download/")
    elif system == "Darwin": # macOS
        print("    Run: brew install node")
        print("    (Or download from nodejs.org)")
    elif system == "Linux":
        print("    Run: sudo apt install nodejs npm")
    
    print("\n    After installing Node.js, run this script again.")
    input("Press Enter to exit...")
    sys.exit(1)

def main():
    print_header()
    
    # 1. OS Detection
    os_type = platform.system()
    print(f"[*] Detected OS: {os_type}")
    
    # 2. Check Node.js
    if not check_command("npm"):
        install_node_warning()
    else:
        print("[*] Node.js (npm) is installed.")

    # 3. Confirm Installation
    print("\nThis script will install:")
    print("  - Homebridge (Core Server)")
    print("  - Homebridge Config UI X (Dashboard)")
    print("  - homebridge-platform-wemo (Wemo Plugin)")
    print("  - homebridge-alexa (Alexa Plugin)")
    
    confirm = input("\nProceed with installation? (y/n): ").lower().strip()
    if confirm != 'y':
        print("Aborted.")
        sys.exit(0)

    # 4. Install Homebridge & UI
    print("\n[*] Installing Homebridge Core & UI...")
    npm_cmd = ["npm", "install", "-g", "--unsafe-perm", "homebridge", "homebridge-config-ui-x"]
    
    # Windows doesn't need sudo for global npm if running as Admin, Mac/Linux usually do
    use_sudo = (os_type != "Windows")
    
    if run_command(npm_cmd, shell=(os_type == "Windows"), sudo=use_sudo):
        print("[+] Core installed successfully.")
    else:
        print("[!] Failed to install Homebridge. Ensure you are running as Administrator/Root.")
        sys.exit(1)

    # 5. Install Plugins
    print("\n[*] Installing Plugins...")
    plugins = ["homebridge-platform-wemo", "homebridge-alexa"]
    plugin_cmd = ["npm", "install", "-g"] + plugins
    
    if run_command(plugin_cmd, shell=(os_type == "Windows"), sudo=use_sudo):
        print("[+] Plugins installed.")
    else:
        print("[!] Plugin installation failed.")

    # 6. Service Setup
    print("\n[*] Setting up System Service...")
    service_cmd = ["hb-service", "install"]
    
    if run_command(service_cmd, shell=(os_type == "Windows"), sudo=use_sudo):
        print("[+] Service installed and started!")
    else:
        print("[!] Service setup failed. You may need to run 'hb-service install' manually.")

    # 7. Final Instructions
    print("\n" + "="*50)
    print("   INSTALLATION COMPLETE")
    print("="*50)
    print("1. Open your browser to: http://localhost:8581")
    print("2. Default User/Pass: admin / admin")
    print("3. Go to 'Plugins' and configure 'Homebridge Alexa'")
    print("4. Open Wemo Ops Center -> Integrations")
    print("5. Click 'Scan & Generate Config' and paste it into the Wemo Plugin settings.")
    print("="*50)
    input("\nPress Enter to close.")

if __name__ == "__main__":
    # Request Admin/Root on Windows if not present
    if platform.system() == "Windows":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Restarting as Administrator...")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()
            
    main()