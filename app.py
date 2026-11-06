"""
linkfreeze — local link-preview proxy MVP.

Provides a /preview endpoint that fetches a target URL in a credential-stripped,
isolated manner and returns a time-bounded snapshot card plus a policy report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

from policy import allows_preview, preview_expires_at, redact_fields
from fetch import build_request, fetch_snapshot

HOST = "127.0.0.1"
PORT = 8123


class PreviewHandler(BaseHTTPRequestHandler):
    allow_list: List[str] = []
    deny_list: List[str] = []

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/health":
            self._json(200, {"status": "ok"})
            return

        if parsed.path != "/preview":
            self._json(404, {"error": "not found"})
            return

        url = (params.get("url", [None])[0] or "").strip()
        if not url:
            self._json(400, {"error": "missing url parameter"})
            return

        if not allows_preview(url, self.allow_list, self.deny_list):
            self._json(403, {"error": "preview denied by policy", "url": url})
            return

        try:
            req = build_request(url)
            snap = fetch_snapshot(req)
        except Exception as exc:  # noqa: BLE001 — MVP: surface fetch failure as a structured error
            self._json(502, {"error": "fetch failed", "detail": str(exc), "url": url})
            return

        now = int(time.time())
        expires = preview_expires_at(now, snap["meta"]["ttl_seconds"])
        report = {
            "url": url,
            "method": req.method,
            "headers_sent": redact_fields(dict(req.headers)),
            "fetched_at": now,
            "expires_at": expires,
            "ttl_seconds": snap["meta"]["ttl_seconds"],
            "final_url": snap.get("final_url"),
            "status": snap.get("status"),
            "content_type": snap.get("content_type"),
        }

        card = {
            "snapshot": {
                "url": snap.get("final_url") or url,
                "title": snap.get("title") or "",
                "summary": snap.get("summary") or "",
                "body_preview": snap.get("body_preview") or "",
            },
            "meta": {
                "expires_at": expires,
                "ttl_seconds": snap["meta"]["ttl_seconds"],
                "fetched_at": now,
            },
            "policy_report": report,
        }

        self._json(200, card)

    def _json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # pragma: no cover
        # Keep console output quiet in MVP unless debugging.
        pass


def run_server(host: str = HOST, port: int = PORT, allow: Optional[List[str]] = None, deny: Optional[List[str]] = None) -> HTTPServer:
    server = HTTPServer((host, port), PreviewHandler)
    server.RequestHandlerClass.allow_list = allow or []
    server.RequestHandlerClass.deny_list = deny or []
    return server


def main() -> None:
    ap = argparse.ArgumentParser(description="linkfreeze local preview server")
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--allow", action="append", default=[], help="Allowed URL prefixes")
    ap.add_argument("--deny", action="append", default=[], help="Denied URL prefixes")
    args = ap.parse_args()

    server = run_server(args.host, args.port, args.allow, args.deny)
    print(f"linkfreeze listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
