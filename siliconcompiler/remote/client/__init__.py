'''
The ``v1`` remote client.

``Client`` is the library surface; ``sc-remote`` is a thin wrapper over it, so
every capability lands here rather than in the app. That is what keeps a later
CLI rename off the critical path.
'''

import logging

from typing import Any, Dict, Optional

from siliconcompiler.remote.client.credentials import Credentials
from siliconcompiler.remote.client.errors import (
    RemoteError, ServerProblem, SessionEnded, describe)
from siliconcompiler.remote.client.identity import local_subject, display_name
from siliconcompiler.remote.client.transport import Transport, normalize_server

__all__ = [
    "Client", "Credentials", "RemoteError", "ServerProblem", "SessionEnded",
    "describe",
]


logger = logging.getLogger(__name__)


class Client:
    '''One machine talking to one server.'''

    def __init__(self, credentials: Credentials,
                 logger: Optional[logging.Logger] = None):
        self.credentials = credentials
        self.logger = logger or logging.getLogger(__name__)

        if not credentials.address:
            # There is no default server to fall back on, so this is an error
            # rather than a redirect. It is raised on use rather than on
            # construction so that `sc-remote -configure` can build a client in
            # order to fix it.
            self._transport = None
            return

        self._transport = Transport(
            normalize_server(credentials.address, credentials.port),
            credentials.key(),
            credentials=credentials)
        # No access token: it is never written down, so a command starts with
        # the refresh token and spends it once.
        self._transport.set_tokens(None, credentials.refresh_token)

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
        if self.credentials.user_id:
            self.logger.info(f"Identity on this server: {self.credentials.user_id}")

        whitelist = self.credentials.directory_whitelist
        self.logger.info("Directory whitelist:")
        for entry in whitelist or ["  (empty)"]:
            self.logger.info(f"  {entry}" if whitelist else entry)

    ######################################################################
    # Discovery
    ######################################################################

    def capabilities(self) -> Dict[str, Any]:
        '''``GET /v1``: the first call on every path, and it carries no
        credential.

        A JSON capabilities block means this is a ``v1`` server. What a client
        branches on inside it is ``grant_types_supported`` and never
        ``identity_assurance``, which is advisory.
        '''
        return self.transport.request(
            "GET", "", authenticated=False).json()

    ######################################################################
    # Sessions
    ######################################################################

    def login(self) -> Dict[str, Any]:
        '''Obtain a session with no human involved.

        ``client_credentials`` against a fixed local client: no browser, no
        issuer, no prompt. The key is generated on first use and bound by the
        server on first contact.
        '''
        subject, machine_hash, source = local_subject()

        form = {
            "grant_type": "client_credentials",
            "client_id": f"local:{subject}",
            "machine_id_source": source,
            "display_name": display_name(),
        }
        if machine_hash:
            form["machine_id_hash"] = machine_hash

        body = self.transport.login(form)
        self.credentials.save_tokens(body)
        return body

    def ensure_session(self) -> None:
        '''Get an access token for this command, the cheapest way there is.

        🔴 The refresh token is spent FIRST and a fresh grant is the fallback,
        not the other way round. `client_credentials` mints a new token family
        every time it is called, and a family lives twelve days whether or not
        anything uses it -- so logging in per command would leave a trail of
        live sessions behind, one for every invocation.
        '''
        if self.transport.access_token is not None:
            return

        try:
            if self.transport.refresh():
                return
        except SessionEnded:
            # Over rather than stale: there is nothing to renew, and this
            # machine's key is still enrolled, so a fresh grant is the answer.
            self.logger.info("This session has ended; starting a new one.")

        self.login()

    def logout(self) -> None:
        '''End this session on the server, then forget it here.

        Revoking needs a live access token and this client holds none between
        commands, so the refresh token is spent to get one. That is worth a
        round trip: the alternative is dropping the refresh token locally and
        leaving the family alive on the server for its twelve-day cap.
        '''
        try:
            self.ensure_session()
            self.transport.request("POST", "auth/revoke")
        except (SessionEnded, RemoteError) as e:
            # Already over, or unreachable. Forgetting it locally is the whole
            # remaining job either way, and it must still happen.
            logger.debug(f"could not revoke on the server: {e}")
        finally:
            self.credentials.forget_tokens()
            self.transport.set_tokens(None, None)

    ######################################################################
    # Identity
    ######################################################################

    def me(self) -> Dict[str, Any]:
        '''``GET /v1/me``, and remember which principal this server saw.'''
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
        return body

    def devices(self) -> list:
        '''The machines that can act as me.'''
        self.ensure_session()
        return self.transport.request("GET", "devices").json()["devices"]

    def revoke_device(self, device_id: str) -> None:
        '''Revoke a machine, ending every session it holds.'''
        self.ensure_session()
        self.transport.request("DELETE", f"devices/{device_id}")

    ######################################################################
    # Jobs
    ######################################################################

    def create_job(self, design: str, jobname: str, *,
                   flow: Optional[Dict[str, Any]] = None,
                   resources: Optional[Dict[str, Any]] = None,
                   versions: Optional[Dict[str, str]] = None,
                   run_hash: Optional[str] = None,
                   idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        '''``POST /v1/jobs``: the job exists, and nothing has moved yet.

        ``design`` and ``jobname`` are authoritative -- nothing in a manifest
        names either, so the server cannot re-derive them. Everything else is
        the descriptor: advisory, re-derived at submit, and present only to let
        the server refuse before the archive uploads.

        ``run_hash`` is the client's opaque hash of the work, for job reuse. The
        server looks it up owner-scoped and hands back the caller's own earlier
        result instead of running it again. 🔴 **Nothing in this client computes
        one yet** -- what SiliconCompiler should hash is its own decision, and a
        hash that is wrong in the direction of *the same* is a wrong answer.
        '''
        self.ensure_session()

        body: Dict[str, Any] = {"design": design, "jobname": jobname}
        for name, value in (("flow", flow), ("resources", resources),
                            ("versions", versions), ("run_hash", run_hash)):
            if value:
                body[name] = value

        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        return self.transport.request(
            "POST", "jobs", json_body=body, headers=headers).json()

    def upload_grant(self, job_id: str) -> Dict[str, Any]:
        '''``POST /v1/jobs/{id}/upload-grant``: where to put the bytes.

        Its own call rather than a member of the create response, which is what
        gives an expired grant a way back: re-issuing is this endpoint, where
        before it meant creating a second job and leaking the first.
        '''
        self.ensure_session()
        return self.transport.request("POST", f"jobs/{job_id}/upload-grant").json()

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

    def submit_job(self, job_id: str, digest: str, size: int,
                   idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        '''``POST /v1/jobs/{id}/submit``: carrying the digest of what was PUT.

        The digest describes the bytes that moved, not a freshly built archive:
        a re-tar of the same directory is a different digest, and the server
        compares against what storage reports.
        '''
        self.ensure_session()

        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        return self.transport.request(
            "POST", f"jobs/{job_id}/submit",
            json_body={"digest": digest, "bytes": size}, headers=headers).json()

    def job(self, job_id: str) -> tuple:
        '''``GET /v1/jobs/{id}``, and the interval the server asked for.

        The pace is the server's: `Retry-After` is read per response rather than
        once at the start of a run, which is what the client this replaces did
        with a single number.
        '''
        self.ensure_session()
        response = self.transport.request("GET", f"jobs/{job_id}")

        retry_after = None
        header = response.headers.get("Retry-After")
        if header:
            try:
                retry_after = max(1, int(header))
            except ValueError:
                # A date-form Retry-After is legal HTTP and nothing here serves
                # one; an unreadable value is not a reason to fail a poll.
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
        '''``POST /v1/jobs/{id}/cancel``. Idempotent, and the body is optional.'''
        self.ensure_session()

        body = {"reason": reason} if reason else {}
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
            allow_redirects=False)
        return self.transport.save(self.transport.follow(response), dest)

    def node_log(self, job_id: str, step: str, index: str, dest) -> str:
        '''``GET /v1/jobs/{id}/logs``: one node's log, followed to its bytes.

        🔴 Branch on the `Content-Type` that comes back, never on the `303`. A
        node can finish between the redirect and the fetch, so what the server
        decided at the endpoint can already be stale; what was actually served
        cannot be. `text/event-stream` is a live tail, anything else is the
        archived file.
        '''
        response = self.follow_log(job_id, step, index)

        if _is_stream(response):
            response.close()
            raise RemoteError(
                f"{step}/{index} is still running; use tail_log() to read it "
                "as it is written")

        return self.transport.save(response, dest)

    def follow_log(self, job_id: str, step: str, index: str,
                   last_event_id=None):
        '''``GET /v1/jobs/{id}/logs``, followed to whatever it points at.

        🔴 Re-requested on every reconnect and never reused. Authorization is
        evaluated here, at the endpoint that takes the token and the proof, and
        the URL it hands back carries a lifetime of its own -- so a six-hour log
        is a sequence of capability-length streams rather than one connection
        outliving the credential that opened it.
        '''
        self.ensure_session()

        response = self.transport.request(
            "GET", f"jobs/{job_id}/logs", params={"step": step, "index": index},
            stream=True, allow_redirects=False)

        headers = {}
        if last_event_id:
            headers["Last-Event-ID"] = str(last_event_id)

        return self.transport.follow(response, headers=headers)

    def tail_log(self, job_id: str, step: str, index: str, write=None):
        '''Read one node's log as it is written, to the end.

        Returns the text it emitted. Reconnects for as long as the node is
        running, because a capability expiring is the ordinary way a long tail
        ends rather than a failure.
        '''
        from siliconcompiler.remote.client.logs import LogTail

        return LogTail(self, job_id, step, index).follow(write=write)

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
        self.credentials.update(address=address, port=port,
                                access_token=None, refresh_token=None,
                                user_id=None)
        self._transport = Transport(
            normalize_server(address, port), self.credentials.key(),
            credentials=self.credentials)

        capabilities = self.capabilities()
        if "client_credentials" not in capabilities.get("grant_types_supported", []):
            raise RemoteError(
                f"{self.base_url} does not offer a login this client can use "
                f"(it offers {capabilities.get('grant_types_supported')})")

        self.login()
        identity = self.me()

        self.logger.info(f"Configured {self.base_url}")
        self.logger.info(f"This machine's key: {self.credentials.thumbprint}")
        self.logger.info(f"You are {identity['id']} on this server")
        if capabilities.get("identity_assurance") != "verified":
            # "verified" is the only value that asserts anything; every other
            # value, known or unknown, means do not rely on this identity.
            self.logger.warning(
                "This server does not verify who you are. Your jobs are "
                "separated from other users', but that separation is not a "
                "security boundary.")
        self.logger.info(f"Saved to {self.credentials.path}")

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


def _ask(question: str) -> str:
    '''A prompt that a scripted run answers by failing rather than hanging.'''
    try:
        return input(question)
    except EOFError:
        raise RemoteError(
            "no answer available and no default to fall back on: "
            "choose a server address with -server") from None


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
