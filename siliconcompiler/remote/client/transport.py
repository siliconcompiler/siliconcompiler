'''
The one request path.

Every request this client makes goes through :meth:`Transport.request`. That is
a design requirement rather than a tidy-up: under ``v1`` each request carries an
``Authorization`` header and a freshly signed DPoP proof, so a second call site
is a call site that forgets one. The client this replaces had six request sites
and passed headers at none of them.
'''

import json
import logging
import time

from typing import Any, Dict, Optional
from urllib.parse import urlsplit, urlunsplit

import requests

from siliconcompiler.remote import dpop
from siliconcompiler.remote.client.errors import (
    RemoteError, ServerProblem, SessionEnded)

__all__ = ["Transport", "join_url"]


logger = logging.getLogger(__name__)

# How many times a request is re-sent after a nonce challenge or a silent
# refresh. Low on purpose: each of these is a server telling the client exactly
# what to do differently, so needing more than one means the answer did not
# help.
MAX_RETRIES = 2

TIMEOUT_SECONDS = 30


def join_url(base: str, path: str = "") -> str:
    '''Join a path onto a base URL, keeping the base's own path.

    Explicitly not ``urljoin``: with a base of ``https://host/v1`` it returns
    ``https://host/jobs``, silently dropping the version prefix. That is fine
    until a server URL carries one -- which is what ``/v1`` is -- and then every
    request goes somewhere else.
    '''
    if not path:
        return base.rstrip("/")
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def normalize_server(address: str, port: Optional[int] = None) -> str:
    '''The base URL for a configured server address.

    The scheme comes from the address, never from the port. The client this
    replaces defaulted the port to 443 and then read the scheme off the port it
    had just defaulted, so a server on :8000 was reached over plaintext because
    of its port number -- which is every local deployment.
    '''
    address = address.strip()
    if "://" not in address:
        # No scheme given. Assume the safe one and let an operator who means
        # plaintext say so, rather than guessing from a port number.
        address = f"https://{address}"

    parts = urlsplit(address)
    netloc = parts.netloc

    if port is not None and ":" not in parts.netloc:
        netloc = f"{parts.netloc}:{port}"

    path = parts.path.rstrip("/")
    if not path:
        path = "/v1"

    return urlunsplit((parts.scheme, netloc, path, "", ""))


class Transport:
    '''Signs, sends, retries and renders.

    Holds the key and the tokens; knows nothing about jobs.
    '''

    def __init__(self, base_url: str, key, credentials=None,
                 session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self._key = key
        self._credentials = credentials
        self._session = session or requests.Session()

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._nonce: Optional[str] = None

    ######################################################################
    # Tokens
    ######################################################################

    @property
    def access_token(self) -> Optional[str]:
        return self._access_token

    def set_tokens(self, access_token: Optional[str],
                   refresh_token: Optional[str]) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token

    def url(self, path: str = "") -> str:
        return join_url(self.base_url, path)

    ######################################################################
    # The request
    ######################################################################

    def request(self, method: str, path: str, *,
                authenticated: bool = True,
                data: Any = None,
                json_body: Any = None,
                params: Optional[Dict[str, Any]] = None,
                headers: Optional[Dict[str, str]] = None,
                allow_redirects: bool = True,
                stream: bool = False,
                _attempt: int = 0) -> requests.Response:
        '''Send one request, proof and all.'''
        url = self.url(path)

        sent = dict(headers or {})
        token = self._access_token if authenticated else None

        if authenticated:
            if token is None:
                raise RemoteError(
                    "not logged in to this server: run sc-remote -configure")
            sent["Authorization"] = f"DPoP {token}"

        # A fresh proof per request, never a reused one: `htm` and `htu` bind it
        # to this method and this URI, and the server remembers its `jti`.
        sent["DPoP"] = dpop.sign_proof(
            self._key, method, url, access_token=token, nonce=self._nonce)

        try:
            response = self._session.request(
                method, url, data=data, json=json_body, params=params,
                headers=sent, timeout=TIMEOUT_SECONDS,
                allow_redirects=allow_redirects, stream=stream)
        except requests.Timeout:
            if _attempt < MAX_RETRIES:
                time.sleep(2 ** _attempt)
                return self.request(
                    method, path, authenticated=authenticated, data=data,
                    json_body=json_body, params=params, headers=headers,
                    allow_redirects=allow_redirects, stream=stream,
                    _attempt=_attempt + 1)
            raise TimeoutError(f"{self.base_url} did not answer") from None
        except requests.RequestException as e:
            # Nothing answered at all: the host is down, the name does not
            # resolve, TLS did not agree. These are the most ordinary failures
            # there are and none of them is a server refusal, so they must not
            # reach a user as a urllib3 traceback.
            raise RemoteError(
                f"could not reach {self.base_url}: {_why(e)}") from None

        # A nonce arrives on the response whether or not the request failed, and
        # the next proof carries it.
        offered = response.headers.get("DPoP-Nonce")
        if offered:
            self._nonce = offered

        if response.status_code < 400:
            return response

        return self._handle_refusal(
            response, method, path, authenticated=authenticated, data=data,
            json_body=json_body, params=params, headers=headers,
            allow_redirects=allow_redirects, stream=stream, attempt=_attempt)

    def _handle_refusal(self, response, method, path, *, attempt, **kwargs):
        '''Three things wear the same status code, and they are three answers.

        A client that only refreshes on 401 loops forever on a nonce challenge,
        and one that refreshes on `session-ended` loops forever on a dead
        session. Building all three at once is the only way any of them is
        right.
        '''
        problem = _problem_body(response)
        slug = _slug(problem)

        if response.status_code == 401 and attempt < MAX_RETRIES:
            challenge = response.headers.get("WWW-Authenticate", "")

            if "use_dpop_nonce" in challenge:
                # The server wants the nonce it just gave us. Re-send as is.
                return self.request(method, path, _attempt=attempt + 1, **kwargs)

            if slug == "invalid-token":
                # An expired access token, and the session is still alive.
                if self.refresh():
                    return self.request(method, path, _attempt=attempt + 1, **kwargs)

        if slug == "session-ended":
            raise SessionEnded(problem, response.status_code)

        raise ServerProblem(problem, response.status_code)

    ######################################################################
    # Storage
    ######################################################################

    def put_object(self, url: str, headers: Dict[str, str], path) -> None:
        '''Send the bytes to wherever the grant points.

        The one request this client makes that does NOT go through
        :meth:`request`, and the exception is the contract rather than an
        oversight: this addresses storage, not the API. A presigned URL carries
        its own credential in its signature, so attaching this session's token
        and a DPoP proof would hand them to a third party that never asked for
        them -- and on a deployment whose storage is somebody else's bucket,
        that third party is somebody else.
        '''
        with open(path, "rb") as f:
            try:
                response = self._session.put(
                    url, data=f, headers=dict(headers or {}),
                    timeout=TIMEOUT_SECONDS)
            except requests.RequestException as e:
                raise RemoteError(f"could not upload to {url}: {_why(e)}") from None

        if response.status_code >= 400:
            problem = _problem_body(response)
            raise ServerProblem(problem, response.status_code)

    ######################################################################
    # Login
    ######################################################################

    def login(self, form: Dict[str, str]) -> Dict[str, Any]:
        '''Exchange a grant for a session. Carries a proof and no token.'''
        response = self.request(
            "POST", "auth/token", authenticated=False, data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"})

        body = response.json()
        self.set_tokens(body.get("access_token"), body.get("refresh_token"))
        return body

    def refresh(self) -> bool:
        '''Spend the refresh token for a new access token.

        Called on a 401, and called once at the start of a command -- the
        access token is never written to disk, so a session that survives
        between invocations survives as its refresh token and nothing else.
        Returns whether it worked.
        '''
        if not self._refresh_token:
            return False

        try:
            body = self.login({"grant_type": "refresh_token",
                               "refresh_token": self._refresh_token})
        except SessionEnded:
            # The session is over rather than stale, so there is nothing to
            # retry and the caller must log in again.
            self.set_tokens(None, None)
            raise
        except ServerProblem as e:
            logger.debug(f"refresh failed: {e}")
            return False

        if self._credentials is not None:
            self._credentials.save_tokens(body)
        return True


def _why(exc: Exception) -> str:
    """The innermost reason, which is the one worth printing.

    requests wraps urllib3, which wraps the socket error, so the useful
    sentence is several layers down and the outer repr is mostly class names.
    """
    reason = exc
    for _ in range(5):
        inner = getattr(reason, "reason", None) or getattr(reason, "args", (None,))[0]
        if not isinstance(inner, Exception):
            break
        reason = inner

    text = str(reason).strip()
    # urllib3 prefixes the connection object's repr; the sentence after it is
    # what a person can act on.
    if ": " in text and text.startswith(("HTTP", "<urllib3")):
        text = text.split(": ", 1)[1]
    return text or exc.__class__.__name__


def _problem_body(response: requests.Response) -> Dict[str, Any]:
    '''What the server said, as far as it can be read.

    problem+json is promised only for what a handler produced. Routing, a
    framework's own validation and any proxy in front of the server answer in
    their own shapes -- and those are the errors production serves most, so
    `response.json()` on a non-2xx is exactly the call that throws.
    '''
    try:
        body = response.json()
    except ValueError:
        body = None

    if isinstance(body, dict) and "type" in body:
        return body

    # Synthesised so that every caller downstream sees one shape. The absence of
    # a `type` is preserved -- nothing pretends the server named a condition.
    text = (response.text or "").strip()
    return {
        "status": response.status_code,
        "title": response.reason or "Request failed",
        "detail": _first_line(text),
    }


def _first_line(text: str, limit: int = 300) -> str:
    '''One line of somebody else's HTML error page, not the whole thing.'''
    if not text:
        return ""
    if "<" in text[:100]:
        import re
        text = re.sub(r"<[^>]+>", " ", text)
    collapsed = " ".join(text.split())
    return collapsed[:limit] + ("..." if len(collapsed) > limit else "")


def _slug(problem: Dict[str, Any]) -> Optional[str]:
    '''The condition the server named, or None if it named none.'''
    uri = problem.get("type")
    if not isinstance(uri, str):
        return None
    return uri.rstrip("/").rsplit("/", 1)[-1]


def dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))
