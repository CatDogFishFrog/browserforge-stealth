"""
Tests for the legacy-profile conversion snippet documented in the README migration guide.
"""

from __future__ import annotations

import json

from browserforge_stealth import (
    Fingerprint,
    FingerprintGenerator,
    ScreenConstraints,
    derive_viewport,
    realism_issues,
)


def test_legacy_payload_can_be_wrapped_into_fingerprint() -> None:
    legacy_json = json.dumps(FingerprintGenerator(os="windows").generate().raw_data)

    raw = json.loads(legacy_json)
    fp = Fingerprint(
        os="windows",
        device_type="desktop",
        locale=raw["navigator"]["language"],
        viewport=derive_viewport(raw, "windows", "desktop"),
        raw_data=raw,
    )

    assert realism_issues(fp, "windows", "desktop") == []
    assert Fingerprint.from_json(fp.to_json()).raw_data == raw


def test_screen_constraints_are_accepted_by_generator() -> None:
    fp = FingerprintGenerator(os="windows", screen=ScreenConstraints(min_width=1600)).generate()

    assert fp.screen_size[0] >= 1600
