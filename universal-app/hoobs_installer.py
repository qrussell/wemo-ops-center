import sys
import os
import subprocess
import platform
import shutil
import urllib.request
import tempfile

def print_header():
    print("=======================================================")
    print("   Homebridge & Wemo Compatibility Layer Installer     ")
    print("   Cross-Platform Auto-Installer (Win / Mac / Linux)   ")
    print("=======================================================")

def refresh_paths():
    """Ensure standard Node.js installation paths are loaded in the current session."""
    if platform.system() == "Windows":
        os.environ["PATH"] += os.pathsep + r"C:\Program Files\nodejs"
    else:
        # Default install path for Mac pkg and Linux
        os.environ["PATH"] += os.pathsep + "/usr/local/bin"

def check_command(command):
    refresh_paths()
    return shutil.which(command) is not None

def run_command(command, shell=False, sudo=False):
    """Run a shell command safely across operating systems."""
    if sudo and sys.platform != "win32":
        if isinstance(command, list):
            command = ["sudo"] + command
        else:
            command = "sudo " + command
    
    cmd_str = " ".join(command) if isinstance(command, list) else command
    print(f"--> Running: {cmd_str}")
    
    try:
        subprocess.check_call(command, shell=shell)
        return True
    except subprocess.CalledProcessError:
        print(f"XXX Error running command.")
        return False

def auto_install_node():
    """Automatically downloads and installs the official Node.js binaries."""
    os_type = platform.system()
    print("\n[*] Node.js is missing. Starting Automated Installation...")
    temp_dir = tempfile.gettempdir()
    
    try:
        if os_type == "Windows":
            url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi"
            dest = os.path.join(temp_dir, "node_installer.msi")
            print(f"    Downloading Official Windows Installer...")
            urllib.request.urlretrieve(url, dest)
            print("    Running Installer (Please wait)...")
            run_command(["msiexec.exe", "/i", dest, "/passive"], shell=False)
            
        elif os_type == "Darwin": # macOS
            # Bypasses Homebrew entirely to avoid OS-version lockouts (Big Sur)
            url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0.pkg"
            dest = os.path.join(temp_dir, "node_installer.pkg")
            print(f"    Downloading Official Mac Installer (Bypassing Homebrew)...")
            urllib.request.urlretrieve(url, dest)
            print("    Running Apple Installer (Requires your Mac password)...")
            run_command(["installer", "-pkg", dest, "-target", "/"], shell=False, sudo=True)
            
        elif os_type == "Linux":
            print("    Running Official NodeSource Setup Script...")
            run_command("curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -", shell=True)
            run_command(["apt-get", "install", "-y", "nodejs"], shell=False, sudo=True)
            
    except Exception as e:
        print(f"[!] Auto-install failed: {e}")
        return False
        
    refresh_paths()
    return check_command("npm")

def main():
    print_header()
    os_type = platform.system()
    print(f"[*] Detected OS: {os_type}")
    
    # 1. Check & Auto-Install Node.js
    if not check_command("npm"):
        if not auto_install_node():
            print("\n[!] FATAL: Could not automatically install Node.js.")
            print("    Please install it manually from https://nodejs.org/")
            input("Press Enter to exit...")
            sys.exit(1)
    
    print("[*] Node.js (npm) is installed and ready.")

    # 2. Confirm Installation
    print("\nThis script will install:")
    print("  - Homebridge (Core Server)")
    print("  - Homebridge Config UI X (Dashboard)")
    print("  - homebridge-wemo (Wemo Plugin)")
    print("  - homebridge-alexa (Alexa Plugin)")
    
    confirm = input("\nProceed with installation? (y/n): ").lower().strip()
    if confirm != 'y':
        print("Aborted.")
        sys.exit(0)

    use_sudo = (os_type != "Windows")

    # 3. Install Homebridge & UI
    print("\n[*] Installing Homebridge Core & UI...")
    npm_cmd = ["npm", "install", "-g", "--unsafe-perm", "homebridge", "homebridge-config-ui-x"]
    if run_command(npm_cmd, shell=(os_type == "Windows"), sudo=use_sudo):
        print("[+] Core installed successfully.")
    else:
        print("[!] Failed to install Homebridge. Ensure you are running as Administrator/Root.")
        sys.exit(1)

    # 4. Install Plugins
    print("\n[*] Installing Plugins...")
    plugin_cmd = ["npm", "install", "-g", "homebridge-wemo", "homebridge-alexa"]
    if run_command(plugin_cmd, shell=(os_type == "Windows"), sudo=use_sudo):
        print("[+] Plugins installed.")
    else:
        print("[!] Plugin installation failed.")
        sys.exit(1)

    # 5. Service Setup
    print("\n[*] Setting up System Service...")
    
    # Pre-create the config directory to prevent ENOENT crashes on Mac/Linux
    homebridge_dir = os.path.expanduser("~/.homebridge")
    try:
        os.makedirs(homebridge_dir, exist_ok=True)
        print(f"[*] Ensured configuration directory exists: {homebridge_dir}")
    except Exception as e:
        print(f"[!] Warning: Could not create {homebridge_dir}: {e}")

    # Use exact path to hb-service if standard name fails
    hb_service_cmd = "hb-service" if check_command("hb-service") else "npx hb-service"
    
    if run_command([hb_service_cmd, "install"], shell=(os_type == "Windows"), sudo=use_sudo):
        print("[+] Service installed and started!")
    else:
        print("[!] Service setup failed. You may need to run 'sudo hb-service install' manually.")

    # 6. Final Instructions
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
    # Request Admin privileges on Windows before starting
    if platform.system() == "Windows":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Restarting as Administrator...")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()
    main()