import asyncio

import httpx2 as httpx
import pytest

from app.core.config import Settings
from app.scraper.fetcher import FetchError, fetch_http
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
