"""
Context options and init-script injection for Patchright and Playwright.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, cast

from browserforge.injectors.utils import InjectFunction

from browserforge_stealth.models import DeviceType, Fingerprint, coerce_device_type
from browserforge_stealth.retarget import retarget


class _Dumpable:
    """Lightweight adapter providing `.dumps()` required by InjectFunction."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._json = json.dumps(data, ensure_ascii=False)

    def dumps(self) -> str:
        return self._json


def context_options(fingerprint: Fingerprint, browser_version: str | None = None) -> dict[str, Any]:
    """Builds context dictionary suitable for browser.new_context(**options) for Patchright and Playwright."""
    retargeted = retarget(fingerprint, browser_version)
    user_agent = (
        retargeted.get("navigator", {}).get("userAgent")
        or retargeted.get("headers", {}).get("User-Agent")
        or fingerprint.user_agent
    )
    headers = retargeted.get("headers", {})
    client_hints = {k: v for k, v in headers.items() if k.lower() != "user-agent"}

    dev_type = coerce_device_type(fingerprint.device_type)
    is_mobile = dev_type == DeviceType.MOBILE

    screen_w, screen_h = fingerprint.screen_size
    vp_w, vp_h = fingerprint.viewport

    options: dict[str, Any] = {
        "user_agent": user_agent,
        "locale": fingerprint.locale,
        "viewport": {"width": vp_w, "height": vp_h},
        "screen": {"width": screen_w, "height": screen_h},
        "device_scale_factor": fingerprint.device_scale_factor,
        "color_scheme": "light",
        "is_mobile": is_mobile,
        "has_touch": is_mobile,
        "extra_http_headers": client_hints,
    }
    if fingerprint.timezone_id:
        options["timezone_id"] = fingerprint.timezone_id

    return options


def build_init_script(fingerprint: Fingerprint, browser_version: str | None = None) -> str:
    """Builds JS init script overriding browser APIs before page scripts execute."""
    retargeted = retarget(fingerprint, browser_version)
    return InjectFunction(cast(Any, _Dumpable(retargeted)))


async def apply_to_context(
    context: Any,
    fingerprint: Fingerprint,
    browser_version: str | None = None,
) -> None:
    """Injects retargeted fingerprint into an async browser context via add_init_script."""
    script = build_init_script(fingerprint, browser_version)
    await context.add_init_script(script)


def apply_to_context_sync(
    context: Any,
    fingerprint: Fingerprint,
    browser_version: str | None = None,
) -> None:
    """Injects retargeted fingerprint into a sync browser context via add_init_script."""
    script = build_init_script(fingerprint, browser_version)
    context.add_init_script(script)
