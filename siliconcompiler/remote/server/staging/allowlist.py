'''
Where this server will fetch a job's sources from.

🔴 **The list decides who fetches, never whether the data arrives** (D128). A
source that is not on it is not refused: the client is asked for it, uploads
it with its own credentials, and the job runs. What the list bounds is the
server making requests on a job's behalf -- the SSRF a job naming any URL would
otherwise be.

An entry may be a glob (D128, profile D30), and every part of a URL is matched
on its own, after the URL is normalised:

==========  ==============================================================
Part        Rule
==========  ==============================================================
scheme      exact, never a glob -- ``http`` for ``https`` is a downgrade
host        exact, or a wildcard as the WHOLE leftmost label
            (``*.zeroasic.com``), compared lowercased. ``*zeroasic.com``
            would admit ``evilzeroasic.com`` and is refused
path        ``*`` matches within one segment, never across ``/``, and the
            entry matches as a prefix at a segment boundary
==========  ==============================================================

🔴 **Before matching**, dot-segments are resolved, an encoded ``/`` is
refused and the default port is dropped: ``github.com/zeroasiccorp/../evil/``
prefix-matches until the ``..`` is resolved.

🔴 **No glob widens the address rule**: a name that resolves to a private,
loopback, link-local or otherwise non-public address is never connected to,
whatever the list says, and every redirect hop is matched again.
'''

import ipaddress
import logging
import posixpath
import re
import socket

from fnmatch import fnmatchcase
from typing import List, NamedTuple, Optional, Sequence, Tuple
from urllib.parse import unquote, urlsplit

__all__ = ["DEFAULT", "Rule", "parse", "check_entries", "normalise",
           "allows", "public_host", "transport"]


logger = logging.getLogger("sc-server")


# SiliconCompiler's GitHub organisation, which is what lambdapdk needs: it
# registers `https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/`
# with its version as the ref, and GitHub redirects archives to codeload --
# KEEPING the owner and repository in the path, so the narrower entry is enough.
# ⚠️ The whole codeload host would admit every public repository's archive.
DEFAULT = ["https://github.com/siliconcompiler/",
           "https://codeload.github.com/siliconcompiler/"]

_DEFAULT_PORTS = {"https": 443, "http": 80}

# Hosting suffixes anyone can publish under. A wildcard over one of these admits
# strangers, so it is allowed and warned about.
_SHARED = ("github.io", "gitlab.io", "pages.dev", "netlify.app", "vercel.app",
           "web.app", "firebaseapp.com", "herokuapp.com", "appspot.com",
           "blogspot.com", "azurewebsites.net", "cloudfront.net",
           "s3.amazonaws.com", "readthedocs.io")

_GLOB = re.compile(r"[*?\[\]]")


class Rule(NamedTuple):
    '''One parsed allowlist entry.'''
    scheme: str
    host: str                   # exact, or "*.suffix"
    port: Optional[int]         # None is the scheme's default
    segments: Tuple[str, ...]   # path segments, each maybe globbed
    text: str


def parse(entry: str) -> Rule:
    '''One entry, refused where no rule can make it safe.

    🔴 Refused when the configuration LOADS, rather than trusting the matcher
    to be careful about an entry it was told to accept: a bare ``*`` host, a
    wildcard anywhere but the whole leftmost label, and a globbed scheme.
    '''
    text = str(entry).strip()
    if "://" not in text:
        raise ValueError(f"allowlist entry {entry!r} names no scheme")

    scheme, rest = text.split("://", 1)
    if _GLOB.search(scheme):
        raise ValueError(f"allowlist entry {entry!r}: the scheme may not be a glob")
    scheme = scheme.lower()
    if scheme not in _DEFAULT_PORTS:
        raise ValueError(f"allowlist entry {entry!r}: only http and https are fetched")

    authority, _, path = rest.partition("/")
    if "@" in authority:
        raise ValueError(f"allowlist entry {entry!r} carries credentials")
    host, _, port_text = authority.partition(":")
    host = host.lower()
    port = int(port_text) if port_text else None
    if port == _DEFAULT_PORTS[scheme]:
        port = None

    if not host or host == "*" or host.startswith("*") and not host.startswith("*."):
        raise ValueError(f"allowlist entry {entry!r}: a host wildcard must be the "
                         "whole leftmost label, as in *.example.com")
    labels = host.split(".")
    if any(_GLOB.search(label) for label in labels[1:]) or \
            (labels[0] != "*" and _GLOB.search(labels[0])):
        raise ValueError(f"allowlist entry {entry!r}: a wildcard may only be the "
                         "whole leftmost label of the host")
    if labels[0] == "*" and len(labels) < 3:
        raise ValueError(f"allowlist entry {entry!r}: a wildcard over a top-level "
                         "domain admits the internet")

    segments = _segments(path)
    if segments is None:
        raise ValueError(f"allowlist entry {entry!r} has a path that does not "
                         "normalise")
    return Rule(scheme, host, port, segments, text)


def check_entries(entries: Sequence[str]) -> List[str]:
    '''Parse every entry, raising on the first unsafe one; return warnings.'''
    warnings = []
    for entry in entries:
        rule = parse(entry)
        if rule.host.startswith("*.") and any(
                rule.host[2:] == shared or rule.host[2:].endswith("." + shared)
                for shared in _SHARED):
            warnings.append(f"allowlist entry {entry!r} is a wildcard over a shared "
                            "hosting suffix, where anyone can publish")
    return warnings


def _segments(path: str) -> Optional[Tuple[str, ...]]:
    '''A URL path as its normalised segments, or None where it is refused.'''
    if re.search(r"%2f|%5c", path, re.IGNORECASE):
        # An encoded separator decodes into a segment boundary a prefix check
        # would not have seen.
        return None
    decoded = unquote(path)
    if "\\" in decoded or "\x00" in decoded:
        return None
    resolved = posixpath.normpath("/" + decoded)
    return tuple(part for part in resolved.split("/") if part)


def normalise(url: str) -> Optional[Tuple[str, str, Optional[int], Tuple[str, ...]]]:
    '''``(scheme, host, port, segments)`` for a URL, or None where it cannot be
    matched safely.'''
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    scheme = transport(parts.scheme)
    if scheme not in _DEFAULT_PORTS or not parts.hostname:
        return None
    if port == _DEFAULT_PORTS[scheme]:
        port = None
    segments = _segments(parts.path or "/")
    if segments is None:
        return None
    return scheme, parts.hostname.lower().rstrip("."), port, segments


def transport(scheme: str) -> str:
    '''The scheme a source is actually fetched over: ``git+https`` is https.'''
    scheme = (scheme or "").lower()
    return scheme[4:] if scheme.startswith("git+") else scheme


def allows(rules: Sequence[Rule], url: str) -> bool:
    '''Whether ``url`` is under one of ``rules``.'''
    found = normalise(url)
    if found is None:
        return False
    scheme, host, port, segments = found

    for rule in rules:
        if rule.scheme != scheme or rule.port != port:
            continue
        if rule.host.startswith("*."):
            # The whole leftmost label and nothing more: `a.zeroasic.com`,
            # never `zeroasic.com` itself and never `evilzeroasic.com`.
            if not host.endswith(rule.host[1:]) or host.count(".") != rule.host.count("."):
                continue
        elif host != rule.host:
            continue
        if len(segments) < len(rule.segments):
            continue
        if all(fnmatchcase(have, want) for have, want in zip(segments, rule.segments)):
            return True
    return False


def public_host(host: str, port: Optional[int] = None) -> bool:
    '''Whether every address ``host`` resolves to is a public one.

    🔴 Never a private, loopback, link-local, multicast, reserved or
    unspecified address -- whatever the allowlist says -- because a name is
    whatever its owner's DNS answers, including 127.0.0.1 and the metadata
    service at 169.254.169.254.
    '''
    try:
        infos = socket.getaddrinfo(host, port or 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return False
    return bool(infos) and _all_public(infos)


def _all_public(infos) -> bool:
    '''Whether every address in ``infos``, `socket.getaddrinfo`'s answer, is
    a public one: :func:`public_host`'s rule, and the envbuild proxy's for the
    connection it then makes to one of those addresses.'''
    for info in infos:
        try:
            address = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if not address.is_global or address.is_multicast:
            return False
    return True
