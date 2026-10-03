'''
The one request path: every API request goes through :meth:`Transport.request`,
so none forgets its token, DPoP proof, ``User-Agent`` or operator headers.

🔴 Two error shapes: OAuth refusals at ``/v1/auth/token`` and ``/v1/auth/device``
are ``{"error", "error_description", "reason"}``, all else problem+json, so the
``Content-Type`` is read first.

🔴 The HTTP library never follows a redirect: it would carry the session's
headers and proof along. A ``303`` is followed by hand without them; any other
redirect on a ``/v1`` path is the edge refusing.
'''

import email.utils
import logging
import time

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlsplit

import requests
import requests.auth

from siliconcompiler import __version__
from siliconcompiler.remote import dpop
from siliconcompiler.remote.client.errors import (
    RemoteError, ServerProblem, SessionEnded, _slug, clean)
from siliconcompiler.utils.units import format_duration

__all__ = ["Transport", "join_url", "normalize_server", "EdgeRefused",
           "OAuthRefusal", "LoginRequired", "USER_AGENT"]


logger = logging.getLogger(__name__)

# Low on purpose: each retry follows the server's exact instruction, so a second
# failure means it did not help.
MAX_RETRIES = 2

# `Retry-After` waits honoured before giving up.
MAX_WAITS = 10

TIMEOUT_SECONDS = 30


# Stable and product-named, so an edge can allowlist it.
USER_AGENT = f"siliconcompiler/{__version__}"


class _NoEnvironmentCredential(requests.auth.AuthBase):
    '''A session `auth` that adds nothing: requests sends only what was set (surface D305).

    🔴 Without it requests fills `auth` from `~/.netrc`, replacing the DPoP
    `Authorization` everywhere. `trust_env` stays on for proxies and CA bundles.
    ⚠️ Holds only with `allow_redirects=False`: `rebuild_auth` rereads netrc.
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
    '''A refresh refused `invalid_grant` with no reason: log in afresh.'''


def join_url(base: str, path: str = "") -> str:
    '''Join a path onto a base URL, keeping the base's path: ``urljoin`` drops ``/v1``.'''
    if not path:
        return base.rstrip("/")
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def normalize_server(address: str, port: Optional[int] = None) -> str:
    '''The base URL for a server address; the scheme comes from it, never the port.'''
    from urllib3.exceptions import LocationParseError
    from urllib3.util import Url, parse_url

    address = address.strip()
    if "://" not in address:
        address = f"https://{address}"

    try:
        parts = parse_url(address)
    except LocationParseError as e:
        raise ValueError(f"{address} is not a server address: {e}") from None

    # A port in the address wins over one given beside it; an IPv6 host keeps
    # its brackets.
    return Url(scheme=parts.scheme, auth=parts.auth, host=parts.host,
               port=parts.port if parts.port is not None else port,
               path=(parts.path or "").rstrip("/") or "/v1").url


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


class Transport:
    '''Signs, sends, retries and renders. Holds the key and the tokens; knows
    nothing about jobs.'''

    def __init__(self, base_url: str, key, credentials):
        self.base_url = base_url.rstrip("/")
        self._key = key
        self._credentials = credentials
        self._session = requests.Session()
        # Never netrc, never a credential from the environment (surface D305).
        self._session.auth = _NoEnvironmentCredential()

        self._access_token: Optional[str] = None
        self._access_expires: Optional[float] = None

        # One nonce per origin: the stream host's is not the API's.
        self._nonces: Dict[str, str] = {}

        # Server clock minus ours, once a proof was refused for its time.
        self._clock_offset = 0.0

        self._refreshing = False
        self._deprecation_warned = False

        # Set by the client.
        self.relogin: Optional[Callable[[Optional[str]], None]] = None
        self.trade: Optional[Callable[[], Any]] = None
        self.fingerprint: Callable[[], Dict[str, str]] = dict

        self.warn: Callable[[str], None] = logger.warning

        # Where this server serves its error `type` pages, from `Link: rel="help"`.
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
                   expires_in: Optional[int] = None) -> None:
        '''Hold an access token until its ``expires_in``; the refresh token stays in the store.'''
        self._access_token = access_token
        self._access_expires = (time.monotonic() + max(0, int(expires_in) - 5)
                                if access_token and expires_in else None)

    def url(self, path: str = "") -> str:
        return join_url(self.base_url, path)

    @property
    def api_origin(self) -> str:
        return origin_of(self.base_url)

    ######################################################################
    # Headers
    ######################################################################

    def operator_headers(self, url: str) -> Dict[str, str]:
        '''The operator headers a request to ``url`` carries.

        🔴 Only to the API's origin, whatever a redirect names (surface D304).
        '''
        if origin_of(url) != self.api_origin:
            return {}
        return self._credentials.headers()

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
                oauth: bool = False,
                absolute: bool = False,
                _attempt: int = 0,
                _waits: int = 0,
                _nonced: bool = False) -> requests.Response:
        '''Send one request, proof and all.

        ``expect_redirect``: the caller follows a ``303`` itself; an unexpected
        redirect is the edge. ``absolute``: ``path`` is a whole URL the server gave.
        '''
        url = path if absolute else self.url(path)

        if authenticated and self.access_token is None:
            # Renew before the request rather than take a 401.
            self._renew()

        sent = {"User-Agent": USER_AGENT, **self.operator_headers(url), **(headers or {})}
        token = self._access_token if authenticated else None

        if authenticated:
            if token is None:
                raise RemoteError(
                    "not logged in to this server: run sc-remote -configure")
            sent["Authorization"] = f"DPoP {token}"

        # A fresh proof per request, retries included: the server remembers its `jti`.
        sent["DPoP"] = dpop.sign_proof(
            self._key, method, url, access_token=token,
            nonce=self._nonces.get(origin_of(url)),
            iat=int(time.time() + self._clock_offset))

        again = dict(method=method, path=path, authenticated=authenticated, data=data,
                     json_body=json_body, params=params, headers=headers,
                     expect_redirect=expect_redirect, stream=stream,
                     oauth=oauth, absolute=absolute, _nonced=_nonced)

        try:
            response = self._session.request(
                method, url, data=data, json=json_body, params=params,
                headers=sent, timeout=TIMEOUT_SECONDS, allow_redirects=False,
                stream=stream)
        except (requests.Timeout, requests.ConnectionError) as e:
            # A lost answer: safe to resend, since a refresh in the grace window
            # gets the same pair and a keyed create or submit replays.
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
            raise EdgeRefused(self.api_origin)

        # HTML below 500 is an access layer's refusal; a gateway's HTML 5xx is a failure.
        if response.status_code < 500 and response.status_code != 204 and \
                (response.headers.get("Content-Type") or "").lower().startswith("text/html"):
            raise EdgeRefused(self.api_origin)

        if response.status_code < 400:
            return response

        return self._handle_refusal(response, again, attempt=_attempt, waits=_waits)

    def _handle_refusal(self, response, again, *, attempt, waits):
        '''Act on a refusal by its slug, not its status alone: refreshing on every
        401 loops on a nonce challenge, and on `session-ended` on a dead session.'''
        status = response.status_code

        # 🔴 At the OAuth endpoints, problem+json is handled below, never read for `error`.
        if again["oauth"] and not (response.headers.get("Content-Type") or "").lower() \
                .startswith("application/problem+json"):
            return self._handle_oauth(response, again, attempt=attempt, waits=waits)

        problem = _problem_body(response)
        slug = _slug(problem)
        challenge = response.headers.get("WWW-Authenticate", "")

        if status == 401 and attempt < MAX_RETRIES:
            if (slug == "dpop-nonce-required" or "use_dpop_nonce" in challenge) \
                    and not again["_nonced"]:
                # Once: a second challenge is the answer.
                return self.request(**{**again, "_nonced": True},
                                    _attempt=attempt + 1, _waits=waits)

            if slug == "invalid-dpop-proof" and self._correct_clock(response):
                return self.request(**again, _attempt=attempt + 1, _waits=waits)

            # 🔴 Only an AUTHENTICATED request renews: an unauthenticated refresh
            # renewing on its own 401 would loop.
            if again["authenticated"] and slug == "invalid-token":
                self._access_token = None
                self._renew()
                return self.request(**again, _attempt=attempt + 1, _waits=waits)

            if again["authenticated"] and slug == "session-ended" and self.relogin:
                # Never refresh: the refresh token is the session that ended.
                self.set_tokens(None)
                self._credentials.forget_tokens()
                self.relogin(problem.get("reason"))
                return self.request(**again, _attempt=attempt + 1, _waits=waits)

        # Waited out only where the server said how long and the answer means *later*.
        wait = _retry_after(response)
        if wait is not None and waits < MAX_WAITS and (
                slug == "rate-limited"
                or (slug == "job-state-conflict" and problem.get("reason") == "in_progress")
                # Only what cannot happen twice: a read, or a keyed write.
                or (status >= 500 and (again["method"] in ("GET", "HEAD")
                                       or "Idempotency-Key" in (again["headers"] or {})))):
            time.sleep(wait)
            return self.request(**again, _attempt=attempt, _waits=waits + 1)
        # A keyed create or submit replays, so a 5xx is retried even with no wait named.
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
        '''Get an access token: trade again on CI, else refresh, else log in.'''
        if self.trade is not None:
            self.trade()
            return
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
        '''Correct later proofs by the server's `Date`, once, saying so.'''
        skew = _skew(response)
        if skew is None or abs(skew) <= dpop.PROOF_LIFETIME_SECONDS or self._clock_offset:
            return False
        self._clock_offset = -skew
        self.warn(
            f"This machine's clock is {format_duration(abs(skew))} "
            f"{'ahead of' if skew > 0 else 'behind'} the server's; proofs are being "
            "corrected for it. Turn on time synchronization.")
        return True

    @staticmethod
    def _clock_advice(response) -> Optional[str]:
        skew = _skew(response)
        if skew is None or abs(skew) <= dpop.PROOF_LIFETIME_SECONDS:
            return None
        return (f"This machine's clock is {format_duration(abs(skew))} "
                f"{'ahead of' if skew > 0 else 'behind'} the server's, and a proof is "
                f"accepted only within {dpop.PROOF_LIFETIME_SECONDS} seconds of it. Correct the "
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

        Not through :meth:`request`: a presigned URL carries its own credential,
        so it gets no `Authorization`, proof, or off-origin operator header.
        '''
        sent = {"User-Agent": USER_AGENT, **self.operator_headers(url),
                **dict(headers or {})}
        with open(path, "rb") as f:
            try:
                response = self._session.put(
                    url, data=f, headers=sent, timeout=TIMEOUT_SECONDS,
                    allow_redirects=False)
            except requests.RequestException as e:
                # 🔴 The URL is a capability: never printed.
                raise RemoteError(f"could not upload the archive: {_why(e)}") from None

        if response.status_code >= 400:
            raise ServerProblem(_problem_body(response), response.status_code)

    def follow(self, response, headers=None, kind: str = "storage"):
        '''Follow a 303 by hand, leaving the session behind: no `Authorization`
        or proof, and never https to http. `kind` names the target in a failure.'''
        if response.status_code not in (301, 302, 303, 307, 308):
            return response

        target = response.headers.get("Location")
        if not target:
            raise RemoteError("the server redirected without saying where")
        from urllib.parse import urljoin
        target = urljoin(response.url or self.base_url, target)

        # 🔴 Contract rule 5 (D70): https never redirects to http.
        ours, theirs = urlsplit(self.base_url).scheme, urlsplit(target).scheme
        if theirs not in ("http", "https") or (ours == "https" and theirs != "https"):
            raise RemoteError(f"the server redirected an {ours} request to {theirs}, "
                              "and an answer to an https request sends a client only to "
                              "https: this client does not follow it")

        sent = {"User-Agent": USER_AGENT, **self.operator_headers(target),
                **dict(headers or {})}
        try:
            return self._session.get(
                target, headers=sent, stream=True,
                timeout=TIMEOUT_SECONDS, allow_redirects=False)
        except requests.RequestException as e:
            raise RemoteError(f"could not reach the {kind} the server named: "
                              f"{_why(e)}") from None

    def save(self, response, dest) -> str:
        '''Stream a response body to a file via a temporary name, so an
        interrupted download never looks complete.

        🔴 Only the bytes: a refusal or redirect is never saved as the object.'''
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
        self.set_tokens(body.get("access_token"), body.get("expires_in"))
        return body

    def refresh(self) -> bool:
        '''Spend the refresh token for a new access token; whether it worked.

        🔴 One refresh at a time per store, inside its locked transaction: a
        rotated token presented after the grace window ends every worker's session.
        '''
        if self._refreshing:
            # Impossible by construction: a nested refresh costs the SERVER.
            logger.debug("declining to refresh inside a refresh")
            return False

        self._refreshing = True
        try:
            with self._credentials.transaction():
                refresh_token = self._credentials.refresh_token
                if not refresh_token:
                    return False

                # No `scope`: a refresh returns the session's full scope.
                form = {"grant_type": "refresh_token", "refresh_token": refresh_token,
                        **self.fingerprint()}
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
                    {"type": "https://siliconcompiler.com/server-errors/session-ended",
                     "title": "Session ended", "reason": refused.reason,
                     "detail": refused.description}, refused.status) from None
            raise LoginRequired(refused.description or "log in again") from None
        finally:
            self._refreshing = False


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
    if theirs.tzinfo is None:
        theirs = theirs.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - theirs).total_seconds()


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
    '''The absolute URL of the `Link: rel="help"` page for this response's error.'''
    from urllib.parse import urljoin

    try:
        target = (response.links.get("help") or {}).get("url")
    except Exception:                                           # noqa: BLE001
        return None
    if not target:
        return None
    return urljoin(response.url or "", target)


def _problem_body(response: requests.Response) -> Dict[str, Any]:
    '''What the server said, as problem+json; one with no `type` is synthesised,
    so nothing pretends the server named a condition.'''
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
