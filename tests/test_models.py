"""Tests for the serializable data models."""

from automacro.models import ActionType, AppConfig, Macro, MatchMode, Step


def test_step_roundtrip():
    step = Step(action=ActionType.HOTKEY, value="ctrl+c", delay_after_ms=120, repeat=3)
    restored = Step.from_dict(step.to_dict())
    assert restored == step


def test_step_from_dict_defaults_and_coercion():
    step = Step.from_dict({"action": "TEXT", "value": 123, "delay_after_ms": "40"})
    assert step.action is ActionType.TEXT
    assert step.value == "123"
    assert step.delay_after_ms == 40
    assert step.repeat == 1
    assert step.enabled is True
    assert step.id  # auto-generated


def test_step_from_dict_bad_action_falls_back():
    step = Step.from_dict({"action": "explode"})
    assert step.action is ActionType.KEY


def test_step_negative_values_clamped():
    step = Step.from_dict({"delay_after_ms": -50, "repeat": 0})
    assert step.delay_after_ms == 0
    assert step.repeat == 1


def test_step_describe():
    assert "Wait" in Step(action=ActionType.DELAY, value="200").describe()
    assert Step(action=ActionType.KEY, value="enter", repeat=2).describe() == "Key enter x2"
    long_text = "x" * 100
    d = Step(action=ActionType.TEXT, value=long_text).describe()
    assert d.endswith('..."')


def test_macro_roundtrip():
    macro = Macro(
        name="Combo",
        steps=[
            Step(action=ActionType.KEY, value="a"),
            Step(action=ActionType.DELAY, value="500"),
        ],
        target_window="Notepad",
        match_mode=MatchMode.EXACT,
        loops=0,
        jitter_pct=0.2,
        trigger_hotkey="f7",
    )
    restored = Macro.from_dict(macro.to_dict())
    assert restored.name == "Combo"
    assert restored.match_mode is MatchMode.EXACT
    assert restored.loops == 0
    assert restored.jitter_pct == 0.2
    assert len(restored.steps) == 2
    assert restored.steps[1].action is ActionType.DELAY


def test_macro_jitter_clamped():
    assert Macro.from_dict({"jitter_pct": 5}).jitter_pct == 1.0
    assert Macro.from_dict({"jitter_pct": -3}).jitter_pct == 0.0


def test_macro_enabled_steps():
    macro = Macro(
        steps=[
            Step(value="a", enabled=True),
            Step(value="b", enabled=False),
            Step(value="c", enabled=True),
        ]
    )
    assert [s.value for s in macro.enabled_steps()] == ["a", "c"]


def test_config_roundtrip_and_active_selection():
    cfg = AppConfig.default()
    restored = AppConfig.from_dict(cfg.to_dict())
    assert restored.active_macro_id == cfg.active_macro_id
    assert restored.active_macro() is not None
    assert restored.active_macro().id == cfg.active_macro_id


def test_config_drops_dangling_active_id():
    cfg = AppConfig(macros=[Macro(name="A")], active_macro_id="does-not-exist")
    restored = AppConfig.from_dict(cfg.to_dict())
    # Falls back to the first available macro's id.
    assert restored.active_macro_id == cfg.macros[0].id


def test_config_get_macro():
    m = Macro(name="findme")
    cfg = AppConfig(macros=[m])
    assert cfg.get_macro(m.id) is m
    assert cfg.get_macro("nope") is None
    assert cfg.get_macro(None) is None


def test_config_ignores_garbage_entries():
    cfg = AppConfig.from_dict({"macros": ["nonsense", 42, {"name": "ok"}]})
    assert len(cfg.macros) == 1
    assert cfg.macros[0].name == "ok"
