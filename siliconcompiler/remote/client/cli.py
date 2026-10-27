# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
'''``sc-config remote``: the servers this machine submits to, and its session on each.'''

import functools

from typing import Any, Dict

from siliconcompiler.remote.client import Client, read_secret, terms_title
from siliconcompiler.remote.client.credentials import (
    UPLOADS, Credentials, describe_certificates)
from siliconcompiler.remote.client.errors import (
    RemoteError, ServerProblem, clean, describe, listed)
from siliconcompiler.scheduler.error import SCRuntimeError
from siliconcompiler.utils import ConfigCommand


def _add_parser(commands) -> None:
    '''
    Add the ``remote`` command: it configures the client.
    '''
    parser = commands.add_parser(
        "remote",
        help="the servers remote jobs are submitted to",
        description="Configure the servers remote jobs are submitted to and this "
                    "machine's session on each, kept in ~/.sc/auth/. A job is followed, "
                    "cancelled and deleted in the server's portal, and a run left before "
                    "its job ended gets its results with fetch. The v1 remote client is "
                    "alpha: its commands and what it prints may still change.")
    actions = parser.add_subparsers(dest="action", metavar="<action>", required=True)

    def action(name, func, what, description=None):
        added = actions.add_parser(name, help=what, description=description or what)
        added.set_defaults(func=functools.partial(_cli, func))
        return added

    configure = action(
        "configure", _cli_configure, "log in to a server and make it the default",
        description="Log in to a server and make it the default. With SC_CI_CREDENTIAL "
                    "set, as in a CI job, the session is that credential's.")
    configure.add_argument("server", nargs="?", help="its address; asked for when left out")
    configure.add_argument(
        "-header", metavar="<name>", action="append", default=[],
        help="a header the server's access layer requires, its value read from standard "
             "input, one line each in the order given; an empty value removes it")
    configure.add_argument(
        "-cert", metavar="<file>",
        help="the PEM certificate of the authority that signs the server's certificate, "
             "where that is not one of the usual authorities")
    action("use", _cli_use, "make a server configured here the default").add_argument(
        "server", help="its address")
    for name, func, what in (
            ("show", _cli_show, "print the configuration, and what the server says about "
                                "itself and you"),
            ("portal", _cli_portal, "open the server's portal in a browser, signed in as "
                                    "this machine, to follow, cancel or delete a job"),
            ("logout", _cli_logout, "end this machine's session on a server, and forget it")):
        action(name, func, what).add_argument(
            "server", nargs="?", help="its address, if not the default server's")
    action("rotate-key", _cli_rotate_key,
           "replace this machine's key on every server configured here, and log in again")
    action("fetch", _cli_fetch, "follow a remote run's job to its end and bring its "
                                "results into the run's build directory",
           description="Reconnect to the job a remote run submitted, as the run itself "
                       "would have: follow it to its end, then bring its results into "
                       "the run's build directory. For a run interrupted, or cut off "
                       "from the server, before its job ended.").add_argument(
        "manifest", help="the run's manifest, <builddir>/<design>/<jobname>/<design>.pkg.json, "
                         "which names its job")


def _cli(func, args) -> int:
    from siliconcompiler import Project

    # A project for its logger and the [option,credentials] default it reads.
    project = Project()
    try:
        client = Client(Credentials.for_project(project), logger=project.logger)
        return func(args, client, project.logger) or 0
    except (RemoteError, SCRuntimeError) as e:
        # A refusal is a message and an exit code, never a traceback.
        project.logger.error(str(e))
        return 1


def _cli_configure(args, client, logger):
    headers = {name: read_secret(name) for name in args.header}
    client.configure_server(server=args.server, headers=headers, authority=args.cert)


def _cli_use(args, client, logger):
    client.use_server(args.server)


def _cli_show(args, client, logger):
    client.select(args.server)
    print_configuration(client)
    # The unauthenticated deployment block first: it explains an identity
    # failure, on an unenrolled machine or a down server.
    print_deployment(client)
    print_identity(client, client.me())


def _cli_portal(args, client, logger):
    client.select(args.server)
    # No job: the browser gets this machine's identity and finds its jobs.
    client.portal()


def _cli_logout(args, client, logger):
    client.select(args.server)
    client.logout()


def _cli_rotate_key(args, client, logger):
    client.rotate_key()


def _cli_fetch(args, client, logger):
    from siliconcompiler import Project
    from siliconcompiler.remote.client.run import RemoteRun
    from siliconcompiler.schema import EditableSchema

    project = Project.from_manifest(filepath=args.manifest)
    job_id = project.get('record', 'remoteid')
    if not job_id:
        raise RemoteError(f"{args.manifest} names no remote job: it is not the manifest of "
                          "a remote run whose job was submitted")

    # The run's own store, which may not be the default.
    client = Client(Credentials.for_project(project), logger=logger)
    try:
        RemoteRun(project, client).watch(job_id)
    except KeyboardInterrupt:
        # Said how to come back as it left.
        return 1
    finally:
        # As the scheduler does as a run ends, in place of the record the
        # interrupted run left: what was fetched is kept.
        jobname = project.option.get_jobname()
        if jobname in project.getkeys("history"):
            EditableSchema(project).remove("history", jobname)
        project._record_history()
        project.write_manifest(args.manifest)
    project.summary()


def print_configuration(client: Client) -> None:
    '''What this machine would use, and what the server knows it by.'''
    logger, credentials = client.logger, client.credentials
    logger.info(f"Server: {client.base_url}" if client.base_url else "Server: not configured")
    logger.info(f"Machine key: {credentials.thumbprint}")
    logger.info(f"Session store: {credentials.auth_dir}")
    if credentials.authority:
        for subject, fingerprint in describe_certificates(credentials.authority.encode()):
            logger.info(f"Verified with: {subject} (SHA-256 {fingerprint})")
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

    logger.info("Directories a run may upload a directory from (remote uploads):")
    for entry in UPLOADS.get() or ["(none)"]:
        logger.info(f"  {entry}")


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
To log in to a server, check the connection, and open the portal its jobs are in:
    sc-config remote configure https://example.com
    sc-config remote show
    sc-config remote portal

To make another server already configured here the default:
    sc-config remote use https://other.example.com

To bring home the results of a remote run interrupted before its job ended:
    sc-config remote fetch build/heartbeat/job0/heartbeat.pkg.json""",
    add_parser=_add_parser)
