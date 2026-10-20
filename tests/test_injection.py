"""
Tests for browser injection and context options.
"""

from __future__ import annotations

import pytest
from browserforge_stealth.injection import (
    apply_to_context,
    apply_to_context_sync,
    build_init_script,
    context_options,
)
from browserforge_stealth.models import DeviceType, Fingerprint, OperatingSystem
from browserforge_stealth.retarget import build_user_agent

REAL_VERSION = "156.0.8078.4"


def make_test_fingerprint() -> Fingerprint:
    raw = {
        "navigator": {
            "userAgent": build_user_agent(OperatingSystem.WINDOWS, 147, DeviceType.DESKTOP),
            "platform": "Win32",
            "vendor": "Google Inc.",
            "deviceMemory": 8,
            "hardwareConcurrency": 8,
            "userAgentData": {"platform": "Windows", "mobile": False},
        },
        "screen": {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "devicePixelRatio": 1.25,
        },
        "videoCard": {
            "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11)",
            "vendor": "Google Inc. (NVIDIA)",
        },
        "headers": {},
    }
    return Fingerprint(
        os=OperatingSystem.WINDOWS,
        device_type=DeviceType.DESKTOP,
        locale="en-US",
        timezone_id="Europe/Kyiv",
        viewport=(1920, 955),
        raw_data=raw,
    )


def test_context_options_pins_environment() -> None:
    fp = make_test_fingerprint()
    options = context_options(fp, REAL_VERSION)

    assert options["user_agent"].endswith("Chrome/156.0.0.0 Safari/537.36")
    assert options["locale"] == "en-US"
    assert options["timezone_id"] == "Europe/Kyiv"
    assert options["viewport"] == {"width": 1920, "height": 955}
    assert options["screen"] == {"width": 1920, "height": 1080}
    assert options["device_scale_factor"] == 1.25
    assert options["color_scheme"] == "light"
    assert options["is_mobile"] is False
    assert options["has_touch"] is False

    headers = options["extra_http_headers"]
    assert "sec-ch-ua" in headers
    assert headers["sec-ch-ua-mobile"] == "?0"
    assert headers["sec-ch-ua-platform"] == '"Windows"'


def test_build_init_script_generates_valid_js() -> None:
    fp = make_test_fingerprint()
    script = build_init_script(fp, REAL_VERSION)

    assert "Chrome/156.0.0.0" in script
    assert "function" in script or script.lstrip().startswith("(")


class _FakeAsyncContext:
    def __init__(self) -> None:
        self.scripts: list[str] = []

    async def add_init_script(self, script: str) -> None:
        self.scripts.append(script)


class _FakeSyncContext:
    def __init__(self) -> None:
        self.scripts: list[str] = []

    def add_init_script(self, script: str) -> None:
        self.scripts.append(script)


@pytest.mark.asyncio
async def test_apply_to_context_async() -> None:
    fp = make_test_fingerprint()
    ctx = _FakeAsyncContext()
    await apply_to_context(ctx, fp, REAL_VERSION)
    assert len(ctx.scripts) == 1
    assert "Chrome/156.0.0.0" in ctx.scripts[0]


def test_apply_to_context_sync() -> None:
    fp = make_test_fingerprint()
    ctx = _FakeSyncContext()
    apply_to_context_sync(ctx, fp, REAL_VERSION)
    assert len(ctx.scripts) == 1
    assert "Chrome/156.0.0.0" in ctx.scripts[0]
