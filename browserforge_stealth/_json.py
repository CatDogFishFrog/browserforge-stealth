"""Fast JSON loading: uses ``orjson`` when installed, falls back to the standard library."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

loads: Callable[[str | bytes], Any]

try:
    import orjson

    loads = orjson.loads
except ImportError:  # pragma: no cover - depends on the optional extra
    loads = json.loads
