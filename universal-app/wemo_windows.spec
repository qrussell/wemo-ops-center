# -*- mode: python ; coding: utf-8 -*-
# Windows build (run by build_windows.bat): one folder, not one-file exes.
#
# One-file PyInstaller exes unpack Python into a temp folder on every start,
# which Microsoft Defender's machine-learning model flags as
# Trojan:Win32/Bearfoos.A!ml (GitHub issue 33). Here the dashboard, the
# background service and the HOOBS helper are built into one folder that
# shares a single _internal\ runtime:
#
#   dist\WemoOps\WemoOps.exe
#   dist\WemoOps\wemo_service.exe
#   dist\WemoOps\Wemo_HOOBS_Integration_Setup.exe
#   dist\WemoOps\_internal\...
#
# The installer copies that folder to {app}; the dashboard finds the service
# and the HOOBS helper next to itself, as before.
import os
from PyInstaller.utils.hooks import collect_all

ICON = os.path.join("images", "app_icon.ico")
icon = ICON if os.path.exists(ICON) else None

ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")

gui = Analysis(
    ["wemo_ops_universal.py"],
    datas=ctk_datas + ([(ICON, "images")] if icon else []),
    binaries=ctk_binaries,
    hiddenimports=ctk_hidden + ["pywemo", "pyperclip", "qrcode", "PIL"],
)
svc = Analysis(
    ["wemo_server.py"],
    datas=[("templates", "templates"), ("static", "static")],
    hiddenimports=["pywemo", "flask", "waitress"],
)
hoobs = Analysis(["hoobs_installer.py"])

gui_exe = EXE(PYZ(gui.pure), gui.scripts, [], exclude_binaries=True,
              name="WemoOps", console=False, icon=icon)
svc_exe = EXE(PYZ(svc.pure), svc.scripts, [], exclude_binaries=True,
              name="wemo_service", console=False, icon=icon)
hoobs_exe = EXE(PYZ(hoobs.pure), hoobs.scripts, [], exclude_binaries=True,
                name="Wemo_HOOBS_Integration_Setup", console=True, uac_admin=True)

COLLECT(
    gui_exe, gui.binaries, gui.datas,
    svc_exe, svc.binaries, svc.datas,
    hoobs_exe, hoobs.binaries, hoobs.datas,
    name="WemoOps",
)
