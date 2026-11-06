# Link Freeze

A local link-preview proxy that renders a safe, time-bounded snapshot of a URL so you can show previews without sending a live browser to the original site on every click.

## What it does

- `GET /preview?url=...` fetches the target URL in an isolated, credential-stripped way and returns a JSON preview card.
- The response includes a snapshot (title, short body preview, final URL) plus a policy report showing what was fetched, when it expires, and which headers were redacted.
- A simple allow/deny prefix list controls which URLs may be previewed.
- No cookies or Authorization headers are forwarded to the target, and the Referer is cleared so the preview does not leak the context of the request.

## Run locally

```bash
cd linkfreeze
python app.py --port 8123
```

Then:

```bash
curl "http://127.0.0.1:8123/preview?url=https://example.com/"
```

Add an allow/deny list:

```bash
python app.py --allow https://trusted.example --deny evil.example
```

## Safety model

- The preview server is a local tool. Running it does not automatically make previews safe for every use case.
- It strips credential headers and does not forward cookies. It does not execute JavaScript from the target inside your browser session.
- Snapshots are time-bounded and marked with an expiry. Treat expired snapshots as stale, not fresh.
- A deny list should be used for sites you do not want previewed at all, even locally.

## Project structure

- `app.py` — preview server with `/preview` and `/health`.
- `policy.py` — allow/deny and expiry logic.
- `fetch.py` — credential-stripped fetcher and snapshot construction.
- `server_config.py` — small settings bundle.
- `tests/` — pytest suite with policy, fetch, and local integration tests.
- `SECURITY.md` — security-relevant design notes.
- `LICENSE` — MIT.

## Limitations

- The MVP uses stdlib HTTP fetching only; it is not a full browser renderer.
- It does not authenticate or restrict access to the preview server itself; run it only on a trusted local interface.
