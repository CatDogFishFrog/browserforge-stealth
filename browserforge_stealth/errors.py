"""
Custom exception hierarchy for browserforge-stealth.
"""


class FingerprintError(Exception):
    """Base exception for all fingerprint errors."""


class GenerationError(FingerprintError):
    """Raised when fingerprint generation fails or constraints cannot be satisfied."""


class RealismError(FingerprintError):
    """Raised when fingerprint realism validation fails."""


class SerializationError(FingerprintError):
    """Raised when serialization or deserialization of a fingerprint fails."""
