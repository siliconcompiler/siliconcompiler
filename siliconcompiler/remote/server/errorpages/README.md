# The error `type` pages

One page per problem `type` in the `v1` API, `<slug>.html`, plus `index.html`
and one stylesheet. Every refusal's `type` is
`https://siliconcompiler.com/server-errors/<slug>`, and RFC 9457 §3.1.1 says
that URI SHOULD dereference to documentation for the type: **this folder,
rendered, is the set that is deployed there** (surface D158), and `sc-server`
serves the same pages at `/server-errors/` on its own host.

🔴 **The registry is normative.** The error type registry -- §7 of crucible's
`orchestration/api/surface.md` -- decides each slug's status, its extension
members and what raises it. Where a page and its registry row disagree, the
page is the bug. The titles are the exception: the pages are where titles are
fixed, and `errors.py` sends them.

## How the folder works

Each `<slug>.html` is a Jinja template holding only its own text. The
boilerplate is written once:

- `_layout.html` -- the doctype, the head, the header (crumb, slug, title,
  status and URI) and the footer, which every type page extends;
- `_help.html` -- the *Getting help with your specific failure* block, for a
  type a request is refused with.

A `_`-prefixed file is a part of the pages, never a page: the route's name
pattern refuses the underscore, and the render below skips it. `index.html` has
its own header and footer, so it does not extend the layout.

`sc-server` renders a page on its first request and keeps it
(`routes/errorpages.py`). The public site is the rendered folder.

## Publishing

```sh
python -m siliconcompiler.remote.server.routes.errorpages <outdir>
```

writes every page as `<slug>.html`, `index.html` and `style.css` into
`<outdir>`, which must be empty or new, so a retired page cannot ride along.
Deploy `<outdir>` as the whole of `/server-errors/` -- never this folder, whose
pages are templates. It needs the server extra installed.

## Serving

The `type` URIs carry no `.html`, so the host MUST resolve the extensionless
path — Apache `Options +MultiViews` on the directory, or nginx
`location /server-errors/ { try_files $uri $uri.html $uri/ =404; }`. The
fallback where no rewrite is available is `<slug>/index.html` per type; the
URIs do not change. A file is never renamed without retiring a published URI.

## Writing a page

A page is its variables and its `main`:

```html
{% extends "_layout.html" %}
{% set title = "Not found" %}
{% set status = "404 Not Found" %}
{% set description = "One sentence, for the meta description." %}
{% block main %}
<p>Its own prose, as HTML.</p>
...
{% include "_help.html" %}

<h2>What this is not</h2>
...
{% endblock %}
```

The slug is the file name. `title`, `status` and `description` are plain text,
escaped as they are rendered: write the character, never an entity. A type that
arrives only on a job's `error` has the status `Not an HTTP response`; one that
also arrives there sets `also_on_a_job = true`, and `_help.html` adds the
job's `id`. A page whose help differs writes its own block where the include
would go. In the prose, `{{`, `{%` and `{#` are Jinja's, never literal text.

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
specific failure is the client's job. One stylesheet, no external requests,
light and dark; the one build step is the render, and only publishing needs it.

⚠️ The plans docs link to this folder on GitHub's `server-v1` branch, not on
`main`, so those links stop resolving once that branch is deleted.
