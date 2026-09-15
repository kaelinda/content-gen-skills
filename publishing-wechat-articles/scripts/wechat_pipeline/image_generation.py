"""Explicitly authorized, optional image generation; no implicit fallback."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import json
import math
from pathlib import Path
import re
import socket
import ssl
from queue import Empty, Queue
from threading import Thread, Timer
import time
from urllib.parse import urlsplit

from .config import ImageGenerationConfig
from .cover import normalize_generated_cover

MODEL = "gpt-image-2"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_RESPONSE_BYTES = 30 * 1024 * 1024


class ImageGenerationError(RuntimeError):
    """Safe, fixed diagnostics: never include provider response/credentials."""


@dataclass(frozen=True)
class ImageGenerationResult:
    cover_path: Path
    source_path: Path
    prompt_path: Path
    provenance_path: Path
    model: str = MODEL


def generate_image_cover(prompt: str, output: Path, *, config: ImageGenerationConfig,
                         authorize_cost: bool = False, transport=None,
                         resolver=socket.getaddrinfo) -> ImageGenerationResult:
    """Generate one cover. The caller must opt in and authorize cost each time."""
    if config.enabled is not True or authorize_cost is not True:
        raise ImageGenerationError("image generation requires opt-in and explicit cost authorization")
    _validate_settings(config, prompt)
    transport = transport or _https_transport
    deadline = time.monotonic() + config.timeout_seconds
    body = json.dumps({"model": MODEL, "prompt": prompt, "n": 1,
                       "size": "1536x1024"}).encode("utf-8")
    response = _request(transport, resolver, deadline, method="POST", url=config.endpoint,
        headers={"Authorization": "Bearer " + config.api_key, "Content-Type": "application/json"},
        body=body, max_bytes=MAX_RESPONSE_BYTES)
    kind, value = _parse_response(response)
    if kind == "b64_json":
        try:
            if len(value) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
                raise ValueError()
            image = base64.b64decode(value, validate=True)
        except Exception:
            raise ImageGenerationError("image response contains invalid or oversized base64") from None
    else:
        image = _request(transport, resolver, deadline, method="GET", url=value,
            headers={"Accept": "image/png,image/jpeg,image/webp"}, body=None,
            max_bytes=MAX_IMAGE_BYTES, allowed_hosts=config.allowed_download_hosts)
    if not image or len(image) > MAX_IMAGE_BYTES:
        raise ImageGenerationError("decoded image exceeds the size limit or is empty")
    try:
        source, cover = normalize_generated_cover(image)
    except Exception:
        raise ImageGenerationError("provider did not return a valid 1536x1024 PNG, JPEG, or WebP image") from None
    output = Path(output)
    result = ImageGenerationResult(output, output.with_suffix(".source.png"),
        output.with_suffix(".prompt.txt"), output.with_suffix(".provenance.json"))
    provenance = {
        "schema_version": 1, "method": "openai-compatible-images-generations",
        "model": MODEL, "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_size": [1536, 1024], "cover_size": [1200, 540],
        "transform": {"resize": [1200, 800], "crop_box": [0, 130, 1200, 670]},
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "cover_sha256": hashlib.sha256(cover).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "visual_review": "required",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    result.source_path.write_bytes(source)
    result.prompt_path.write_text(prompt, encoding="utf-8")
    output.write_bytes(cover)
    result.provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return result


def _parse_response(response: bytes) -> tuple[str, str]:
    try:
        decoded = json.loads(response)
        if not isinstance(decoded, dict) or decoded.get("model", MODEL) != MODEL:
            raise ValueError()
        data = decoded["data"]
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise ValueError()
        item = data[0]
        keys = [key for key in ("b64_json", "url") if key in item]
        if len(keys) != 1 or not isinstance(item[keys[0]], str) or not item[keys[0]]:
            raise ValueError()
        return keys[0], item[keys[0]]
    except Exception:
        raise ImageGenerationError("image provider returned an invalid generation response") from None


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ImageGenerationError("image request timed out; reconcile cost before retry")
    return remaining


def _public_address(url: str, resolver, *, deadline: float, allowed_hosts=None) -> str:
    try:
        if not isinstance(url, str) or len(url) > 8192 or any(ord(c) <= 32 or ord(c) >= 127 for c in url):
            raise ValueError()
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.fragment or parsed.port not in (None, 443)
                or "\\" in url or (allowed_hosts is None and parsed.query)):
            raise ValueError()
        if allowed_hosts is not None and parsed.hostname.lower() not in {h.lower() for h in allowed_hosts}:
            raise ValueError()
        try:
            addresses = [str(ipaddress.ip_address(parsed.hostname))]
        except ValueError:
            addresses = [row[4][0] for row in _resolve_bounded(resolver, parsed.hostname, deadline)]
        if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
            raise ValueError()
        return addresses[0]
    except Exception:
        raise ImageGenerationError("image URL or DNS is unsafe or unavailable") from None


def _request(transport, resolver, deadline, *, method, url, headers, body, max_bytes, allowed_hosts=None):
    resolved_ip = _public_address(url, resolver, deadline=deadline, allowed_hosts=allowed_hosts)
    try:
        status, response = transport(method=method, url=url, headers=headers, body=body,
            max_bytes=max_bytes, timeout=_remaining(deadline), resolved_ip=resolved_ip)
    except Exception:
        raise ImageGenerationError("image request failed; reconcile cost before retry") from None
    _remaining(deadline)
    if status != 200:
        raise ImageGenerationError("image provider rejected the request; redirects and automatic retries are disabled")
    if not isinstance(response, bytes) or len(response) > max_bytes:
        raise ImageGenerationError("image response exceeds the size limit or is invalid")
    return response


def _resolve_bounded(resolver, host: str, deadline: float):
    """Bound blocking system DNS without waiting for a hung resolver on exit."""
    results = Queue(maxsize=1)
    def resolve():
        try:
            results.put((True, resolver(host, 443)))
        except Exception:
            results.put((False, None))
    Thread(target=resolve, daemon=True).start()
    try:
        ok, value = results.get(timeout=_remaining(deadline))
    except Empty:
        raise ImageGenerationError("image DNS lookup timed out") from None
    if not ok:
        raise ImageGenerationError("image DNS lookup failed")
    return value


def _https_transport(*, method, url, headers, body, timeout, max_bytes, resolved_ip):
    """Direct HTTPS only; pinned IP, original SNI/Host, no proxy or redirects."""
    import certifi

    parsed = urlsplit(url)
    deadline = time.monotonic() + timeout
    context = ssl.create_default_context(cafile=certifi.where())
    raw = socket.socket(socket.AF_INET6 if ":" in resolved_ip else socket.AF_INET, socket.SOCK_STREAM)
    connection = http.client.HTTPConnection(parsed.hostname, 443, timeout=timeout)
    sockets = [raw]

    def abort():
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    timer = Timer(_remaining(deadline), abort)
    timer.daemon = True
    timer.start()
    try:
        raw.settimeout(_remaining(deadline))
        raw.connect((resolved_ip, 443))
        raw.settimeout(_remaining(deadline))
        # Register the TLS socket BEFORE handshake so the deadline can abort it.
        tls = context.wrap_socket(raw, server_hostname=parsed.hostname, do_handshake_on_connect=False)
        sockets.append(tls)
        tls.settimeout(_remaining(deadline))
        tls.do_handshake()
        connection.sock = tls
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        tls.settimeout(_remaining(deadline))
        connection.request(method, path, body=body, headers=headers)
        tls.settimeout(_remaining(deadline))
        response = connection.getresponse()
        length = response.getheader("Content-Length")
        if length is not None and (not length.isdigit() or int(length) > max_bytes):
            raise ImageGenerationError("image response exceeds the size limit")
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise ImageGenerationError("compressed image HTTP responses are not accepted")
        data = bytearray()
        while True:
            tls.settimeout(_remaining(deadline))
            chunk = response.read1(min(65536, max_bytes + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > max_bytes:
                raise ImageGenerationError("image response exceeds the size limit")
        _remaining(deadline)
        if length is not None and len(data) != int(length):
            raise ImageGenerationError("image response was truncated")
        return response.status, bytes(data)
    finally:
        timer.cancel()
        connection.close()
        for sock in sockets:
            sock.close()


def _validate_settings(config: ImageGenerationConfig, prompt: str) -> None:
    if config.model != MODEL:
        raise ImageGenerationError("image generation requires model gpt-image-2; no fallback")
    if (not isinstance(config.api_key, str) or not config.api_key
            or any(ord(char) < 33 or ord(char) > 126 for char in config.api_key)):
        raise ImageGenerationError("image generation requires a valid local API key")
    if (type(config.timeout_seconds) not in (float, int)
            or not math.isfinite(config.timeout_seconds) or not 1 <= config.timeout_seconds <= 120):
        raise ImageGenerationError("image generation timeout must be between 1 and 120 seconds")
    if (not isinstance(config.allowed_download_hosts, (tuple, list))
            or any(not isinstance(host, str) or not re.fullmatch(r"[a-zA-Z0-9.-]+", host)
                   for host in config.allowed_download_hosts)):
        raise ImageGenerationError("image download allowlist requires exact hostnames")
    if (not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 32000
            or config.api_key in prompt):
        raise ImageGenerationError("image prompt is empty, too long, or contains credentials")
