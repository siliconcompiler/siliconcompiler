import functools
import http.server
import io
import os
import tarfile
import threading
import time

import pytest
import requests

from siliconcompiler.package.cache import DataSourceUnavailableError
from siliconcompiler.remote.server.packages import envbuild
from siliconcompiler.remote.server.staging import allowlist, fetch, sources
from siliconcompiler.remote.server.staging.sources import Permanent, SourceStore, Transient
from siliconcompiler.utils import UnsafeArchiveError


# A source is fetched by SiliconCompiler's own resolver, unchanged, in a
# process of its own: nothing of this process's to send, and one way out, the
# proxy. These run that process for real, against servers on this machine --
# which the proxy refuses as non-public unless a test lets it through.


def tarball(files, top="ip-v1"):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, body in files.items():
            info = tarfile.TarInfo(f"{top}/{name}")
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


class Site:
    '''A web server on loopback that records every request: answers from
    ``routes`` by path, or serves ``directory``.'''

    def __init__(self, routes=None, directory=None):
        self.routes = routes or {}
        self.asked = []
        site = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                site.asked.append((self.path, dict(self.headers)))
                if directory is not None:
                    return super().do_GET()
                answer = site.routes.get(self.path, (404, b"", {}))
                status, body, headers = answer() if callable(answer) else answer
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        handler = functools.partial(Handler, directory=directory) if directory else Handler
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def site():
    made = []

    def make(routes=None, directory=None):
        made.append(Site(routes, directory))
        return made[-1]
    yield make
    for one in made:
        one.close()


@pytest.fixture
def loopback(monkeypatch):
    '''Let the proxy connect to this machine, as it never does for a real
    source: every other rule still applies.'''
    monkeypatch.setattr(envbuild.Proxy, "_public_only", lambda self, rules, url: False)


def store_for(web):
    return SourceStore(os.getcwd(), [allowlist.parse(f"{web.url}/")])


def test_a_source_is_fetched_and_held_with_nothing_of_this_process_sent(
        site, loopback, monkeypatch):
    '''🔴 By SiliconCompiler's own resolver, so the copy is the user's -- and
    with no token of this process's, whatever its environment holds.'''
    monkeypatch.setenv("GITHUB_TOKEN", "a-token-of-this-servers")
    monkeypatch.setenv("GIT_TOKEN", "a-token-of-this-servers")
    web = site({"/ip/v1.tar.gz": (200, tarball({"lef/a.lef": b"LEF"}), {})})
    store = store_for(web)

    root = store.fetch(f"{web.url}/ip/", "v1", timeout=60)

    assert open(f"{root}/ip-v1/lef/a.lef").read() == "LEF"
    assert [path for path, _ in web.asked] == ["/ip/v1.tar.gz"]
    assert not any("Authorization" in headers for _, headers in web.asked)
    # Held, and holding the copy and its record alone.
    assert store.held(f"{web.url}/ip/", "v1") == root
    assert sorted(os.listdir(os.path.dirname(root))) == [".complete", "data"]


def test_git_reaches_nothing_but_through_the_proxy(site):
    '''🔴 git is held by the proxy too: a clone of a host the proxy will not
    connect to is refused there, never made directly.'''
    web = site()
    https = web.url.replace("http://", "https://")
    store = SourceStore(os.getcwd(), [allowlist.parse(f"{https}/")])

    with pytest.raises(Permanent, match="127.0.0.1"):
        store.fetch(f"git+{https}/ip.git", "v1", timeout=60)


def test_a_redirect_off_the_list_is_refused(site, loopback):
    web = site()
    elsewhere = web.url.replace("127.0.0.1", "localhost")
    web.routes["/ip/v1.tar.gz"] = (302, b"", {"Location": f"{elsewhere}/x"})
    store = store_for(web)

    with pytest.raises(Permanent, match="localhost"):
        store.fetch(f"{web.url}/ip/", "v1", timeout=60)
    assert store.held(f"{web.url}/ip/", "v1") is None


def test_a_host_resolving_to_a_private_address_is_never_connected_to(site):
    web = site({"/ip/v1.tar.gz": (200, tarball({"a": b"a"}), {})})

    with pytest.raises(Permanent, match="not a public address"):
        store_for(web).fetch(f"{web.url}/ip/", "v1", timeout=60)
    assert web.asked == []


@pytest.mark.parametrize("status,kind", [
    (404, Permanent), (401, Permanent), (403, Permanent),
    (429, Transient), (503, Transient),
])
def test_a_failure_is_permanent_or_transient_by_what_it_means(site, loopback, status, kind):
    '''⚠️ GitHub answers 404 for a private repository a caller cannot see, so
    *not found* is the client's to send; a 429 or a 5xx is retried.'''
    web = site({"/ip/v1.tar.gz": (status, b"", {})})

    with pytest.raises(kind, match=f"answered {status}"):
        store_for(web).fetch(f"{web.url}/ip/", "v1", timeout=60)


def test_a_fetch_past_its_time_is_killed_and_retried(site, loopback):
    def slow():
        time.sleep(10)
        return 200, b"", {}
    web = site({"/ip/v1.tar.gz": slow})

    started = time.monotonic()
    with pytest.raises(Transient, match="ran past its 3s"):
        store_for(web).fetch(f"{web.url}/ip/", "v1", timeout=3)
    assert time.monotonic() - started < 9


def test_a_source_heavier_than_the_ceiling_is_refused(site, loopback, monkeypatch):
    monkeypatch.setattr(sources, "MAX_SOURCE_BYTES", 64 * 1024)
    web = site({"/ip/v1.tar.gz": (200, os.urandom(1024 * 1024), {})})

    with pytest.raises(Permanent, match="larger than 65536 bytes"):
        store_for(web).fetch(f"{web.url}/ip/", "v1", timeout=60)


@pytest.mark.parametrize("error,permanent", [
    (DataSourceUnavailableError("Failed to download x. Status code: 404"), True),
    (FileNotFoundError("Failed to download x. Status code: 403"), True),
    (FileNotFoundError("Failed to download x. Status code: 429"), False),
    (FileNotFoundError("Failed to download x. Status code: 502"), False),
    (requests.ConnectionError("refused"), False),
    (RuntimeError("fatal: could not read Username for 'https://x': terminal prompts disabled"),
     True),
    (TypeError("File is not a valid tar or zip archive."), True),
    (UnsafeArchiveError("a member escapes"), True),
    (RuntimeError("something else"), False),
])
def test_a_resolvers_failure_is_classified_by_what_it_means(error, permanent):
    assert fetch.classify(error)["permanent"] is permanent


def test_the_status_is_read_as_the_https_resolver_reports_it(monkeypatch):
    '''The classification reads the status out of the resolver's own message:
    this breaks first if that message changes.'''
    def answer(*args, **kwargs):
        response = requests.Response()
        response.status_code = 503
        return response
    monkeypatch.setattr(requests, "get", answer)

    with pytest.raises(FileNotFoundError) as raised:
        fetch.resolve("https://example.com/ip/", "v1", os.path.abspath("cache"))
    assert fetch.classify(raised.value) == {"permanent": False,
                                            "message": "the source answered 503"}
