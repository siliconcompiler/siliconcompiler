# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler
import tarfile
import json
from siliconcompiler.scheduler import _runtask, _executenode
from siliconcompiler.utils.issue import generate_testcase
from siliconcompiler.tools._common import get_tool_task


def main():
    progname = "sc-issue"
    chip = siliconcompiler.Chip(progname)
    switchlist = ['-cfg',
                  '-arg_step',
                  '-arg_index',
                  '-tool_task_var',
                  '-tool_task_option',
                  '-loglevel',
                  '-use']
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

    issue_arguments = {
        '-exclude_libraries': {'action': 'store_true',
                               'help': 'flag to ensure libraries are excluded in the testcase',
                               'sc_print': False},
        '-exclude_pdks': {'action': 'store_true',
                          'help': 'flag to ensure pdks are excluded in the testcase',
                          'sc_print': False},
        '-hash_files': {'action': 'store_true',
                        'help': 'flag to hash the files in the schema before generating '
                                'the manifest',
                        'sc_print': False},

        '-run': {'action': 'store_true',
                 'help': 'run a provided testcase',
                 'sc_print': False},

        '-add_library': {'action': 'append',
                         'help': 'library to include in the testcase, if not provided all '
                                 'libraries will be added according to the -exclude_libraries flag',
                         'metavar': '<library>',
                         'sc_print': False},
        '-add_pdk': {'action': 'append',
                     'help': 'pdk to include in the testcase, if not provided all libraries '
                             'will be added according to the -exclude_pdks flag',
                     'metavar': '<pdk>',
                     'sc_print': False},

        '-file': {'help': 'filename for the generated testcase',
                  'metavar': '<file>',
                  'sc_print': False},
    }

    try:
        switches = chip.create_cmdline(progname,
                                       switchlist=switchlist,
                                       description=description,
                                       additional_args=issue_arguments)
    except Exception as e:
        chip.logger.error(e)
        return 1

    if not switches['run']:
        step = chip.get('arg', 'step')
        index = chip.get('arg', 'index')

        if not step:
            chip.logger.error('Unable to determine step from manifest')
        if not index:
            chip.logger.error('Unable to determine index from manifest')
        if not step or not index:
            # Exit out
            return 1

        generate_testcase(chip,
                          step,
                          index,
                          switches['file'],
                          include_pdks=not switches['exclude_pdks'],
                          include_specific_pdks=switches['add_pdk'],
                          include_libraries=not switches['exclude_libraries'],
                          include_specific_libraries=switches['add_library'],
                          hash_files=switches['hash_files'])

        return 0

    if switches['run']:
        if not switches['file']:
            raise ValueError('-file must be provided')

        test_dir = os.path.basename(switches['file']).split('.')[0]
        with tarfile.open(switches['file'], 'r:gz') as f:
            f.extractall(path='.')

        chip.read_manifest(f'{test_dir}/orig_manifest.json')

        with open(f'{test_dir}/issue.json', 'r') as f:
            issue_info = json.load(f)

        # Report major information
        sc_version = issue_info['version']['sc']
        if 'commit' in issue_info['version']['git']:
            sc_source = issue_info['version']['git']['commit']
        else:
            sc_source = 'installed'

        chip.logger.info(f"Design: {chip.design}")
        chip.logger.info(f"SiliconCompiler version: {sc_version} / {sc_source}")
        chip.logger.info(f"Schema version: {issue_info['version']['schema']}")
        chip.logger.info(f"Python version: {issue_info['python']['version']}")

        sc_machine = issue_info['machine']
        sc_os = sc_machine['system']
        if 'distro' in sc_machine:
            sc_os += f" {sc_machine['distro']}"
        sc_os += f" {sc_machine['osversion']} {sc_machine['arch']} {sc_machine['kernelversion']}"
        chip.logger.info(f"Machine: {sc_os}")
        chip.logger.info(f"Date: {issue_info['date']}")

        step = issue_info['run']['step']
        index = issue_info['run']['index']

        chip.set('arg', 'step', step)
        chip.set('arg', 'index', index)
        tool, task = get_tool_task(chip, step, index)
        chip.logger.info(f'Preparing run for {step}{index} - {tool}/{task}')

        # Modify run environment to point to extracted files
        builddir_key = ['option', 'builddir']
        new_builddir = f"{test_dir}/{chip.get(*builddir_key)}"
        chip.logger.info(f"Changing {builddir_key} to '{new_builddir}'")
        chip.set(*builddir_key, new_builddir)

        # Run task
        # Rerun setup task, assumed to be running in its own thread so
        # multiprocess is not needed
        flow = chip.get('option', 'flow')
        _runtask(chip, flow, step, index, _executenode, replay=True)

        return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
