# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import argparse
import sys
import os
import importlib
from inspect import getmembers, isfunction, getfullargspec
from siliconcompiler._metadata import version
from siliconcompiler.schema import utils


__default_source_file = "make.py"


def __process_file(path):
    if not os.path.exists(path):
        return {}, None, None
    mod_name = 'scmake'
    spec = importlib.util.spec_from_file_location(mod_name, path)
    make = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = make
    syspath = sys.path.copy()
    sys.path.insert(0, os.getcwd())
    spec.loader.exec_module(make)
    sys.path = syspath

    args = {}
    for name, func in getmembers(make, isfunction):
        if name.startswith('_'):
            continue

        # generate doc
        docstring = utils.trim(func.__doc__)
        if not docstring:
            docstring = f"run \"{name}\""
        short_help = docstring.splitlines()[0]

        func_spec = getfullargspec(func)

        func_args = {}
        for arg in func_spec.args:
            arg_type = str
            if arg in func_spec.annotations:
                arg_type = func_spec.annotations[arg]
            func_args[arg] = {
                "type": arg_type
            }

        if func_spec.defaults:
            for arg, defval in zip(reversed(func_spec.args), reversed(func_spec.defaults)):
                func_args[arg]["default"] = defval

                if defval is None:
                    continue

                if type(defval) is not func_args[arg]["type"]:
                    if isinstance(defval, (bool, str, float, int)):
                        func_args[arg]["type"] = type(defval)

        args[name] = {
            "function": func,
            "help": short_help,
            "full_help": docstring,
            "args": func_args
        }

    if args:
        default_arg = list(args.keys())[0]
    else:
        default_arg = None

    default_arg = getattr(make, '__scdefault', default_arg)

    module_help = utils.trim(make.__doc__)

    return args, default_arg, module_help


def main(source_file=None):
    progname = "smake"
    description = f"""-----------------------------------------------------------
SC app that provides an Makefile like interface to python
configuration files. This utility app will analyze a file
"{__default_source_file}" or the file specified with --file to determine
the available targets.

To view the help, use:
    smake --help

    or view the help for a specific target:
    smake --help <target>

To run a target, use:
    smake <target>

    or run a target from a file other than "{__default_source_file}":
    smake --file <file> <target>

    or run a target in a different directory:
    smake --directory <directory> <target>

To run a target with supported arguments, use:
    smake <target> --flow asicflow
-----------------------------------------------------------"""

    # handle source file identification before arg parse
    file_args = None
    if not source_file:
        source_file = __default_source_file
        file_args = ('--file', '-f')
        for file_arg in file_args:
            if file_arg in sys.argv:
                source_file_idx = sys.argv.index(file_arg) + 1
                if source_file_idx < len(sys.argv):
                    source_file = sys.argv[source_file_idx]
                else:
                    source_file = None
                break

    # handle directory identification before arg parse
    source_dir = os.getcwd()
    dir_args = ('--directory', '-C')
    for file_arg in dir_args:
        if file_arg in sys.argv:
            source_dir_idx = sys.argv.index(file_arg) + 1
            if source_dir_idx < len(sys.argv):
                source_dir = sys.argv[source_dir_idx]
            else:
                source_dir = None
            break

    if source_dir:
        if not os.path.isdir(source_dir):
            print(f"Unable to change directory to {source_dir}")
            return 1

        os.chdir(source_dir)

    make_args = {}
    default_arg = None
    module_help = None
    if source_file:
        make_args, default_arg, module_help = __process_file(source_file)

    if module_help:
        description += \
            f"\n\n{module_help}\n\n-----------------------------------------------------------"

    parser = argparse.ArgumentParser(
        progname,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    if file_args:
        parser.add_argument(
            *file_args,
            metavar='<file>',
            help=f'Use file as makefile, default is {__default_source_file}')

    parser.add_argument(
        *dir_args,
        metavar='<directory>',
        help='Change to directory <directory> before reading the makefile.')

    parser.add_argument(
        '--version', '-v',
        action='version',
        version=version)

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

        for subarg, subarg_info in info['args'].items():
            # print(subarg, subarg_info)
            add_args = {}

            if "default" not in subarg_info:
                add_args["required"] = True
            else:
                if type(subarg_info["default"]) is subarg_info["type"]:
                    add_args["default"] = subarg_info["default"]

            if subarg_info["type"] is bool:
                def str2bool(v):
                    # modified from:
                    # https://github.com/pypa/distutils/blob/8993718731b951ee36d08cb784f02aa13542ce15/distutils/util.py
                    val = v.lower()
                    if val in ('y', 'yes', 't', 'true', 'on', '1'):
                        return True
                    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
                        return False
                    else:
                        raise ValueError(f"invalid truth value {val!r}")
                subarg_info["type"] = str2bool

            subparse.add_argument(
                f'--{subarg}',
                dest=f'sub_{subarg}',
                metavar=f'<{subarg}>',
                type=subarg_info["type"],
                **add_args)

    args = parser.parse_args()
    target = args.target
    if not target:
        target = default_arg

    if not os.path.isfile(source_file):
        print(f"Unable to load {source_file}")
        return 1

    call_args = {}
    args_vars = vars(args)
    for arg in make_args[target]["args"]:
        if f'sub_{arg}' in args_vars and args_vars[f'sub_{arg}'] is not None:
            call_args[arg] = args_vars[f'sub_{arg}']
    make_args[target]["function"](**call_args)

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
