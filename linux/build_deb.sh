#!/bin/bash

# --- CONFIGURATION ---
APP_NAME="WemoOps"
VERSION="4.1"
ARCH="amd64"  # Use 'arm64' if building on Raspberry Pi
MAINTAINER="Quentin Russell <your@email.com>"
DESC="Wemo Ops Center - Automation and Provisioning Tool"

# 1. SETUP PATHS
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Define where we will stage the files before zipping
STAGING_DIR="dist/deb_staging"
INSTALL_DIR="/opt/$APP_NAME"  # Where files live on the destination PC

echo "========================================="
echo "   WEMO OPS - DEBIAN PACKAGER (.DEB)     "
echo "========================================="

# 2. CHECK FOR BINARIES
# (We assume you already ran master_build_linux.sh)
if [ ! -f "dist/WemoOps_Installer/WemoOps" ]; then
    echo "ERROR: Compiled binaries not found!"
    echo "Please run './master_build_linux.sh' first."
    exit 1
fi

# 3. CLEANUP AND INIT DIRECTORY STRUCTURE
echo "[1/4] Creating Directory Structure..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/DEBIAN"
mkdir -p "$STAGING_DIR$INSTALL_DIR"                  # /opt/WemoOps
mkdir -p "$STAGING_DIR/usr/bin"                      # /usr/bin (for symlink)
mkdir -p "$STAGING_DIR/usr/share/applications"       # Desktop Shortcut
mkdir -p "$STAGING_DIR/usr/lib/systemd/user"         # Systemd Service (User level)

# 4. COPY FILES
echo "[2/4] Copying Files..."

# Copy Binaries to /opt/WemoOps/
cp "dist/WemoOps_Installer/WemoOps" "$STAGING_DIR$INSTALL_DIR/"
cp "dist/WemoOps_Installer/wemo_service" "$STAGING_DIR$INSTALL_DIR/"

# Create Symlink in /usr/bin so users can just type 'WemoOps'
# (We create the link relative to the staging root)
ln -s "$INSTALL_DIR/WemoOps" "$STAGING_DIR/usr/bin/$APP_NAME"

# Create Desktop Entry
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

# Create Systemd Service File
# Note: We install to /usr/lib/systemd/user/ so EVERY user gets this service available
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

# 5. CREATE CONTROL FILES
echo "[3/4] Generating Control Scripts..."

# The 'control' file tells dpkg what this package is
cat > "$STAGING_DIR/DEBIAN/control" <<EOF
Package: wemo-ops
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Description: $DESC
Depends: python3, python3-tk, network-manager, xclip
EOF

# The 'postinst' script runs AFTER installation
# We use it to set permissions and update the desktop database
cat > "$STAGING_DIR/DEBIAN/postinst" <<EOF
#!/bin/bash
chmod 755 $INSTALL_DIR/WemoOps
chmod 755 $INSTALL_DIR/wemo_service
update-desktop-database /usr/share/applications || true
echo "Wemo Ops installed successfully."
echo "Enable the background service by running: systemctl --user enable --now wemo_ops"
EOF
chmod 755 "$STAGING_DIR/DEBIAN/postinst"

# The 'prerm' script runs BEFORE removal
cat > "$STAGING_DIR/DEBIAN/prerm" <<EOF
#!/bin/bash
# Stop service if running (ignoring errors if not active)
systemctl --user stop wemo_ops 2>/dev/null || true
systemctl --user disable wemo_ops 2>/dev/null || true
rm -f /usr/bin/$APP_NAME
EOF
chmod 755 "$STAGING_DIR/DEBIAN/prerm"

# 6. BUILD THE PACKAGE
echo "[4/4] Building .deb Package..."
dpkg-deb --build "$STAGING_DIR" "dist/${APP_NAME}_${VERSION}_${ARCH}.deb"

echo "========================================="
echo "   SUCCESS! Package Ready:"
echo "   dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "========================================="
