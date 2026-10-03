import socket

import pytest

from siliconcompiler.remote.server.staging import allowlist
from siliconcompiler.remote.server.staging.sources import SourceStore


# Where this server fetches a job's sources from (D113, D128, profile D30): the
# list admits exactly what it says and nothing a URL can dress up as it.


def rules(*entries):
    return [allowlist.parse(entry) for entry in entries]


DEFAULT = rules(*allowlist.DEFAULT)


@pytest.mark.parametrize("url,allowed", [
    ("https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/v0.2.22.tar.gz", True),
    # Where GitHub's archive redirects -- owner and repository kept in the path.
    ("https://codeload.github.com/siliconcompiler/lambdapdk/tar.gz/refs/tags/v0.2.22", True),
    ("https://github.com:443/siliconcompiler/lambdapdk/", True),
    ("git+https://github.com/siliconcompiler/lambdapdk.git", True),
    # A string prefix would admit this; a segment boundary does not.
    ("https://github.com/siliconcompiler-evil/lambdapdk/archive/x.tar.gz", False),
    # The whole codeload host would admit every public repository's archive.
    ("https://codeload.github.com/someone-else/repo/tar.gz/main", False),
    # Resolved before matching; an encoded separator is refused outright.
    ("https://github.com/siliconcompiler/../evil/x.tar.gz", False),
    ("https://github.com/siliconcompiler%2F..%2Fevil/x.tar.gz", False),
    # The scheme and port are exact: http for https is a downgrade.
    ("http://github.com/siliconcompiler/lambdapdk/", False),
    ("https://github.com:8443/siliconcompiler/lambdapdk/", False),
    ("ssh://git@github.com/siliconcompiler/lambdapdk.git", False),
])
def test_the_default_admits_what_lambdapdk_needs_and_nothing_like_it(url, allowed):
    assert allowlist.allows(DEFAULT, url) is allowed


@pytest.mark.parametrize("entry,url,allowed", [
    # ⚠️ Only `*.` is a host wildcard, covering one label and not the domain.
    ("https://*.zeroasic.com/", "https://git.zeroasic.com/x", True),
    ("https://*.zeroasic.com/", "https://GIT.ZeroAsic.com/x", True),
    ("https://*.zeroasic.com/", "https://zeroasic.com/x", False),
    ("https://*.zeroasic.com/", "https://evilzeroasic.com/x", False),
    ("https://*.zeroasic.com/", "https://a.b.zeroasic.com/x", False),
    # A path star matches within one segment.
    ("https://github.com/*/pdk-*/", "https://github.com/zeroasiccorp/pdk-gf180/archive/x", True),
    ("https://github.com/*/pdk-*/", "https://github.com/a/b/pdk-gf180/", False),
    ("https://github.com/*/pdk-*/", "https://github.com/zeroasiccorp/other/", False),
    # Prefix matching already admits a new repository under an org entry.
    ("https://github.com/zeroasiccorp/",
     "https://github.com/zeroasiccorp/brand-new-repo/archive/v1.tar.gz", True),
])
def test_a_glob_matches_what_it_says(entry, url, allowed):
    '''Globs (D128).'''
    assert allowlist.allows(rules(entry), url) is allowed


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


@pytest.mark.parametrize("address,public", [
    ("127.0.0.1", False), ("10.0.0.5", False), ("192.168.1.1", False),
    ("169.254.169.254", False),   # the metadata service
    ("::1", False), ("fe80::1", False),
    ("140.82.112.3", True),
])
def test_a_name_is_judged_by_what_it_resolves_to(monkeypatch, address, public):
    '''🔴 No glob widens the address rule.'''
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda *a, **k: [(family, socket.SOCK_STREAM, 6, "", (address, 443))])

    assert allowlist.public_host("github.com") is public


def test_only_what_the_server_can_fetch_without_a_key_is_allowlisted(tmp_path):
    store = SourceStore(tmp_path, DEFAULT)

    assert store.allowlisted("https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
                             "v0.2.22")
    assert store.allowlisted("git+https://github.com/siliconcompiler/x.git", "v1")
    assert not store.allowlisted("git+ssh://git@github.com/siliconcompiler/x.git", "v1")
    assert not store.allowlisted("https://gitlab.com/someone/x/", "v1")
