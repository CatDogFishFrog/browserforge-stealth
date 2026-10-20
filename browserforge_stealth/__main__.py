"""
Executable module entry point for `python -m browserforge_stealth`.
"""

from __future__ import annotations

import sys

from browserforge_stealth.cli import main

if __name__ == "__main__":
    sys.exit(main())
