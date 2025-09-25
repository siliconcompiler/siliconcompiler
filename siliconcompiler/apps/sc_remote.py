# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys

from siliconcompiler import Project, Design
from siliconcompiler.remote import Client, ConfigureClient


def main():
    progname = "sc-remote"
    description = """
-----------------------------------------------------------
SC app that provides an entry point to common remote / server
interactions.

To generate a configuration file, use:
    sc-remote -configure

    or to specify a specific server and/or port:
    sc-remote -configure -server https://example.com
    sc-remote -configure -server https://example.com:1234

    to add or remove directories from upload whitelist, these
        also support globbing:
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

    if remote.get("cmdarg", 'configure'):
        if remote.get("cmdarg", 'list'):
            client = Client(remote)
            client.print_configuration()
            return 0

        if not remote.get("cmdarg", 'add') and not remote.get("cmdarg", 'remove'):
            client = ConfigureClient(remote)
            client.configure_server(server=remote.get("cmdarg", 'server'))
        else:
            client = ConfigureClient(remote)
            client.configure_whitelist(add=remote.get("cmdarg", 'add'),
                                       remove=remote.get("cmdarg", 'remove'))

        return 0

    if project_cfg:
        project = Project.from_manifest(filepath=remote.find_files('cmdarg', 'cfg'))
    else:
        project = remote

    if remote.get("option", "credentials"):
        project.set("option", "credentials", remote.find_files("option", "credentials"))

    client = Client(project)
    # Main logic.
    # If no job-related options are specified, fetch and report basic info.
    # Create temporary project object and check on the server.
    client.check()

    # If the -cancel flag is specified, cancel the job.
    if remote.get("cmdarg", 'cancel'):
        client.cancel_job()

    # If the -delete flag is specified, delete the job.
    elif remote.get("cmdarg", 'delete'):
        client.delete_job()

    # If the -reconnect flag is specified, re-enter the client flow
    # in its "check_progress/ until job is done" loop.
    elif remote.get("cmdarg", 'reconnect'):
        # Start from successors of entry nodes, so entry nodes are not fetched from remote.
        flow = project.get('option', 'flow')
        entry_nodes = project.get("flowgraph", flow, field="schema").get_entry_nodes()
        for entry_node in entry_nodes:
            outputs = project.get("flowgraph", flow,
                                  field='schema').get_node_outputs(*entry_node)
            project.set('option', 'from', list(map(lambda node: node[0], outputs)))
        # Enter the remote run loop.
        try:
            client._run_loop()
        except KeyboardInterrupt:
            return 0

        # Summarize the run.
        project.summary()

    # If only a manifest is specified, make a 'check_progress/' request and report results:
    elif project_cfg:
        info = client.check_job_status()
        client._report_job_status(info)

    # Done
    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
