"""Global (system-wide) hotkey handling built on :mod:`pynput`.

Global hotkeys let the user start/stop a macro and trigger an emergency stop
without the AutoMacro window being focused.  This is essential: once a macro
starts driving another app, that other app has focus, so the stop key must
work globally.

The heavy import is deferred; :func:`create_hotkey_manager` returns a working
manager when pynput is present and an inert :class:`NullHotkeyManager`
otherwise, so the app still runs (just without global hotkeys).
"""

from __future__ import annotations

from typing import Callable

from .keyspec import KeySpecError, parse_hotkey

__all__ = [
    "to_pynput_hotkey",
    "HotkeyManager",
    "NullHotkeyManager",
    "create_hotkey_manager",
]


def to_pynput_hotkey(spec: str) -> str:
    """Convert a canonical ``"ctrl+shift+a"`` spec to pynput's format.

    pynput expects special keys and modifiers wrapped in angle brackets
    (``<ctrl>+<shift>+a``) while literal characters stay bare.  Raises
    :class:`~automacro.keyspec.KeySpecError` for an invalid spec.
    """

    hotkey = parse_hotkey(spec)
    tokens = [
        name if len(name) == 1 else f"<{name}>" for name in hotkey.as_names()
    ]
    return "+".join(tokens)


class NullHotkeyManager:
    """No-op manager used when global hotkeys are unavailable."""

    available = False

    def __init__(self, reason: str = "global hotkeys unavailable") -> None:
        self.reason = reason

    def set_bindings(self, bindings: dict[str, Callable[[], None]]) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class HotkeyManager:
    """Registers a set of global hotkeys, each mapped to a callback.

    Callbacks fire on pynput's listener thread; a GUI consumer should
    marshal back onto its own thread inside the callback.
    """

    available = True

    def __init__(self) -> None:
        from pynput import keyboard  # noqa: F401 - availability check

        self._keyboard = keyboard
        self._listener = None
        self._bindings: dict[str, Callable[[], None]] = {}
        self._errors: list[str] = []

    @property
    def errors(self) -> list[str]:
        """Specs that could not be registered (for surfacing in the UI)."""

        return list(self._errors)

    def set_bindings(self, bindings: dict[str, Callable[[], None]]) -> None:
        """Replace all bindings and (re)start the listener.

        *bindings* maps canonical hotkey specs to zero-arg callbacks.  Invalid
        or duplicate specs are skipped and recorded in :attr:`errors`.
        """

        self._bindings = dict(bindings)
        self._restart()

    def _restart(self) -> None:
        self.stop()
        self._errors = []
        pynput_map: dict[str, Callable[[], None]] = {}
        for spec, callback in self._bindings.items():
            try:
                key = to_pynput_hotkey(spec)
            except KeySpecError as exc:
                self._errors.append(f"{spec}: {exc}")
                continue
            if key in pynput_map:
                self._errors.append(f"{spec}: duplicate hotkey")
                continue
            pynput_map[key] = callback

        if not pynput_map:
            return
        self._listener = self._keyboard.GlobalHotKeys(pynput_map)
        self._listener.daemon = True
        self._listener.start()

    def start(self) -> None:
        if self._listener is None and self._bindings:
            self._restart()

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


def create_hotkey_manager():
    """Return a working :class:`HotkeyManager`, or a null one if unavailable."""

    try:
        return HotkeyManager()
    except Exception as exc:  # pragma: no cover - depends on runtime env
        return NullHotkeyManager(reason=str(exc))
