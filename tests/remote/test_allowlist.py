import io
import socket
import tarfile

import pytest

from siliconcompiler.remote.server.staging import allowlist
from siliconcompiler.remote.server.staging.sources import Permanent, SourceStore, Transient


# Where this server fetches a job's sources from (D113, D128, profile D30). The
# list decides who fetches, never whether the data arrives -- so what is tested
# is that it admits exactly what it says and nothing a URL can dress up as it.


def rules(*entries):
    return [allowlist.parse(entry) for entry in entries]


DEFAULT = rules(*allowlist.DEFAULT)


###########################
# The default
###########################

@pytest.mark.parametrize("url", [
    "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/v0.2.22.tar.gz",
    # Where GitHub's archive redirects -- owner and repository kept in the path.
    "https://codeload.github.com/siliconcompiler/lambdapdk/tar.gz/refs/tags/v0.2.22",
    "https://github.com:443/siliconcompiler/lambdapdk/",
    "git+https://github.com/siliconcompiler/lambdapdk.git",
])
def test_the_default_admits_what_lambdapdk_needs(url):
    assert allowlist.allows(DEFAULT, url)


@pytest.mark.parametrize("url", [
    # A string prefix would admit this; a segment boundary does not.
    "https://github.com/siliconcompiler-evil/lambdapdk/archive/x.tar.gz",
    # The whole codeload host would admit every public repository's archive.
    "https://codeload.github.com/someone-else/repo/tar.gz/main",
    # Resolved before matching: prefix-matches until the `..` is gone.
    "https://github.com/siliconcompiler/../evil/x.tar.gz",
    # An encoded separator is refused outright.
    "https://github.com/siliconcompiler%2F..%2Fevil/x.tar.gz",
    # The scheme is exact: http for https is a downgrade.
    "http://github.com/siliconcompiler/lambdapdk/",
    "https://github.com:8443/siliconcompiler/lambdapdk/",
    "ssh://git@github.com/siliconcompiler/lambdapdk.git",
])
def test_the_default_refuses_what_only_looks_like_it(url):
    assert not allowlist.allows(DEFAULT, url)


###########################
# Globs (D128)
###########################

def test_a_host_wildcard_is_the_whole_leftmost_label():
    '''⚠️ `*zeroasic.com` would admit `evilzeroasic.com`, so only `*.` is a
    wildcard -- and it covers one label, not the domain itself.'''
    wild = rules("https://*.zeroasic.com/")

    assert allowlist.allows(wild, "https://git.zeroasic.com/x")
    assert allowlist.allows(wild, "https://GIT.ZeroAsic.com/x")
    assert not allowlist.allows(wild, "https://zeroasic.com/x")
    assert not allowlist.allows(wild, "https://evilzeroasic.com/x")
    assert not allowlist.allows(wild, "https://a.b.zeroasic.com/x")


def test_a_path_star_matches_within_one_segment():
    wild = rules("https://github.com/*/pdk-*/")

    assert allowlist.allows(wild, "https://github.com/zeroasiccorp/pdk-gf180/archive/x")
    assert not allowlist.allows(wild, "https://github.com/a/b/pdk-gf180/")
    assert not allowlist.allows(wild, "https://github.com/zeroasiccorp/other/")


def test_an_org_entry_admits_a_new_repository_under_it():
    '''Prefix matching already does, so the glob is for hosts and the middle of
    paths.'''
    assert allowlist.allows(rules("https://github.com/zeroasiccorp/"),
                            "https://github.com/zeroasiccorp/brand-new-repo/archive/v1.tar.gz")


@pytest.mark.parametrize("entry", [
    "https://*/",                 # a bare `*` host
    "https://*zeroasic.com/",     # a wildcard that is not the whole label
    "https://git.*.com/",         # anywhere but the leftmost label
    "https://*.com/",             # over a top-level domain
    "http*://github.com/",        # a globbed scheme
    "ftp://example.com/",         # a scheme this server does not fetch
    "https://user:pw@example.com/",
])
def test_an_entry_no_rule_can_make_safe_is_refused_at_load(entry):
    with pytest.raises(ValueError):
        allowlist.parse(entry)


def test_a_wildcard_over_shared_hosting_is_warned_about():
    '''Anyone can publish under `*.github.io`.'''
    warnings = allowlist.check_entries(["https://*.github.io/"])

    assert warnings and "shared hosting" in warnings[0]


def test_the_config_refuses_a_bad_entry_when_it_loads(tmp_path):
    import json

    from siliconcompiler.remote.server.config import Config

    (tmp_path / "config.json").write_text(json.dumps({"fetch_allowlist": ["https://*/"]}))
    with pytest.raises(ValueError, match="leftmost label"):
        Config.load(tmp_path)


###########################
# 🔴 No glob widens the address rule
###########################

@pytest.mark.parametrize("address,public", [
    ("127.0.0.1", False), ("10.0.0.5", False), ("192.168.1.1", False),
    ("169.254.169.254", False),   # the metadata service
    ("::1", False), ("fe80::1", False),
    ("140.82.112.3", True),
])
def test_a_name_is_judged_by_what_it_resolves_to(monkeypatch, address, public):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda *a, **k: [(family, socket.SOCK_STREAM, 6, "", (address, 443))])

    assert allowlist.public_host("github.com") is public


###########################
# The fetch
###########################

def tarball(files, top="lambdapdk-0.2.22"):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, body in files.items():
            info = tarfile.TarInfo(f"{top}/{name}" if top else name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


class Response:
    def __init__(self, status, body=b"", location=None):
        self.status_code = status
        self.ok = status < 400
        self.headers = {"Location": location} if location else {}
        self._body = body
        self.content = body

    def iter_content(self, size):
        yield self._body

    def close(self):
        pass


class Session:
    '''Answers by URL, and records every URL asked -- and what was sent.'''

    def __init__(self, answers):
        self.answers = answers
        self.asked = []
        self.headers_sent = []
        self.trust_env = True

    def get(self, url, **kwargs):
        assert kwargs.get("allow_redirects") is False, "every hop must be checked"
        assert self.trust_env is False, "nothing of the environment is sent"
        self.asked.append(url)
        self.headers_sent.append(kwargs.get("headers") or {})
        return self.answers[url]


@pytest.fixture
def through(monkeypatch):
    '''The session SiliconCompiler's https resolver fetches with, faked.'''
    from siliconcompiler.package import https

    def use(session):
        monkeypatch.setattr(https.requests, "Session", lambda: session)
        return session
    return use


SOURCE = "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/"
ARCHIVE = SOURCE + "v0.2.22.tar.gz"
CODELOAD = "https://codeload.github.com/siliconcompiler/lambdapdk/tar.gz/refs/tags/v0.2.22"


@pytest.fixture
def public(monkeypatch):
    monkeypatch.setattr(allowlist, "public_host", lambda host, port=None: True)


def test_a_source_is_fetched_through_its_redirect_and_held(
        tmp_path, public, through, monkeypatch):
    '''By SiliconCompiler's own resolver, so the copy is the user's -- and with
    nothing of this process's sent, however the environment is set up.'''
    monkeypatch.setenv("GITHUB_TOKEN", "a-token-of-this-servers")
    store = SourceStore(tmp_path, DEFAULT)
    session = through(Session({
        ARCHIVE: Response(302, location=CODELOAD),
        CODELOAD: Response(200, tarball({"sky130/lef/a.lef": b"LEF"}))}))

    root = store.fetch(SOURCE, "v0.2.22", timeout=5)

    assert not any("Authorization" in sent for sent in session.headers_sent)

    assert session.asked == [ARCHIVE, CODELOAD]
    # Laid out as SiliconCompiler's resolver lays it out: GitHub's top-level
    # directory flattened away.
    assert (tmp_path / "sources").is_dir()
    assert open(f"{root}/sky130/lef/a.lef").read() == "LEF"
    # And held: the next job is instant.
    assert store.held(SOURCE, "v0.2.22") == root


def test_a_redirect_off_the_list_is_refused(tmp_path, public, through):
    store = SourceStore(tmp_path, DEFAULT)
    through(Session({ARCHIVE: Response(302, location="https://evil.example/x.tar.gz")}))

    with pytest.raises(Permanent, match="allowlist"):
        store.fetch(SOURCE, "v0.2.22", timeout=5)
    assert store.held(SOURCE, "v0.2.22") is None


def test_a_host_resolving_to_a_private_address_is_never_connected_to(
        tmp_path, monkeypatch, through):
    monkeypatch.setattr(allowlist, "public_host", lambda host, port=None: False)
    store = SourceStore(tmp_path, DEFAULT)
    session = through(Session({}))

    with pytest.raises(Permanent, match="public address"):
        store.fetch(SOURCE, "v0.2.22", timeout=5)
    assert session.asked == []


@pytest.mark.parametrize("status,kind", [
    (404, Permanent), (401, Permanent), (403, Permanent),
    (429, Transient), (503, Transient),
])
def test_a_failure_is_permanent_or_transient_by_what_it_means(tmp_path, public, through,
                                                              status, kind):
    '''⚠️ GitHub answers 404 for a private repository a caller cannot see, so
    *not found* is the client's to send; a 429 or a 5xx is retried.'''
    store = SourceStore(tmp_path, DEFAULT)
    through(Session({ARCHIVE: Response(status)}))

    with pytest.raises(kind):
        store.fetch(SOURCE, "v0.2.22", timeout=5)


def test_only_what_the_server_can_fetch_without_a_key_is_allowlisted(tmp_path):
    store = SourceStore(tmp_path, DEFAULT)

    assert store.allowlisted(SOURCE, "v0.2.22")
    assert store.allowlisted("git+https://github.com/siliconcompiler/x.git", "v1")
    assert not store.allowlisted("git+ssh://git@github.com/siliconcompiler/x.git", "v1")
    assert not store.allowlisted("https://gitlab.com/someone/x/", "v1")
