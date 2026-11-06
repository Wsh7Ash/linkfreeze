"""
fetch.py — credential-stripped request builder and snapshot construction.

MVP uses urllib so the preview server has no third-party dependencies.
"""

from __future__ import annotations

import email.message
import html
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from policy import redact_fields


def build_request(url: str) -> urllib.request.Request:
    """Build a request that does not forward credentials or cookies."""
    parsed = urllib.parse.urlparse(url)
    req = urllib.request.Request(url, method="GET")
    # Explicitly avoid sending cookies or auth by omitting those headers entirely.
    req.add_header("User-Agent", "linkfreeze-preview/0.1.0")
    req.add_header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    req.add_header("Accept-Language", "en")
    # Do not forward Referer to avoid leaking context about where the preview was requested.
    req.add_header("Referer", "")
    return req


def strip_credential_headers(headers: email.message.Message) -> Dict[str, str]:
    return redact_fields({k: v for k, v in headers.items()})


def extract_title(html_bytes: bytes) -> str:
    try:
        text = html_bytes.decode("utf-8", "replace")
    except Exception:
        return ""
    m = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I | re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def extract_summary(html_bytes: bytes, max_lines: int = 3) -> str:
    try:
        text = html_bytes.decode("utf-8", "replace")
    except Exception:
        return ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return " ".join(lines[:max_lines])


def body_preview(html_bytes: bytes, max_chars: int = 300) -> str:
    s = extract_summary(html_bytes, max_lines=8)
    if not s:
        return ""
    return s[:max_chars]


def fetch_snapshot(req: urllib.request.Request) -> Dict[str, Any]:
    """Fetch a URL and return a snapshot dict. No credentials are forwarded."""
    resp: Any = None
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            final_url = resp.url
            status = resp.status
            resp_headers = resp.headers
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        final_url = exc.url or req.full_url
        status = exc.code
        resp_headers = exc.headers if hasattr(exc, "headers") else email.message.Message()
    except Exception as exc:  # noqa: BLE001
        return {
            "meta": {"ttl_seconds": 0, "error": str(exc)},
            "final_url": None,
            "status": None,
            "content_type": None,
            "title": "",
            "summary": "",
            "body_preview": "",
        }
    headers = strip_credential_headers(resp_headers)
    content_type = headers.get("content-type", "application/octet-stream")

    title = ""
    summary = ""
    preview = ""
    if isinstance(body, (bytes, bytearray)) and body:
        ct = (content_type or "").lower()
        if "text/html" in ct or "application/xhtml" in ct or ct == "application/octet-stream":
            title = extract_title(body)
            summary = extract_summary(body)
            preview = body_preview(body)

    return {
        "meta": {"ttl_seconds": 300, "headers": headers},
        "final_url": final_url,
        "status": status,
        "content_type": content_type,
        "title": title,
        "summary": summary,
        "body_preview": preview,
    }
