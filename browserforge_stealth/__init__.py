"""
BrowserForge-Stealth.
Realistic and intelligent browser header & fingerprint generator for Patchright,
Playwright, and anti-detect automation.
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
from browserforge_stealth.headers import (
    Browser,
    HeaderGenerator,
)
from browserforge_stealth.injection import (
    apply_to_context,
    apply_to_context_sync,
    build_init_script,
    context_options,
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
from browserforge_stealth.sampler import FingerprintSampler, ScreenConstraints

__version__ = "2.0.0"

__all__ = [
    "Browser",
    "DeviceType",
    "Fingerprint",
    "FingerprintError",
    "FingerprintGenerator",
    "FingerprintSampler",
    "GenerationError",
    "HardwareInfo",
    "HeaderGenerator",
    "OperatingSystem",
    "RealismError",
    "ScreenConstraints",
    "ScreenInfo",
    "SerializationError",
    "Viewport",
    "__version__",
    "apply_to_context",
    "apply_to_context_sync",
    "build_init_script",
    "build_user_agent",
    "chromium_brands",
    "client_hint_headers",
    "context_options",
    "derive_viewport",
    "generate_fingerprint",
    "normalize_fingerprint_dict",
    "normalize_languages",
    "parse_browser_version",
    "realism_issues",
    "retarget",
    "sec_ch_ua",
]
