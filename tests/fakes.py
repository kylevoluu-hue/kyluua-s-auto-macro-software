"""In-memory fake backends used by the engine tests."""

from __future__ import annotations

import threading
from typing import Sequence

from automacro.backends.base import WindowInfo


class FakeInput:
    """Records every input call so tests can assert on the sequence."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.available = True

    def tap(self, key: str, presses: int = 1) -> None:
        self.calls.append(("tap", key, presses))

    def hotkey(self, keys: Sequence[str]) -> None:
        self.calls.append(("hotkey", tuple(keys)))

    def type_text(self, text: str) -> None:
        self.calls.append(("text", text))


class FakeWindows:
    """A controllable window backend for focus/activation tests."""

    def __init__(self, windows: list[WindowInfo] | None = None) -> None:
        self.available = True
        self._windows = windows or []
        self._active: WindowInfo | None = None
        self.activated: list[str] = []
        self._lock = threading.Lock()

    def set_windows(self, windows: list[WindowInfo]) -> None:
        with self._lock:
            self._windows = list(windows)

    def set_active(self, window: WindowInfo | None) -> None:
        with self._lock:
            self._active = window

    def list_windows(self) -> list[WindowInfo]:
        with self._lock:
            return list(self._windows)

    def active_window(self) -> WindowInfo | None:
        with self._lock:
            return self._active

    def activate(self, window: WindowInfo) -> bool:
        with self._lock:
            self.activated.append(window.title)
            self._active = window
        return True
