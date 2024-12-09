# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

# Standard Modules
import os
import stat
import sys

import siliconcompiler
from siliconcompiler.apps._common import UNSET_DESIGN
from siliconcompiler import SiliconCompilerError
from siliconcompiler import utils


###########################
def main():
    progname = "summarize"
    description = """
    ------------------------------------------------------------
    Utility script to print job record information from a manifest
    needed to replay that manifest.
    ------------------------------------------------------------
    """
    # Create a base chip class.
    chip = siliconcompiler.Chip(UNSET_DESIGN)

    # Read command-line inputs and generate Chip objects to run the flow on.
    try:
        generation_arg = {
            'metavar': '<path>',
            'help': '(optional) Path to generate replay files to, if specified.',
            'sc_print': True
        }
        args = chip.create_cmdline(
            progname,
            description=description,
            switchlist=['-cfg',
                        '-jobname',
                        '-loglevel'],
            additional_args={
                '-path': generation_arg
            })
    except SiliconCompilerError:
        return 1
    except Exception as e:
        chip.logger.error(e)
        return 1

    design = chip.get('design')
    if design == UNSET_DESIGN:
        chip.logger.error('Design not loaded')
        return 1

    # Print Job Summary
    jobname = chip.get('option', 'jobname')
    pythonpackages = chip.get('record', 'pythonpackage', job=jobname)

    pythonversion = set()
    nodes = set()
    for version, step, index in chip.schema._getvals('history', jobname, 'record', 'pythonversion'):
        pythonversion.add(version)
        nodes.add((step, index))

    if len(pythonversion) > 1:
        chip.logger.warning(f"More than one python version detected: {', '.join(pythonversion)}")
    pythonversion = list(pythonversion)[0]

    tools = {}
    tool_versions = []
    for step, index in nodes:
        toolpath = chip.get('record', 'toolpath', job=jobname, step=step, index=index)
        toolversion = chip.get('record', 'toolversion', job=jobname, step=step, index=index)

        if toolpath is None:
            continue

        tools.setdefault(toolpath, set()).add(toolversion)
        if toolversion:
            tool = chip.get('flowgraph', chip.get('option', 'flow'), step, index, 'tool')
            tool_versions.append(
                ((step, index), tool, toolversion)
            )

    print("SUMMARY       :")
    print(f"design        : {chip.design}")
    print(f"pythonversion : {pythonversion}")

    print("Python packages requires:")
    for pkg in sorted(pythonpackages):
        print(f"  {pkg}")

    print("Tool requirements:")
    tool_len = max([len(os.path.basename(tool)) for tool, _ in tools.items()])
    for tool, version in tools.items():
        print(f"  {os.path.basename(tool):<{tool_len}}: {', '.join(version)}")

    if 'path' in args and args['path']:
        path = args['path']
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, 'requirements.txt'), 'w', encoding='utf-8') as wf:
            wf.write(utils.get_file_template('replay/requirements.txt').render(
                design=chip.design,
                source=', '.join(chip.find_files('option', 'cfg')),
                jobname=jobname,
                pkgs=pythonpackages
            ))

        scripts = []
        scripts.append(os.path.join(path, 'setup.sh'))
        with open(scripts[-1], 'w', encoding='utf-8') as wf:
            wf.write(utils.get_file_template('replay/setup.sh').render(
                design=chip.design,
                source=', '.join(chip.find_files('option', 'cfg')),
                jobname=jobname,
                pythonversion=pythonversion
            ))

        scripts.append(os.path.join(path, 'run.py'))
        with open(scripts[-1], 'w', encoding='utf-8') as wf:
            wf.write(utils.get_file_template('replay/run.py.j2').render(
                design=chip.design,
                source=', '.join(chip.find_files('option', 'cfg')),
                cfgs=chip.find_files('option', 'cfg'),
                jobname=jobname,
                tool_versions=sorted(tool_versions)
            ))

        for script in scripts:
            permissions = stat.S_IMODE(os.lstat(script).st_mode)
            os.chmod(script, permissions | stat.S_IXUSR)

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
