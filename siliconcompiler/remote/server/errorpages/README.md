# The error `type` pages

One page per problem `type` in the `v1` API, `<slug>.html`, plus `index.html`
and one stylesheet. Every refusal's `type` is
`https://siliconcompiler.com/server-errors/<slug>`, and RFC 9457 §3.1.1 says
that URI SHOULD dereference to documentation for the type: **this folder is the
set that is deployed there** (surface D158), and `sc-server` serves the same
files at `/server-errors/` on its own host.

🔴 **The registry is normative.** The error type registry -- §7 of crucible's
`orchestration/api/surface.md` -- decides each slug's status, its extension
members and what raises it. Where a page and its registry row disagree, the
page is the bug. The titles are the exception: the pages are where titles are
fixed, and `errors.py` sends them.

## Serving

The `type` URIs carry no `.html`, so the host MUST resolve the extensionless
path — Apache `Options +MultiViews` on the directory, or nginx
`location /server-errors/ { try_files $uri $uri.html $uri/ =404; }`. The
fallback where no rewrite is available is `<slug>/index.html` per type; the
URIs do not change. A file is never renamed without retiring a published URI.

## Writing a page

1. Quote the `title` verbatim. The pages are where titles are fixed; the
   registry does not carry them. `detail` is occurrence prose, never quoted as
   though fixed.
2. Lead with what the client should do, in the `.do` block.
3. End with *What this is not*, naming the confusable neighbour —
   `entitlement-denied` vs `insufficient-scope`, `feature-unsupported` vs
   `not-ready`, `404` vs `409`.
4. The four rows that restate their status — `invalid-request`,
   `method-not-allowed`, `unsupported-media-type`, `not-acceptable` — each say
   an untyped answer is expected, because a proxy or the framework often
   answers first.
5. A slug that replaced older names says which: `limit-exceeded`
   (`quota-exhausted`, `pending-upload-limit`, `concurrent-job-limit`,
   `concurrent-stream-limit`), `session-ended` (`session-revoked`,
   `session-expired`), `not-ready` (`logs-not-ready`), `run-interrupted`
   (`scheduler-lost`), `software-unavailable` and `declared-mismatch`
   (`version-skew`, at create and while staging).
6. A retired slug loses its page and keeps an unlinked row in `index.html`'s
   retired table: `unsatisfiable-request`, `version-skew`,
   `too-many-attempts` and `scheduler-lost`. It is never raised again and
   never reused.

## No JavaScript, and a page cannot show the reader's own error

RFC 9457 gives the occurrence to `instance`, not `type`, and the `type` URI is
identical on every deployment and occurrence. A page documents the type and
tells the reader to quote `trace_id` and `instance` for a refused request, and
the job's `id` for a type that arrives on a job's `error`; rendering the
specific failure is the client's job. One stylesheet, no build step, no external
requests, light and dark.

⚠️ The plans docs link to this folder on GitHub's `server-v1` branch, so those
links resolve only once the branch is pushed.
