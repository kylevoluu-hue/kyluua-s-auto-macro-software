"""Window enumeration and focusing on Windows via :mod:`pygetwindow`.

Activation is made robust against the common Windows quirks: minimized
windows are restored first, and if pygetwindow's own ``activate`` is refused
by the OS we fall back to ``ShowWindow`` + ``SetForegroundWindow`` through
``ctypes``.
"""

from __future__ import annotations

from .base import WindowInfo


class WindowsWindowBackend:
    def __init__(self) -> None:
        import pygetwindow  # noqa: F401  (import-time availability check)

        self._gw = pygetwindow

    @property
    def available(self) -> bool:
        return True

    def _process_name(self, win) -> str:
        """Best-effort process/app name for a window; blank if unavailable."""

        try:
            import ctypes

            import psutil  # optional dependency

            hwnd = getattr(win, "_hWnd", None)
            if not hwnd:
                return ""
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(
                hwnd, ctypes.byref(pid)
            )
            return psutil.Process(pid.value).name()
        except Exception:
            return ""

    def list_windows(self) -> list[WindowInfo]:
        results: list[WindowInfo] = []
        seen: set[str] = set()
        try:
            windows = self._gw.getAllWindows()
        except Exception:
            return results
        for win in windows:
            title = (getattr(win, "title", "") or "").strip()
            if not title:
                continue
            # Skip zero-size / hidden shell windows.
            try:
                if win.width <= 0 or win.height <= 0:
                    continue
            except Exception:
                pass
            if title in seen:
                continue
            seen.add(title)
            results.append(
                WindowInfo(title=title, handle=win, process=self._process_name(win))
            )
        return results

    def active_window(self) -> WindowInfo | None:
        try:
            win = self._gw.getActiveWindow()
        except Exception:
            return None
        if win is None:
            return None
        title = (getattr(win, "title", "") or "").strip()
        return WindowInfo(title=title, handle=win)

    def activate(self, window: WindowInfo) -> bool:
        win = window.handle
        if win is None:
            return False
        try:
            if getattr(win, "isMinimized", False):
                win.restore()
            win.activate()
            return True
        except Exception:
            return self._force_foreground(win)

    @staticmethod
    def _force_foreground(win) -> bool:
        try:
            import ctypes

            hwnd = getattr(win, "_hWnd", None)
            if not hwnd:
                return False
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            return bool(user32.SetForegroundWindow(hwnd))
        except Exception:
            return False
