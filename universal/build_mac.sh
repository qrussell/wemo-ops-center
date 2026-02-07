#!/bin/bash

# --- CONFIGURATION ---
APP_NAME="WemoOps"
VERSION="4.2.0"
ICON_FILE="images/WemoOpsCenter.icns"
MAIN_SCRIPT="wemo_ops_universal.py"
SERVICE_SCRIPT="wemo_service_universal.py"

echo "========================================="
echo "   WEMO OPS - MACOS BUILDER (.DMG)       "
echo "   Version: $VERSION (Native Arch)"
echo "========================================="

# 1. SETUP ENVIRONMENT
echo "[1/5] Setting up Virtual Environment..."
if [ -d ".venv" ]; then rm -rf .venv; fi
python3 -m venv .venv
source .venv/bin/activate

# Install Dependencies
pip install --upgrade pip
pip install "pywemo>=2.1.1" customtkinter requests pyinstaller pyperclip pystray Pillow

# 2. CLEANUP
rm -rf build/ dist/

# 3. COMPILE BINARIES
echo "[2/5] Compiling Binaries..."

# Check for Icon
ICON_FLAG=""
ADD_DATA_FLAG=""
if [ -f "$ICON_FILE" ]; then
    echo "   - Found Icon: $ICON_FILE"
    ICON_FLAG="--icon=$ICON_FILE"
    ADD_DATA_FLAG="--add-data $ICON_FILE:." 
else
    echo "   - WARNING: Icon not found at $ICON_FILE"
fi

# Build GUI (Windowed .app) - REMOVED UNIVERSAL FLAG
echo "   > Building GUI App..."
pyinstaller --noconfirm --windowed --clean \
    --name "$APP_NAME" \
    $ICON_FLAG \
    $ADD_DATA_FLAG \
    --collect-all customtkinter \
    --hidden-import pywemo \
    --hidden-import pyperclip \
    --hidden-import pystray \
    --hidden-import PIL \
    "$MAIN_SCRIPT"

# Build Service (Console Binary) - REMOVED UNIVERSAL FLAG
echo "   > Building Service Binary..."
pyinstaller --noconfirm --noconsole --onefile --clean \
    --name "wemo_service" \
    $ICON_FLAG \
    --hidden-import pywemo \
    --hidden-import pystray \
    --hidden-import PIL \
    "$SERVICE_SCRIPT"

deactivate

# 4. ORGANIZE FOR DISTRIBUTION
echo "[3/5] Packaging..."

# Create a staging folder
STAGING="dist/dmg_staging"
mkdir -p "$STAGING"

# Copy the .app bundle
cp -R "dist/$APP_NAME.app" "$STAGING/"

# Copy the service binary
mkdir -p "$STAGING/Service_Binary"
cp "dist/wemo_service" "$STAGING/Service_Binary/"

# Create an Install Script for the user
cat > "$STAGING/Install_WemoOps.command" <<EOF
#!/bin/bash
echo "Installing WemoOps..."

# 1. Move App to Applications
if [ -d "/Applications/WemoOps.app" ]; then
    rm -rf "/Applications/WemoOps.app"
fi
cp -R "\$(dirname "\$0")/WemoOps.app" /Applications/

# 2. Setup Data Directory
DATA_DIR="$HOME/Library/Application Support/WemoOps"
mkdir -p "\$DATA_DIR"

# 3. Install Service Binary
cp "\$(dirname "\$0")/Service_Binary/wemo_service" "\$DATA_DIR/"
chmod +x "\$DATA_DIR/wemo_service"

# 4. Create Launch Agent (Auto-Start)
PLIST="$HOME/Library/LaunchAgents/com.qrussell.wemoops.plist"
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
</dict>
</plist>
PLIST_CONTENT

# Load the service
launchctl unload "\$PLIST" 2>/dev/null
launchctl load "\$PLIST"

echo "==========================================="
echo "Success! WemoOps is in your Applications."
echo "The Background Service has been started."
echo "==========================================="
EOF

chmod +x "$STAGING/Install_WemoOps.command"

# 5. CREATE DMG
echo "[4/5] Creating DMG..."
DMG_NAME="${APP_NAME}_${VERSION}_Installer.dmg"
# Check if hdiutil exists (Mac only)
if command -v hdiutil &> /dev/null; then
    hdiutil create -volname "$APP_NAME Installer" -srcfolder "$STAGING" -ov -format UDZO "dist/$DMG_NAME"
    echo "========================================="
    echo "   BUILD COMPLETE!"
    echo "   Installer: dist/$DMG_NAME"
    echo "========================================="
else
    echo "WARNING: 'hdiutil' not found. DMG skipped."
    echo "The App Bundle is ready in dist/"
fi
