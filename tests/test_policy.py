"""
tests/test_policy.py — policy unit tests.
"""
from __future__ import annotations

import pytest
from linkfreeze.policy import allows_preview, preview_expires_at, redact_fields


class TestAllowsPreview:
    def test_empty_lists_allow_anything(self):
        assert allows_preview("https://example.com/page", [], []) is True

    def test_deny_blocks_substring(self):
        assert allows_preview("https://evil.example/phish", [], ["evil.example"]) is False

    def test_allow_list_allows_prefix(self):
        assert allows_preview("https://trusted.example/page", ["https://trusted.example"], []) is True
        assert allows_preview("https://evil.example/page", ["https://trusted.example"], []) is False

    def test_deny_wins_over_allow(self):
        assert allows_preview("https://trusted.example/evil", ["https://trusted.example"], ["evil"]) is False

    def test_case_insensitive_matching(self):
        assert allows_preview("https://Trusted.Example/page", ["https://trusted.example"], []) is True
        assert allows_preview("https://trusted.example/EVIL", [], ["evil"]) is False


class TestPreviewExpiresAt:
    def test_ttl_applied(self):
        now = 1_000_000.0
        assert preview_expires_at(now, 300) == 1_000_300

    def test_zero_ttl_means_now(self):
        now = 1_000_000.0
        assert preview_expires_at(now, 0) == 1_000_000

    def test_negative_ttl_normalized_to_zero(self):
        now = 1_000_000.0
        assert preview_expires_at(now, -5) == 1_000_000


class TestRedactFields:
    def test_credential_headers_redacted(self):
        headers = {
            "Cookie": "session=abc",
            "Authorization": "Bearer token",
            "User-Agent": "linkfreeze",
            "X-Custom": "value",
        }
        out = redact_fields(headers)
        assert out["Cookie"] == "<redacted>"
        assert out["Authorization"] == "<redacted>"
        assert out["User-Agent"] == "linkfreeze"
        assert out["X-Custom"] == "value"

    def test_case_insensitive(self):
        headers = {"COOKIE": "x=y", "authorization": "Bearer z"}
        out = redact_fields(headers)
        assert out["COOKIE"] == "<redacted>"
        assert out["authorization"] == "<redacted>"
