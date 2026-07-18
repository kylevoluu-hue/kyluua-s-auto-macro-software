# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for AutoMacro.

Produces a single, self-contained, windowed executable named ``AutoMacro``
that can be pinned to the taskbar / dock and launched like any other app.

Build with:
    pip install -r requirements.txt pyinstaller
    pyinstaller automacro.spec

The result is placed in ``dist/`` (``dist/AutoMacro.exe`` on Windows,
``dist/AutoMacro.app`` on macOS, ``dist/AutoMacro`` on Linux).
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Bundle customtkinter's theme/asset JSON files and pull in dynamically
# imported submodules of the input/GUI libraries so nothing is missing at
# runtime.
datas = collect_data_files("customtkinter")
datas += [("assets/icon.png", "assets")]
if sys.platform.startswith("win"):
    datas += [("assets/icon.ico", "assets")]

# Auto-collection imports the package to enumerate it, which can fail on a
# headless build machine (no display).  Guard it and add the platform's
# pynput backend explicitly so input works no matter how the build ran.
try:
    _pynput_mods = collect_submodules("pynput")
except Exception:
    _pynput_mods = []

hiddenimports = _pynput_mods + collect_submodules("customtkinter")

if sys.platform.startswith("win"):
    hiddenimports += ["pynput.keyboard._win32", "pynput.mouse._win32"]
elif sys.platform == "darwin":
    hiddenimports += ["pynput.keyboard._darwin", "pynput.mouse._darwin"]
else:
    hiddenimports += [
        "pynput.keyboard._xorg",
        "pynput.mouse._xorg",
        "pynput.keyboard._uinput",
    ]
    try:
        hiddenimports += collect_submodules("Xlib")
    except Exception:
        pass

# De-duplicate while preserving order.
hiddenimports = list(dict.fromkeys(hiddenimports))

# Per-platform executable icon.
if sys.platform.startswith("win"):
    app_icon = "assets/icon.ico"
elif sys.platform == "darwin":
    app_icon = "assets/icon.icns"
else:
    app_icon = None

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "numpy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

is_windows = sys.platform.startswith("win")
is_mac = sys.platform == "darwin"

if is_windows:
    # Windows: build a one-FOLDER app (not one-file). A stable, on-disk
    # ``AutoMacro.exe`` pins to the taskbar reliably and is always relaunched
    # from the same path. One-file builds instead unpack themselves into a
    # fresh %TEMP% folder on every launch, which SmartScreen / Smart App
    # Control and antivirus repeatedly re-evaluate and often block — and that
    # churn is also what can break a taskbar pin between launches.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="AutoMacro",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,  # windowed app: no terminal window
        disable_windowed_traceback=False,
        icon=app_icon,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="AutoMacro",
    )
else:
    # macOS / Linux: a single self-contained executable.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="AutoMacro",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=is_mac,  # macOS: accept file/URL open events
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=app_icon,
    )

    # macOS: wrap the executable in a proper .app bundle so it pins to the Dock.
    if is_mac:
        app = BUNDLE(
            exe,
            name="AutoMacro.app",
            icon=app_icon,
            bundle_identifier="com.kyluua.automacro",
            info_plist={
                "CFBundleName": "AutoMacro",
                "CFBundleDisplayName": "AutoMacro",
                "CFBundleShortVersionString": "1.0.2",
                "NSHighResolutionCapable": True,
                # Explains the accessibility prompt macOS shows on first use.
                "NSAppleEventsUsageDescription": (
                    "AutoMacro sends keystrokes to the application you choose."
                ),
            },
        )
