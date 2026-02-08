#!/bin/sh
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Create group and user with requested IDs
groupadd -g "$PGID" -o wemo 2>/dev/null || true
useradd -u "$PUID" -g "$PGID" -d /home/wemo -m -s /bin/sh wemo 2>/dev/null || true

# Symlink /data to where wemo_server.py expects it for non-root user
mkdir -p /home/wemo/.local/share
ln -sfn /data /home/wemo/.local/share/WemoOps

# Fix ownership
chown -R "$PUID:$PGID" /data /home/wemo

# Drop privileges and run
exec gosu wemo gunicorn -w 1 -b "0.0.0.0:${PORT:-5000}" --log-level info wemo_server:app
