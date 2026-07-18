"""Parsing and validation of mouse action specifications.

Like :mod:`keyspec`, this module only understands the *names* of mouse
actions; the concrete pynput calls live in the input backend.  Canonical
names are lower case and separator-insensitive on input (so ``"Left Click"``,
``"left-click"`` and ``"left"`` all resolve to ``"left"``).
"""

from __future__ import annotations

import re

__all__ = [
    "MOUSE_ACTIONS",
    "MouseSpecError",
    "normalize_mouse",
    "is_valid_mouse",
    "describe_mouse",
]


class MouseSpecError(ValueError):
    """Raised when a mouse action string cannot be understood."""


#: Canonical mouse actions the engine can perform (at the current cursor
#: position).
MOUSE_ACTIONS: tuple[str, ...] = (
    "left",
    "right",
    "middle",
    "double",
    "left_down",
    "left_up",
    "scroll_up",
    "scroll_down",
)

#: Friendly labels for the UI dropdown / step descriptions.
MOUSE_LABELS: dict[str, str] = {
    "left": "left click",
    "right": "right click",
    "middle": "middle click",
    "double": "double click",
    "left_down": "left hold (down)",
    "left_up": "left release (up)",
    "scroll_up": "scroll up",
    "scroll_down": "scroll down",
}

# Aliases (in separator-free form) that map onto a canonical action.
_ALIASES = {
    "leftclick": "left",
    "lclick": "left",
    "lmb": "left",
    "click": "left",
    "rightclick": "right",
    "rclick": "right",
    "rmb": "right",
    "middleclick": "middle",
    "mclick": "middle",
    "mmb": "middle",
    "doubleclick": "double",
    "dblclick": "double",
    "doubleleft": "double",
    "leftpress": "left_down",
    "holdleft": "left_down",
    "leftrelease": "left_up",
    "releaseleft": "left_up",
    "scrollup": "scroll_up",
    "wheelup": "scroll_up",
    "scrolldown": "scroll_down",
    "wheeldown": "scroll_down",
}


def _compact(value: str) -> str:
    return re.sub(r"[\s\-_]+", "", value.strip().lower())


# Precompute a "compact form -> canonical" lookup for all canonical actions
# and their aliases.
_COMPACT_TO_CANONICAL: dict[str, str] = {}
for _action in MOUSE_ACTIONS:
    _COMPACT_TO_CANONICAL[_compact(_action)] = _action
for _alias, _target in _ALIASES.items():
    _COMPACT_TO_CANONICAL[_compact(_alias)] = _target


def normalize_mouse(value: str) -> str:
    """Return the canonical mouse action for *value*.

    Raises :class:`MouseSpecError` if the value is empty or not a recognised
    mouse action.
    """

    if value is None or not value.strip():
        raise MouseSpecError("Empty mouse action")
    canonical = _COMPACT_TO_CANONICAL.get(_compact(value))
    if canonical is None:
        raise MouseSpecError(f"Unknown mouse action: {value!r}")
    return canonical


def is_valid_mouse(value: str) -> bool:
    """Return ``True`` if *value* names a supported mouse action."""

    try:
        normalize_mouse(value)
        return True
    except MouseSpecError:
        return False


def describe_mouse(value: str) -> str:
    """A friendly label for a (possibly non-canonical) mouse action value."""

    try:
        return MOUSE_LABELS[normalize_mouse(value)]
    except MouseSpecError:
        return value
