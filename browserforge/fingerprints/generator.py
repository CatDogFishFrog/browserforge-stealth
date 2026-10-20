import copy
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from apify_fingerprint_datapoints import get_fingerprint_network

from browserforge.bayesian_network import BayesianNetwork, get_possible_values
from browserforge.headers import HeaderGenerator
from browserforge.headers.utils import get_user_agent

try:
    import orjson as json

    USE_ORJSON = True
except ImportError:
    import json

    USE_ORJSON = False

DATA_DIR: Path = Path(__file__).parent / 'data'


@dataclass
class ScreenFingerprint:
    availHeight: int
    availWidth: int
    availTop: int
    availLeft: int
    colorDepth: int
    height: int
    pixelDepth: int
    width: int
    devicePixelRatio: float
    pageXOffset: int
    pageYOffset: int
    innerHeight: int
    outerHeight: int
    outerWidth: int
    innerWidth: int
    screenX: int
    clientWidth: int
    clientHeight: int
    hasHDR: bool


@dataclass
class NavigatorFingerprint:
    userAgent: str
    userAgentData: Dict[str, str]
    doNotTrack: Optional[str]
    appCodeName: str
    appName: str
    appVersion: str
    oscpu: str
    webdriver: str
    language: str
    languages: List[str]
    platform: str
    deviceMemory: Optional[int]
    hardwareConcurrency: int
    product: str
    productSub: str
    vendor: str
    vendorSub: str
    maxTouchPoints: int
    extraProperties: Dict[str, str]


@dataclass
class VideoCard:
    renderer: str
    vendor: str


@dataclass
class Fingerprint:
    """Output data of the fingerprint generator"""

    screen: ScreenFingerprint
    navigator: NavigatorFingerprint
    headers: Dict[str, str]
    videoCodecs: Dict[str, str]
    audioCodecs: Dict[str, str]
    pluginsData: Dict[str, str]
    battery: Optional[Dict[str, str]]
    videoCard: Optional[VideoCard]
    multimediaDevices: List[str]
    fonts: List[str]
    mockWebRTC: Optional[bool]
    slim: Optional[bool]

    def dumps(self) -> str:
        """
        Dumps the dataclass as a JSON string.
        """
        if USE_ORJSON:
            return json.dumps(self).decode()
        # Built-in `json` does not take dataclass objects
        # Instead, convert to a dict first
        return json.dumps(asdict(self))

    def asdict(self) -> Dict[str, Any]:
        """Convert to dict matching dataclasses.asdict."""
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        try:
            val = getattr(self, key)
            if is_dataclass(val):
                return asdict(val)
            return val
        except AttributeError:
            raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def keys(self):
        return asdict(self).keys()

    def values(self):
        return asdict(self).values()

    def items(self):
        return asdict(self).items()

    @property
    def user_agent(self) -> str:
        return self.navigator.userAgent

    @property
    def screen_size(self) -> tuple[int, int]:
        return (self.screen.width, self.screen.height)

    @property
    def device_scale_factor(self) -> float:
        return float(self.screen.devicePixelRatio)

    @property
    def gpu_renderer(self) -> str:
        return self.videoCard.renderer if self.videoCard else ""

    @property
    def hardware_concurrency(self) -> int | None:
        return self.navigator.hardwareConcurrency

    @property
    def device_memory(self) -> float | None:
        return float(self.navigator.deviceMemory) if self.navigator.deviceMemory is not None else None

    @property
    def viewport(self) -> tuple[int, int]:
        from browserforge_stealth.realism import derive_viewport
        plat = self.navigator.platform or ""
        if "Win" in plat:
            os_name = "windows"
        elif "Mac" in plat:
            os_name = "macos"
        elif "Android" in plat or "arm" in plat.lower():
            os_name = "android"
        elif "iPhone" in plat:
            os_name = "ios"
        else:
            os_name = "linux"
        dev = "mobile" if "Mobile" in self.navigator.userAgent else "desktop"
        return derive_viewport({"screen": asdict(self.screen)}, os=os_name, device_type=dev)

    def to_stealth(self) -> Any:
        from browserforge_stealth.models import (
            DeviceType,
            Fingerprint as StealthFingerprint,
            OperatingSystem,
        )
        dev = DeviceType.MOBILE if "Mobile" in self.navigator.userAgent else DeviceType.DESKTOP
        plat = self.navigator.platform or ""
        if "Win" in plat:
            os_val = OperatingSystem.WINDOWS
        elif "Mac" in plat:
            os_val = OperatingSystem.MACOS
        elif "iPhone" in plat:
            os_val = OperatingSystem.IOS
        elif "Android" in plat or dev == DeviceType.MOBILE:
            os_val = OperatingSystem.ANDROID
        else:
            os_val = OperatingSystem.LINUX

        return StealthFingerprint(
            device_type=dev,
            os=os_val,
            locale=self.navigator.language or "en-US",
            viewport=self.viewport,
            raw_data=asdict(self),
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.to_stealth().to_dict()

    def to_json(self, indent: Optional[int] = None) -> str:
        return self.to_stealth().to_json(indent=indent)


@dataclass
class Screen:
    """Constrains the screen dimensions of the generated fingerprint"""

    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None

    def __post_init__(self):
        if (
            None not in (self.min_width, self.max_width)
            and self.min_width > self.max_width
            or None not in (self.min_height, self.max_height)
            and self.min_height > self.max_height
        ):
            raise ValueError(
                "Invalid screen constraints: min values cannot be greater than max values"
            )

    def is_set(self) -> bool:
        """
        Returns true if any constraints were set
        """
        return any(value is not None for value in self.__dict__.values())


def _sample_to_dict(
    sample: Dict[str, Any],
    headers: Dict[str, str],
    mock_webrtc: bool = False,
    slim: bool = False,
) -> Dict[str, Any]:
    if "navigator" in sample and isinstance(sample["navigator"], dict):
        d = copy.deepcopy(sample)
        if "headers" not in d:
            d["headers"] = headers
        return d
    nav_keys = (
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
        "language",
        "maxTouchPoints",
    )
    navigator = {k: sample[k] for k in nav_keys if k in sample}
    if "languages" in navigator and "language" not in navigator and navigator["languages"]:
        navigator["language"] = navigator["languages"][0]

    return {
        "screen": sample.get("screen", {}),
        "navigator": navigator,
        "headers": headers,
        "videoCodecs": sample.get("videoCodecs", {}),
        "audioCodecs": sample.get("audioCodecs", {}),
        "pluginsData": sample.get("pluginsData", {}),
        "battery": sample.get("battery"),
        "videoCard": sample.get("videoCard"),
        "multimediaDevices": sample.get("multimediaDevices", []),
        "fonts": sample.get("fonts", []),
        "mockWebRTC": mock_webrtc,
        "slim": slim,
    }


class FingerprintGenerator:
    """Generates realistic browser fingerprints"""

    fingerprint_generator_network = BayesianNetwork(get_fingerprint_network())

    def __init__(
        self,
        screen: Optional[Screen] = None,
        strict: bool = False,
        mock_webrtc: bool = False,
        slim: bool = False,
        realistic: bool = True,
        **header_kwargs,
    ):
        """
        Initializes the FingerprintGenerator with the given options.

        Parameters:
            screen (Screen, optional): Screen constraints for the generated fingerprint.
            strict (bool, optional): Whether to raise an exception if the constraints are too strict. Default is False.
            mock_webrtc (bool, optional): Whether to mock WebRTC when injecting the fingerprint. Default is False.
            slim (bool, optional): Disables performance-heavy evasions when injecting the fingerprint. Default is False.
            realistic (bool, optional): Whether to sanitize and validate realistic fingerprint rules. Default is True.
            **header_kwargs: Header generation options for HeaderGenerator
        """
        self.header_generator: HeaderGenerator = HeaderGenerator(**header_kwargs)

        # Set default options
        self.screen: Optional[Screen] = screen
        self.strict: bool = strict
        self.mock_webrtc: bool = mock_webrtc
        self.slim: bool = slim
        self.realistic: bool = realistic

    def generate(
        self,
        *,
        screen: Optional[Screen] = None,
        strict: Optional[bool] = None,
        mock_webrtc: Optional[bool] = None,
        slim: Optional[bool] = None,
        realistic: Optional[bool] = None,
        **header_kwargs,
    ) -> Fingerprint:
        """
        Generates a fingerprint and a matching set of ordered headers using a combination of the default options
        specified in the constructor and their possible overrides provided here.

        Parameters:
            screen (Screen, optional): Screen constraints for the generated fingerprint.
            strict (bool, optional): Whether to raise an exception if the constraints are too strict.
            mock_webrtc (bool, optional): Whether to mock WebRTC when injecting the fingerprint. Default is False.
            slim (bool, optional): Disables performance-heavy evasions when injecting the fingerprint. Default is False.
            realistic (bool, optional): Whether to enforce realistic constraints. Default is True.
            **header_kwargs: Additional header generation options for HeaderGenerator.generate
        """
        if header_kwargs is None:
            header_kwargs = {}

        # merge new options with old
        screen = _first(screen, self.screen)
        strict = _first(strict, self.strict)
        is_realistic = _first(realistic, self.realistic, True)
        mock_webrtc = _first(mock_webrtc, self.mock_webrtc)
        slim = _first(slim, self.slim)

        is_mobile_req = False
        device_opt = header_kwargs.get("device", self.header_generator.options.get("devices"))
        if device_opt and any(
            "mobile" in str(d).lower()
            for d in (device_opt if isinstance(device_opt, tuple) else (device_opt,))
        ):
            is_mobile_req = True

        if is_realistic and (screen is None or not screen.is_set()) and not is_mobile_req:
            screen = Screen(min_width=1280, min_height=720)

        max_attempts = 60 if is_realistic else 1
        rejected_issues: List[str] = []
        last_sample_dict = None
        last_headers: Dict[str, str] = {}

        for _ in range(max_attempts):
            filtered_values: Dict[str, str] = {}
            partial_csp = self.partial_csp(
                strict=strict, screen=screen, filtered_values=filtered_values
            )

            current_header_kwargs = dict(header_kwargs)
            if partial_csp:
                current_header_kwargs["user_agent"] = partial_csp["userAgent"]
            headers = self.header_generator.generate(**current_header_kwargs)
            last_headers = headers
            user_agent = get_user_agent(headers)
            if user_agent is None:
                raise ValueError("Failed to find User-Agent in generated response")

            while True:
                fingerprint: Optional[Dict] = (
                    self.fingerprint_generator_network.generate_consistent_sample_when_possible(
                        {**filtered_values, "userAgent": (user_agent,)}
                    )
                )
                if fingerprint is not None:
                    break
                if strict:
                    raise ValueError(
                        "Cannot generate headers. User-Agent may be invalid, or screen constraints are too restrictive."
                    )
                filtered_values = {}

            for attribute in list(fingerprint.keys()):
                if fingerprint[attribute] == "*MISSING_VALUE*":
                    fingerprint[attribute] = None
                if isinstance(fingerprint[attribute], str) and fingerprint[attribute].startswith(
                    "*STRINGIFIED*"
                ):
                    fingerprint[attribute] = json.loads(fingerprint[attribute][len("*STRINGIFIED*") :])

            if not is_realistic:
                accept_language_header_value = headers.get("Accept-Language", "")
                accepted_languages = [
                    locale.split(";", 1)[0] for locale in accept_language_header_value.split(",")
                ]
                fingerprint["languages"] = accepted_languages
                return self._transform_fingerprint(
                    fingerprint,
                    headers,
                    mock_webrtc,
                    slim,
                )

            # When is_realistic is True:
            os_opt = header_kwargs.get("os", self.header_generator.options.get("os"))
            if os_opt:
                detected_os = str(os_opt[0] if isinstance(os_opt, (tuple, list)) else os_opt).lower()
            else:
                plat = str(fingerprint.get("platform", "")).lower()
                ua_low = user_agent.lower()
                if "win" in ua_low or "win32" in plat:
                    detected_os = "windows"
                elif "mac" in ua_low or "macintel" in plat:
                    detected_os = "macos"
                elif "android" in ua_low:
                    detected_os = "android"
                elif "iphone" in ua_low or "ios" in ua_low:
                    detected_os = "ios"
                else:
                    detected_os = "linux"

            detected_device = "mobile" if ("mobile" in user_agent.lower() or is_mobile_req) else "desktop"

            locale_opt = header_kwargs.get("locale", self.header_generator.options.get("locales"))
            if locale_opt:
                detected_locale = str(
                    locale_opt[0] if isinstance(locale_opt, (tuple, list)) else locale_opt
                )
            else:
                acc_lang = headers.get("Accept-Language", "en-US")
                detected_locale = acc_lang.split(",")[0].split(";")[0] or "en-US"

            from browserforge_stealth.normalization import normalize_fingerprint_dict
            from browserforge_stealth.realism import realism_issues

            raw_dict = _sample_to_dict(fingerprint, headers, mock_webrtc, slim)
            normalized_dict = normalize_fingerprint_dict(
                raw_dict,
                os=detected_os,
                locale=detected_locale,
                device_type=detected_device,
            )
            last_sample_dict = normalized_dict

            issues = realism_issues(normalized_dict, os=detected_os, device_type=detected_device)
            if not issues:
                return self._transform_fingerprint(
                    normalized_dict,
                    headers=normalized_dict.get("headers", headers),
                    mock_webrtc=mock_webrtc,
                    slim=slim,
                )
            rejected_issues.extend(issues)

        if strict:
            raise ValueError(
                f"Failed to generate realistic fingerprint after {max_attempts} attempts. "
                f"Issues: {sorted(set(rejected_issues))[:5]}"
            )

        assert last_sample_dict is not None
        return self._transform_fingerprint(
            last_sample_dict,
            headers=last_sample_dict.get("headers", last_headers),
            mock_webrtc=mock_webrtc,
            slim=slim,
        )

    def partial_csp(
        self, strict: Optional[bool], screen: Optional[Screen], filtered_values: Dict
    ) -> Optional[Dict]:
        """
        Generates partial content security policy (CSP) based on the provided options and filtered values.

        Parameters:
            strict (Optional[bool): Whether to raise an exception if the constraints are too strict.
            screen (Optional[Screen]): Screen for generating the partial CSP.
            filtered_values (Dict): Filtered values used for generating the partial CSP.

        Returns:
            Dict: Partial CSP values.
        """
        # if extensive constraints need to be used
        if not (screen and screen.is_set()):
            return None

        filtered_values['screen'] = [
            screen_string
            for screen_string in self.fingerprint_generator_network.nodes_by_name[
                'screen'
            ].possible_values
            if self._is_screen_within_constraints(screen_string, screen)
        ]

        try:
            return get_possible_values(self.fingerprint_generator_network, filtered_values)
        except Exception as e:
            if strict:
                raise e
            del filtered_values['screen']
        return None

    @staticmethod
    def _is_screen_within_constraints(screen_string: str, screen_options: Screen) -> bool:
        """
        Checks if the given screen dimensions are within the specified constraints.

        Parameters:
            screen_string (str): Stringified screen dimensions.
            screen_options (Screen): Screen constraint options.

        Returns:
            bool: True if the screen dimensions are within the constraints, False otherwise.
        """
        try:
            screen = json.loads(screen_string[len('*STRINGIFIED*') :])
            return (
                # Ensure that the screen width/height are greater than the minimum constraints
                # Default missing values to -1 to ensure they are excluded
                screen.get('width', -1) >= (screen_options.min_width or 0)
                and screen.get('height', -1) >= (screen_options.min_height or 0)
                # Ensure that the screen width/height are less than the maximum constraints
                and screen.get('width', 0) <= (screen_options.max_width or 1e5)
                and screen.get('height', 0) <= (screen_options.max_height or 1e5)
            )
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _transform_fingerprint(
        fingerprint: Dict, headers: Dict, mock_webrtc: bool, slim: bool
    ) -> Fingerprint:
        """
        Transforms fingerprint into a final dataclass instance.

        Parameters:
            fingerprint (Dict): Fingerprint to be transformed.
            headers (Dict): Generated headers.
            mock_webrtc (bool): Whether to mock WebRTC when injecting the fingerprint.
            slim (bool): Disables performance-heavy evasions when injecting the fingerprint.

        Returns:
            Fingerprint: Transformed fingerprint as a Fingerprint dataclass instance.
        """

        nav_dict = (
            fingerprint["navigator"]
            if isinstance(fingerprint.get("navigator"), dict)
            else fingerprint
        )

        navigator_kwargs = {
            k: nav_dict[k]
            for k in (
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
            )
            if k in nav_dict
        }

        navigator_kwargs.setdefault("doNotTrack", None)
        navigator_kwargs.setdefault("appCodeName", "Mozilla")
        navigator_kwargs.setdefault("appName", "Netscape")
        navigator_kwargs.setdefault("appVersion", "5.0")
        navigator_kwargs.setdefault("oscpu", None)
        navigator_kwargs.setdefault("webdriver", "false")
        navigator_kwargs.setdefault("product", "Gecko")
        navigator_kwargs.setdefault("productSub", "20030107")
        navigator_kwargs.setdefault("vendor", "Google Inc.")
        navigator_kwargs.setdefault("vendorSub", "")
        navigator_kwargs.setdefault("extraProperties", {})
        navigator_kwargs.setdefault("languages", ["en-US", "en"])

        if "language" in nav_dict:
            navigator_kwargs["language"] = nav_dict["language"]
        elif navigator_kwargs.get("languages"):
            navigator_kwargs["language"] = navigator_kwargs["languages"][0]
        else:
            navigator_kwargs["language"] = "en-US"

        navigator_kwargs["maxTouchPoints"] = nav_dict.get("maxTouchPoints", 0)

        # Screen
        screen_data = fingerprint["screen"]
        if isinstance(screen_data, ScreenFingerprint):
            screen_obj = screen_data
        else:
            screen_kwargs = dict(screen_data)
            for field_name, default_val in (
                ("availHeight", 1040),
                ("availWidth", 1920),
                ("availTop", 0),
                ("availLeft", 0),
                ("colorDepth", 24),
                ("height", 1080),
                ("pixelDepth", 24),
                ("width", 1920),
                ("devicePixelRatio", 1.0),
                ("pageXOffset", 0),
                ("pageYOffset", 0),
                ("innerHeight", 900),
                ("outerHeight", 1040),
                ("outerWidth", 1920),
                ("innerWidth", 1920),
                ("screenX", 0),
                ("clientWidth", 1920),
                ("clientHeight", 900),
                ("hasHDR", False),
            ):
                screen_kwargs.setdefault(field_name, default_val)
            screen_obj = ScreenFingerprint(**screen_kwargs)

        # VideoCard
        vc = fingerprint.get("videoCard")
        if isinstance(vc, VideoCard):
            video_card_obj = vc
        elif isinstance(vc, dict):
            video_card_obj = VideoCard(**vc)
        else:
            video_card_obj = None

        return Fingerprint(
            screen=screen_obj,
            navigator=NavigatorFingerprint(**navigator_kwargs),
            headers=headers,
            videoCodecs=fingerprint.get("videoCodecs", {}),
            audioCodecs=fingerprint.get("audioCodecs", {}),
            pluginsData=fingerprint.get("pluginsData", {}),
            battery=fingerprint.get("battery"),
            videoCard=video_card_obj,
            multimediaDevices=fingerprint.get("multimediaDevices", []),
            fonts=fingerprint.get("fonts", []),
            mockWebRTC=mock_webrtc,
            slim=slim,
        )


def _first(*values):
    """
    Simple function that returns the first non-None value passed
    """
    return next((v for v in values if v is not None), None)
