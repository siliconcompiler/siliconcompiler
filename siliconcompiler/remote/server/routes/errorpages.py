'''
The error `type` pages, served from this host.

Every refusal's `type` ends in ``/server-errors/<slug>``, and RFC 9457 section
3.1.1 says that URI SHOULD dereference to documentation for the type. The pages
are static; this serves them at that path on this host, so a person holding a
refusal from `sc-server` can read what it means.

Each ``<slug>.html`` is a Jinja template holding only its own text, in the
layout ``_layout.html``. :func:`render` puts the two together, for this route
and for the public site alike::

    python -m siliconcompiler.remote.server.routes.errorpages <outdir>

writes the static folder that is deployed there.

**The `type` in a body does not change.** `sc-server` keeps one host in it,
which a client does not compare, only the slug.

Outside ``/v1`` on purpose: the v1 API claims only ``/v1/`` paths, and a
deployment's own pages need no reservation.
'''

import argparse
import functools
import hashlib
import io
import re
import shutil
import sys

from pathlib import Path

import flask
import jinja2

from siliconcompiler.remote.server.errors import ProblemError

__all__ = ["blueprint", "PAGES", "pages", "render", "write_site"]


blueprint = flask.Blueprint("errorpages", __name__)

PAGES = Path(__file__).resolve().parent.parent / "errorpages"

# A page name, as a `type` URI spells it or as the pages link to each other --
# the slug alone, `<slug>.html`, or the one stylesheet. Anything else is not a
# page, and nothing with a separator in it reaches the filesystem. Nor does an
# underscore: `_layout.html` and its includes are parts of pages, never served.
_NAME = re.compile(r"(?P<stem>[a-z0-9-]+)(?P<ext>\.html|\.css)?")

# The same on every deployment and every day, so a browser may keep them.
_CACHE = "public, max-age=3600"

# The pages' own loader, not the app's: that one serves the portal's templates.
_TEMPLATES = jinja2.Environment(loader=jinja2.FileSystemLoader(PAGES), autoescape=True,
                                trim_blocks=True, keep_trailing_newline=True,
                                undefined=jinja2.StrictUndefined)


def pages() -> list:
    '''Every page's slug, ``index`` included: each ``<slug>.html`` here that
    is not a ``_``-prefixed part of the layout.'''
    return sorted(path.stem for path in PAGES.glob("*.html")
                  if not path.name.startswith("_"))


@functools.cache
def render(slug: str) -> str:
    '''One page, in the layout: what this host serves and a static site
    publishes. Rendered once; the pages do not change while a server runs.'''
    return _TEMPLATES.get_template(f"{slug}.html").render(slug=slug)


@functools.cache
def _served(slug: str) -> tuple:
    '''A page's bytes, its `ETag`, and when it or the layout last changed.'''
    body = render(slug).encode("utf-8")
    parts = [PAGES / f"{slug}.html", *PAGES.glob("_*.html")]
    return body, hashlib.sha256(body).hexdigest(), max(p.stat().st_mtime for p in parts)


def write_site(outdir) -> list:
    '''Render the folder to static HTML: every page as ``<slug>.html``, and
    the stylesheet. Returns the paths written.

    Into an empty folder only, so that a retired type's page cannot outlive
    it in the copy that gets deployed.
    '''
    outdir = Path(outdir)
    if outdir.exists() and any(outdir.iterdir()):
        raise FileExistsError(f"{outdir} is not empty")
    outdir.mkdir(parents=True, exist_ok=True)

    written = []
    for slug in pages():
        path = outdir / f"{slug}.html"
        path.write_text(render(slug), encoding="utf-8")
        written.append(path)
    written.append(Path(shutil.copyfile(PAGES / "style.css", outdir / "style.css")))
    return written


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
        filename = "style.css"
    else:
        filename = f"{stem}.html"

    if not (PAGES / filename).is_file():
        raise ProblemError("not-found", detail="no such error page")

    if filename == "style.css":
        response = flask.send_from_directory(PAGES, filename, mimetype="text/css")
    else:
        # As a file is sent -- its name, `ETag`, `Last-Modified`, and the
        # conditional and range answers -- from the rendered bytes.
        body, etag, modified = _served(stem)
        response = flask.send_file(io.BytesIO(body), mimetype="text/html",
                                   download_name=filename, etag=etag,
                                   last_modified=modified)
    response.headers["Cache-Control"] = _CACHE
    return response


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m siliconcompiler.remote.server.routes.errorpages",
        description="Render the error type pages to a static folder to deploy at "
                    "/server-errors/ on a host.")
    parser.add_argument("outdir", help="an empty or new folder to write the pages into")
    args = parser.parse_args(argv)

    try:
        written = write_site(args.outdir)
    except FileExistsError as e:
        parser.error(str(e))
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
