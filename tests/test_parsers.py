"""Tests for the pure parsing/formatting helpers in backends and hotkeys."""

import pytest

from automacro.backends.window_linux import parse_wmctrl
from automacro.backends.window_macos import parse_list_output
from automacro.hotkeys import to_pynput_hotkey
from automacro.keyspec import KeySpecError


def test_parse_wmctrl():
    text = (
        "0x03000007  0 host Firefox\n"
        "0x05200003  0 host Untitled - Notepad\n"
        "0x05200004 -1 host \n"  # empty title dropped
        "garbage line\n"
    )
    windows = parse_wmctrl(text)
    assert [w.title for w in windows] == ["Firefox", "Untitled - Notepad"]
    assert windows[0].handle == "0x03000007"


def test_parse_macos_list():
    text = "Safari\tStart Page\nNotes\tGrocery list\nFinder\t\nSafari\tStart Page\n"
    windows = parse_list_output(text)
    # Empty title dropped; exact duplicate collapsed.
    assert [(w.process, w.title) for w in windows] == [
        ("Safari", "Start Page"),
        ("Notes", "Grocery list"),
    ]


@pytest.mark.parametrize(
    "spec,expected",
    [
        ("ctrl+shift+a", "<ctrl>+<shift>+a"),
        ("f6", "<f6>"),
        ("esc", "<esc>"),
        ("a", "a"),
        ("ctrl+c", "<ctrl>+c"),
        ("alt+f4", "<alt>+<f4>"),
    ],
)
def test_to_pynput_hotkey(spec, expected):
    assert to_pynput_hotkey(spec) == expected


def test_to_pynput_hotkey_invalid():
    with pytest.raises(KeySpecError):
        to_pynput_hotkey("ctrl+ctrl")  # no main key
