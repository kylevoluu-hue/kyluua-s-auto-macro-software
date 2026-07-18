"""Window enumeration and focusing on macOS via AppleScript (``osascript``).

Listing and activating windows uses System Events, which requires the app
(or the terminal/Python running it) to be granted Accessibility permission
in *System Settings -> Privacy & Security -> Accessibility*.  Without it the
list simply comes back empty and the engine falls back to sending keys to
whatever is focused.
"""

from __future__ import annotations

import subprocess

from .base import WindowInfo

_LIST_SCRIPT = r"""
tell application "System Events"
    set output to ""
    repeat with proc in (every process whose background only is false)
        set procName to name of proc
        try
            repeat with win in (every window of proc)
                set output to output & procName & "\t" & (name of win) & linefeed
            end repeat
        end try
    end repeat
end tell
return output
"""

_ACTIVE_SCRIPT = r"""
tell application "System Events"
    set procName to name of (first process whose frontmost is true)
    try
        set winName to name of front window of (first process whose frontmost is true)
    on error
        set winName to ""
    end try
end tell
return procName & "\t" & winName
"""


def parse_list_output(text: str) -> list[WindowInfo]:
    """Parse ``process\\ttitle`` lines into :class:`WindowInfo` objects."""

    results: list[WindowInfo] = []
    seen: set[tuple[str, str]] = set()
    for line in text.splitlines():
        if "\t" not in line:
            continue
        proc, _, title = line.partition("\t")
        proc, title = proc.strip(), title.strip()
        if not title:
            continue
        key = (proc, title)
        if key in seen:
            continue
        seen.add(key)
        # Handle stores the owning process name; activation targets the app.
        results.append(WindowInfo(title=title, handle=proc, process=proc))
    return results


class MacWindowBackend:
    def __init__(self) -> None:
        import shutil

        self._osascript = shutil.which("osascript")
        if not self._osascript:  # pragma: no cover - depends on OS
            raise RuntimeError("osascript not found")

    @property
    def available(self) -> bool:
        return self._osascript is not None

    def _run(self, script: str, timeout: float = 4.0) -> str:
        try:
            proc = subprocess.run(
                [self._osascript, "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return proc.stdout
        except Exception:
            return ""

    def list_windows(self) -> list[WindowInfo]:
        return parse_list_output(self._run(_LIST_SCRIPT))

    def active_window(self) -> WindowInfo | None:
        out = self._run(_ACTIVE_SCRIPT).strip()
        if "\t" not in out:
            return None
        proc, _, title = out.partition("\t")
        return WindowInfo(title=title.strip(), handle=proc.strip(), process=proc.strip())

    def activate(self, window: WindowInfo) -> bool:
        proc = window.handle or window.process
        if not proc:
            return False
        # Escape embedded quotes for the AppleScript string literal.
        safe = str(proc).replace('"', '\\"')
        script = f'tell application "System Events" to set frontmost of process "{safe}" to true'
        result = subprocess.run(
            [self._osascript, "-e", script], capture_output=True, text=True
        )
        return result.returncode == 0
