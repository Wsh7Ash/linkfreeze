# Security Notes — linkfreeze

## What this is

A local link-preview proxy that fetches a URL and returns a time-bounded snapshot plus a policy report.

## Threat model

The main risk linkfreeze addresses is unnecessary credential and context leakage when generating a preview: cookies, Authorization headers, and Referer context may be forwarded to the linked site if a preview is generated naively. Linkfreeze strips credential headers and clears Referer when fetching a target.

## What it does not do

- It is not a browser sandbox. Fetching a URL still contacts the target server and receives whatever response it returns.
- It does not render JavaScript. Snapshot extraction works on static HTML only.
- It does not authenticate or authorize access to the preview server itself. Run it only on a trusted local interface.
- It does not guarantee the target content is safe to display. Treat previews as untrusted content.

## Safe usage

- Run on localhost only.
- Use a deny list for sites you do not want previewed.
- Treat snapshot expiry as authoritative: do not reuse expired previews as fresh evidence.
- Review the policy report for each preview if you use previews in a security-sensitive workflow.
