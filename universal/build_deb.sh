#!/bin/bash

# --- CONFIGURATION ---
APP_NAME="WemoOps"
VERSION="4.2.6"  # Incremented version for the font update
ARCH="amd64"     # Use 'arm64' if building on Raspberry Pi
MAINTAINER="Quentin Russell <quentin@quentinrussell.com>"
DESC="Wemo Ops Center - Automation and Provisioning Tool"
MAIN_SCRIPT="wemo_ops_universal.py"
SERVICE_SCRIPT="wemo_service_universal.py"

# 1. SETUP PATHS
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Define where we will stage the files before zipping
STAGING_DIR="dist/deb_staging"
INSTALL_DIR="/opt/$APP_NAME"  # Where files live on the destination PC

echo "========================================="
echo "   WEMO OPS - DEBIAN PACKAGER (.DEB)     "
echo "   Version: $VERSION"
echo "========================================="

# 2. INSTALL BUILD DEPENDENCIES
echo "[1/5] Checking Build Tools..."
if [ -f /etc/debian_version ]; then
    sudo apt-get update -qq
    # Added build-essential and binutils for PyInstaller
    sudo apt-get install -y python3-venv python3-pip python3-tk xclip build-essential binutils
fi

# 3. SETUP VIRTUAL ENVIRONMENT & COMPILE
echo "[2/5] Compiling Binaries..."

if [ -d ".venv" ]; then rm -rf .venv; fi
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install "pywemo>=2.1.1" customtkinter requests pyinstaller pyperclip pystray Pillow

# Clean old builds
rm -rf build/ dist/

# Build GUI
echo "   > Compiling GUI..."
pyinstaller --noconfirm --onefile --windowed \
    --name "$APP_NAME" \
    --collect-all customtkinter \
    --hidden-import pywemo \
    --hidden-import pyperclip \
    --hidden-import pystray \
    --hidden-import PIL \
    "$MAIN_SCRIPT"

# Build Service
echo "   > Compiling Service..."
pyinstaller --noconfirm --onefile --noconsole \
    --name "wemo_service" \
    --hidden-import pywemo \
    --hidden-import pystray \
    --hidden-import PIL \
    "$SERVICE_SCRIPT"

deactivate

# 4. PREPARE DIRECTORY STRUCTURE
echo "[3/5] Creating Package Structure..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/DEBIAN"
mkdir -p "$STAGING_DIR$INSTALL_DIR"                  # /opt/WemoOps
mkdir -p "$STAGING_DIR/usr/bin"                      # /usr/bin (for symlink)
mkdir -p "$STAGING_DIR/usr/share/applications"       # Desktop Shortcut
mkdir -p "$STAGING_DIR/usr/lib/systemd/user"         # Systemd Service

# 5. COPY FILES
echo "[4/5] Copying Files..."

# Binaries
if [ -f "dist/$APP_NAME" ]; then
    cp "dist/$APP_NAME" "$STAGING_DIR$INSTALL_DIR/"
else
    echo "ERROR: GUI Binary missing!"
    exit 1
fi

if [ -f "dist/wemo_service" ]; then
    cp "dist/wemo_service" "$STAGING_DIR$INSTALL_DIR/"
else
    echo "ERROR: Service Binary missing!"
    exit 1
fi

# Copy Images (Icon) if available
if [ -f "images/app_icon.ico" ]; then
    mkdir -p "$STAGING_DIR$INSTALL_DIR/images"
    cp "images/app_icon.ico" "$STAGING_DIR$INSTALL_DIR/images/"
fi

# --- NEW: Copy Local Fonts (If you have a fonts/ folder) ---
if [ -d "fonts" ]; then
    echo "   > Bundling local fonts..."
    mkdir -p "$STAGING_DIR$INSTALL_DIR/fonts"
    cp -r "fonts/"* "$STAGING_DIR$INSTALL_DIR/fonts/"
fi
# ---------------------------------------------------------

# Symlink
ln -s "$INSTALL_DIR/$APP_NAME" "$STAGING_DIR/usr/bin/$APP_NAME"

# Desktop Shortcut
cat > "$STAGING_DIR/usr/share/applications/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Wemo Ops Center
Comment=Manage and Automate Wemo Devices
Exec=/usr/bin/$APP_NAME
Icon=utilities-terminal
Terminal=false
Categories=Utility;Network;
EOF

# Systemd Service
cat > "$STAGING_DIR/usr/lib/systemd/user/wemo_ops.service" <<EOF
[Unit]
Description=Wemo Ops Automation Service
After=network.target

[Service]
ExecStart=$INSTALL_DIR/wemo_service
Restart=on-failure
StandardOutput=null
StandardError=journal

[Install]
WantedBy=default.target
EOF

# Control File
# --- UPDATED DEPENDENCIES FOR FONTS ---
cat > "$STAGING_DIR/DEBIAN/control" <<EOF
Package: wemo-ops
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Description: $DESC
Depends: python3, python3-tk, xclip, fonts-liberation, fonts-noto, fontconfig
EOF

# Post-Install Script
cat > "$STAGING_DIR/DEBIAN/postinst" <<EOF
#!/bin/bash
chmod 755 $INSTALL_DIR/$APP_NAME
chmod 755 $INSTALL_DIR/wemo_service
# Refresh font cache if we copied new ones
if [ -d "$INSTALL_DIR/fonts" ]; then
    fc-cache -f -v >/dev/null 2>&1 || true
fi
update-desktop-database /usr/share/applications || true
echo "Wemo Ops installed successfully."
echo "Enable the background service: systemctl --user enable --now wemo_ops"
EOF
chmod 755 "$STAGING_DIR/DEBIAN/postinst"

# Pre-Remove Script
cat > "$STAGING_DIR/DEBIAN/prerm" <<EOF
#!/bin/bash
systemctl --user stop wemo_ops 2>/dev/null || true
systemctl --user disable wemo_ops 2>/dev/null || true
rm -f /usr/bin/$APP_NAME
EOF
chmod 755 "$STAGING_DIR/DEBIAN/prerm"

# 6. BUILD PACKAGE
echo "[5/5] Building .deb Package..."
dpkg-deb --build "$STAGING_DIR" "dist/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo "========================================="
echo "   SUCCESS! Package Ready:"
echo "   dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "========================================="
