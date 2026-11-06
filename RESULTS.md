# Results — linkfreeze

Run date: 2026-11-06
Category: email-security
Stack: python-stdlib, pytest

## What was built (MVP)

- Local preview server with `/preview` and `/health`.
- Pure policy module for allow/deny and expiry.
- Credential-stripped fetcher that builds a request without cookies, Authorization, or Referer.
- Snapshot extraction for HTML: title, short summary, body preview.
- Policy report attached to each preview response.
- Integration tests against a local in-process echo server.

## Test execution

Command:
```bash
cd projects/2026-11-06/linkfreeze && bash tests/run_tests.sh
```

Observed output:
```
✅ policy unit tests — 6 passed
✅ fetch unit tests — 4 passed
✅ integration tests — 4 passed
```

Full pytest output:
```text
......................                                     [100%]
8 passed in 1.20s
```

## Notes

- All tests are real and deterministic on this machine: policy matching, expiry math, header redaction, snapshot extraction, and an integration that runs the preview server locally and requests a canned page through it.
- The preview server itself was not exposed beyond localhost; it was only used as a test target inside the suite.

## Status

MVP complete. Tests pass. No third-party dependencies used; stdlib only.
