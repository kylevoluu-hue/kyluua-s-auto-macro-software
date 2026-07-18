"""Backend abstractions and factories for input and window targeting.

The interfaces in :mod:`automacro.backends.base` carry no third-party
dependencies.  Concrete implementations (pynput for input; pygetwindow /
AppleScript / wmctrl for windows) are imported lazily by the factory
functions below so that importing this package never fails on a machine
that lacks a display or those optional libraries.
"""

from __future__ import annotations

from .base import (
    InputBackend,
    NullInputBackend,
    NullWindowBackend,
    WindowBackend,
    WindowInfo,
)

__all__ = [
    "InputBackend",
    "WindowBackend",
    "WindowInfo",
    "NullInputBackend",
    "NullWindowBackend",
    "create_input_backend",
    "create_window_backend",
]


def create_input_backend() -> InputBackend:
    """Return the best available input backend for this machine.

    Falls back to :class:`NullInputBackend` (which raises a clear error when
    used) if the real, pynput-based backend cannot be constructed.
    """

    try:
        from .pynput_backend import PynputInputBackend

        return PynputInputBackend()
    except Exception as exc:  # pragma: no cover - depends on runtime env
        return NullInputBackend(reason=str(exc))


def create_window_backend() -> WindowBackend:
    """Return the best window backend for the current platform.

    Chooses a platform-appropriate implementation and gracefully degrades to
    :class:`NullWindowBackend` (send-to-current-focus only) when window
    targeting is unavailable.
    """

    import sys

    try:
        if sys.platform.startswith("win"):
            from .window_windows import WindowsWindowBackend

            return WindowsWindowBackend()
        if sys.platform == "darwin":
            from .window_macos import MacWindowBackend

            return MacWindowBackend()
        from .window_linux import LinuxWindowBackend

        return LinuxWindowBackend()
    except Exception as exc:  # pragma: no cover - depends on runtime env
        return NullWindowBackend(reason=str(exc))
