"""Application entry point and command-line interface.

Running with no arguments launches the desktop GUI.  ``--doctor`` prints a
diagnostic report (useful for support and CI) without opening a window, and
``--version`` prints the version.
"""

from __future__ import annotations

import argparse
import sys

from . import APP_ID, APP_NAME, __version__


def _set_windows_app_id() -> None:
    """Give Windows an explicit AppUserModelID.

    Without this a pinned shortcut and the running process can end up as
    separate taskbar entries; setting it makes pinning and icon grouping
    behave as users expect.
    """

    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def doctor() -> int:
    """Print an environment / capability report and return an exit code."""

    from .backends import create_input_backend, create_window_backend
    from .config import config_path
    from .hotkeys import create_hotkey_manager

    inp = create_input_backend()
    win = create_window_backend()
    hk = create_hotkey_manager()

    def mark(ok: bool) -> str:
        return "available" if ok else "UNAVAILABLE"

    print(f"{APP_NAME} {__version__} — diagnostics")
    print(f"  Python           : {sys.version.split()[0]} ({sys.platform})")
    print(f"  Config file      : {config_path()}")
    print(f"  Keyboard input   : {mark(getattr(inp, 'available', False))}")
    if not getattr(inp, "available", False):
        print(f"      reason       : {getattr(inp, 'reason', 'unknown')}")
    print(f"  Window targeting : {mark(getattr(win, 'available', False))}")
    if not getattr(win, "available", False):
        print(f"      reason       : {getattr(win, 'reason', 'unknown')}")
    print(f"  Global hotkeys   : {mark(getattr(hk, 'available', False))}")
    if not getattr(hk, "available", False):
        print(f"      reason       : {getattr(hk, 'reason', 'unknown')}")

    ready = getattr(inp, "available", False)
    print()
    print("  Status: " + ("ready to run macros." if ready else
                          "keyboard input unavailable — GUI will open but cannot send keys."))
    return 0 if ready else 1


def launch_gui() -> int:
    _set_windows_app_id()
    try:
        from .ui import run_app
    except Exception as exc:  # pragma: no cover - depends on runtime env
        sys.stderr.write(
            f"{APP_NAME}: could not start the graphical interface: {exc}\n"
            "The GUI needs 'customtkinter' and a desktop session.\n"
            "Install dependencies with:  pip install -r requirements.txt\n"
            "Run 'automacro --doctor' to check your environment.\n"
        )
        return 2
    return run_app()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="automacro",
        description=f"{APP_NAME} — configurable hotkey macro automation for any app.",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="print an environment/capability report and exit",
    )
    args = parser.parse_args(argv)

    if args.doctor:
        return doctor()
    return launch_gui()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
