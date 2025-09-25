# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.
import base64
import gzip
import io
import json
import os
import stat
import sys
import tarfile
import tempfile
import textwrap

import os.path

from datetime import datetime

from siliconcompiler import Project
from siliconcompiler import utils
from siliconcompiler.utils.curation import collect
from siliconcompiler.schema_support.record import RecordTime


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
    progname = "replay"
    description = """
    ------------------------------------------------------------
    Utility script to generate a replay script from a previous run.
    ------------------------------------------------------------
    """

    class ReplayProject(Project):
        def __init__(self):
            super().__init__()
            self._add_commandline_argument(
                "file", "file", "Path to generate replay file to.", defvalue="replay.sh")
            self._add_commandline_argument(
                "cfg", "file", "configuration manifest")
            self.unset("option", "jobname")

    # Read command-line inputs and generate project objects to run the flow on.
    proj = ReplayProject.create_cmdline(
        progname,
        description=description,
        switchlist=[
            "-file",
            "-cfg",
            "-jobname"
        ],
        use_sources=False
    )

    if not proj.get("cmdarg", "cfg"):
        proj.logger.error("-cfg not provided")
        return 1

    replay = Project.from_manifest(filepath=proj.get("cmdarg", "cfg"))
    if proj.get("option", "jobname"):
        replay.set("option", "jobname", proj.get("option", "jobname"))

    # Print Job Summary
    job = replay.history(replay.get('option', 'jobname'))
    pythonpackages = job.get('record', 'pythonpackage')

    pythonversion = set()
    nodes = set()
    for version, step, index in job.get('record', 'pythonversion', field=None).getvalues():
        pythonversion.add(version)
        nodes.add((step, index))

    if len(pythonversion) > 1:
        replay.logger.warning(f"More than one python version detected: {', '.join(pythonversion)}")
    pythonversion = list(pythonversion)[0]

    tools = {}
    tool_versions = []
    for step, index in nodes:
        toolpath = job.get('record', 'toolpath', step=step, index=index)
        toolversion = job.get('record', 'toolversion', step=step, index=index)

        if toolpath is None:
            continue

        tools.setdefault(toolpath, set()).add(toolversion)
        if toolversion:
            tool = job.get('flowgraph', job.get('option', 'flow'), step, index, 'tool')
            tool_versions.append(
                ((step, index), tool, toolversion)
            )

    print("SUMMARY       :")
    print(f"design        : {job.name}")
    print(f"pythonversion : {pythonversion}")

    print("Python packages requires:")
    for pkg in sorted(pythonpackages):
        print(f"  {pkg}")

    if tools:
        print("Tool requirements:")
        tool_len = max([len(os.path.basename(tool)) for tool, _ in tools.items()])
        for tool, version in tools.items():
            print(f"  {os.path.basename(tool):<{tool_len}}: {', '.join(version)}")

    path = os.path.abspath(proj.get("cmdarg", "file"))
    os.makedirs(os.path.dirname(path), exist_ok=True)

    record_schema = job.get('record', field="schema")
    starttime = datetime.fromtimestamp(
        record_schema.get_earliest_time(RecordTime.START)).strftime(
            '%Y-%m-%d %H:%M:%S')

    with io.StringIO() as fd:
        fd.write(utils.get_file_template('replay/requirements.txt').render(
            design=job.name,
            jobname=job.get("option", "jobname"),
            date=starttime,
            pkgs=pythonpackages
        ))
        fd.flush()
        requirements_file = fd.getvalue()

    with tempfile.TemporaryDirectory() as collectdir:
        collect(job, directory=collectdir, verbose=True)

        with io.BytesIO() as fd:
            with tarfile.open(fileobj=fd, mode='w:gz') as tar:
                tar.add(collectdir, arcname='')
            fd.flush()
            collect_files = convert_base64(fd.getvalue())

    with io.StringIO() as fd:
        fd.write(utils.get_file_template('replay/replay.py.j2').render(
            design=job.name,
            jobname=job.get("option", "jobname"),
            date=starttime,
            src_file=wrap_text(collect_files),
            tool_versions=sorted(tool_versions)
        ))
        fd.flush()
        script = convert_base64(compress(fd.getvalue()))

    manifest = convert_base64(compress(json.dumps(job.getdict(), indent=2)))

    tool_info = []
    for tool, version in tools.items():
        tool_info.append(f"{os.path.basename(tool):<{tool_len}}: {', '.join(version)}")

    description = f"Replay for {job.name} / {job.get('option', 'jobname')}\n" \
        f"Run on: {starttime}"

    with open(path, 'w', encoding='utf-8') as wf:
        wf.write(utils.get_file_template('replay/setup.sh').render(
            design=job.name,
            jobname=job.get("option", "jobname"),
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
