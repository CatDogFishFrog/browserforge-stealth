# BrowserForge-Stealth

**Realistic, self-consistent browser fingerprints for Patchright, Playwright and anti-detect automation.**

BrowserForge-Stealth is a modernized fork of [`browserforge`](https://github.com/daijro/browserforge). It keeps the
Apify Bayesian fingerprint/header networks, but adds realism validation, Chromium GREASE brands, mobile profiles and
runtime browser-version retargeting. It is a standalone package with a single import name: `browserforge_stealth`.
It does **not** keep the old `browserforge` API.

## Why

Raw Bayesian samples regularly contain combinations that never occur on real devices:

* Brave traces in `sec-ch-ua` while the User-Agent claims Google Chrome;
* `navigator.deviceMemory` of 16/32 GB (Chrome caps it at 8);
* software GPUs (`SwiftShader`, `llvmpipe`, `Microsoft Basic Render Driver`);
* fractional `devicePixelRatio`, screens below 1280x720 on desktop, OS/platform mismatches;
* a frozen Chrome version that disagrees with the real browser binary.

BrowserForge-Stealth draws samples, sanitizes them, rejects unrealistic ones and retargets the result to the browser
that actually runs.

## Features

* **Typed contract:** `Fingerprint` with `OperatingSystem`, `DeviceType`, `ScreenInfo`, `HardwareInfo`, `Viewport`.
* **Rejection sampling:** `FingerprintGenerator(realistic=True)` retries until all realism rules pass.
* **Chromium GREASE brands** and clean Client Hints (`sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`).
* **Desktop and mobile** (Windows, macOS, Linux, Android, iOS) with matching touch points and UA tokens.
* **Retargeting:** UA, `appVersion`, `userAgentData` and headers follow the real engine version; hardware stays fixed.
* **Persistence:** `to_dict()` / `from_dict()` / `to_json()` / `from_json()` with a schema version.
* **Duck-typed injection:** works with any context exposing `add_init_script` (Patchright, Playwright).
* **CLI:** `browserforge-stealth generate` / `inspect`.

## Installation

```bash
pip install browserforge-stealth
pip install "browserforge-stealth[orjson]"   # optional faster JSON loading
```

Python 3.11+ is required. Patchright / Playwright are **not** dependencies; install the one you use.

## Quick start

```python
from browserforge_stealth import FingerprintGenerator

generator = FingerprintGenerator(os="windows", locale="uk-UA", timezone_id="Europe/Kyiv")
fp = generator.generate()

print(fp.user_agent)
print(fp.screen_size, fp.device_scale_factor, fp.viewport)
print(fp.gpu_renderer, fp.device_memory, fp.hardware_concurrency)
```

One-liner:

```python
from browserforge_stealth import generate_fingerprint

fp = generate_fingerprint(os="macos", locale="en-US")
```

### Async Playwright / Patchright

```python
import asyncio
from patchright.async_api import async_playwright   # or: from playwright.async_api import async_playwright
from browserforge_stealth import generate_fingerprint


async def main() -> None:
    fp = generate_fingerprint(os="windows", locale="en-US", timezone_id="Europe/Kyiv")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(**fp.context_options(browser.version))
        await fp.apply(context, browser_version=browser.version)
        page = await context.new_page()
        await page.goto("https://example.com")
        await browser.close()


asyncio.run(main())
```

### Sync

```python
from playwright.sync_api import sync_playwright
from browserforge_stealth import apply_to_context_sync, generate_fingerprint

fp = generate_fingerprint(os="linux")
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(**fp.context_options(browser.version))
    apply_to_context_sync(context, fp, browser_version=browser.version)
```

### Mobile

```python
fp = generate_fingerprint(device_type="mobile", os="android", locale="uk-UA")
print(fp.user_agent)                  # contains "Mobile" and "Android"
print(fp.navigator["maxTouchPoints"])  # >= 5
```

### Saving a profile

```python
from browserforge_stealth import Fingerprint

Path("profile.json").write_text(fp.to_json(indent=2), encoding="utf-8")
restored = Fingerprint.from_json(Path("profile.json").read_text(encoding="utf-8"))
options = restored.context_options(browser_version="156.0.8078.4")   # retargeted to the real engine
```

## The `Fingerprint` object

| Member | Description |
| --- | --- |
| `schema_version`, `created_at` | Serialization metadata (UTC timestamp). |
| `device_type`, `os`, `locale`, `timezone_id`, `viewport` | Typed context metadata. |
| `raw_data` | Injectable payload: `navigator`, `screen`, `headers`, `videoCard`, codecs, battery. |
| `navigator`, `screen`, `headers`, `video_card` | Read-only views of the payload sections (plain dicts). |
| `user_agent`, `screen_size`, `device_scale_factor`, `gpu_renderer`, `hardware_concurrency`, `device_memory` | Typed getters. |
| `screen_info`, `hardware_info` | `ScreenInfo` / `HardwareInfo` dataclasses. |
| `context_options(version)`, `init_script(version)` | Playwright context kwargs / JS init script. |
| `apply(context, version)`, `apply_sync(context, version)` | Inject through `add_init_script`. |

## Realism rules

Desktop: no software GPUs, no foreign browsers in the UA, platform matches OS, allowed DPR set per OS, screen at
least 1280x720, `deviceMemory <= 8`, at most 8 threads for old Intel iGPUs. Mobile: Android/iOS only, valid mobile
DPR, `maxTouchPoints >= 5`, `Mobile` plus `Android`/`iPhone` tokens, `sec-ch-ua-mobile: ?1`. Inspect any payload with
`realism_issues(fp, os, device_type)`.

## Migrating from `browserforge`

`browserforge-stealth` replaces `browserforge`; it is not a drop-in alias. The import name is `browserforge_stealth`,
and the old API (`browserforge.*`) no longer exists.

1. Swap the package. The two use different import names, so they do not conflict, but you should remove the old one:

   ```bash
   pip uninstall browserforge
   pip install browserforge-stealth
   ```

2. Update imports and calls:

   | `browserforge` | `browserforge-stealth` |
   | --- | --- |
   | `from browserforge.fingerprints import FingerprintGenerator` | `from browserforge_stealth import FingerprintGenerator` |
   | `from browserforge.fingerprints import Screen` | `from browserforge_stealth import ScreenConstraints` |
   | `from browserforge.headers import HeaderGenerator, Browser` | `from browserforge_stealth.headers import HeaderGenerator, Browser` (API unchanged) |
   | `FingerprintGenerator(browser="chrome", os="windows", device="mobile", locale="uk-UA")` | `FingerprintGenerator(os="windows", device_type="mobile", locale="uk-UA", timezone_id=...)` |
   | `FingerprintGenerator(screen=Screen(min_width=1280))` | `FingerprintGenerator(screen=ScreenConstraints(min_width=1280))` |
   | `fp.navigator.userAgent`, `fp.screen.width`, `fp.videoCard.renderer`, `fp.headers` | `fp.navigator["userAgent"]` (or `fp.user_agent`), `fp.screen["width"]`, `fp.video_card["renderer"]`, `fp.headers` |
   | `fp.dumps()` | `fp.to_json()` (full profile with metadata) or `json.dumps(fp.raw_data)` (payload only) |
   | `InjectFunction(fp)` | `fp.init_script(browser_version)` |
   | `await AsyncNewContext(browser, fp)` | `context = await browser.new_context(**fp.context_options(browser.version))`, then `await fp.apply(context, browser.version)` |
   | `NewContext(browser, fp)` (sync) | `context = browser.new_context(**fp.context_options(browser.version))`, then `fp.apply_sync(context, browser.version)` |
   | `browserforge.injectors.pyppeteer`, `browserforge.injectors.undetected_playwright` | Removed. Use Patchright or Playwright. |
   | `python -m browserforge update/remove`, `browserforge.download` | Removed (model files are bundled). |

3. Review the behavior changes:

   * Generation is **realistic by default** and **Chrome-only** (rejection sampling, sanitized payload).
     Pass `browser=("firefox",)` etc. to the generator only if you accept unrealistic results for it.
   * The OS defaults to the host OS (Android for `device_type="mobile"`) instead of a random one.
   * `mock_webrtc` and `slim` options are gone; the payload always has both set to `False`.
   * Contexts use `color_scheme="light"` (the old injectors forced dark mode) and carry the timezone, `is_mobile`
     and `has_touch` of the profile.
   * `pluginsData`, `multimediaDevices` and `fonts` are dropped from the payload; `navigator.webdriver` is `False`.
   * Generation errors raise `GenerationError` (subclass of `FingerprintError`) instead of `ValueError`.

4. Convert profiles you stored with `fp.dumps()`. The old JSON has the same payload layout, so wrap it:

   ```python
   import json
   from pathlib import Path

   from browserforge_stealth import Fingerprint, derive_viewport, realism_issues

   raw = json.loads(Path("old_profile.json").read_text(encoding="utf-8"))
   os_name, device = "windows", "desktop"          # what the profile was generated for
   fp = Fingerprint(
       os=os_name,
       device_type=device,
       locale=raw["navigator"]["language"],
       viewport=derive_viewport(raw, os_name, device),
       raw_data=raw,
   )
   if realism_issues(fp, os_name, device):
       ...  # old profile has artifacts (Brave traces, 16 GB RAM, software GPU): regenerate it instead
   Path("new_profile.json").write_text(fp.to_json(indent=2), encoding="utf-8")
   ```

   Profiles that fail `realism_issues` carry the artifacts this fork exists to remove, so regenerate them if your
   account history allows changing the fingerprint.

## Headers only

```python
from browserforge_stealth.headers import HeaderGenerator

headers = HeaderGenerator().generate(browser="chrome", os="windows", device="desktop", locale="en-US")
```

## Low-level sampling

`browserforge_stealth.sampler.FingerprintSampler` draws raw samples from the Bayesian network with optional
`ScreenConstraints`, without any realism filtering. Use `FingerprintGenerator` unless you need raw data.

## CLI

```bash
browserforge-stealth generate --os windows --locale uk-UA
browserforge-stealth generate --device mobile --os android --json
browserforge-stealth generate --os macos --output profile.json
browserforge-stealth inspect profile.json
```

## Development

```bash
pip install -e ".[dev]"
pytest && ruff check . && mypy
```

## Credits and license

Based on [daijro/browserforge](https://github.com/daijro/browserforge) and Apify's
[fingerprint-suite](https://github.com/apify/fingerprint-suite) (bundled `utils.js`), both Apache-2.0; their notices
are kept in [NOTICE.md](NOTICE.md). BrowserForge-Stealth itself is licensed under the
**GNU General Public License v3.0**, see [LICENSE](LICENSE).
