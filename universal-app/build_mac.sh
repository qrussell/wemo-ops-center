#!/bin/bash

# ==============================================================================
#  WEMO OPS - MASTER BUILDER (Port 5050 Edition)
#  Version: read from wemo_ops_universal.py (see ci/get_version.py)
#
#  Builds for the chip of the machine it runs on (Apple Silicon or Intel).
#  Optional signing/notarization (all via environment variables):
#    MAC_SIGN_IDENTITY   "Developer ID Application: Name (TEAMID)"; default "-" = ad-hoc
#    NOTARY_APPLE_ID, NOTARY_TEAM_ID, NOTARY_PASSWORD   app-specific password for notarytool
# ==============================================================================

set -e

APP_NAME="WemoOps"
CLIENT_SCRIPT="wemo_ops_universal.py"
SERVER_SCRIPT="wemo_server.py"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# VERSION: single source is VERSION in wemo_ops_universal.py (override with WEMO_VERSION)
APP_VERSION="${WEMO_VERSION:-$(python3 ci/get_version.py)}"
if [ -z "$APP_VERSION" ]; then echo "❌ ERROR: could not read VERSION from wemo_ops_universal.py"; exit 1; fi
VERSION="${APP_VERSION}-${PKG_RELEASE:-1}"
case "$(uname -m)" in
    arm64) CHIP="apple-silicon" ;;
    x86_64) CHIP="intel" ;;
    *) CHIP="$(uname -m)" ;;
esac
# The app runs on the macOS version it was built on and newer, so the DMG
# name says which: e.g. macos15-apple-silicon, macos26-intel
MACOS_MAJOR="$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)"
ARCH_LABEL="macos${MACOS_MAJOR:-unknown}-${CHIP}"
SIGN_ID="${MAC_SIGN_IDENTITY:--}"

echo "========================================="
echo "   WEMO OPS - MAC PACKAGER (.DMG)        "
echo "   Version: $VERSION (Port 5050)"
echo "========================================="

# 1. CHECK TOOLS
if ! command -v python3 &> /dev/null; then echo "❌ ERROR: python3 not found."; exit 1; fi
if ! command -v hdiutil &> /dev/null; then echo "❌ ERROR: hdiutil not found."; exit 1; fi

# 2. SETUP ENV
echo "[1/5] Setting up Virtual Environment..."
if [ -d ".venv_mac" ]; then rm -rf ".venv_mac"; fi
python3 -m venv ".venv_mac"
source ".venv_mac/bin/activate"

echo "   > Installing Libraries..."
pip install --upgrade pip --quiet
pip install "pywemo>=2.1.1" customtkinter requests pyinstaller pyperclip Pillow flask qrcode waitress --quiet

# Python without Tk (e.g. some Homebrew builds) produces an app that will not launch (#21)
if ! python -c "import tkinter; tkinter.Tcl()" >/dev/null 2>&1; then
    echo "❌ ERROR: this Python has no working tkinter."
    PYV=$(python -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    echo "👉 Use the python.org installer, or: brew install python-tk@$PYV"
    exit 1
fi

# 3. CLEANUP
rm -rf build/ dist/

# 4. COMPILE
echo "[2/5] Compiling Binaries..."

# Icon Detection
ICON_FLAG=""
ADD_DATA_FLAG=""
if [ -f "images/WemoOpsCenter.icns" ]; then
    ICON_FLAG="--icon=images/WemoOpsCenter.icns"
    ADD_DATA_FLAG="--add-data images/WemoOpsCenter.icns:."
elif [ -f "images/app_icon.ico" ]; then
    ICON_FLAG="--icon=images/app_icon.ico"
    ADD_DATA_FLAG="--add-data images/app_icon.ico:."
fi

# A. Build Client
echo "   > Building GUI App..."
pyinstaller --noconfirm --windowed --clean \
    --name "$APP_NAME" \
    $ICON_FLAG \
    $ADD_DATA_FLAG \
    --collect-all customtkinter \
    --collect-all pillow \
    --hidden-import pywemo \
    --hidden-import pyperclip \
    --hidden-import qrcode \
    --hidden-import PIL \
    --hidden-import PIL._tkinter_finder \
    --hidden-import PIL.ImageTk \
    "$CLIENT_SCRIPT" >/dev/null

# B. Build Server
echo "   > Building Service Binary..."
pyinstaller --noconfirm --noconsole --onefile --clean \
    --name "wemo_service" \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --hidden-import pywemo \
    --hidden-import flask \
    --hidden-import waitress \
    "$SERVER_SCRIPT" >/dev/null

deactivate

# 5. BUNDLE
echo "[3/5] Bundling Executables..."
cp "dist/wemo_service" "dist/$APP_NAME.app/Contents/MacOS/"

# Adding a file to the bundle invalidates the signature PyInstaller applied, and
# macOS then reports the app as "damaged" (#21). Re-sign the finished bundle.
echo "   > Signing (identity: $SIGN_ID)..."
if [ "$SIGN_ID" = "-" ]; then
    codesign --force --sign - "dist/wemo_service"
    codesign --force --deep --sign - "dist/$APP_NAME.app"
else
    for target in "dist/wemo_service" "dist/$APP_NAME.app/Contents/MacOS/wemo_service"; do
        codesign --force --timestamp --options runtime --entitlements ci/entitlements.plist --sign "$SIGN_ID" "$target"
    done
    codesign --force --deep --timestamp --options runtime --entitlements ci/entitlements.plist --sign "$SIGN_ID" "dist/$APP_NAME.app"
fi
codesign --verify --deep --strict "dist/$APP_NAME.app"

# 6. PACKAGE
echo "[4/5] Packaging DMG..."
STAGING="dist/dmg_staging"
mkdir -p "$STAGING/Service_Binary"

cp -R "dist/$APP_NAME.app" "$STAGING/"
cp "dist/wemo_service" "$STAGING/Service_Binary/"

# Create Install Script
cat > "$STAGING/Install_WemoOps.command" <<EOF
#!/bin/bash
DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
APP_NAME="$APP_NAME"

echo "==============================================="
echo "   Installing $APP_NAME..."
echo "==============================================="

# 1. Install App
echo "[1/3] Copying App to /Applications..."
rm -rf "/Applications/\$APP_NAME.app"
cp -R "\$DIR/\$APP_NAME.app" /Applications/

# 2. Install Service
echo "[2/3] Installing Background Service..."
DATA_DIR="\$HOME/Library/Application Support/\$APP_NAME"
mkdir -p "\$DATA_DIR"
cp "\$DIR/Service_Binary/wemo_service" "\$DATA_DIR/"
chmod +x "\$DATA_DIR/wemo_service"

# 3. Register LaunchAgent
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
echo "==============================================="
EOF

chmod +x "$STAGING/Install_WemoOps.command"

# 7. GENERATE DMG
echo "[5/5] Generating DMG..."
DMG_NAME="${APP_NAME}_${VERSION}_${ARCH_LABEL}.dmg"
rm -f "dist/$DMG_NAME"
hdiutil create -volname "$APP_NAME Installer" -srcfolder "$STAGING" -ov -format UDZO "dist/$DMG_NAME" >/dev/null

if [ "$SIGN_ID" != "-" ]; then
    codesign --force --timestamp --sign "$SIGN_ID" "dist/$DMG_NAME"
    if [ -n "$NOTARY_APPLE_ID" ] && [ -n "$NOTARY_TEAM_ID" ] && [ -n "$NOTARY_PASSWORD" ]; then
        echo "   > Notarizing (this can take several minutes)..."
        xcrun notarytool submit "dist/$DMG_NAME" --apple-id "$NOTARY_APPLE_ID" --team-id "$NOTARY_TEAM_ID" --password "$NOTARY_PASSWORD" --wait
        xcrun stapler staple "dist/$DMG_NAME"
    else
        echo "   ⚠️  Signed but not notarized (NOTARY_* not set): Gatekeeper will still warn."
    fi
fi

echo ""
echo "========================================="
echo "   SUCCESS! DMG Ready:"
echo "   dist/$DMG_NAME"
echo "========================================="