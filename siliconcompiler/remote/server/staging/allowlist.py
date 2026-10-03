'''
Where this server will fetch a job's sources from.

The list decides who fetches, never whether the data arrives (D128): a source
not on it is uploaded by the client with its own credentials. What it bounds
is the server making requests on a job's behalf, the SSRF.

An entry may be a glob (D128, profile D30), each URL part matched on its own:

==========  ==============================================================
scheme      exact, never a glob: ``http`` for ``https`` is a downgrade
host        exact, or a wildcard as the whole leftmost label
            (``*.zeroasic.com``); ``*zeroasic.com`` is refused
path        ``*`` within one segment; the entry is a segment-boundary prefix
==========  ==============================================================

Before matching, dot-segments are resolved, an encoded ``/`` is refused and
the default port dropped, or ``github.com/zeroasiccorp/../evil/`` would match.
No glob widens the address rule: a non-public address is never connected to.
What a fetch reaches after the named source (redirects, submodules, LFS) is
held to the list's hosts only, not paths (`staging.fetch`).
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


# SiliconCompiler's GitHub organisation, for lambdapdk; GitHub redirects archives
# to codeload. A redirect is held to the host alone.
DEFAULT = ["https://github.com/siliconcompiler/",
           "https://codeload.github.com/siliconcompiler/"]

_DEFAULT_PORTS = {"https": 443, "http": 80}

# Hosting suffixes anyone can publish under: a wildcard over one is warned about.
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
    '''Parse one entry, refusing at load one no rule can make safe.'''
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
        # It would decode into a boundary the prefix check never saw.
        return None
    decoded = unquote(path)
    if "\\" in decoded or "\x00" in decoded:
        return None
    resolved = posixpath.normpath("/" + decoded)
    return tuple(part for part in resolved.split("/") if part)


def normalise(url: str) -> Optional[Tuple[str, str, Optional[int], Tuple[str, ...]]]:
    '''``(scheme, host, port, segments)`` for a URL, or None where unsafe to match.'''
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
            # One whole label: never `zeroasic.com` itself or `evilzeroasic.com`.
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

    Whatever the allowlist says: a name's DNS can answer 127.0.0.1 or the
    metadata service at 169.254.169.254.
    '''
    try:
        infos = socket.getaddrinfo(host, port or 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return False
    return bool(infos) and _all_public(infos)


def _all_public(infos) -> bool:
    '''Whether every `socket.getaddrinfo` address is public; the envbuild proxy's rule too.'''
    for info in infos:
        try:
            address = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if not address.is_global or address.is_multicast:
            return False
    return True
