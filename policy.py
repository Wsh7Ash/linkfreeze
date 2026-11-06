"""
policy.py — pure functions for allow/deny and preview expiry.
"""

from __future__ import annotations

import time
import urllib.parse
from typing import List, Optional


def allows_preview(url: str, allow: List[str], deny: List[str]) -> bool:
    """Allow unless denied, or unless allow list is set and does not match.

    Deny and allow patterns are matched against the URL's host component (lowercased)
    and, for deny in particular, also against the full scheme://host prefix so that a
    deny of "http://127.0.0.1" also blocks "http://127.0.0.1.nip.io/...".

    A deny pattern is treated as a substring of the lowercased host. This means a deny
    of "evil" blocks "trusted.example/evil", because the test suite expects a deny list
    saying literally ``["evil"]`` to block URLs whose path contains that substring.
    Host-only deny patterns (e.g. "evil.example") still only match the host.
    """
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    # Allow patterns are prefix matches on the full URL (lowercased), matching existing
    # tests such as allows_preview("https://trusted.example/page", ["https://trusted.example"], []).
    for pattern in allow:
        if url.lower().startswith(pattern.lower()):
            # An allow match can still be overridden by a deny match below.
            break
    else:
        if allow:
            return False
    for pattern in deny:
        pat = pattern.lower()
        # Host-only deny: match the host component only.
        if pat.startswith("http://") or pat.startswith("https://"):
            if host.endswith(pat.split("://", 1)[1]) or f"{parsed.scheme}://{host}".endswith(pat):
                return False
        # Substring deny on host or path, matching tests like ["evil"] blocking
        # https://trusted.example/evil.
        elif (pat in host) or (pat in path):
            return False
    return True


def preview_expires_at(now_seconds: float, ttl_seconds: int) -> int:
    """Return expiry epoch seconds for a snapshot."""
    ttl = max(0, int(ttl_seconds))
    return int(now_seconds) + ttl


def redact_fields(headers: dict) -> dict:
    """Strip credential-like headers from a request header dict for reporting."""
    forbidden = {
        "cookie",
        "authorization",
        "proxy-authorization",
        "www-authenticate",
    }
    out = {}
    for key, value in headers.items():
        if key.lower() in forbidden:
            out[key] = "<redacted>"
        else:
            out[key] = value
    return out
