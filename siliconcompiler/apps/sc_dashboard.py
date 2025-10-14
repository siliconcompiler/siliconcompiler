# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys
import shlex

import os.path

from typing import Union

from siliconcompiler import Project
from siliconcompiler.apps._common import pick_manifest
from siliconcompiler.report.dashboard.web import WebDashboard


def main():
    progname = "sc-dashboard"
    description = """
-----------------------------------------------------------
SC app to open a dashboard for a given manifest.

To open and allow sc-dashboard to autoload manifest:
    sc-dashboard

To open by specifying manifest:
    sc-dashboard -cfg <path to manifest>

To open by specifying design and optionally jobname:
    sc-dashboard -design <name>
    sc-dashboard -design <name> -jobname <jobname>

To specify a different port than the default:
    sc-dashboard -cfg <path to manifest> -port 10000

To include another project object to compare to:
    sc-dashboard -cfg <path to manifest> -graph_cfg <name of manifest> <path to other manifest>
        -graph_cfg <path to other manifest> ...
-----------------------------------------------------------
"""

    class DashboardProject(Project):
        def __init__(self):
            super().__init__()

            self._add_commandline_argument("cfg", "file", "configuration manifest")
            self._add_commandline_argument("port", "int", "port to open the dashboard app on")
            self._add_commandline_argument(
                "graph_cfg", "[str]", "project name - optional, path to project manifest (json)")

    cli = DashboardProject.create_cmdline(
        progname,
        description=description,
        switchlist=[
            '-design',
            '-arg_step',
            '-arg_index',
            '-jobname',
            '-cfg',
            '-port',
            '-graph_cfg'],
        use_sources=False)

    manifest: Union[None, str] = cli.get("cmdarg", "cfg")

    # Attempt to load a manifest
    if not manifest:
        manifest = pick_manifest(cli)

    if not manifest:
        cli.logger.error("Unable to find manifest")
        return 1

    cli.logger.info(f'Loading manifest: {manifest}')
    project = Project.from_manifest(filepath=manifest)

    graph_projs = []
    if cli.get("cmdarg", "graph_cfg"):
        for i, name_and_file_path in enumerate(cli.get("cmdarg", "graph_cfg")):
            name_and_file_path = shlex.split(name_and_file_path)
            args = len(name_and_file_path)
            if args == 0:
                continue
            elif args == 1:
                name = f'cfg{i}'
                file_path = name_and_file_path[0]
            elif args == 2:
                name = name_and_file_path[0]
                file_path = name_and_file_path[1]
            else:
                raise ValueError(('graph_cfg accepts a max of 2 values, you supplied'
                                  f' {args} in "-graph_cfg {name_and_file_path}"'))
            if not os.path.isfile(file_path):
                raise ValueError(f'not a valid file path: {file_path}')
            graph_proj = Project.from_manifest(filepath=file_path)
            graph_projs.append({
                'project': graph_proj,
                'name': name,
                'cfg_path': os.path.abspath(file_path)
            })

    dashboard = WebDashboard(project, port=cli.get("cmdarg", "port"), graph_projs=graph_projs)
    dashboard.open_dashboard()
    dashboard.wait()

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
