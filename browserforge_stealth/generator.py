"""
Modern, stealth-aware fingerprint generator for browser automation.
"""

from __future__ import annotations

import sys
from typing import Any

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
from browserforge_stealth.sampler import FingerprintSampler, ScreenConstraints


def _default_os(device_type: DeviceType) -> OperatingSystem:
    if device_type == DeviceType.MOBILE:
        return OperatingSystem.ANDROID
    plat = sys.platform
    if plat == "darwin":
        return OperatingSystem.MACOS
    if plat.startswith("linux"):
        return OperatingSystem.LINUX
    return OperatingSystem.WINDOWS


class FingerprintGenerator:
    """High-level realistic fingerprint generator with rejection sampling and sanitization."""

    def __init__(
        self,
        *,
        screen: ScreenConstraints | None = None,
        os: OperatingSystem | str | None = None,
        device_type: DeviceType | str = DeviceType.DESKTOP,
        locale: str = "en-US",
        timezone_id: str | None = None,
        realistic: bool = True,
        max_attempts: int = 60,
        **kwargs: Any,
    ) -> None:
        self.screen = screen
        self.os = coerce_os(os) if os is not None else None
        self.device_type = coerce_device_type(device_type)
        self.locale = str(locale)
        self.timezone_id = str(timezone_id) if timezone_id is not None else None
        self.realistic = realistic
        self.max_attempts = max_attempts
        self.extra_kwargs = kwargs
        self._sampler: FingerprintSampler | None = None

    def _get_sampler(self) -> FingerprintSampler:
        if self._sampler is None:
            self._sampler = FingerprintSampler()
        return self._sampler

    def generate(
        self,
        *,
        screen: ScreenConstraints | None = None,
        os: OperatingSystem | str | None = None,
        device_type: DeviceType | str | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
        realistic: bool | None = None,
        max_attempts: int | None = None,
        **kwargs: Any,
    ) -> Fingerprint:
        effective_device = coerce_device_type(device_type) if device_type is not None else self.device_type
        effective_os = coerce_os(os) if os is not None else (self.os or _default_os(effective_device))
        effective_locale = str(locale) if locale is not None else self.locale
        effective_tz = str(timezone_id) if timezone_id is not None else self.timezone_id
        effective_realistic = realistic if realistic is not None else self.realistic
        effective_max_attempts = max_attempts if max_attempts is not None else self.max_attempts

        effective_screen = screen if screen is not None else self.screen
        if effective_screen is None and effective_device == DeviceType.DESKTOP:
            effective_screen = ScreenConstraints(min_width=1280, min_height=720)

        sampler = self._get_sampler()
        rejected_issues: list[str] = []
        last_normalized: dict[str, Any] | None = None

        for _ in range(effective_max_attempts if effective_realistic else 1):
            gen_kwargs = {
                "browser": ("chrome",),
                "os": (effective_os.value,),
                "device": effective_device.value,
                "locale": (effective_locale,),
                "screen": effective_screen,
                **self.extra_kwargs,
                **kwargs,
            }
            raw = sampler.sample(**gen_kwargs)
            normalized = normalize_fingerprint_dict(
                raw,
                os=effective_os,
                locale=effective_locale,
                device_type=effective_device,
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
    screen: ScreenConstraints | None = None,
    os: OperatingSystem | str | None = None,
    device_type: DeviceType | str = DeviceType.DESKTOP,
    locale: str = "en-US",
    timezone_id: str | None = None,
    realistic: bool = True,
    max_attempts: int = 60,
    **kwargs: Any,
) -> Fingerprint:
    """Convenience function to generate a realistic Fingerprint."""
    generator = FingerprintGenerator(
        screen=screen,
        os=os,
        device_type=device_type,
        locale=locale,
        timezone_id=timezone_id,
        realistic=realistic,
        max_attempts=max_attempts,
        **kwargs,
    )
    return generator.generate()
