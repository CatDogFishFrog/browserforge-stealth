"""
Tests for Fingerprint and related data models.
"""

from __future__ import annotations

from datetime import UTC, datetime

from browserforge_stealth.models import (
    DeviceType,
    Fingerprint,
    HardwareInfo,
    OperatingSystem,
    ScreenInfo,
)


def _sample_raw_data() -> dict:
    return {
        "navigator": {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
            "platform": "Win32",
            "vendor": "Google Inc.",
            "languages": ["en-US", "en"],
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "devicePixelRatio": 1.25,
        },
        "videoCard": {
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "vendor": "Google Inc. (NVIDIA)",
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        },
        "videoCodecs": {"h264": "probably"},
        "audioCodecs": {"mp3": "probably"},
        "battery": None,
    }


def test_roundtrip_dict_and_json() -> None:
    raw = _sample_raw_data()
    now = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)
    fp = Fingerprint(
        schema_version=1,
        created_at=now,
        device_type=DeviceType.DESKTOP,
        os=OperatingSystem.WINDOWS,
        locale="en-US",
        timezone_id="Europe/Kyiv",
        viewport=(1920, 995),
        raw_data=raw,
    )

    d = fp.to_dict()
    assert d["schema_version"] == 1
    assert d["created_at"] == "2026-10-20T12:00:00+00:00"
    assert d["device_type"] == "desktop"
    assert d["os"] == "windows"
    assert d["locale"] == "en-US"
    assert d["timezone_id"] == "Europe/Kyiv"
    assert d["viewport"] == [1920, 995]
    assert d["raw_data"]["navigator"]["platform"] == "Win32"

    fp_from_d = Fingerprint.from_dict(d)
    assert fp_from_d.os == OperatingSystem.WINDOWS
    assert fp_from_d.device_type == DeviceType.DESKTOP
    assert fp_from_d.locale == "en-US"
    assert fp_from_d.timezone_id == "Europe/Kyiv"
    assert fp_from_d.viewport == (1920, 995)
    assert fp_from_d.created_at == now

    json_str = fp.to_json(indent=2)
    fp_from_json = Fingerprint.from_json(json_str)
    assert fp_from_json.os == fp.os
    assert fp_from_json.device_type == fp.device_type
    assert fp_from_json.locale == fp.locale
    assert fp_from_json.viewport == fp.viewport
    assert fp_from_json.raw_data == fp.raw_data


def test_fingerprint_properties() -> None:
    raw = _sample_raw_data()
    fp = Fingerprint(
        device_type=DeviceType.DESKTOP,
        os=OperatingSystem.WINDOWS,
        locale="en-US",
        timezone_id="America/New_York",
        viewport=(1920, 995),
        raw_data=raw,
    )

    assert fp.screen_size == (1920, 1080)
    assert fp.device_scale_factor == 1.25
    assert "RTX 3070" in fp.gpu_renderer
    assert fp.hardware_concurrency == 8
    assert fp.device_memory == 8.0
    assert "Chrome/133" in fp.user_agent

    screen_info = fp.screen_info
    assert isinstance(screen_info, ScreenInfo)
    assert screen_info.width == 1920
    assert screen_info.height == 1080
    assert screen_info.avail_width == 1920
    assert screen_info.avail_height == 1040
    assert screen_info.device_scale_factor == 1.25

    hw_info = fp.hardware_info
    assert isinstance(hw_info, HardwareInfo)
    assert hw_info.cores == 8
    assert hw_info.memory_gb == 8.0
    assert hw_info.gpu_renderer == fp.gpu_renderer


def test_dict_like_access() -> None:
    raw = _sample_raw_data()
    fp = Fingerprint(raw_data=raw)

    assert fp["navigator"]["platform"] == "Win32"
    assert fp.get("screen")["width"] == 1920
    assert fp.get("nonexistent", "fallback") == "fallback"
    assert "navigator" in fp
    assert "missing_key" not in fp
    assert len(fp) == len(raw)
    assert list(fp.keys()) == list(raw.keys())
    assert "screen" in list(iter(fp))
    assert len(list(fp.items())) == len(raw.items())


def test_injector_attribute_compatibility() -> None:
    raw = _sample_raw_data()
    fp = Fingerprint(raw_data=raw)

    assert fp.navigator.platform == "Win32"
    assert fp.screen.width == 1920
    assert fp.screen.devicePixelRatio == 1.25
    assert "RTX 3070" in fp.videoCard.renderer
    assert fp.dumps().startswith("{")
