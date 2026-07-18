"""Tests for the mouse action spec parser."""

import pytest

from automacro.mousespec import (
    MOUSE_ACTIONS,
    MouseSpecError,
    describe_mouse,
    is_valid_mouse,
    normalize_mouse,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("left", "left"),
        ("Left Click", "left"),
        ("left-click", "left"),
        ("LMB", "left"),
        ("right click", "right"),
        ("RMB", "right"),
        ("middle", "middle"),
        ("double", "double"),
        ("Double Click", "double"),
        ("dblclick", "double"),
        ("scroll up", "scroll_up"),
        ("wheelup", "scroll_up"),
        ("scroll_down", "scroll_down"),
        ("hold left", "left_down"),
        ("left release", "left_up"),
    ],
)
def test_normalize_mouse(raw, expected):
    assert normalize_mouse(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "spin", "leftx", "click2"])
def test_invalid_mouse(raw):
    assert not is_valid_mouse(raw)
    with pytest.raises(MouseSpecError):
        normalize_mouse(raw)


def test_all_canonical_actions_are_valid():
    for action in MOUSE_ACTIONS:
        assert is_valid_mouse(action)
        assert normalize_mouse(action) == action


def test_describe_mouse():
    assert describe_mouse("left") == "left click"
    assert describe_mouse("scroll_up") == "scroll up"
    # Unknown values are echoed back rather than raising.
    assert describe_mouse("???") == "???"
