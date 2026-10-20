"""
Low-level sampling of raw browser fingerprints from Apify's Bayesian networks.

The sampler knows nothing about realism: it only draws a statistically consistent sample
(headers + navigator + screen + GPU + codecs) and assembles it into a plain dictionary.
Realism filtering, normalization and the public ``Fingerprint`` contract live in
:mod:`browserforge_stealth.generator`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from apify_fingerprint_datapoints import get_fingerprint_network

from browserforge_stealth.bayesian_network import BayesianNetwork, get_possible_values
from browserforge_stealth.errors import GenerationError
from browserforge_stealth.headers import HeaderGenerator
from browserforge_stealth.headers.utils import get_user_agent

_STRINGIFIED = "*STRINGIFIED*"
_MISSING = "*MISSING_VALUE*"

_NAVIGATOR_KEYS: tuple[str, ...] = (
    "userAgent",
    "userAgentData",
    "doNotTrack",
    "appCodeName",
    "appName",
    "appVersion",
    "oscpu",
    "webdriver",
    "platform",
    "deviceMemory",
    "product",
    "productSub",
    "vendor",
    "vendorSub",
    "extraProperties",
    "hardwareConcurrency",
    "languages",
    "maxTouchPoints",
)

_NAVIGATOR_DEFAULTS: dict[str, Any] = {
    "doNotTrack": None,
    "appCodeName": "Mozilla",
    "appName": "Netscape",
    "appVersion": "5.0",
    "oscpu": None,
    "webdriver": "false",
    "product": "Gecko",
    "productSub": "20030107",
    "vendor": "Google Inc.",
    "vendorSub": "",
    "extraProperties": {},
    "languages": ["en-US", "en"],
    "maxTouchPoints": 0,
}

_SCREEN_DEFAULTS: dict[str, Any] = {
    "availHeight": 1040,
    "availWidth": 1920,
    "availTop": 0,
    "availLeft": 0,
    "colorDepth": 24,
    "height": 1080,
    "pixelDepth": 24,
    "width": 1920,
    "devicePixelRatio": 1.0,
    "pageXOffset": 0,
    "pageYOffset": 0,
    "innerHeight": 900,
    "outerHeight": 1040,
    "outerWidth": 1920,
    "innerWidth": 1920,
    "screenX": 0,
    "clientWidth": 1920,
    "clientHeight": 900,
    "hasHDR": False,
}


@dataclass(frozen=True)
class ScreenConstraints:
    """Bounds for the physical screen size of a sampled fingerprint."""

    min_width: int | None = None
    max_width: int | None = None
    min_height: int | None = None
    max_height: int | None = None

    def __post_init__(self) -> None:
        if (
            self.min_width is not None and self.max_width is not None and self.min_width > self.max_width
        ) or (
            self.min_height is not None and self.max_height is not None and self.min_height > self.max_height
        ):
            raise ValueError("Invalid screen constraints: min values cannot be greater than max values")

    def is_set(self) -> bool:
        """True if at least one bound is specified."""
        return any(
            value is not None for value in (self.min_width, self.max_width, self.min_height, self.max_height)
        )

    def accepts(self, width: int, height: int) -> bool:
        """True if the given screen size satisfies every specified bound."""
        return (
            width >= (self.min_width or 0)
            and height >= (self.min_height or 0)
            and width <= (self.max_width or 100_000)
            and height <= (self.max_height or 100_000)
        )


class FingerprintSampler:
    """Draws raw fingerprint dictionaries from the Apify Bayesian networks."""

    network = BayesianNetwork(get_fingerprint_network())

    def __init__(self) -> None:
        self.header_generator = HeaderGenerator()

    def sample(
        self,
        *,
        screen: ScreenConstraints | None = None,
        strict: bool = False,
        **header_kwargs: Any,
    ) -> dict[str, Any]:
        """Samples one raw fingerprint.

        Args:
            screen: Optional screen-size constraints.
            strict: Raise instead of relaxing constraints that cannot be satisfied.
            **header_kwargs: Options forwarded to ``HeaderGenerator.generate``
                (``browser``, ``os``, ``device``, ``locale``, ...).

        Returns:
            A dictionary with ``navigator``, ``screen``, ``headers``, ``videoCard``, codecs and extras.
        """
        filtered_values: dict[str, Any] = {}
        partial = self._partial_csp(strict, screen, filtered_values)

        call_kwargs = dict(header_kwargs)
        if partial:
            call_kwargs["user_agent"] = partial["userAgent"]
        headers = self.header_generator.generate(**call_kwargs, strict=strict)
        user_agent = get_user_agent(headers)
        if user_agent is None:
            raise GenerationError("Failed to find User-Agent in generated headers")

        sample = self.network.generate_consistent_sample_when_possible(
            {**filtered_values, "userAgent": (user_agent,)}
        )
        if sample is None and filtered_values:
            if strict:
                raise GenerationError(
                    "Cannot generate fingerprint: screen constraints are too restrictive for this User-Agent"
                )
            sample = self.network.generate_consistent_sample_when_possible({"userAgent": (user_agent,)})
        if sample is None:
            raise GenerationError(f"Cannot generate fingerprint for User-Agent {user_agent!r}")

        for attribute, value in list(sample.items()):
            if value == _MISSING:
                sample[attribute] = None
            elif isinstance(value, str) and value.startswith(_STRINGIFIED):
                sample[attribute] = json.loads(value[len(_STRINGIFIED) :])

        accepted = headers.get("Accept-Language", "")
        if accepted:
            sample["languages"] = [part.split(";", 1)[0] for part in accepted.split(",")]
        return self._assemble(sample, headers)

    def _partial_csp(
        self,
        strict: bool,
        screen: ScreenConstraints | None,
        filtered_values: dict[str, Any],
    ) -> dict[str, Any] | None:
        if screen is None or not screen.is_set():
            return None

        filtered_values["screen"] = [
            screen_string
            for screen_string in self.network.nodes_by_name["screen"].possible_values
            if self._screen_within(screen_string, screen)
        ]
        try:
            return get_possible_values(self.network, filtered_values)
        except Exception as exc:
            if strict:
                raise GenerationError(f"Screen constraints cannot be satisfied: {exc}") from exc
            del filtered_values["screen"]
        return None

    @staticmethod
    def _screen_within(screen_string: str, constraints: ScreenConstraints) -> bool:
        try:
            screen = json.loads(screen_string[len(_STRINGIFIED) :])
            return constraints.accepts(int(screen.get("width", -1)), int(screen.get("height", -1)))
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _assemble(sample: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        navigator: dict[str, Any] = {k: sample[k] for k in _NAVIGATOR_KEYS if k in sample}
        for key, default in _NAVIGATOR_DEFAULTS.items():
            navigator.setdefault(key, default)
        languages = navigator["languages"]
        navigator["language"] = languages[0] if languages else "en-US"

        screen = {**_SCREEN_DEFAULTS, **(sample.get("screen") or {})}

        return {
            "screen": screen,
            "navigator": navigator,
            "headers": dict(headers),
            "videoCodecs": sample.get("videoCodecs") or {},
            "audioCodecs": sample.get("audioCodecs") or {},
            "pluginsData": sample.get("pluginsData") or {},
            "battery": sample.get("battery"),
            "videoCard": sample.get("videoCard"),
            "multimediaDevices": sample.get("multimediaDevices") or [],
            "fonts": sample.get("fonts") or [],
            "mockWebRTC": False,
            "slim": False,
        }
