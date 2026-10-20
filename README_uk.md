# BrowserForge-Stealth 🎭

**Реалістичний, інтелектуальний генератор відбитків браузера (fingerprint) та інструментарій для антидетект-автоматизації на Python.**

Модернізований форк бібліотеки [`browserforge`](https://github.com/daijro/browserforge), створений спеціально для автоматизації без виявлення ботів, веб-скрапінгу та обходу систем перевірки (Cloudflare Turnstile, DataDome, Akamai, Kasada тощо) у зв'язці з **Patchright**, **Playwright** та іншими Chromium-сумісними бібліотеками.

---

## Чому саме BrowserForge-Stealth?

Стандартні генератори відбитків часто створюють синтетичні підписи, які миттєво викликають підозру сучасних систем захисту. Чистий `browserforge` та наївні байєсівські моделі регулярно генерують комбінації, які ніколи не трапляються у звичайних користувачів:

1. **Витоки слідів Brave у Chrome:** до 15% зразків browserforge містили `"Brave"` у заголовках `sec-ch-ua` або описах плагінів, тоді як User-Agent заявляв звичайний Google Chrome.
2. **Неможливі значення апаратних ресурсів:** `navigator.deviceMemory` зі значеннями 16 ГБ або 32 ГБ, хоча Google Chrome апаратно обмежує `deviceMemory` максимумом у 8 ГБ у всіх релізах.
3. **Програмні/віртуальні відеокарти:** рендерери на зразок `SwiftShader`, `llvmpipe`, `Microsoft Basic Render Driver` або `Mesa`, які видають хмарний сервер чи віртуальну машину.
4. **Спотворені параметри дисплея:** дробові `devicePixelRatio` (наприклад, `1.145829...`), доступна область екрана більша за сам екран, або роздільність менша за 1280×720 на десктопі.
5. **Розбіжність версій рушія (Time Drift):** відбиток зафіксовано на застарілій версії Chrome (наприклад, 124), тоді як реальний браузер працює на сучасній версії 140+ чи 156+, що створює явні протиріччя між DOM API та заголовками.
6. **Брудні мовні заголовки:** відсутність ваги у `Accept-Language` та наявність пробілів у `navigator.languages` (наприклад, `' uk-UA'`).

**BrowserForge-Stealth усуває кожну з цих проблем.** Він поєднує статистичну байєсівську мережу з багаторівневою фільтрацією (rejection sampling), детерміністичною санітизацією, алгоритмом GREASE-брендів Chromium та динамічною підгонкою версії рушія.

---

## Ключові можливості

* **100% зворотна сумісність:** повна заміна оригінального `browserforge`. Код `from browserforge.fingerprints import FingerprintGenerator, Fingerprint` працює без змін, але автоматично отримує реалістичні відбитки.
* **Сучасний типізований API:** чистий інтерфейс у модулі `browserforge_stealth` (`generate_fingerprint`, `FingerprintGenerator`, `context_options`, `apply_to_context`).
* **Багаторівнева фільтрація реалістичності:** автоматичне відкидання програмних GPU, неприпустимих значень пам'яті, нереалістичної кількості ядер для старих Intel iGPU та спотворених екранів.
* **Алгоритм Chromium GREASE:** формує правдоподібні перестановки GREASE-брендів (`"Not A(Brand"`, `"Chromium"`, `"Google Chrome"`) та структуровані Client Hints (`sec-ch-ua`, `sec-ch-ua-platform`, `sec-ch-ua-mobile`).
* **Динамічний Retargeting версії:** автоматично узгоджує User-Agent і заголовки із версією запущеного бінарника браузера без зміни сталого «заліза» (GPU, екран, пам'ять).
* **Емуляція десктопних і мобільних пристроїв:** підтримка профілів для Windows, macOS, Linux, Android та iOS із відповідними сенсорними точками, розмірами вікон та заголовками.
* **Готові адаптери для браузерів:** зручні помічники для Patchright і Playwright (`context_options`, `build_init_script`, `apply_to_context`, `apply_to_context_sync`).
* **Постійність сесії:** повне збереження та завантаження через JSON чи словник (`to_dict`, `from_dict`, `to_json`, `from_json`) із версіонуванням схеми.
* **Вбудований CLI:** консольна утиліта для генерації, інспекції та збереження профілів.

---

## Встановлення

```bash
pip install browserforge-stealth
```

Опціональне прискорення JSON через `orjson`:

```bash
pip install browserforge-stealth[orjson]
```

---

## Швидкий старт

### 1. Генерація реалістичного відбитка

```python
from browserforge_stealth import FingerprintGenerator, OperatingSystem, DeviceType

# Ініціалізація генератора з потрібними обмеженнями
generator = FingerprintGenerator(
    os=OperatingSystem.WINDOWS,
    locale="uk-UA",
    timezone_id="Europe/Kyiv",
)

# Генерація перевіреного реалістичного відбитка
fp = generator.generate()

print("User-Agent:", fp.user_agent)
print("Screen:", fp.screen_size, "DPR:", fp.device_scale_factor)
print("Viewport:", fp.viewport)
print("GPU:", fp.gpu_renderer)
print("RAM:", fp.device_memory, "GB | Cores:", fp.hardware_concurrency)
```

Або через функцію швидкого доступу:

```python
from browserforge_stealth import generate_fingerprint

fp = generate_fingerprint(os="windows", locale="uk-UA")
```

---

### 2. Використання з Playwright або Patchright (Async)

```python
import asyncio
from patchright.async_api import async_playwright
# або: from playwright.async_api import async_playwright
from browserforge_stealth import generate_fingerprint

async def main():
    # 1. Створюємо або завантажуємо відбиток
    fp = generate_fingerprint(os="windows", locale="en-US", timezone_id="Europe/Kyiv")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # 2. Отримуємо параметри контексту під реальну версію браузера
        browser_version = browser.version  # наприклад, "156.0.8078.4"
        options = fp.context_options(browser_version=browser_version)
        
        # 3. Створюємо контекст і впроваджуємо скрипт підміни
        context = await browser.new_context(**options)
        await fp.apply(context, browser_version=browser_version)

        page = await context.new_page()
        await page.goto("https://bot.sannysoft.com")
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 3. Використання з Playwright або Patchright (Sync)

```python
from patchright.sync_api import sync_playwright
from browserforge_stealth import generate_fingerprint, apply_to_context_sync

fp = generate_fingerprint(os="macos", locale="en-US")

with sync_playwright() as p:
    browser = p.chromium.launch()
    options = fp.context_options(browser_version=browser.version)
    context = browser.new_context(**options)
    apply_to_context_sync(context, fp, browser_version=browser.version)
    
    page = context.new_page()
    page.goto("https://nowsecure.nl")
    browser.close()
```

---

### 4. Зворотна сумісність із існуючим кодом `browserforge`

Якщо ваш проєкт уже використовує `browserforge`, переписувати імпорти не потрібно:

```python
# Старий код продовжує працювати на 100%, але тепер отримує реалістичні відбитки!
from browserforge.fingerprints import FingerprintGenerator, Screen
from browserforge.injectors.utils import InjectFunction
from browserforge.headers import HeaderGenerator

generator = FingerprintGenerator(browser="chrome", os="windows")
fingerprint = generator.generate()

# Метод .dumps() повністю підтримується:
js_script = InjectFunction(fingerprint)
```

---

### 5. Мобільні відбитки (Android та iOS)

```python
from browserforge_stealth import generate_fingerprint, DeviceType, OperatingSystem

mobile_fp = generate_fingerprint(
    device_type=DeviceType.MOBILE,
    os=OperatingSystem.ANDROID,
    locale="uk-UA",
)

print(mobile_fp.user_agent)       # Містить 'Mobile' та 'Android'
print(mobile_fp.viewport)         # Мобільний viewport (наприклад, 390x844)
print(mobile_fp.raw_data["navigator"]["maxTouchPoints"])  # >= 5
```

---

### 6. Збереження та відновлення профілів акаунтів

Щоб сайт бачив ваш акаунт завжди з одного й того ж комп'ютера:

```python
import json
from browserforge_stealth import generate_fingerprint, Fingerprint

# --- День 1: Створення та збереження ---
fp = generate_fingerprint(os="windows", locale="uk-UA")
with open("account_profile.json", "w", encoding="utf-8") as f:
    f.write(fp.to_json(indent=2))

# --- День 2: Відновлення профілю ---
with open("account_profile.json", "r", encoding="utf-8") as f:
    saved_fp = Fingerprint.from_json(f.read())

# Динамічний retargeting автоматично узгодить UA з поточною версією рушія!
context_opts = saved_fp.context_options(browser_version="156.0.8078.4")
```

---

## Консольна утиліта (CLI)

### Генерація відбитка
```bash
# Коротке зведення у термінал
browserforge-stealth generate --os windows --locale uk-UA

# Вивід у форматі JSON
browserforge-stealth generate --os macos --json

# Збереження у файл
browserforge-stealth generate --os windows --output profile.json
```

### Інспекція збереженого файлу відбитка
```bash
browserforge-stealth inspect profile.json
```

---

## Ліцензія

Apache-2.0. Дивіться файл [LICENSE](LICENSE) для деталей.
