"""
Tests backward compatibility with original browserforge package imports and APIs.
"""

from __future__ import annotations


def test_browserforge_fingerprints_imports() -> None:
    from browserforge.fingerprints import (
        Fingerprint,
        FingerprintGenerator,
        Screen,
    )

    assert Fingerprint is not None
    assert FingerprintGenerator is not None
    assert Screen is not None


def test_browserforge_injectors_utils_imports() -> None:
    from browserforge.injectors.utils import InjectFunction

    assert callable(InjectFunction)


def test_browserforge_headers_imports() -> None:
    from browserforge.headers import HeaderGenerator

    assert HeaderGenerator is not None
    gen = HeaderGenerator()
    headers = gen.generate()
    assert isinstance(headers, dict)
    assert len(headers) > 0


def test_classic_generator_produces_dumps() -> None:
    from browserforge.fingerprints import FingerprintGenerator

    gen = FingerprintGenerator(realistic=False)
    sample = gen.generate(browser=("chrome",), os=("windows",))
    assert hasattr(sample, "dumps")
    dumped = sample.dumps()
    assert isinstance(dumped, str)
    assert len(dumped) > 0
    assert "navigator" in dumped or "screen" in dumped
