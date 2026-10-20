"""
Modern, stealth-aware fingerprint generator for browser automation.
"""

from __future__ import annotations

import json
import random
import sys
from typing import Any

from browserforge.fingerprints.generator import (
    FingerprintGenerator as ClassicFingerprintGenerator,
    Screen,
)
from browserforge_stealth.errors import GenerationError
from browserforge_stealth.models import (
    DeviceType,
    Fingerprint,
    OperatingSystem,
    coerce_device_type,
    coerce_os,
)
from browserforge_stealth.normalization import normalize_fingerprint_dict
from browserforge_stealth.realism import derive_viewport, realism_issues


def _default_os(device_type: DeviceType) -> OperatingSystem:
    if device_type == DeviceType.MOBILE:
        return OperatingSystem.ANDROID
    if sys.platform == "win32":
        return OperatingSystem.WINDOWS
    if sys.platform == "darwin":
        return OperatingSystem.MACOS
    return OperatingSystem.LINUX


class FingerprintGenerator:
    """High-level realistic fingerprint generator with rejection sampling and sanitization."""

    def __init__(
        self,
        *,
        os: OperatingSystem | str | None = None,
        device_type: DeviceType | str = DeviceType.DESKTOP,
        locale: str = "en-US",
        timezone_id: str | None = None,
        realistic: bool = True,
        max_attempts: int = 60,
        rng: random.Random | None = None,
        **kwargs: Any,
    ) -> None:
        self.os = coerce_os(os) if os is not None else None
        self.device_type = coerce_device_type(device_type)
        self.locale = str(locale)
        self.timezone_id = str(timezone_id) if timezone_id is not None else None
        self.realistic = realistic
        self.max_attempts = max_attempts
        self.rng = rng or random.Random()
        self.extra_kwargs = kwargs
        self._classic_generator: ClassicFingerprintGenerator | None = None

    def _get_classic_generator(self) -> ClassicFingerprintGenerator:
        if self._classic_generator is None:
            self._classic_generator = ClassicFingerprintGenerator(
                realistic=False, **self.extra_kwargs
            )
        return self._classic_generator

    def generate(
        self,
        *,
        os: OperatingSystem | str | None = None,
        device_type: DeviceType | str | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
        realistic: bool | None = None,
        max_attempts: int | None = None,
        **kwargs: Any,
    ) -> Fingerprint:
        effective_device = (
            coerce_device_type(device_type) if device_type is not None else self.device_type
        )
        effective_os = (
            coerce_os(os) if os is not None else (self.os or _default_os(effective_device))
        )
        effective_locale = str(locale) if locale is not None else self.locale
        effective_tz = (
            str(timezone_id)
            if timezone_id is not None
            else self.timezone_id
        )
        effective_realistic = realistic if realistic is not None else self.realistic
        effective_max_attempts = (
            max_attempts if max_attempts is not None else self.max_attempts
        )

        screen_constraint = (
            Screen(min_width=1280, min_height=720)
            if effective_device == DeviceType.DESKTOP
            else None
        )

        classic_gen = self._get_classic_generator()
        rejected_issues: list[str] = []
        last_normalized: dict[str, Any] | None = None

        for _ in range(effective_max_attempts if effective_realistic else 1):
            gen_kwargs = {
                "browser": ("chrome",),
                "os": (effective_os.value,),
                "device": effective_device.value,
                "locale": (effective_locale,),
                "screen": screen_constraint,
                "realistic": False,
                **self.extra_kwargs,
                **kwargs,
            }
            sample_obj = classic_gen.generate(**gen_kwargs)
            raw = json.loads(sample_obj.dumps())
            normalized = normalize_fingerprint_dict(
                raw,
                os=effective_os,
                locale=effective_locale,
                device_type=effective_device,
                rng=self.rng,
            )
            last_normalized = normalized

            if effective_realistic:
                issues = realism_issues(normalized, os=effective_os, device_type=effective_device)
                if issues:
                    rejected_issues.extend(issues)
                    continue

            vp = derive_viewport(normalized, os=effective_os, device_type=effective_device)
            return Fingerprint(
                device_type=effective_device,
                os=effective_os,
                locale=effective_locale,
                timezone_id=effective_tz,
                viewport=vp,
                raw_data=normalized,
            )

        if not effective_realistic and last_normalized is not None:
            vp = derive_viewport(last_normalized, os=effective_os, device_type=effective_device)
            return Fingerprint(
                device_type=effective_device,
                os=effective_os,
                locale=effective_locale,
                timezone_id=effective_tz,
                viewport=vp,
                raw_data=last_normalized,
            )

        raise GenerationError(
            f"Failed to generate realistic fingerprint for {effective_os.value} ({effective_device.value}) "
            f"after {effective_max_attempts} attempts. Issues: {sorted(set(rejected_issues))[:5]}"
        )


def generate_fingerprint(
    *,
    os: OperatingSystem | str | None = None,
    device_type: DeviceType | str = DeviceType.DESKTOP,
    locale: str = "en-US",
    timezone_id: str | None = None,
    realistic: bool = True,
    max_attempts: int = 60,
    rng: random.Random | None = None,
    **kwargs: Any,
) -> Fingerprint:
    """Convenience function to generate a realistic Fingerprint."""
    generator = FingerprintGenerator(
        os=os,
        device_type=device_type,
        locale=locale,
        timezone_id=timezone_id,
        realistic=realistic,
        max_attempts=max_attempts,
        rng=rng,
        **kwargs,
    )
    return generator.generate()
