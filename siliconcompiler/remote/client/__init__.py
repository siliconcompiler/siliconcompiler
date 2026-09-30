'''
The ``v1`` remote client.

``Client`` is the library surface; ``sc-remote`` is a thin wrapper over it, so
every capability lands here rather than in the app. That is what keeps a later
CLI rename off the critical path.
'''

import logging
import os
import sys
import time

from typing import Any, Dict, List, Optional

from siliconcompiler.remote.client.credentials import Credentials, parse_ci_secret
from siliconcompiler.remote.client.errors import (
    RemoteError, ServerProblem, SessionEnded, clean, describe)
from siliconcompiler.remote.client.identity import local_subject, display_name
from siliconcompiler.remote.client.transport import (
    EdgeRefused, LoginRequired, OAuthRefusal, Transport, normalize_server)

__all__ = [
    "Client", "Credentials", "RemoteError", "ServerProblem", "SessionEnded",
    "EdgeRefused", "describe", "SCOPES",
]


logger = logging.getLogger(__name__)


# Every registered scope, sent explicitly: an unsent parameter is an untested
# one, and a server drops what it does not recognise.
SCOPES = ("jobs:read", "jobs:write", "jobs:delete", "artifacts:read",
          "devices:read", "devices:write", "profile:read")

GRANT_CLIENT_CREDENTIALS = "client_credentials"
GRANT_DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"
GRANT_TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"

# How long before a CI credential expires the log is warned in.
CI_EXPIRY_WARNING_SECONDS = 7 * 86400

# The key rotation command, named in every message that needs it.
ROTATE_COMMAND = "sc-remote -rotate_key"

# A project a CI credential bound to one names on every create.
PROJECT_VARIABLE = "SC_REMOTE_PROJECT"

# A cancel's reason, at most: the server refuses a longer one and serves what it
# takes whole (surface D288).
MAX_CANCEL_REASON = 300


class Client:
    '''One machine talking to one server.'''

    def __init__(self, credentials: Credentials,
                 logger: Optional[logging.Logger] = None,
                 open_browser: bool = True):
        self.credentials = credentials
        self.logger = logger or logging.getLogger(__name__)
        self.open_browser = open_browser

        # How this session logged in, once it has: a CI session has no refresh
        # token and trades again instead.
        self._mode: Optional[str] = None

        # A session is this client: each notice, and each upcoming terms
        # version, is shown once in it.
        self._notices_shown = set()
        self._terms_reminded = set()

        if not credentials.address:
            # There is no default server to fall back on, so this is an error
            # rather than a redirect. It is raised on use rather than on
            # construction so that `sc-remote -configure` can build a client in
            # order to fix it.
            self._transport = None
            return

        self._transport = self._make_transport(
            normalize_server(credentials.address, credentials.port))

    def _make_transport(self, base_url: str) -> Transport:
        transport = Transport(base_url, self.credentials.key(),
                              credentials=self.credentials)
        # No access token: it is never written down, so a command starts with
        # the refresh token and spends it once.
        transport.set_tokens(None, self.credentials.refresh_token)
        transport.relogin = self._relogin
        transport.fingerprint = self._fingerprint
        transport.warn = self.logger.warning
        return transport

    ######################################################################
    # Configuration
    ######################################################################

    @property
    def transport(self) -> Transport:
        if self._transport is None:
            raise RemoteError(
                "No remote server address is configured. "
                "Run: sc-remote -configure -server https://<host>")
        return self._transport

    @property
    def base_url(self) -> Optional[str]:
        return self._transport.base_url if self._transport else None

    def print_configuration(self) -> None:
        '''What this machine would use, and what the server knows it by.'''
        if self._transport is None:
            self.logger.info("Server: not configured")
        else:
            self.logger.info(f"Server: {self.base_url}")

        self.logger.info(f"Machine key: {self.credentials.thumbprint}")
        self.logger.info(f"Session store: {self.credentials.auth_dir}")
        if self.credentials.user_id:
            self.logger.info(f"Identity on this server: {self.credentials.user_id}")

        # Names only: a header's value is a secret, and never printed.
        for origin in sorted(self.credentials.configured_origins()):
            names = ", ".join(sorted(self.credentials.headers_for(origin)))
            self.logger.info(f"Operator headers for {origin}: {names}")
        if self.credentials.ci_secret():
            self.logger.info("CI credential: present")

        whitelist = self.credentials.directory_whitelist
        self.logger.info("Directory whitelist:")
        for entry in whitelist or ["  (empty)"]:
            self.logger.info(f"  {entry}" if whitelist else entry)

    ######################################################################
    # Discovery
    ######################################################################

    def capabilities(self, notices: bool = True) -> Dict[str, Any]:
        '''``GET /v1``: the first call on every path, and it carries no
        credential.

        A JSON capabilities block means this is a ``v1`` server. What a client
        branches on inside it is ``grant_types_supported`` and never
        ``identity_assurance``, which is advisory.

        Each of its `notices` is shown once per session, which is when a person
        is reading; ``notices=False`` leaves that to the caller.
        '''
        published = self.transport.request(
            "GET", "", authenticated=False).json()
        if notices:
            self._show_notices(published)
        return published

    def _show_notices(self, published, always: bool = False) -> None:
        '''Each notice once per session, or with ``always`` every time.

        Displayed and never branched on: `level` only picks how loudly, and a
        level this client does not know is shown as a warning.
        '''
        import json

        for notice in (published.get("notices") if isinstance(published, dict)
                       else None) or []:
            key = json.dumps(notice, sort_keys=True, default=str)
            if key in self._notices_shown and not always:
                continue
            self._notices_shown.add(key)
            level, line = _notice(notice)
            (self.logger.info if level == "info" else self.logger.warning)(
                f"Notice: {line}")

    def health(self) -> Dict[str, Any]:
        '''``GET /v1/healthz``: one word, and no credential.

        🔴 **A `fail` arrives as a 503, so the refusal path IS the answer.**
        The endpoint's whole vocabulary is `pass`, `warn` and `fail`, and it
        serves the last of those with a status a client would otherwise raise
        on -- so catching it and reporting `fail` is reading the endpoint
        correctly rather than swallowing an error. Anything else that answers
        503 on this path, a proxy included, means the same thing to whoever
        asked: this deployment is not serving.
        '''
        try:
            return self.transport.request(
                "GET", "healthz", authenticated=False).json()
        except ServerProblem:
            return {"status": "fail"}
        except ValueError:
            # 200 with something that is not JSON. Up, and not this server.
            return {"status": "warn"}

    def print_deployment(self) -> None:
        '''What the server says it is, for a person at a terminal.

        The same two blocks the portal's Server screen renders, and for the
        same reason: `GET /v1` is what every client branches on, so *what does
        this deployment actually allow* should be answerable without curl and
        without a browser.

        ⚠️ Unauthenticated, both of them, so this works before enrolment and
        says the same thing to everybody.
        '''
        from siliconcompiler.remote.units import duration, size

        health = self.health()
        published = self.capabilities(notices=False)

        self.logger.info(f"Health: {health.get('status', 'unknown')}")
        self.logger.info(f"API: {published.get('api_version', 'unknown')}")
        self.logger.info(
            f"Identity assurance: {published.get('identity_assurance', 'unknown')}")

        # Every time here, which is where somebody asks for the server's
        # status; once per session everywhere else.
        self._show_notices(published, always=True)

        # Two buckets, a closed set, and both always present. They are shown
        # apart because they are satisfied apart: the whole python set has to
        # be in ONE image and a tool is resolved per node.
        software = published.get("software") or {}
        for bucket, label in (("python", "Python distributions"),
                              ("tools", "Tools")):
            held = software.get(bucket) or {}
            self.logger.info(f"{label} it can run:")
            for name, versions in sorted(held.items()):
                self.logger.info(f"  {name}: {', '.join(versions)}")
            if not held:
                self.logger.info("  (none advertised)")

        self.logger.info(
            f"Sign-in: {', '.join(published.get('grant_types_supported') or []) or 'none'}")
        self.logger.info(
            f"Features: {', '.join(published.get('features') or []) or 'none'}")

        self.logger.info("Limits:")
        for name, value in (published.get("limits") or {}).items():
            # null is unlimited, which is the wire's meaning for it
            # everywhere, and it is not zero.
            if value is None:
                shown = "unlimited"
            elif name.endswith("_bytes"):
                shown = size(value)
            elif name.endswith("_seconds"):
                shown = duration(value)
            else:
                shown = str(value)
            self.logger.info(f"  {name}: {shown}")

        if published.get("terms_url"):
            self.logger.info(f"Terms: {published['terms_url']}")

    def print_identity(self, identity: Dict[str, Any]) -> None:
        '''Who the server says you are, the session this machine holds, and
        what you have used -- all from one `GET /v1/me`, which rotates
        nothing, so showing a session never refreshes it (surface §5).'''
        from siliconcompiler.remote.units import duration, size

        self.logger.info(f"Server reports you as {identity['id']} "
                         f"(issuer {identity['issuer']})")

        session = identity.get("session") or {}
        if session:
            where = f" on device {session['device_id']}" if session.get("device_id") else ""
            self.logger.info(f"Session: {session.get('kind', 'unknown')}{where}")
            self.logger.info(f"  scope: {session.get('scope') or '(none)'}")
            self.logger.info(f"  access token until {session.get('access_expires_at')}")
            self.logger.info("  refresh token until "
                             f"{session.get('refresh_expires_at') or '(none: it cannot refresh)'}")
            self.logger.info(f"  ends at {session.get('session_expires_at')}, "
                             "and is never extended")

        usage = identity.get("usage") or {}
        self.logger.info(f"Jobs running: {usage.get('concurrent_jobs', 0)}")
        compute = usage.get("compute_seconds") or {}
        if compute:
            total = compute.get("total")
            self.logger.info(f"Compute: {duration(compute.get('used') or 0)} this month"
                             + (f", {duration(total)} in all" if total is not None else ""))
        stored = usage.get("storage_bytes") or {}
        if stored:
            self.logger.info(f"Storage: {size(stored.get('used') or 0)}")

    ######################################################################
    # Sessions
    ######################################################################

    def login(self) -> Dict[str, Any]:
        '''Obtain a session, the way this deployment offers one.

        🔴 **The login algorithm** (identity §3): `client_credentials` where it
        is offered; token exchange where this caller holds a CI credential;
        otherwise the device grant. What is offered is cached beside the
        credential, per server, and `unsupported_grant_type` -- from either
        OAuth endpoint -- is the only thing that says the cache is stale. A
        `401`, a timeout or a `503` means try again later, never switch.
        '''
        offered = self.credentials.session_value("grant_types_supported")
        if not offered:
            offered = self._grant_types()

        tried = set()
        while True:
            mode = self._choose(offered, tried)
            try:
                return self._login_with(mode)
            except OAuthRefusal as e:
                if e.error != "unsupported_grant_type" or mode in tried:
                    raise self._refused(e, mode) from None
                # Stale: switch, and refresh what is cached.
                tried.add(mode)
                offered = [grant for grant in self._grant_types() if grant not in tried]

    def _grant_types(self) -> List[str]:
        offered = list(self.capabilities().get("grant_types_supported") or [])
        self.credentials.update_session(grant_types_supported=offered)
        return offered

    def _choose(self, offered, tried) -> str:
        '''The two non-interactive branches do not race: which credential this
        caller holds decides. With no browser, token exchange comes before any
        user code is printed.'''
        candidates = [grant for grant in offered if grant not in tried]
        if GRANT_CLIENT_CREDENTIALS in candidates:
            return GRANT_CLIENT_CREDENTIALS
        if self.credentials.ci_secret() and GRANT_TOKEN_EXCHANGE in candidates:
            return GRANT_TOKEN_EXCHANGE
        if GRANT_DEVICE_CODE in candidates:
            return GRANT_DEVICE_CODE
        raise RemoteError(
            f"{self.base_url} offers no login this client can use "
            f"(it offers {', '.join(offered) or 'none'})")

    def _login_with(self, mode: str) -> Dict[str, Any]:
        if mode == GRANT_CLIENT_CREDENTIALS:
            body = self._login_client_credentials()
        elif mode == GRANT_TOKEN_EXCHANGE:
            body = self._trade_login()
        else:
            body = self._login_device()
        self._mode = mode
        self.credentials.update_session(login=mode)
        return body

    def _login_client_credentials(self) -> Dict[str, Any]:
        '''``client_credentials`` against a fixed local client: no browser, no
        issuer, no prompt. The key is bound by the server on first contact.

        🔴 **No fingerprint, no access.** The subject is derived from this
        machine's id and the uid; with no id every such machine would be the
        same principal, so this refuses before asking.
        '''
        subject, machine_hash, source = local_subject()
        if source == "none":
            raise RemoteError(
                "this machine has no id to sign in with (no /etc/machine-id on "
                "Linux, no IOPlatformUUID on macOS, no MachineGuid on Windows), and "
                "the server identifies you by this machine and your user. Create one "
                "-- `systemd-machine-id-setup` on Linux -- and try again")

        form = {
            "grant_type": GRANT_CLIENT_CREDENTIALS,
            "client_id": f"local:{subject}",
            "machine_id_source": source,
            "display_name": display_name(),
            "scope": " ".join(SCOPES),
        }
        if machine_hash:
            form["machine_id_hash"] = machine_hash

        body = self.transport.login(form)
        self.credentials.save_tokens(body)
        return body

    def _login_device(self) -> Dict[str, Any]:
        '''The device grant: a code for a person, a browser, and a poll.

        The URL is opened where a browser can be, and printed with the code
        always -- for a headless machine, and for a launch that fails silently.
        '''
        import platform

        form = {"scope": " ".join(SCOPES),
                "requesting_host": platform.node() or "unknown",
                "device_label": display_name(), **self._fingerprint()}

        while True:
            started = self.transport.request(
                "POST", "auth/device", authenticated=False, data=form, oauth=True,
                headers={"Content-Type": "application/x-www-form-urlencoded"}).json()

            uri = started.get("verification_uri") or ""
            code = started.get("user_code") or ""
            self.logger.info(f"To log in, open {clean(uri)} and enter the code {clean(code)}")
            self.open_url(uri, "the login page")

            interval = max(1, int(started.get("interval") or 5))
            deadline = time.monotonic() + int(started.get("expires_in") or 600)
            while time.monotonic() < deadline:
                time.sleep(interval)
                try:
                    body = self.transport.login(
                        {"grant_type": GRANT_DEVICE_CODE,
                         "device_code": started.get("device_code", "")})
                except OAuthRefusal as e:
                    if e.error == "authorization_pending":
                        continue
                    if e.error == "slow_down":
                        interval += 5
                        continue
                    if e.error == "expired_token":
                        break
                    if e.error == "access_denied" and e.reason == "devices":
                        raise RemoteError(
                            "the login was refused because your account is at its "
                            "limit of devices: revoke a device you no longer use "
                            "in the portal, and log in again") from None
                    if e.error == "access_denied":
                        raise RemoteError("the login was denied") from None
                    raise
                self.credentials.save_tokens(body)
                return body
            self.logger.info("The code expired before it was approved; starting again.")

    def _trade_login(self) -> Dict[str, Any]:
        body = self._trade()
        self.transport.trade = self._trade_again
        return body

    def _trade_again(self) -> bool:
        self._trade()
        return True

    def _trade(self) -> Dict[str, Any]:
        '''Token exchange: the CI credential traded for one access token.

        No refresh token comes back, so each new access token is a new trade.
        🔴 Never over plaintext: the request carries the credential itself.
        '''
        import uuid

        import jwt

        from siliconcompiler.remote import dpop
        from siliconcompiler.remote.client.transport import origin_of

        if not self.transport.base_url.startswith("https://"):
            raise RemoteError("a CI credential is exchanged only over https, and "
                              f"{self.transport.base_url} is not")

        credential_id, credential_key = parse_ci_secret(self.credentials.ci_secret())
        issued = int(time.time())
        assertion = jwt.encode(
            {"iss": credential_id, "sub": credential_id,
             "aud": origin_of(self.transport.base_url),
             "jti": str(uuid.uuid4()), "iat": issued, "exp": issued + 300,
             # Bound to the key that signs this request's proof, so it cannot
             # be re-paired with somebody else's.
             "cnf": {"jkt": self.credentials.thumbprint}},
            credential_key, algorithm=dpop.ALGORITHM)

        form = {"grant_type": GRANT_TOKEN_EXCHANGE,
                "subject_token": assertion,
                "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token"}
        try:
            body = self.transport.login(form)
        except OAuthRefusal as e:
            if e.error == "invalid_grant":
                raise RemoteError(self._ci_refusal(e.reason)) from None
            raise

        left = body.get("session_expires_in")
        if isinstance(left, int) and left <= CI_EXPIRY_WARNING_SECONDS:
            days = max(0, left // 86400)
            message = (f"This CI credential expires in {days} day{'s' if days != 1 else ''}: "
                       "mint a new one in the portal and replace the secret")
            if os.environ.get("GITHUB_ACTIONS") == "true":
                print(f"::warning::{message}", flush=True)
            self.logger.warning(message)
        return body

    @staticmethod
    def _ci_refusal(reason: Optional[str]) -> str:
        return {
            "expired": "the CI credential has expired: mint a new one in the portal "
                       "and replace the secret",
            "revoked": "the CI credential was revoked: ask for a new one",
            "deactivated": "the account this CI credential belongs to is deactivated",
        }.get(reason, "the CI credential was refused")

    def _refused(self, refusal: OAuthRefusal, mode: str) -> RemoteError:
        '''What a failed login tells the person.'''
        if refusal.error == "invalid_client":
            subject = local_subject()[0]
            return RemoteError(
                "this server knows you by a different key: "
                f"{clean(refusal.description or 'the subject is bound to another key')}. "
                "Retrying will not help. An operator can release the binding: "
                "python3 -m siliconcompiler.remote.server.software.registry release-binding "
                f"{subject}")
        return RemoteError(str(refusal))

    def _relogin(self, reason: Optional[str]) -> None:
        '''The session is over: re-authenticate, and never refresh.'''
        if reason == "reused":
            # The rotation revokes the old device with the old key first, so a
            # server that binds a subject to one key takes the new one too.
            self.logger.warning(
                "This session was ended because its refresh token was used twice: your "
                "credentials were used elsewhere. Replace this machine's key with "
                f"`{ROTATE_COMMAND}`, which also revokes the device the old key is bound "
                "to, ending every session it holds.")
        elif reason:
            self.logger.info(f"This session has ended ({reason}); starting a new one.")
        self.login()

    def _fingerprint(self) -> Dict[str, str]:
        '''The fingerprint pair, derived and never stored; nothing where nothing
        can be derived, and nothing on a CI session.'''
        if self._mode == GRANT_TOKEN_EXCHANGE:
            return {}
        _, machine_hash, source = local_subject()
        if source == "none" or not machine_hash:
            return {}
        return {"machine_id_hash": machine_hash, "machine_id_source": source}

    def ensure_session(self) -> None:
        '''Get an access token for this command, the cheapest way there is.

        🔴 The refresh token is spent FIRST and a fresh grant is the fallback:
        `client_credentials` mints a new token family every time, so logging in
        per command would leave a trail of live sessions behind.
        '''
        if self.transport.access_token is not None:
            return
        if self.credentials.session_value("login") == GRANT_TOKEN_EXCHANGE:
            self._mode = GRANT_TOKEN_EXCHANGE
            self._trade_login()
            return
        try:
            if self.transport.refresh():
                return
        except SessionEnded as e:
            self._relogin(e.reason)
            return
        except LoginRequired:
            self.logger.info("This machine must log in again.")
        self.login()

    def rotate_key(self) -> None:
        '''Replace this machine's DPoP key, and enrol again as a new device.

        The one deliberate act that changes the key; no error ever does.

        🔴 **The old key ends its own device first.** It is still here, so it
        can prove possession one last time: revoking the device it is bound to
        ends every session that device holds -- whoever else is using them --
        and, on a server that binds a subject to the key it first saw, frees
        the subject for the new one. Without it `sc-server` refuses the new key
        `invalid_client` until an operator releases the binding. Where the old
        device cannot be revoked -- the server is unreachable -- the key is
        replaced anyway, and the login below says what the server answered.
        '''
        old = self.credentials.thumbprint
        if self._transport is not None:
            self._retire_this_device()
        self.credentials.rotate_key()
        if self._transport is not None:
            self._transport = self._make_transport(self._transport.base_url)
        self.logger.info(f"Replaced this machine's key ({old[:12]}... -> "
                         f"{self.credentials.thumbprint[:12]}...)")
        if self._transport is not None:
            self.login()
            self.logger.info("Logged in again as a new device.")

    def _retire_this_device(self) -> None:
        '''Revoke the device the current key is bound to, with that key, and
        forget its session here.'''
        try:
            self.ensure_session()
            current = next((device for device in self.devices() if device.get("current")),
                           None)
            if current is not None:
                self.revoke_device(current["id"])
                self.logger.info(f"Revoked this machine's device under the old key "
                                 f"({clean(str(current.get('name') or current['id']))}).")
        except RemoteError as e:
            self.logger.warning(
                f"Could not revoke this machine's device under the old key ({e}); the "
                "server may refuse the new key until its operator releases the binding.")
        finally:
            self.credentials.forget_tokens()
            self.transport.set_tokens(None, None)

    def logout(self) -> None:
        '''End this session on the server, then forget it here.

        Revoking needs a live access token and this client holds none between
        commands, so the refresh token is spent to get one.
        '''
        try:
            if self.transport.access_token is None:
                self.transport.refresh()
            if self.transport.access_token is not None:
                self.transport.request("POST", "auth/revoke")
        except (SessionEnded, RemoteError) as e:
            # Already over, or unreachable. Forgetting it locally is the whole
            # remaining job either way, and it must still happen.
            logger.debug(f"could not revoke on the server: {e}")
        finally:
            self.credentials.forget_tokens()
            self.transport.set_tokens(None, None)

    ######################################################################
    # CI and operator headers
    ######################################################################

    def ci_setup(self, server: Optional[str] = None) -> None:
        '''Write the store from the CI secret, for a CI job.

        The secret is read from the environment. On GitHub Actions the store
        goes in the job's own temporary directory, which the runner empties
        between jobs, and SC_AUTH_DIR is exported to the job's later steps. On a
        terminal it then asks for any headers the server's access layer needs;
        a pipeline sets each with `sc-remote -header <name>`, the value on
        standard input.
        '''
        from siliconcompiler.remote.client.credentials import (
            AUTH_DIR_VARIABLE, CI_SECRET_VARIABLE)

        secret = os.environ.get(CI_SECRET_VARIABLE)
        if not secret:
            raise RemoteError(f"{CI_SECRET_VARIABLE} is not set: it holds the one-line "
                              "CI credential")
        parse_ci_secret(secret)

        runner_temp = os.environ.get("RUNNER_TEMP")
        if runner_temp and not os.environ.get(AUTH_DIR_VARIABLE):
            from pathlib import Path

            self.credentials.auth_dir = Path(runner_temp) / "sc-auth"
            exported = os.environ.get("GITHUB_ENV")
            if exported:
                with open(exported, "a") as f:
                    f.write(f"{AUTH_DIR_VARIABLE}={self.credentials.auth_dir}\n")

        if server:
            address, port, _ = _split_address(server.strip())
            self.credentials.update(address=address, port=port)
            self._transport = self._make_transport(normalize_server(address, port))

        self.credentials.save_ci_secret(secret)
        self.logger.info(f"CI credential stored in {self.credentials.auth_dir}")
        self.ask_headers()

    def ask_headers(self) -> None:
        '''Ask for the headers the server's access layer requires, name then
        hidden value, until a blank name. Nothing is asked without a terminal.'''
        if not sys.stdin.isatty():
            self.logger.info("Set any header the server's access layer requires with "
                             "`sc-remote -header <name>`, the value on standard input.")
            return
        while True:
            name = input("Header the server's access layer requires (blank when done): ")
            if not name.strip():
                return
            self.set_header(name.strip(), read_secret(name.strip()))

    def set_header(self, name: str, value: Optional[str], origin: Optional[str] = None) -> None:
        '''An operator-configured header for an origin, the API's by default.
        Its value is a secret, kept in the store and never printed.'''
        origin = origin or self.transport.api_origin
        self.credentials.set_header(origin, name, value)
        self.logger.info(f"{'Set' if value is not None else 'Removed'} the {name} header "
                         f"for {origin}")

    def open_url(self, url: str, what: str, require_tty: bool = True) -> bool:
        '''Open a URL a person has to act on -- only `https`, or `http` from a
        deployment that authenticates nobody -- and never anything else.'''
        from urllib.parse import urlsplit

        scheme = urlsplit(url or "").scheme
        unauthenticated = GRANT_CLIENT_CREDENTIALS in (
            self.credentials.session_value("grant_types_supported") or [])
        if scheme != "https" and not (scheme == "http" and unauthenticated):
            self.logger.warning(f"Not opening {what}: {clean(url)} is not an https URL")
            return False
        if not self.open_browser or (require_tty and not sys.stdout.isatty()):
            return False
        import webbrowser

        try:
            return bool(webbrowser.open(url))
        except Exception:                                        # noqa: BLE001
            return False

    ######################################################################
    # Identity
    ######################################################################

    def me(self, remind: bool = True) -> Dict[str, Any]:
        '''``GET /v1/me``, and remember which principal this server saw.

        An upcoming terms version not yet accepted is named once per session;
        ``remind=False`` leaves that to the caller.
        '''
        self.ensure_session()
        body = self.transport.request("GET", "me").json()

        seen = self.credentials.user_id
        if seen and seen != body.get("id"):
            # Not an error: a reimage, a new container or a changed uid each
            # mint a new identity without anyone doing anything wrong. Saying so
            # is what stops it reading as "my jobs were deleted".
            self.logger.warning(
                "This server now knows this machine as a different user "
                f"({seen} -> {body.get('id')}). Jobs submitted as the previous "
                "identity are not visible to this one.")

        self.credentials.update(user_id=body.get("id"))
        if remind:
            self.remind_terms(body)
        return body

    def remind_terms(self, me: Dict[str, Any], always: bool = False) -> None:
        '''Each upcoming terms version this person has not accepted: the
        document, the version and when it takes effect, with where to accept
        it, so the change need not first reach them as a refused submit.

        Once per session, or with ``always`` every time. 🔴 **Never accepted
        here**: accepting is the person's, in a browser. On an interactive
        terminal outside CI this offers to open the page; a CI run only
        reports it.
        '''
        for entry in (me.get("terms") if isinstance(me, dict) else None) or []:
            if not isinstance(entry, dict):
                continue
            upcoming = entry.get("upcoming")
            if not isinstance(upcoming, dict) or upcoming.get("accepted_at") is not None:
                continue
            key = (entry.get("id"), upcoming.get("version"))
            if key in self._terms_reminded and not always:
                continue
            self._terms_reminded.add(key)

            title = clean(entry.get("title") or entry.get("id") or "A terms document")
            when = upcoming.get("effective_at")
            self.logger.warning(
                f"{title}: version {clean(upcoming.get('version') or '?')} takes effect"
                + (f" {clean(when)}" if when else "")
                + ", and you have not accepted it. Once it does, a submit it covers is "
                  "refused until you have.")

            url = entry.get("decision_url")
            if not isinstance(url, str) or not url:
                continue
            self.logger.warning(f"  It may be accepted early, at {clean(url)}")
            interactive = sys.stdin.isatty() and sys.stdout.isatty()
            if interactive and not self._in_ci() and self.open_browser:
                if _ask("Open it in a browser? [y/N] ").strip().lower() in ("y", "yes"):
                    self.open_url(url, "the terms page")

    def _in_ci(self) -> bool:
        return self._mode == GRANT_TOKEN_EXCHANGE or bool(os.environ.get("CI")) \
            or bool(self.credentials.ci_secret())

    def devices(self) -> list:
        '''The machines that can act as me, following ``Link`` to the end.'''
        self.ensure_session()

        items, params = [], {}
        while True:
            response = self.transport.request("GET", "devices", params=params)
            items.extend(response.json().get("items") or [])
            cursor = _next_cursor(response.headers.get("Link"))
            if not cursor:
                return items
            params = {"cursor": cursor}

    def revoke_device(self, device_id: str) -> None:
        '''Revoke a machine, ending every session it holds.'''
        self.ensure_session()
        self.transport.request("DELETE", f"devices/{device_id}")

    ######################################################################
    # Jobs
    ######################################################################

    def create_job(self, design: str, jobname: str, *,
                   flow: Optional[str] = None,
                   node_count: Optional[int] = None,
                   needs: Optional[List[str]] = None,
                   requested_versions: Optional[Dict[str, Any]] = None,
                   sources: Optional[List[Dict[str, Any]]] = None,
                   run_hash: Optional[str] = None,
                   continues_from: Optional[List[Dict[str, str]]] = None,
                   python_packages: Optional[Dict[str, List[str]]] = None,
                   idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        '''``POST /v1/jobs``: the job exists, and nothing has moved yet.
        Returns the job object, in `created`.

        ``design`` and ``jobname`` are authoritative -- nothing in a manifest
        names either, so the server cannot re-derive them. Everything else goes
        in the ``descriptor``: advisory, re-derived at submit, and present only
        to let the server refuse before the archive uploads.

        ``flow`` and ``node_count`` are the flowgraph's name and how many nodes
        it has, so a flow over ``max_job_nodes`` is refused before it uploads.

        ``requested_versions`` is what the image must HOLD, keyed on ``python`` and
        ``tools``, every value a list of PEP 440 specifier sets. 🔴 It names
        every Python distribution the job imports, pinned exactly: a name left
        out is not required, and the job may land in an image without it. The
        split is structural -- the whole ``python`` set shares an interpreter,
        so ONE image has to hold all of it, while a tool is satisfied per node.

        ``needs`` is the feature strings the job relies on; a server lacking
        one refuses here rather than after the upload.

        ``run_hash`` is the client's opaque hash of the work, for job reuse --
        top level, beside ``design``: the descriptor is what submit re-derives,
        and nothing recomputes this. A server advertising ``jobs.reuse`` looks
        it up owner-scoped and hands back the caller's own earlier result, with
        a ``200``. 🔴 **Nothing in this client computes one yet** -- what
        SiliconCompiler should hash is its own decision, and a hash that is
        wrong in the direction of *the same* is a wrong answer.

        ``python_packages`` is the run's Python packages an index can supply,
        ``{"requirements": [...], "constraints": [...]}`` of ``name==version``
        -- top level and authoritative, since nothing in the manifest records
        it. A job sending it names ``python.env`` in ``needs``.
        '''
        self.ensure_session()

        descriptor: Dict[str, Any] = {}
        for name, value in (("flow", flow), ("needs", needs),
                            ("requested_versions", requested_versions),
                            ("sources", sources)):
            if value:
                descriptor[name] = value
        if node_count is not None:
            descriptor["node_count"] = node_count

        body: Dict[str, Any] = {"design": design, "jobname": jobname}
        if descriptor:
            body["descriptor"] = descriptor
        # A CI credential bound to a project acts only in it, so a pipeline
        # using one names that project on every create.
        if os.environ.get(PROJECT_VARIABLE):
            body["project"] = os.environ[PROJECT_VARIABLE]
        if run_hash:
            body["run_hash"] = run_hash
        if continues_from:
            # For a run that starts part-way through its flow: each node whose
            # results this run takes from the job that ran it (surface D175).
            body["continues_from"] = continues_from
        if python_packages:
            body["python_packages"] = python_packages

        headers = {"Idempotency-Key": idempotency_key or _fresh_key()}

        return self._waiting_for_a_slot(lambda: self.transport.request(
            "POST", "jobs", json_body=body, headers=headers).json())

    def upload_grant(self, job_id: str, size: int, digest: str) -> Dict[str, Any]:
        '''``POST /v1/jobs/{id}/upload-grant``: where to put the bytes.

        Its own call rather than a member of the create response, which is what
        gives an expired grant a way back: re-issuing is this endpoint, where
        before it meant creating a second job and leaking the first.

        🔴 ``size`` and ``digest`` are the exact bytes about to go up, and the
        first grant for them fixes both: a re-issue must repeat them, and the
        server runs only bytes matching the digest.
        '''
        self.ensure_session()
        return self.transport.request("POST", f"jobs/{job_id}/upload-grant",
                                      json_body={"size_bytes": size,
                                                 "digest": digest}).json()

    def upload(self, grant: Dict[str, Any], path) -> None:
        '''Send the archive to wherever the grant points.

        🔴 ``content-length`` is dropped and recomputed from the file. The grant
        publishes the byte count it was issued for, and on a deployment whose
        descriptor carried no size that number is the server's ceiling rather
        than this archive's length -- sending it verbatim would announce a
        gigabyte and then send twenty kilobytes, and the server would wait for
        the rest for ever. The count the server enforces is in the signature,
        not in this header.
        '''
        headers = {name: value for name, value in (grant.get("headers") or {}).items()
                   if name.lower() != "content-length"}
        self.transport.put_object(grant["url"], headers, path)

    def submit_job(self, job_id: str,
                   idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        '''``POST /v1/jobs/{id}/submit``, with no body (surface §15; D277).

        The grant fixed the archive's size and digest, and the server checks
        what storage holds against the digest the grant bound -- so the bytes
        that moved are what is judged, not a freshly built archive, and there
        is nothing left for the request to say.
        '''
        self.ensure_session()

        # A fresh key on every submit, a resubmit after the job was sent back
        # included; a retry of this one reuses it.
        headers = {"Idempotency-Key": idempotency_key or _fresh_key()}

        return self._waiting_for_a_slot(lambda: self.transport.request(
            "POST", f"jobs/{job_id}/submit", json_body={}, headers=headers).json())

    def _waiting_for_a_slot(self, send):
        '''A create or a submit, with the `limit-exceeded` that only means
        *later* -- `concurrent_jobs`, `pending_uploads` -- waited out for as
        long as the server's `Retry-After` says, and retried with the same key.'''
        told = None
        while True:
            try:
                return send()
            except ServerProblem as e:
                if e.slug == "terms-not-accepted":
                    raise self._to_sign(e) from None
                limit = e.member("limit")
                if e.slug != "limit-exceeded" or not e.retry_after or \
                        limit not in ("concurrent_jobs", "pending_uploads"):
                    raise
                if told != limit:
                    told = limit
                    if limit == "pending_uploads":
                        held = ", ".join(clean(str(job)) for job in e.member("job_ids") or [])
                        self.logger.warning(
                            "Waiting: this server's limit of jobs waiting for an upload is "
                            f"reached, held by {held or 'your other jobs'}. Cancel any of "
                            "them you abandoned.")
                    else:
                        self.logger.warning(
                            "Waiting: this server's limit of running jobs is reached; "
                            "this one goes as soon as one of yours finishes.")
                time.sleep(e.retry_after)

    def _to_sign(self, refusal: ServerProblem) -> ServerProblem:
        '''A `terms-not-accepted` refusal as a person acts on it: each document
        in its `blocked_by` printed with its own link -- opened, where it may be,
        on a terminal -- and one with no link named by its title in
        `GET /v1/me`'s `terms`. Never accepted here.'''
        blocked = refusal.member("blocked_by")
        if not isinstance(blocked, dict):
            return refusal

        for entry in blocked.values():
            url = entry.get("url") if isinstance(entry, dict) else None
            if isinstance(url, str) and url:
                self.open_url(url, "the terms page")

        if all(isinstance(entry, dict) and entry.get("url") for entry in blocked.values()):
            return refusal
        try:
            terms = self.me(remind=False).get("terms") or []
        except RemoteError:
            return refusal
        titles = {entry.get("id"): entry.get("title") for entry in terms
                  if isinstance(entry, dict) and entry.get("title")}
        return ServerProblem(refusal.problem, refusal.status, help_url=refusal.help_url,
                             titles=titles, retry_after=refusal.retry_after)

    def job(self, job_id: str) -> tuple:
        '''``GET /v1/jobs/{id}``, and the interval the server asked for.

        The pace is the server's: `Retry-After` is read per response rather than
        once at the start of a run, which is what the client this replaces did
        with a single number.
        '''
        self.ensure_session()
        try:
            response = self.transport.request("GET", f"jobs/{job_id}")
        except ServerProblem as e:
            if e.slug == "not-found" and self._mode == GRANT_TOKEN_EXCHANGE:
                # A project-bound CI credential reads no job outside its
                # project, and that looks exactly like a job that is gone.
                raise ServerProblem(
                    e.problem, e.status, help_url=e.help_url, job_id=job_id,
                    next_step="The job may be gone, or this CI credential may be bound "
                              "to another project than the job's.") from None
            raise

        # The pace is the server's, in whole seconds and never below 1: a
        # value below 1 is waited as 1, and no longer floor is added here.
        retry_after = None
        header = response.headers.get("Retry-After")
        if header:
            try:
                retry_after = max(1.0, float(header))
            except ValueError:
                retry_after = None

        return response.json(), retry_after

    def jobs(self, **filters) -> list:
        '''``GET /v1/jobs``, following ``Link`` to the end.

        The cursor is opaque and is only ever taken from the header, never
        built: a cursor a client made up continues from a position the server
        never named, which silently skips rows.
        '''
        self.ensure_session()

        params = {k: v for k, v in filters.items() if v is not None}
        items = []
        path = "jobs"

        while True:
            response = self.transport.request("GET", path, params=params)
            items.extend(response.json().get("items") or [])

            link = response.headers.get("Link")
            cursor = _next_cursor(link)
            if not cursor:
                return items
            params = dict(params, cursor=cursor)

    def cancel_job(self, job_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        '''``POST /v1/jobs/{id}/cancel``. Idempotent, and the body is optional.

        🔴 A reason is always sent, because *why did this stop* is a question
        the job page has to answer: the caller's own words, else what this
        client says for itself -- with no host name, since every reader of the
        job sees it.

        It is at most `MAX_CANCEL_REASON` characters, one line (surface D288):
        a longer one is refused here, naming the limit, before anything is
        sent, as the server would refuse it rather than cut it.
        '''
        if reason is not None and (len(reason) > MAX_CANCEL_REASON or
                                   any(ord(c) < 32 or 127 <= ord(c) < 160 for c in reason)):
            raise RemoteError(f"a cancel's reason is one line of at most "
                              f"{MAX_CANCEL_REASON} characters, and this one is "
                              f"{len(reason)}")
        self.ensure_session()

        body = {"reason": reason or "cancelled from sc-remote"}
        return self.transport.request(
            "POST", f"jobs/{job_id}/cancel", json_body=body).json()

    def delete_job(self, job_id: str) -> None:
        '''``DELETE /v1/jobs/{id}``. Idempotent; the job stays readable.'''
        self.ensure_session()
        self.transport.request("DELETE", f"jobs/{job_id}")

    ######################################################################
    # Artifacts
    ######################################################################

    def artifacts(self, job_id: str, **filters) -> list:
        '''``GET /v1/jobs/{id}/artifacts``, following ``Link`` to the end.

        🔴 `items` may be `[]` and no kind is guaranteed, the manifest
        included. This returns what the server listed and judges none of it;
        deciding what an entry means is the caller's, because the five
        not-fetchable cases are five different sentences to a person.
        '''
        self.ensure_session()

        params = {k: v for k, v in filters.items() if v is not None}
        items = []
        path = f"jobs/{job_id}/artifacts"

        while True:
            response = self.transport.request("GET", path, params=params)
            items.extend(response.json().get("items") or [])

            cursor = _next_cursor(response.headers.get("Link"))
            if not cursor:
                return items
            params = dict(params, cursor=cursor)

    def fetch_artifact(self, job_id: str, artifact_id: str, dest) -> str:
        '''``GET /v1/jobs/{id}/artifacts/{artifact_id}``, followed to the bytes.

        The redirect is the contract: this endpoint never carries a payload, so
        the bytes come from wherever it points -- which on another deployment is
        a bucket on a different origin.
        '''
        self.ensure_session()

        response = self.transport.request(
            "GET", f"jobs/{job_id}/artifacts/{artifact_id}", stream=True,
            expect_redirect=True)
        return self.transport.save(self.transport.follow(response), dest)

    def node_log(self, job_id: str, step: str, index: str, dest) -> str:
        '''A finished node's log, from its `logs` artifact -- `/logs` is live
        output only.'''
        items = [item for item in self.artifacts(job_id, kind="logs", step=step, index=index)
                 if item.get("fetchable")]
        if not items:
            raise RemoteError(f"no log of {step}/{index} can be fetched")
        text = self.archived_log(job_id, items[0]["id"], step, index)
        with open(dest, "w") as f:
            f.write(text)
        return str(dest)

    def archived_log(self, job_id: str, artifact_id: str, step: str, index: str) -> str:
        '''A node's `logs` artifact -- a gzip tar of its log files -- as the
        text of its SiliconCompiler log.'''
        import tarfile
        import tempfile

        with tempfile.TemporaryDirectory(prefix="sc-log-") as tmpdir:
            path = os.path.join(tmpdir, "logs.tar.gz")
            self.fetch_artifact(job_id, artifact_id, path)
            with tarfile.open(path, "r:*") as tar:
                members = [member for member in tar.getmembers() if member.isfile()]
                own = f"sc_{step}_{index}.log"
                member = next((m for m in members if m.name == own),
                              members[0] if members else None)
                if member is None:
                    return ""
                return clean(tar.extractfile(member).read().decode(errors="replace"))

    def follow_log(self, job_id: str, step: Optional[str] = None,
                   index: Optional[str] = None, last_event_id=None):
        '''``GET /v1/jobs/{id}/logs``, followed to whatever it points at.

        With a step and an index, that node; with neither, the whole job as one
        live stream (`logs.stream.job`).

        🔴 Re-requested on every reconnect and never reused. Authorization is
        evaluated here, at the endpoint that takes the token and the proof, and
        the URL it hands back carries a lifetime of its own -- so a six-hour log
        is a sequence of capability-length streams rather than one connection
        outliving the credential that opened it.
        '''
        self.ensure_session()

        # Both or neither: one without the other is a 400, and sending
        # `step=None` would be the string "None".
        params = {"step": step, "index": index} if step is not None else {}
        response = self.transport.request(
            "GET", f"jobs/{job_id}/logs", params=params,
            stream=True, expect_redirect=True)

        headers = {}
        if last_event_id:
            headers["Last-Event-ID"] = str(last_event_id)

        return self.transport.follow(response, headers=headers, kind="stream")

    def tail_log(self, job_id: str, step: str, index: str, write=None):
        '''Read one node's log as it is written, to the end.

        Returns the text it emitted. Reconnects for as long as the node is
        running, because a capability expiring is the ordinary way a long tail
        ends rather than a failure.
        '''
        from siliconcompiler.remote.client.logs import LogTail

        return LogTail(self, job_id, step, index).follow(write=write)

    def tail_job(self, job_id: str, write=None) -> str:
        '''Read every node's log as it is written, merged, to the job's end.

        One connection for the whole job, where the server advertises
        `logs.stream.job`. Raises the server's refusal otherwise, and a
        `feature-unsupported` naming `logs.stream.job` is permanent: follow each
        running node instead.
        '''
        from siliconcompiler.remote.client.logs import LogTail

        return LogTail(self, job_id).follow(write=write)

    ######################################################################
    # sc-remote -configure
    ######################################################################

    def configure_server(self, server: Optional[str] = None,
                         clobber: bool = False,
                         prompt: bool = True) -> None:
        '''Point this machine at a server and prove it can reach it.

        There is no default address, so an unanswerable prompt is an error and
        nothing is written -- a half-written credentials file is worse than
        none, because the next command fails somewhere further away.
        '''
        if self.credentials.address and not clobber:
            if not prompt:
                raise RemoteError(
                    f"{self.credentials.path} already configures "
                    f"{self.credentials.address}; pass clobber=True instead")
            answer = _ask(f"Overwrite the configuration for "
                          f"{self.credentials.address}? [y/N] ")
            if answer.strip().lower() not in ("y", "yes"):
                self.logger.info("Left unchanged.")
                return

        if not server and prompt:
            server = _ask("Remote server address: ")

        if not server or not server.strip():
            raise RemoteError(
                "a remote server address is required: there is no default "
                "server to fall back on")

        address, port, had_credentials = _split_address(server.strip())

        if had_credentials:
            # Under v1 a username and password are not the credential -- the
            # key is. Dropping them silently would leave a user believing they
            # had configured something.
            self.logger.warning(
                "Ignoring the username and password in that address: this "
                "server authenticates with a key held on this machine, which "
                "is generated for you.")

        # user_id goes with the tokens, because all three are about ONE server
        # and the address is changing. Keeping it would make the first `me()`
        # against the new server report a drift that did not happen -- the
        # principal is different because the server is, which is the one case
        # that warning must not fire on.
        self.credentials.update(address=address, port=port, user_id=None)
        self._transport = self._make_transport(normalize_server(address, port))
        self.credentials.forget_tokens()
        self._transport.set_tokens(None, None)

        capabilities = self.capabilities()
        self.credentials.update_session(
            grant_types_supported=list(capabilities.get("grant_types_supported") or []))

        self.login()
        identity = self.me()

        self.logger.info(f"Configured {self.base_url}")
        self.logger.info(f"This machine's key: {self.credentials.thumbprint}")
        self.logger.info(f"You are {identity['id']} on this server")
        self._report_software(capabilities)
        if capabilities.get("identity_assurance") != "verified":
            # "verified" is the only value that asserts anything; every other
            # value, known or unknown, means do not rely on this identity.
            self.logger.warning(
                "This server does not verify who you are. Your jobs are "
                "separated from other users', but that separation is not a "
                "security boundary.")
        self.logger.info(f"Saved to {self.credentials.path}")

    def _report_software(self, capabilities) -> None:
        '''What this server runs, and whether this machine is on the list.

        🔴 The check is the client's and the decision is the server's, and the
        asymmetry is deliberate: a client that skips this is not broken -- it
        gets a `software-unavailable` a moment later -- and a server that trusted it
        would be. What it buys is that the mismatch is visible while somebody is
        watching, rather than at the first submit of the first job.

        Said here rather than at every run because it is the answer to a
        question `-configure` is already asking: *can this machine use that
        server*.
        '''
        from siliconcompiler import __version__ as sc_version

        # In `python`: `siliconcompiler` is a distribution in the interpreter,
        # and the bucket it is published under is part of what the key means.
        published = (capabilities.get("software") or {}).get("python") or {}
        runs = published.get("siliconcompiler")
        if not runs:
            # REQUIRED on the wire, so its absence is an older or a broken
            # server rather than a deployment with an opinion. Nothing useful
            # to say about it and nothing worth refusing over.
            return

        self.logger.info(f"This server runs siliconcompiler {', '.join(runs)}")

        if sc_version not in runs:
            self.logger.warning(
                f"This machine has {sc_version}, which is not one of them. "
                "Jobs from here will be refused when they are created -- "
                "before anything is uploaded -- until you install a version "
                "this server accepts or an operator adds yours.")

    def portal(self, open_browser: bool = True, landing: str = None) -> str:
        '''Hand this machine's browser a session, and open it there.

        🔴 The browser has none of what this client has. Identity here is a
        machine-and-uid derivation pinned to a key on first contact, and a
        browser arriving cold can present none of it -- so the client proves
        possession of the key and passes a session across.

        ⚠️ The URL it gets back is a capability and is spent on arrival. It
        reaches the browser's history and possibly an access log, and being
        single-use is what makes both worthless. It lives under a minute,
        because it is handed to a browser on the same machine and there is no
        legitimate slow path.
        '''
        self.ensure_session()

        # Outside /v1, because /v1 is exactly the contract's endpoints and this
        # is not one of them.
        # `landing` is where the browser should end up once the cookie is
        # set. Without it the handover lands on the jobs list, which is the
        # wrong answer when the caller knows exactly which job it just made.
        answer = self.transport.request(
            "POST", "/portal/session", authenticated=True, on_v1=False,
            json_body={"next": landing} if landing else {}).json()

        url = answer["url"]
        self.logger.info(f"Opening {clean(url)}")
        self.logger.info(
            f"It is good for one use and about {answer['expires_in']} seconds.")

        if open_browser and not self.open_url(url, "the portal", require_tty=False):
            self.logger.warning(
                "No browser was opened here. Paste that URL into one on this "
                "machine -- quickly.")

        return url

    def configure_whitelist(self, add=None, remove=None) -> None:
        '''Which directories may be uploaded from.

        Entries are absolute, added once, and removing one that was never there
        is not an error.
        '''
        import os.path

        entries = list(self.credentials.directory_whitelist)

        for path in add or []:
            absolute = os.path.abspath(path)
            if absolute not in entries:
                entries.append(absolute)

        for path in remove or []:
            absolute = os.path.abspath(path)
            if absolute in entries:
                entries.remove(absolute)

        self.credentials.update(directory_whitelist=entries)
        self.logger.info(f"Directory whitelist saved to {self.credentials.path}")


def _is_stream(response) -> bool:
    '''🔴 The ONLY thing that says a live tail from a finished file.

    Deliberately not a flag on the 303: a node can finish between the redirect
    and the fetch, so anything the server computed at `/logs` can be stale by
    the time it is used. What was actually served cannot be.
    '''
    return response.headers.get("Content-Type", "").startswith("text/event-stream")


def _next_cursor(link: Optional[str]) -> Optional[str]:
    '''The `cursor` of a `rel="next"` link, or None on the last page.'''
    if not link or 'rel="next"' not in link:
        return None

    from urllib.parse import parse_qs, urlsplit

    target = link.split(">", 1)[0].lstrip("<")
    values = parse_qs(urlsplit(target).query).get("cursor")
    return values[0] if values else None


def _fresh_key() -> str:
    '''An `Idempotency-Key`: fresh per create and per submit.'''
    import uuid

    return str(uuid.uuid4())


def _notice(notice) -> tuple:
    '''A notice as ``(level, line)``. An unknown level, or a notice that is
    not an object, is shown as a warning: the cautious default.'''
    if not isinstance(notice, dict):
        return "warning", clean(str(notice))
    level = notice.get("level") if notice.get("level") in ("info", "warning") else "warning"
    line = clean(notice.get("message") or "")
    starts, ends = notice.get("starts_at"), notice.get("ends_at")
    if starts and ends:
        line += f" ({clean(starts)} to {clean(ends)})"
    elif starts:
        line += f" (from {clean(starts)})"
    elif ends:
        line += f" (until {clean(ends)})"
    return level, line


def _ask(question: str) -> str:
    '''A prompt that a scripted run answers by failing rather than hanging.'''
    try:
        return input(question)
    except EOFError:
        raise RemoteError(
            "no answer available and no default to fall back on: "
            "choose a server address with -server") from None


def read_secret(name: str) -> str:
    '''A header value: hidden on a terminal, one line of standard input
    otherwise, and never an argument, where shell history would keep it.'''
    if sys.stdin.isatty():
        import getpass
        value = getpass.getpass(f"Value for {name}: ")
    else:
        value = sys.stdin.readline().rstrip("\r\n")
    if not value:
        raise RemoteError(f"no value was given for {name}")
    return value


def _split_address(server: str):
    '''Split an address into its parts, keeping the scheme it was given.

    A port in the address is split out; a username and password in it are
    reported as ignored rather than stored, because they are not the credential
    any more.
    '''
    from urllib.parse import urlsplit

    if "://" not in server:
        server = f"https://{server}"

    parts = urlsplit(server)
    had_credentials = bool(parts.username or parts.password)

    host = parts.hostname or ""
    if parts.path.rstrip("/"):
        host += parts.path.rstrip("/")

    return f"{parts.scheme}://{host}", parts.port, had_credentials
