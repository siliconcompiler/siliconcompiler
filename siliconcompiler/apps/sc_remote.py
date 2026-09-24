# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import os
import sys

from siliconcompiler import Project, Design
from siliconcompiler.remote import Client, Credentials, RemoteError
from siliconcompiler.scheduler.error import SCRuntimeError


def main():
    progname = "sc-remote"
    description = """
-----------------------------------------------------------
SC app that provides an entry point to common remote / server
interactions.

To configure a server, use:
    sc-remote -configure -server https://example.com

    to add or remove directories from the upload whitelist,
        these also support globbing:
    sc-remote -configure -add ./fine_to_upload
    sc-remote -configure -remove ./no_longer_okay_to_upload

    to display the full configuration of the credentials file
    sc-remote -configure -list

To check an ongoing job's progress, use:
    sc-remote -cfg <stepdir>/outputs/<design>.pkg.json

To cancel an ongoing job, use:
    sc-remote -cancel -cfg <stepdir>/outputs/<design>.pkg.json

To reconnect an ongoing job, use:
    sc-remote -reconnect -cfg <stepdir>/outputs/<design>.pkg.json

To delete a job, use:
    sc-remote -delete -cfg <stepdir>/outputs/<design>.pkg.json

To read one node's log, live if it is still running, use:
    sc-remote -tail place/0 -cfg <stepdir>/outputs/<design>.pkg.json
-----------------------------------------------------------
"""

    class RemoteProject(Project):
        def __init__(self):
            super().__init__()

            self.set_design(Design("dummy"))

            self._add_commandline_argument("cfg", "file",
                                           "configuration manifest")
            self._add_commandline_argument("configure", "bool",
                                           "create configuration file for the remote")
            self._add_commandline_argument("server", "str",
                                           "address of server for configure (only valid with "
                                           "-configure)")
            self._add_commandline_argument("add", "[dir]",
                                           "path to add to the upload whitelist (only valid "
                                           "with -configure)")
            self._add_commandline_argument("remove", "[dir]",
                                           "path to remove from the upload whitelist (only valid "
                                           "with -configure)")
            self._add_commandline_argument("list", "bool",
                                           "print the current configuration (only valid with "
                                           "-configure)")
            self._add_commandline_argument("reconnect", "bool",
                                           "reconnect to a running job on the remote")
            self._add_commandline_argument("cancel", "bool",
                                           "cancel a running job on the remote")
            self._add_commandline_argument("delete", "bool",
                                           "delete a job on the remote")
            self._add_commandline_argument("tail", "str",
                                           "read one node's log as <step>/<index>; "
                                           "follows it live while the node runs")
            self._add_commandline_argument("portal", "bool",
                                           "open this server's portal in a browser, "
                                           "signed in as this machine")

    switchlist = ['-cfg',
                  '-credentials',
                  '-configure',
                  '-server',
                  '-add',
                  '-remove',
                  '-list',
                  '-reconnect',
                  '-cancel',
                  '-delete',
                  '-tail',
                  '-portal']

    # Argument Parser
    remote = RemoteProject.create_cmdline(progname, switchlist=switchlist, description=description,
                                          use_sources=False)

    try:
        return _dispatch(remote)
    except (RemoteError, SCRuntimeError) as e:
        # A refusal is a message and an exit code, never a traceback. The
        # client already renders a server's problem+json in three lines, so
        # printing it is the whole job here.
        remote.logger.error(str(e))
        return 1


def _credentials(remote) -> Credentials:
    '''Where this machine keeps its key and its session.'''
    return Credentials.for_project(remote)


def _dispatch(remote):
    # Sanity checks.
    exclusive = ['configure', 'reconnect', 'cancel', 'delete', 'tail', 'portal']
    cfg_only = ['reconnect', 'cancel', 'delete', 'tail']

    exclusive_count = sum([1 for arg in exclusive if remote.get("cmdarg", arg)])
    if exclusive_count > 1:
        remote.logger.error(f'Error: {", ".join(["-"+e for e in exclusive])} '
                            'are mutually exclusive')
        return 1
    project_cfg = remote.get('cmdarg', 'cfg')
    if not project_cfg and any([remote.get("cmdarg", arg) for arg in cfg_only]):
        remote.logger.error(f'Error: -cfg is required for {", ".join(["-"+e for e in cfg_only])}')
        return 2
    if any([remote.get("cmdarg", arg) for arg in cfg_only]) and remote.get("cmdarg", 'server'):
        remote.logger.error('Error: -server cannot be specified with '
                            f'{", ".join(["-"+e for e in cfg_only])}')

    client = Client(_credentials(remote), logger=remote.logger)

    if remote.get("cmdarg", 'configure'):
        if remote.get("cmdarg", 'list'):
            client.print_configuration()
            return 0

        if remote.get("cmdarg", 'add') or remote.get("cmdarg", 'remove'):
            client.configure_whitelist(add=remote.get("cmdarg", 'add'),
                                       remove=remote.get("cmdarg", 'remove'))
            return 0

        try:
            client.configure_server(server=remote.get("cmdarg", 'server'))
        except RemoteError as e:
            # An answer that is needed and was not given, most often the server
            # address, which has no default to fall back on.
            remote.logger.error(str(e))
            return 3
        return 0

    if remote.get("cmdarg", 'portal'):
        # 🔴 Nothing about a job, so it takes no -cfg: the browser gets a
        # session for this machine's identity, and finds its jobs itself.
        client.portal()
        return 0

    if project_cfg:
        return _act_on_job(remote, client, project_cfg)

    # No job named: report what this machine is configured for, what the
    # server says it is, and who the server says you are.
    #
    # 🔴 The deployment block comes before the identity one and is printed even
    # when the identity call fails, because it is the half that explains the
    # failure: `GET /v1` and `GET /v1/healthz` carry no credential, so they
    # answer for a machine that has not enrolled and for a server that is down
    # -- which are the two states somebody runs a bare `sc-remote` in.
    client.print_configuration()
    client.print_deployment()

    identity = client.me()
    remote.logger.info(f"Server reports you as {identity['id']} "
                       f"(issuer {identity['issuer']})")
    remote.logger.info(f"Jobs running: {identity['usage']['jobs_active']}")

    return 0


def _act_on_job(remote, client, project_cfg):
    '''Everything that names a job names it with a manifest, not an id.

    The two commands a user is given after a Ctrl-C both take the path of the
    manifest the run wrote, so a person who interrupted a long job needs the
    path they already have rather than an id they would have to find.
    '''
    if not os.path.isfile(project_cfg):
        remote.logger.error(f"Unable to find manifest: {project_cfg}")
        return 1

    try:
        project = Project.from_manifest(filepath=project_cfg)
    except Exception as e:
        remote.logger.error(f"Unable to read {project_cfg}: {e}")
        return 1

    job_id = project.get('record', 'remoteid')
    if not job_id:
        remote.logger.error(
            f"{project_cfg} names no remote job: it was never submitted, or it "
            "was submitted by a different run")
        return 1

    # The server is confirmed before it is acted on, which is the order the
    # client this replaces used and the reason a cancel against an unreachable
    # server says so rather than reporting the job as gone.
    remote.logger.info(f"Server: {client.base_url}")

    if remote.get("cmdarg", 'cancel'):
        job = client.cancel_job(job_id)
        remote.logger.info(f"Job {job_id} is {job['state']}")
        return 0

    if remote.get("cmdarg", 'delete'):
        client.delete_job(job_id)
        remote.logger.info(f"Job {job_id} deleted")
        return 0

    node = remote.get("cmdarg", 'tail')
    if node:
        step, _, index = node.partition("/")
        if not step:
            remote.logger.error("-tail takes <step>/<index>, for example place/0")
            return 1
        # Two fields rather than one string, which is why the separator is
        # required rather than parsed out of a run-together name: step=place
        # index=10 and step=place1 index=0 both render "place10".
        client.tail_log(job_id, step, index or "0",
                        write=lambda text: (sys.stdout.write(text),
                                            sys.stdout.flush()))
        return 0

    if remote.get("cmdarg", 'reconnect'):
        from siliconcompiler.remote.client.run import RemoteRun

        RemoteRun(project, client).reconnect(job_id)

        try:
            project.summary()
        except ValueError:
            # A summary reads the run's history, and the history is rebuilt from
            # the manifests the results carry -- which are not fetched yet. The
            # job's own status was already printed by the wait, so this is a
            # missing extra rather than a failed command.
            _print_status(remote.logger, client.job(job_id)[0])
        return 0

    job, _ = client.job(job_id)
    _print_status(remote.logger, job)
    return 0


def _print_status(logger, job) -> None:
    logger.info(f"Job {job['id']}: {job['state']}")
    logger.info(f"  design:  {job['design']}/{job['jobname']}")
    logger.info(f"  created: {job['created_at']}")

    progress = job.get('progress') or {}
    if progress.get('total_count'):
        logger.info(f"  nodes:   {progress.get('completed_count', 0)} completed, "
                    f"{progress.get('failed_count', 0)} failed, "
                    f"of {progress['total_count']}")

    if job.get('error'):
        logger.error(f"  error:   {job['error'].get('title')}")


#########################
if __name__ == "__main__":
    sys.exit(main())
