import pytest

from app.scraper.url_guard import UnsafeURLError, check_url


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://10.0.0.5/admin",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://0.0.0.0/",
        "http://metadata.google.internal/",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://user:pass@example.com/",
        "http://example.com:5432/",
        "not a url",
    ],
)
def test_blocks_unsafe_urls(url, public_dns):
    with pytest.raises(UnsafeURLError):
        check_url(url)


def test_blocks_hostnames_that_resolve_to_private_ips(monkeypatch):
    monkeypatch.setattr("app.scraper.url_guard.resolve_host", lambda host: ["93.184.215.14", "10.1.2.3"])
    with pytest.raises(UnsafeURLError, match="private"):
        check_url("https://sneaky.example.com/")


def test_allows_public_urls(public_dns):
    assert check_url("  https://example.com/product?id=42 ") == "https://example.com/product?id=42"
    assert check_url("http://93.184.215.14:8080/") == "http://93.184.215.14:8080/"
