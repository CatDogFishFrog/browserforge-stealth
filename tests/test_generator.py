"""
Tests for FingerprintGenerator (rejection sampling and diversity).
"""

from __future__ import annotations

import random

import pytest
from browserforge_stealth.generator import FingerprintGenerator, generate_fingerprint
from browserforge_stealth.models import DeviceType, OperatingSystem
from browserforge_stealth.realism import realism_issues


@pytest.mark.parametrize("os_val", [OperatingSystem.WINDOWS, OperatingSystem.MACOS, OperatingSystem.LINUX])
def test_generated_desktop_profiles_are_coherent(os_val: OperatingSystem) -> None:
    random.seed(42)
    gen = FingerprintGenerator(os=os_val, locale="en-US", timezone_id="Europe/Kyiv")
    for _ in range(3):
        fp = gen.generate()
        assert realism_issues(fp.raw_data, os_val, DeviceType.DESKTOP) == []
        assert fp.device_memory is not None and fp.device_memory <= 8
        assert fp.device_scale_factor in {1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0}
        w, h = fp.screen_size
        assert w >= 1280 and h >= 720
        vw, vh = fp.viewport
        assert 1000 <= vw <= w
        assert 600 <= vh <= h


def test_diversity_across_samples() -> None:
    random.seed(123)
    gen = FingerprintGenerator(os=OperatingSystem.WINDOWS, locale="en-US")
    gpus = {gen.generate().gpu_renderer for _ in range(8)}
    assert len(gpus) > 1  # different accounts produce different GPUs


def test_convenience_function_generates_valid_fingerprint() -> None:
    fp = generate_fingerprint(os="windows", locale="uk-UA")
    assert fp.locale == "uk-UA"
    assert fp.os == OperatingSystem.WINDOWS
    assert "Chrome/" in fp.user_agent
