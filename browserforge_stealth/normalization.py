"""
Normalization and sanitization routines for browser fingerprints and headers.
"""

from __future__ import annotations

import copy
import random
from typing import Any

from browserforge_stealth.models import (
    DeviceType,
    OperatingSystem,
    coerce_device_type,
    coerce_os,
)

# ── Chromium GREASE & Brands constants ─────────────────────────────────────
_GREASE_CHARS = (" ", "(", ":", "-", ".", "/", ")", ";", "=", "?", "_")
_GREASE_VERSIONS = ("8", "99", "24")
_BRAND_ORDERS = ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0))
_PRODUCT_BRAND = "Google Chrome"

_OS_UACH_PLATFORM: dict[OperatingSystem, str] = {
    OperatingSystem.WINDOWS: "Windows",
    OperatingSystem.MACOS: "macOS",
    OperatingSystem.LINUX: "Linux",
    OperatingSystem.ANDROID: "Android",
    OperatingSystem.IOS: "iOS",
}


def chromium_brands(major: int, full_version: str | None = None) -> list[tuple[str, str]]:
    """Calculates navigator.userAgentData.brands matching the exact Chromium GREASE algorithm.

    Seed is the major version: it determines the GREASE brand name, version, and order.
    If full_version is passed, returns entries for fullVersionList.
    """
    seed = major
    grease_name = f"Not{_GREASE_CHARS[seed % 11]}A{_GREASE_CHARS[(seed + 1) % 11]}Brand"
    grease_version = _GREASE_VERSIONS[seed % 3]
    version = str(major) if full_version is None else full_version
    order = _BRAND_ORDERS[seed % 6]
    slots: list[tuple[str, str] | None] = [None, None, None]
    slots[order[0]] = (
        grease_name,
        grease_version if full_version is None else f"{grease_version}.0.0.0",
    )
    slots[order[1]] = ("Chromium", version)
    slots[order[2]] = (_PRODUCT_BRAND, version)
    return [slot for slot in slots if slot is not None]


def sec_ch_ua(brands: list[tuple[str, str]]) -> str:
    """Formats brands list into the Sec-CH-UA HTTP header value."""
    return ", ".join(f'"{name}";v="{version}"' for name, version in brands)


def normalize_languages(locale: str) -> tuple[list[str], str]:
    """Generates (navigator.languages, Accept-Language) formatted for Chrome.

    Strictly RFC/Chrome format without whitespace and with descending weighted q-values.
    Examples:
        'uk-UA' -> (['uk-UA', 'uk', 'en-US', 'en'], 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7')
        'en-GB' -> (['en-GB', 'en-US', 'en'], 'en-GB,en-US;q=0.9,en;q=0.8')
        'en-US' -> (['en-US', 'en'], 'en-US,en;q=0.9')
    """
    locale = locale.strip()
    base = locale.split("-")[0]
    if base == "en":
        languages = [locale, *(["en-US"] if locale != "en-US" else []), "en"]
    else:
        languages = [locale, *([base] if base != locale else []), "en-US", "en"]
    unique = list(dict.fromkeys(languages))
    parts = [unique[0]] + [f"{lang};q={max(1.0 - 0.1 * i, 0.1):.1f}" for i, lang in enumerate(unique[1:], 1)]
    return unique, ",".join(parts)


def client_hint_headers(
    os: OperatingSystem | str,
    locale: str,
    major: int,
    device_type: DeviceType | str = DeviceType.DESKTOP,
) -> dict[str, str]:
    """Returns low-entropy client hint headers sent by genuine Chrome + accept-language."""
    os_enum = coerce_os(os)
    dev_enum = coerce_device_type(device_type)
    _, accept_language = normalize_languages(locale)
    is_mobile = dev_enum == DeviceType.MOBILE
    return {
        "accept-language": accept_language,
        "sec-ch-ua": sec_ch_ua(chromium_brands(major)),
        "sec-ch-ua-mobile": "?1" if is_mobile else "?0",
        "sec-ch-ua-platform": f'"{_OS_UACH_PLATFORM[os_enum]}"',
    }


def normalize_fingerprint_dict(
    raw: dict[str, Any],
    *,
    os: OperatingSystem | str,
    locale: str,
    device_type: DeviceType | str = DeviceType.DESKTOP,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Sanitizes raw browserforge sample dictionary.

    - Fixes languages and accept-language.
    - Bounds deviceMemory <= 8.
    - Sets webdriver = False.
    - Sets maxTouchPoints = (0 if desktop else 5).
    - Bounds outerWidth/outerHeight to screen width/height.
    - Removes bloat unused by injectors that contained Brave artifacts: pluginsData, multimediaDevices, fonts.
    - Sets mockWebRTC = False, slim = False.
    - Sets initial headers.
    """
    _coerce_os = coerce_os(os)
    dev_enum = coerce_device_type(device_type)

    fp = copy.deepcopy(raw)
    if "navigator" not in fp:
        nav_keys = (
            "userAgent",
            "userAgentData",
            "doNotTrack",
            "appCodeName",
            "appName",
            "appVersion",
            "oscpu",
            "webdriver",
            "platform",
            "deviceMemory",
            "product",
            "productSub",
            "vendor",
            "vendorSub",
            "extraProperties",
            "hardwareConcurrency",
            "languages",
            "language",
            "maxTouchPoints",
        )
        fp["navigator"] = {k: fp[k] for k in nav_keys if k in fp}

    navigator = fp.setdefault("navigator", {})
    languages, accept_language = normalize_languages(locale)
    navigator["language"] = languages[0]
    navigator["languages"] = languages
    navigator["webdriver"] = False

    memory = navigator.get("deviceMemory")
    if isinstance(memory, (int, float)):
        navigator["deviceMemory"] = min(memory, 8)

    if dev_enum == DeviceType.DESKTOP:
        navigator["maxTouchPoints"] = 0
    else:
        existing_tp = navigator.get("maxTouchPoints")
        navigator["maxTouchPoints"] = max(int(existing_tp), 5) if existing_tp is not None else 5

    screen = fp.setdefault("screen", {})
    if not screen.get("outerWidth"):
        screen["outerWidth"] = screen.get("availWidth") or screen.get("width")
    if not screen.get("outerHeight"):
        screen["outerHeight"] = screen.get("availHeight") or screen.get("height")
    for outer, full in (("outerWidth", "width"), ("outerHeight", "height")):
        if screen.get(outer) and screen.get(full):
            screen[outer] = min(screen[outer], screen[full])

    for unused in ("pluginsData", "multimediaDevices", "fonts"):
        fp.pop(unused, None)

    fp["mockWebRTC"] = False
    fp["slim"] = False
    fp["headers"] = {"Accept-Language": accept_language}
    _ = rng
    return fp
