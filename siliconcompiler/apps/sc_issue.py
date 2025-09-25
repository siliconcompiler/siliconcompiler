# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import json
import sys
import tarfile

import os.path

from siliconcompiler import Project
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.utils.issue import generate_testcase


def main():
    progname = "sc-issue"
    description = """
-----------------------------------------------------------
Restricted SC app that generates a sharable testcase from a
failed flow or runs an issue generated with this program.

To generate a testcase, use:
    sc-issue -cfg <stepdir>/outputs/<design>.pkg.json

    or include a different step/index than what the cfg_file is pointing to:
    sc-issue -cfg <otherdir>/outputs/<design>.pkg.json -arg_step <step> -arg_index <index>

    or include specific libraries while excluding others:
    sc-issue -cfg <stepdir>/outputs/<design>.pkg.json -exclude_libraries -add_library sram -add_library gpio

To run a testcase, use:
    sc-issue -run -file sc_issue_<...>.tar.gz
-----------------------------------------------------------
"""  # noqa E501

    class IssueProject(Project):
        def __init__(self):
            super().__init__()

            self._add_commandline_argument("cfg", "file", "configuration manifest")
            self._add_commandline_argument("run", "bool", "run a provided testcase")
            self._add_commandline_argument("hash_files", "bool",
                                           "flag to hash the files in the schema before "
                                           "generating the manifest")
            self._add_commandline_argument("file", "file",
                                           "filename for the generated testcase")
            self._add_commandline_argument("add_pdk", "[str]",
                                           "pdk to include in the testcase, if not provided all "
                                           "libraries will be added according to the "
                                           "-exclude_pdks flag")
            self._add_commandline_argument("add_library", "[str]",
                                           "library to include in the testcase, if not "
                                           "provided all libraries will be added according to "
                                           "the -exclude_libraries flag")
            self._add_commandline_argument("exclude_libraries", "bool",
                                           "flag to ensure libraries are excluded in the testcase")
            self._add_commandline_argument("exclude_pdks", "bool",
                                           "flag to ensure pdks are excluded in the testcase")

            # TODO port add dep func
            # self._add_commandline_argument("add_dep", "[str]",
            # "dependency to load before running", "-add_dep <str>")

    switchlist = ['-arg_step',
                  '-arg_index',
                  '-cfg',
                  '-run',
                  '-hash_files',
                  '-file',
                  '-add_pdk',
                  '-add_library',
                  '-exclude_libraries',
                  '-exclude_pdks']

    issue = IssueProject.create_cmdline(
        progname,
        description=description,
        switchlist=switchlist)

    if not issue.get("cmdarg", "run"):
        project = Project.from_manifest(filepath=issue.get("cmdarg", "cfg"))

        if issue.get("arg", "step"):
            project.set("arg", "step", issue.get("arg", "step"))
        if issue.get("arg", "index"):
            project.set("arg", "index", issue.get("arg", "index"))

        step = project.get('arg', 'step')
        index = project.get('arg', 'index')
        if not step:
            project.logger.error('Unable to determine step from manifest')
        if not index:
            project.logger.error('Unable to determine index from manifest')
        if not step or not index:
            # Exit out
            return 1

        generate_testcase(project,
                          step,
                          index,
                          issue.get("cmdarg", "file"),
                          include_pdks=not issue.get("cmdarg", "exclude_pdks"),
                          include_specific_pdks=issue.get("cmdarg", "add_pdk"),
                          include_libraries=not issue.get("cmdarg", "exclude_libraries"),
                          include_specific_libraries=issue.get("cmdarg", "add_library"),
                          hash_files=issue.get("cmdarg", "hash_files"))

        return 0
    else:
        file = issue.get("cmdarg", "file")
        if not file:
            raise ValueError('-file must be provided')

        test_dir = os.path.basename(file)[0:-7]
        with tarfile.open(file, 'r:gz') as f:
            f.extractall(path='.')

        project = Project.from_manifest(filepath=f'{test_dir}/orig_manifest.json')

        with open(f'{test_dir}/issue.json', 'r') as f:
            issue_info = json.load(f)

        # Report major information
        sc_version = issue_info['version']['sc']
        if 'commit' in issue_info['version']['git']:
            sc_source = issue_info['version']['git']['commit']
        else:
            sc_source = 'installed'

        project.logger.info(f"Design: {project.name}")
        project.logger.info(f"SiliconCompiler version: {sc_version} / {sc_source}")
        project.logger.info(f"Schema version: {issue_info['version']['schema']}")
        project.logger.info(f"Python version: {issue_info['python']['version']}")

        sc_machine = issue_info['machine']
        sc_os = sc_machine['system']
        if 'distro' in sc_machine:
            sc_os += f" {sc_machine['distro']}"
        sc_os += f" {sc_machine['osversion']} {sc_machine['arch']} {sc_machine['kernelversion']}"
        project.logger.info(f"Machine: {sc_os}")
        project.logger.info(f"Date: {issue_info['date']}")

        step = issue_info['run']['step']
        index = issue_info['run']['index']

        project.set('arg', 'step', step)
        project.set('arg', 'index', index)
        flow = project.get("option", 'flow')
        tool = project.get("flowgraph", flow, step, index, "tool")
        task = project.get("flowgraph", flow, step, index, "task")
        taskmod = project.get("flowgraph", flow, step, index, "taskmodule")
        project.logger.info(f'Preparing run for {step}/{index} - {tool}/{task} - {taskmod}')

        # Modify run environment to point to extracted files
        builddir_key = ['option', 'builddir']
        new_builddir = f"{test_dir}/{project.get(*builddir_key)}"
        project.logger.info(f"Changing {builddir_key} to '{new_builddir}'")
        project.set(*builddir_key, new_builddir)

        # Run task
        # Rerun setup task, assumed to be running in its own thread so
        # multiprocess is not needed
        SchedulerNode(project,
                      step,
                      index,
                      replay=True).run()

        return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
