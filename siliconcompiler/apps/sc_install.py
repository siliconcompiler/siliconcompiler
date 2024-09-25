# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

import argparse
import glob
import subprocess
import sys
import shutil
import re
import os.path
from pathlib import Path
import siliconcompiler
from siliconcompiler.scheduler import _get_machine_info


def install_tool(tool, script, build_dir, prefix):
    # Ensure build dir is available
    build_dir = Path(build_dir) / tool
    shutil.rmtree(str(build_dir), ignore_errors=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    # setup environment
    env = os.environ.copy()
    env["PREFIX"] = prefix

    # run
    ret = subprocess.call(script, env=env, cwd=build_dir)
    if ret != 0:
        print(f"Error occurred while building/installing {tool}")
        return False
    return True


def _get_tools_list():
    tools_root = Path(siliconcompiler.__file__).parent / "toolscripts"

    machine_info = _get_machine_info()
    script_dir = None
    if machine_info['system'].lower() == 'linux':
        if machine_info['distro'].lower() == 'ubuntu':
            version, _ = machine_info['osversion'].split('.')
            script_dir = f"{machine_info['distro'].lower()}{version}"
    if script_dir:
        script_dir = tools_root / script_dir
        if not script_dir.exists():
            script_dir = None

    tools = {}
    if script_dir:
        for script in glob.glob(str(script_dir / "install-*.sh")):
            tool = re.match(r"install-(.*)\.sh", os.path.basename(script).lower())
            tools[tool.group(1)] = script

    return tools


def main():
    progname = "sc-install"
    description = """
-----------------------------------------------------------
SC app install supported tools.

To install a single tool:
    sc-install openroad

To install multiple tools tool:
    sc-install openroad yosys klayout

To install tools in a different location:
    sc-install -prefix /usr/local yosys

To build tools in a different location:
    sc-install -build_dir /tmp yosys
-----------------------------------------------------------
"""
    parser = argparse.ArgumentParser(
        prog=progname,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    tools = _get_tools_list()

    parser.add_argument(
        "tool",
        nargs="+",
        choices=tools.keys(),
        help="tool to install")

    parser.add_argument(
        "-prefix",
        default=Path.home() / ".local",
        help="Prefix to use when installing tool",
        metavar="<path>")

    parser.add_argument(
        "-build_dir",
        default=Path.home() / ".sc" / "tool_build",
        help="Directory to build the tool in",
        metavar="<path>")

    args = parser.parse_args()

    for tool in args.tool:
        if not install_tool(tool, tools[tool], args.build_dir, args.prefix):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
