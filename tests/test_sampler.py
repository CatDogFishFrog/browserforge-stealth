"""
Tests for the low-level Bayesian fingerprint sampler.
"""

from __future__ import annotations

import pytest
from browserforge_stealth.errors import GenerationError
from browserforge_stealth.sampler import FingerprintSampler, ScreenConstraints


def test_sample_has_injectable_shape() -> None:
    raw = FingerprintSampler().sample(
        browser=("chrome",), os=("windows",), device="desktop", locale=("en-US",)
    )

    for key in ("navigator", "screen", "headers", "videoCard", "videoCodecs", "audioCodecs"):
        assert key in raw
    assert raw["navigator"]["language"] == raw["navigator"]["languages"][0]
    assert "Chrome/" in raw["navigator"]["userAgent"]
    assert raw["mockWebRTC"] is False
    assert raw["slim"] is False


def test_screen_constraints_are_respected() -> None:
    sampler = FingerprintSampler()
    constraints = ScreenConstraints(min_width=1280, min_height=720)

    for _ in range(5):
        raw = sampler.sample(
            screen=constraints, browser=("chrome",), os=("windows",), device="desktop", locale=("en-US",)
        )
        assert raw["screen"]["width"] >= 1280
        assert raw["screen"]["height"] >= 720


def test_screen_constraints_validate_bounds() -> None:
    with pytest.raises(ValueError, match="min values"):
        ScreenConstraints(min_width=2000, max_width=1000)
    assert not ScreenConstraints().is_set()
    assert ScreenConstraints(min_width=1).is_set()
    assert ScreenConstraints(min_width=100, max_width=200).accepts(150, 10)
    assert not ScreenConstraints(max_height=100).accepts(10, 101)


def test_impossible_strict_screen_constraints_raise() -> None:
    constraints = ScreenConstraints(min_width=90_000)

    with pytest.raises(GenerationError):
        FingerprintSampler().sample(
            screen=constraints, strict=True, browser=("chrome",), os=("windows",), device="desktop"
        )
