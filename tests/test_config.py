"""Tests for config load/save behaviour."""

from automacro.config import load_config, save_config
from automacro.models import AppConfig, Macro


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = AppConfig(macros=[Macro(name="Mine")], theme="dark")
    save_config(cfg, path)
    assert path.exists()

    loaded = load_config(path)
    assert loaded.theme == "dark"
    assert [m.name for m in loaded.macros] == ["Mine"]


def test_load_missing_file_returns_default(tmp_path):
    cfg = load_config(tmp_path / "nope.json")
    assert isinstance(cfg, AppConfig)
    assert cfg.macros  # default seeds an example macro


def test_load_corrupt_file_returns_default(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ this is not json", encoding="utf-8")
    cfg = load_config(path)
    assert isinstance(cfg, AppConfig)
    assert cfg.macros


def test_load_non_object_json_returns_default(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    cfg = load_config(path)
    assert isinstance(cfg, AppConfig)


def test_save_is_atomic_no_temp_left_behind(tmp_path):
    path = tmp_path / "config.json"
    save_config(AppConfig.default(), path)
    # No leftover temp files in the directory.
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "config.json"]
    assert leftovers == []


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "deep" / "config.json"
    save_config(AppConfig.default(), path)
    assert path.exists()
