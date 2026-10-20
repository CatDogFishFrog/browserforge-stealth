"""
CLI entry point for browserforge-stealth.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from browserforge_stealth.generator import FingerprintGenerator
from browserforge_stealth.models import DeviceType, Fingerprint, OperatingSystem


def _format_summary(fp: Fingerprint) -> str:
    os_name = fp.os.value if isinstance(fp.os, OperatingSystem) else str(fp.os)
    dev_name = fp.device_type.value if isinstance(fp.device_type, DeviceType) else str(fp.device_type)
    screen_str = f"{fp.screen_size[0]}x{fp.screen_size[1]}"
    viewport_str = f"{fp.viewport[0]}x{fp.viewport[1]}"
    ram_str = f"{fp.device_memory} GB" if fp.device_memory is not None else "Unknown"
    cores_str = str(fp.hardware_concurrency) if fp.hardware_concurrency is not None else "Unknown"
    tz_str = fp.timezone_id if fp.timezone_id else "None"

    lines = [
        "============================================================",
        "BrowserForge Fingerprint Summary",
        "============================================================",
        f"OS:       {os_name}",
        f"Device:   {dev_name}",
        f"UA:       {fp.user_agent}",
        f"Screen:   {screen_str}",
        f"Viewport: {viewport_str}",
        f"DPR:      {fp.device_scale_factor}",
        f"GPU:      {fp.gpu_renderer}",
        f"RAM:      {ram_str}",
        f"Cores:    {cores_str}",
        f"Locale:   {fp.locale}",
        f"Timezone: {tz_str}",
        "============================================================",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="browserforge-stealth",
        description="Realistic and intelligent browser fingerprint generator & inspector.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    gen_parser = subparsers.add_parser("generate", help="Generate a realistic fingerprint")
    gen_parser.add_argument(
        "--os",
        choices=["windows", "macos", "linux", "android", "ios"],
        default=None,
        help="Operating system",
    )
    gen_parser.add_argument(
        "--device",
        choices=["desktop", "mobile"],
        default="desktop",
        help="Device type (default: desktop)",
    )
    gen_parser.add_argument(
        "--locale",
        default="en-US",
        help="Locale string (default: en-US)",
    )
    gen_parser.add_argument(
        "--timezone",
        default=None,
        help="Timezone identifier (e.g. Europe/Kyiv)",
    )
    gen_parser.add_argument(
        "--json",
        action="store_true",
        help="Output formatted JSON to stdout",
    )
    gen_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Path to write JSON file",
    )

    inspect_parser = subparsers.add_parser("inspect", help="Inspect an existing fingerprint JSON file")
    inspect_parser.add_argument(
        "file",
        help="Path to fingerprint JSON file",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.subcommand == "generate":
        generator = FingerprintGenerator(
            os=args.os,
            device_type=args.device,
            locale=args.locale,
            timezone_id=args.timezone,
        )
        fp = generator.generate()

        json_str = fp.to_json(indent=2)
        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json_str, encoding="utf-8")

        if args.json:
            print(json_str)
        elif not args.output:
            print(_format_summary(fp))
        else:
            print(f"Fingerprint written to {args.output}")
        return 0

    if args.subcommand == "inspect":
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            return 1
        content = file_path.read_text(encoding="utf-8")
        fp = Fingerprint.from_json(content)
        print(_format_summary(fp))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
