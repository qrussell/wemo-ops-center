#!/bin/bash

# ==============================================================================
#  WEMO OPS - MASTER BUILDER (Apple Silicon / Modern macOS Edition)
#  Version: 5.3.0
# ==============================================================================

set -e

APP_NAME="WemoOps"
VERSION="5.3.0"
CLIENT_SCRIPT="wemo_ops_universal.py"
SERVER_SCRIPT="wemo_server.py"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================="
echo "   WEMO OPS - MAC PACKAGER (.DMG)        "
echo "   Architecture: Native / Apple Silicon  "
echo "========================================="

# 1. CHECK TOOLS
if ! command -v python3 &> /dev/null; then echo "❌ ERROR: python3 not found."; exit 1; fi
if ! command -v hdiutil &> /dev/null; then echo "❌ ERROR: hdiutil not found."; exit 1; fi

# 2. SETUP ENV
echo "[1/4] Setting up Virtual Environment..."
if [ -d ".venv_mac" ]; then rm -rf ".venv_mac"; fi
python3 -m venv ".venv_mac"
source ".venv_mac/bin/activate"

echo "   > Installing Libraries..."
pip install --upgrade pip --quiet
pip install "pywemo>=2.1.1" customtkinter requests pyinstaller pyperclip Pillow flask qrcode waitress --quiet

# 3. CLEANUP
rm -rf build/ dist/

# 4. COMPILE
echo "[2/4] Compiling Binaries..."

ICON_FLAG=""
ADD_DATA_FLAG=""
if [ -f "images/WemoOpsCenter.icns" ]; then
    ICON_FLAG="--icon=images/WemoOpsCenter.icns"
    ADD_DATA_FLAG="--add-data images/WemoOpsCenter.icns:."
elif [ -f "images/app_icon.ico" ]; then
    ICON_FLAG="--icon=images/app_icon.ico"
    ADD_DATA_FLAG="--add-data images/app_icon.ico:."
fi

# A. Build Server FIRST
echo "   > Building Service Binary..."
pyinstaller --noconfirm --noconsole --onefile --clean \
    --name "wemo_service" \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --hidden-import pywemo \
    --hidden-import flask \
    --hidden-import waitress \
    "$SERVER_SCRIPT" >/dev/null

# B. Build Client SECOND and intelligently inject Server
echo "   > Building GUI App..."
pyinstaller --noconfirm --windowed --clean \
    --name "$APP_NAME" \
    $ICON_FLAG \
    $ADD_DATA_FLAG \
    --add-binary "dist/wemo_service:." \
    --collect-all customtkinter \
    --collect-all pillow \
    --hidden-import pywemo \
    --hidden-import pyperclip \
    --hidden-import qrcode \
    --hidden-import PIL \
    --hidden-import PIL._tkinter_finder \
    --hidden-import PIL.ImageTk \
    "$CLIENT_SCRIPT" >/dev/null

deactivate

# 5. PACKAGE
echo "[3/4] Packaging DMG..."
STAGING="dist/dmg_staging"
mkdir -p "$STAGING/Service_Binary"

cp -R "dist/$APP_NAME.app" "$STAGING/"
# We still want a loose copy of the service to register as a system background daemon
cp "dist/wemo_service" "$STAGING/Service_Binary/"

cat > "$STAGING/Install_WemoOps.command" <<EOF
#!/bin/bash
DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
APP_NAME="$APP_NAME"

echo "==============================================="
echo "   Installing \$APP_NAME for macOS..."
echo "==============================================="

echo "System administrator password is required to install and bypass Gatekeeper."
sudo -v

echo "[1/3] Copying App to /Applications..."
sudo rm -rf "/Applications/\$APP_NAME.app"
sudo cp -R "\$DIR/\$APP_NAME.app" /Applications/

# Target quarantine stripping specifically, avoiding deep signature tampering
echo "   > Removing Quarantine attributes..."
sudo xattr -r -d com.apple.quarantine "/Applications/\$APP_NAME.app" 2>/dev/null || true

echo "[2/3] Installing Background Service..."
DATA_DIR="\$HOME/Library/Application Support/\$APP_NAME"
mkdir -p "\$DATA_DIR"
cp "\$DIR/Service_Binary/wemo_service" "\$DATA_DIR/"
chmod +x "\$DATA_DIR/wemo_service"
sudo xattr -r -d com.apple.quarantine "\$DATA_DIR/wemo_service" 2>/dev/null || true

echo "[3/3] Registering Startup Service..."
PLIST="\$HOME/Library/LaunchAgents/com.qrussell.wemoops.plist"

cat > "\$PLIST" <<PLIST_CONTENT
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.qrussell.wemoops</string>
    <key>ProgramArguments</key>
    <array>
        <string>\$DATA_DIR/wemo_service</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/wemo_ops.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/wemo_ops_err.log</string>
</dict>
</plist>
PLIST_CONTENT

launchctl unload "\$PLIST" 2>/dev/null || true
launchctl load "\$PLIST"

echo ""
echo "✅ Installation Complete!"
echo "   - Service running on PORT 5050"
echo "   - You can now launch WemoOps from your Applications folder."
echo "==============================================="
EOF

chmod +x "$STAGING/Install_WemoOps.command"

# 6. GENERATE DMG
echo "[4/4] Generating DMG..."
DMG_NAME="${APP_NAME}_${VERSION}_universal.dmg"
rm -f "dist/$DMG_NAME"
hdiutil create -volname "$APP_NAME Installer" -srcfolder "$STAGING" -ov -format UDZO "dist/$DMG_NAME" >/dev/null

echo ""
echo "========================================="
echo "   SUCCESS! DMG Ready:"
echo "   dist/$DMG_NAME"
echo "========================================="