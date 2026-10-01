'''
The one request path.

Every request this client makes to the API goes through :meth:`Transport.request`.
That is a design requirement rather than a tidy-up: under ``v1`` each request
carries an ``Authorization`` header, a freshly signed DPoP proof, a
``User-Agent`` and any operator-configured headers, so a second call site is a
call site that forgets one.

🔴 **Two error shapes, keyed on the endpoint.** At ``/v1/auth/token`` and
``/v1/auth/device`` what OAuth processing refuses arrives as ``{"error",
"error_description", "reason"}``; everything else, the transport-level
refusals at those two endpoints included, is problem+json. So the
``Content-Type`` is read first, and a client branches on ``error`` or ``type``,
then on ``reason``.

🔴 **Redirects are never followed by the HTTP library.** It would carry this
session's headers and proof to wherever the redirect points. A ``303`` from the
logs or artifact endpoints is followed by hand, with no ``Authorization`` and no
proof; any other redirect on a ``/v1`` path is an intermediary refusing the
request, reported as the edge.
'''

import email.utils
import json
import logging
import time

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlsplit, urlunsplit

import requests
import requests.auth

from siliconcompiler.remote import dpop
from siliconcompiler.remote.client.errors import (
    RemoteError, ServerProblem, SessionEnded, clean)

__all__ = ["Transport", "join_url", "normalize_server", "EdgeRefused",
           "OAuthRefusal", "LoginRequired", "USER_AGENT"]


logger = logging.getLogger(__name__)

# How many times a request is re-sent after a nonce challenge, a clock
# correction, a silent refresh or a lost answer. Low on purpose: each of these
# is a server telling the client exactly what to do differently, so needing
# more than one means the answer did not help.
MAX_RETRIES = 2

# How many times a wait the server asked for (`Retry-After`) is honoured before
# giving up, for the waits the transport takes on itself.
MAX_WAITS = 10

TIMEOUT_SECONDS = 30

# How far a proof's `iat` may be from the server's clock (surface §6).
PROOF_WINDOW_SECONDS = 60


def _user_agent() -> str:
    from siliconcompiler import __version__
    return f"siliconcompiler/{__version__}"


# Stable and product-named, never randomised and never the library's default:
# an edge in front of the API allowlists it rather than challenging it.
USER_AGENT = _user_agent()


class _NoEnvironmentCredential(requests.auth.AuthBase):
    '''The session's own `auth`, which adds nothing: a request goes out with
    only what this client put on it (surface D305).

    🔴 **requests fills a missing `auth` from `~/.netrc`** while `trust_env` is
    on, and its `HTTPBasicAuth` then replaces whatever `Authorization` the
    request carried -- the API's `DPoP <token>` included -- with the netrc
    login, which would go to the API, to storage and to a stream host alike.
    An `auth` of the session's own is never replaced. `trust_env` stays on,
    because it is also what applies `HTTPS_PROXY`, `NO_PROXY` and
    `REQUESTS_CA_BUNDLE`.

    ⚠️ **It holds only while requests follows no redirect itself**: its
    `rebuild_auth` reads netrc again for the new URL, whatever `auth` says.
    Every request here sends `allow_redirects=False`, and a redirect is
    followed by hand (:meth:`Transport.follow`).
    '''

    def __call__(self, r):
        return r


class EdgeRefused(RemoteError):
    '''An intermediary in front of the API refused the request: HTML, or a
    redirect to an identity provider, on a `/v1` path. Never an API failure.'''

    def __init__(self, origin: str):
        super().__init__(
            f"the edge refused this request: check the Cloudflare credentials -- the "
            f"operator-configured headers for {origin} (sc-remote -header). This is an "
            "intermediary in front of the server, not the API")


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


class LoginRequired(RemoteError):
    '''The session cannot be refreshed and a fresh login is the answer: a
    refresh refused `invalid_grant` with no reason, such as a changed
    fingerprint.'''


def join_url(base: str, path: str = "") -> str:
    '''Join a path onto a base URL, keeping the base's own path.

    Explicitly not ``urljoin``: with a base of ``https://host/v1`` it returns
    ``https://host/jobs``, silently dropping the version prefix.
    '''
    if not path:
        return base.rstrip("/")
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def normalize_server(address: str, port: Optional[int] = None) -> str:
    '''The base URL for a configured server address.

    The scheme comes from the address, never from the port. A server on :8000
    reached over plaintext because of its port number is every local
    deployment of the client this replaces.
    '''
    address = address.strip()
    if "://" not in address:
        address = f"https://{address}"

    parts = urlsplit(address)
    netloc = parts.netloc

    if port is not None and ":" not in parts.netloc:
        netloc = f"{parts.netloc}:{port}"

    path = parts.path.rstrip("/")
    if not path:
        path = "/v1"

    return urlunsplit((parts.scheme, netloc, path, "", ""))


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


class Transport:
    '''Signs, sends, retries and renders. Holds the key and the tokens; knows
    nothing about jobs.'''

    def __init__(self, base_url: str, key, credentials=None,
                 session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self._key = key
        self._credentials = credentials
        self._session = session or requests.Session()
        # Never netrc, never a credential from the environment (surface D305).
        self._session.auth = _NoEnvironmentCredential()

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        # When the access token runs out, from its response's `expires_in`,
        # never assumed.
        self._access_expires: Optional[float] = None

        # One nonce per origin: the stream host's is not the API's.
        self._nonces: Dict[str, str] = {}

        # The server's clock minus this one's, once a proof was refused for its
        # time; later proofs are corrected by it.
        self._clock_offset = 0.0

        self._refreshing = False
        self._deprecation_warned = False

        # Set by the client: how a fresh login is had, how a CI session trades
        # again, and what fingerprint a refresh carries.
        self.relogin: Optional[Callable[[Optional[str]], None]] = None
        self.trade: Optional[Callable[[], bool]] = None
        self.fingerprint: Callable[[], Dict[str, str]] = dict

        # Where messages go, so they reach the run's own log.
        self.warn: Callable[[str], None] = logger.warning

        # Where this server serves its own error `type` pages, once it has
        # said so with a `Link: <...>; rel="help"`.
        self.help_pages: Optional[str] = None

    ######################################################################
    # Tokens
    ######################################################################

    @property
    def access_token(self) -> Optional[str]:
        if self._access_expires is not None and time.monotonic() >= self._access_expires:
            return None
        return self._access_token

    def set_tokens(self, access_token: Optional[str],
                   refresh_token: Optional[str],
                   expires_in: Optional[int] = None) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._access_expires = (time.monotonic() + max(0, int(expires_in) - 5)
                                if access_token and expires_in else None)

    def url(self, path: str = "") -> str:
        return join_url(self.base_url, path)

    @property
    def origin(self) -> str:
        '''The server without the version prefix, where its signed routes, the
        upload PUT among them, live outside ``/v1``.'''
        base = self.base_url
        return base[:-len("/v1")] if base.endswith("/v1") else base

    @property
    def api_origin(self) -> str:
        return origin_of(self.base_url)

    ######################################################################
    # Headers
    ######################################################################

    def operator_headers(self, url: str) -> Dict[str, str]:
        '''The operator-configured headers a request to ``url`` carries.

        🔴 To the API's origin, its signed routes included, and nowhere else
        (surface D304): a server sends a client to no other origin that
        requires one, so a stream or storage URL elsewhere gets none, whatever
        a redirect names.
        '''
        if self._credentials is None or origin_of(url) != self.api_origin:
            return {}
        return self._credentials.headers()

    def _proof(self, method: str, url: str, token: Optional[str]) -> str:
        return dpop.sign_proof(
            self._key, method, url, access_token=token,
            nonce=self._nonces.get(origin_of(url)),
            iat=int(time.time() + self._clock_offset))

    ######################################################################
    # The request
    ######################################################################

    def request(self, method: str, path: str, *,
                authenticated: bool = True,
                data: Any = None,
                json_body: Any = None,
                params: Optional[Dict[str, Any]] = None,
                headers: Optional[Dict[str, str]] = None,
                expect_redirect: bool = False,
                stream: bool = False,
                on_v1: bool = True,
                oauth: bool = False,
                absolute: bool = False,
                _attempt: int = 0,
                _waits: int = 0,
                _nonced: bool = False) -> requests.Response:
        '''Send one request, proof and all.

        ``expect_redirect`` says the caller expects a ``303`` and follows it
        itself; a redirect nobody expected is the edge. ``absolute`` takes
        ``path`` as a whole URL the server gave, such as a `Link` target.
        '''
        url = path if absolute else self.url(path) if on_v1 else join_url(self.origin, path)

        if authenticated and self.access_token is None:
            # Expired by its own `expires_in`, or never had: one refresh, or a
            # login, before the request rather than a 401 after it.
            self._renew()

        sent = {"User-Agent": USER_AGENT, **self.operator_headers(url), **(headers or {})}
        token = self._access_token if authenticated else None

        if authenticated:
            if token is None:
                raise RemoteError(
                    "not logged in to this server: run sc-remote -configure")
            sent["Authorization"] = f"DPoP {token}"

        # A fresh proof per request, retries included: `htm` and `htu` bind it
        # to this method and URI, and the server remembers its `jti`.
        sent["DPoP"] = self._proof(method, url, token)

        again = dict(method=method, path=path, authenticated=authenticated, data=data,
                     json_body=json_body, params=params, headers=headers,
                     expect_redirect=expect_redirect, stream=stream, on_v1=on_v1,
                     oauth=oauth, absolute=absolute, _nonced=_nonced)

        try:
            response = self._session.request(
                method, url, data=data, json=json_body, params=params,
                headers=sent, timeout=TIMEOUT_SECONDS, allow_redirects=False,
                stream=stream)
        except (requests.Timeout, requests.ConnectionError) as e:
            # A lost answer. Every retry carries a fresh proof and the same
            # body: a refresh inside the server's grace window gets the same
            # pair, and a keyed create or submit replays.
            if _attempt < MAX_RETRIES and (isinstance(e, requests.Timeout) or oauth):
                time.sleep(2 ** _attempt)
                return self.request(**again, _attempt=_attempt + 1, _waits=_waits)
            if isinstance(e, requests.Timeout):
                raise TimeoutError(f"{self.base_url} did not answer") from None
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

        if 300 <= response.status_code < 400:
            if expect_redirect and response.status_code in (301, 302, 303, 307, 308):
                return response
            if on_v1:
                raise EdgeRefused(self.api_origin)
            return response

        # An HTML page in place of an answer is an access layer's refusal. A
        # gateway's 5xx is HTML too, but it says the server is unwell, not that
        # the request was refused, and it is handled as the failure it is.
        if on_v1 and _is_html(response) and response.status_code < 500 \
                and response.status_code != 204:
            raise EdgeRefused(self.api_origin)

        if response.status_code < 400:
            return response

        return self._handle_refusal(response, again, attempt=_attempt, waits=_waits)

    def _handle_refusal(self, response, again, *, attempt, waits):
        '''Several answers wear the same status, and they are different answers.

        A client that only refreshes on 401 loops for ever on a nonce challenge,
        and one that refreshes on `session-ended` loops for ever on a dead
        session.
        '''
        status = response.status_code

        # 🔴 At the two OAuth endpoints the Content-Type decides the shape:
        # problem+json is a transport-level refusal, handled by status and type
        # below and never read for `error`.
        if again["oauth"] and not _is_problem(response):
            return self._handle_oauth(response, again, attempt=attempt, waits=waits)

        problem = _problem_body(response)
        slug = _slug(problem)
        challenge = response.headers.get("WWW-Authenticate", "")

        if status == 401 and attempt < MAX_RETRIES:
            if (slug == "dpop-nonce-required" or "use_dpop_nonce" in challenge) \
                    and not again["_nonced"]:
                # The server wants the nonce it just gave, for this origin:
                # retried once, and a second challenge is the answer.
                return self.request(**{**again, "_nonced": True},
                                    _attempt=attempt + 1, _waits=waits)

            if slug == "invalid-dpop-proof" and self._correct_clock(response):
                return self.request(**again, _attempt=attempt + 1, _waits=waits)

            # 🔴 Only an AUTHENTICATED request can have an expired access token
            # worth renewing; an unauthenticated one refreshing on its own 401
            # is a refresh that fails, asks for a refresh, and fails again.
            if again["authenticated"] and slug == "invalid-token":
                self._access_token = None
                self._renew()
                return self.request(**again, _attempt=attempt + 1, _waits=waits)

            if again["authenticated"] and slug == "session-ended" and self.relogin:
                # Re-authenticate, and never refresh: the refresh token is the
                # session that ended.
                self.set_tokens(None, None)
                if self._credentials is not None:
                    self._credentials.forget_tokens()
                self.relogin(problem.get("reason"))
                return self.request(**again, _attempt=attempt + 1, _waits=waits)

        # Waited out only where the server said how long, and only for the
        # answers whose meaning is *later*: a request rate, and a keyed retry
        # the server is still handling.
        wait = _retry_after(response)
        if wait is not None and waits < MAX_WAITS and (
                slug == "rate-limited"
                or (slug == "job-state-conflict" and problem.get("reason") == "in_progress")
                or (status >= 500 and _replayable(again))):
            time.sleep(wait)
            return self.request(**again, _attempt=attempt, _waits=waits + 1)
        # A keyed create or submit replays, so a 5xx is retried with the same
        # key and body even where the server named no wait.
        if status >= 500 and wait is None and attempt < MAX_RETRIES \
                and again["method"] == "POST" and "Idempotency-Key" in (again["headers"] or {}):
            time.sleep(2 ** attempt)
            return self.request(**again, _attempt=attempt + 1, _waits=waits)

        if slug == "session-ended":
            raise SessionEnded(problem, status, help_url=help_url(response))

        raise ServerProblem(problem, status, help_url=help_url(response),
                            next_step=self._clock_advice(response)
                            if slug == "invalid-dpop-proof" else None,
                            retry_after=wait)

    def _handle_oauth(self, response, again, *, attempt, waits):
        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict) or not isinstance(body.get("error"), str):
            # Neither shape: an untyped failure of its status.
            raise ServerProblem(_problem_body(response), response.status_code)

        error = body["error"]
        if attempt < MAX_RETRIES:
            if error == "use_dpop_nonce" and not again["_nonced"]:
                return self.request(**{**again, "_nonced": True},
                                    _attempt=attempt + 1, _waits=waits)
            if error == "invalid_dpop_proof" and self._correct_clock(response):
                return self.request(**again, _attempt=attempt + 1, _waits=waits)

        raise OAuthRefusal(error, body.get("error_description"),
                           body.get("reason"), response.status_code)

    def _renew(self) -> None:
        '''Get an access token: refresh where there is a session, trade again
        where this is CI, and log in where neither works.'''
        if self.trade is not None:
            if self.trade():
                return
        else:
            try:
                if self.refresh():
                    return
            except (SessionEnded, LoginRequired) as e:
                reason = e.reason if isinstance(e, SessionEnded) else None
                if self.relogin is None:
                    raise
                self.relogin(reason)
                return
        if self.relogin is not None:
            self.relogin(None)

    ######################################################################
    # The clock
    ######################################################################

    def _correct_clock(self, response) -> bool:
        '''A proof refused for its time: take the server's clock from `Date`,
        correct later proofs by the offset, and say so -- once.'''
        skew = _skew(response)
        if skew is None or abs(skew) <= PROOF_WINDOW_SECONDS or self._clock_offset:
            return False
        self._clock_offset = -skew
        self.warn(
            f"This machine's clock is {_duration(abs(skew))} "
            f"{'ahead of' if skew > 0 else 'behind'} the server's; proofs are being "
            "corrected for it. Turn on time synchronization.")
        return True

    @staticmethod
    def _clock_advice(response) -> Optional[str]:
        skew = _skew(response)
        if skew is None or abs(skew) <= PROOF_WINDOW_SECONDS:
            return None
        return (f"This machine's clock is {_duration(abs(skew))} "
                f"{'ahead of' if skew > 0 else 'behind'} the server's, and a proof is "
                f"accepted only within {PROOF_WINDOW_SECONDS} seconds of it. Correct the "
                "clock -- turn on time synchronization -- and try again.")

    def _notice_deprecation(self, response) -> None:
        '''Once per session: a `Deprecation` header, with its `Sunset` date.'''
        if self._deprecation_warned or "Deprecation" not in response.headers:
            return
        self._deprecation_warned = True
        sunset = response.headers.get("Sunset")
        self.warn("This server says the API this client uses is deprecated"
                  + (f", and it goes away on {clean(sunset)}" if sunset else "")
                  + ". Upgrade SiliconCompiler.")

    ######################################################################
    # Storage and streams
    ######################################################################

    def put_object(self, url: str, headers: Dict[str, str], path) -> None:
        '''Send the bytes to wherever the grant points.

        The one request that does NOT go through :meth:`request`, and the
        exception is the contract: this addresses storage, not the API. A
        presigned URL carries its own credential in its signature, so it gets no
        `Authorization`, no proof, and no operator header on another origin.
        '''
        sent = {"User-Agent": USER_AGENT, **self.operator_headers(url),
                **dict(headers or {})}
        with open(path, "rb") as f:
            try:
                response = self._session.put(
                    url, data=f, headers=sent, timeout=TIMEOUT_SECONDS,
                    allow_redirects=False)
            except requests.RequestException as e:
                # 🔴 The URL is a capability: never printed, error messages
                # included.
                raise RemoteError(f"could not upload the archive: {_why(e)}") from None

        if response.status_code >= 400:
            raise ServerProblem(_problem_body(response), response.status_code)

    def follow(self, response, headers=None, stream: bool = True, kind: str = "storage"):
        '''Follow a 303 by hand, with this session left behind.

        No `Authorization` and no proof, whatever the target's origin; never
        from https to http; operator headers only to the API's own origin, its
        signed routes included (:meth:`operator_headers`). `kind` is `storage` or `stream`,
        and names it in a failure.
        '''
        if response.status_code not in (301, 302, 303, 307, 308):
            return response

        target = response.headers.get("Location")
        if not target:
            raise RemoteError("the server redirected without saying where")
        from urllib.parse import urljoin
        target = urljoin(response.url or self.base_url, target)

        # 🔴 Contract rule 5 (D70): an answer to an https request sends the
        # client only to https URLs, and one to an http request may send it to
        # either. So http to https is followed, and https to http never is.
        ours, theirs = urlsplit(self.base_url).scheme, urlsplit(target).scheme
        if theirs not in ("http", "https") or (ours == "https" and theirs != "https"):
            raise RemoteError(f"the server redirected an {ours} request to {theirs}, "
                              "and an answer to an https request sends a client only to "
                              "https: this client does not follow it")

        sent = {"User-Agent": USER_AGENT, **self.operator_headers(target),
                **dict(headers or {})}
        try:
            return self._session.get(
                target, headers=sent, stream=stream,
                timeout=TIMEOUT_SECONDS, allow_redirects=False)
        except requests.RequestException as e:
            raise RemoteError(f"could not reach the {kind} the server named: "
                              f"{_why(e)}") from None

    def save(self, response, dest) -> str:
        '''Stream a response body to a file, through a temporary name, so an
        interrupted download never leaves something that looks complete.

        🔴 **Only the bytes are written.** A refusal from storage, or a
        redirect it answered with -- which nothing here follows -- is never
        saved as the object.'''
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

    ######################################################################
    # Login
    ######################################################################

    def token(self, form: Dict[str, str]) -> Dict[str, Any]:
        '''`POST /v1/auth/token`: a grant for a session. A proof and no token.'''
        response = self.request(
            "POST", "auth/token", authenticated=False, data=form, oauth=True,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        return response.json()

    def login(self, form: Dict[str, str]) -> Dict[str, Any]:
        '''Exchange a grant for a session, and hold it.'''
        body = self.token(form)
        self.set_tokens(body.get("access_token"), body.get("refresh_token"),
                        body.get("expires_in"))
        return body

    def refresh(self) -> bool:
        '''Spend the refresh token for a new access token.

        🔴 **One refresh at a time, per store**: inside the store's transaction,
        which re-reads it under its lock. A process that waited uses the token
        the last refresh wrote, never the one it held before: presenting a
        rotated one after the grace window would end every worker's session.
        Returns whether it worked; raises `SessionEnded` or `LoginRequired`
        where a login is the answer.
        '''
        if self._refreshing:
            # A refresh that provokes a refresh costs the SERVER: impossible by
            # construction rather than by one condition being right.
            logger.debug("declining to refresh inside a refresh")
            return False

        import contextlib

        self._refreshing = True
        try:
            held = self._credentials.transaction() if self._credentials is not None \
                else contextlib.nullcontext()
            with held:
                refresh_token = (self._credentials.refresh_token
                                 if self._credentials is not None else None) \
                    or self._refresh_token
                if not refresh_token:
                    return False

                # No `scope`: a refresh returns the session's full scope. The
                # fingerprint pair, where one can be derived.
                form = {"grant_type": "refresh_token", "refresh_token": refresh_token,
                        **self.fingerprint()}
                try:
                    body = self.token(form)
                except OAuthRefusal as e:
                    if e.error != "invalid_grant":
                        raise
                    refused = e
                else:
                    self.set_tokens(body.get("access_token"),
                                    body.get("refresh_token") or refresh_token,
                                    body.get("expires_in"))
                    if self._credentials is not None:
                        self._credentials.save_tokens(body)
                    return True

            # Out of the transaction: forgetting the dead token inside it would
            # be rolled back by the raise that follows.
            self.set_tokens(None, None)
            if self._credentials is not None:
                self._credentials.forget_tokens()
            if refused.reason:
                raise SessionEnded(
                    {"type": "https://siliconcompiler.com/server-errors/session-ended",
                     "title": "Session ended", "reason": refused.reason,
                     "detail": refused.description}, refused.status) from None
            # A changed fingerprint, or a token the server does not know: the
            # person logs in again.
            raise LoginRequired(refused.description or "log in again") from None
        finally:
            self._refreshing = False


def _replayable(again) -> bool:
    '''Whether a retry cannot do something twice: a read, or a keyed write.'''
    return again["method"] in ("GET", "HEAD") or \
        "Idempotency-Key" in (again["headers"] or {})


def _retry_after(response) -> Optional[float]:
    '''`Retry-After` in seconds, a date or a number, never below 1.'''
    value = (response.headers.get("Retry-After") or "").strip()
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        seconds = (when - datetime.now(timezone.utc)).total_seconds()
    return max(1.0, min(seconds, 300.0))


def _skew(response) -> Optional[float]:
    '''This machine's clock minus the server's, from the response's `Date`.'''
    try:
        theirs = email.utils.parsedate_to_datetime(response.headers.get("Date") or "")
    except (TypeError, ValueError):
        return None
    if theirs is None:
        return None
    if theirs.tzinfo is None:
        theirs = theirs.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - theirs).total_seconds()


def _duration(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 120:
        return f"{seconds} seconds"
    if seconds < 7200:
        return f"{seconds // 60} minutes"
    return f"{seconds // 3600} hours"


def _is_html(response) -> bool:
    return (response.headers.get("Content-Type") or "").lower().startswith("text/html")


def _is_problem(response) -> bool:
    return (response.headers.get("Content-Type") or "").lower().startswith(
        "application/problem+json")


def _why(exc: Exception) -> str:
    """The innermost reason, which is the one worth printing."""
    reason = exc
    for _ in range(5):
        inner = getattr(reason, "reason", None) or getattr(reason, "args", (None,))[0]
        if not isinstance(inner, Exception):
            break
        reason = inner

    text = str(reason).strip()
    if ": " in text and text.startswith(("HTTP", "<urllib3")):
        text = text.split(": ", 1)[1]
    return text or exc.__class__.__name__


def help_url(response) -> Optional[str]:
    '''The page a server names for this response's error, as an absolute URL
    (`Link: <...>; rel="help"`), resolved against the URL that was called.'''
    from urllib.parse import urljoin

    try:
        target = (response.links.get("help") or {}).get("url")
    except Exception:                                           # noqa: BLE001
        return None
    if not target:
        return None
    return urljoin(response.url or "", target)


def _problem_body(response: requests.Response) -> Dict[str, Any]:
    '''What the server said, as far as it can be read.

    problem+json is promised only for what a handler produced; routing, a
    framework's own validation and any proxy answer in their own shapes. A body
    with no `type` is synthesised so every caller sees one shape, and nothing
    pretends the server named a condition.
    '''
    try:
        body = response.json()
    except ValueError:
        body = None

    if isinstance(body, dict) and "type" in body:
        return body

    text = (response.text or "").strip()
    return {
        "status": response.status_code,
        "title": response.reason or "Request failed",
        "detail": _first_line(text),
    }


def _first_line(text: str, limit: int = 300) -> str:
    '''One line of somebody else's error page, not the whole thing.'''
    if not text:
        return ""
    if "<" in text[:100]:
        import re
        text = re.sub(r"<[^>]+>", " ", text)
    collapsed = " ".join(text.split())
    return collapsed[:limit] + ("..." if len(collapsed) > limit else "")


def _slug(problem: Dict[str, Any]) -> Optional[str]:
    uri = problem.get("type")
    if not isinstance(uri, str):
        return None
    return uri.rstrip("/").rsplit("/", 1)[-1]


def dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))
