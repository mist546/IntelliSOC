import ipaddress
import socket
from urllib.parse import urlparse

from app.config import get_settings

settings = get_settings()

ALLOWED_SCHEMES = {"http", "https"}


class ScanTargetError(Exception):
    pass


def _is_private_or_reserved(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast


def validate_scan_target(url: str) -> str:
    """Validates a scan target against SSRF risks. Only explicitly
    allow-listed hosts (SCAN_ALLOWED_HOSTS, default localhost/127.0.0.1) may
    be scanned, matching the project's "authorized lab targets only" scope.
    Returns the normalized URL on success or raises ScanTargetError.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ScanTargetError(f"Unsupported scheme '{parsed.scheme}'. Only http/https are allowed.")
    if not parsed.hostname:
        raise ScanTargetError("URL has no hostname.")
    if parsed.username or parsed.password:
        raise ScanTargetError("URLs with embedded credentials are not allowed.")

    hostname = parsed.hostname.lower()
    allowed_hosts = {h.lower() for h in settings.SCAN_ALLOWED_HOSTS}

    if hostname not in allowed_hosts:
        raise ScanTargetError(
            f"'{hostname}' is not an authorized scan target. "
            f"Allowed hosts: {sorted(allowed_hosts)}. Add lab targets to SCAN_ALLOWED_HOSTS."
        )

    try:
        resolved_ips = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except socket.gaierror as exc:
        raise ScanTargetError(f"Could not resolve hostname '{hostname}': {exc}") from exc

    for ip_str in resolved_ips:
        try:
            if _is_private_or_reserved(ip_str) and hostname not in ("localhost", "127.0.0.1", "::1"):
                raise ScanTargetError(f"'{hostname}' resolves to a private/internal address ({ip_str}); refusing to scan.")
        except ValueError:
            continue

    return url
