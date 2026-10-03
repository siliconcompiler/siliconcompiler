import re

from pathlib import Path

import pytest

pytest.importorskip("flask", reason="the server extra is not installed")

from siliconcompiler.remote.server.errors import ERRORS, TYPE_BASE   # noqa: E402
from siliconcompiler.remote.server.routes.errorpages import (       # noqa: E402
    PAGES, help_link, main, pages, render)


# Retired, never raised, and not to be reused. Each has an index row and no page.
RETIRED = ("unsatisfiable-request", "version-skew", "too-many-attempts",
           "scheduler-lost")


# The error `type` pages. RFC 9457 says a `type` URI SHOULD dereference to
# documentation for the type; these are those pages, and this server serves a
# copy of them. What is asserted is that they agree with the registry -- where a
# page and the registry disagree the registry is right and the page is the bug.
# A page is read as it is rendered in the layout, which is what a reader gets.


def read(slug):
    return render(slug)


@pytest.mark.parametrize("slug", sorted(ERRORS))
def test_every_type_has_a_page_that_agrees_with_the_registry(slug):
    error = ERRORS[slug]
    page = read(slug)

    # The title is quoted verbatim, never reworded: it is the same string on
    # every occurrence, and a paraphrase makes the page and the response
    # disagree.
    title = re.search(r'<p class="title">(.*?)</p>', page).group(1)
    assert title == error.title

    assert f'<span class="uri">{TYPE_BASE}/{slug}</span>' in page

    status = re.search(r'<span class="status">(.*?)</span>', page).group(1)
    if error.status is None:
        assert status == "Not an HTTP response"
    else:
        assert status.startswith(f"{error.status} ")

    # Every member the registry makes REQUIRED is named on its page.
    for member in error.members:
        assert f"<code>{member}</code>" in page, member

    # Every page leads with what to do, and names what it is not.
    assert '<div class="do">' in page
    assert "<h2>What this is not</h2>" in page


def test_the_index_lists_every_type():
    index = read("index")

    for slug in ERRORS:
        assert f'href="{slug}.html"' in index, slug
    assert f"All {len(ERRORS)}" in index
    assert len(ERRORS) == 38


@pytest.mark.parametrize("slug", RETIRED)
def test_a_retired_type_has_a_row_and_no_page(slug):
    '''Retired, never raised, and not to be reused: listed, unlinked, and with
    no page to land on.'''
    index = read("index")

    assert slug not in ERRORS
    assert f"<code>{slug}</code>" in index
    assert f'href="{slug}.html"' not in index
    assert not (PAGES / f"{slug}.html").exists()
    for name in pages():
        assert f'href="{slug}.html"' not in read(name), name


def test_nothing_is_fetched_from_anywhere_else():
    '''No script, no remote stylesheet, no remote image: a page is readable
    from a host that reaches nothing.'''
    for name in pages():
        page = read(name)
        assert "<script" not in page, name
        assert not re.search(r'(src|href)="(https?:)?//[^"]*\.(css|js|png|svg|woff2?)"',
                             page), name
        assert '<link rel="stylesheet" href="style.css">' in page, name


def test_the_renamed_types_name_what_they_replaced():
    assert "quota-exhausted" in read("limit-exceeded")
    assert "session-revoked" in read("session-ended")
    assert "logs-not-ready" in read("not-ready")
    assert "scheduler-lost" in read("run-interrupted")
    assert "version-skew" in read("software-unavailable")
    assert "version-skew" in read("declared-mismatch")


@pytest.mark.parametrize("slug", ["invalid-request", "method-not-allowed",
                                  "unsupported-media-type", "not-acceptable"])
def test_the_ones_answered_below_the_handler_say_so(slug):
    '''A reader holding a bare HTML 415 needs that sentence on the page.'''
    assert "An untyped answer is expected here" in read(slug)


def test_the_render_script_writes_every_page():
    '''The folder deployed at the public `type` URIs: every page, the index
    and the stylesheet, as this host serves them -- and nothing else, so a
    retired page cannot ride along.'''
    assert main(["site"]) == 0

    site = Path("site")
    assert sorted(path.name for path in site.iterdir()) == \
        sorted([f"{slug}.html" for slug in ERRORS] + ["index.html", "style.css"])
    for slug in [*ERRORS, "index"]:
        assert (site / f"{slug}.html").read_text() == render(slug), slug
        assert "{%" not in render(slug) and "{{" not in render(slug), slug
    assert (site / "style.css").read_bytes() == (PAGES / "style.css").read_bytes()

    # Into an empty folder only: a stale copy would keep a retired page.
    with pytest.raises(SystemExit):
        main(["site"])


@pytest.mark.parametrize("path", ["/server-errors/entitlement-denied",
                                  "/server-errors/entitlement-denied.html"])
def test_a_page_is_served_by_its_slug_with_or_without_the_extension(server_client,
                                                                    path):
    '''The `type` URIs carry no `.html`, and the pages link to each other
    with it. Both resolve.'''
    response = server_client.get(path)

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert response.data == render("entitlement-denied").encode()
    assert b"Not entitled to this resource" in response.data
    assert "max-age" in response.headers["Cache-Control"]


def test_the_index_and_the_stylesheet(server_client):
    assert server_client.get("/server-errors").status_code == 301
    assert server_client.get("/server-errors").headers["Location"].endswith("/server-errors/")

    index = server_client.get("/server-errors/")
    assert index.status_code == 200
    assert b"entitlement-denied" in index.data

    css = server_client.get("/server-errors/style.css")
    assert css.status_code == 200
    assert css.mimetype == "text/css"


@pytest.mark.parametrize("name", ["no-such-type", "..", "app.py", "entitlement-denied.txt",
                                  "%2e%2e%2fapp.py"])
def test_anything_else_is_not_found(server_client, name):
    assert server_client.get(f"/server-errors/{name}").status_code == 404


def test_the_layout_and_its_includes_are_never_served(server_client):
    '''A `_`-prefixed file is a part of the pages, not one: not served, not
    named by a `Link`, and not published.'''
    parts = sorted(path.stem for path in PAGES.glob("_*.html"))
    assert parts == ["_help", "_layout"]

    for stem in parts:
        assert stem not in pages()
        assert help_link(f"{TYPE_BASE}/{stem}") == ""
        for name in (stem, f"{stem}.html"):
            assert server_client.get(f"/server-errors/{name}").status_code == 404, name


def test_the_type_in_a_body_is_still_the_public_one(server_client):
    '''The pages are a copy, not a second namespace: a client compares `type`
    against a constant, so it is byte-identical on every deployment.'''
    body = server_client.get("/v1/me").get_json()

    assert body["type"].startswith("https://siliconcompiler.com/server-errors/")


def help_of(response):
    found = re.fullmatch(r'<([^>]*)>;\s*rel="help"', response.headers.get("Link", ""))
    return found.group(1) if found else None


def test_a_refusal_names_this_hosts_page_for_it(server_client):
    '''The body's `type` stays the public URI a client compares against; the
    `Link` beside it is the copy that answers here.'''
    response = server_client.get("/v1/me")

    assert response.status_code == 401
    assert help_of(response) == \
        f"/server-errors/{response.get_json()['type'].rsplit('/', 1)[-1]}"
    assert response.get_json()["type"].startswith("https://siliconcompiler.com/")


def test_a_routing_refusal_names_it_too(server_client):
    response = server_client.get("/v1/no-such-endpoint")

    assert response.status_code == 404
    assert help_of(response) == "/server-errors/not-found"


def test_the_link_honours_where_the_server_is_mounted(server_client):
    '''Relative to this host's own root -- never built from `Host`, so a
    request cannot make the server name somewhere else.'''
    response = server_client.get("/v1/me", environ_overrides={"SCRIPT_NAME": "/sc"},
                                 headers={"Host": "attacker.test"})

    assert help_of(response).startswith("/sc/server-errors/")
    assert "attacker" not in response.headers["Link"]


def test_a_failed_jobs_read_names_the_page_for_its_error(
        server, server_client, key, token):
    from conftest import call
    import uuid

    me = call(server_client, key, "GET", "/v1/me", token).get_json()["id"]
    job_id = str(uuid.uuid4())
    server.config["SC_STORE"].execute(
        "INSERT INTO jobs (id, user_id, state, design, jobname, descriptor, "
        "manifest_pdk, error_type) VALUES (?, ?, 'failed', 'gcd', 'job0', '{}', "
        "'none', ?)", (job_id, me, f"{TYPE_BASE}/run-failed"))

    response = call(server_client, key, "GET", f"/v1/jobs/{job_id}", token)

    assert response.status_code == 200
    assert help_of(response) == "/server-errors/run-failed"
