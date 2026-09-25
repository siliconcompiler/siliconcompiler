'''
The error `type` pages, served from this host.

Every refusal's `type` is ``https://siliconcompiler.com/server-errors/<slug>``,
and RFC 9457 §3.1.1 says that URI SHOULD dereference to documentation for the
type. The pages are static and identical on every deployment; this serves the
same files at the same path on this host, so a person holding a refusal from
`sc-server` can read what it means without the public site.

🔴 **The `type` in a body does not change.** It is byte-identical on every
deployment because a client compares it against a constant; this is a copy of
the pages, not a second namespace.

⚠️ Outside ``/v1`` on purpose: the contract claims only ``/v1/`` paths, and a
deployment's own pages need no reservation.
'''

import re

from pathlib import Path

import flask

from siliconcompiler.remote.server.errors import ProblemError

__all__ = ["blueprint", "PAGES", "help_link"]


blueprint = flask.Blueprint("errorpages", __name__)

PAGES = Path(__file__).resolve().parent.parent / "errorpages"

# A page name, as a `type` URI spells it or as the pages link to each other --
# the slug alone, `<slug>.html`, or the one stylesheet. Anything else is not a
# page, and nothing with a separator in it reaches the filesystem.
_NAME = re.compile(r"(?P<stem>[a-z0-9-]+)(?P<ext>\.html|\.css)?")

# The same on every deployment and every day, so a browser may keep them.
_CACHE = "public, max-age=3600"


def help_link(type_uri) -> str:
    '''The `Link` header value naming this host's page for a `type`, or ''.

    ``Link: </server-errors/<slug>>; rel="help"`` (RFC 8288), sent beside a
    refusal so a client can show the page that actually answers here, while the
    body's `type` stays the public URI it compares against.

    ⚠️ A reference relative to this host -- its mount point included -- and
    never built from `Host` or `X-Forwarded-Host`. The client resolves it
    against the URL it called, which is the one origin it already trusts.
    '''
    if not isinstance(type_uri, str) or "/server-errors/" not in type_uri:
        return ""
    slug = type_uri.rstrip("/").rsplit("/", 1)[-1]
    if not _NAME.fullmatch(slug) or not (PAGES / f"{slug}.html").is_file():
        return ""
    root = flask.request.script_root if flask.has_request_context() else ""
    return f'<{root}/server-errors/{slug}>; rel="help"'


@blueprint.route("/server-errors", methods=["GET"])
def root():
    # With the slash, so that the pages' relative links resolve under it.
    return flask.redirect(flask.url_for("errorpages.page"), code=301)


@blueprint.route("/server-errors/", methods=["GET"])
@blueprint.route("/server-errors/<name>", methods=["GET"])
def page(name: str = "index"):
    '''One page, by its slug -- extensionless, as the `type` URIs are.'''
    found = _NAME.fullmatch(name)
    if found is None:
        raise ProblemError("not-found", detail="no such error page")

    stem, ext = found.group("stem"), found.group("ext")
    if ext == ".css" or (ext is None and stem == "style"):
        filename, mimetype = "style.css", "text/css"
    else:
        filename, mimetype = f"{stem}.html", "text/html"

    if not (PAGES / filename).is_file():
        raise ProblemError("not-found", detail="no such error page")

    response = flask.send_from_directory(PAGES, filename, mimetype=mimetype)
    response.headers["Cache-Control"] = _CACHE
    return response
