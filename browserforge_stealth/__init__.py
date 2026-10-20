"""
BrowserForge-Stealth
Realistic and intelligent browser header & fingerprint generator for Patchright, Playwright, and anti-detect automation.
"""

from browserforge_stealth.errors import (
    FingerprintError,
    GenerationError,
    RealismError,
    SerializationError,
)
from browserforge_stealth.generator import (
    FingerprintGenerator,
    generate_fingerprint,
)
from browserforge_stealth.models import (
    DeviceType,
    Fingerprint,
    HardwareInfo,
    OperatingSystem,
    ScreenInfo,
    Viewport,
)
from browserforge_stealth.normalization import (
    chromium_brands,
    client_hint_headers,
    normalize_fingerprint_dict,
    normalize_languages,
    sec_ch_ua,
)
from browserforge_stealth.realism import (
    derive_viewport,
    realism_issues,
)
from browserforge_stealth.retarget import (
    build_user_agent,
    parse_browser_version,
    retarget,
)

__version__ = "1.3.0"

__all__ = [
    "FingerprintError",
    "GenerationError",
    "RealismError",
    "SerializationError",
    "DeviceType",
    "Fingerprint",
    "HardwareInfo",
    "OperatingSystem",
    "ScreenInfo",
    "Viewport",
    "FingerprintGenerator",
    "generate_fingerprint",
    "chromium_brands",
    "client_hint_headers",
    "normalize_fingerprint_dict",
    "normalize_languages",
    "sec_ch_ua",
    "derive_viewport",
    "realism_issues",
    "build_user_agent",
    "parse_browser_version",
    "retarget",
    "__version__",
]
