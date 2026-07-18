"""The macro execution engine.

:class:`MacroEngine` runs a :class:`~automacro.models.Macro` on a background
thread, honouring every configurable cooldown (start delay, per-step delay,
between-loop cooldown) and optional timing jitter.  It talks to the outside
world only through the injected :class:`~automacro.backends.base.InputBackend`
and optional :class:`~automacro.backends.base.WindowBackend`, which makes the
whole engine testable with fakes and free of any GUI or OS dependency.

All waiting is done via a :class:`threading.Event`, so a running macro stops
promptly (within a small quantum) the instant :meth:`MacroEngine.stop` is
called.
"""

from __future__ import annotations

import random
import re
import threading
from typing import Callable

from .backends.base import InputBackend, WindowBackend, WindowInfo
from .keyspec import KeySpecError, parse_hotkey
from .models import ActionType, Macro, MatchMode, Step
from .mousespec import MouseSpecError, normalize_mouse

__all__ = ["EngineListener", "MacroEngine", "window_matches"]

# Longest single wait between stop-flag checks.  Keeps long cooldowns
# responsive to a stop request without busy-waiting.
_WAIT_QUANTUM_S = 0.05


def window_matches(title: str, query: str, mode: MatchMode) -> bool:
    """Return ``True`` if window *title* satisfies *query* under *mode*.

    An empty query matches everything (meaning "no specific target").
    Matching is case-insensitive for the textual modes.  An invalid regex
    never raises here; it simply fails to match.
    """

    if not query:
        return True
    if mode is MatchMode.EXACT:
        return title.strip().lower() == query.strip().lower()
    if mode is MatchMode.STARTS_WITH:
        return title.lower().startswith(query.lower())
    if mode is MatchMode.REGEX:
        try:
            return re.search(query, title) is not None
        except re.error:
            return False
    # Default: CONTAINS
    return query.lower() in title.lower()


class EngineListener:
    """Callback surface for engine events.  Override what you care about.

    All methods are invoked from the engine's worker thread, so a GUI
    listener must marshal back onto the UI thread itself.
    """

    def state_changed(self, running: bool) -> None:  # noqa: D401
        """Called when the engine starts (``True``) or stops (``False``)."""

    def status(self, message: str) -> None:
        """A human-readable status update."""

    def loop_completed(self, completed: int, total: int) -> None:
        """One full pass over the steps finished (``total`` 0 => infinite)."""

    def step_executed(self, index: int, step: Step) -> None:
        """A single step finished executing."""

    def error(self, message: str) -> None:
        """An error aborted the run."""


class MacroEngine:
    """Runs macros on a worker thread with full stop control."""

    def __init__(
        self,
        input_backend: InputBackend,
        window_backend: WindowBackend | None = None,
        listener: EngineListener | None = None,
        reactivate_each_loop: bool = True,
        rng: random.Random | None = None,
    ) -> None:
        self._input = input_backend
        self._windows = window_backend
        self._listener = listener or EngineListener()
        self._reactivate_each_loop = reactivate_each_loop
        self._rng = rng or random.Random()

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # -- public API --------------------------------------------------------

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self, macro: Macro) -> bool:
        """Begin running *macro*.  Returns ``False`` if already running."""

        with self._lock:
            if self.is_running:
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                args=(macro,),
                name="AutoMacroEngine",
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self, wait: bool = False, timeout: float | None = 5.0) -> None:
        """Request the running macro to stop as soon as possible."""

        self._stop_event.set()
        if wait:
            thread = self._thread
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout)

    def toggle(self, macro: Macro) -> bool:
        """Start if idle, stop if running.  Returns the new running state."""

        if self.is_running:
            self.stop()
            return False
        return self.start(macro)

    # -- internals ---------------------------------------------------------

    def _sleep_ms(self, ms: float) -> bool:
        """Sleep for *ms* milliseconds, returning ``True`` if interrupted.

        Waits in short quanta on the stop event so the run reacts quickly to
        :meth:`stop` even during a long cooldown.
        """

        if ms <= 0:
            return self._stop_event.is_set()
        remaining = ms / 1000.0
        while remaining > 0:
            if self._stop_event.wait(min(_WAIT_QUANTUM_S, remaining)):
                return True
            remaining -= _WAIT_QUANTUM_S
        return self._stop_event.is_set()

    def _jitter(self, ms: float, jitter_pct: float) -> float:
        """Apply +/- jitter to a delay, never returning a negative value."""

        if jitter_pct <= 0 or ms <= 0:
            return ms
        factor = 1.0 + self._rng.uniform(-jitter_pct, jitter_pct)
        return max(0.0, ms * factor)

    def _find_target(self, macro: Macro) -> WindowInfo | None:
        if not macro.target_window or self._windows is None:
            return None
        for win in self._windows.list_windows():
            if window_matches(win.title, macro.target_window, macro.match_mode):
                return win
        return None

    def _focus_ok(self, macro: Macro) -> bool:
        """Whether the required target currently holds focus."""

        if self._windows is None:
            return True
        active = self._windows.active_window()
        if active is None:
            return True  # cannot tell; do not block
        return window_matches(active.title, macro.target_window, macro.match_mode)

    def _execute_step(self, step: Step) -> None:
        if step.action is ActionType.DELAY:
            try:
                self._sleep_ms(int(float(step.value)))
            except (TypeError, ValueError):
                pass
            return

        if step.action is ActionType.TEXT:
            for _ in range(max(1, step.repeat)):
                if self._stop_event.is_set():
                    return
                self._input.type_text(step.value)
            return

        if step.action is ActionType.HOTKEY:
            keys = parse_hotkey(step.value).as_names()  # may raise KeySpecError
            for _ in range(max(1, step.repeat)):
                if self._stop_event.is_set():
                    return
                self._input.hotkey(keys)
            return

        if step.action is ActionType.MOUSE:
            action = normalize_mouse(step.value)  # may raise MouseSpecError
            for _ in range(max(1, step.repeat)):
                if self._stop_event.is_set():
                    return
                self._input.mouse(action)
            return

        # ActionType.KEY
        self._input.tap(step.value, presses=max(1, step.repeat))

    def _prepare_target(self, macro: Macro, first: bool) -> bool:
        """Focus the target window if configured; return ``False`` to skip.

        Returns ``False`` when the macro requires focus but the target is not
        currently focused, signalling the caller to wait and retry.
        """

        target = self._find_target(macro)

        if macro.activate_target and target is not None:
            if first or self._reactivate_each_loop:
                self._windows.activate(target) if self._windows else None

        if macro.target_window and target is None:
            self._listener.status(f"Target window not found: {macro.target_window!r}")

        if macro.require_focus and not self._focus_ok(macro):
            return False
        return True

    def _run(self, macro: Macro) -> None:
        listener = self._listener
        try:
            listener.state_changed(True)

            steps = macro.enabled_steps()
            if not steps:
                listener.status("Macro has no enabled steps; nothing to do.")
                return

            listener.status(
                f"Starting in {macro.start_delay_ms} ms — switch to your target app."
            )
            if self._sleep_ms(macro.start_delay_ms):
                return

            loop = 0
            while not self._stop_event.is_set():
                if not self._prepare_target(macro, first=(loop == 0)):
                    listener.status("Waiting for target window to gain focus...")
                    if self._sleep_ms(250):
                        return
                    continue

                loop += 1
                listener.status(
                    f"Running loop {loop}"
                    + (f" of {macro.loops}" if macro.loops else " (infinite)")
                )

                for index, step in enumerate(steps):
                    if self._stop_event.is_set():
                        return
                    self._execute_step(step)
                    listener.step_executed(index, step)
                    if self._sleep_ms(self._jitter(step.delay_after_ms, macro.jitter_pct)):
                        return

                listener.loop_completed(loop, macro.loops)

                if macro.loops and loop >= macro.loops:
                    listener.status(f"Finished after {loop} loop(s).")
                    return
                if self._sleep_ms(self._jitter(macro.loop_cooldown_ms, macro.jitter_pct)):
                    return

        except KeySpecError as exc:
            listener.error(f"Invalid key in macro: {exc}")
        except MouseSpecError as exc:
            listener.error(f"Invalid mouse action in macro: {exc}")
        except Exception as exc:  # pragma: no cover - defensive catch-all
            listener.error(f"Macro run failed: {exc}")
        finally:
            self._stop_event.set()
            listener.state_changed(False)
