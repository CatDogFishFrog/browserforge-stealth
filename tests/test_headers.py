"""
Tests for HeaderGenerator and Browser dataclass.
"""

from __future__ import annotations

import pytest
from browserforge_stealth import Browser, HeaderGenerator


def test_default_header_generation() -> None:
    headers = HeaderGenerator().generate()

    assert isinstance(headers, dict)
    assert any(k.lower() == "user-agent" for k in headers)
    assert any(k.lower() == "accept" for k in headers)
    assert any(k.lower() == "accept-language" for k in headers)


@pytest.mark.parametrize("browser_name", ["chrome", "firefox", "safari"])
def test_generate_for_specific_browser(browser_name: str) -> None:
    gen = HeaderGenerator(browser=browser_name)
    headers = gen.generate()

    ua = next(v for k, v in headers.items() if k.lower() == "user-agent")
    if browser_name == "chrome":
        assert "Chrome" in ua
    elif browser_name == "firefox":
        assert "Firefox" in ua
    elif browser_name == "safari":
        assert "Safari" in ua


def test_generate_with_browser_version_constraints() -> None:
    browser = Browser(name="chrome", min_version=115, max_version=125)
    headers = HeaderGenerator().generate(browser=(browser,))

    ua = next(v for k, v in headers.items() if k.lower() == "user-agent")
    assert "Chrome/" in ua


@pytest.mark.parametrize("os_name", ["windows", "macos", "linux", "android", "ios"])
def test_generate_for_various_os(os_name: str) -> None:
    headers = HeaderGenerator().generate(os=os_name)
    assert isinstance(headers, dict)
    assert any(k.lower() == "user-agent" for k in headers)


def test_generate_with_locale() -> None:
    headers = HeaderGenerator().generate(locale="uk-UA")
    accept_lang = next(v for k, v in headers.items() if k.lower() == "accept-language")
    assert "uk" in accept_lang


def test_http_version_1_vs_2() -> None:
    h1 = HeaderGenerator().generate(http_version=1)
    assert "User-Agent" in h1
    assert "Accept-Language" in h1

    h2 = HeaderGenerator().generate(http_version=2)
    # In HTTP/2, headers are lowercase
    assert any(k == "user-agent" or k.lower() == "user-agent" for k in h2)


def test_request_dependent_headers() -> None:
    headers_h1 = HeaderGenerator().generate(
        http_version=1,
        request_dependent_headers={"Accept": "application/json"},
    )
    assert headers_h1["Accept"] == "application/json"

    headers_h2 = HeaderGenerator().generate(
        http_version=2,
        request_dependent_headers={"accept": "application/json"},
    )
    accept_val = next(v for k, v in headers_h2.items() if k.lower() == "accept")
    assert accept_val == "application/json"


def test_impossible_strict_constraints_raise() -> None:
    with pytest.raises(ValueError, match="No headers based on this input"):
        # impossible combination: Safari on Windows with strict=True
        HeaderGenerator().generate(browser="safari", os="windows", strict=True)
