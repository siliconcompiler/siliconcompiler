'''The ``v1`` remote client: ``Client`` is the library, ``sc-remote`` a thin wrapper over it.'''

import logging
import os
import re
import sys
import time

from typing import Any, Dict, List, Optional

from siliconcompiler.remote.client.credentials import Credentials, parse_ci_secret
from siliconcompiler.remote.client.errors import (
    RemoteError, ServerProblem, SessionEnded, clean, describe)
from siliconcompiler.remote.client.identity import local_subject, display_name
from siliconcompiler.remote.client.transport import (
    EdgeRefused, LoginRequired, OAuthRefusal, Transport, _retry_after, normalize_server,
    origin_of)

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

CI_EXPIRY_WARNING_SECONDS = 7 * 86400

ROTATE_COMMAND = "sc-remote -rotate_key"

# Named on every create by a CI credential bound to a project.
PROJECT_VARIABLE = "SC_REMOTE_PROJECT"

# The server refuses a longer cancel reason rather than cutting it.
MAX_CANCEL_REASON = 300

# What a cancel's reason may not hold: a control character.
_UNPRINTABLE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class Client:
    '''One machine talking to one server.'''

    def __init__(self, credentials: Credentials,
                 logger: Optional[logging.Logger] = None,
                 open_browser: bool = True):
        self.credentials = credentials
        self.logger = logger or logging.getLogger(__name__)
        self.open_browser = open_browser

        # The grant this session logged in with: a CI session trades, never refreshes.
        self._mode: Optional[str] = None

        # Each notice and upcoming terms version is shown once per client.
        self._notices_shown = set()
        self._terms_reminded = set()

        if not credentials.server:
            # Raised on use, not here, so `sc-remote -configure` can build a client to fix it.
            self._transport = None
            return

        self._transport = self._make_transport(credentials.server)

    def _make_transport(self, base_url: str) -> Transport:
        transport = Transport(base_url, self.credentials.key(), self.credentials)
        transport.relogin = self._relogin
        transport.fingerprint = self._fingerprint
        transport.warn = self.logger.warning
        return transport

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

        # Names only: a header's value is a secret.
        if self._transport is not None:
            names = ", ".join(sorted(self.credentials.headers()))
            if names:
                self.logger.info(f"Operator headers: {names}")
        if self.credentials.ci_secret():
            self.logger.info("CI credential: present")

        whitelist = self.credentials.directory_whitelist
        self.logger.info("Directory whitelist:")
        for entry in whitelist or ["  (empty)"]:
            self.logger.info(f"  {entry}" if whitelist else entry)

    def capabilities(self, notices: bool = True) -> Dict[str, Any]:
        '''``GET /v1``, sent with no credential.

        Branch on ``grant_types_supported``, never ``identity_assurance``, which
        is advisory. ``notices=False`` leaves showing the notices to the caller.
        '''
        published = self.transport.request(
            "GET", "", authenticated=False).json()
        if notices:
            self._show_notices(published)
        return published

    def _show_notices(self, published, always: bool = False) -> None:
        '''Each notice once per session, or with ``always`` every time. Never
        branched on: `level` only picks how loudly.'''
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

        A `fail` arrives as a 503, so the refusal path IS the answer, not a
        swallowed error.
        '''
        try:
            return self.transport.request(
                "GET", "healthz", authenticated=False).json()
        except ServerProblem:
            return {"status": "fail"}
        except ValueError:
            # 200 but not JSON: up, and not this server.
            return {"status": "warn"}

    def print_deployment(self) -> None:
        '''What the server says it is, for a person at a terminal.

        Unauthenticated, so it works before enrolment and says the same to everybody.
        '''
        health = self.health()
        published = self.capabilities(notices=False)

        self.logger.info(f"Health: {clean(health.get('status', 'unknown'))}")
        self.logger.info(f"API: {clean(published.get('api_version', 'unknown'))}")
        self.logger.info(
            f"Identity assurance: {clean(published.get('identity_assurance', 'unknown'))}")

        self._show_notices(published, always=True)

        # Apart, as they are satisfied apart: the python set in ONE image, a tool per node.
        software = published.get("software") or {}
        for bucket, label in (("python", "Python distributions"),
                              ("tools", "Tools")):
            held = software.get(bucket) or {}
            self.logger.info(f"{label} it can run:")
            for name, versions in sorted(held.items()):
                self.logger.info(f"  {clean(name)}: {_listed(versions)}")
            if not held:
                self.logger.info("  (none advertised)")

        self.logger.info(f"Sign-in: {_listed(published.get('grant_types_supported'))}")
        self.logger.info(f"Features: {_listed(published.get('features'))}")

        # Defaults only: an account's own are in `GET /v1/me`.
        self._print_limits("Default limits:", published.get("limits"))

        if published.get("terms_url"):
            self.logger.info(f"Terms: {clean(published['terms_url'])}")

    def _print_limits(self, heading: str, limits) -> None:
        '''Each limit under ``heading``, in readable units.'''
        from siliconcompiler.utils.units import format_binary, format_duration

        if not limits:
            return
        self.logger.info(heading)
        for name, value in limits.items():
            # null is unlimited, not zero.
            if value is None:
                shown = "unlimited"
            elif name.endswith("_bytes"):
                shown = format_binary(value, "B", digits=1, show_unit=True, compact=True,
                                      default="—")
            elif name.endswith("_seconds"):
                shown = format_duration(value)
            else:
                shown = clean(value)
            self.logger.info(f"  {clean(name)}: {shown}")

    def print_identity(self, identity: Dict[str, Any]) -> None:
        '''Who the server says you are, this machine's session, your limits,
        usage and terms, from one `GET /v1/me`.'''
        from siliconcompiler.utils.units import format_binary, format_duration

        self.logger.info(f"Server reports you as {clean(identity['id'])} "
                         f"(issuer {clean(identity['issuer'])})")

        session = identity.get("session") or {}
        if session:
            where = f" on device {clean(session['device_id'])}" \
                if session.get("device_id") else ""
            self.logger.info(f"Session: {clean(session.get('kind', 'unknown'))}{where}")
            self.logger.info(f"  scope: {clean(session.get('scope') or '(none)')}")
            self.logger.info(f"  access token until {clean(session.get('access_expires_at'))}")
            self.logger.info("  refresh token until " + clean(
                session.get('refresh_expires_at') or '(none: it cannot refresh)'))
            self.logger.info(f"  ends at {clean(session.get('session_expires_at'))}, "
                             "and is never extended")

        if identity.get("can_submit") is False:
            self.logger.warning(describe({"title": "You cannot submit jobs here",
                                          "type": identity.get("blocked_type")}))

        self._print_limits("Your limits:", identity.get("limits"))

        usage = identity.get("usage") or {}
        self.logger.info(f"Unfinished jobs (staging, queued, running or cancelling): "
                         f"{clean(usage.get('concurrent_jobs', 0))}")
        compute = usage.get("compute_seconds") or {}
        if compute:
            total = compute.get("total")
            window = compute.get("window")
            # `used` is this window's; with no window, it is the whole.
            period = (_WINDOWS.get(window) or f"in this {clean(window)} window") \
                if window else "in all"
            self.logger.info(f"Compute: {format_duration(compute.get('used') or 0)} {period}"
                             + (f", {format_duration(total)} in all" if total is not None else ""))
        stored = usage.get("storage_bytes") or {}
        if stored:
            used = format_binary(stored.get("used") or 0, "B", digits=1, show_unit=True,
                                 compact=True, default="—")
            self.logger.info(f"Storage: {used}")

        terms = [entry for entry in identity.get("terms") or [] if isinstance(entry, dict)]
        if terms:
            self.logger.info("Terms:")
        for entry in terms:
            title = clean(entry.get("title") or entry.get("id") or "A terms document")
            decided = "accepted" if entry.get("accepted_at") else \
                "declined" if entry.get("declined_at") else "undecided"
            self.logger.info(f"  {title}, version {clean(entry.get('version') or '?')}: "
                             f"{decided}")
            # Not after a decline, which drops the prompt; nor where the reminder of
            # its upcoming version has just offered the same page.
            upcoming = entry.get("upcoming") if isinstance(entry.get("upcoming"), dict) else {}
            if entry.get("can_decide") is True and entry.get("declined_at") is None \
                    and entry.get("id") and \
                    (entry["id"], upcoming.get("version")) not in self._terms_reminded:
                self.logger.info("    It may be decided on its page in this server's portal.")
                self._offer_terms_page(entry["id"], title)

    def login(self) -> Dict[str, Any]:
        '''Obtain a session, the way this deployment offers one.

        Only `unsupported_grant_type` switches grant: that one is dropped and
        `GET /v1` reread. A `401`, timeout or `503` means later, never switch.
        A CI key goes straight to token exchange and never prints a
        `user_code`.
        '''
        if self.credentials.ci_secret():
            return self._ci_login()

        offered = self._grant_types()

        tried = set()
        while True:
            mode = self._choose(offered, tried)
            try:
                return self._login_with(mode)
            except OAuthRefusal as e:
                if e.error != "unsupported_grant_type":
                    raise self._refused(e, mode) from None
                tried.add(mode)
                offered = [grant for grant in self._grant_types() if grant not in tried]

    def _grant_types(self) -> List[str]:
        '''What `GET /v1` offers, reread for each login, which is rare.'''
        return list(self.capabilities().get("grant_types_supported") or [])

    def _ci_login(self) -> Dict[str, Any]:
        '''Token exchange for a CI key, retried once if `GET /v1` offers it after
        `unsupported_grant_type`. Never falls back to another grant.'''
        try:
            return self._login_with(GRANT_TOKEN_EXCHANGE)
        except OAuthRefusal as e:
            if e.error != "unsupported_grant_type":
                raise self._refused(e, GRANT_TOKEN_EXCHANGE) from None
        if GRANT_TOKEN_EXCHANGE in self._grant_types():
            try:
                return self._login_with(GRANT_TOKEN_EXCHANGE)
            except OAuthRefusal as e:
                if e.error != "unsupported_grant_type":
                    raise self._refused(e, GRANT_TOKEN_EXCHANGE) from None
        raise RemoteError(
            f"{self.base_url} has no non-interactive login for a CI credential: it "
            "offers no token exchange. Run this job against a deployment that does, "
            "or without the CI credential")

    def _choose(self, offered, tried) -> str:
        '''`client_credentials` first, needing no person, then the device grant.'''
        candidates = [grant for grant in offered if grant not in tried]
        if GRANT_CLIENT_CREDENTIALS in candidates:
            return GRANT_CLIENT_CREDENTIALS
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
        return body

    def _login_client_credentials(self) -> Dict[str, Any]:
        '''``client_credentials``: no browser, no prompt; the server binds the key on first contact.

        No machine id, no access: every such machine would be one principal.
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
        '''The device grant: a code for a person, a browser, and a poll. The URL
        and code are always printed, for a headless machine or a silent launch failure.'''
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
        self.transport.trade = self._trade
        return body

    def _trade(self) -> Dict[str, Any]:
        '''Trade the CI credential for one access token; no refresh token comes back.

        Never over plaintext: the request carries the credential itself.
        '''
        import uuid

        import jwt

        from siliconcompiler.remote import dpop

        if not self.transport.base_url.startswith("https://"):
            raise RemoteError("a CI credential is exchanged only over https, and "
                              f"{self.transport.base_url} is not")

        credential_id, credential_key = parse_ci_secret(self.credentials.ci_secret())
        issued = int(time.time())
        assertion = jwt.encode(
            {"iss": credential_id, "sub": credential_id,
             "aud": origin_of(self.transport.base_url),
             "jti": str(uuid.uuid4()), "iat": issued, "exp": issued + 300,
             # Bound to this request's proof key, so it cannot be re-paired.
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
                raise RemoteError({
                    "expired": "the CI credential has expired: mint a new one in the "
                               "portal and replace the secret",
                    "revoked": "the CI credential was revoked: ask for a new one",
                    "deactivated": "the account this CI credential belongs to is "
                                   "deactivated",
                }.get(e.reason, "the CI credential was refused")) from None
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
            self.logger.warning(
                "This session was ended because its refresh token was used twice: your "
                "credentials were used elsewhere. Replace this machine's key with "
                f"`{ROTATE_COMMAND}`, which also revokes the device the old key is bound "
                "to, ending every session it holds.")
        elif reason:
            self.logger.info(f"This session has ended ({reason}); starting a new one.")
        self.login()

    def _fingerprint(self) -> Dict[str, str]:
        '''The fingerprint pair, derived and never stored; empty on a CI session.'''
        if self._mode == GRANT_TOKEN_EXCHANGE:
            return {}
        _, machine_hash, source = local_subject()
        if not machine_hash:
            return {}
        return {"machine_id_hash": machine_hash, "machine_id_source": source}

    def ensure_session(self) -> None:
        '''Get an access token for this command, the cheapest way there is.

        Refresh FIRST: each `client_credentials` login mints a new token
        family, so logging in per command leaves live sessions behind.
        '''
        if self.transport.access_token is not None:
            return
        if self.credentials.ci_secret():
            # No refresh token to spend.
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
        '''Replace this machine's DPoP key and enrol again as a new device; no
        error ever changes the key.

        The old key revokes its own device first, ending its sessions and
        freeing the subject: else `sc-server` refuses the new key
        `invalid_client`. If that fails, the key is replaced anyway.
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
        '''Revoke the current key's device with that key, and forget its session.'''
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
            self.transport.set_tokens(None)

    def logout(self) -> None:
        '''End this session on the server, then forget it here. Revoking needs
        an access token, so the refresh token is spent for one.'''
        try:
            if self.transport.access_token is None:
                self.transport.refresh()
            if self.transport.access_token is not None:
                self.transport.request("POST", "auth/revoke")
        except (SessionEnded, RemoteError) as e:
            # Over or unreachable: forgetting it locally must still happen.
            logger.debug(f"could not revoke on the server: {e}")
        finally:
            self.credentials.forget_tokens()
            self.transport.set_tokens(None)

    def ci_setup(self, server: Optional[str] = None) -> None:
        '''Write the store from the CI secret in the environment, for a CI job.

        On GitHub Actions the store goes in `RUNNER_TEMP`, emptied between jobs,
        and SC_AUTH_DIR is exported to later steps.
        '''
        from siliconcompiler.remote.client.credentials import (
            AUTH_DIR_VARIABLE, CI_SECRET_VARIABLE)

        secret = os.environ.get(CI_SECRET_VARIABLE)
        if not secret:
            raise RemoteError(f"{CI_SECRET_VARIABLE} is not set: it holds the one-line "
                              "CI credential")
        parse_ci_secret(secret)

        configured = self.credentials.server
        runner_temp = os.environ.get("RUNNER_TEMP")
        if runner_temp and not os.environ.get(AUTH_DIR_VARIABLE):
            from pathlib import Path

            self.credentials.relocate(Path(runner_temp) / "sc-auth")
            exported = os.environ.get("GITHUB_ENV")
            if exported:
                with open(exported, "a") as f:
                    f.write(f"{AUTH_DIR_VARIABLE}={self.credentials.auth_dir}\n")

        if server:
            address, port, _ = _split_address(server.strip())
            configured = normalize_server(address, port)
        if configured:
            if configured != self.credentials.server:
                self.credentials.set_server(configured)
            self._transport = self._make_transport(configured)

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

    def set_header(self, name: str, value: Optional[str]) -> None:
        '''An operator header, sent only to the server's own origin.
        Its value is a secret, never printed.'''
        self.credentials.set_header(name, value)
        self.logger.info(f"{'Set' if value is not None else 'Removed'} the {name} header "
                         f"for {self.transport.api_origin}")

    def _unauthenticated(self) -> bool:
        '''Whether this deployment authenticates nobody: only then is an http page opened.'''
        try:
            offered = self.capabilities(notices=False).get("grant_types_supported") or []
        except RemoteError:
            return False
        return GRANT_CLIENT_CREDENTIALS in offered

    def open_url(self, url: str, what: str, require_tty: bool = True) -> bool:
        '''Open a URL a person must act on: `https`, or `http` where nobody is authenticated.'''
        from urllib.parse import urlsplit

        scheme = urlsplit(url or "").scheme
        if scheme != "https" and not (scheme == "http" and self._unauthenticated()):
            self.logger.warning(f"Not opening {what}: {clean(url)} is not an https URL")
            return False
        if not self.open_browser or (require_tty and not sys.stdout.isatty()):
            return False
        import webbrowser

        try:
            return bool(webbrowser.open(url))
        except Exception:                                        # noqa: BLE001
            return False

    def me(self, remind: bool = True) -> Dict[str, Any]:
        '''``GET /v1/me``, remembering which principal this server saw.
        ``remind=False`` leaves naming unaccepted terms to the caller.'''
        self.ensure_session()
        body = self.transport.request("GET", "me").json()

        seen = self.credentials.user_id
        if seen and seen != body.get("id"):
            # Not an error (a reimage, a changed uid), but it must not read as lost jobs.
            self.logger.warning(
                "This server now knows this machine as a different user "
                f"({seen} -> {body.get('id')}). Jobs submitted as the previous "
                "identity are not visible to this one.")

        self.credentials.set_user_id(body.get("id"))
        if remind:
            self.remind_terms(body)
        return body

    def remind_terms(self, me: Dict[str, Any], always: bool = False) -> None:
        '''Warn of each unaccepted upcoming terms version before it refuses a submit.

        Once per session, or with ``always`` every time. Never accepted here:
        that is the person's, in a browser, which a terminal outside CI offers.
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

            # `can_decide`: whether its page can take the decision.
            if entry.get("can_decide") is not True or not entry.get("id"):
                continue
            self.logger.warning("  It may be accepted early, on its page in this "
                                "server's portal.")
            self._offer_terms_page(entry["id"], title)

    def _offer_terms_page(self, terms_id: str, title: str) -> None:
        '''Open a document's page if a person here says so. Never accepted here.'''
        if sys.stdin.isatty() and self.may_open():
            if _ask("Open it in a browser? [y/N] ").strip().lower() in ("y", "yes"):
                self.open_page(f"{title}'s page", terms_id=terms_id)

    def devices(self) -> list:
        '''The machines that can act as me, following ``Link`` to the end.'''
        self.ensure_session()

        return self._pages("devices")

    def revoke_device(self, device_id: str) -> None:
        '''Revoke a machine, ending every session it holds.'''
        self.ensure_session()
        self.transport.request("DELETE", f"devices/{device_id}")

    def create_job(self, design: str, jobname: str, *,
                   flow: Optional[str] = None,
                   node_count: Optional[int] = None,
                   needs: Optional[List[str]] = None,
                   requested_versions: Optional[Dict[str, Any]] = None,
                   sources: Optional[List[Dict[str, Any]]] = None,
                   continues_from: Optional[List[Dict[str, str]]] = None,
                   python_packages: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        '''``POST /v1/jobs``: returns the job object, in `created`.

        ``design``, ``jobname`` and ``python_packages`` are authoritative: no
        manifest records them. The rest is the advisory ``descriptor``,
        re-derived at submit, there only so the server can refuse before upload.
        ``requested_versions`` is what the image must HOLD, each a list of PEP
        440 specifier sets; a ``python`` name left out may be missing from the image.
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
        project = os.environ.get(PROJECT_VARIABLE)
        if project:
            body["project"] = project
        if continues_from:
            body["continues_from"] = continues_from
        if python_packages:
            body["python_packages"] = python_packages

        headers = {"Idempotency-Key": _fresh_key()}

        try:
            return self._waiting_for_a_slot(lambda: self.transport.request(
                "POST", "jobs", json_body=body, headers=headers).json())
        except ServerProblem as e:
            # At create these two are about the project named, never a job.
            why = {"not-found": "is not one you are a member of: check its name",
                   "not-permitted": "is archived: name another"}.get(e.slug)
            if not project or not why:
                raise
            raise ServerProblem(
                e.problem, e.status, help_url=e.help_url, retry_after=e.retry_after,
                next_step=f"The project {project}, which {PROJECT_VARIABLE} names, {why}.") \
                from None

    def upload_grant(self, job_id: str, size: int, digest: str) -> Dict[str, Any]:
        '''``POST /v1/jobs/{id}/upload-grant``: where to put the bytes.

        ``size`` and ``digest`` are the exact bytes about to go up; the first
        grant fixes both, and the server runs only bytes matching the digest.
        '''
        self.ensure_session()
        return self.transport.request("POST", f"jobs/{job_id}/upload-grant",
                                      json_body={"size_bytes": size,
                                                 "digest": digest}).json()

    def upload(self, grant: Dict[str, Any], path) -> None:
        '''Send the archive to wherever the grant points.

        ``content-length`` is recomputed from the file: one announcing more
        than is sent leaves the server waiting for ever.
        '''
        headers = {name: value for name, value in (grant.get("headers") or {}).items()
                   if name.lower() != "content-length"}
        self.transport.put_object(grant["url"], headers, path)

    def submit_job(self, job_id: str) -> Dict[str, Any]:
        '''``POST /v1/jobs/{id}/submit``, with no body: the grant bound the digest.'''
        self.ensure_session()

        # Fresh per submit, a resubmit included; a retry of this one reuses it.
        headers = {"Idempotency-Key": _fresh_key()}

        return self._waiting_for_a_slot(lambda: self.transport.request(
            "POST", f"jobs/{job_id}/submit", json_body={}, headers=headers).json())

    def _waiting_for_a_slot(self, send):
        '''A create or submit, waiting out a `limit-exceeded` per its
        `Retry-After`, whichever limit it names, and retrying with the same key.'''
        told = []
        while True:
            try:
                return send()
            except ServerProblem as e:
                if e.slug == "terms-not-accepted":
                    raise self._to_sign(e) from None
                if e.slug != "limit-exceeded" or not e.retry_after:
                    raise
                limit = e.member("limit")
                if limit not in told:
                    told.append(limit)
                    if limit == "pending_uploads":
                        held = ", ".join(clean(str(job)) for job in e.member("job_ids") or [])
                        self.logger.warning(
                            "Waiting: this server's limit of jobs waiting for an upload is "
                            f"reached, held by {held or 'your other jobs'}. Cancel any of "
                            "them you abandoned.")
                    elif limit == "concurrent_jobs":
                        self.logger.warning(
                            "Waiting: this server's limit of running jobs is reached; "
                            "this one goes as soon as one of yours finishes.")
                    else:
                        named = f"{clean(str(limit))} " if limit else ""
                        self.logger.warning(f"Waiting: this server's {named}limit is "
                                            "reached, and it refills.")
                time.sleep(e.retry_after)

    def _to_sign(self, refusal: ServerProblem) -> ServerProblem:
        '''A `terms-not-accepted` refusal with each blocking document named by
        title and its page opened where a person can see it. Never accepted here.'''
        blocked = refusal.member("blocked_by")
        if not isinstance(blocked, list) or not blocked:
            return refusal

        try:
            terms = self.me(remind=False).get("terms") or []
        except RemoteError:
            terms = []
        titles = {entry.get("id"): entry.get("title") for entry in terms
                  if isinstance(entry, dict) and entry.get("title")}

        self.open_terms(blocked, titles)

        if not titles:
            return refusal
        return ServerProblem(refusal.problem, refusal.status, help_url=refusal.help_url,
                             titles=titles, retry_after=refusal.retry_after)

    def open_terms(self, blocked, titles: Dict[str, str]) -> None:
        '''Open each `terms` id's page, named by its title, where a person is
        plausibly here to see it. Never accepted here.'''
        if not self.may_open():
            return
        for terms_id in blocked:
            if isinstance(terms_id, str) and terms_id:
                title = clean(titles.get(terms_id) or terms_id)
                self.open_page(f"{title}'s page", terms_id=terms_id)

    def job(self, job_id: str) -> tuple:
        '''``GET /v1/jobs/{id}``, and the `Retry-After` interval, read per response.'''
        self.ensure_session()
        try:
            response = self.transport.request("GET", f"jobs/{job_id}")
        except ServerProblem as e:
            if e.slug == "not-found" and self._mode == GRANT_TOKEN_EXCHANGE:
                raise ServerProblem(
                    e.problem, e.status, help_url=e.help_url, job_id=job_id,
                    next_step="The job may be gone, or this CI credential may be bound "
                              "to another project than the job's.") from None
            raise

        return response.json(), _retry_after(response)

    def jobs(self, **filters) -> list:
        '''``GET /v1/jobs``, following ``Link`` to the end.'''
        self.ensure_session()
        return self._pages("jobs", _filters(filters))

    def cancel_job(self, job_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        '''``POST /v1/jobs/{id}/cancel``. Idempotent.

        A reason is always sent, so the job page says why it stopped; no host
        name, since every reader sees it. Too long or holding a control
        character is refused here, as the server would.
        '''
        if reason is not None and len(reason) > MAX_CANCEL_REASON:
            raise RemoteError(f"a cancel's reason is at most {MAX_CANCEL_REASON} "
                              f"characters, and this one is {len(reason)}")
        if reason is not None and _UNPRINTABLE.search(reason):
            raise RemoteError("a cancel's reason is one line, with no control "
                              "character, and this one has one")
        self.ensure_session()

        body = {"reason": reason or "cancelled from sc-remote"}
        return self.transport.request(
            "POST", f"jobs/{job_id}/cancel", json_body=body).json()

    def delete_job(self, job_id: str) -> None:
        '''``DELETE /v1/jobs/{id}``. Idempotent; the job stays readable.'''
        self.ensure_session()
        try:
            self.transport.request("DELETE", f"jobs/{job_id}")
        except ServerProblem as e:
            if e.slug != "job-state-conflict":
                raise
            raise ServerProblem(
                e.problem, e.status, help_url=e.help_url, retry_after=e.retry_after,
                next_step="Only a finished job can be deleted: cancel it with sc-remote "
                          "-cancel, or let it finish, then delete it.") from None

    def artifacts(self, job_id: str, **filters) -> list:
        '''``GET /v1/jobs/{id}/artifacts``, following ``Link`` to the end.

        `items` may be `[]` and no kind is guaranteed, the manifest included;
        judging an entry is the caller's.
        '''
        self.ensure_session()
        return self._pages(f"jobs/{job_id}/artifacts", _filters(filters))

    def _pages(self, path: str, params: Optional[Dict[str, Any]] = None) -> list:
        '''A listing's `items`, following `Link` to the end.

        Each next page is the `rel="next"` target as given, never a rebuilt
        cursor, and only on the API's origin: it carries the session. A cursor
        the server no longer takes restarts the listing from its first page, once.
        '''
        for restarted in (False, True):
            items = []
            try:
                response = self.transport.request("GET", path, params=params or None)
                while True:
                    items.extend(response.json().get("items") or [])
                    target = _next_link(response.headers.get("Link"), response.url)
                    if not target:
                        return items
                    if origin_of(target) != self.transport.api_origin:
                        raise RemoteError("the server's next page is on another origin, "
                                          "and this client sends its session only to its own")
                    response = self.transport.request("GET", target, absolute=True)
            except ServerProblem as e:
                if e.slug != "invalid-cursor" or restarted:
                    raise

    def fetch_artifact(self, job_id: str, artifact_id: str, dest) -> str:
        '''``GET /v1/jobs/{id}/artifacts/{artifact_id}``, followed to the bytes.
        The API redirects: the bytes may be on another origin. One still being
        described is waited for as its `Retry-After` says, a bounded number of times.'''
        from siliconcompiler.remote.client.transport import MAX_WAITS

        self.ensure_session()

        waits = 0
        while True:
            try:
                response = self.transport.request(
                    "GET", f"jobs/{job_id}/artifacts/{artifact_id}", stream=True,
                    expect_redirect=True)
                break
            except ServerProblem as e:
                if e.slug != "not-ready" or not e.retry_after or waits == MAX_WAITS:
                    raise
                waits += 1
                time.sleep(e.retry_after)
        return self.transport.save(self.transport.follow(response), dest)

    def node_log(self, job_id: str, step: str, index: str, dest) -> str:
        '''A finished node's log, from its `logs` artifact, written to ``dest``
        -- `/logs` is live output only.'''
        text = self.archived_log(job_id, step, index)
        with open(dest, "w") as f:
            f.write(text)
        return str(dest)

    def archived_log(self, job_id: str, step: str, index: str) -> str:
        '''A finished node's `logs` artifact -- a gzip tar of its log files -- as
        the text of its SiliconCompiler log, checked against its listing first.'''
        import tarfile
        import tempfile

        from siliconcompiler.remote.client.results import _download

        items = [item for item in self.artifacts(job_id, kind="logs", step=step, index=index)
                 if item.get("fetchable")]
        if not items:
            raise RemoteError(f"no log of {step}/{index} can be fetched")

        with tempfile.TemporaryDirectory(prefix="sc-log-") as tmpdir:
            path = _download(self, job_id, items[0], os.path.join(tmpdir, "logs.tar.gz"))
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
        '''``GET /v1/jobs/{id}/logs`` for one node, or with neither step nor index
        the whole job (`logs.stream.job`), followed to whatever it points at.

        Re-requested on every reconnect, never reused (see `logs`).
        '''
        self.ensure_session()

        # Both or neither: one alone is a 400.
        params = {"step": step, "index": index} if step is not None else {}
        try:
            response = self.transport.request(
                "GET", f"jobs/{job_id}/logs", params=params,
                stream=True, expect_redirect=True)
        except ServerProblem as e:
            if e.slug == "terms-not-accepted":
                # A live log is gated like its archive.
                raise self._to_sign(e) from None
            raise

        headers = {}
        if last_event_id:
            headers["Last-Event-ID"] = str(last_event_id)

        return self.transport.follow(response, headers=headers, kind="stream")

    def tail_log(self, job_id: str, step: str, index: str, write=None):
        '''Read one node's log as it is written, to the end; returns the text.'''
        from siliconcompiler.remote.client.logs import LogTail

        return LogTail(self, job_id, step, index).follow(write=write)

    def configure_server(self, server: Optional[str] = None,
                         clobber: bool = False,
                         prompt: bool = True) -> None:
        '''Point this machine at a server and prove it can reach it. An
        unanswerable prompt writes nothing: a half-written store fails later.'''
        if self.credentials.server and not clobber:
            if not prompt:
                raise RemoteError(
                    f"{self.credentials.path} already configures "
                    f"{self.credentials.server}; pass clobber=True instead")
            answer = _ask(f"Overwrite the configuration for "
                          f"{self.credentials.server}? [y/N] ")
            if answer.strip().lower() not in ("y", "yes"):
                self.logger.info("Left unchanged.")
                return

        if not server and prompt:
            server = _ask("Remote server address: ",
                          hint="choose a server address with -server")

        if not server or not server.strip():
            raise RemoteError(
                "a remote server address is required: there is no default "
                "server to fall back on")

        address, port, had_credentials = _split_address(server.strip())

        if had_credentials:
            # The key is the credential; say so rather than drop them silently.
            self.logger.warning(
                "Ignoring the username and password in that address: this "
                "server authenticates with a key held on this machine, which "
                "is generated for you.")

        # Each server has its own entry; configuring one again starts afresh.
        self.credentials.set_server(normalize_server(address, port))
        self._transport = self._make_transport(self.credentials.server)
        self.credentials.forget_tokens()

        capabilities = self.capabilities()
        self.login()
        identity = self.me()

        self.logger.info(f"Configured {self.base_url}")
        self.logger.info(f"This machine's key: {self.credentials.thumbprint}")
        self.logger.info(f"You are {identity['id']} on this server")
        self._report_software(capabilities)
        if capabilities.get("identity_assurance") != "verified":
            # Only "verified" asserts anything; any other value, known or not, does not.
            self.logger.warning(
                "This server does not verify who you are. Your jobs are "
                "separated from other users', but that separation is not a "
                "security boundary.")
        self.logger.info(f"Saved to {self.credentials.path}")

    def _report_software(self, capabilities) -> None:
        '''What siliconcompiler this server runs, and whether this machine's is one.

        Advisory: the server decides. This only shows a mismatch while somebody
        is watching, rather than at the first submit.
        '''
        from siliconcompiler import __version__ as sc_version

        published = (capabilities.get("software") or {}).get("python") or {}
        runs = published.get("siliconcompiler")
        if not runs:
            # Required on the wire: an older or broken server, not worth refusing over.
            return

        self.logger.info(f"This server runs siliconcompiler {_listed(runs)}")

        if sc_version not in runs:
            self.logger.warning(
                f"This machine has {sc_version}, which is not one of them. "
                "Jobs from here will be refused when they are created -- "
                "before anything is uploaded -- until you install a version "
                "this server accepts or an operator adds yours.")

    @property
    def ci_session(self) -> bool:
        '''Whether this session is a CI credential's, which nobody is at.'''
        return self._mode == GRANT_TOKEN_EXCHANGE or bool(self.credentials.ci_secret())

    def browser_page(self, **named) -> Dict[str, Any]:
        '''``POST /v1/auth/browser``: the page for a ``job_id``, ``terms_id`` or
        ``artifact_id``, or the portal's home.

        Asked for, never built: the portal's routes are outside the API.
        '''
        if self.ci_session:
            raise RemoteError("a CI session asks for no page: nobody is at a browser")
        self.ensure_session()
        return self.transport.request("POST", "auth/browser", json_body=named).json()

    def open_page(self, what: str, require_tty: bool = True, **named) -> bool:
        '''Ask for a page and open it; whether one opened. A refusal is only warned of.'''
        try:
            answer = self.browser_page(**named)
        except RemoteError as e:
            why = (str(e).strip().splitlines() or [type(e).__name__])[0]
            self.logger.warning(f"No page for {what}: {why}")
            return False
        return self._show(answer, what, require_tty=require_tty)

    def _show(self, answer: Dict[str, Any], what: str, require_tty: bool = True) -> bool:
        '''Open the page endpoint 6 answered, and print it where it may be.

        A non-null `expires_at` marks a single-use sign-in, a bearer secret:
        printed only where no browser opened, to the terminal, never a log.
        '''
        url = answer.get("url") if isinstance(answer, dict) else None
        if not isinstance(url, str) or not url:
            self.logger.warning(f"No page for {what}: the server answered no url")
            return False
        expires = answer.get("expires_at")

        if expires is None:
            self.logger.info(f"{what[:1].upper()}{what[1:]}: {clean(url)}")
        opened = self.open_url(url, what, require_tty=require_tty)
        if expires is not None and not opened:
            print(f"No browser was opened for {what}. Open this in one on this machine; "
                  f"it signs you in once, until {clean(expires)}:\n  {clean(url)}",
                  flush=True)
        return opened

    def may_open(self) -> bool:
        '''Whether a person is plausibly here to see a page opened unasked.'''
        return self.open_browser and sys.stdout.isatty() and \
            not (self.ci_session or os.environ.get("CI"))

    def portal(self) -> bool:
        '''`sc-remote -portal`: the portal's home, signed in as this machine.

        A cold browser cannot present this machine's key-bound identity, so
        endpoint 6 answers a sign-in. Asked for on purpose: a refusal fails.
        '''
        return self._show(self.browser_page(), "the portal", require_tty=False)

    def configure_whitelist(self, add=None, remove=None) -> None:
        '''Which directories may be uploaded from: absolute paths, each once.'''
        entries = list(self.credentials.directory_whitelist)

        for path in add or []:
            absolute = os.path.abspath(path)
            if absolute not in entries:
                entries.append(absolute)

        for path in remove or []:
            absolute = os.path.abspath(path)
            if absolute in entries:
                entries.remove(absolute)

        self.credentials.set_directory_whitelist(entries)
        self.logger.info(f"Directory whitelist saved to {self.credentials.path}")


def _filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    '''Listing filters as query parameters: booleans as `true`/`false`,
    not Python's `True`; lists repeated; None left out.'''
    def one(value):
        return ("true" if value else "false") if isinstance(value, bool) else value

    return {name: [one(v) for v in value] if isinstance(value, (list, tuple)) else one(value)
            for name, value in filters.items() if value is not None}


def _next_link(header: Optional[str], base: str) -> Optional[str]:
    '''The `rel="next"` target of a `Link` header (RFC 8288), resolved against
    the request; None on the last page.'''
    from urllib.parse import urljoin

    from requests.utils import parse_header_links

    for link in parse_header_links(header or ""):
        # A parameter's name is case-insensitive; requests keeps it as sent.
        rel = next((value for name, value in link.items() if name.lower() == "rel"), "")
        if "next" in rel.lower().split():
            return urljoin(base, link["url"])
    return None


def _fresh_key() -> str:
    '''An `Idempotency-Key`: fresh per create and per submit.'''
    import uuid

    return str(uuid.uuid4())


# A metered usage key's `window`, as the period its `used` covers.
_WINDOWS = {"calendar_month": "this month"}


def _listed(values) -> str:
    '''Server-supplied names, one line, made safe to print.'''
    return ", ".join(clean(value) for value in values or []) or "none"


def _notice(notice) -> tuple:
    '''A notice as ``(level, line)``; anything unknown is a warning.'''
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


def _ask(question: str, hint: Optional[str] = None) -> str:
    '''A prompt a scripted run answers by failing, not hanging; ``hint`` says
    how to answer without one.'''
    try:
        return input(question)
    except EOFError:
        raise RemoteError(
            f"no answer was given to \"{question.strip()}\", and it has no default"
            + (f": {hint}" if hint else "")) from None


def read_secret(name: str) -> str:
    '''A header value: hidden on a terminal, else one stdin line; never an
    argument, which shell history would keep.'''
    if sys.stdin.isatty():
        import getpass
        value = getpass.getpass(f"Value for {name}: ")
    else:
        value = sys.stdin.readline().rstrip("\r\n")
    if not value:
        raise RemoteError(f"no value was given for {name}")
    return value


def _split_address(server: str):
    '''Split an address into ``(scheme://host, port, had userinfo)``, keeping its scheme.'''
    from urllib3.exceptions import LocationParseError
    from urllib3.util import parse_url

    if "://" not in server:
        server = f"https://{server}"

    try:
        parts = parse_url(server)
    except LocationParseError as e:
        raise RemoteError(f"{server} is not a server address: {e}") from None

    # An IPv6 host keeps its brackets, so its port is not read as part of it.
    host = (parts.host or "") + (parts.path or "").rstrip("/")
    return f"{parts.scheme}://{host}", parts.port, bool(parts.auth)
