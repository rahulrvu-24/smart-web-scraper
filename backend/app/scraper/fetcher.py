"""Fetch a page: plain HTTP first, headless Chromium only when the page needs JavaScript.

Plain HTTP uses ~no memory and takes well under a second. Chromium needs a few hundred MB,
so it only runs when the HTTP response has almost no visible text (a JavaScript app shell).
"""

import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx2 as httpx

from app.core.config import Settings
from app.scraper.html_clean import visible_text_length
from app.scraper.url_guard import UnsafeURLError, check_url

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; SmartWebScraper/0.1; +https://github.com/rahulrvu-24/smart-web-scraper)"
MAX_REDIRECTS = 5
HTML_TYPES = ("text/html", "application/xhtml+xml")


class FetchError(Exception):
    """The page could not be fetched. `retryable` says whether trying again might help."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class FetchedPage:
    url: str
    status_code: int
    html: str
    method: str  # "http" or "browser"


async def fetch_http(url: str, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> FetchedPage:
    """GET the URL, following redirects by hand so every hop is SSRF-checked."""
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"}
    async with httpx.AsyncClient(
        timeout=settings.fetch_timeout_seconds, follow_redirects=False, headers=headers, transport=transport
    ) as client:
        current = check_url(url)
        for _ in range(MAX_REDIRECTS + 1):
            try:
                async with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location", "")
                        current = check_url(urljoin(current, location))
                        continue
                    if response.status_code >= 500 or response.status_code == 429:
                        raise FetchError(f"Site returned HTTP {response.status_code}", retryable=True)
                    if response.status_code >= 400:
                        raise FetchError(f"Site returned HTTP {response.status_code}")
                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if content_type and content_type not in HTML_TYPES:
                        raise FetchError(f"Not an HTML page (content type {content_type})")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > settings.max_page_bytes:
                            raise FetchError("Page is larger than the size limit")
                    encoding = response.encoding or "utf-8"
                    html = bytes(body).decode(encoding, errors="replace")
                    return FetchedPage(url=current, status_code=response.status_code, html=html, method="http")
            except httpx.TimeoutException:
                raise FetchError("The site took too long to respond", retryable=True)
            except httpx.TransportError as exc:
                raise FetchError(f"Could not connect to the site ({type(exc).__name__})", retryable=True)
        raise FetchError("Too many redirects")


async def fetch_browser(url: str, settings: Settings) -> FetchedPage:
    """Render with headless Chromium. Sub-requests are SSRF-checked and heavy assets skipped."""
    from playwright.async_api import async_playwright  # imported lazily: optional and heavy

    async def guard(route):
        request = route.request
        if request.resource_type in {"image", "media", "font"}:
            return await route.abort()
        try:
            await asyncio.to_thread(check_url, request.url)
        except UnsafeURLError:
            return await route.abort()
        return await route.continue_()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--disable-dev-shm-usage", "--no-sandbox"],
            executable_path=settings.browser_executable_path or None,
        )
        try:
            page = await browser.new_page(user_agent=USER_AGENT)
            await page.route("**/*", guard)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=settings.fetch_timeout_seconds * 1000)
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:  # noqa: BLE001 - some pages never go idle; use what we have
                pass
            html = await page.content()
            final_url = check_url(page.url)
            status = response.status if response else 200
            return FetchedPage(url=final_url, status_code=status, html=html, method="browser")
        finally:
            await browser.close()


async def fetch_page(url: str, settings: Settings) -> FetchedPage:
    page = await fetch_http(url, settings)
    if not settings.playwright_enabled or visible_text_length(page.html) >= settings.min_text_chars_before_render:
        return page
    log.info("Page %s has little text; rendering with Chromium", urlsplit(url).hostname)
    try:
        return await fetch_browser(page.url, settings)
    except UnsafeURLError:
        raise
    except Exception as exc:  # noqa: BLE001 - fall back to what plain HTTP gave us
        log.warning("Browser render failed (%s); using plain HTTP result", exc)
        return page
