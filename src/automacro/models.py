"""Serializable data models for macros, steps and application config.

Everything here is plain-old-data built on :mod:`dataclasses` with explicit
``to_dict`` / ``from_dict`` helpers.  The ``from_dict`` methods are written
to be tolerant of missing or unexpected keys so that config written by an
older or newer build still loads instead of crashing the app.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return default


class ActionType(str, Enum):
    """The kind of action a single macro step performs."""

    KEY = "key"  # tap a single key, ``value`` is a key name e.g. "enter"
    HOTKEY = "hotkey"  # a combo, ``value`` is e.g. "ctrl+shift+a"
    TEXT = "text"  # type a literal string, ``value`` is the text
    DELAY = "delay"  # wait, ``value`` is a number of milliseconds

    @classmethod
    def coerce(cls, value: Any, default: "ActionType" = None) -> "ActionType":
        default = default or cls.KEY
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            return default


class MatchMode(str, Enum):
    """How a target window title is compared against open windows."""

    CONTAINS = "contains"
    EXACT = "exact"
    STARTS_WITH = "starts_with"
    REGEX = "regex"

    @classmethod
    def coerce(cls, value: Any, default: "MatchMode" = None) -> "MatchMode":
        default = default or cls.CONTAINS
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            return default


@dataclass
class Step:
    """A single action within a macro.

    ``delay_after_ms`` is the cooldown applied *after* the step runs.  For a
    :attr:`ActionType.DELAY` step, ``value`` itself holds the number of
    milliseconds to wait.  ``repeat`` runs the same action several times
    before moving on (ignored for DELAY).
    """

    action: ActionType = ActionType.KEY
    value: str = ""
    delay_after_ms: int = 50
    repeat: int = 1
    enabled: bool = True
    id: str = field(default_factory=_new_id)

    def describe(self) -> str:
        """A short, human-readable one-line summary for the UI."""

        if self.action is ActionType.DELAY:
            return f"Wait {_as_int(self.value, 0)} ms"
        rep = f" x{self.repeat}" if self.repeat > 1 else ""
        if self.action is ActionType.TEXT:
            preview = self.value if len(self.value) <= 40 else self.value[:37] + "..."
            return f'Type "{preview}"{rep}'
        if self.action is ActionType.HOTKEY:
            return f"Hotkey {self.value}{rep}"
        return f"Key {self.value}{rep}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "value": self.value,
            "delay_after_ms": self.delay_after_ms,
            "repeat": self.repeat,
            "enabled": self.enabled,
            "id": self.id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Step":
        return cls(
            action=ActionType.coerce(data.get("action")),
            value=str(data.get("value", "")),
            delay_after_ms=max(0, _as_int(data.get("delay_after_ms"), 50)),
            repeat=max(1, _as_int(data.get("repeat"), 1)),
            enabled=_as_bool(data.get("enabled"), True),
            id=str(data.get("id") or _new_id()),
        )


@dataclass
class Macro:
    """A named sequence of steps plus its execution / cooldown settings."""

    name: str = "New Macro"
    steps: list[Step] = field(default_factory=list)

    # --- Target application selection -------------------------------------
    target_window: str = ""  # window-title query; empty => whatever is focused
    match_mode: MatchMode = MatchMode.CONTAINS
    activate_target: bool = True  # bring the target to the foreground first
    require_focus: bool = False  # only send keys while the target is focused

    # --- Configurable cooldowns / timing ----------------------------------
    start_delay_ms: int = 500  # delay before the very first run
    loop_cooldown_ms: int = 1000  # cooldown between full repeats of the macro
    loops: int = 1  # number of times to run the sequence; 0 => infinite
    jitter_pct: float = 0.0  # 0..1 random variance applied to every delay

    # --- Trigger ----------------------------------------------------------
    trigger_hotkey: str = "f6"  # global hotkey that starts/stops this macro

    id: str = field(default_factory=_new_id)

    def enabled_steps(self) -> list[Step]:
        return [s for s in self.steps if s.enabled]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
            "target_window": self.target_window,
            "match_mode": self.match_mode.value,
            "activate_target": self.activate_target,
            "require_focus": self.require_focus,
            "start_delay_ms": self.start_delay_ms,
            "loop_cooldown_ms": self.loop_cooldown_ms,
            "loops": self.loops,
            "jitter_pct": self.jitter_pct,
            "trigger_hotkey": self.trigger_hotkey,
            "id": self.id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Macro":
        steps_data = data.get("steps") or []
        steps = [Step.from_dict(s) for s in steps_data if isinstance(s, dict)]
        return cls(
            name=str(data.get("name", "New Macro")),
            steps=steps,
            target_window=str(data.get("target_window", "")),
            match_mode=MatchMode.coerce(data.get("match_mode")),
            activate_target=_as_bool(data.get("activate_target"), True),
            require_focus=_as_bool(data.get("require_focus"), False),
            start_delay_ms=max(0, _as_int(data.get("start_delay_ms"), 500)),
            loop_cooldown_ms=max(0, _as_int(data.get("loop_cooldown_ms"), 1000)),
            loops=max(0, _as_int(data.get("loops"), 1)),
            jitter_pct=min(1.0, max(0.0, _as_float(data.get("jitter_pct"), 0.0))),
            trigger_hotkey=str(data.get("trigger_hotkey", "f6")),
            id=str(data.get("id") or _new_id()),
        )


@dataclass
class AppConfig:
    """Top-level application configuration persisted to disk."""

    version: int = 1
    macros: list[Macro] = field(default_factory=list)
    active_macro_id: str | None = None
    panic_hotkey: str = "esc"  # global emergency-stop hotkey
    theme: str = "system"  # system | dark | light
    reactivate_each_loop: bool = True  # re-focus the target before each loop

    def get_macro(self, macro_id: str | None) -> Macro | None:
        if macro_id is None:
            return None
        for macro in self.macros:
            if macro.id == macro_id:
                return macro
        return None

    def active_macro(self) -> Macro | None:
        macro = self.get_macro(self.active_macro_id)
        if macro is None and self.macros:
            return self.macros[0]
        return macro

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "macros": [m.to_dict() for m in self.macros],
            "active_macro_id": self.active_macro_id,
            "panic_hotkey": self.panic_hotkey,
            "theme": self.theme,
            "reactivate_each_loop": self.reactivate_each_loop,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        macros_data = data.get("macros") or []
        macros = [Macro.from_dict(m) for m in macros_data if isinstance(m, dict)]
        active_id = data.get("active_macro_id")
        # Drop a dangling active id that no longer points at a real macro.
        if active_id is not None and not any(m.id == active_id for m in macros):
            active_id = macros[0].id if macros else None
        return cls(
            version=_as_int(data.get("version"), 1),
            macros=macros,
            active_macro_id=active_id,
            panic_hotkey=str(data.get("panic_hotkey", "esc")),
            theme=str(data.get("theme", "system")),
            reactivate_each_loop=_as_bool(data.get("reactivate_each_loop"), True),
        )

    @classmethod
    def default(cls) -> "AppConfig":
        """A config seeded with one illustrative example macro."""

        example = Macro(
            name="Example: type greeting",
            steps=[
                Step(action=ActionType.TEXT, value="Hello from AutoMacro!", delay_after_ms=100),
                Step(action=ActionType.KEY, value="enter", delay_after_ms=100),
            ],
            loops=1,
            start_delay_ms=1000,
        )
        return cls(macros=[example], active_macro_id=example.id)
