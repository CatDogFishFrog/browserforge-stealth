# BrowserForge-Stealth

**Realistic, self-consistent browser fingerprints and headers for Patchright, Playwright and anti-detect automation.**

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
* **Header-only mode:** `HeaderGenerator` can be used independently for any HTTP client.
* **CLI:** `browserforge-stealth generate` / `inspect`.

## Installation

```bash
pip install git+https://github.com/CatDogFishFrog/browserforge-stealth.git
pip install "git+https://github.com/CatDogFishFrog/browserforge-stealth.git#egg=browserforge-stealth[orjson]"  # optional faster JSON
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
from pathlib import Path
from browserforge_stealth import Fingerprint

Path("profile.json").write_text(fp.to_json(indent=2), encoding="utf-8")
restored = Fingerprint.from_json(Path("profile.json").read_text(encoding="utf-8"))
options = restored.context_options(browser_version="156.0.8078.4")   # retargeted to the real engine
```

### Screen constraints

Constrain the minimum/maximum screen width and height:

```python
from browserforge_stealth import FingerprintGenerator, ScreenConstraints

screen = ScreenConstraints(min_width=1600, min_height=900)
fp = FingerprintGenerator(os="windows", screen=screen).generate()
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
| `to_dict()`, `from_dict()`, `to_json()`, `from_json()` | Serialization / deserialization. |

## Realism rules

Desktop: no software GPUs, no foreign browsers in the UA, platform matches OS, allowed DPR set per OS, screen at
least 1280x720, `deviceMemory <= 8`, at most 8 threads for old Intel iGPUs. Mobile: Android/iOS only, valid mobile
DPR, `maxTouchPoints >= 5`, `Mobile` plus `Android`/`iPhone` tokens, `sec-ch-ua-mobile: ?1`. Inspect any payload with
`realism_issues(fp, os, device_type)`.

## Migrating from `browserforge`

`browserforge-stealth` replaces `browserforge`; it is not a drop-in alias. The import name is `browserforge_stealth`,
and the old API (`browserforge.*`) no longer exists.

1. Swap the package:

   ```bash
   pip uninstall browserforge
   pip install git+https://github.com/CatDogFishFrog/browserforge-stealth.git
   ```

2. Update imports and calls:

   | `browserforge` | `browserforge-stealth` |
   | --- | --- |
   | `from browserforge.fingerprints import FingerprintGenerator` | `from browserforge_stealth import FingerprintGenerator` |
   | `from browserforge.fingerprints import Screen` | `from browserforge_stealth import ScreenConstraints` |
   | `from browserforge.headers import HeaderGenerator, Browser` | `from browserforge_stealth import HeaderGenerator, Browser` (API unchanged) |
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

## Generating headers only

`HeaderGenerator` can be used on its own for any HTTP client (requests, httpx, curl_cffi, aiohttp, etc.):

```python
from browserforge_stealth import HeaderGenerator

headers = HeaderGenerator().generate()
# {
#   'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
#   'sec-ch-ua-mobile': '?0',
#   'sec-ch-ua-platform': '"macOS"',
#   'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
#   'Accept': 'text/html,...',
#   'Accept-Language': 'en-US;q=1.0',
#   ...
# }
```

### Using with requests

```python
import requests
from browserforge_stealth import HeaderGenerator

session = requests.Session()
session.headers = HeaderGenerator().generate()
```

### Single constraint

```python
headers = HeaderGenerator(
    browser="chrome",
    os="windows",
    device="desktop",
    locale="en-US",
    http_version=2,
).generate()
```

### Multiple constraints

Set multiple constraints to select from. Selection frequency matches real-world browser distribution:

```python
headers = HeaderGenerator(
    browser=("chrome", "firefox", "safari", "edge"),
    os=("windows", "macos", "linux"),
    device=("desktop", "mobile"),
    locale=("en-US", "en", "uk-UA"),
    http_version=2,
).generate()
```

### Browser specification

Use a `Browser` dataclass to pin exact version ranges. You can also set a per-browser HTTP version:

```python
from browserforge_stealth import Browser, HeaderGenerator

browsers = [
    Browser(name="chrome", min_version=130, max_version=147),
    Browser(name="firefox", min_version=130),
    Browser(name="edge", max_version=140, http_version=1),
]
headers = HeaderGenerator(browser=browsers).generate()
```

### Generate headers for an existing User-Agent

Generate a matching set of headers for a specific User-Agent string:

```python
headers = HeaderGenerator().generate(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
)
```

Pass a tuple to randomly select from multiple User-Agents by their frequency:

```python
headers = HeaderGenerator().generate(
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    )
)
```

### HTTP version

`HeaderGenerator` supports HTTP/1 and HTTP/2. The `http_version` parameter controls which Bayesian
network is used internally, affecting header set and ordering. In HTTP/1 mode, a `Connection: keep-alive`
header is added. Headers are Title-Cased in both modes (e.g. `User-Agent`, `Accept-Language`); only
`sec-ch-ua*` fields remain lowercase, as they are always sent that way by real Chrome.

```python
# HTTP/1 — includes Connection: keep-alive
headers = HeaderGenerator(http_version=1).generate()

# HTTP/2 — no Connection header (forbidden in HTTP/2)
headers = HeaderGenerator(http_version=2).generate()  # default
```

### Overriding request-dependent headers

Some headers differ per request (e.g. `Accept` for an API call vs a page load). Pass them via
`request_dependent_headers` — they will override the generated value for that request:

```python
headers = HeaderGenerator().generate(
    browser="chrome",
    http_version=1,
    request_dependent_headers={"Accept": "application/json"},
)
# headers['Accept'] == 'application/json'
```

### HeaderGenerator parameters

Both `HeaderGenerator.__init__` and `HeaderGenerator.generate` accept the same parameters.
Values passed to `.generate()` override the constructor defaults for that call only.

| Parameter | Type | Description |
| --- | --- | --- |
| `browser` | `str \| Browser \| list` | Browser name(s) or `Browser` spec(s). Supported: `chrome`, `firefox`, `safari`, `edge`. Default: all four. |
| `os` | `str \| list` | Operating system(s): `windows`, `macos`, `linux`, `android`, `ios`. Default: all five. |
| `device` | `str \| list` | Device type(s): `desktop`, `mobile`. Default: both. |
| `locale` | `str \| list` | Language locale(s) for `Accept-Language`, e.g. `en-US`, `uk-UA`. Up to 10. Default: `en-US`. |
| `http_version` | `1 \| 2` | HTTP version (affects header set and ordering). Default: `2`. |
| `strict` | `bool` | Raise `ValueError` instead of relaxing impossible constraints. Default: `False`. |
| `user_agent` | `str \| list` | (`generate()` only) Pin to a specific User-Agent string or select from a tuple. |
| `request_dependent_headers` | `dict` | (`generate()` only) Override specific headers for this request. |

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

You can also run it as a module:

```bash
python -m browserforge_stealth generate --os windows
```

## Development

```bash
git clone https://github.com/CatDogFishFrog/browserforge-stealth.git
cd browserforge-stealth
pip install -e ".[dev]"
pytest && ruff check . && mypy
```

## Credits and license

Based on [daijro/browserforge](https://github.com/daijro/browserforge) and Apify's
[fingerprint-suite](https://github.com/apify/fingerprint-suite) (bundled `utils.js`), both Apache-2.0; their notices
are kept in [NOTICE.md](NOTICE.md). BrowserForge-Stealth itself is licensed under the
**GNU General Public License v3.0**, see [LICENSE](LICENSE).
