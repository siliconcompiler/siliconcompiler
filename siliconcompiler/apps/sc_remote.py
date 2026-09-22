# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys

from pathlib import Path

from siliconcompiler import Project, Design, utils
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

    switchlist = ['-cfg',
                  '-credentials',
                  '-configure',
                  '-server',
                  '-add',
                  '-remove',
                  '-list',
                  '-reconnect',
                  '-cancel',
                  '-delete']

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
    '''Where this machine keeps its key and its session.

    The path is taken as given rather than resolved through find_files, which
    requires the file to exist -- and creating it is exactly what -configure is
    for.
    '''
    configured = remote.option.get_credentials()
    if configured:
        return Credentials(Path(configured).expanduser().absolute())
    return Credentials(Path(utils.default_credentials_file()))


def _dispatch(remote):
    # Sanity checks.
    exclusive = ['configure', 'reconnect', 'cancel', 'delete']
    cfg_only = ['reconnect', 'cancel', 'delete']

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

    # Everything below submits, watches or acts on a job, and the job path is
    # not on this branch yet. Reaching the server at all is what works today.
    if project_cfg or any(remote.get("cmdarg", arg) for arg in cfg_only):
        raise SCRuntimeError(
            "acting on a job is not available yet: the v1 client can configure "
            "a server, log in and read it, but the job path has not landed")

    # No job named: report what this machine is configured for and who the
    # server says it is.
    client.print_configuration()
    identity = client.me()
    remote.logger.info(f"Server reports you as {identity['id']} "
                       f"(issuer {identity['issuer']})")
    remote.logger.info(f"Jobs running: {identity['usage']['jobs_active']}")

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
