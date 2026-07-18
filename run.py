#!/usr/bin/env python3
"""Development / PyInstaller launch script.

Puts the ``src`` layout on the import path and starts the app.  This is the
entry script referenced by ``automacro.spec`` when building the standalone
executable, and it also works for a quick ``python run.py`` during dev.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from automacro.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
