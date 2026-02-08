#!/bin/bash

# Configuration
APP_NAME="wemo-ops-server"
VERSION="1.0.1"
ARCH="amd64"
MAINTAINER="Quentin Russell <qrussell@example.com>"
DESC="Headless Wemo Automation Server with Web UI"
BUILD_DIR="build_deb_server"

# Clean previous build
echo "--- Cleaning up ---"
rm -rf $BUILD_DIR
rm -f ${APP_NAME}_${VERSION}_${ARCH}.deb

# Create directory structure
echo "--- Creating directory structure ---"
mkdir -p $BUILD_DIR/DEBIAN
mkdir -p $BUILD_DIR/opt/WemoOpsServer
mkdir -p $BUILD_DIR/usr/bin
mkdir -p $BUILD_DIR/etc/systemd/system

# 1. Install Dependencies locally (Bundling them makes the DEB robust)
echo "--- Bundling Python dependencies ---"
# We install these into a 'libs' folder inside the package so the user doesn't need to pip install
pip3 install flask waitress schedule requests ifaddr --target $BUILD_DIR/opt/WemoOpsServer/libs --upgrade

# 2. Copy Application Files
echo "--- Copying application files ---"
cp wemo_server.py $BUILD_DIR/opt/WemoOpsServer/
# If you have templates (HTML) or static files, uncomment these:
# cp -r templates $BUILD_DIR/opt/WemoOpsServer/
# cp -r static $BUILD_DIR/opt/WemoOpsServer/

# 3. Create the Launcher Script
# This wrapper script tells Python where to find our bundled libraries
cat > $BUILD_DIR/usr/bin/$APP_NAME <<EOF
#!/bin/bash
export PYTHONPATH=\$PYTHONPATH:/opt/WemoOpsServer/libs
exec python3 /opt/WemoOpsServer/wemo_server.py "\$@"
EOF
chmod +x $BUILD_DIR/usr/bin/$APP_NAME

# 4. Create Systemd Service File
cat > $BUILD_DIR/etc/systemd/system/wemo-web.service <<EOF
[Unit]
Description=Wemo Ops Web Server
After=network.target

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/bin/$APP_NAME
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 5. Create Control File (Package Metadata)
cat > $BUILD_DIR/DEBIAN/control <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Depends: python3
Description: $DESC
 A headless server to manage Belkin Wemo devices via a Web UI.
 Includes automated scheduling and device discovery.
EOF

# 6. Create Post-Install Script (Permissions & Systemd reload)
cat > $BUILD_DIR/DEBIAN/postinst <<EOF
#!/bin/bash
# Set permissions
chmod -R 755 /opt/WemoOpsServer
chmod +x /usr/bin/$APP_NAME

# Reload systemd to recognize the new service
systemctl daemon-reload

echo "------------------------------------------------"
echo "✅ Wemo Ops Server installed!"
echo "To start the service, run:"
echo "  sudo systemctl enable --now wemo-web"
echo "------------------------------------------------"
EOF
chmod 755 $BUILD_DIR/DEBIAN/postinst

# 7. Create Pre-Remove Script (Stop service before uninstall)
cat > $BUILD_DIR/DEBIAN/prerm <<EOF
#!/bin/bash
systemctl stop wemo-web
systemctl disable wemo-web
EOF
chmod 755 $BUILD_DIR/DEBIAN/prerm

# 8. Build the Package
echo "--- Building .deb package ---"
dpkg-deb --build $BUILD_DIR ${APP_NAME}_${VERSION}_${ARCH}.deb

echo "🎉 Build Complete: ${APP_NAME}_${VERSION}_${ARCH}.deb"

