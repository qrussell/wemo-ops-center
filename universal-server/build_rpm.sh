#!/bin/bash
set -e

APP_NAME="WemoOpsServer"
SAFE_NAME="wemo-ops-server"
VERSION="1.0.1"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. COMPILE THE WEB SERVER
echo "Compiling Web Server..."
python3.11 -m venv .venv
source .venv/bin/activate
pip install pywemo flask requests pyinstaller
pyinstaller --noconfirm --onefile --noconsole --name "wemo_web" \
    --hidden-import flask \
    --hidden-import pywemo \
    "wemo_server.py"
deactivate

# 2. PREPARE RPM FILES
mkdir -p dist/rpm_server/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
mkdir -p dist/rpm_server/SOURCES/$SAFE_NAME-$VERSION
cp dist/wemo_web dist/rpm_server/SOURCES/$SAFE_NAME-$VERSION/

cd dist/rpm_server/SOURCES
tar -czf $SAFE_NAME-$VERSION.tar.gz $SAFE_NAME-$VERSION
cd "$SCRIPT_DIR"

# 3. GENERATE SPEC FILE
cat > dist/rpm_server/SPECS/$SAFE_NAME.spec <<EOF
Name:           $SAFE_NAME
Version:        $VERSION
Release:        1%{?dist}
Summary:        Wemo Ops Web Server (Headless)
License:        Proprietary
Source0:        %{name}-%{version}.tar.gz
BuildArch:      x86_64
Requires:       python3

%description
A headless web server for managing Wemo devices and automation schedules.

%prep
%setup -q

%install
mkdir -p %{buildroot}/opt/$APP_NAME
install -m 755 wemo_web %{buildroot}/opt/$APP_NAME/wemo_web

# Install Systemd Service
mkdir -p %{buildroot}/etc/systemd/system
cat > %{buildroot}/etc/systemd/system/wemo-web.service <<SERVICE
[Unit]
Description=Wemo Ops Web Interface
After=network.target

[Service]
ExecStart=/opt/$APP_NAME/wemo_web
Restart=always
User=root
WorkingDirectory=/opt/$APP_NAME

[Install]
WantedBy=multi-user.target
SERVICE

%files
/opt/$APP_NAME
/etc/systemd/system/wemo-web.service

%post
systemctl daemon-reload
# Open Firewall Port 5000
if command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=5000/tcp
    firewall-cmd --reload
fi
echo "✅ Wemo Ops Web Server Installed!"
echo "   Enable it: systemctl enable --now wemo-web"
echo "   Access it: http://<YOUR_IP>:5000"

%preun
systemctl stop wemo-web
systemctl disable wemo-web

EOF

# 4. BUILD
rpmbuild --define "_topdir $SCRIPT_DIR/dist/rpm_server" -bb dist/rpm_server/SPECS/$SAFE_NAME.spec
echo "RPM Built in dist/rpm_server/RPMS/"