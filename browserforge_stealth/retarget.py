"""
Dynamic browser version retargeting for fingerprints.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from browserforge_stealth.models import (
    DeviceType,
    Fingerprint,
    OperatingSystem,
    coerce_device_type,
    coerce_os,
)
from browserforge_stealth.normalization import (
    chromium_brands,
    client_hint_headers,
)

_FULL_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

_UA_SYSTEM_TOKEN: dict[OperatingSystem, str] = {
    OperatingSystem.WINDOWS: "Windows NT 10.0; Win64; x64",
    OperatingSystem.MACOS: "Macintosh; Intel Mac OS X 10_15_7",
    OperatingSystem.LINUX: "X11; Linux x86_64",
    OperatingSystem.ANDROID: "Linux; Android 10; K",
    OperatingSystem.IOS: "iPhone; CPU iPhone OS 17_0 like Mac OS X",
}

_OS_PLATFORM: dict[OperatingSystem, str] = {
    OperatingSystem.WINDOWS: "Win32",
    OperatingSystem.MACOS: "MacIntel",
    OperatingSystem.LINUX: "Linux x86_64",
    OperatingSystem.ANDROID: "Linux armv81",
    OperatingSystem.IOS: "iPhone",
}

_OS_UACH_PLATFORM: dict[OperatingSystem, str] = {
    OperatingSystem.WINDOWS: "Windows",
    OperatingSystem.MACOS: "macOS",
    OperatingSystem.LINUX: "Linux",
    OperatingSystem.ANDROID: "Android",
    OperatingSystem.IOS: "iOS",
}


def parse_browser_version(version: str | None, fallback_ua: str = "") -> tuple[int, str]:
    """Returns (major, full_version).

    If the engine version is unknown or empty, extracts it from fallback_ua.
    """
    if version and _FULL_VERSION_RE.match(version):
        return int(version.split(".")[0]), version
    if version and version.split(".")[0].isdigit():
        return int(version.split(".")[0]), f"{int(version.split('.')[0])}.0.0.0"
    match = re.search(r"Chrome/(\d+)", fallback_ua)
    major = int(match.group(1)) if match else 140
    return major, f"{major}.0.0.0"


def build_user_agent(
    os: OperatingSystem | str,
    major: int,
    device_type: DeviceType | str = DeviceType.DESKTOP,
) -> str:
    """Builds a modern reduced User-Agent string for the specified OS and major version."""
    os_enum = coerce_os(os)
    dev_enum = coerce_device_type(device_type)

    if dev_enum == DeviceType.MOBILE:
        if os_enum == OperatingSystem.IOS:
            return (
                f"Mozilla/5.0 ({_UA_SYSTEM_TOKEN[os_enum]}) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"CriOS/{major}.0.0.0 Mobile/15E148 Safari/604.1"
            )
        token = _UA_SYSTEM_TOKEN[OperatingSystem.ANDROID]
        return (
            f"Mozilla/5.0 ({token}) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{major}.0.0.0 Mobile Safari/537.36"
        )

    token = _UA_SYSTEM_TOKEN.get(os_enum, _UA_SYSTEM_TOKEN[OperatingSystem.WINDOWS])
    return f"Mozilla/5.0 ({token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"


def retarget(fp: Fingerprint, browser_version: str | None) -> dict[str, Any]:
    """Returns a retargeted copy of the fingerprint payload matching the real running engine version.

    Dynamically updates Chrome major/full version in UA, appVersion, userAgentData
    brands/fullVersionList, and Client Hints without mutating stored hardware.
    """
    raw = copy.deepcopy(fp.raw_data)
    os_val, dev_val, locale = fp.os, fp.device_type, fp.locale

    os_enum, dev_enum = os_val, dev_val

    navigator = raw.setdefault("navigator", {})
    fallback_ua = str(navigator.get("userAgent", ""))
    major, full = parse_browser_version(browser_version, fallback_ua)

    user_agent = build_user_agent(os_enum, major, dev_enum)
    navigator["userAgent"] = user_agent
    navigator["appVersion"] = user_agent.removeprefix("Mozilla/")
    navigator["platform"] = _OS_PLATFORM.get(os_enum, "Win32")

    previous = navigator.get("userAgentData") or {}
    navigator["userAgentData"] = {
        "brands": [{"brand": n, "version": v} for n, v in chromium_brands(major)],
        "mobile": dev_enum == DeviceType.MOBILE,
        "platform": _OS_UACH_PLATFORM.get(os_enum, "Windows"),
        "architecture": previous.get("architecture") or ("arm" if dev_enum == DeviceType.MOBILE else "x86"),
        "bitness": previous.get("bitness") or "64",
        "model": previous.get("model") or "",
        "platformVersion": previous.get("platformVersion")
        or ("10.0.0" if os_enum == OperatingSystem.ANDROID else "15.0.0"),
        "uaFullVersion": full,
        "fullVersionList": [{"brand": n, "version": v} for n, v in chromium_brands(major, full)],
    }
    raw["headers"] = {
        **client_hint_headers(os_enum, locale, major, dev_enum),
        "User-Agent": user_agent,
    }
    return raw
