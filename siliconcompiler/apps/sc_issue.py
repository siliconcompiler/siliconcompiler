# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler
import tarfile
import json
import importlib

def main():
    progname = "sc-issue"
    chip = siliconcompiler.Chip(progname)
    switchlist = ['-cfg',
                  '-version',
                  '-arg_step',
                  '-arg_index',
                  '-tool_task_variable',
                  '-tool_task_option',
                  '-loglevel']
    description = """
    -----------------------------------------------------------
    Restricted SC app that generates a sharable testcase from a 
    failed flow or runs an issue generated with this program.
    -----------------------------------------------------------
    """

    default_file = 'sc_issue.tgz'

    issue_arguments = {
        '-generate': {'action': 'store_true',
                      'help': 'generate a testcase'},

        '-exclude_libraries': {'action': 'store_true',
                               'help': 'flag to ensure libraries are excluded in the testcase'},
        '-exclude_pdks': {'action': 'store_true',
                          'help': 'flag to ensure pdks are excluded in the testcase'},
        '-hash_files': {'action': 'store_true',
                        'help': 'flag to hash the files in the schema before generating the manifest'},

        '-run': {'action': 'store_true',
                 'help': 'run a provided testcase'},

        '-use': {'action': 'append',
                 'help': 'list of modules to load into test run'},

        '-file': {'default': default_file,
                  'help': f'filename for the generated testcase, defaults to {default_file}',
                  'metavar': '<file>'},
    }

    switches = chip.create_cmdline(progname,
                                   switchlist=switchlist,
                                   description=description,
                                   additional_args=issue_arguments)

    if switches['generate'] and switches['run']:
        raise ValueError('Only one of -generate or -run can be used')

    if switches['generate']:
        step = chip.get('arg', 'step')
        index = chip.get('arg', 'index')
        chip._generate_testcase(step,
                                index,
                                switches['file'],
                                include_pdks=not switches['exclude_pdks'],
                                include_libraries=not switches['exclude_libraries'],
                                hash_files=switches['hash_files'])
    if switches['run']:
        test_dir = os.path.splitext(os.path.basename(switches['file']))[0]
        with tarfile.open(switches['file'], 'r:gz') as f:
            f.extractall(path=test_dir)

        chip.read_manifest(f'{test_dir}/manifest.json')

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

        sc_os = issue_info['machine']['system']
        if 'distro' in issue_info['machine']:
            sc_os += f" {issue_info['machine']['distro']}"
        sc_os += f" {issue_info['machine']['osversion']} {issue_info['machine']['arch']} {issue_info['machine']['kernelversion']}"
        chip.logger.info(f"Machine: {sc_os}")
        chip.logger.info(f"Date: {issue_info['date']}")

        step = issue_info['run']['step']
        index = issue_info['run']['index']

        chip.set('arg', 'step', step)
        chip.set('arg', 'index', index)
        tool, task = chip._get_tool_task(step, index)
        chip.logger.info(f'Preparing run for {step}{index} - {tool}/{task}')

        # Modify run environment to point to extracted files
        builddir_key = ['option', 'builddir']
        new_builddir = f"{test_dir}/{chip.get(*builddir_key)}"
        chip.logger.info(f"Changing {builddir_key} to '{new_builddir}'")
        chip.set(*builddir_key, new_builddir)

        option_key = ['tool', tool, 'task', task, 'option']
        chip.logger.info(f"Removing previous settings of {option_key}: {chip.get(*option_key, step=step, index=index)}")
        chip.unset(*option_key, step=step, index=index)

        breakpoint_key = ['option', 'breakpoint']
        chip.logger.info(f"Setting {breakpoint_key} to True")
        chip.set(*breakpoint_key, True, step=step, index=index)

        if switches['use']:
            for use in switches['use']:
                try:
                    module = importlib.import_module(use)
                    chip.logger.info(f"Loading '{use}' module")
                    chip.use(module)
                except ModuleNotFoundError:
                    chip.logger.error(f"Unable to use '{use}' module")

        # Run task
        # Rerun setup task
        chip._setup_task(step, index)
        chip._runtask(step, index, {}, replay=True)

#########################
if __name__ == "__main__":
    sys.exit(main())
