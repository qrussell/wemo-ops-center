#!/bin/bash

# ==============================================================================
#  WEMO OPS - MASTER BUILDER (DEB / Debian / Ubuntu / Raspberry Pi)
#  Version: 5.2.3-Stable
# ==============================================================================

# --- CRITICAL: Stop immediately if any command fails ---
set -e

# --- CONFIGURATION ---
APP_NAME="WemoOps"
SAFE_NAME="wemo-ops"
VERSION="5.2.3-2"
ARCH="amd64"     # Change to 'arm64' if building on Raspberry Pi
MAINTAINER="Quentin Russell <quentin@quentinrussell.com>"
DESC="Wemo Ops Center - Automation Server and Client"
CLIENT_SCRIPT="wemo_ops_universal.py"
SERVER_SCRIPT="wemo_server.py"

# 1. SETUP PATHS
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Define where we will stage the files before zipping
STAGING_DIR="dist/deb_staging"
INSTALL_DIR="/opt/$APP_NAME"

echo "========================================="
echo "   WEMO OPS - DEB PACKAGER               "
echo "   Version: $VERSION"
echo "========================================="

# 2. INSTALL BUILD DEPENDENCIES
echo "[1/6] Checking Build Tools..."
if [ -f /etc/debian_version ]; then
    if ! command -v dpkg-deb &> /dev/null; then
        echo "❌ Error: dpkg-deb not found."
        exit 1
    fi
fi

# 3. COMPILE BINARIES
echo "[2/6] Compiling Binaries..."

if [ -d ".venv" ]; then rm -rf .venv; fi

# Create Virtual Env
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "   > Installing Python libraries..."
pip install --upgrade pip --quiet
pip install "pywemo>=2.1.1" customtkinter requests pyinstaller pyperclip Pillow flask qrcode waitress --quiet

# Clean previous builds
rm -rf build/ dist/

# A. Build Client (GUI)
echo "   > Compiling Client ($CLIENT_SCRIPT)..."
pyinstaller --noconfirm --onefile --windowed \
    --name "wemo-ops-client" \
    --collect-all customtkinter \
    --collect-all pillow \
    --hidden-import pywemo \
    --hidden-import pyperclip \
    --hidden-import qrcode \
    --hidden-import PIL \
    --hidden-import PIL._tkinter_finder \
    --hidden-import PIL.ImageTk \
    "$CLIENT_SCRIPT" >/dev/null

# B. Build Server (Service)
echo "   > Compiling Server ($SERVER_SCRIPT)..."
pyinstaller --noconfirm --onefile --noconsole \
    --name "wemo-ops-server" \
    --hidden-import pywemo \
    --hidden-import flask \
    --hidden-import waitress \
    "$SERVER_SCRIPT" >/dev/null

deactivate

# Verify binaries
if [ ! -f "dist/wemo-ops-client" ] || [ ! -f "dist/wemo-ops-server" ]; then
    echo "❌ ERROR: Compilation failed. Binaries missing."
    exit 1
fi

# 4. PREPARE DIRECTORY STRUCTURE
echo "[3/6] Creating Package Structure..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/DEBIAN"
mkdir -p "$STAGING_DIR$INSTALL_DIR"
mkdir -p "$STAGING_DIR$INSTALL_DIR/images"
mkdir -p "$STAGING_DIR/usr/bin"
mkdir -p "$STAGING_DIR/usr/share/applications"
mkdir -p "$STAGING_DIR/usr/lib/systemd/system"

# 5. COPY FILES
echo "[4/6] Copying Files..."

# Copy Binaries
cp "dist/wemo-ops-client" "$STAGING_DIR$INSTALL_DIR/"
cp "dist/wemo-ops-server" "$STAGING_DIR$INSTALL_DIR/"

# Copy Icon
if [ -f "images/app_icon.ico" ]; then
    cp "images/app_icon.ico" "$STAGING_DIR$INSTALL_DIR/images/"
fi

# --- A. CLIENT WRAPPER ---
cat > "$STAGING_DIR/usr/bin/wemo-ops" <<WRAPPER
#!/bin/bash
export XLIB_SKIP_ARGB_VISUALS=1
exec $INSTALL_DIR/wemo-ops-client "\$@"
WRAPPER
chmod 755 "$STAGING_DIR/usr/bin/wemo-ops"

# --- B. SERVER SYMLINK ---
ln -s "$INSTALL_DIR/wemo-ops-server" "$STAGING_DIR/usr/bin/wemo-server"

# --- C. DESKTOP SHORTCUT ---
cat > "$STAGING_DIR/usr/share/applications/$SAFE_NAME.desktop" <<ENTRY
[Desktop Entry]
Type=Application
Name=Wemo Ops Center
Comment=Wemo Automation Dashboard
Exec=/usr/bin/wemo-ops
Icon=utilities-terminal
Terminal=false
Categories=Utility;Network;
ENTRY

# --- D. SYSTEMD SERVICE ---
cat > "$STAGING_DIR/usr/lib/systemd/system/wemo-ops-server.service" <<SERVICE
[Unit]
Description=Wemo Ops Automation Server
After=network.target

[Service]
ExecStart=$INSTALL_DIR/wemo-ops-server
WorkingDirectory=$INSTALL_DIR
Restart=always
User=root
# Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE

# --- E. CONTROL FILE ---
SIZE=$(du -s "$STAGING_DIR" | cut -f1)

cat > "$STAGING_DIR/DEBIAN/control" <<CTRL
Package: $SAFE_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Installed-Size: $SIZE
Depends: python3, python3-tk, fontconfig
Description: $DESC
 Wemo Ops is a complete automation suite for Belkin Wemo devices.
CTRL

# --- F. POST INSTALL SCRIPT (THE FIX) ---
cat > "$STAGING_DIR/DEBIAN/postinst" <<POST
#!/bin/bash
set -e

# 1. Fix Permissions
chmod 755 $INSTALL_DIR/wemo-ops-client
chmod 755 $INSTALL_DIR/wemo-ops-server

# 2. Update Desktop Database
if command -v update-desktop-database > /dev/null; then
    update-desktop-database /usr/share/applications
fi

# 3. SERVICE AUTO-START (Critical Fix)
# We check if systemd is running (to avoid errors in docker/chroot builds)
if [ -d /run/systemd/system ]; then
    echo "⚙️  Configuring Systemd Service..."
    systemctl daemon-reload
    systemctl enable wemo-ops-server
    systemctl restart wemo-ops-server
    echo "✅ Service Started."
fi

# 4. FIREWALL AUTO-CONFIG (UFW)
if command -v ufw > /dev/null; then
    if ufw status | grep -q "Status: active"; then
        echo "🔥 Configuring UFW Firewall..."
        ufw allow 5000/tcp comment 'WemoOps Web UI'
        ufw allow 5050/tcp comment 'WemoOps Web UI Alt'
        ufw allow 1900/udp comment 'Wemo SSDP Discovery'
        ufw allow 49152:49155/tcp comment 'Wemo Control Ports'
        ufw reload
        echo "✅ Firewall Rules Applied."
    fi
fi

echo "--------------------------------------------------------"
echo "✅ Wemo Ops installed successfully!"
echo "   Server is running at http://localhost:5050"
echo "--------------------------------------------------------"
POST
chmod 755 "$STAGING_DIR/DEBIAN/postinst"

# --- G. PRE REMOVE SCRIPT ---
cat > "$STAGING_DIR/DEBIAN/prerm" <<PRE
#!/bin/bash
# Stop service before uninstall
if [ -d /run/systemd/system ]; then
    systemctl stop wemo-ops-server 2>/dev/null || true
    systemctl disable wemo-ops-server 2>/dev/null || true
fi
PRE
chmod 755 "$STAGING_DIR/DEBIAN/prerm"

# 6. BUILD PACKAGE
echo "[6/6] Building .deb Package..."
dpkg-deb --build "$STAGING_DIR" "dist/${SAFE_NAME}_${VERSION}_${ARCH}.deb"

echo ""
echo "========================================="
echo "   SUCCESS! Package Ready:"
ls dist/*.deb
echo "========================================="
