# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import argparse
import sys

from siliconcompiler.package.cleanup import CACHE_COMMAND
from siliconcompiler.scheduler.send_messages import EMAIL_COMMAND
from siliconcompiler.utils import PATHS_COMMAND
from siliconcompiler.utils.settings import SETTINGS_COMMAND


#: The app's commands, each declared by the module that owns what it configures.
_COMMANDS = (SETTINGS_COMMAND, EMAIL_COMMAND, CACHE_COMMAND, PATHS_COMMAND)


def _parser() -> argparse.ArgumentParser:
    rule = "-" * 59
    description = "\n\n".join((
        f"{rule}\nSC app to view and change this machine's SiliconCompiler\nconfiguration.",
        *(command.examples for command in _COMMANDS))) + f"\n{rule}"

    parser = argparse.ArgumentParser(
        prog="sc-config",
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", metavar="<command>", required=True)
    for command in _COMMANDS:
        command.add_parser(commands)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        return args.func(args)
    except (ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
