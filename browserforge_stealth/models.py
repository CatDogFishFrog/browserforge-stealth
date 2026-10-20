from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from browserforge_stealth.errors import SerializationError


class OperatingSystem(StrEnum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"


class DeviceType(StrEnum):
    DESKTOP = "desktop"
    MOBILE = "mobile"


def coerce_os(val: OperatingSystem | str) -> OperatingSystem:
    if isinstance(val, OperatingSystem):
        return val
    s = str(val).lower()
    if s in ("windows", "win", "win32"):
        return OperatingSystem.WINDOWS
    if s in ("macos", "mac", "darwin", "osx"):
        return OperatingSystem.MACOS
    if s in ("linux",):
        return OperatingSystem.LINUX
    if s in ("android",):
        return OperatingSystem.ANDROID
    if s in ("ios", "iphone", "ipad"):
        return OperatingSystem.IOS
    return OperatingSystem(val)


def coerce_device_type(val: DeviceType | str) -> DeviceType:
    if isinstance(val, DeviceType):
        return val
    s = str(val).lower()
    if s in ("desktop", "pc"):
        return DeviceType.DESKTOP
    if s in ("mobile", "phone", "tablet"):
        return DeviceType.MOBILE
    return DeviceType(val)


@dataclass
class ScreenInfo:
    width: int
    height: int
    device_scale_factor: float = 1.0
    avail_width: int | None = None
    avail_height: int | None = None


@dataclass
class HardwareInfo:
    cores: int | None = None
    memory_gb: float | None = None
    gpu_renderer: str = ""


@dataclass
class Viewport:
    width: int
    height: int

    def to_tuple(self) -> tuple[int, int]:
        return (self.width, self.height)


def _default_json_serializer(o: Any) -> Any:
    if is_dataclass(o) and not isinstance(o, type):
        return asdict(o)
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, (OperatingSystem, DeviceType)):
        return o.value
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def _parse_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    elif not isinstance(value, datetime):
        raise TypeError(f"Invalid created_at type: {type(value).__name__}")
    return value if value.tzinfo else value.replace(tzinfo=UTC)


@dataclass
class Fingerprint:
    """A complete, self-consistent browser fingerprint.

    ``raw_data`` holds the injectable payload (``navigator``, ``screen``, ``headers``, ``videoCard``, ...),
    while the remaining fields are typed metadata used to build browser contexts.
    """

    schema_version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    device_type: DeviceType = DeviceType.DESKTOP
    os: OperatingSystem = OperatingSystem.WINDOWS
    locale: str = "en-US"
    timezone_id: str | None = None
    viewport: tuple[int, int] = (1920, 1080)
    raw_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = int(self.schema_version)
        self.created_at = _parse_datetime(self.created_at)
        self.device_type = coerce_device_type(self.device_type)
        self.os = coerce_os(self.os)
        self.locale = str(self.locale)
        if self.timezone_id is not None:
            self.timezone_id = str(self.timezone_id)
        viewport: Any = self.viewport
        if isinstance(viewport, Viewport):
            viewport = viewport.to_tuple()
        self.viewport = (int(viewport[0]), int(viewport[1]))

    # --- raw payload sections -------------------------------------------------------------------

    @property
    def navigator(self) -> dict[str, Any]:
        return self.raw_data.get("navigator") or {}

    @property
    def screen(self) -> dict[str, Any]:
        return self.raw_data.get("screen") or {}

    @property
    def headers(self) -> dict[str, str]:
        return self.raw_data.get("headers") or {}

    @property
    def video_card(self) -> dict[str, Any]:
        return self.raw_data.get("videoCard") or {}

    # --- typed getters --------------------------------------------------------------------------

    @property
    def user_agent(self) -> str:
        if ua := self.navigator.get("userAgent"):
            return str(ua)
        for key, value in self.headers.items():
            if key.lower() == "user-agent":
                return str(value)
        return ""

    @property
    def screen_size(self) -> tuple[int, int]:
        width, height = self.screen.get("width"), self.screen.get("height")
        if width is not None and height is not None:
            return (int(width), int(height))
        return self.viewport

    @property
    def device_scale_factor(self) -> float:
        return float(self.screen.get("devicePixelRatio", 1.0))

    @property
    def gpu_renderer(self) -> str:
        return str(self.video_card.get("renderer") or "")

    @property
    def hardware_concurrency(self) -> int | None:
        cores = self.navigator.get("hardwareConcurrency")
        return int(cores) if cores is not None else None

    @property
    def device_memory(self) -> float | None:
        memory = self.navigator.get("deviceMemory")
        return float(memory) if memory is not None else None

    @property
    def screen_info(self) -> ScreenInfo:
        screen = self.screen
        width, height = self.screen_size
        return ScreenInfo(
            width=width,
            height=height,
            device_scale_factor=self.device_scale_factor,
            avail_width=int(screen["availWidth"]) if screen.get("availWidth") is not None else None,
            avail_height=int(screen["availHeight"]) if screen.get("availHeight") is not None else None,
        )

    @property
    def hardware_info(self) -> HardwareInfo:
        return HardwareInfo(
            cores=self.hardware_concurrency,
            memory_gb=self.device_memory,
            gpu_renderer=self.gpu_renderer,
        )

    # --- serialization --------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat(),
            "device_type": self.device_type.value,
            "os": self.os.value,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "viewport": list(self.viewport),
            "raw_data": self.raw_data,
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=_default_json_serializer)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Fingerprint:
        if not isinstance(d, Mapping):
            raise SerializationError(f"Expected mapping, got {type(d).__name__}")
        try:
            for key in ("device_type", "os", "locale", "viewport", "raw_data"):
                if key not in d:
                    raise ValueError(f"Missing required key: {key!r}")
            viewport = d["viewport"]
            if not isinstance(viewport, (tuple, list)) or len(viewport) != 2:
                raise ValueError(f"Viewport must be a 2-tuple or list, got {viewport!r}")
            raw_data = d["raw_data"]
            if not isinstance(raw_data, dict):
                raise ValueError(f"raw_data must be a dict, got {type(raw_data).__name__}")
            return cls(
                schema_version=int(d.get("schema_version", 1)),
                created_at=_parse_datetime(d.get("created_at")),
                device_type=DeviceType(d["device_type"]),
                os=OperatingSystem(d["os"]),
                locale=str(d["locale"]),
                timezone_id=d.get("timezone_id"),
                viewport=(int(viewport[0]), int(viewport[1])),
                raw_data=raw_data,
            )
        except Exception as exc:
            raise SerializationError(f"Failed to deserialize Fingerprint from dict: {exc}") from exc

    @classmethod
    def from_json(cls, s: str) -> Fingerprint:
        try:
            data = json.loads(s)
        except Exception as exc:
            raise SerializationError(f"Invalid JSON string: {exc}") from exc
        return cls.from_dict(data)

    # --- browser adaptation ---------------------------------------------------------------------

    def context_options(self, browser_version: str | None = None) -> dict[str, Any]:
        """Keyword arguments for ``browser.new_context(**options)`` (Playwright / Patchright)."""
        from browserforge_stealth.injection import context_options

        return context_options(self, browser_version=browser_version)

    def init_script(self, browser_version: str | None = None) -> str:
        """JavaScript init script that overrides browser APIs before page scripts execute."""
        from browserforge_stealth.injection import build_init_script

        return build_init_script(self, browser_version=browser_version)

    async def apply(self, context: Any, browser_version: str | None = None) -> None:
        """Injects the fingerprint into an async browser context via ``add_init_script``."""
        from browserforge_stealth.injection import apply_to_context

        await apply_to_context(context, self, browser_version=browser_version)

    def apply_sync(self, context: Any, browser_version: str | None = None) -> None:
        """Injects the fingerprint into a sync browser context via ``add_init_script``."""
        from browserforge_stealth.injection import apply_to_context_sync

        apply_to_context_sync(context, self, browser_version=browser_version)
