#!/bin/bash

# ==============================================================================
#  WEMO OPS - MASTER BUILDER (RPM / Rocky / Fedora / RHEL)
#  Version: 5.3.0-Stable
# ==============================================================================

set -e

# --- CONFIGURATION ---
APP_NAME="WemoOps"
SAFE_NAME="wemo-ops"
VERSION="5.3.0"
RELEASE="1"
ARCH="x86_64"
SUMMARY="Wemo Ops Center - Automation Server and Client"
CLIENT_SCRIPT="wemo_ops_universal.py"
SERVER_SCRIPT="wemo_server.py"
HOOBS_SCRIPT="hoobs_installer.py"

# 1. SETUP PATHS
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

RPM_TOP_DIR="$SCRIPT_DIR/dist/rpm_build"
INSTALL_DIR="/opt/$APP_NAME"

echo "========================================="
echo "   WEMO OPS - RPM PACKAGER               "
echo "   Version: $VERSION-$RELEASE"
echo "========================================="

# 2. CHECK SYSTEM PREREQUISITES
echo "[1/5] Checking Build Tools..."

if ! command -v rpmbuild &> /dev/null; then
    echo "❌ ERROR: 'rpmbuild' not found."
    echo "👉 ACTION: Run 'sudo dnf install rpm-build rpmdevtools'"
    exit 1
fi

# FIND COMPATIBLE PYTHON (Must be 3.10+)
PYTHON_BIN=""
for p in python3.12 python3.11 python3.10; do
    if command -v $p &> /dev/null; then
        PYTHON_BIN=$p
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ ERROR: Python 3.10+ is required but not found."
    echo "👉 ACTION: Run 'sudo dnf install python3.11 python3.11-devel'"
    exit 1
fi
echo "   > Using Python: $PYTHON_BIN"

# 3. COMPILE BINARIES
echo "[2/5] Compiling Binaries..."

if [ -d ".venv" ]; then rm -rf .venv; fi

$PYTHON_BIN -m venv .venv
source .venv/bin/activate

echo "   > Installing Python libraries..."
pip install --upgrade pip --quiet
pip install "pywemo>=2.1.1" customtkinter requests pyinstaller pyperclip Pillow flask qrcode waitress --quiet --prefer-binary

rm -rf dist/rpm_build
rm -f dist/*.rpm

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
    --add-data "templates:templates" \
    --add-data "static:static" \
    --hidden-import pywemo \
    --hidden-import flask \
    --hidden-import waitress \
    "$SERVER_SCRIPT" >/dev/null

# C. Build HOOBS Installer
if [ -f "$HOOBS_SCRIPT" ]; then
    echo "   > Compiling HOOBS Installer ($HOOBS_SCRIPT)..."
    # Note: Built WITH console so the user can see the terminal output
    pyinstaller --noconfirm --onefile \
        --name "wemo_hoobs_setup" \
        "$HOOBS_SCRIPT" >/dev/null
fi

deactivate

if [ ! -f "dist/wemo-ops-client" ] || [ ! -f "dist/wemo-ops-server" ]; then
    echo "❌ ERROR: Compilation failed. Binaries are missing in 'dist/'."
    exit 1
fi

# 4. PREPARE RPM DIRECTORY STRUCTURE
echo "[3/5] Setting up RPM Build Tree..."
mkdir -p "$RPM_TOP_DIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

SOURCE_DIR="$RPM_TOP_DIR/SOURCES/$SAFE_NAME-$VERSION"
mkdir -p "$SOURCE_DIR"

cp "dist/wemo-ops-client" "$SOURCE_DIR/"
cp "dist/wemo-ops-server" "$SOURCE_DIR/"
if [ -f "dist/wemo_hoobs_setup" ]; then
    cp "dist/wemo_hoobs_setup" "$SOURCE_DIR/"
fi

if [ -f "images/app_icon.ico" ]; then
    cp "images/app_icon.ico" "$SOURCE_DIR/"
fi

cd "$RPM_TOP_DIR/SOURCES"
tar -czf "$SAFE_NAME-$VERSION.tar.gz" "$SAFE_NAME-$VERSION"
cd "$SCRIPT_DIR"

# 5. GENERATE SPEC FILE
echo "[4/5] Generating .spec file..."
cat > "$RPM_TOP_DIR/SPECS/$SAFE_NAME.spec" <<EOF
%define debug_package %{nil}
%define _enable_debug_packages 0
%define _build_id_links none

Name:           $SAFE_NAME
Version:        $VERSION
Release:        $RELEASE%{?dist}
Summary:        $SUMMARY
License:        Proprietary
Group:          Applications/System
Source0:        %{name}-%{version}.tar.gz
BuildArch:      $ARCH
AutoReqProv:    no

Requires:       python3, python3-tkinter, fontconfig, liberation-sans-fonts

%description
Wemo Ops is a complete automation suite for Belkin Wemo devices.

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}$INSTALL_DIR
mkdir -p %{buildroot}$INSTALL_DIR/images
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/lib/systemd/system

install -m 755 wemo-ops-client %{buildroot}$INSTALL_DIR/wemo-ops-client
install -m 755 wemo-ops-server %{buildroot}$INSTALL_DIR/wemo-ops-server

if [ -f wemo_hoobs_setup ]; then
    install -m 755 wemo_hoobs_setup %{buildroot}$INSTALL_DIR/wemo_hoobs_setup
fi

if [ -f app_icon.ico ]; then
    install -m 644 app_icon.ico %{buildroot}$INSTALL_DIR/images/app_icon.ico
fi

cat > %{buildroot}/usr/bin/wemo-ops <<WRAPPER
#!/bin/bash
export XLIB_SKIP_ARGB_VISUALS=1
exec $INSTALL_DIR/wemo-ops-client "\$@"
WRAPPER
chmod 755 %{buildroot}/usr/bin/wemo-ops

ln -s $INSTALL_DIR/wemo-ops-server %{buildroot}/usr/bin/wemo-server

cat > %{buildroot}/usr/share/applications/$SAFE_NAME.desktop <<ENTRY
[Desktop Entry]
Type=Application
Name=Wemo Ops Center
Comment=Wemo Automation Dashboard
Exec=/usr/bin/wemo-ops
Icon=utilities-terminal
Terminal=false
Categories=Utility;Network;
ENTRY

cat > %{buildroot}/usr/lib/systemd/system/wemo-ops-server.service <<SERVICE
[Unit]
Description=Wemo Ops Automation Server
After=network.target

[Service]
ExecStart=$INSTALL_DIR/wemo-ops-server
WorkingDirectory=$INSTALL_DIR
Restart=always
User=root

[Install]
WantedBy=multi-user.target
SERVICE

%files
$INSTALL_DIR
/usr/bin/wemo-ops
/usr/bin/wemo-server
/usr/share/applications/$SAFE_NAME.desktop
/usr/lib/systemd/system/wemo-ops-server.service

%post
update-desktop-database &> /dev/null || :
systemctl daemon-reload
systemctl enable --now wemo-ops-server

if command -v firewall-cmd &> /dev/null; then
    if systemctl is-active --quiet firewalld; then
        echo "🔥 Wemo Ops: Configuring Firewall Ports..."
        firewall-cmd --permanent --add-port=5000/tcp &> /dev/null || :
        firewall-cmd --permanent --add-port=5050/tcp &> /dev/null || :
        firewall-cmd --permanent --add-port=49152-49155/tcp &> /dev/null || :
        firewall-cmd --permanent --add-port=1900/udp &> /dev/null || :
        firewall-cmd --reload &> /dev/null || :
    fi
fi

%preun
if [ \$1 -eq 0 ]; then
    systemctl stop wemo-ops-server
    systemctl disable wemo-ops-server
fi

%postun
update-desktop-database &> /dev/null || :
if [ \$1 -eq 0 ]; then
    rm -rf $INSTALL_DIR
fi
EOF

# 6. BUILD RPM
echo "[5/5] Running rpmbuild..."
rpmbuild --define "_topdir $RPM_TOP_DIR" -bb "$RPM_TOP_DIR/SPECS/$SAFE_NAME.spec"

mv "$RPM_TOP_DIR/RPMS/$ARCH/"*.rpm dist/
rm -rf "$RPM_TOP_DIR"

echo ""
echo "========================================="
echo "   SUCCESS! RPM Ready in dist/ folder:"
ls dist/*.rpm
echo "========================================="