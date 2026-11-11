import asyncio

import httpx2 as httpx
import pytest

from app.core.config import Settings
from app.scraper import fetcher
from app.scraper.fetcher import FetchedPage, FetchError, fetch_http, fetch_page
from app.scraper.url_guard import UnsafeURLError

SETTINGS = Settings(max_page_bytes=1000)


def _fetch(url, handler):
    return asyncio.run(fetch_http(url, SETTINGS, transport=httpx.MockTransport(handler)))


def test_fetches_html(public_dns):
    page = _fetch("https://shop.example/p/1", lambda r: httpx.Response(200, html="<h1>Hi</h1>"))
    assert page.html == "<h1>Hi</h1>" and page.method == "http"


def test_follows_safe_redirects(public_dns):
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return httpx.Response(200, html="<p>moved</p>")

    page = _fetch("https://shop.example/old", handler)
    assert page.url == "https://shop.example/new"


def test_blocks_redirect_to_internal_address(public_dns):
    handler = lambda r: httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})  # noqa: E731
    with pytest.raises(UnsafeURLError):
        _fetch("https://evil.example/", handler)


def test_rejects_non_html(public_dns):
    handler = lambda r: httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})  # noqa: E731
    with pytest.raises(FetchError, match="Not an HTML page"):
        _fetch("https://shop.example/file.pdf", handler)


def test_rejects_oversized_pages(public_dns):
    with pytest.raises(FetchError, match="size limit"):
        _fetch("https://shop.example/", lambda r: httpx.Response(200, html="x" * 5000))


def test_server_errors_are_retryable_but_404_is_not(public_dns):
    with pytest.raises(FetchError) as busy:
        _fetch("https://shop.example/", lambda r: httpx.Response(503))
    assert busy.value.retryable
    with pytest.raises(FetchError) as missing:
        _fetch("https://shop.example/", lambda r: httpx.Response(404))
    assert not missing.value.retryable


def test_render_js_goes_straight_to_the_browser_and_scrolls(public_dns, monkeypatch):
    calls = {}

    async def browser(url, settings, scroll=False):
        calls["scroll"] = scroll
        return FetchedPage(url=url, status_code=200, html="<p>items</p>", method="browser")

    async def no_http(*args, **kwargs):
        raise AssertionError("plain HTTP should be skipped")

    monkeypatch.setattr(fetcher, "fetch_browser", browser)
    monkeypatch.setattr(fetcher, "fetch_http", no_http)
    page = asyncio.run(fetch_page("https://shop.example/men", Settings(), render_js=True))
    assert page.method == "browser" and calls == {"scroll": True}


def test_render_js_still_checks_the_url():
    with pytest.raises(UnsafeURLError):
        asyncio.run(fetch_page("http://169.254.169.254/", Settings(), render_js=True))


def test_render_js_browser_crash_becomes_a_retryable_fetch_error(public_dns, monkeypatch):
    async def crash(url, settings, scroll=False):
        raise RuntimeError("chromium died")

    monkeypatch.setattr(fetcher, "fetch_browser", crash)
    with pytest.raises(FetchError, match="render the page") as info:
        asyncio.run(fetch_page("https://shop.example/", Settings(), render_js=True))
    assert info.value.retryable


def test_render_js_refused_when_browser_disabled(public_dns):
    with pytest.raises(FetchError, match="turned off"):
        asyncio.run(fetch_page("https://shop.example/", Settings(playwright_enabled=False), render_js=True))
