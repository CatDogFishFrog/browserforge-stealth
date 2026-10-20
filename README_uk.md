# BrowserForge-Stealth 🎭

**Реалістичні, узгоджені відбитки браузера для Patchright, Playwright та антидетект-автоматизації.**

BrowserForge-Stealth — модернізований форк [`browserforge`](https://github.com/daijro/browserforge). Він зберігає
байєсівські мережі Apify для відбитків і заголовків, але додає перевірку реалістичності, GREASE-бренди Chromium,
мобільні профілі та підгонку під версію реального браузера. Це самостійний пакет з єдиною назвою для імпорту:
`browserforge_stealth`. Старого API `browserforge` тут **немає**.

## Навіщо

Сирі байєсівські зразки регулярно містять комбінації, яких не буває на реальних пристроях:

* сліди Brave у `sec-ch-ua`, коли User-Agent заявляє Google Chrome;
* `navigator.deviceMemory` 16/32 ГБ (Chrome обмежує значення 8);
* програмні GPU (`SwiftShader`, `llvmpipe`, `Microsoft Basic Render Driver`);
* дробовий `devicePixelRatio`, екрани менші за 1280x720 на десктопі, розбіжність ОС і платформи;
* зафіксована версія Chrome, що не збігається з реальним бінарником браузера.

BrowserForge-Stealth генерує зразок, санітизує його, відхиляє нереалістичні та підганяє результат під браузер, який
справді запущено.

## Можливості

* **Типізований контракт:** `Fingerprint`, `OperatingSystem`, `DeviceType`, `ScreenInfo`, `HardwareInfo`, `Viewport`.
* **Rejection sampling:** `FingerprintGenerator(realistic=True)` повторює генерацію, доки всі правила не пройдено.
* **GREASE-бренди Chromium** та чисті Client Hints (`sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`).
* **Десктоп і мобільні** (Windows, macOS, Linux, Android, iOS) з відповідними touch-точками та токенами UA.
* **Retargeting:** UA, `appVersion`, `userAgentData` і заголовки підлаштовуються під версію рушія, залізо не змінюється.
* **Збереження:** `to_dict()` / `from_dict()` / `to_json()` / `from_json()` з версією схеми.
* **Інжекція через duck-typing:** працює з будь-яким контекстом, що має `add_init_script`.
* **CLI:** `browserforge-stealth generate` / `inspect`.

## Встановлення

```bash
pip install browserforge-stealth
pip install "browserforge-stealth[orjson]"   # опційно: швидше завантаження JSON
```

Потрібен Python 3.11+. Patchright / Playwright **не є** залежностями — встановлюйте той, яким користуєтесь.

## Швидкий старт

```python
from browserforge_stealth import FingerprintGenerator

generator = FingerprintGenerator(os="windows", locale="uk-UA", timezone_id="Europe/Kyiv")
fp = generator.generate()

print(fp.user_agent)
print(fp.screen_size, fp.device_scale_factor, fp.viewport)
print(fp.gpu_renderer, fp.device_memory, fp.hardware_concurrency)
```

Коротка форма:

```python
from browserforge_stealth import generate_fingerprint

fp = generate_fingerprint(os="macos", locale="en-US")
```

### Async Playwright / Patchright

```python
import asyncio
from patchright.async_api import async_playwright   # або: from playwright.async_api import async_playwright
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

### Мобільні відбитки

```python
fp = generate_fingerprint(device_type="mobile", os="android", locale="uk-UA")
print(fp.user_agent)                  # містить "Mobile" та "Android"
print(fp.navigator["maxTouchPoints"])  # >= 5
```

### Збереження профілю акаунта

```python
from pathlib import Path

from browserforge_stealth import Fingerprint

Path("profile.json").write_text(fp.to_json(indent=2), encoding="utf-8")
restored = Fingerprint.from_json(Path("profile.json").read_text(encoding="utf-8"))
options = restored.context_options(browser_version="156.0.8078.4")   # підгонка під реальний рушій
```

## Об'єкт `Fingerprint`

| Член | Опис |
| --- | --- |
| `schema_version`, `created_at` | Метадані серіалізації (час у UTC). |
| `device_type`, `os`, `locale`, `timezone_id`, `viewport` | Типізовані метадані контексту. |
| `raw_data` | Корисне навантаження для інжекції: `navigator`, `screen`, `headers`, `videoCard`, кодеки, батарея. |
| `navigator`, `screen`, `headers`, `video_card` | Секції навантаження (звичайні словники, лише читання). |
| `user_agent`, `screen_size`, `device_scale_factor`, `gpu_renderer`, `hardware_concurrency`, `device_memory` | Типізовані геттери. |
| `screen_info`, `hardware_info` | Датакласи `ScreenInfo` / `HardwareInfo`. |
| `context_options(version)`, `init_script(version)` | Параметри контексту Playwright / JS init-скрипт. |
| `apply(context, version)`, `apply_sync(context, version)` | Інжекція через `add_init_script`. |

## Правила реалістичності

Десктоп: без програмних GPU, без сторонніх браузерів в UA, платформа відповідає ОС, DPR із дозволеного набору для ОС,
екран не менший за 1280x720, `deviceMemory <= 8`, не більше 8 потоків для старих Intel iGPU. Мобільні: лише
Android/iOS, коректний мобільний DPR, `maxTouchPoints >= 5`, токени `Mobile` та `Android`/`iPhone`,
`sec-ch-ua-mobile: ?1`. Перевірити будь-яке навантаження: `realism_issues(fp, os, device_type)`.

## Лише заголовки

```python
from browserforge_stealth.headers import HeaderGenerator

headers = HeaderGenerator().generate(browser="chrome", os="windows", device="desktop", locale="en-US")
```

## Низькорівнева вибірка

`browserforge_stealth.sampler.FingerprintSampler` бере сирі зразки з байєсівської мережі (з опційними
`ScreenConstraints`) без фільтрації реалістичності. Якщо сирі дані не потрібні — користуйтесь `FingerprintGenerator`.

## CLI

```bash
browserforge-stealth generate --os windows --locale uk-UA
browserforge-stealth generate --device mobile --os android --json
browserforge-stealth generate --os macos --output profile.json
browserforge-stealth inspect profile.json
```

## Розробка

```bash
pip install -e ".[dev]"
pytest && ruff check . && mypy
```

## Подяки та ліцензія

Основа — [daijro/browserforge](https://github.com/daijro/browserforge) та
[fingerprint-suite](https://github.com/apify/fingerprint-suite) від Apify (вбудований `utils.js`, Apache-2.0).
Ліцензія Apache-2.0, див. [LICENSE](LICENSE).
