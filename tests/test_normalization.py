"""
Tests for normalization, sanitization, GREASE brands, and client hint headers.
"""

from __future__ import annotations

from browserforge_stealth.models import DeviceType, OperatingSystem
from browserforge_stealth.normalization import (
    chromium_brands,
    client_hint_headers,
    normalize_fingerprint_dict,
    normalize_languages,
)


def test_chromium_grease_brands_known_seeds() -> None:
    # Seed 120
    b120 = chromium_brands(120)
    assert b120[0] == ("Not_A Brand", "8")
    assert b120[1] == ("Chromium", "120")
    assert b120[2] == ("Google Chrome", "120")

    # Seed 124
    b124 = chromium_brands(124)
    assert b124[0] == ("Chromium", "124")
    assert b124[1] == ("Google Chrome", "124")
    assert b124[2] == ("Not-A.Brand", "99")

    # Seed 131
    b131 = chromium_brands(131)
    assert b131[0] == ("Google Chrome", "131")
    assert b131[1] == ("Chromium", "131")
    assert b131[2] == ("Not_A Brand", "24")

    # Seed 133
    b133 = chromium_brands(133)
    assert b133[0] == ("Not(A:Brand", "99")
    assert b133[1] == ("Google Chrome", "133")
    assert b133[2] == ("Chromium", "133")

    # Seed 147
    b147 = chromium_brands(147)
    assert b147[0] == ("Google Chrome", "147")
    assert b147[1] == ("Not.A/Brand", "8")
    assert b147[2] == ("Chromium", "147")

    # Full version test
    full_brands = chromium_brands(133, "133.0.6943.53")
    assert full_brands[0] == ("Not(A:Brand", "99.0.0.0")
    assert full_brands[1] == ("Google Chrome", "133.0.6943.53")
    assert full_brands[2] == ("Chromium", "133.0.6943.53")


def test_languages_normalization() -> None:
    # uk-UA
    langs, header = normalize_languages("uk-UA")
    assert langs == ["uk-UA", "uk", "en-US", "en"]
    assert header == "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7"

    # en-US
    langs_us, header_us = normalize_languages("en-US")
    assert langs_us == ["en-US", "en"]
    assert header_us == "en-US,en;q=0.9"

    # en-GB
    langs_gb, header_gb = normalize_languages("en-GB")
    assert langs_gb == ["en-GB", "en-US", "en"]
    assert header_gb == "en-GB,en-US;q=0.9,en;q=0.8"


def test_client_hint_headers() -> None:
    desktop_hints = client_hint_headers(OperatingSystem.WINDOWS, "en-US", 133, DeviceType.DESKTOP)
    assert set(desktop_hints.keys()) == {
        "accept-language",
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform",
    }
    assert desktop_hints["sec-ch-ua-mobile"] == "?0"
    assert desktop_hints["sec-ch-ua-platform"] == '"Windows"'
    assert desktop_hints["accept-language"] == "en-US,en;q=0.9"
    assert '"Chromium";v="133"' in desktop_hints["sec-ch-ua"]

    mobile_hints = client_hint_headers(OperatingSystem.ANDROID, "en-US", 133, DeviceType.MOBILE)
    assert mobile_hints["sec-ch-ua-mobile"] == "?1"
    assert mobile_hints["sec-ch-ua-platform"] == '"Android"'


def test_brave_removal_and_ram_limitation() -> None:
    raw = {
        "navigator": {
            "userAgent": "Mozilla/5.0 ... Chrome/133.0.0.0",
            "deviceMemory": 16,
            "webdriver": True,
            "maxTouchPoints": 10,
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "outerWidth": 2560,
            "outerHeight": 1440,
        },
        # Bloat that can carry Brave or unneeded artifacts
        "pluginsData": {"plugins": []},
        "multimediaDevices": [{"kind": "audioinput"}],
        "fonts": ["Arial", "Roboto"],
        "mockWebRTC": True,
        "slim": True,
    }

    normalized = normalize_fingerprint_dict(
        raw,
        os=OperatingSystem.WINDOWS,
        locale="en-US",
        device_type=DeviceType.DESKTOP,
    )

    # RAM bounded to <= 8
    assert normalized["navigator"]["deviceMemory"] == 8
    # Webdriver forced to False
    assert normalized["navigator"]["webdriver"] is False
    # Desktop maxTouchPoints forced to 0
    assert normalized["navigator"]["maxTouchPoints"] == 0
    # Outer dimensions bounded
    assert normalized["screen"]["outerWidth"] <= 1920
    assert normalized["screen"]["outerHeight"] <= 1080
    # Bloat removed
    assert "pluginsData" not in normalized
    assert "multimediaDevices" not in normalized
    assert "fonts" not in normalized
    assert normalized["mockWebRTC"] is False
    assert normalized["slim"] is False
