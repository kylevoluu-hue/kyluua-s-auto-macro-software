"""Loading and saving :class:`~automacro.models.AppConfig` to disk.

Config is stored as a single JSON file in the per-user config directory.
Writes are atomic (write to a temp file, then ``os.replace``) so an
interrupted save can never corrupt an existing config.  Loading is
defensive: a missing or unreadable file simply yields a fresh default
config rather than an error.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from . import APP_NAME
from .models import AppConfig

__all__ = ["config_dir", "config_path", "load_config", "save_config"]


def config_dir() -> Path:
    """Return the directory where AutoMacro stores its files.

    Uses :mod:`platformdirs` when available for correct per-OS locations,
    otherwise falls back to a sensible ``~/.config`` style path.
    """

    try:
        import platformdirs

        return Path(platformdirs.user_config_dir(APP_NAME, appauthor=False))
    except Exception:  # pragma: no cover - fallback path
        base = os.environ.get("APPDATA") or os.path.join(
            os.path.expanduser("~"), ".config"
        )
        return Path(base) / APP_NAME


def config_path() -> Path:
    """Full path to the ``config.json`` file."""

    return config_dir() / "config.json"


def load_config(path: Path | None = None) -> AppConfig:
    """Load config from *path* (default location if omitted).

    Returns a freshly seeded default config when the file does not exist or
    cannot be parsed, so callers always get a usable object.
    """

    path = path or config_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return AppConfig.default()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return AppConfig.default()

    if not isinstance(data, dict):
        return AppConfig.default()
    return AppConfig.from_dict(data)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    """Persist *config* atomically and return the path written to."""

    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(config.to_dict(), indent=2, ensure_ascii=False)

    # Write to a temp file in the same directory, then atomically replace so
    # a crash mid-write cannot corrupt the previous good config.
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=".config-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        # Best-effort cleanup of the temp file on any failure.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return path
