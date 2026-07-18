"""AutoMacro - configurable hotkey macro automation for any application.

A small, dependency-light desktop tool that sends sequences of key taps,
hotkey combinations and typed text to a target application, with fully
configurable cooldowns and delays.

The package is split so that the *core* logic (models, key parsing, the
execution engine and configuration handling) has **no** third-party
dependencies and can be imported and unit-tested on a headless machine.
The platform specific pieces (real keyboard input, window targeting and the
graphical interface) live behind interfaces and import their heavy
dependencies lazily, so importing :mod:`automacro` never fails just because
a GUI toolkit is missing.
"""

from __future__ import annotations

__all__ = ["__version__", "APP_NAME", "APP_ID"]

__version__ = "1.0.4"

#: Human facing product name.
APP_NAME = "AutoMacro"

#: Stable identifier used for config directories, the Windows AppUserModelID
#: (so the taskbar groups/pins the app correctly) and similar plumbing.
APP_ID = "com.kyluua.automacro"
