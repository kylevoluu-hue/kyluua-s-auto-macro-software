"""Parsing and validation of key / hotkey specifications.

This module is deliberately free of any dependency on an input backend: it
only understands the *names* of keys and how a hotkey string such as
``"ctrl+shift+a"`` decomposes into modifiers and a main key.  The concrete
translation from these canonical names to backend key objects lives in
:mod:`automacro.backends`.

Canonical names are always lower case.  A number of common aliases are
accepted on input and normalised (for example ``"control" -> "ctrl"`` and
``"escape" -> "esc"``) so the UI can be forgiving about what the user types.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "MODIFIERS",
    "SPECIAL_KEYS",
    "KeySpecError",
    "Hotkey",
    "normalize_name",
    "is_valid_key",
    "parse_hotkey",
    "format_hotkey",
]


class KeySpecError(ValueError):
    """Raised when a key or hotkey string cannot be understood."""


#: The modifier keys, in a canonical display order.
MODIFIERS: tuple[str, ...] = ("ctrl", "alt", "shift", "cmd")

#: Aliases that map onto a canonical modifier name.
_MODIFIER_ALIASES = {
    "control": "ctrl",
    "ctl": "ctrl",
    "option": "alt",
    "opt": "alt",
    "altgr": "alt",
    "win": "cmd",
    "windows": "cmd",
    "super": "cmd",
    "meta": "cmd",
    "command": "cmd",
    "apple": "cmd",
}

#: Named non-character keys understood by the engine.  Character keys
#: (letters, digits and punctuation) are handled separately and do not need
#: to appear here.
SPECIAL_KEYS: frozenset[str] = frozenset(
    {
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
        "media_play_pause",
        "media_volume_up",
        "media_volume_down",
        "media_volume_mute",
        "media_next",
        "media_previous",
    }
    | {f"f{i}" for i in range(1, 25)}  # function keys f1..f24
)

#: Aliases that map onto a canonical special key name.
_KEY_ALIASES = {
    "return": "enter",
    "escape": "esc",
    "del": "delete",
    "ins": "insert",
    "pgup": "page_up",
    "pgdn": "page_down",
    "spacebar": "space",
    "prtsc": "print_screen",
    "prtscn": "print_screen",
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
}


def _compact(name: str) -> str:
    """Reduce a name to a separator-free comparison key (``page up`` ->
    ``pageup``)."""

    return re.sub(r"[\s\-_]+", "", name.strip().lower())


# Precompute a single "compact form -> canonical name" table.  This lets
# ``normalize_name`` treat spaces, dashes and underscores interchangeably, so
# ``"page up"``, ``"page-up"``, ``"page_up"`` and ``"pageup"`` all resolve to
# the canonical ``"page_up"``.
_COMPACT_TO_CANONICAL: dict[str, str] = {}
for _canon in (*MODIFIERS, *SPECIAL_KEYS):
    _COMPACT_TO_CANONICAL[_compact(_canon)] = _canon
for _alias, _target in {**_MODIFIER_ALIASES, **_KEY_ALIASES}.items():
    _COMPACT_TO_CANONICAL[_compact(_alias)] = _target


def normalize_name(name: str) -> str:
    """Return the canonical, lower-case form of a single key name.

    Treats spaces, dashes and underscores as equivalent and resolves known
    aliases for both modifiers and special keys.  Does not validate the
    result; use :func:`is_valid_key` for that.
    """

    if not name:
        return ""
    compact = _compact(name)
    if compact in _COMPACT_TO_CANONICAL:
        return _COMPACT_TO_CANONICAL[compact]
    # Unknown multi-word names keep an underscore-joined form; single
    # characters and everything else pass through cleaned and lower-cased.
    return re.sub(r"[\s\-]+", "_", name.strip().lower())


def is_valid_key(name: str) -> bool:
    """Return ``True`` if *name* denotes a key the engine can produce.

    Accepts modifiers, known special keys and any single printable
    character (letters, digits, punctuation).
    """

    key = normalize_name(name)
    if not key:
        return False
    if key in MODIFIERS or key in SPECIAL_KEYS:
        return True
    # A single printable character is a valid literal key.
    return len(key) == 1 and key.isprintable()


@dataclass(frozen=True)
class Hotkey:
    """A parsed hotkey: a set of modifiers plus a single main key."""

    modifiers: tuple[str, ...]
    key: str

    def as_names(self) -> tuple[str, ...]:
        """Return the full ordered tuple of key names (modifiers then key)."""

        return (*self.modifiers, self.key)

    def __str__(self) -> str:
        return format_hotkey(self)


def parse_hotkey(spec: str) -> Hotkey:
    """Parse a ``"ctrl+shift+a"`` style string into a :class:`Hotkey`.

    Raises :class:`KeySpecError` when the string is empty, contains an
    unknown key, has more than one non-modifier key, or is missing a main
    key entirely.
    """

    if spec is None or not spec.strip():
        raise KeySpecError("Empty hotkey")

    parts = [p for p in (part.strip() for part in spec.split("+")) if p]
    if not parts:
        raise KeySpecError(f"Could not parse hotkey: {spec!r}")

    modifiers: list[str] = []
    main_keys: list[str] = []
    for part in parts:
        name = normalize_name(part)
        if name in MODIFIERS:
            if name not in modifiers:
                modifiers.append(name)
        elif is_valid_key(name):
            main_keys.append(name)
        else:
            raise KeySpecError(f"Unknown key {part!r} in hotkey {spec!r}")

    if not main_keys:
        raise KeySpecError(f"Hotkey {spec!r} has no main key")
    if len(main_keys) > 1:
        raise KeySpecError(
            f"Hotkey {spec!r} has multiple non-modifier keys: {main_keys}"
        )

    # Keep modifiers in canonical order for stable comparisons/formatting.
    ordered = tuple(m for m in MODIFIERS if m in modifiers)
    return Hotkey(modifiers=ordered, key=main_keys[0])


def format_hotkey(hotkey: Hotkey) -> str:
    """Render a :class:`Hotkey` back to its canonical ``a+b+c`` string."""

    return "+".join(hotkey.as_names())
