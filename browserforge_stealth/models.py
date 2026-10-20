from __future__ import annotations

import copy
import json
from collections.abc import Iterator, Mapping
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


class _AttrDict(dict):
    """Dictionary subclass supporting attribute-style access for injector compatibility."""

    def __getattr__(self, name: str) -> Any:
        try:
            val = self[name]
            if isinstance(val, dict):
                return _AttrDict(val)
            return val
        except KeyError:
            raise AttributeError(f"No attribute {name!r}") from None

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _default_json_serializer(o: Any) -> Any:
    if is_dataclass(o) and not isinstance(o, type):
        return asdict(o)
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, (OperatingSystem, DeviceType)):
        return o.value
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


@dataclass
class Fingerprint:
    schema_version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    device_type: DeviceType = DeviceType.DESKTOP
    os: OperatingSystem = OperatingSystem.WINDOWS
    locale: str = "en-US"
    timezone_id: str | None = None
    viewport: tuple[int, int] = (1920, 1080)
    raw_data: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        *args: Any,
        schema_version: int = 1,
        created_at: datetime | str | None = None,
        device_type: DeviceType | str | None = None,
        os: OperatingSystem | str | None = None,
        locale: str | None = None,
        timezone_id: str | None = None,
        viewport: tuple[int, int] | list[int] | Viewport | None = None,
        raw_data: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        if len(args) == 8:
            schema_version, created_at, device_type, os, locale, timezone_id, viewport, raw_data = args
        elif len(args) == 5:
            device_type, os, locale, viewport, raw_data = args
        elif len(args) > 0:
            raise TypeError(
                f"Fingerprint.__init__ takes 5 or 8 positional arguments, but {len(args)} were given"
            )

        self.schema_version = int(schema_version)

        if created_at is None:
            self.created_at = datetime.now(UTC)
        elif isinstance(created_at, str):
            parsed = datetime.fromisoformat(created_at)
            self.created_at = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        elif isinstance(created_at, datetime):
            self.created_at = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
        else:
            raise TypeError(f"Invalid created_at type: {type(created_at).__name__}")

        self.device_type = DeviceType(device_type) if device_type is not None else DeviceType.DESKTOP
        self.os = OperatingSystem(os) if os is not None else OperatingSystem.WINDOWS
        self.locale = str(locale) if locale is not None else "en-US"
        self.timezone_id = str(timezone_id) if timezone_id is not None else None

        if isinstance(viewport, Viewport):
            self.viewport = viewport.to_tuple()
        elif viewport is not None:
            self.viewport = (int(viewport[0]), int(viewport[1]))
        else:
            self.viewport = (1920, 1080)

        self.raw_data = raw_data if raw_data is not None else {}

    @property
    def user_agent(self) -> str:
        nav = self.raw_data.get("navigator")
        if isinstance(nav, dict):
            if ua := nav.get("userAgent"):
                return str(ua)
        elif nav is not None and hasattr(nav, "userAgent"):
            return str(nav.userAgent)

        headers = self.raw_data.get("headers")
        if isinstance(headers, dict):
            for k, v in headers.items():
                if k.lower() == "user-agent":
                    return str(v)
        return ""

    @property
    def screen_size(self) -> tuple[int, int]:
        screen = self.raw_data.get("screen")
        if isinstance(screen, dict):
            w = screen.get("width")
            h = screen.get("height")
            if w is not None and h is not None:
                return (int(w), int(h))
        elif screen is not None and hasattr(screen, "width") and hasattr(screen, "height"):
            return (int(screen.width), int(screen.height))
        return self.viewport

    @property
    def device_scale_factor(self) -> float:
        screen = self.raw_data.get("screen")
        if isinstance(screen, dict):
            ratio = screen.get("devicePixelRatio", 1.0)
            return float(ratio)
        elif screen is not None and hasattr(screen, "devicePixelRatio"):
            return float(screen.devicePixelRatio)
        return 1.0

    @property
    def gpu_renderer(self) -> str:
        vc = self.raw_data.get("videoCard")
        if isinstance(vc, dict):
            return str(vc.get("renderer", ""))
        elif vc is not None and hasattr(vc, "renderer"):
            return str(vc.renderer or "")
        return ""

    @property
    def hardware_concurrency(self) -> int | None:
        nav = self.raw_data.get("navigator")
        if isinstance(nav, dict):
            hc = nav.get("hardwareConcurrency")
            return int(hc) if hc is not None else None
        elif nav is not None and hasattr(nav, "hardwareConcurrency"):
            hc = nav.hardwareConcurrency
            return int(hc) if hc is not None else None
        return None

    @property
    def device_memory(self) -> float | None:
        nav = self.raw_data.get("navigator")
        if isinstance(nav, dict):
            dm = nav.get("deviceMemory")
            return float(dm) if dm is not None else None
        elif nav is not None and hasattr(nav, "deviceMemory"):
            dm = nav.deviceMemory
            return float(dm) if dm is not None else None
        return None

    # Injector compatibility accessors
    @property
    def navigator(self) -> Any:
        nav = self.raw_data.get("navigator", {})
        if isinstance(nav, dict):
            return _AttrDict(nav)
        return nav

    @property
    def screen(self) -> Any:
        sc = self.raw_data.get("screen", {})
        if isinstance(sc, dict):
            return _AttrDict(sc)
        return sc

    @property
    def headers(self) -> dict[str, Any]:
        return self.raw_data.get("headers", {})

    @property
    def videoCard(self) -> Any:
        vc = self.raw_data.get("videoCard")
        if isinstance(vc, dict):
            return _AttrDict(vc)
        return vc

    @property
    def videoCodecs(self) -> Any:
        return self.raw_data.get("videoCodecs", {})

    @property
    def audioCodecs(self) -> Any:
        return self.raw_data.get("audioCodecs", {})

    @property
    def battery(self) -> Any:
        return self.raw_data.get("battery")

    @property
    def pluginsData(self) -> Any:
        return self.raw_data.get("pluginsData", {})

    @property
    def multimediaDevices(self) -> Any:
        return self.raw_data.get("multimediaDevices", [])

    @property
    def fonts(self) -> Any:
        return self.raw_data.get("fonts", [])

    @property
    def mockWebRTC(self) -> Any:
        return self.raw_data.get("mockWebRTC", False)

    @property
    def slim(self) -> Any:
        return self.raw_data.get("slim", False)

    @property
    def screen_info(self) -> ScreenInfo:
        sc = self.raw_data.get("screen", {})
        w, h = self.screen_size
        return ScreenInfo(
            width=w,
            height=h,
            device_scale_factor=self.device_scale_factor,
            avail_width=int(sc["availWidth"]) if sc.get("availWidth") is not None else None,
            avail_height=int(sc["availHeight"]) if sc.get("availHeight") is not None else None,
        )

    @property
    def hardware_info(self) -> HardwareInfo:
        return HardwareInfo(
            cores=self.hardware_concurrency,
            memory_gb=self.device_memory,
            gpu_renderer=self.gpu_renderer,
        )

    def asdict(self) -> dict[str, Any]:
        """Dictionary representation of raw_data."""
        return copy.deepcopy(self.raw_data)

    def dumps(self) -> str:
        """JSON dumps of raw_data for browserforge injector compatibility."""
        return json.dumps(self.raw_data, default=_default_json_serializer)

    def to_dict(self) -> dict[str, Any]:
        dev_val = (
            self.device_type.value if isinstance(self.device_type, DeviceType) else self.device_type
        )
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat(),
            "device_type": str(dev_val),
            "os": str(self.os.value if isinstance(self.os, OperatingSystem) else self.os),
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
            schema_version = int(d.get("schema_version", 1))

            created_at_val = d.get("created_at")
            if created_at_val is None:
                created_at = datetime.now(UTC)
            elif isinstance(created_at_val, datetime):
                created_at = created_at_val if created_at_val.tzinfo else created_at_val.replace(tzinfo=UTC)
            elif isinstance(created_at_val, str):
                created_at = datetime.fromisoformat(created_at_val)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=UTC)
            else:
                raise ValueError(f"Invalid created_at type: {type(created_at_val).__name__}")

            if "device_type" not in d:
                raise ValueError("Missing required key: 'device_type'")
            device_type = DeviceType(d["device_type"])

            if "os" not in d:
                raise ValueError("Missing required key: 'os'")
            os = OperatingSystem(d["os"])

            if "locale" not in d:
                raise ValueError("Missing required key: 'locale'")
            locale = str(d["locale"])

            timezone_id = d.get("timezone_id")
            if timezone_id is not None:
                timezone_id = str(timezone_id)

            if "viewport" not in d:
                raise ValueError("Missing required key: 'viewport'")
            vp = d["viewport"]
            if isinstance(vp, (tuple, list)) and len(vp) == 2:
                viewport = (int(vp[0]), int(vp[1]))
            else:
                raise ValueError(f"Viewport must be a 2-tuple or list, got {vp!r}")

            if "raw_data" not in d:
                raise ValueError("Missing required key: 'raw_data'")
            raw_data = d["raw_data"]
            if not isinstance(raw_data, dict):
                raise ValueError(f"raw_data must be a dict, got {type(raw_data).__name__}")

            return cls(
                schema_version=schema_version,
                created_at=created_at,
                device_type=device_type,
                os=os,
                locale=locale,
                timezone_id=timezone_id,
                viewport=viewport,
                raw_data=raw_data,
            )
        except Exception as exc:
            if isinstance(exc, SerializationError):
                raise
            raise SerializationError(f"Failed to deserialize Fingerprint from dict: {exc}") from exc

    @classmethod
    def from_json(cls, s: str) -> Fingerprint:
        try:
            data = json.loads(s)
        except Exception as exc:
            raise SerializationError(f"Invalid JSON string: {exc}") from exc
        return cls.from_dict(data)

    def __getitem__(self, key: str) -> Any:
        return self.raw_data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw_data.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self.raw_data

    def __iter__(self) -> Iterator[str]:
        return iter(self.raw_data)

    def __len__(self) -> int:
        return len(self.raw_data)

    def keys(self):
        return self.raw_data.keys()

    def values(self):
        return self.raw_data.values()

    def items(self):
        return self.raw_data.items()

    def context_options(self, browser_version: str | None = None) -> dict[str, Any]:
        """Builds context dictionary suitable for browser.new_context(**options)."""
        from browserforge_stealth.injection import context_options

        return context_options(self, browser_version=browser_version)

    def init_script(self, browser_version: str | None = None) -> str:
        """Builds JS init script overriding browser APIs before page scripts execute."""
        from browserforge_stealth.injection import build_init_script

        return build_init_script(self, browser_version=browser_version)

    async def apply(self, context: Any, browser_version: str | None = None) -> None:
        """Injects fingerprint into an async browser context via add_init_script."""
        from browserforge_stealth.injection import apply_to_context

        await apply_to_context(context, self, browser_version=browser_version)

    def apply_sync(self, context: Any, browser_version: str | None = None) -> None:
        """Injects fingerprint into a sync browser context via add_init_script."""
        from browserforge_stealth.injection import apply_to_context_sync

        apply_to_context_sync(context, self, browser_version=browser_version)
