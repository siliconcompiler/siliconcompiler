# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

# Standard Modules
import base64
import io
import json
import gzip
import os
import stat
import sys
import tarfile
import tempfile
import textwrap

from datetime import datetime

import siliconcompiler
from siliconcompiler.apps._common import UNSET_DESIGN
from siliconcompiler import SiliconCompilerError
from siliconcompiler import utils
from siliconcompiler.record import RecordTime


def make_bytes(data):
    if isinstance(data, bytes):
        return data
    return data.encode('utf-8')


def compress(data):
    return gzip.compress(make_bytes(data))


def convert_base64(data):
    return base64.b64encode(make_bytes(data))


def wrap_text(data):
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    return textwrap.wrap(data)


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
        file_arg = {
            'metavar': '<file>',
            'help': 'Path to generate replay file to.',
            'default': 'replay.sh',
            'sc_print': True
        }
        args = chip.create_cmdline(
            progname,
            description=description,
            switchlist=['-cfg',
                        '-jobname',
                        '-loglevel'],
            additional_args={
                '-file': file_arg
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
    for version, step, index in chip.schema.get('history', jobname, 'record', 'pythonversion',
                                                field=None).getvalues():
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

    path = os.path.abspath(args['file'])
    os.makedirs(os.path.dirname(path), exist_ok=True)

    record_schema = chip.schema.get('history', jobname, 'record', field="schema")
    starttime = datetime.fromtimestamp(
        record_schema.get_earliest_time(RecordTime.START)).strftime(
            '%Y-%m-%d %H:%M:%S')

    with io.StringIO() as fd:
        fd.write(utils.get_file_template('replay/requirements.txt').render(
            design=chip.design,
            jobname=jobname,
            date=starttime,
            pkgs=pythonpackages
        ))
        fd.flush()
        requirements_file = fd.getvalue()

    with tempfile.TemporaryDirectory() as collect:
        chip.collect(directory=collect, verbose=True, exclude_packages=['siliconcompiler'])

        with io.BytesIO() as fd:
            with tarfile.open(fileobj=fd, mode='w:gz') as tar:
                tar.add(collect, arcname='')

            fd.flush()
            collect_files = convert_base64(fd.getvalue())

    with io.StringIO() as fd:
        fd.write(utils.get_file_template('replay/replay.py.j2').render(
            design=chip.design,
            jobname=jobname,
            date=starttime,
            src_file=wrap_text(collect_files),
            tool_versions=sorted(tool_versions)
        ))
        fd.flush()
        script = convert_base64(compress(fd.getvalue()))

    manifest = convert_base64(compress(json.dumps(chip.schema.getdict(), indent=2)))

    tool_info = []
    for tool, version in tools.items():
        tool_info.append(f"{os.path.basename(tool):<{tool_len}}: {', '.join(version)}")

    description = f"Replay for {chip.design} / {jobname}\nRun on: {starttime}"

    with open(path, 'w', encoding='utf-8') as wf:
        wf.write(utils.get_file_template('replay/setup.sh').render(
            design=chip.design,
            jobname=jobname,
            date=starttime,
            description=description,
            pythonversion=pythonversion,
            requirements=requirements_file.splitlines(),
            script=wrap_text(script),
            manifest=wrap_text(manifest),
            tools=tool_info
        ))

    permissions = stat.S_IMODE(os.lstat(path).st_mode)
    os.chmod(path, permissions | stat.S_IXUSR)

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
