"""Window enumeration and focusing on Linux (X11) via ``wmctrl`` / ``xdotool``.

Either tool alone is enough; both are common and installable from every
mainstream distro's package manager (``sudo apt install wmctrl xdotool``).
When neither is present the backend reports itself unavailable and the
engine sends keys to the currently focused window.

Note: these are X11 tools.  Under a pure Wayland session they may not be
able to enumerate or focus windows; that is a limitation of Wayland's
security model rather than of this backend.
"""

from __future__ import annotations

import shutil
import subprocess

from .base import WindowInfo


def parse_wmctrl(text: str) -> list[WindowInfo]:
    """Parse ``wmctrl -l`` output into :class:`WindowInfo` objects.

    Each line looks like::

        0x03000007  0 hostname Window Title Here

    i.e. ``<hex-id> <desktop> <host> <title...>``.
    """

    results: list[WindowInfo] = []
    for line in text.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        win_id, _desktop, _host, title = parts
        title = title.strip()
        if not title:
            continue
        results.append(WindowInfo(title=title, handle=win_id))
    return results


class LinuxWindowBackend:
    def __init__(self) -> None:
        self._wmctrl = shutil.which("wmctrl")
        self._xdotool = shutil.which("xdotool")
        if not self._wmctrl and not self._xdotool:
            raise RuntimeError(
                "Neither 'wmctrl' nor 'xdotool' found; install one to enable "
                "window targeting (e.g. 'sudo apt install wmctrl xdotool')."
            )

    @property
    def available(self) -> bool:
        return bool(self._wmctrl or self._xdotool)

    def _run(self, args: list[str], timeout: float = 4.0) -> str:
        try:
            proc = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout
            )
            return proc.stdout
        except Exception:
            return ""

    def list_windows(self) -> list[WindowInfo]:
        if self._wmctrl:
            return parse_wmctrl(self._run([self._wmctrl, "-l"]))
        # xdotool fallback: search visible windows and read their names.
        if self._xdotool:
            ids = self._run(
                [self._xdotool, "search", "--onlyvisible", "--name", ""]
            ).split()
            windows: list[WindowInfo] = []
            for win_id in ids:
                name = self._run([self._xdotool, "getwindowname", win_id]).strip()
                if name:
                    windows.append(WindowInfo(title=name, handle=win_id))
            return windows
        return []

    def active_window(self) -> WindowInfo | None:
        if self._xdotool:
            win_id = self._run([self._xdotool, "getactivewindow"]).strip()
            if win_id:
                name = self._run([self._xdotool, "getwindowname", win_id]).strip()
                return WindowInfo(title=name, handle=win_id)
        return None

    def activate(self, window: WindowInfo) -> bool:
        win_id = window.handle
        if not win_id:
            return False
        if self._wmctrl:
            result = subprocess.run(
                [self._wmctrl, "-i", "-a", str(win_id)],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True
        if self._xdotool:
            result = subprocess.run(
                [self._xdotool, "windowactivate", str(win_id)],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        return False
