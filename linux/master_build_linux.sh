#!/bin/bash

# 1. SETUP CORRECT DIRECTORY CONTEXT
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================="
echo "   WEMO OPS - UNIVERSAL BUILDER (LINUX)  "
echo "   Working Directory: $SCRIPT_DIR"
echo "========================================="

# 2. DETECT OS AND INSTALL DEPENDENCIES
echo "[1/5] Checking OS and Dependencies..."

if [ -f /etc/redhat-release ]; then
    # --- ROCKY LINUX / RHEL / FEDORA ---
    echo "   > Detected RHEL-based system (Rocky/CentOS/Fedora)."
    echo "   > Using DNF package manager..."
    
    # Check for EPEL (Crucial for xclip)
    if ! dnf repolist | grep -q "epel"; then
        echo "WARNING: EPEL repository not found. 'xclip' might fail to install."
        echo "Please run: sudo dnf install epel-release"
    fi

    sudo dnf install -y python3 python3-devel python3-tkinter python3-pip NetworkManager xclip gcc

elif [ -f /etc/debian_version ]; then
    # --- UBUNTU / DEBIAN / MINT ---
    echo "   > Detected Debian-based system (Ubuntu/Mint/Kali)."
    echo "   > Using APT package manager..."
    
    sudo apt-get update
    sudo apt-get install -y python3-tk python3-venv python3-pip network-manager xclip build-essential

else
    echo "ERROR: Unsupported Linux Distribution."
    exit 1
fi

# 3. SETUP VIRTUAL ENVIRONMENT
echo "[2/5] Setting up Isolated Build Environment..."

# Clean old env if exists to prevent conflicts
if [ -d ".venv" ]; then
    rm -rf .venv
fi

python3 -m venv .venv
source .venv/bin/activate

echo "   > Installing Python libraries..."
pip install --upgrade pip
# Wheel is often needed on Rocky for compiling
pip install wheel 
pip install pyinstaller customtkinter pywemo requests pyperclip

# 4. BUILD BINARIES
echo "[3/5] Building Binaries..."

rm -rf build/ dist/ *.spec

# Build GUI
echo "   > Compiling GUI..."
pyinstaller --noconfirm --onefile --windowed \
    --name "WemoOps" \
    --distpath ./dist \
    --workpath ./build \
    --collect-all customtkinter \
    --hidden-import pywemo \
    --hidden-import pyperclip \
    wemo_ops_linux.py

# Build Service
echo "   > Compiling Service..."
pyinstaller --noconfirm --onefile --noconsole \
    --name "wemo_service" \
    --distpath ./dist \
    --workpath ./build \
    --hidden-import pywemo \
    wemo_service_linux.py

deactivate

# 5. ORGANIZE INSTALLER
echo "[4/5] Organizing Installer Files..."
INSTALLER_DIR="$SCRIPT_DIR/dist/WemoOps_Installer"
mkdir -p "$INSTALLER_DIR"

if [ -f "dist/WemoOps" ]; then
    mv dist/WemoOps "$INSTALLER_DIR/"
else
    echo "ERROR: WemoOps binary failed to build."
    exit 1
fi

if [ -f "dist/wemo_service" ]; then
    mv dist/wemo_service "$INSTALLER_DIR/"
else
    echo "ERROR: wemo_service binary failed to build."
    exit 1
fi

# 6. CREATE INSTALL SCRIPT
echo "[5/5] Creating Install Script..."

cat > "$INSTALLER_DIR/install.sh" <<'EOF'
#!/bin/bash
APP_DIR="$HOME/.local/share/WemoOps"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
SYSTEMD_DIR="$HOME/.config/systemd/user"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing Wemo Ops..."

# 1. Create Directories
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$SYSTEMD_DIR"

# 2. Install Binaries
cp "$DIR/WemoOps" "$BIN_DIR/"
cp "$DIR/wemo_service" "$APP_DIR/"
chmod +x "$BIN_DIR/WemoOps"
chmod +x "$APP_DIR/wemo_service"

# 3. Create Desktop Shortcut
cat > "$DESKTOP_DIR/WemoOps.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Wemo Ops Center
Exec=$BIN_DIR/WemoOps
Icon=utilities-terminal
Terminal=false
Categories=Utility;
DESKTOP

# Note: update-desktop-database might not be in path on minimal installs, silencing errors
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# 4. Create Systemd Service
cat > "$SYSTEMD_DIR/wemo_ops.service" <<SERVICE
[Unit]
Description=Wemo Ops Automation Service
After=network.target

[Service]
ExecStart=$APP_DIR/wemo_service
Restart=on-failure
StandardOutput=null
StandardError=journal

[Install]
WantedBy=default.target
SERVICE

# 5. Enable Service
systemctl --user daemon-reload
systemctl --user enable --now wemo_ops.service

echo "=========================================="
echo "Success! Installation Complete."
echo "Note: If the app doesn't appear in your menu immediately,"
echo "you may need to log out and log back in."
echo "=========================================="
EOF

chmod +x "$INSTALLER_DIR/install.sh"

echo "========================================="
echo "   BUILD COMPLETE"
echo "========================================="
