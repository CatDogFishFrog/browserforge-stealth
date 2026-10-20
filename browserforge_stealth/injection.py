"""
Context options and init-script injection for Patchright and Playwright.
"""

from __future__ import annotations

import json
import lzma
from functools import cache
from pathlib import Path
from random import randrange
from typing import Any

from browserforge_stealth.models import DeviceType, Fingerprint, coerce_device_type
from browserforge_stealth.retarget import retarget

_UTILS_JS = Path(__file__).parent / "assets" / "utils.js.xz"

_INIT_TEMPLATE = """
(() => {
    __UTILS__

    const fp = __FINGERPRINT__;
    const {
        battery,
        navigator: { userAgentData, webdriver, ...navigatorProps },
        screen: allScreenProps,
        videoCard,
        audioCodecs,
        videoCodecs,
        mockWebRTC,
    } = fp;

    slim = fp.slim;

    const historyLength = __HISTORY_LENGTH__;

    const {
        outerHeight,
        outerWidth,
        devicePixelRatio,
        innerWidth,
        innerHeight,
        screenX,
        pageXOffset,
        pageYOffset,
        clientWidth,
        clientHeight,
        hasHDR,
        ...newScreen
    } = allScreenProps;

    const windowScreenProps = {
        innerHeight,
        outerHeight,
        outerWidth,
        innerWidth,
        screenX,
        pageXOffset,
        pageYOffset,
        devicePixelRatio,
    };

    const documentScreenProps = { clientHeight, clientWidth };

    runHeadlessFixes();
    if (mockWebRTC) blockWebRTC();
    if (slim) {
        window['slim'] = true;
    }
    overrideIntlAPI(navigatorProps.language);
    overrideStatic();
    if (userAgentData) {
        overrideUserAgentData(userAgentData);
    }
    if (window.navigator.webdriver) {
        navigatorProps.webdriver = false;
    }
    overrideInstancePrototype(window.navigator, navigatorProps);
    overrideInstancePrototype(window.screen, newScreen);
    overrideWindowDimensionsProps(windowScreenProps);
    overrideDocumentDimensionsProps(documentScreenProps);
    overrideInstancePrototype(window.history, { length: historyLength });
    overrideWebGl(videoCard);
    overrideCodecs(audioCodecs, videoCodecs);
    overrideBattery(battery);
})()
"""


@cache
def _utils_js() -> str:
    """Returns the bundled Apify ``utils.js`` helper library (decompressed once)."""
    with lzma.open(_UTILS_JS, "rt", encoding="utf-8") as handle:
        return handle.read()


def _render_init_script(data: dict[str, Any]) -> str:
    return (
        _INIT_TEMPLATE.replace("__FINGERPRINT__", json.dumps(data, ensure_ascii=False))
        .replace("__HISTORY_LENGTH__", str(randrange(1, 6)))
        .replace("__UTILS__", _utils_js())
    )


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
    return _render_init_script(retargeted)


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
