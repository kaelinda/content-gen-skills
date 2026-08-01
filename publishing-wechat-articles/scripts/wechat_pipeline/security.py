from __future__ import annotations

import ipaddress
from pathlib import Path
import re
import socket
from urllib.parse import urlsplit, urlunsplit


class SecurityError(ValueError):
    pass


def _reject_non_public_ip(value: str) -> None:
    ip = ipaddress.ip_address(value)
    if not ip.is_global:
        raise SecurityError(f"non-public address is blocked: {ip}")


def validate_public_url(url: str, resolver=socket.getaddrinfo) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise SecurityError("only http and https URLs are allowed")
    if not parsed.hostname or parsed.username or parsed.password:
        raise SecurityError("URL must have a hostname and no embedded credentials")
    try:
        _reject_non_public_ip(parsed.hostname)
    except ValueError:
        try:
            addresses = {row[4][0] for row in resolver(parsed.hostname, parsed.port or 443)}
        except OSError as exc:
            raise SecurityError(f"hostname resolution failed: {parsed.hostname}") from exc
        if not addresses:
            raise SecurityError(f"hostname did not resolve: {parsed.hostname}")
        for address in addresses:
            _reject_non_public_ip(address)
    clean = parsed._replace(fragment="")
    return urlunsplit(clean)


def sanitize_resource_url(url: str) -> str:
    value = url.strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return value


def normalize_slug(value: str, max_length: int = 64) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)[:max_length].rstrip("-")
    return slug or "article"


def safe_output_path(root: Path, relative: str | Path) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise SecurityError(f"path escapes root: {relative}") from exc
    return candidate
