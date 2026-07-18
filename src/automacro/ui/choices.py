"""Curated key / hotkey lists for the selection dropdowns.

These give the user a pick-from-a-list experience instead of having to know
and type key names.  Every entry is a valid canonical spec understood by
:mod:`automacro.keyspec`, so a chosen value can be stored verbatim.
"""

from __future__ import annotations

# Single keys, most useful first, for "Key tap" steps.
KEY_CHOICES: list[str] = (
    [
        "enter",
        "esc",
        "tab",
        "space",
        "backspace",
        "delete",
        "up",
        "down",
        "left",
        "right",
        "home",
        "end",
        "page_up",
        "page_down",
        "insert",
    ]
    + [f"f{i}" for i in range(1, 13)]
    + list("abcdefghijklmnopqrstuvwxyz")
    + [str(d) for d in range(10)]
)

# Common hotkey combinations for "Hotkey" steps.
COMBO_CHOICES: list[str] = [
    "ctrl+c",
    "ctrl+v",
    "ctrl+x",
    "ctrl+z",
    "ctrl+y",
    "ctrl+a",
    "ctrl+s",
    "ctrl+f",
    "ctrl+w",
    "ctrl+t",
    "ctrl+n",
    "ctrl+p",
    "ctrl+r",
    "ctrl+enter",
    "shift+enter",
    "ctrl+shift+esc",
    "ctrl+shift+n",
    "ctrl+shift+t",
    "ctrl+shift+s",
    "alt+f4",
    "alt+tab",
    "alt+enter",
    "cmd+c",
    "cmd+v",
    "cmd+tab",
]

# A few handy presets for "Wait" steps (milliseconds).
DELAY_CHOICES: list[str] = ["50", "100", "250", "500", "1000", "2000", "5000"]

# Good global start/stop and emergency-stop keys (easy to reach, rarely
# clash with the target app). Function keys first.
TRIGGER_CHOICES: list[str] = (
    [f"f{i}" for i in (6, 7, 8, 9, 10, 1, 2, 3, 4, 5, 11, 12)]
    + [
        "esc",
        "pause",
        "scroll_lock",
        "insert",
        "home",
        "end",
        "page_up",
        "page_down",
    ]
    + ["ctrl+shift+s", "alt+shift+s", "ctrl+shift+x"]
)


def with_current(value: str, choices: list[str]) -> list[str]:
    """Return *choices* guaranteeing *value* is selectable (prepended if new).

    Lets a dropdown display and re-select a saved value that isn't one of the
    built-in presets.
    """

    value = (value or "").strip()
    if value and value not in choices:
        return [value, *choices]
    return list(choices)
