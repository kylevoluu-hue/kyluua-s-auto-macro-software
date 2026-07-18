"""Real keyboard input backend built on :mod:`pynput`.

Synthetic key events are delivered to whichever window currently holds the
OS keyboard focus.  This is the reliable, cross-platform way to drive
another application: the engine focuses the target window first, then this
backend sends the keys.

``pynput`` is imported at construction time (not module import time) so that
merely importing the package on a headless machine does not fail.
"""

from __future__ import annotations

import time
from typing import Sequence

from ..keyspec import KeySpecError, normalize_name

# Time a key is held down before release.  A hair of hold time makes input
# register reliably in games and some apps that poll rather than queue keys.
_PRESS_HOLD_S = 0.012


class PynputInputBackend:
    """Sends key taps, hotkeys and typed text via :mod:`pynput`."""

    def __init__(self) -> None:
        from pynput.keyboard import Controller, Key, KeyCode

        self._Key = Key
        self._KeyCode = KeyCode
        self._controller = Controller()
        self._special = self._build_special_map(Key)

    @property
    def available(self) -> bool:
        return True

    @staticmethod
    def _build_special_map(Key) -> dict[str, object]:
        """Map canonical key names to pynput ``Key`` members.

        Built with ``getattr`` so that keys missing on a given platform or
        pynput version are simply omitted rather than raising at import.
        """

        names = [
            "enter",
            "esc",
            "tab",
            "space",
            "backspace",
            "delete",
            "insert",
            "home",
            "end",
            "page_up",
            "page_down",
            "up",
            "down",
            "left",
            "right",
            "caps_lock",
            "num_lock",
            "scroll_lock",
            "print_screen",
            "pause",
            "menu",
            "ctrl",
            "alt",
            "shift",
            "cmd",
            "media_play_pause",
            "media_volume_up",
            "media_volume_down",
            "media_volume_mute",
            "media_next",
            "media_previous",
        ]
        names += [f"f{i}" for i in range(1, 21)]  # pynput exposes f1..f20

        mapping: dict[str, object] = {}
        for name in names:
            member = getattr(Key, name, None)
            if member is not None:
                mapping[name] = member
        return mapping

    def _resolve(self, name: str):
        """Translate a canonical key name into a pynput key object."""

        key = normalize_name(name)
        if not key:
            raise KeySpecError("Empty key")
        if key in self._special:
            return self._special[key]
        if len(key) == 1:
            return self._KeyCode.from_char(key)
        raise KeySpecError(f"Unsupported key: {name!r}")

    def tap(self, key: str, presses: int = 1) -> None:
        obj = self._resolve(key)
        for _ in range(max(1, presses)):
            self._controller.press(obj)
            if _PRESS_HOLD_S:
                time.sleep(_PRESS_HOLD_S)
            self._controller.release(obj)

    def hotkey(self, keys: Sequence[str]) -> None:
        objs = [self._resolve(k) for k in keys]
        # Press modifiers-then-key in order, hold briefly, release in reverse.
        for obj in objs:
            self._controller.press(obj)
        if _PRESS_HOLD_S:
            time.sleep(_PRESS_HOLD_S)
        for obj in reversed(objs):
            self._controller.release(obj)

    def type_text(self, text: str) -> None:
        self._controller.type(text)
