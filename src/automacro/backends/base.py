"""Abstract input and window backends plus inert null implementations.

These types are pure Python and safe to import anywhere.  The ``Null*``
classes let the rest of the app run (and be tested) on machines where the
real backends are unavailable: input becomes a no-op that reports why, and
window targeting reports an empty list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class WindowInfo:
    """A lightweight description of an on-screen window."""

    title: str
    handle: object = None  # opaque, backend-specific handle
    process: str = ""  # process/app name when the backend can supply it

    @property
    def label(self) -> str:
        """A user-friendly label for lists and dropdowns."""

        if self.process and self.process.lower() not in self.title.lower():
            return f"{self.title}  —  {self.process}"
        return self.title or "(untitled window)"


@runtime_checkable
class InputBackend(Protocol):
    """Sends synthetic keyboard input to whatever window has focus."""

    def tap(self, key: str, presses: int = 1) -> None:
        """Press and release a single key *presses* times."""

    def hotkey(self, keys: Sequence[str]) -> None:
        """Press modifiers + key together, then release in reverse order."""

    def type_text(self, text: str) -> None:
        """Type a literal string as individual key presses."""

    def mouse(self, action: str) -> None:
        """Perform a canonical mouse action at the current cursor position.

        Actions: ``left``/``right``/``middle`` (click), ``double`` (double
        left click), ``left_down``/``left_up`` (press/release), and
        ``scroll_up``/``scroll_down`` (one notch).
        """

    @property
    def available(self) -> bool:
        """Whether real input can actually be sent."""


@runtime_checkable
class WindowBackend(Protocol):
    """Enumerates and focuses top-level windows."""

    def list_windows(self) -> list[WindowInfo]:
        """Return the currently open, titled top-level windows."""

    def active_window(self) -> WindowInfo | None:
        """Return the currently focused window, if known."""

    def activate(self, window: WindowInfo) -> bool:
        """Bring *window* to the foreground.  Return ``True`` on success."""

    @property
    def available(self) -> bool:
        """Whether window enumeration/targeting is supported here."""


class NullInputBackend:
    """Input backend used when no real one is available.

    It never sends input; every attempt raises :class:`RuntimeError` with a
    message explaining what went wrong, so failures are obvious rather than
    silent.
    """

    def __init__(self, reason: str = "input backend unavailable") -> None:
        self.reason = reason

    @property
    def available(self) -> bool:
        return False

    def _fail(self) -> None:
        raise RuntimeError(f"Cannot send keyboard input: {self.reason}")

    def tap(self, key: str, presses: int = 1) -> None:
        self._fail()

    def hotkey(self, keys: Sequence[str]) -> None:
        self._fail()

    def type_text(self, text: str) -> None:
        self._fail()

    def mouse(self, action: str) -> None:
        self._fail()


class NullWindowBackend:
    """Window backend used when targeting is unavailable.

    Reports no windows and cannot activate anything; the engine treats this
    as "send to whatever is currently focused".
    """

    def __init__(self, reason: str = "window targeting unavailable") -> None:
        self.reason = reason

    @property
    def available(self) -> bool:
        return False

    def list_windows(self) -> list[WindowInfo]:
        return []

    def active_window(self) -> WindowInfo | None:
        return None

    def activate(self, window: WindowInfo) -> bool:
        return False
