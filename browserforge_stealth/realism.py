"""
Realism rules and viewport derivation for browser fingerprints.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from browserforge_stealth.models import (
    DeviceType,
    OperatingSystem,
    coerce_device_type,
    coerce_os,
)

_OS_PLATFORM: dict[OperatingSystem, str] = {
    OperatingSystem.WINDOWS: "Win32",
    OperatingSystem.MACOS: "MacIntel",
    OperatingSystem.LINUX: "Linux x86_64",
}

_OS_UACH_PLATFORM: dict[OperatingSystem, str] = {
    OperatingSystem.WINDOWS: "Windows",
    OperatingSystem.MACOS: "macOS",
    OperatingSystem.LINUX: "Linux",
    OperatingSystem.ANDROID: "Android",
    OperatingSystem.IOS: "iOS",
}

_ALLOWED_DPR: dict[OperatingSystem, frozenset[float]] = {
    OperatingSystem.WINDOWS: frozenset({1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0}),
    OperatingSystem.MACOS: frozenset({1.0, 2.0}),
    OperatingSystem.LINUX: frozenset({1.0, 1.25, 1.5, 2.0}),
}

_BROWSER_UI_HEIGHT: dict[OperatingSystem, int] = {
    OperatingSystem.WINDOWS: 85,
    OperatingSystem.MACOS: 79,
    OperatingSystem.LINUX: 88,
    OperatingSystem.ANDROID: 56,
    OperatingSystem.IOS: 50,
}

_SOFTWARE_GPU_RE = re.compile(r"basic render|swiftshader|llvmpipe|software|microsoft basic", re.IGNORECASE)
_OLD_INTEL_IGPU_RE = re.compile(
    r"UHD Graphics 620|HD Graphics (?:[456]\d{2,3})|Iris\(TM\) Graphics 6100", re.IGNORECASE
)
_OLD_IGPU_MAX_THREADS = 8
_FOREIGN_BROWSER_UA_RE = re.compile(r"Edg/|OPR/|Brave|Firefox|YaBrowser", re.IGNORECASE)


def realism_issues(
    fingerprint: Any,
    os: OperatingSystem | str,
    device_type: DeviceType | str = DeviceType.DESKTOP,
) -> list[str]:
    """Evaluates fingerprint realism. Returns a list of rejection reasons (empty list if realistic)."""
    os_enum = coerce_os(os)
    dev_enum = coerce_device_type(device_type)

    if hasattr(fingerprint, "raw_data") and isinstance(fingerprint.raw_data, Mapping):
        fp = fingerprint.raw_data
    elif hasattr(fingerprint, "fingerprint") and isinstance(fingerprint.fingerprint, Mapping):
        fp = fingerprint.fingerprint
    elif isinstance(fingerprint, Mapping):
        fp = fingerprint
    else:
        return ["Invalid fingerprint object (not a Mapping or Fingerprint)"]

    issues: list[str] = []
    navigator: Mapping[str, Any] = fp.get("navigator") or {}
    screen: Mapping[str, Any] = fp.get("screen") or {}
    gpu: Mapping[str, Any] = fp.get("videoCard") or {}
    uad: Mapping[str, Any] = navigator.get("userAgentData") or {}
    ua = str(navigator.get("userAgent", ""))

    # Common GPU check
    renderer = str(gpu.get("renderer", ""))
    if not renderer or _SOFTWARE_GPU_RE.search(renderer):
        issues.append(f"Software or empty GPU renderer: {renderer!r} (програмний або порожній GPU)")

    # Common screen available bounds
    width = int(screen.get("width") or 0)
    height = int(screen.get("height") or 0)
    avail_w = int(screen.get("availWidth") or 0)
    avail_h = int(screen.get("availHeight") or 0)
    if (avail_w and avail_w > width) or (avail_h and avail_h > height):
        issues.append(
            f"Available screen area exceeds screen dimensions (доступна область більша за екран): "
            f"availWidth={avail_w} > width={width} or availHeight={avail_h} > height={height}"
        )

    if dev_enum == DeviceType.DESKTOP:
        # Desktop UA clean Chrome check
        if "Chrome/" not in ua or _FOREIGN_BROWSER_UA_RE.search(ua):
            issues.append(f"UA is not clean Chrome (UA не є чистим Chrome): {ua!r}")

        # platform matches OS
        expected_platform = _OS_PLATFORM.get(os_enum)
        nav_platform = navigator.get("platform")
        if expected_platform and nav_platform != expected_platform:
            issues.append(
                f"navigator.platform={nav_platform!r} does not match {os_enum.value} (platform не відповідає)"
            )

        # userAgentData.platform matches OS
        expected_uach_platform = _OS_UACH_PLATFORM.get(os_enum)
        uad_platform = uad.get("platform")
        if expected_uach_platform and uad_platform != expected_uach_platform:
            issues.append(
                f"userAgentData.platform={uad_platform!r} does not match OS {os_enum.value}"
            )

        # DPR check
        dpr = screen.get("devicePixelRatio")
        allowed_dpr = _ALLOWED_DPR.get(os_enum, frozenset({1.0, 2.0}))
        if not isinstance(dpr, (int, float)) or float(dpr) not in allowed_dpr:
            issues.append(f"Non-standard DPR (нестандартний DPR): {dpr!r}")

        # Screen dimensions
        if width < 1280 or height < 720:
            issues.append(f"Screen too small (занадто малий екран): {width}x{height} (min 1280x720)")

        # deviceMemory
        memory = navigator.get("deviceMemory")
        if not isinstance(memory, (int, float)) or memory < 2:
            issues.append(f"deviceMemory={memory!r} is unrealistic for desktop (min 2)")

        # hardwareConcurrency
        cores = navigator.get("hardwareConcurrency")
        if not isinstance(cores, int) or not (2 <= cores <= 64):
            issues.append(f"hardwareConcurrency={cores!r} outside 2..64")
        elif cores > _OLD_IGPU_MAX_THREADS and _OLD_INTEL_IGPU_RE.search(renderer):
            issues.append(f"{cores} threads (потоків) impossible with old integrated GPU ({renderer[:40]!r})")

        # vendor
        if navigator.get("vendor") != "Google Inc.":
            issues.append(f"navigator.vendor={navigator.get('vendor')!r} is not 'Google Inc.'")

    else:
        # Mobile rules
        if os_enum not in (OperatingSystem.ANDROID, OperatingSystem.IOS):
            issues.append(f"Mobile device_type requires Android or iOS, got {os_enum.value}")

        # Touch check
        max_touch_points = navigator.get("maxTouchPoints")
        if not isinstance(max_touch_points, int) or max_touch_points < 5:
            issues.append(f"Mobile device requires maxTouchPoints >= 5, got {max_touch_points!r}")

        # DPR check
        dpr = screen.get("devicePixelRatio")
        if not isinstance(dpr, (int, float)) or float(dpr) < 2.0:
            issues.append(f"Invalid mobile DPR {dpr!r} (expected >= 2.0)")

        # UA check
        if "Mobile" not in ua or not ("Android" in ua or "iPhone" in ua):
            issues.append(f"Mobile UA must contain 'Mobile' and ('Android' or 'iPhone'): {ua!r}")
        if _FOREIGN_BROWSER_UA_RE.search(ua):
            issues.append(f"Mobile UA contains foreign browser tokens: {ua!r}")

        # userAgentData.platform
        uad_platform = uad.get("platform")
        if os_enum == OperatingSystem.ANDROID:
            if uad_platform and uad_platform != "Android":
                issues.append(f"userAgentData.platform={uad_platform!r} must match 'Android'")
        elif os_enum == OperatingSystem.IOS and uad_platform and uad_platform not in ("iOS", ""):
            issues.append(f"userAgentData.platform={uad_platform!r} must match 'iOS'")

        # Screen dimensions
        if width < 320 or height < 480:
            issues.append(f"Screen too small for mobile (занадто малий екран): {width}x{height}")

    return issues


def derive_viewport(
    fingerprint: Any,
    os: OperatingSystem | str,
    device_type: DeviceType | str = DeviceType.DESKTOP,
) -> tuple[int, int]:
    """Calculates inner viewport deducting browser UI bar."""
    os_enum = coerce_os(os)
    dev_enum = coerce_device_type(device_type)

    if hasattr(fingerprint, "raw_data") and isinstance(fingerprint.raw_data, Mapping):
        fp = fingerprint.raw_data
    elif hasattr(fingerprint, "fingerprint") and isinstance(fingerprint.fingerprint, Mapping):
        fp = fingerprint.fingerprint
    elif isinstance(fingerprint, Mapping):
        fp = fingerprint
    else:
        fp = {}

    screen: Mapping[str, Any] = fp.get("screen") or {}
    screen_w = int(screen.get("width") or 0) or 10_000
    screen_h = int(screen.get("height") or 0) or 10_000
    outer_w = int(
        screen.get("outerWidth")
        or screen.get("availWidth")
        or screen.get("width")
        or (1366 if dev_enum == DeviceType.DESKTOP else 390)
    )
    outer_h = int(
        screen.get("outerHeight")
        or screen.get("availHeight")
        or screen.get("height")
        or (768 if dev_enum == DeviceType.DESKTOP else 844)
    )
    ui_h = _BROWSER_UI_HEIGHT.get(os_enum, 85 if dev_enum == DeviceType.DESKTOP else 56)

    if dev_enum == DeviceType.MOBILE:
        width = min(max(320, outer_w), screen_w)
        height = min(max(400, outer_h - ui_h), screen_h)
        return width, height

    width = min(max(1000, outer_w), screen_w)
    height = min(max(600, outer_h - ui_h), screen_h)
    return width, height
