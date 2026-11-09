"""SSRF protection: only fetch public http(s) URLs.

A scraper that fetches any URL a user types is a classic SSRF hole: without checks,
"http://169.254.169.254/" (cloud metadata) or "http://localhost:5432" would make our
server attack itself. Every URL, and every redirect hop, goes through `check_url`.
"""

import ipaddress
import socket
from urllib.parse import urlsplit

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "metadata.google.internal"}
MAX_URL_LENGTH = 2048


class UnsafeURLError(ValueError):
    """The URL is malformed or points somewhere we refuse to fetch."""


def _is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped  # ::ffff:127.0.0.1 is still loopback
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or not ip.is_global
    )


def resolve_host(host: str) -> list[str]:
    """All IP addresses `host` resolves to. Split out so tests can replace it."""
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return sorted({info[4][0] for info in infos})


def check_url(url: str) -> str:
    """Return the normalised URL, or raise UnsafeURLError explaining why not."""
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise UnsafeURLError("URL is too long")
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Only http and https URLs are allowed")
    if parts.username or parts.password:
        raise UnsafeURLError("URLs with embedded credentials are not allowed")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise UnsafeURLError("URL has no host")
    if host in BLOCKED_HOSTNAMES or host.endswith(".localhost") or host.endswith(".internal"):
        raise UnsafeURLError("Internal hostnames are not allowed")
    try:
        port = parts.port
    except ValueError:
        raise UnsafeURLError("Invalid port")
    if port is not None and port not in (80, 443, 8080, 8443):
        raise UnsafeURLError("Only standard web ports are allowed")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        addresses = [str(literal)]
    else:
        try:
            addresses = resolve_host(host)
        except socket.gaierror:
            raise UnsafeURLError("Could not resolve the hostname")
    if not addresses:
        raise UnsafeURLError("Could not resolve the hostname")
    for address in addresses:
        if not _is_public(ipaddress.ip_address(address.split("%")[0])):
            raise UnsafeURLError("URL points to a private or internal address")
    return parts.geturl()
