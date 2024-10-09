# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

import argparse
import glob
import subprocess
import sys
import shutil
import re
import os.path
from collections.abc import Container
from pathlib import Path
import siliconcompiler
from siliconcompiler.scheduler import _get_machine_info


class ChoiceOptional(Container):
    def __init__(self, choices):
        super().__init__()

        self.__choices = set(choices)

    def __contains__(self, item):
        if not item:
            # allow empty value
            return True
        return item in self.__choices

    def __iter__(self):
        return self.__choices.__iter__()

    def get_items(self, choices):
        items = set(choices)
        return sorted(list(items))


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


def show_tool(tool, script):
    def print_header(head):
        border_len = max(80, len(script) + 2)
        border = border_len*"#"
        print(border)
        print(f"# {tool} script / {head}")
        if head == "start":
            print(f"# {script}")
        print(border)

    print_header("start")

    with open(script) as f:
        for line in f:
            print(line.rstrip())

    print_header("end")


def _get_os_name():
    machine_info = _get_machine_info()
    system = machine_info.get('system', "").lower()
    distro = machine_info.get('distro', "").lower()
    osversion = machine_info.get('osversion', "").lower()
    if system == 'linux':
        if distro == 'ubuntu':
            version, _ = osversion.split('.')
            return f"{distro}{version}"
        elif distro == 'rocky':
            version, _ = osversion.split('.')
            return f"rhel{version}"
        elif distro == 'rhel':
            version, _ = osversion.split('.')
            return f"rhel{version}"
    return None


def print_machine_info():
    machine_info = _get_machine_info()
    mapped_os = _get_os_name()

    print("System:   ", machine_info.get('system', None))
    print("Distro:   ", machine_info.get('distro', None))
    print("Version:  ", machine_info.get('osversion', None))
    print("Mapped OS:", mapped_os)
    print("Scripts:  ", _get_tool_script_dir())


def _get_tool_script_dir():
    return Path(siliconcompiler.__file__).parent / "toolscripts"


def _get_tools_list():
    tools_root = _get_tool_script_dir()

    script_dir = None
    os_dir = _get_os_name()
    if os_dir:
        script_dir = tools_root / os_dir
        if not script_dir.exists():
            script_dir = None

    tools = {}
    if script_dir:
        for script in glob.glob(str(script_dir / "install-*.sh")):
            tool = re.match(r"install-(.*)\.sh", os.path.basename(script).lower())
            tools[tool.group(1)] = script

    return tools


def _recommended_tool_groups(tools):
    groups = {
        "asic": {"surelog", "sv2v", "yosys", "openroad", "klayout"},
        "fpga": {"surelog", "sv2v", "yosys", "vpr"},
        "digital-simulation": {"verilator", "icarus"},
        "analog-simulation": {"xyce"}
    }

    filter_groups = {}
    for group, group_tools in groups.items():
        if all([tool in tools for tool in group_tools]):
            filter_groups[group] = group_tools
    return filter_groups


def main():
    progname = "sc-install"
    description = """
-----------------------------------------------------------
SC app install supported tools.

To install a single tool:
    sc-install openroad

To install multiple tools:
    sc-install openroad yosys klayout

To install a group of tools:
    sc-install -group asic

To install tools in a different location:
    sc-install -prefix /usr/local yosys

To build tools in a different location:
    sc-install -build_dir /tmp yosys

To show the install script:
    sc-install -show openroad

To system debugging information (this should only be used to debug):
    sc-install -debug_machine
-----------------------------------------------------------
"""
    parser = argparse.ArgumentParser(
        prog=progname,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    tools = _get_tools_list()

    tool_choices = ChoiceOptional(tools.keys())
    parser.add_argument(
        "tool",
        nargs="*",
        choices=tool_choices,
        help="tool to install")

    tool_groups = _recommended_tool_groups(tools)
    parser.add_argument(
        "-group",
        nargs="+",
        choices=tool_groups.keys(),
        help=f"tool group to install{' - not supported' if not tool_groups else ''}")

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

    parser.add_argument(
        "-show",
        action="store_true",
        help="Show the install script and exit")

    parser.add_argument(
        "-debug_machine",
        action="store_true",
        help="Show information about this machine and exit")

    args = parser.parse_args()

    if args.debug_machine:
        print_machine_info()
        return 0

    if not args.tool:
        args.tool = []

    args.tool = list(args.tool)
    if args.group:
        for group in args.group:
            args.tool.extend(tool_groups[group])

    tools_handled = set()
    for tool in args.tool:
        if tool in tools_handled:
            continue
        tools_handled.add(tool)
        if args.show:
            show_tool(tool, tools[tool])
        else:
            if not install_tool(tool, tools[tool], args.build_dir, args.prefix):
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
