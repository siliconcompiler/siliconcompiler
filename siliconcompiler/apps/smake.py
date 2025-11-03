# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
"""
A 'make'-like command-line utility for executing Python functions.

This script, 'smake', provides a simple command-line interface to run Python
functions defined in a specified file (defaulting to 'make.py'). It inspects
the target file, discovers all public functions, and automatically creates a
command-line interface to execute them with their respective arguments.

This allows for creating simple, self-documenting build or task scripts in
Python without the need for complex boilerplate code.
"""
import argparse
import sys
import tempfile

import os.path

from typing import Union, Tuple, Optional, Dict

from pathlib import Path

from inspect import getmembers, isfunction, getfullargspec

from siliconcompiler._metadata import version
from siliconcompiler.schema import utils

# The default filename to look for if none is specified.
__default_source_file = "make.py"


def __process_file(path: Union[Path, str], dir: str) -> Tuple[Dict, Optional[str], Optional[str]]:
    """
    Dynamically loads a Python module and inspects it for runnable targets.

    This function takes a file path, imports it as a Python module, and scans
    for all public functions (those not starting with an underscore). For each
    function found, it extracts its signature (arguments, default values, type
    annotations) and docstring to build a dictionary of "targets" that can be
    called from the command line.

    It also looks for a special `__scdefault` variable in the module to determine
    the default target to run if none is specified.

    Args:
        path (str): The path to the Python file to process.

    Returns:
        tuple: A tuple containing:
            - dict: A dictionary of discovered targets, with metadata for each.
            - str or None: The name of the default target, if any.
            - str or None: The docstring of the loaded module, if any.
    """
    if not os.path.exists(path):
        return {}, None, None

    mod_name, _ = os.path.splitext(os.path.basename(path))

    # Dynamically load the specified file as a Python module.
    with open(os.path.join(dir, "sc_module_load.py"), "w") as f:
        f.write(f"import {mod_name} as make\n")

    sys.path.insert(0, os.getcwd())
    sys.path.insert(0, os.path.dirname(path))

    # Load newly created file
    import sc_module_load
    make = sc_module_load.make

    # Inspect the module for public functions to treat as targets.
    args = {}
    for name, func in getmembers(make, isfunction):
        if name.startswith('_'):
            continue

        # Use the function's docstring for help text.
        docstring = utils.trim(func.__doc__)
        if not docstring:
            docstring = f"run \"{name}\""
        short_help = docstring.splitlines()[0]

        # Inspect the function's signature to build CLI arguments.
        func_spec = getfullargspec(func)
        func_args = {}
        for arg in func_spec.args:
            arg_type = func_spec.annotations.get(arg, str)
            func_args[arg] = {"type": arg_type}

        if func_spec.defaults:
            for arg, defval in zip(reversed(func_spec.args), reversed(func_spec.defaults)):
                func_args[arg]["default"] = defval
                # Infer type from default value if it's a basic type.
                if defval is not None and isinstance(defval, (bool, str, float, int)):
                    func_args[arg]["type"] = type(defval)

        args[name] = {
            "function": func,
            "help": short_help,
            "full_help": docstring,
            "args": func_args
        }

    # Determine the default target.
    default_arg = getattr(make, '__scdefault', list(args.keys())[0] if args else None)
    module_help = utils.trim(make.__doc__)

    return args, default_arg, module_help


def main(source_file: Optional[Union[str, Path]] = None) -> int:
    """
    The main entry point for the smake command-line application.

    This function handles command-line argument parsing, discovers targets
    from the source file, and executes the selected target function with the
    provided arguments.
    """
    progname = "smake"
    description = f"""-----------------------------------------------------------
SC app that provides a Makefile-like interface to Python
configuration files. This utility app will analyze a file
named "{__default_source_file}" (or the file specified with --file) to
determine the available targets.

To view the help, use:
    smake --help

To view the help for a specific target, use:
    smake <target> --help

To run a target, use:
    smake <target>

To run a target from a different file, use:
    smake --file <file> <target>

To run a target in a different directory, use:
    smake -C <directory> <target>

To run a target with arguments, use:
    smake <target> --arg1 value1 --arg2 value2
-----------------------------------------------------------"""

    # --- Pre-parsing to find --file and --directory arguments ---
    # This allows us to load the correct file before setting up the full parser.
    if not source_file:
        source_file = __default_source_file
        file_args = ('--file', '-f')
        if any(arg in sys.argv for arg in file_args):
            for file_arg in file_args:
                if file_arg in sys.argv:
                    try:
                        source_file = sys.argv[sys.argv.index(file_arg) + 1]
                    except IndexError:
                        print(f"Error: Argument for {file_arg} is missing.")
                        return 1
                    break

    source_dir = os.getcwd()
    dir_args = ('--directory', '-C')
    if any(arg in sys.argv for arg in dir_args):
        for dir_arg in dir_args:
            if dir_arg in sys.argv:
                try:
                    source_dir = sys.argv[sys.argv.index(dir_arg) + 1]
                except IndexError:
                    print(f"Error: Argument for {dir_arg} is missing.")
                    return 1
                break

    if source_dir and os.path.isdir(source_dir):
        os.chdir(source_dir)
    elif source_dir:
        print(f"Error: Unable to change directory to {source_dir}")
        return 1

    with tempfile.TemporaryDirectory(prefix="smake") as dir:
        # Add temp dir to path
        sys.path.insert(0, dir)

        # --- Process the source file to discover targets ---
        make_args, default_arg, module_help = __process_file(source_file, dir) \
            if source_file else ({}, None, None)

        if module_help:
            description += f"\n\n{module_help}\n\n"
            description += "-----------------------------------------------------------"

        # --- Set up the main argument parser ---
        parser = argparse.ArgumentParser(
            progname,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter)

        parser.add_argument(
            '--file', '-f',
            metavar='<file>',
            help=f'Use file as makefile, default is {__default_source_file}')
        parser.add_argument(
            '--directory', '-C',
            metavar='<directory>',
            help='Change to directory <directory> before reading the makefile.')
        parser.add_argument(
            '--version', '-v',
            action='version',
            version=f"%(prog)s {version}")

        # --- Create subparsers for each discovered target ---
        targetparsers = parser.add_subparsers(
            dest='target',
            metavar='<target>',
            help='Target to execute')

        for arg, info in make_args.items():
            subparse = targetparsers.add_parser(
                arg,
                description=info['full_help'],
                help=info['help'],
                formatter_class=argparse.RawDescriptionHelpFormatter)

            # Add arguments for each parameter of the target function.
            for subarg, subarg_info in info['args'].items():
                add_args = {}
                if "default" not in subarg_info:
                    add_args["required"] = True
                else:
                    add_args["default"] = subarg_info["default"]

                # Handle boolean arguments correctly.
                arg_type = subarg_info["type"]
                if arg_type is bool:
                    # Use a custom string-to-boolean converter.
                    def str2bool(v):
                        val = str(v).lower()
                        if val in ('y', 'yes', 't', 'true', 'on', '1'):
                            return True
                        elif val in ('n', 'no', 'f', 'false', 'off', '0'):
                            return False
                        raise ValueError(f"invalid truth value {val!r}")
                    arg_type = str2bool

                subparse.add_argument(
                    f'--{subarg}',
                    dest=f'sub_{subarg}',
                    metavar=f'<{subarg}>',
                    type=arg_type,
                    **add_args)

        # --- Parse arguments and execute the target ---
        args = parser.parse_args()
        target = args.target or default_arg

        if not target:
            if make_args:
                print("Error: No target specified and no default target found.")
                parser.print_help()
            else:
                print(f"Error: Unable to load makefile '{source_file}'.")
            return 1

        if target not in make_args:
            print(f"Error: Target '{target}' not found in '{source_file}'.")
            return 1

        # Prepare arguments to pass to the target function.
        call_args = {}
        args_vars = vars(args)
        for arg in make_args[target]["args"]:
            arg_key = f'sub_{arg}'
            if arg_key in args_vars and args_vars[arg_key] is not None:
                call_args[arg] = args_vars[arg_key]

        # Call the selected function with its arguments.
        make_args[target]["function"](**call_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
