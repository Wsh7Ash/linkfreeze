"""
tests/test_preview_integration.py — integration against a local static test server.

This uses a tiny in-process HTTP server that returns a canned HTML page and a
second endpoint that echoes request headers so we can assert no credentials are
sent by the preview fetcher.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from linkfreeze.app import PreviewHandler
from linkfreeze.policy import redact_fields
from linkfreeze.fetch import build_request


class EchoHandler(BaseHTTPRequestHandler):
    """Echo request headers and serve a canned page on /page."""

    request_headers: dict = {}

    def do_GET(self) -> None:
        EchoHandler.request_headers = {k: v for k, v in self.headers.items()}
        if self.path.startswith("/page"):
            body = (
                b"<html><head><title>Test Page</title></head><body>"
                b"<p>Hello preview</p><p>second line</p></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: ANN401
        pass


@pytest.fixture(scope="module")
def echo_server():
    server = HTTPServer(("127.0.0.1", 0), EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.server_close()


def base_url(server: HTTPServer) -> str:
    return f"http://127.0.0.1:{server.server_port}"


def _start_preview_server(allow=None, deny=None):
    from linkfreeze.app import run_server
    ps = run_server("127.0.0.1", 0, allow=allow, deny=deny)
    thread = threading.Thread(target=ps.serve_forever, daemon=True)
    thread.start()
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{ps.server_port}/health", timeout=0.1) as r:
                if r.status == 200:
                    break
        except OSError:
            time.sleep(0.02)
    return ps


class TestPreviewIntegration:
    def test_preview_endpoint_returns_snapshot_card(self, echo_server):
        ps = _start_preview_server(allow=[], deny=[])
        try:
            server = echo_server
            base = base_url(server)

            deadline = time.time() + 5
            last_exc = None
            preview_base = f"http://127.0.0.1:{ps.server_port}"
            page_url = f"{base}/page"
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen(f"{preview_base}/preview?url={urllib.parse.quote(page_url)}", timeout=0.2) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                        break
                except urllib.error.HTTPError as exc:
                    body = json.loads(exc.read().decode("utf-8"))
                    last_exc = exc
                    break
                except OSError:
                    time.sleep(0.02)
            else:
                raise last_exc or OSError("timeout")

            assert "snapshot" in body
            assert body["snapshot"]["url"] == page_url
            assert body["snapshot"]["title"] == "Test Page"
            assert "Hello preview" in body["snapshot"]["body_preview"]
            assert "policy_report" in body
        finally:
            ps.server_close()

    def test_no_credentials_forwarded_to_target(self, echo_server):
        base = base_url(echo_server)
        page_url = f"{base}/page"
        req = build_request(page_url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            received = EchoHandler.request_headers
        assert "cookie" not in {k.lower() for k in received}
        assert "authorization" not in {k.lower() for k in received}
        assert received.get("Referer", "") == ""

    def test_policy_report_lists_redacted_credentials_if_present(self, echo_server):
        headers = {"Cookie": "s=1", "Authorization": "Bearer t", "User-Agent": "x"}
        redacted = redact_fields(headers)
        assert redacted["Cookie"] == "<redacted>"
        assert redacted["Authorization"] == "<redacted>"
        assert redacted["User-Agent"] == "x"

    def test_expiry_is_reported(self, echo_server):
        ps = _start_preview_server(allow=[], deny=[])
        try:
            server = echo_server
            base = base_url(server)

            preview_base = f"http://127.0.0.1:{ps.server_port}"
            page_url = f"{base}/page"
            deadline = time.time() + 5
            last_exc = None
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen(f"{preview_base}/preview?url={urllib.parse.quote(page_url)}", timeout=0.2) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                        break
                except urllib.error.HTTPError as exc:
                    body = json.loads(exc.read().decode("utf-8"))
                    last_exc = exc
                    break
                except OSError:
                    time.sleep(0.02)
            else:
                raise last_exc or OSError("timeout")

            assert "meta" in body
            assert "expires_at" in body["meta"]
            assert body["meta"]["expires_at"] > body["meta"]["fetched_at"]
        finally:
            ps.server_close()

    def test_deny_blocks_preview(self, echo_server):
        ps = _start_preview_server(allow=[], deny=["127.0.0.1"])
        try:
            server = echo_server
            base = base_url(server)

            preview_base = f"http://127.0.0.1:{ps.server_port}"
            page_url = f"{base}/page"
            deadline = time.time() + 5
            last_exc = None
            while time.time() < deadline:
                try:
                    with urllib.request.urlopen(f"{preview_base}/preview?url={urllib.parse.quote(page_url)}", timeout=0.2) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                        break
                except urllib.error.HTTPError as exc:
                    body = json.loads(exc.read().decode("utf-8"))
                    last_exc = exc
                    break
                except OSError:
                    time.sleep(0.02)
            else:
                raise last_exc or OSError("timeout")

            assert body["error"] == "preview denied by policy"
        finally:
            ps.server_close()
