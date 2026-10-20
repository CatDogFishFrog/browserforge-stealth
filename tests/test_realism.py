"""
Tests for realism rules (desktop and mobile).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from browserforge_stealth.models import DeviceType, OperatingSystem
from browserforge_stealth.realism import derive_viewport, realism_issues
from browserforge_stealth.retarget import build_user_agent


def good_windows_fingerprint() -> dict:
    return {
        "navigator": {
            "userAgent": build_user_agent(OperatingSystem.WINDOWS, 147, DeviceType.DESKTOP),
            "platform": "Win32",
            "vendor": "Google Inc.",
            "deviceMemory": 8,
            "hardwareConcurrency": 8,
            "userAgentData": {"platform": "Windows", "platformVersion": "15.0.0"},
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "devicePixelRatio": 1.0,
        },
        "videoCard": {
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
            "vendor": "Google Inc. (NVIDIA)",
        },
    }


def test_good_desktop_fingerprint_passes() -> None:
    fp = good_windows_fingerprint()
    assert realism_issues(fp, OperatingSystem.WINDOWS, DeviceType.DESKTOP) == []


@pytest.mark.parametrize(
    ("mutation", "fragment"),
    [
        (lambda f: f["navigator"].update(platform="Linux x86_64"), "platform"),
        (lambda f: f["navigator"]["userAgentData"].update(platform="Linux"), "userAgentData"),
        (lambda f: f["navigator"].update(userAgent=f["navigator"]["userAgent"] + " Edg/147"), "Chrome"),
        (lambda f: f["navigator"].update(deviceMemory=0.5), "deviceMemory"),
        (lambda f: f["navigator"].update(hardwareConcurrency=1), "hardwareConcurrency"),
        (lambda f: f["navigator"].update(vendor="Apple Computer, Inc."), "vendor"),
        (lambda f: f["screen"].update(devicePixelRatio=1.1458), "DPR"),
        (lambda f: f["screen"].update(width=1024, height=600), "screen"),
        (lambda f: f["screen"].update(availWidth=2000), "available"),
        (lambda f: f["videoCard"].update(renderer="Microsoft Basic Render Driver"), "software or empty GPU"),
        (lambda f: f["videoCard"].update(renderer="Google SwiftShader"), "software or empty GPU"),
        (
            lambda f: (
                f["navigator"].update(hardwareConcurrency=20),
                f["videoCard"].update(renderer="ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11)"),
            ),
            "impossible with old integrated GPU",
        ),
    ],
)
def test_unrealistic_desktop_samples_are_rejected(mutation: Callable[[dict[str, Any]], Any], fragment: str) -> None:
    fp = good_windows_fingerprint()
    mutation(fp)
    issues = realism_issues(fp, OperatingSystem.WINDOWS, DeviceType.DESKTOP)
    assert any(fragment.lower() in issue.lower() for issue in issues), issues


def test_derive_viewport_desktop() -> None:
    fp = {"screen": {"width": 1920, "height": 1080, "availWidth": 1920, "availHeight": 1040}}
    w, h = derive_viewport(fp, OperatingSystem.WINDOWS, DeviceType.DESKTOP)
    assert w == 1920
    assert h == 1040 - 85  # Windows UI height is 85


def test_derive_viewport_never_exceeds_screen() -> None:
    fp = {"screen": {"width": 1512, "height": 982, "availWidth": 1600, "availHeight": 1100}}
    w, h = derive_viewport(fp, OperatingSystem.MACOS, DeviceType.DESKTOP)
    assert w <= 1512 and h <= 982


def test_mobile_realism() -> None:
    mobile_fp = {
        "navigator": {
            "userAgent": build_user_agent(OperatingSystem.ANDROID, 147, DeviceType.MOBILE),
            "platform": "Linux armv81",
            "vendor": "Google Inc.",
            "deviceMemory": 6,
            "hardwareConcurrency": 8,
            "maxTouchPoints": 5,
            "userAgentData": {"platform": "Android", "mobile": True},
        },
        "screen": {
            "width": 390,
            "height": 844,
            "availWidth": 390,
            "availHeight": 844,
            "devicePixelRatio": 3.0,
        },
        "videoCard": {
            "renderer": "Adreno (TM) 740",
            "vendor": "Qualcomm",
        },
    }
    assert realism_issues(mobile_fp, OperatingSystem.ANDROID, DeviceType.MOBILE) == []
