# BrowserForge-Stealth 🎭

**Реалістичні, узгоджені відбитки та заголовки браузера для Patchright, Playwright та антидетект-автоматизації.**

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
* **Лише заголовки:** `HeaderGenerator` можна використовувати окремо для будь-якого HTTP-клієнта.
* **CLI:** `browserforge-stealth generate` / `inspect`.

## Встановлення

```bash
pip install git+https://github.com/CatDogFishFrog/browserforge-stealth.git
pip install "git+https://github.com/CatDogFishFrog/browserforge-stealth.git#egg=browserforge-stealth[orjson]"  # опційно: швидше завантаження JSON
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

### Обмеження розмірів екрана

Можна задати мінімальний та максимальний розмір екрана:

```python
from browserforge_stealth import FingerprintGenerator, ScreenConstraints

screen = ScreenConstraints(min_width=1600, min_height=900)
fp = FingerprintGenerator(os="windows", screen=screen).generate()
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
| `to_dict()`, `from_dict()`, `to_json()`, `from_json()` | Серіалізація / десеріалізація. |

## Правила реалістичності

Десктоп: без програмних GPU, без сторонніх браузерів в UA, платформа відповідає ОС, DPR із дозволеного набору для ОС,
екран не менший за 1280x720, `deviceMemory <= 8`, не більше 8 потоків для старих Intel iGPU. Мобільні: лише
Android/iOS, коректний мобільний DPR, `maxTouchPoints >= 5`, токени `Mobile` та `Android`/`iPhone`,
`sec-ch-ua-mobile: ?1`. Перевірити будь-яке навантаження: `realism_issues(fp, os, device_type)`.

## Міграція зі старого `browserforge`

`browserforge-stealth` замінює `browserforge`, але не є його псевдонімом. Назва для імпорту — `browserforge_stealth`,
старого API (`browserforge.*`) більше не існує.

1. Замініть пакет:

   ```bash
   pip uninstall browserforge
   pip install git+https://github.com/CatDogFishFrog/browserforge-stealth.git
   ```

2. Оновіть імпорти та виклики:

   | `browserforge` | `browserforge-stealth` |
   | --- | --- |
   | `from browserforge.fingerprints import FingerprintGenerator` | `from browserforge_stealth import FingerprintGenerator` |
   | `from browserforge.fingerprints import Screen` | `from browserforge_stealth import ScreenConstraints` |
   | `from browserforge.headers import HeaderGenerator, Browser` | `from browserforge_stealth import HeaderGenerator, Browser` (API без змін) |
   | `FingerprintGenerator(browser="chrome", os="windows", device="mobile", locale="uk-UA")` | `FingerprintGenerator(os="windows", device_type="mobile", locale="uk-UA", timezone_id=...)` |
   | `FingerprintGenerator(screen=Screen(min_width=1280))` | `FingerprintGenerator(screen=ScreenConstraints(min_width=1280))` |
   | `fp.navigator.userAgent`, `fp.screen.width`, `fp.videoCard.renderer`, `fp.headers` | `fp.navigator["userAgent"]` (або `fp.user_agent`), `fp.screen["width"]`, `fp.video_card["renderer"]`, `fp.headers` |
   | `fp.dumps()` | `fp.to_json()` (повний профіль із метаданими) або `json.dumps(fp.raw_data)` (лише навантаження) |
   | `InjectFunction(fp)` | `fp.init_script(browser_version)` |
   | `await AsyncNewContext(browser, fp)` | `context = await browser.new_context(**fp.context_options(browser.version))`, потім `await fp.apply(context, browser.version)` |
   | `NewContext(browser, fp)` (sync) | `context = browser.new_context(**fp.context_options(browser.version))`, потім `fp.apply_sync(context, browser.version)` |
   | `browserforge.injectors.pyppeteer`, `browserforge.injectors.undetected_playwright` | Видалено. Використовуйте Patchright або Playwright. |
   | `python -m browserforge update/remove`, `browserforge.download` | Видалено (файли моделей вбудовані). |

3. Врахуйте зміни поведінки:

   * Генерація **реалістична за замовчуванням** і **лише Chrome** (rejection sampling, санітизоване навантаження).
     Передавайте `browser=("firefox",)` тощо лише якщо готові до нереалістичних результатів для нього.
   * ОС за замовчуванням — ОС хоста (Android для `device_type="mobile"`), а не випадкова.
   * Опцій `mock_webrtc` та `slim` більше немає; у навантаженні обидві завжди `False`.
   * Контексти використовують `color_scheme="light"` (старі інжектори примусово ставили dark) і містять часовий пояс,
     `is_mobile` та `has_touch` профілю.
   * `pluginsData`, `multimediaDevices` та `fonts` прибрано з навантаження; `navigator.webdriver` — `False`.
   * Помилки генерації — `GenerationError` (підклас `FingerprintError`) замість `ValueError`.

4. Перетворіть профілі, збережені через `fp.dumps()`. Старий JSON має ту саму структуру навантаження, тож його
   достатньо обгорнути:

   ```python
   import json
   from pathlib import Path

   from browserforge_stealth import Fingerprint, derive_viewport, realism_issues

   raw = json.loads(Path("old_profile.json").read_text(encoding="utf-8"))
   os_name, device = "windows", "desktop"          # для чого профіль генерували
   fp = Fingerprint(
       os=os_name,
       device_type=device,
       locale=raw["navigator"]["language"],
       viewport=derive_viewport(raw, os_name, device),
       raw_data=raw,
   )
   if realism_issues(fp, os_name, device):
       ...  # у старому профілі є артефакти (сліди Brave, 16 ГБ RAM, програмний GPU): краще згенерувати новий
   Path("new_profile.json").write_text(fp.to_json(indent=2), encoding="utf-8")
   ```

   Профілі, що не проходять `realism_issues`, містять саме ті артефакти, які цей форк прибирає, тож перегенеруйте їх,
   якщо історія акаунта дозволяє змінити відбиток.

## Генерація заголовків

`HeaderGenerator` можна використовувати окремо — для requests, httpx, curl_cffi, aiohttp тощо:

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

### Використання з requests

```python
import requests
from browserforge_stealth import HeaderGenerator

session = requests.Session()
session.headers = HeaderGenerator().generate()
```

### Одне обмеження

```python
headers = HeaderGenerator(
    browser="chrome",
    os="windows",
    device="desktop",
    locale="en-US",
    http_version=2,
).generate()
```

### Декілька обмежень

Можна передати кортеж або список — генератор вибиратиме між варіантами відповідно до реального розподілу браузерів:

```python
headers = HeaderGenerator(
    browser=("chrome", "firefox", "safari", "edge"),
    os=("windows", "macos", "linux"),
    device=("desktop", "mobile"),
    locale=("en-US", "en", "uk-UA"),
    http_version=2,
).generate()
```

### Специфікація браузера

Датаклас `Browser` дозволяє точно обмежити діапазон версій. Також можна встановити HTTP-версію на рівні браузера:

```python
from browserforge_stealth import Browser, HeaderGenerator

browsers = [
    Browser(name="chrome", min_version=130, max_version=147),
    Browser(name="firefox", min_version=130),
    Browser(name="edge", max_version=140, http_version=1),
]
headers = HeaderGenerator(browser=browsers).generate()
```

### Генерація заголовків під конкретний User-Agent

```python
headers = HeaderGenerator().generate(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
)
```

Або вибір з декількох UA за частотою:

```python
headers = HeaderGenerator().generate(
    user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    )
)
```

### HTTP-версія

`HeaderGenerator` підтримує HTTP/1 та HTTP/2. Параметр `http_version` визначає, яка байєсівська мережа
використовується — а отже, набір і порядок заголовків. У режимі HTTP/1 додається `Connection: keep-alive`.
Заголовки у Title-Case в обох режимах (`User-Agent`, `Accept-Language`); лише `sec-ch-ua*` залишаються
в нижньому регістрі — так їх і надсилає реальний Chrome.

```python
# HTTP/1 — додається Connection: keep-alive
headers = HeaderGenerator(http_version=1).generate()

# HTTP/2 — Connection заборонений протоколом, не включається
headers = HeaderGenerator(http_version=2).generate()  # за замовчуванням
```

### Перевизначення заголовків запиту

Деякі заголовки відрізняються залежно від запиту (наприклад, `Accept` для API vs сторінки). Передайте їх через
`request_dependent_headers` — вони замінять згенероване значення для цього запиту:

```python
headers = HeaderGenerator().generate(
    browser="chrome",
    http_version=1,
    request_dependent_headers={"Accept": "application/json"},
)
# headers['Accept'] == 'application/json'
```

### Параметри HeaderGenerator

Обидва методи — `HeaderGenerator.__init__` та `HeaderGenerator.generate` — приймають ті самі параметри.
Значення, передані в `.generate()`, перекривають дефолти конструктора лише для цього виклику.

| Параметр | Тип | Опис |
| --- | --- | --- |
| `browser` | `str \| Browser \| list` | Браузер(и) або специфікація `Browser`. Підтримуються: `chrome`, `firefox`, `safari`, `edge`. За замовчуванням — всі чотири. |
| `os` | `str \| list` | Операційна система: `windows`, `macos`, `linux`, `android`, `ios`. За замовчуванням — всі п'ять. |
| `device` | `str \| list` | Тип пристрою: `desktop`, `mobile`. За замовчуванням — обидва. |
| `locale` | `str \| list` | Локаль для `Accept-Language`, наприклад `uk-UA`, `en-US`. До 10 значень. За замовчуванням: `en-US`. |
| `http_version` | `1 \| 2` | Версія HTTP (впливає на набір і порядок заголовків). За замовчуванням: `2`. |
| `strict` | `bool` | Кидати `ValueError` замість пом'якшення неможливих обмежень. За замовчуванням: `False`. |
| `user_agent` | `str \| list` | (лише `.generate()`) Прив'язати до конкретного User-Agent або кортежу UA. |
| `request_dependent_headers` | `dict` | (лише `.generate()`) Перевизначити конкретні заголовки для цього запиту. |

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

Або як модуль:

```bash
python -m browserforge_stealth generate --os windows
```

## Розробка

```bash
git clone https://github.com/CatDogFishFrog/browserforge-stealth.git
cd browserforge-stealth
pip install -e ".[dev]"
pytest && ruff check . && mypy
```

## Подяки та ліцензія

Основа — [daijro/browserforge](https://github.com/daijro/browserforge) та
[fingerprint-suite](https://github.com/apify/fingerprint-suite) від Apify (вбудований `utils.js`), обидва під
Apache-2.0; їхні повідомлення збережено в [NOTICE.md](NOTICE.md). Сам BrowserForge-Stealth ліцензовано під
**GNU General Public License v3.0**, див. [LICENSE](LICENSE).
