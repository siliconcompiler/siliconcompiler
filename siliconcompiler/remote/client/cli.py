# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
'''``sc-config remote``: the servers this machine submits to, and the jobs it submitted.'''

import argparse
import functools
import os
import sys

from typing import Any, Dict

from siliconcompiler.remote.client import Client, read_secret, terms_title
from siliconcompiler.remote.client.credentials import Credentials
from siliconcompiler.remote.client.errors import (
    RemoteError, ServerProblem, clean, describe, listed)
from siliconcompiler.remote.client.results import recorded_job
from siliconcompiler.remote.client.transport import retrying
from siliconcompiler.scheduler.error import SCRuntimeError
from siliconcompiler.utils import ConfigCommand


def _add_parser(commands) -> None:
    '''
    Add the ``remote`` command: it configures the client and acts on its jobs.
    '''
    parser = commands.add_parser(
        "remote",
        help="the servers jobs are submitted to, and the jobs submitted",
        description="Configure the servers remote jobs are submitted to and this "
                    "machine's session on each, kept in ~/.sc/auth/; and check, follow, "
                    "cancel or delete a submitted job. The v1 remote client is alpha: its "
                    "commands and what it prints may still change.")
    actions = parser.add_subparsers(dest="action", metavar="<action>", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-credentials", metavar="<file>",
                        help="the store, if not the one a project uses by default")
    common.add_argument("-no_browser", action="store_true",
                        help="never open a browser; print the URL instead")

    def action(name, func, what):
        added = actions.add_parser(name, help=what, description=what, parents=[common])
        added.set_defaults(func=functools.partial(_cli, func))
        return added

    action("configure", _cli_configure, "log in to a server and make it the default").add_argument(
        "server", nargs="?", help="its address; asked for when left out")
    action("use", _cli_use, "make a server already configured here the default").add_argument(
        "server")
    action("show", _cli_show, "print the configuration, the default server, and who it "
                              "says you are")
    uploads = action("uploads", _cli_uploads, "change which directories may be uploaded from")
    uploads.add_argument("change", choices=("add", "remove"))
    uploads.add_argument("path", nargs="+", help="each directory; globs are allowed")
    import_cert = action("import-cert", _cli_import_cert,
                         "keep a certificate authority's PEM certificate, for configure to offer")
    import_cert.add_argument("file")
    import_cert.add_argument("-overwrite", action="store_true",
                             help="replace a different certificate already imported under "
                                  "this file's name")
    header = action("header", _cli_header, "set or remove a header the server's operator "
                                           "requires; a value is read from standard input")
    header.add_argument("change", choices=("set", "remove"))
    header.add_argument("name")
    action("rotate-key", _cli_rotate_key, "replace this machine's key and log in again")
    action("logout", _cli_logout, "end this machine's session on the server")
    action("ci-setup", _cli_ci_setup, "write the store for a CI job from the "
                                      "SC_CI_CREDENTIAL secret").add_argument(
        "server", nargs="?", help="its address, if not the secret's")
    action("portal", _cli_portal, "open the server's portal in a browser, signed in as "
                                  "this machine")

    for name, func, what in (("status", _cli_status, "print a job's state"),
                             ("cancel", _cli_cancel, "cancel a job"),
                             ("delete", _cli_delete, "delete a finished job"),
                             ("reconnect", _cli_reconnect,
                              "follow a job to the end and fetch its results"),
                             ("tail", _cli_tail, "print one node's log, live while it runs")):
        job = action(name, func, what)
        job.add_argument("manifest", help="the job's manifest, from its build directory")
        if name == "cancel":
            job.add_argument("-reason", metavar="<text>",
                             help="why: one line of at most 300 characters, shown to every "
                                  "reader of the job")
        if name == "tail":
            job.add_argument("node", help="<step>/<index>, for example place/0")


def _cli(func, args) -> int:
    from siliconcompiler import Project

    # A project for its logger and the [option,credentials] default it reads.
    project = Project()
    if args.credentials:
        project.option.set_credentials(args.credentials)
    try:
        client = Client(Credentials.for_project(project), logger=project.logger,
                        open_browser=not args.no_browser)
        return func(args, client, project.logger) or 0
    except (RemoteError, SCRuntimeError) as e:
        # A refusal is a message and an exit code, never a traceback.
        project.logger.error(str(e))
        return 1


def _cli_configure(args, client, logger):
    client.configure_server(server=args.server)


def _cli_use(args, client, logger):
    client.use_server(args.server)


def _cli_show(args, client, logger):
    print_configuration(client)
    # The unauthenticated deployment block first: it explains an identity
    # failure, on an unenrolled machine or a down server.
    print_deployment(client)
    print_identity(client, client.me())


def _cli_uploads(args, client, logger):
    client.configure_whitelist(**{args.change: args.path})


def _cli_import_cert(args, client, logger):
    client.import_certificate(args.file, overwrite=args.overwrite)


def _cli_header(args, client, logger):
    client.set_header(args.name, read_secret(args.name) if args.change == "set" else None)


def _cli_rotate_key(args, client, logger):
    client.rotate_key()


def _cli_logout(args, client, logger):
    client.logout()


def _cli_ci_setup(args, client, logger):
    client.ci_setup(server=args.server)


def _cli_portal(args, client, logger):
    # No manifest: the browser gets this machine's identity and finds its jobs.
    client.portal()


def _job(args, client, logger):
    '''The job a manifest names: after a Ctrl-C a user has the path, not the id.'''
    if not os.path.isfile(args.manifest):
        raise RemoteError(f"Unable to find manifest: {args.manifest}")

    try:
        from siliconcompiler.remote import manifests

        # It may be one a job returned: read as data, importing nothing it names.
        project = manifests.read(args.manifest)
    except Exception as e:
        raise RemoteError(f"Unable to read {args.manifest}: {e}") from e

    # The job this client recorded beside the results, never the manifest's
    # own `record,remoteid`: the server wrote the manifest.
    where = os.path.dirname(os.path.abspath(args.manifest))
    job_id = recorded_job(where) or recorded_job(os.path.dirname(where))
    if not job_id:
        raise RemoteError(
            f"no remote job is recorded beside {args.manifest}: it was never submitted, "
            "or it was submitted by a different run")

    # Named first, so any refusal that follows reads against its address.
    logger.info(f"Server: {client.base_url}")
    return project, job_id


def _cli_status(args, client, logger):
    _, job_id = _job(args, client, logger)
    _print_status(logger, client.job(job_id)[0])


def _cli_cancel(args, client, logger):
    _, job_id = _job(args, client, logger)
    job = client.cancel_job(job_id, reason=args.reason)
    logger.info(f"Job {clean(job_id)} is {clean(job['state'])}")


def _cli_delete(args, client, logger):
    _, job_id = _job(args, client, logger)
    client.delete_job(job_id)
    logger.info(f"Job {clean(job_id)} deleted")


def _cli_reconnect(args, client, logger):
    from siliconcompiler.remote.client.run import RemoteRun

    project, job_id = _job(args, client, logger)
    RemoteRun(project, client).reconnect(job_id)
    try:
        project.summary()
    except ValueError:
        # No history until the results' manifests are fetched: not a failure.
        _print_status(logger, client.job(job_id)[0])


def _cli_tail(args, client, logger):
    step, _, index = args.node.partition("/")
    if not step:
        raise RemoteError("a node is <step>/<index>, for example place/0")
    # The separator is required: "place10" could be place/10 or place1/0.
    index = index or "0"
    _, job_id = _job(args, client, logger)

    def write(text):
        sys.stdout.write(text)
        sys.stdout.flush()

    told = []

    def say(_):
        if not told:
            told.append(True)
            logger.info(f"{step}/{index} has not started; waiting for it")

    try:
        retrying(lambda: client.tail_log(job_id, step, index, write=write),
                 lambda e: e.slug == "not-ready", notice=say)
    except ServerProblem as e:
        if e.slug != "feature-unsupported" or e.member("feature") != "logs.stream":
            raise
        logger.info("This server serves no live log, so only a finished "
                    "node's log can be read")
        write(client.archived_log(job_id, step, index))


def _print_status(logger, job) -> None:
    from siliconcompiler.remote.client.run import _reason

    logger.info(clean(f"Job {job['id']}: {job['state']}"))
    logger.info(clean(f"  design:  {job['design']}/{job['jobname']}"))
    logger.info(f"  created: {clean(job['created_at'])}")

    # A failed job's error already says why.
    reason = None if job.get('error') else _reason(job)
    if reason:
        logger.info(f"  reason:  {reason}")
    if job.get('deleted_at'):
        logger.info(f"  deleted: {clean(job['deleted_at'])}"
                    + (f" ({clean(job['deleted_reason'])})" if job.get('deleted_reason') else ""))
    if job.get('archived_at'):
        logger.info(f"  archived: {clean(job['archived_at'])}")

    progress = job.get('progress') or {}
    if progress.get('total_count'):
        logger.info(f"  nodes:   {progress.get('completed_count', 0)} completed, "
                    f"{progress.get('failed_count', 0)} failed, "
                    f"of {progress['total_count']}")

    error = job.get('error')
    if error:
        logger.error(f"  error:   {clean(error.get('title'))}"
                     + (f": {clean(error['detail'])}" if error.get('detail') else ""))


def print_configuration(client: Client) -> None:
    '''What this machine would use, and what the server knows it by.'''
    logger, credentials = client.logger, client.credentials
    logger.info(f"Server: {client.base_url}" if client.base_url else "Server: not configured")
    logger.info(f"Machine key: {credentials.thumbprint}")
    logger.info(f"Session store: {credentials.auth_dir}")
    if credentials.certificate:
        logger.info(f"Verified with: {credentials.certificate} ({credentials.certs_dir})")
    if credentials.user_id:
        logger.info(f"Identity on this server: {credentials.user_id}")
    others = [server for server in credentials.servers() if server != credentials.server]
    if others:
        logger.info(f"Also configured (sc-config remote use): {', '.join(others)}")

    # Names only: a header's value is a secret.
    names = ", ".join(sorted(credentials.headers()))
    if names:
        logger.info(f"Operator headers: {names}")
    if credentials.ci_secret():
        logger.info("CI credential: present")

    whitelist = credentials.directory_whitelist
    logger.info("Directory whitelist:")
    for entry in whitelist or ["  (empty)"]:
        logger.info(f"  {entry}" if whitelist else entry)


def health(client: Client) -> Dict[str, Any]:
    '''``GET /v1/healthz``: one word, and no credential.

    A `fail` arrives as a 503, so the refusal path IS the answer, not a
    swallowed error.
    '''
    try:
        return client.transport.request("GET", "healthz", authenticated=False).json()
    except ServerProblem:
        return {"status": "fail"}
    except ValueError:
        # 200 but not JSON: up, and not this server.
        return {"status": "warn"}


def print_deployment(client: Client) -> None:
    '''What the server says it is, for a person at a terminal.

    Unauthenticated, so it works before enrolment and says the same to everybody.
    '''
    logger = client.logger
    status = health(client)
    published = client.capabilities(notices=False)

    logger.info(f"Health: {clean(status.get('status', 'unknown'))}")
    logger.info(f"API: {clean(published.get('api_version', 'unknown'))}")
    logger.info(f"Identity assurance: {clean(published.get('identity_assurance', 'unknown'))}")

    client.show_notices(published, always=True)

    # Apart, as they are satisfied apart: the python set in ONE image, a tool per node.
    software = published.get("software") or {}
    for bucket, label in (("python", "Python distributions"), ("tools", "Tools")):
        held = software.get(bucket) or {}
        logger.info(f"{label} it can run:")
        for name, versions in sorted(held.items()):
            logger.info(f"  {clean(name)}: {listed(versions)}")
        if not held:
            logger.info("  (none advertised)")

    logger.info(f"Sign-in: {listed(published.get('grant_types_supported'))}")
    logger.info(f"Features: {listed(published.get('features'))}")

    # Defaults only: an account's own are in `GET /v1/me`.
    _print_limits(logger, "Default limits:", published.get("limits"))

    if published.get("terms_url"):
        logger.info(f"Terms: {clean(published['terms_url'])}")


def _print_limits(logger, heading: str, limits) -> None:
    '''Each limit under ``heading``, in readable units.'''
    from siliconcompiler.utils.units import format_binary, format_duration

    if not limits:
        return
    logger.info(heading)
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
        logger.info(f"  {clean(name)}: {shown}")


# A metered usage key's `window`, as the period its `used` covers.
_WINDOWS = {"calendar_month": "this month"}


def print_identity(client: Client, identity: Dict[str, Any]) -> None:
    '''Who the server says you are, this machine's session, your limits,
    usage and terms, from one `GET /v1/me`.'''
    from siliconcompiler.utils.units import format_binary, format_duration

    logger = client.logger
    logger.info(f"Server reports you as {clean(identity['id'])} "
                f"(issuer {clean(identity['issuer'])})")

    session = identity.get("session") or {}
    if session:
        where = f" on device {clean(session['device_id'])}" if session.get("device_id") else ""
        logger.info(f"Session: {clean(session.get('kind', 'unknown'))}{where}")
        logger.info(f"  scope: {clean(session.get('scope') or '(none)')}")
        logger.info(f"  access token until {clean(session.get('access_expires_at'))}")
        logger.info("  refresh token until " + clean(
            session.get('refresh_expires_at') or '(none: it cannot refresh)'))
        logger.info(f"  ends at {clean(session.get('session_expires_at'))}, "
                    "and is never extended")

    if identity.get("can_submit") is False:
        logger.warning(describe({"title": "You cannot submit jobs here",
                                 "type": identity.get("blocked_type")}))

    _print_limits(logger, "Your limits:", identity.get("limits"))

    usage = identity.get("usage") or {}
    logger.info("Unfinished jobs (staging, queued, running or cancelling): "
                f"{clean(usage.get('concurrent_jobs', 0))}")
    compute = usage.get("compute_seconds") or {}
    if compute:
        total = compute.get("total")
        window = compute.get("window")
        # `used` is this window's; with no window, it is the whole.
        period = (_WINDOWS.get(window) or f"in this {clean(window)} window") \
            if window else "in all"
        logger.info(f"Compute: {format_duration(compute.get('used') or 0)} {period}"
                    + (f", {format_duration(total)} in all" if total is not None else ""))
    stored = usage.get("storage_bytes") or {}
    if stored:
        used = format_binary(stored.get("used") or 0, "B", digits=1, show_unit=True,
                             compact=True, default="—")
        logger.info(f"Storage: {used}")

    terms = [entry for entry in identity.get("terms") or [] if isinstance(entry, dict)]
    if terms:
        logger.info("Terms:")
    for entry in terms:
        title = terms_title(entry)
        decided = "accepted" if entry.get("accepted_at") else \
            "declined" if entry.get("declined_at") else "undecided"
        logger.info(f"  {title}, version {clean(entry.get('version') or '?')}: {decided}")
        # Not after a decline, which drops the prompt; nor where the reminder of
        # its upcoming version has just offered the same page.
        upcoming = entry.get("upcoming") if isinstance(entry.get("upcoming"), dict) else {}
        if entry.get("can_decide") is True and entry.get("declined_at") is None \
                and entry.get("id") and \
                (entry["id"], upcoming.get("version")) not in client.terms_reminded:
            logger.info("    It may be decided on its page in this server's portal.")
            client.offer_terms_page(entry["id"], title)


REMOTE_COMMAND = ConfigCommand(
    examples="""\
To log in to a server, check the connection, and act on a job submitted to it:
    sc-config remote configure https://example.com
    sc-config remote show
    sc-config remote status build/<design>/<jobname>/<design>.pkg.json
    sc-config remote cancel build/<design>/<jobname>/<design>.pkg.json""",
    add_parser=_add_parser)
