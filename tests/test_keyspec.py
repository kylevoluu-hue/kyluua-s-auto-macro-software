"""Tests for the key / hotkey specification parser."""

import pytest

from automacro import keyspec
from automacro.keyspec import KeySpecError, Hotkey


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Control", "ctrl"),
        ("CTL", "ctrl"),
        ("Return", "enter"),
        ("Escape", "esc"),
        ("Win", "cmd"),
        ("super", "cmd"),
        ("Page Up", "page_up"),
        ("arrow-left", "left"),
        ("F5", "f5"),
        ("A", "a"),
    ],
)
def test_normalize_name(raw, expected):
    assert keyspec.normalize_name(raw) == expected


@pytest.mark.parametrize(
    "name",
    ["a", "Z", "5", "enter", "f12", "ctrl", "cmd", "space", "!", "page_down"],
)
def test_valid_keys(name):
    assert keyspec.is_valid_key(name)


@pytest.mark.parametrize("name", ["", "  ", "notakey", "f99", "ctrlx"])
def test_invalid_keys(name):
    assert not keyspec.is_valid_key(name)


def test_parse_simple_combo():
    hk = keyspec.parse_hotkey("ctrl+shift+a")
    assert hk == Hotkey(modifiers=("ctrl", "shift"), key="a")
    assert hk.as_names() == ("ctrl", "shift", "a")


def test_parse_reorders_modifiers_canonically():
    # shift given before ctrl should still come out in canonical order.
    hk = keyspec.parse_hotkey("shift+ctrl+alt+delete")
    assert hk.modifiers == ("ctrl", "alt", "shift")
    assert hk.key == "delete"


def test_parse_aliases():
    hk = keyspec.parse_hotkey("control+Return")
    assert hk == Hotkey(modifiers=("ctrl",), key="enter")


def test_parse_single_key():
    hk = keyspec.parse_hotkey("f5")
    assert hk.modifiers == ()
    assert hk.key == "f5"


def test_parse_dedupes_modifiers():
    hk = keyspec.parse_hotkey("ctrl+ctrl+c")
    assert hk.modifiers == ("ctrl",)
    assert hk.key == "c"


@pytest.mark.parametrize(
    "spec",
    ["", "   ", "ctrl", "ctrl+shift", "ctrl+a+b", "ctrl+nope", "+", "a+b"],
)
def test_parse_errors(spec):
    with pytest.raises(KeySpecError):
        keyspec.parse_hotkey(spec)


def test_format_roundtrip():
    hk = keyspec.parse_hotkey("ctrl+shift+f4")
    assert keyspec.format_hotkey(hk) == "ctrl+shift+f4"
    assert str(hk) == "ctrl+shift+f4"
