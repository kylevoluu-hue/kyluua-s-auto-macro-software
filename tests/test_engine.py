"""Tests for the macro execution engine."""

import random
import threading
import time

import pytest

from automacro.backends.base import WindowInfo
from automacro.engine import EngineListener, MacroEngine, window_matches
from automacro.models import ActionType, Macro, MatchMode, Step

from fakes import FakeInput, FakeWindows


class Recorder(EngineListener):
    """Captures engine callbacks and signals when the run has stopped."""

    def __init__(self) -> None:
        self.states: list[bool] = []
        self.statuses: list[str] = []
        self.errors: list[str] = []
        self.loops: list[tuple[int, int]] = []
        self.steps: list[int] = []
        self.stopped = threading.Event()

    def state_changed(self, running: bool) -> None:
        self.states.append(running)
        if not running:
            self.stopped.set()

    def status(self, message: str) -> None:
        self.statuses.append(message)

    def loop_completed(self, completed: int, total: int) -> None:
        self.loops.append((completed, total))

    def step_executed(self, index: int, step) -> None:
        self.steps.append(index)

    def error(self, message: str) -> None:
        self.errors.append(message)


def run_to_completion(engine: MacroEngine, macro: Macro, rec: Recorder, timeout=3.0):
    assert engine.start(macro)
    assert rec.stopped.wait(timeout), "engine did not stop within timeout"
    # Give the worker thread a beat to fully unwind.
    time.sleep(0.01)
    assert not engine.is_running


# -- window_matches --------------------------------------------------------


@pytest.mark.parametrize(
    "title,query,mode,expected",
    [
        ("Untitled - Notepad", "notepad", MatchMode.CONTAINS, True),
        ("Untitled - Notepad", "Word", MatchMode.CONTAINS, False),
        ("Notepad", "notepad", MatchMode.EXACT, True),
        ("Untitled - Notepad", "notepad", MatchMode.EXACT, False),
        ("Notepad - file", "notepad", MatchMode.STARTS_WITH, True),
        ("My Notepad", "notepad", MatchMode.STARTS_WITH, False),
        ("Chrome v123", r"v\d+", MatchMode.REGEX, True),
        ("Chrome", r"v\d+", MatchMode.REGEX, False),
        ("anything", "", MatchMode.CONTAINS, True),  # empty query matches all
        ("x", "(", MatchMode.REGEX, False),  # invalid regex never raises
    ],
)
def test_window_matches(title, query, mode, expected):
    assert window_matches(title, query, mode) is expected


# -- basic execution -------------------------------------------------------


def test_runs_all_step_types_in_order():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        name="mix",
        steps=[
            Step(action=ActionType.TEXT, value="hi", delay_after_ms=0),
            Step(action=ActionType.KEY, value="enter", delay_after_ms=0),
            Step(action=ActionType.HOTKEY, value="ctrl+s", delay_after_ms=0),
            Step(action=ActionType.DELAY, value="1", delay_after_ms=0),
        ],
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)

    assert inp.calls == [
        ("text", "hi"),
        ("tap", "enter", 1),
        ("hotkey", ("ctrl", "s")),
    ]
    assert rec.loops == [(1, 1)]
    assert rec.errors == []
    assert rec.states[0] is True and rec.states[-1] is False


def test_repeat_counts():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[
            Step(action=ActionType.KEY, value="a", repeat=3, delay_after_ms=0),
            Step(action=ActionType.TEXT, value="x", repeat=2, delay_after_ms=0),
            Step(action=ActionType.HOTKEY, value="ctrl+c", repeat=2, delay_after_ms=0),
        ],
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)

    assert inp.calls == [
        ("tap", "a", 3),  # key repeat is passed as presses
        ("text", "x"),
        ("text", "x"),
        ("hotkey", ("ctrl", "c")),
        ("hotkey", ("ctrl", "c")),
    ]


def test_mouse_actions_execute_with_repeat_and_aliases():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[
            Step(action=ActionType.MOUSE, value="left", delay_after_ms=0),
            Step(action=ActionType.MOUSE, value="Right Click", delay_after_ms=0),
            Step(action=ActionType.MOUSE, value="scroll_up", repeat=3, delay_after_ms=0),
            Step(action=ActionType.MOUSE, value="double", delay_after_ms=0),
        ],
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)

    assert inp.calls == [
        ("mouse", "left"),
        ("mouse", "right"),  # alias normalised
        ("mouse", "scroll_up"),
        ("mouse", "scroll_up"),
        ("mouse", "scroll_up"),
        ("mouse", "double"),
    ]
    assert rec.errors == []


def test_invalid_mouse_action_reports_error():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[Step(action=ActionType.MOUSE, value="wiggle", delay_after_ms=0)],
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)
    assert rec.errors
    assert "mouse" in rec.errors[0].lower()
    assert rec.states[-1] is False


def test_disabled_steps_are_skipped():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[
            Step(action=ActionType.KEY, value="a", enabled=False, delay_after_ms=0),
            Step(action=ActionType.KEY, value="b", delay_after_ms=0),
        ],
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)
    assert inp.calls == [("tap", "b", 1)]


def test_finite_loops():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[Step(action=ActionType.KEY, value="a", delay_after_ms=0)],
        start_delay_ms=0,
        loops=3,
        loop_cooldown_ms=0,
    )
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)
    assert inp.calls == [("tap", "a", 1)] * 3
    assert rec.loops == [(1, 3), (2, 3), (3, 3)]


def test_delay_step_tolerates_float_and_garbage_values():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[
            Step(action=ActionType.DELAY, value="0.0", delay_after_ms=0),
            Step(action=ActionType.DELAY, value="not-a-number", delay_after_ms=0),
            Step(action=ActionType.KEY, value="a", delay_after_ms=0),
        ],
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)
    assert inp.calls == [("tap", "a", 1)]
    assert rec.errors == []


def test_empty_macro_does_nothing():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(steps=[], start_delay_ms=0, loops=1)
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)
    assert inp.calls == []
    assert any("no enabled steps" in s for s in rec.statuses)


# -- stopping --------------------------------------------------------------


def test_infinite_loop_stops_promptly():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[Step(action=ActionType.KEY, value="a", delay_after_ms=5)],
        start_delay_ms=0,
        loops=0,  # infinite
        loop_cooldown_ms=5,
    )
    engine = MacroEngine(inp, listener=rec)
    assert engine.start(macro)
    time.sleep(0.1)
    assert engine.is_running
    t0 = time.monotonic()
    engine.stop(wait=True, timeout=2)
    assert (time.monotonic() - t0) < 1.0
    assert not engine.is_running
    assert len(inp.calls) >= 1


def test_cannot_start_twice():
    inp = FakeInput()
    macro = Macro(
        steps=[Step(action=ActionType.KEY, value="a", delay_after_ms=50)],
        start_delay_ms=0,
        loops=0,
    )
    engine = MacroEngine(inp)
    assert engine.start(macro) is True
    try:
        assert engine.start(macro) is False  # already running
    finally:
        engine.stop(wait=True)


def test_toggle():
    inp = FakeInput()
    macro = Macro(
        steps=[Step(action=ActionType.KEY, value="a", delay_after_ms=50)],
        start_delay_ms=0,
        loops=0,
    )
    engine = MacroEngine(inp)
    assert engine.toggle(macro) is True
    time.sleep(0.05)
    assert engine.toggle(macro) is False
    engine.stop(wait=True)


def test_start_delay_is_interruptible():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[Step(action=ActionType.KEY, value="a")],
        start_delay_ms=5000,
        loops=1,
    )
    engine = MacroEngine(inp, listener=rec)
    engine.start(macro)
    engine.stop(wait=True, timeout=2)
    assert not engine.is_running
    assert inp.calls == []  # never got past the start delay


# -- window targeting ------------------------------------------------------


def test_activate_target_focuses_window():
    inp = FakeInput()
    rec = Recorder()
    win = WindowInfo(title="Untitled - Notepad", process="notepad.exe")
    windows = FakeWindows([win])
    macro = Macro(
        steps=[Step(action=ActionType.KEY, value="a", delay_after_ms=0)],
        target_window="Notepad",
        activate_target=True,
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, window_backend=windows, listener=rec)
    run_to_completion(engine, macro, rec)
    assert windows.activated == ["Untitled - Notepad"]


def test_missing_target_reports_status_but_still_runs():
    inp = FakeInput()
    rec = Recorder()
    windows = FakeWindows([WindowInfo(title="Some Other App")])
    macro = Macro(
        steps=[Step(action=ActionType.KEY, value="a", delay_after_ms=0)],
        target_window="Notepad",
        activate_target=True,
        require_focus=False,
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, window_backend=windows, listener=rec)
    run_to_completion(engine, macro, rec)
    assert any("not found" in s for s in rec.statuses)
    assert inp.calls == [("tap", "a", 1)]  # still sends to current focus


def test_require_focus_waits_then_proceeds():
    inp = FakeInput()
    rec = Recorder()
    target = WindowInfo(title="Game Window")
    other = WindowInfo(title="Desktop")
    windows = FakeWindows([target])
    windows.set_active(other)  # target not focused yet
    macro = Macro(
        steps=[Step(action=ActionType.KEY, value="a", delay_after_ms=0)],
        target_window="Game",
        activate_target=False,  # do not auto-focus; test the gate itself
        require_focus=True,
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, window_backend=windows, listener=rec)
    engine.start(macro)
    time.sleep(0.15)
    assert inp.calls == []  # gated: waiting for focus
    windows.set_active(target)  # now focus the target
    assert rec.stopped.wait(3)
    assert inp.calls == [("tap", "a", 1)]
    assert any("focus" in s.lower() for s in rec.statuses)


# -- jitter ----------------------------------------------------------------


def test_jitter_is_deterministic_with_seeded_rng_and_never_negative():
    eng = MacroEngine(FakeInput(), rng=random.Random(1234))
    values = [eng._jitter(100, 0.5) for _ in range(1000)]
    assert all(v >= 0 for v in values)
    # Reproducible for the same seed.
    eng2 = MacroEngine(FakeInput(), rng=random.Random(1234))
    values2 = [eng2._jitter(100, 0.5) for _ in range(1000)]
    assert values == values2
    # No jitter requested => value unchanged.
    assert eng._jitter(100, 0.0) == 100


# -- error handling --------------------------------------------------------


def test_invalid_hotkey_reports_error():
    inp = FakeInput()
    rec = Recorder()
    macro = Macro(
        steps=[Step(action=ActionType.HOTKEY, value="ctrl+nope", delay_after_ms=0)],
        start_delay_ms=0,
        loops=1,
    )
    engine = MacroEngine(inp, listener=rec)
    run_to_completion(engine, macro, rec)
    assert rec.errors
    assert "Invalid key" in rec.errors[0]
    assert rec.states[-1] is False  # still cleaned up
