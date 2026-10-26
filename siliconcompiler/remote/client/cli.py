# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
'''``sc-config remote``: the servers this machine submits to, and the jobs it submitted.'''

import argparse
import functools
import os
import sys
import time

from siliconcompiler.remote.client import Client, read_secret
from siliconcompiler.remote.client.credentials import Credentials
from siliconcompiler.remote.client.errors import RemoteError, ServerProblem, clean
from siliconcompiler.remote.client.results import recorded_job
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
    client.print_configuration()
    # The unauthenticated deployment block first: it explains an identity
    # failure, on an unenrolled machine or a down server.
    client.print_deployment()
    client.print_identity(client.me())


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

    waiting = False
    while True:
        try:
            client.tail_log(job_id, step, index, write=write)
            return
        except ServerProblem as e:
            if e.slug == "feature-unsupported" and e.member("feature") == "logs.stream":
                logger.info("This server serves no live log, so only a finished "
                            "node's log can be read")
                write(client.archived_log(job_id, step, index))
                return
            if e.slug != "not-ready" or not e.retry_after:
                raise
            if not waiting:
                waiting = True
                logger.info(f"{step}/{index} has not started; waiting for it")
            time.sleep(e.retry_after)


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


REMOTE_COMMAND = ConfigCommand(
    examples="""\
To log in to a server, check the connection, and act on a job submitted to it:
    sc-config remote configure https://example.com
    sc-config remote show
    sc-config remote status build/<design>/<jobname>/<design>.pkg.json
    sc-config remote cancel build/<design>/<jobname>/<design>.pkg.json""",
    add_parser=_add_parser)
