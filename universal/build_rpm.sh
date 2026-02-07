#!/bin/bash

# --- CONFIGURATION ---
APP_NAME="WemoOps"
SAFE_NAME="wemo-ops" # RPMs don't like uppercase or spaces
VERSION="4.2.0"      # Incremented for font update
RELEASE="1"
ARCH="x86_64"        # RPM calls amd64 "x86_64"
SUMMARY="Wemo Ops Center - Automation and Provisioning Tool"
MAIN_SCRIPT="wemo_ops_universal.py"
SERVICE_SCRIPT="wemo_service_universal.py"

# 1. SETUP PATHS
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

RPM_TOP_DIR="$SCRIPT_DIR/dist/rpm_build"
INSTALL_DIR="/opt/$APP_NAME"

echo "========================================="
echo "   WEMO OPS - RPM PACKAGER (.RPM)        "
echo "   Version: $VERSION-$RELEASE"
echo "========================================="

# 2. COMPILE BINARIES (Smart Python Selection)
echo "[1/4] Compiling Binaries..."

# Detect Python 3.11 (Required for CustomTkinter on RHEL 8) or fall back to system default
if command -v python3.11 &> /dev/null; then
    PYTHON_BIN="python3.11"
else
    PYTHON_BIN="python3"
fi
echo "   > Using Python interpreter: $PYTHON_BIN"

if [ ! -d ".venv" ]; then
    $PYTHON_BIN -m venv .venv
fi
source .venv/bin/activate

# Ensure dependencies are installed
pip install -q "pywemo>=2.1.1" customtkinter requests pyinstaller pyperclip pystray Pillow

# Clean dist only (keep build to speed up)
rm -rf dist/rpm_build
rm -f dist/*.rpm

# Build GUI
echo "   > Compiling GUI..."
pyinstaller --noconfirm --onefile --windowed \
    --name "$APP_NAME" \
    --collect-all customtkinter \
    --hidden-import pywemo \
    --hidden-import pyperclip \
    --hidden-import pystray \
    --hidden-import PIL \
    "$MAIN_SCRIPT" >/dev/null 2>&1

# Build Service
echo "   > Compiling Service..."
pyinstaller --noconfirm --onefile --noconsole \
    --name "wemo_service" \
    --hidden-import pywemo \
    --hidden-import pystray \
    --hidden-import PIL \
    "$SERVICE_SCRIPT" >/dev/null 2>&1

deactivate

# 3. PREPARE RPM DIRECTORY STRUCTURE
echo "[2/4] Setting up RPM Build Tree..."
mkdir -p "$RPM_TOP_DIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# We copy the compiled binaries into a "source" folder that rpmbuild will use
SOURCE_DIR="$RPM_TOP_DIR/SOURCES/$SAFE_NAME-$VERSION"
mkdir -p "$SOURCE_DIR"

cp "dist/$APP_NAME" "$SOURCE_DIR/"
cp "dist/wemo_service" "$SOURCE_DIR/"
if [ -f "images/app_icon.ico" ]; then
    cp "images/app_icon.ico" "$SOURCE_DIR/"
fi

# --- Bundle Local Fonts (If you have a fonts/ folder) ---
if [ -d "fonts" ]; then
    echo "   > Bundling local fonts..."
    cp -r "fonts" "$SOURCE_DIR/"
fi
# ---------------------------------------------------------

# Create a tarball of the sources (Standard RPM practice)
cd "$RPM_TOP_DIR/SOURCES"
tar -czf "$SAFE_NAME-$VERSION.tar.gz" "$SAFE_NAME-$VERSION"
cd "$SCRIPT_DIR"

# 4. GENERATE SPEC FILE
echo "[3/4] Generating .spec file..."
cat > "$RPM_TOP_DIR/SPECS/$SAFE_NAME.spec" <<EOF
# --- FIXES FOR PYINSTALLER BINARIES ---
# Disable debug info generation (Fixes "Empty %files" error)
%define debug_package %{nil}
%define _enable_debug_packages 0
# Disable build-id conflict checks (Fixes "Duplicate build-ids" error)
%define _build_id_links none
# --------------------------------------

Name:           $SAFE_NAME
Version:        $VERSION
Release:        $RELEASE%{?dist}
Summary:        $SUMMARY
License:        Proprietary
Group:          Applications/System
Source0:        %{name}-%{version}.tar.gz
BuildArch:      $ARCH
AutoReqProv:    no

# Runtime Dependencies
Requires:       python3, python3-tkinter, xclip, fontconfig
# Font Dependencies (Standardizing for RHEL/Fedora)
Requires:       liberation-sans-fonts, google-noto-sans-fonts

%description
Wemo Ops Center is a tool for provisioning and automating Wemo smart devices.
It includes a dashboard UI and a background automation service.

%prep
%setup -q

%build
# Binaries are already compiled by PyInstaller.

%install
mkdir -p %{buildroot}$INSTALL_DIR
mkdir -p %{buildroot}$INSTALL_DIR/images
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/lib/systemd/user

# Install Binaries
install -m 755 $APP_NAME %{buildroot}$INSTALL_DIR/$APP_NAME
install -m 755 wemo_service %{buildroot}$INSTALL_DIR/wemo_service
# Install Icon
if [ -f app_icon.ico ]; then
    install -m 644 app_icon.ico %{buildroot}$INSTALL_DIR/images/app_icon.ico
fi

# --- Install Fonts ---
if [ -d fonts ]; then
    mkdir -p %{buildroot}$INSTALL_DIR/fonts
    cp -r fonts/* %{buildroot}$INSTALL_DIR/fonts/
fi
# ---------------------

# Symlink
ln -s $INSTALL_DIR/$APP_NAME %{buildroot}/usr/bin/$APP_NAME

# Desktop Shortcut
cat > %{buildroot}/usr/share/applications/$APP_NAME.desktop <<ENTRY
[Desktop Entry]
Type=Application
Name=Wemo Ops Center
Comment=Manage and Automate Wemo Devices
Exec=/usr/bin/$APP_NAME
Icon=utilities-terminal
Terminal=false
Categories=Utility;Network;
ENTRY

# Systemd Service
cat > %{buildroot}/usr/lib/systemd/user/wemo_ops.service <<SERVICE
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
SERVICE

%files
$INSTALL_DIR
/usr/bin/$APP_NAME
/usr/share/applications/$APP_NAME.desktop
/usr/lib/systemd/user/wemo_ops.service

%post
update-desktop-database &> /dev/null || :
# --- Update Font Cache ---
if [ -d "$INSTALL_DIR/fonts" ]; then
    # Force re-scan of font directories
    fc-cache -f -v >/dev/null 2>&1 || :
fi
echo "Wemo Ops installed."
echo "Enable service with: systemctl --user enable --now wemo_ops"

%preun
# Stop service before removal
systemctl --user stop wemo_ops &> /dev/null || :
systemctl --user disable wemo_ops &> /dev/null || :

%postun
update-desktop-database &> /dev/null || :
rm -rf $INSTALL_DIR

%changelog
* $(date "+%a %b %d %Y") Quentin Russell <user@example.com> - $VERSION-$RELEASE
- Release $VERSION
EOF

# 5. BUILD RPM
echo "[4/4] Running rpmbuild..."
# We define _topdir to keep everything local to this project folder
rpmbuild --define "_topdir $RPM_TOP_DIR" -bb "$RPM_TOP_DIR/SPECS/$SAFE_NAME.spec"

# Move final RPM to dist folder
mv "$RPM_TOP_DIR/RPMS/$ARCH/"*.rpm dist/
rm -rf "$RPM_TOP_DIR"

echo "========================================="
echo "   SUCCESS! RPM Ready in dist/ folder:"
ls dist/*.rpm
echo "========================================="
