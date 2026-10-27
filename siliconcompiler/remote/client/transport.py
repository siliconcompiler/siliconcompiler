'''
The one request path: every API request goes through :meth:`Transport.request`,
so none forgets its token, DPoP proof, ``User-Agent`` or operator headers.

Two error shapes: OAuth refusals at ``/v1/auth/token`` and ``/v1/auth/device``
are ``{"error", "error_description", "reason"}``, all else problem+json, so the
``Content-Type`` is read first.

The HTTP library never follows a redirect: it would carry the session's
headers and proof along. A ``303`` is followed by hand without them; any other
redirect on a ``/v1`` path is the edge refusing.
'''

import email.utils
import logging
import re
import ssl
import threading
import time

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from urllib.parse import urljoin, urlsplit

import requests
import requests.auth

from siliconcompiler import __version__
from siliconcompiler.remote import dpop
from siliconcompiler.remote.client.errors import (
    TYPE_BASE, RemoteError, RemoteTimeout, ServerProblem, SessionEnded, _slug, clean)
from siliconcompiler.remote.client.identity import device_fingerprint
from siliconcompiler.utils.units import format_duration

__all__ = ["Transport", "join_url", "normalize_server", "EdgeRefused",
           "CertificateRefused", "OAuthRefusal", "USER_AGENT", "link", "retrying", "wait_out"]


logger = logging.getLogger(__name__)

# Low on purpose: each retry follows the server's exact instruction, so a second
# failure means it did not help.
MAX_RETRIES = 2

# `Retry-After` waits honoured before giving up.
MAX_WAITS = 10

TIMEOUT_SECONDS = 30

# How long a live log may be silent: an edge drops a connection idle for 100
# seconds, so the server's keep-alive comments come sooner and the client waits longer.
STREAM_READ_SECONDS = 120


# Stable and product-named, so an edge can allowlist it.
USER_AGENT = f"siliconcompiler/{__version__}"

# The grants of a deployment that authenticates nobody: a self-asserted login and its refresh.
_UNAUTHENTICATED_GRANTS = {"client_credentials", "refresh_token"}

# The `WWW-Authenticate` errors a 401 carries; any other is surfaced as it is.
_CHALLENGES = ("invalid_token", "invalid_dpop_proof", "use_dpop_nonce")


class _NoEnvironmentCredential(requests.auth.AuthBase):
    '''A session `auth` that adds nothing: requests sends only what was set.

    Without it requests fills `auth` from `~/.netrc`, replacing the DPoP
    `Authorization` everywhere. `trust_env` stays on for proxies and CA bundles.
    Holds only with `allow_redirects=False`: `rebuild_auth` rereads netrc.
    '''

    def __call__(self, r):
        return r


class EdgeRefused(RemoteError):
    '''An intermediary in front of the API refused the request: HTML, or a
    redirect to an identity provider, on a `/v1` path. Never an API failure.'''

    def __init__(self, origin: str):
        super().__init__(
            f"the edge refused this request: check the Cloudflare credentials -- the "
            f"operator-configured headers for {origin} (sc-config remote header set). This is an "
            "intermediary in front of the server, not the API")


class CertificateRefused(RemoteError):
    '''The server's TLS certificate could not be verified.'''

    def __init__(self, origin: str, why: str):
        super().__init__(
            f"{origin}'s certificate could not be verified ({why}). If an authority of "
            "your own signs it, import that authority's certificate with sc-config "
            "remote import-cert <file>, then run sc-config remote configure again to "
            "choose it")


class OAuthRefusal(RemoteError):
    '''What OAuth processing refused at `/v1/auth/token` or `/v1/auth/device`.'''

    def __init__(self, error: str, description: Optional[str] = None,
                 reason: Optional[str] = None, status: int = 400):
        self.error = error
        self.description = description
        self.reason = reason
        self.status = status
        said = f"{error}" + (f" ({reason})" if reason else "")
        super().__init__(f"the server refused the login: {said}"
                         + (f": {clean(description)}" if description else ""))


def join_url(base: str, path: str = "") -> str:
    '''Join a path onto a base URL, keeping the base's path: ``urljoin`` drops ``/v1``.'''
    if not path:
        return base.rstrip("/")
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def normalize_server(address: str, port: Optional[int] = None) -> str:
    '''The base URL for a server address; the scheme comes from it, never the port.
    Any username and password in it are dropped: the key is the credential.'''
    from urllib3.exceptions import LocationParseError
    from urllib3.util import Url, parse_url

    address = address.strip()
    if "://" not in address:
        address = f"https://{address}"

    try:
        parts = parse_url(address)
    except LocationParseError as e:
        raise RemoteError(f"{address} is not a server address: {e}") from None

    # A port in the address wins over one given beside it; an IPv6 host keeps
    # its brackets.
    return Url(scheme=parts.scheme, host=parts.host,
               port=parts.port if parts.port is not None else port,
               path=(parts.path or "").rstrip("/") or "/v1").url


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def authenticates(grants) -> bool:
    '''Whether a deployment offering ``grants`` authenticates: any grant beyond
    `client_credentials` and its refresh does, an unknown one included.'''
    return "client_credentials" not in grants or bool(set(grants) - _UNAUTHENTICATED_GRANTS)


class Transport:
    '''Signs, sends, retries and renders. Holds the key and the tokens; knows
    nothing about jobs.'''

    def __init__(self, base_url: str, key, credentials,
                 relogin: Callable[[Optional[str]], None], *,
                 logger: logging.Logger = logger, trades: bool = False,
                 verify: Optional[str] = None):
        '''``relogin(reason)`` gets a session by logging in. ``trades``: a CI
        credential, which trades for each token and never refreshes.'''
        self.base_url = base_url.rstrip("/")
        self._key = key
        self._credentials = credentials
        self._relogin = relogin
        self._logger = logger
        self._trades = trades
        self._session = requests.Session()
        # Never netrc, never a credential from the environment.
        self._session.auth = _NoEnvironmentCredential()
        if verify:
            # A REQUESTS_CA_BUNDLE in the environment still wins: requests applies it first.
            self._session.verify = verify

        self._access_token: Optional[str] = None
        self._access_expires: Optional[float] = None

        # One nonce per origin: the stream host's is not the API's.
        self._nonces: Dict[str, str] = {}

        # Server clock minus ours, once a proof was refused for its time.
        self._clock_offset = 0.0

        # One renewal at a time: threads share a client, and one that waited
        # finds the token another got rather than spend a rotated refresh token.
        self._renewing = threading.RLock()
        self._deprecation_warned = False
        self._published: Optional[Dict[str, Any]] = None

        # Where this server serves its error `type` pages, from `Link: rel="help"`.
        self.help_pages: Optional[str] = None

    @property
    def access_token(self) -> Optional[str]:
        if self._access_expires is not None and time.monotonic() >= self._access_expires:
            return None
        return self._access_token

    def set_tokens(self, access_token: Optional[str],
                   expires_in: Optional[int] = None) -> None:
        '''Hold an access token until its ``expires_in``; the refresh token stays in the store.'''
        self._access_token = access_token
        self._access_expires = (time.monotonic() + max(0, int(expires_in) - 5)
                                if access_token and expires_in else None)

    def now(self) -> float:
        '''This machine's time, corrected by the server's once a proof was refused for it.'''
        return time.time() + self._clock_offset

    def url(self, path: str = "") -> str:
        return join_url(self.base_url, path)

    @property
    def api_origin(self) -> str:
        return origin_of(self.base_url)

    def operator_headers(self, url: str) -> Dict[str, str]:
        '''The operator headers a request to ``url`` carries.

        Only to the API's origin, whatever a redirect names.
        '''
        if origin_of(url) != self.api_origin:
            return {}
        return self._credentials.headers()

    def request(self, method: str, path: str, *,
                authenticated: bool = True,
                data: Any = None,
                json_body: Any = None,
                params: Optional[Dict[str, Any]] = None,
                headers: Optional[Dict[str, str]] = None,
                expect_redirect: bool = False,
                stream: bool = False,
                oauth: bool = False,
                absolute: bool = False,
                renew: bool = True) -> requests.Response:
        '''Send one request, proof and all.

        ``data`` may be a function, called for each attempt. ``expect_redirect``:
        the caller follows a ``303`` itself; any other redirect is the edge.
        ``absolute``: ``path`` is a whole URL the server gave. ``renew=False``: a
        `401` is the answer, with no refresh or login.
        '''
        url = path if absolute else self.url(path)
        keyed = _keyed(method, headers)
        attempts = waits = 0
        nonced = False

        while True:
            if authenticated and renew and self.access_token is None:
                # Renew before the request rather than take a 401.
                self.renew()

            sent = {"User-Agent": USER_AGENT, **self.operator_headers(url), **(headers or {})}
            token = self._access_token if authenticated else None

            if authenticated:
                if token is None:
                    raise RemoteError(
                        "not logged in to this server: run sc-config remote configure")
                sent["Authorization"] = f"DPoP {token}"

            # A fresh proof per request, retries included: the server remembers its `jti`.
            sent["DPoP"] = dpop.sign_proof(
                self._key, method, url, access_token=token,
                nonce=self._nonces.get(origin_of(url)),
                iat=int(self.now()))

            try:
                response = self._session.request(
                    method, url, data=data() if callable(data) else data, json=json_body,
                    params=params, headers=sent, timeout=TIMEOUT_SECONDS,
                    allow_redirects=False, stream=stream)
            except (requests.Timeout, requests.ConnectionError) as e:
                if _unverified(e):
                    # Never retried: the same certificate is refused the same way.
                    raise CertificateRefused(self.api_origin, _why(e)) from None
                # A lost answer: safe to resend, since a refresh in the grace window
                # gets the same pair and a keyed create or submit replays.
                if attempts < MAX_RETRIES and (isinstance(e, requests.Timeout) or oauth
                                               or keyed):
                    time.sleep(2 ** attempts)
                    attempts += 1
                    continue
                if isinstance(e, requests.Timeout):
                    raise RemoteTimeout(f"{self.base_url} did not answer") from None
                raise RemoteError(f"could not reach {self.base_url}: {_why(e)}") from None
            except requests.RequestException as e:
                raise RemoteError(f"could not reach {self.base_url}: {_why(e)}") from None

            offered = response.headers.get("DPoP-Nonce")
            if offered:
                self._nonces[origin_of(url)] = offered

            helped = help_url(response)
            if helped:
                self.help_pages = helped.rsplit("/", 1)[0] + "/"

            self._notice_deprecation(response)

            status = response.status_code
            if 300 <= status < 400:
                if expect_redirect and status == 303:
                    return response
                raise EdgeRefused(self.api_origin)

            # HTML refusing access, or answering in the API's place, is the edge; any
            # other HTML failure is untyped and acted on by its status.
            if (response.headers.get("Content-Type") or "").lower().startswith("text/html") \
                    and (status in (401, 403) or (status < 300 and status != 204)):
                raise EdgeRefused(self.api_origin)

            if status < 400:
                return response

            # Act on a refusal by its slug, not its status alone: refreshing on every
            # 401 loops on a nonce challenge, and on `session-ended` on a dead session.
            # At the OAuth endpoints only the OAuth shape is read for `error`; a
            # problem, or an intermediary's page, is handled as any other.
            body = _json(response) if oauth and not _is_problem(response) else None
            refusal = body if isinstance(body, dict) and isinstance(body.get("error"), str) \
                else None
            problem = _problem_body(response)
            slug = _slug(problem)
            challenge = response.headers.get("WWW-Authenticate", "")

            if refusal:
                needs_nonce = refusal["error"] == "use_dpop_nonce"
                bad_proof = refusal["error"] == "invalid_dpop_proof"
            else:
                needs_nonce = status == 401 and (
                    slug == "dpop-nonce-required" or "use_dpop_nonce" in challenge)
                bad_proof = status == 401 and slug == "invalid-dpop-proof"

            if attempts < MAX_RETRIES:
                # The nonce once: a second challenge is the answer.
                if needs_nonce and not nonced:
                    nonced = True
                    attempts += 1
                    continue
                if bad_proof and self._correct_clock(response):
                    attempts += 1
                    continue

            if refusal:
                raise OAuthRefusal(refusal["error"], refusal.get("error_description"),
                                   refusal.get("reason"), status)

            # Once per request, and only an AUTHENTICATED one: an unauthenticated
            # refresh renewing on its own 401 would loop.
            # The header alone says `invalid_token` where no handler typed the body.
            expired = slug == "invalid-token" or (
                slug is None and _challenge(response) == "invalid_token")
            if status == 401 and attempts < MAX_RETRIES and authenticated and renew and (
                    expired or slug == "session-ended"):
                self.renew(refused=token, ended=(problem.get("reason") or "revoked")
                           if slug == "session-ended" else None)
                renew = False
                attempts += 1
                continue

            # Waited out only where the server said how long and the answer means *later*.
            # An untyped failure goes by its status: a 429 was not acted on, and a
            # 5xx may have been, so only a read or a keyed write is repeated.
            untyped = slug is None
            wait = _retry_after(response)
            if wait is not None and waits < MAX_WAITS and (
                    slug == "rate-limited"
                    or (slug == "job-state-conflict" and problem.get("reason") == "in_progress")
                    or (untyped and status == 429)
                    or (untyped and status >= 500 and (method in ("GET", "HEAD") or keyed))):
                time.sleep(wait)
                waits += 1
                continue
            # A keyed create or submit replays, so an untyped 5xx is retried even with
            # no wait named. A typed one, `feature-unsupported`, is the answer.
            if untyped and status >= 500 and wait is None and attempts < MAX_RETRIES and keyed:
                time.sleep(2 ** attempts)
                attempts += 1
                continue

            if slug == "session-ended":
                raise SessionEnded(problem, status, help_url=help_url(response))

            raise ServerProblem(problem, status, help_url=help_url(response),
                                next_step=self._clock_advice(response)
                                if slug == "invalid-dpop-proof" else _unknown_challenge(response),
                                retry_after=wait)

    def renew(self, refused: Optional[str] = None, ended: Optional[str] = None) -> None:
        '''Get an access token: refresh, else log in; a CI credential trades.

        ``refused`` is the token a `401` refused, dropped only while still held;
        ``ended`` is why its session is over, so a login replaces it and a
        refresh never does. A thread that waited here keeps the token another got.
        Refreshing comes first: each `client_credentials` login mints a new token
        family, so logging in per command leaves live sessions behind.
        '''
        with self._renewing:
            if refused is not None and self._access_token == refused:
                self.set_tokens(None)
                if ended:
                    self._credentials.forget_tokens()
                    self._relogin(ended)
                    return
            if self.access_token is not None:
                return
            reason = None
            if not self._trades:
                try:
                    if self.refresh():
                        return
                except SessionEnded as e:
                    reason = e.reason
            self._relogin(reason)

    def _correct_clock(self, response) -> bool:
        '''Correct later proofs by the server's `Date`, once, saying so.'''
        skew = _skew(response)
        if skew is None or abs(skew) <= dpop.PROOF_LIFETIME_SECONDS or self._clock_offset:
            return False
        self._clock_offset = -skew
        self._logger.warning(
            f"{_skew_phrase(skew)}; proofs are being corrected for it. "
            "Turn on time synchronization.")
        return True

    @staticmethod
    def _clock_advice(response) -> Optional[str]:
        skew = _skew(response)
        if skew is None or abs(skew) <= dpop.PROOF_LIFETIME_SECONDS:
            return None
        return (f"{_skew_phrase(skew)}, and a proof is accepted only within "
                f"{dpop.PROOF_LIFETIME_SECONDS} seconds of it. Correct the "
                "clock -- turn on time synchronization -- and try again.")

    def _notice_deprecation(self, response) -> None:
        '''Once per session: a `Deprecation` header, with its `Sunset` date.'''
        if self._deprecation_warned or "Deprecation" not in response.headers:
            return
        self._deprecation_warned = True
        sunset = response.headers.get("Sunset")
        self._logger.warning("This server says the API this client uses is deprecated"
                             + (f", and it goes away on {clean(sunset)}" if sunset else "")
                             + ". Upgrade SiliconCompiler.")

    def put_object(self, url: str, headers: Dict[str, str], path) -> None:
        '''Send the bytes to wherever the grant points.

        Not through :meth:`request`: a presigned URL carries its own credential,
        so it gets no `Authorization`, proof, or off-origin operator header.
        '''
        self._check_scheme(url)
        sent = {"User-Agent": USER_AGENT, **self.operator_headers(url),
                **dict(headers or {})}
        with open(path, "rb") as f:
            try:
                response = self._session.put(
                    url, data=f, headers=sent, timeout=TIMEOUT_SECONDS,
                    allow_redirects=False)
            except requests.RequestException as e:
                # The URL is a capability: never printed.
                raise RemoteError(f"could not upload the archive: {_why(e)}") from None

        if 300 <= response.status_code < 400:
            raise RemoteError("the storage the server named redirected the upload, which "
                              "this client does not follow: the archive was not stored")
        if response.status_code >= 400:
            raise ServerProblem(_problem_body(response), response.status_code)

    def _check_scheme(self, target: str) -> None:
        '''Where an answer sends the client: never from https to http, and never
        to any other scheme.'''
        ours, theirs = urlsplit(self.base_url).scheme, urlsplit(target).scheme
        if theirs not in ("http", "https") or (ours == "https" and theirs != "https"):
            raise RemoteError(f"the server pointed this client from {ours} to {theirs}, "
                              "and an answer to an https request sends a client only to "
                              "https: this client does not go there")

    def follow(self, response, headers=None, kind: str = "storage"):
        '''Follow a 303 by hand, leaving the session behind: no `Authorization`
        or proof. `kind` names the target in a failure; a "stream" may be silent
        for longer than any other answer.'''
        if response.status_code != 303:
            return response

        target = response.headers.get("Location")
        if not target:
            raise RemoteError("the server redirected without saying where")
        target = urljoin(response.url or self.base_url, target)
        self._check_scheme(target)

        sent = {"User-Agent": USER_AGENT, **self.operator_headers(target),
                **dict(headers or {})}
        try:
            return self._session.get(
                target, headers=sent, stream=True, allow_redirects=False,
                timeout=(TIMEOUT_SECONDS, STREAM_READ_SECONDS) if kind == "stream"
                else TIMEOUT_SECONDS)
        except requests.RequestException as e:
            raise RemoteError(f"could not reach the {kind} the server named: "
                              f"{_why(e)}") from None

    def save(self, response, dest) -> str:
        '''Stream a response body to a file via a temporary name, so an
        interrupted download never looks complete.

        Only the bytes: a refusal or redirect is never saved as the object.'''
        import os
        import shutil

        if 300 <= response.status_code < 400:
            raise RemoteError("the storage the server named redirected again, which "
                              "this client does not follow")
        if response.status_code >= 400:
            raise ServerProblem(_problem_body(response), response.status_code)

        dest = str(dest)
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)

        partial = dest + ".part"
        try:
            with open(partial, "wb") as f:
                shutil.copyfileobj(response.raw, f)
            os.replace(partial, dest)
        except BaseException:
            if os.path.exists(partial):
                os.remove(partial)
            raise

        return dest

    def published(self) -> Dict[str, Any]:
        '''``GET /v1``, sent with no credential and read once: the contract
        lets a client keep it per server URL. :meth:`forget_published` drops it.'''
        if self._published is None:
            self._published = self.request("GET", "", authenticated=False).json()
        return self._published

    def forget_published(self) -> None:
        self._published = None

    def check_plaintext(self) -> None:
        '''Refuse to send a credential over plaintext, unless `GET /v1` says this
        deployment authenticates nobody.'''
        if urlsplit(self.base_url).scheme == "https":
            return
        grants = self.published().get("grant_types_supported") or []
        if authenticates(grants):
            raise RemoteError(
                f"{self.base_url} is not https, and this deployment authenticates (it "
                f"offers {', '.join(grants) or 'no login'}): a credential goes to it only "
                "over https. Configure its https address with sc-config remote configure")

    def token(self, form) -> Dict[str, Any]:
        '''`POST /v1/auth/token`: a grant for a session. A proof and no token.
        ``form`` may be a function, to build it afresh for each attempt.'''
        response = self.request(
            "POST", "auth/token", authenticated=False, data=form, oauth=True,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        return response.json()

    def login(self, form) -> Dict[str, Any]:
        '''Exchange a grant for a session, and hold it.'''
        body = self.token(form)
        self.set_tokens(body.get("access_token"), body.get("expires_in"))
        return body

    def refresh(self) -> bool:
        '''Spend the refresh token for a new access token; whether one is held. A
        refusal with no reason ends the session quietly: log in afresh.

        One refresh at a time per store, inside its locked transaction: a
        rotated token presented after the grace window ends every worker's
        session. A thread that waited keeps the token another got.
        '''
        with self._renewing:
            if self.access_token is not None:
                return True
            with self._credentials.transaction():
                refresh_token = self._credentials.refresh_token
                if not refresh_token:
                    return False
                self.check_plaintext()

                # No `scope`: a refresh returns the session's full scope.
                form = {"grant_type": "refresh_token", "refresh_token": refresh_token,
                        **device_fingerprint()}
                try:
                    body = self.token(form)
                except OAuthRefusal as e:
                    if e.error != "invalid_grant":
                        raise
                    refused = e
                else:
                    self.set_tokens(body.get("access_token"), body.get("expires_in"))
                    self._credentials.save_tokens(body)
                    return True

            # Outside the transaction, which the raise below would roll back.
            self.set_tokens(None)
            self._credentials.forget_tokens()
            if refused.reason:
                raise SessionEnded(
                    {"type": f"{TYPE_BASE}session-ended", "title": "Session ended",
                     "reason": refused.reason, "detail": refused.description},
                    refused.status) from None
            return False


def _keyed(method: str, headers: Optional[Dict[str, str]]) -> bool:
    '''A keyed create or submit, which the server replays rather than repeats.'''
    return method == "POST" and "Idempotency-Key" in (headers or {})


def _http_date(value: Optional[str]) -> Optional[datetime]:
    '''An HTTP date as an aware UTC time; None where it is absent or unreadable.'''
    try:
        when = email.utils.parsedate_to_datetime(value or "")
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def _retry_after(response) -> Optional[float]:
    '''`Retry-After` in seconds, a date or a number, never below 1 and never cut short.'''
    value = (response.headers.get("Retry-After") or "").strip()
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        when = _http_date(value)
        if when is None:
            return None
        seconds = (when - datetime.now(timezone.utc)).total_seconds()
    return max(1.0, seconds)


def wait_out(problem: ServerProblem) -> bool:
    '''Sleep the ``Retry-After`` a refusal names; False where it named none.'''
    if not problem.retry_after:
        return False
    time.sleep(problem.retry_after)
    return True


def retrying(send: Callable[[], Any], when: Callable[[ServerProblem], bool],
             limit: Optional[int] = None, notice: Optional[Callable[[ServerProblem], None]] = None):
    '''``send()``, waiting out each refusal ``when`` accepts and that names a
    ``Retry-After``, at most ``limit`` times (for ever if None). ``notice`` is
    told of each before it waits.'''
    waits = 0
    while True:
        try:
            return send()
        except ServerProblem as e:
            if not when(e) or not e.retry_after or (limit is not None and waits >= limit):
                raise
            if notice:
                notice(e)
            waits += 1
            time.sleep(e.retry_after)


def _skew(response) -> Optional[float]:
    '''This machine's clock minus the server's, from the response's `Date`.'''
    theirs = _http_date(response.headers.get("Date"))
    if theirs is None:
        return None
    return (datetime.now(timezone.utc) - theirs).total_seconds()


def _skew_phrase(skew: float) -> str:
    return (f"This machine's clock is {format_duration(abs(skew))} "
            f"{'ahead of' if skew > 0 else 'behind'} the server's")


def _inner(exc: BaseException) -> Optional[BaseException]:
    '''The exception a requests or urllib3 error wraps, if it wraps one.'''
    inner = getattr(exc, "reason", None)
    if not isinstance(inner, BaseException) and exc.args:
        inner = exc.args[0]
    return inner if isinstance(inner, BaseException) else None


def _unverified(exc: BaseException) -> bool:
    '''Whether a failure to connect was the server's certificate failing verification.'''
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if isinstance(exc, ssl.SSLCertVerificationError):
            return True
        exc = _inner(exc) or exc.__context__
    return False


def _why(exc: Exception) -> str:
    """The innermost reason, which is the one worth printing."""
    reason = exc
    for _ in range(5):
        inner = _inner(reason)
        if inner is None:
            break
        reason = inner

    text = str(reason).strip()
    if ": " in text and text.startswith(("HTTP", "<urllib3")):
        text = text.split(": ", 1)[1]
    return text or exc.__class__.__name__


def link(response, rel: str) -> Optional[str]:
    '''The absolute URL of a response's ``Link`` of this ``rel`` (RFC 8288), or None.

    Not ``response.links``, which keys on the whole `rel` as sent: `rel="next last"`
    and a `REL` parameter name are both valid.'''
    from requests.utils import parse_header_links

    for found in parse_header_links(response.headers.get("Link") or ""):
        value = next((v for name, v in found.items() if name.lower() == "rel"), "")
        if rel in value.lower().split():
            return urljoin(response.url or "", found["url"])
    return None


def help_url(response) -> Optional[str]:
    '''The absolute URL of the `Link: rel="help"` page for this response's error.'''
    return link(response, "help")


def _is_problem(response) -> bool:
    return (response.headers.get("Content-Type") or "").lower() \
        .startswith("application/problem+json")


def _json(response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _problem_body(response: requests.Response) -> Dict[str, Any]:
    '''What the server said. Only problem+json names a condition: any other
    body is synthesised into an untyped one, so nothing pretends it did.'''
    body = _json(response) if _is_problem(response) else None
    if isinstance(body, dict):
        return {"status": response.status_code, **body}

    text = (response.text or "").strip()
    return {
        "status": response.status_code,
        "title": response.reason or "Request failed",
        "detail": _first_line(text),
    }


def _challenge(response) -> Optional[str]:
    '''The `error=` of a response's `WWW-Authenticate`, if it has one.'''
    found = re.search(r'\berror="?([^",\s]+)', response.headers.get("WWW-Authenticate") or "")
    return found.group(1) if found else None


def _unknown_challenge(response) -> Optional[str]:
    '''A 401's `WWW-Authenticate` `error=` this client does not know, said as it is.'''
    error = _challenge(response)
    if response.status_code != 401 or not error or error in _CHALLENGES:
        return None
    return (f"The server refused it with WWW-Authenticate error=\"{clean(error)}\", "
            "which this client does not know.")


def _first_line(text: str, limit: int = 300) -> str:
    '''One line of somebody else's error page, not the whole thing.'''
    if not text:
        return ""
    if "<" in text[:100]:
        text = re.sub(r"<[^>]+>", " ", text)
    collapsed = " ".join(text.split())
    return collapsed[:limit] + ("..." if len(collapsed) > limit else "")
