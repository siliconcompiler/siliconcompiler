# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.
import argparse
import glob
import re
import shutil
import subprocess
import sys

import os.path

from typing import Dict, List, Optional, Set

from collections.abc import Container
from pathlib import Path

import siliconcompiler

from siliconcompiler.schema_support.record import RecordSchema
from siliconcompiler.utils import get_plugins


def get_install_groups() -> Dict[str, List[str]]:
    """
    Provide recommended install tool groups for common workflows.

    Each mapping key is a high-level group name and each value is an ordered list of tool
    identifiers suitable for that group.

    Returns:
        dict: Mapping from group name (str) to a list of tool identifiers (List[str]).
    """
    return {
        "asic": ["sv2v", "yosys", "yosys-slang", "openroad", "klayout"],
        "asic-hls": ["bambu", "yosys", "yosys-slang", "openroad", "klayout"],
        "fpga": ["sv2v", "yosys", "yosys-slang", "wildebeest", "vpr", "opensta"],
        "digital-simulation": ["verilator", "icarus", "surfer"],
        "analog-simulation": ["xyce"]
    }


def get_install_tools(osname: str) -> Dict[str, str]:
    tools_root = _get_tool_script_dir()

    script_dir = None
    if osname:
        script_dir = tools_root / osname
        if not script_dir.exists():
            script_dir = None

    tools = {}
    if script_dir:
        for script in glob.glob(str(script_dir / "install-*.sh")):
            tool = re.match(r"install-(.*)\.sh", os.path.basename(script).lower())
            if tool:
                tools[tool.group(1)] = script

    return tools


class ChoiceOptional(Container):
    def __init__(self, choices):
        super().__init__()

        self.__choices = sorted(set(choices))

    def __contains__(self, item):
        if not item:
            # allow empty value
            return True
        return item in self.__choices

    def __iter__(self):
        """
        Iterate over the stored choices.

        Returns:
            iterator: An iterator over the stored choice strings.
        """
        return self.__choices.__iter__()

    def get_items(self, choices: List[str]) -> List[str]:
        """
        Return a sorted list of unique choice strings.

        Parameters:
            choices (List[str]): Iterable of choice strings which may contain duplicates.

        Returns:
            List[str]: Sorted list containing each unique choice from `choices`.
        """
        items = set(choices)
        return sorted(items)


def install_tool(tool: str, script: str, build_dir: str, prefix: str) -> bool:
    """
    Prepare a build directory, configure the environment, and execute an install script for a tool.

    Parameters:
        tool (str): Tool identifier used to create a per-tool build subdirectory under `build_dir`.
        script (str): Path to the install script to execute.
        build_dir (str): Base directory where a per-tool build directory will be created.
        prefix (str): Installation prefix; added to PATH and used to determine whether
                      sudo is required.

    Returns:
        bool: `True` if the install script exited with status 0, `False` otherwise.
    """
    build_path = Path(build_dir) / tool
    shutil.rmtree(str(build_path), ignore_errors=True)
    build_path.mkdir(parents=True, exist_ok=True)

    # setup environment
    env = os.environ.copy()
    path = env.get("PATH", "").split(":")
    path.insert(0, os.path.join(prefix, "bin"))
    env["PATH"] = ":".join(path)
    env["PREFIX"] = prefix
    env["USE_SUDO_INSTALL"] = "no"
    try:
        os.makedirs(prefix, exist_ok=True)
    except PermissionError:
        env["USE_SUDO_INSTALL"] = "yes"
    if not os.access(prefix, os.W_OK):
        env["USE_SUDO_INSTALL"] = "yes"

    # run
    ret = subprocess.call(script, env=env, cwd=build_path)
    if ret != 0:
        print(f"Error occurred while building/installing {tool}")
        return False
    return True


def show_tool(tool: str, script: str) -> None:
    """
    Print a bordered header, the contents of the given install script, and a
    closing bordered footer.

    Parameters:
        tool (str): Tool identifier used in the printed header.
        script (str): Path to the install script file whose contents will be displayed.
    """
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


def _get_os_name() -> Optional[str]:
    """
    Map recorded machine information to a short OS identifier used by the installer.

    This inspects the machine information provided by RecordSchema and, for supported
    Linux distributions, returns a compact identifier composed of the distro and
    major version (for example, "ubuntu20" or "rhel8"). Returns None for
    non-Linux systems or unrecognized distributions.

    Returns:
        os_name (Optional[str]): Mapped OS identifier (e.g., "ubuntu20", "rhel8") or
        `None` if the OS cannot be mapped.
    """
    machine_info = RecordSchema.get_machine_information()
    system = machine_info.get('system', "").lower()
    if system == 'linux':
        distro = machine_info.get('distro', "").lower()
        if distro == 'ubuntu':
            osversion = machine_info.get('osversion', "").lower()
            version, _ = osversion.split('.')
            return f"{distro}{version}"
        elif distro == 'rocky':
            osversion = machine_info.get('osversion', "").lower()
            version, _ = osversion.split('.')
            return f"rhel{version}"
        elif distro == 'rhel':
            osversion = machine_info.get('osversion', "").lower()
            version, _ = osversion.split('.')
            return f"rhel{version}"
    return None


def print_machine_info() -> None:
    """
    Prints detected machine and mapped OS information.

    Prints the system name, distribution name, OS version, mapped OS identifier, and the path to
    the install tools scripts directory as obtained from RecordSchema.get_machine_information()
    and internal helpers.
    """
    machine_info = RecordSchema.get_machine_information()
    mapped_os = _get_os_name()

    print("System:   ", machine_info.get('system', None))
    print("Distro:   ", machine_info.get('distro', None))
    print("Version:  ", machine_info.get('osversion', None))
    print("Mapped OS:", mapped_os)
    print("Scripts:  ", _get_tool_script_dir())


def __print_summary(successful: Optional[Set[str]],
                    failed: Optional[str],
                    notstarted: Optional[Set[str]]) -> None:
    """
    Prints a fixed-width summary banner listing installed, failed, and pending tools.

    Parameters:
        successful (Optional[Set[str]]): Set of tool names that were installed; when provided,
                                         they are shown under "Installed".
        failed (Optional[str]): Name of a tool that failed to install; when provided, it is shown
                                under "Failed to install".
        notstarted (Optional[Set[str]]): Set of tool names that were not started or are pending;
                                         when provided, they are shown under "Pending".
    """
    max_len = 64
    print("#"*max_len)
    if successful:
        msg = f"Installed: {', '.join(sorted(successful))}"
        print(f"# {msg}")

    if failed:
        msg = f"Failed to install: {failed}"
        print(f"# {msg}")

    if notstarted:
        msg = f"Pending: {', '.join(sorted(notstarted))}"
        print(f"# {msg}")

    print("#"*max_len)


def _get_tool_script_dir() -> Path:
    return Path(siliconcompiler.__file__).parent / "toolscripts"


def _get_tools_list() -> Dict[str, str]:
    tools = {}
    os = _get_os_name()
    for plugin in get_plugins("install", name="tools"):
        tools.update(plugin(os))

    return tools


def _recommended_tool_groups(tools) -> Dict[str, List[str]]:
    groups = {}
    for plugin in get_plugins("install", name="groups"):
        groups.update(plugin())

    filter_groups = {}
    for group, group_tools in groups.items():
        if all([tool in tools for tool in group_tools]):
            filter_groups[group] = group_tools
        else:
            missing = sorted([tool for tool in group_tools if tool not in tools])
            filter_groups[group] = f"{group} group is not available for {_get_os_name()} " \
                f"due to lack of support for the following tools: {', '.join(missing)}"
    return filter_groups


class HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


def main() -> int:
    """
    CLI entry point for installing tools, showing install scripts, or printing machine
    debug information.

    Parses command-line arguments, validates the host OS, expands tool groups, and either
    displays install scripts (-show), prints machine info (-debug_machine), or runs install
    scripts for the requested tools, then prints a summary and optional shell-path guidance.

    Returns:
        `0` on successful completion, `1` on failure (e.g., unsupported OS or
        any tool installation failure).
    """
    progname = "sc-install"

    tools = _get_tools_list()
    group_desc = "\n".join(
        [f"    {grp}: {', '.join(grp_tools)}"
         for grp, grp_tools in _recommended_tool_groups(tools).items()])

    description = f"""
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
Tool groups:
{group_desc}
-----------------------------------------------------------
"""

    parser = argparse.ArgumentParser(
        prog=progname,
        description=description,
        formatter_class=HelpFormatter)

    if _get_os_name() is None:
        print("Unsupported operating system", file=sys.stderr)
        print_machine_info()
        return 1

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
            if isinstance(tool_groups[group], str):
                print(tool_groups[group], file=sys.stderr)
                return 1
            else:
                args.tool.extend(tool_groups[group])

    tools_handled = set()
    tools_completed = set()
    for tool in args.tool:
        if tool in tools_handled:
            continue
        tools_handled.add(tool)
        if args.show:
            show_tool(tool, tools[tool])
        else:
            if not install_tool(tool, tools[tool], args.build_dir, args.prefix):
                notstarted = set(args.tool) - tools_completed - tools_handled
                __print_summary(tools_completed, tool, notstarted)
                return 1
            else:
                tools_completed.add(tool)

    if not args.show:
        __print_summary(tools_completed, None, None)

        msgs = []
        for env, path in (
                ("PATH", "bin"),
                ("LD_LIBRARY_PATH", "lib")):
            check_path = os.path.join(args.prefix, path)
            envs = [
                os.path.expandvars(os.path.expanduser(p))
                for p in os.getenv(env, "").split(":")
            ]
            if check_path not in envs:
                msgs.extend([
                    "",
                    f"{check_path} not found in {env}",
                    "you may need to add it the following your shell",
                    "initialization script:",
                    f'export {env}="{check_path}:${env}"'
                ])
        if msgs:
            center_len = max(len(msg) for msg in msgs)
            max_len = center_len + 4
            print("#"*max_len)
            for msg in msgs:
                print(f"# {msg:<{center_len}} #")
            print(f"# {' '*center_len} #")
            print("#"*max_len)

    return 0


if __name__ == "__main__":
    sys.exit(main())
