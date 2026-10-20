"""
Tests for browser engine retargeting.
"""

from __future__ import annotations

from browserforge_stealth.models import DeviceType, Fingerprint, OperatingSystem
from browserforge_stealth.normalization import chromium_brands, sec_ch_ua
from browserforge_stealth.retarget import (
    build_user_agent,
    parse_browser_version,
    retarget,
)

REAL_VERSION = "156.0.8078.4"


def make_test_fingerprint() -> Fingerprint:
    raw = {
        "navigator": {
            "userAgent": build_user_agent(OperatingSystem.WINDOWS, 147, DeviceType.DESKTOP),
            "platform": "Win32",
            "vendor": "Google Inc.",
            "deviceMemory": 8,
            "hardwareConcurrency": 8,
            "userAgentData": {
                "brands": [{"brand": n, "version": v} for n, v in chromium_brands(147)],
                "platform": "Windows",
                "mobile": False,
            },
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "devicePixelRatio": 1.0,
        },
        "videoCard": {
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11)",
            "vendor": "Google Inc. (NVIDIA)",
        },
        "headers": {
            "User-Agent": build_user_agent(OperatingSystem.WINDOWS, 147, DeviceType.DESKTOP),
            "sec-ch-ua": sec_ch_ua(chromium_brands(147)),
        },
    }
    return Fingerprint(
        os=OperatingSystem.WINDOWS,
        device_type=DeviceType.DESKTOP,
        locale="en-US",
        timezone_id="Europe/Kyiv",
        viewport=(1920, 955),
        raw_data=raw,
    )


def test_parse_browser_version() -> None:
    assert parse_browser_version(REAL_VERSION) == (156, REAL_VERSION)
    assert parse_browser_version("141.0.3537.71") == (141, "141.0.3537.71")
    assert parse_browser_version("141") == (141, "141.0.0.0")
    ua = "Mozilla/5.0 Chrome/147.0.0.0 Safari/537.36"
    assert parse_browser_version(None, ua) == (147, "147.0.0.0")


def test_retarget_follows_real_engine_version() -> None:
    fp = make_test_fingerprint()
    retargeted = retarget(fp, REAL_VERSION)

    assert "Chrome/156.0.0.0" in retargeted["navigator"]["userAgent"]
    uad = retargeted["navigator"]["userAgentData"]
    assert uad["uaFullVersion"] == REAL_VERSION
    assert uad["platform"] == "Windows"
    assert not uad["mobile"]
    assert {b["brand"] for b in uad["brands"]} >= {"Chromium", "Google Chrome"}
    assert retargeted["headers"]["sec-ch-ua"] == sec_ch_ua(chromium_brands(156))


def test_retarget_does_not_mutate_original_fingerprint() -> None:
    fp = make_test_fingerprint()
    ua_before = fp.user_agent
    retarget(fp, REAL_VERSION)
    assert fp.user_agent == ua_before


def test_hardware_stays_identical_across_browser_updates() -> None:
    fp = make_test_fingerprint()
    a = retarget(fp, "156.0.8078.4")
    b = retarget(fp, "157.0.8100.2")

    assert a["navigator"]["userAgent"] != b["navigator"]["userAgent"]
    assert a["navigator"]["hardwareConcurrency"] == b["navigator"]["hardwareConcurrency"]
    assert a["videoCard"]["renderer"] == b["videoCard"]["renderer"]
    assert a["screen"] == b["screen"]
