import ipaddress
import os
import re
import socket
from urllib.parse import urlparse

from fastapi import HTTPException


SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}
BLOCKED_IPS = {
    ipaddress.ip_address("169.254.169.254"),
}


def sanitize_name(value: str, fallback: str = "source") -> str:
    name = os.path.basename(value or "").strip().replace(" ", "_")
    name = SAFE_FILENAME_RE.sub("_", name)
    return name[:120] or fallback


def is_private_or_reserved_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
        or ip in BLOCKED_IPS
    )


def validate_public_url(raw_url: str) -> str:
    parsed = urlparse((raw_url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http and https URLs are allowed.")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL must include a valid host.")

    host = parsed.hostname.lower()
    if host in BLOCKED_HOSTS or host.endswith(".localhost"):
        raise HTTPException(status_code=400, detail="Localhost URLs are not allowed.")

    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            addresses = [item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)]
        except socket.gaierror:
            raise HTTPException(status_code=400, detail="URL host could not be resolved.")

    if any(is_private_or_reserved_ip(address) for address in set(addresses)):
        raise HTTPException(status_code=400, detail="Private, local, or reserved network URLs are blocked.")

    return parsed.geturl()
