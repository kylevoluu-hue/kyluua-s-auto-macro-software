"""Graphical interface for AutoMacro (customtkinter).

This subpackage is imported lazily by :func:`automacro.app.main` so that the
core package remains importable without a GUI toolkit installed.
"""

from __future__ import annotations

__all__ = ["run_app"]


def run_app() -> int:
    """Launch the AutoMacro desktop application.  Returns a process exit code."""

    from .app_window import run_app as _run

    return _run()
