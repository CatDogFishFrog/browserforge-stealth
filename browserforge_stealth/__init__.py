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
from browserforge_stealth.models import (
    DeviceType,
    Fingerprint,
    HardwareInfo,
    OperatingSystem,
    ScreenInfo,
    Viewport,
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
    "__version__",
]
