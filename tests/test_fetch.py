"""
tests/test_fetch.py — fetch and request-builder unit tests.
"""
from __future__ import annotations

import email.message
import pytest

from linkfreeze.fetch import (
    build_request,
    strip_credential_headers,
    extract_title,
    extract_summary,
    body_preview,
)
import email.message


class TestBuildRequest:
    def test_url_preserved(self):
        req = build_request("https://example.com/path?q=1")
        assert req.full_url == "https://example.com/path?q=1"

    def test_no_credential_headers_emitted(self):
        req = build_request("https://example.com/")
        msg = email.message.Message()
        for k, v in req.header_items():
            msg[k] = v
        headers = {k.lower(): msg[k] for k in msg.keys()}
        assert "cookie" not in headers
        assert "authorization" not in headers
        assert headers.get("referer") == ""

    def test_user_agent_present(self):
        req = build_request("https://example.com/")
        msg = email.message.Message()
        for k, v in req.header_items():
            msg[k] = v
        assert "user-agent" in {k.lower() for k in msg.keys()}
        ua = msg["User-Agent"]
        assert ua is not None
        assert "linkfreeze-preview" in ua


class TestStripCredentialHeaders:
    def test_strips_credentials(self):
        msg = email.message.Message()
        msg["Cookie"] = "a=b"
        msg["Authorization"] = "Bearer t"
        msg["User-Agent"] = "linkfreeze"
        out = strip_credential_headers(msg)
        out_lower = {k.lower(): v for k, v in out.items()}
        assert out_lower["cookie"] == "<redacted>"
        assert out_lower["authorization"] == "<redacted>"
        assert out_lower["user-agent"] == "linkfreeze"


class TestExtractTitle:
    def test_extracts_title(self):
        html = b"<html><head><title>Hello World</title></head><body></body></html>"
        assert extract_title(html) == "Hello World"

    def test_no_title_returns_empty(self):
        assert extract_title(b"<html><body></body></html>") == ""


class TestExtractSummary:
    def test_extracts_first_lines_without_tags(self):
        html = (
            b"<html><body><p>First paragraph.</p>"
            b"<p>Second paragraph here.</p></body></html>"
        )
        assert "First paragraph" in extract_summary(html)
        assert "Second paragraph" in extract_summary(html)


class TestBodyPreview:
    def test_truncates_long_summary(self):
        html = b"<html><body>" + b"<p>line </p>" * 20 + b"</body></html>"
        preview = body_preview(html, max_chars=40)
        assert len(preview) <= 40
