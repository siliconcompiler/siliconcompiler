import argparse
import re
import sys

import os.path

from typing import Set

from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, Scope, PerNode
from siliconcompiler.schema.utils import trim
from siliconcompiler import _metadata


class CommandLineSchemaTmp:
    '''
    Class to provide the :meth:`create_cmdline` option to a schema object.

    This class should not be instantiated by itself.

    Examples:
        class NewSchema(BaseSchema, CommandLineSchema):
            creates a new class with the commandline options available
    '''

    ###########################################################################
    def create_cmdline(self,
                       progname,
                       description=None,
                       switchlist=None,
                       additional_args=None,
                       version=None,
                       print_banner=None,
                       input_map_handler=None,
                       preprocess_keys=None,
                       post_process=None,
                       logger=None):
        """Creates a Schema command line interface.

        Exposes parameters in the SC schema as command line switches,
        simplifying creation of SC apps with a restricted set of schema
        parameters exposed at the command line. The order of command
        line switch settings parsed from the command line is as follows:

         1. loglevel, if available in schema
         2. read_manifest([cfg]), if available in schema
         3. read inputs with input_map_handler
         4. all other switches
         5. Run post_process

        The cmdline interface is implemented using the Python argparse package
        and the following use restrictions apply.

        * Help is accessed with the '-h' switch.
        * Arguments that include spaces must be enclosed with double quotes.
        * List parameters are entered individually. (ie. -y libdir1 -y libdir2)
        * For parameters with Boolean types, the switch implies "true".
        * Special characters (such as '-') must be enclosed in double quotes.
        * Compiler compatible switches include: -D, -I, -O{0,1,2,3}
        * Legacy switch formats are supported: +libext+, +incdir+

        Args:
            progname (str): Name of program to be executed.
            description (str): Short program description.
            switchlist (list of str): List of SC parameter switches to expose
                at the command line. By default all SC schema switches are
                available. Parameter switches should be entered based on the
                parameter 'switch' field in the schema. For parameters with
                multiple switches, both will be accepted if any one is included
                in this list.
            input_map (dict of str): Dictionary mapping file extensions to input
                filetypes. This is used to automatically assign positional
                source arguments to ['input', 'fileset', ...] keypaths based on their file
                extension. If None, the CLI will not accept positional source
                arguments.
            additional_args (dict of dict): Dictionary of extra arguments to add
                to the command line parser, with the arguments matching the
                argparse.add_argument() call.
            version (str): Version to report when calling with -version
            print_banner (function): Function callback to print command line banner
            input_map_handler (function): Function callback handle inputs to the input map
            preprocess_keys (function): Function callback to preprocess keys that need to be
                corrected
            post_process (function): Function callback to process arguments before returning

        Returns:
            None if additional_args is not provided, otherwise a dictionary with the
                command line options detected from the additional_args

        Examples:
            >>> schema.create_cmdline(progname='sc-show',switchlist=['-input','-cfg'])
            Creates a command line interface for 'sc-show' app.
            >>> schema.create_cmdline(progname='sc', input_map={'v': ('rtl', 'verilog')})
            All sources ending in .v will be stored in ['input', 'rtl', 'verilog']
            >>> extra = schema.create_cmdline(progname='sc',
                                              additional_args={'-demo': {'action': 'store_true'}})
            Returns extra = {'demo': False/True}
        """

        # Argparse
        parser = argparse.ArgumentParser(prog=progname,
                                         prefix_chars='-+',
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description=description,
                                         allow_abbrev=False)

        # Create empty copy of schema
        schema = type(self)()

        # Track arguments
        argument_map = {}
        arguments = set()

        # Iterate over all keys from an empty schema to add parser arguments
        for keypath in sorted(schema.allkeys()):
            param = schema.get(*keypath, field=None)

            dest, switches = param.add_commandline_arguments(
                parser,
                *keypath,
                switchlist=switchlist)

            if switches:
                argument_map[dest] = (keypath, param)
                arguments.update(switches)

        print_additional_arg_value = {}
        if additional_args:
            # Add additional user specified arguments
            arg_dests = []
            for arg, arg_detail in additional_args.items():
                do_print = True
                if "sc_print" in arg_detail:
                    do_print = arg_detail["sc_print"]
                    del arg_detail["sc_print"]
                argument = parser.add_argument(arg, **arg_detail)
                print_additional_arg_value[argument.dest] = do_print

                arg_dests.append(argument.dest)
                arguments.add(arg)
            # rewrite additional_args with new dest information
            additional_args = arg_dests

        if version:
            parser.add_argument('-version', action='version', version=version)

        # Check if there are invalid switches
        if switchlist:
            for switch in switchlist:
                if switch not in arguments:
                    raise ValueError(f'{switch} is not a valid commandline argument')

        if input_map_handler:
            parser.add_argument('source',
                                nargs='*',
                                help='Input files with filetype inferred by extension')

        # Preprocess sys.argv to enable linux commandline switch formats
        # (gcc, verilator, etc)
        scargs = []

        # Iterate from index 1, otherwise we end up with script name as a
        # 'source' positional argument
        for argument in sys.argv[1:]:
            # Split switches with one character and a number after (O0,O1,O2)
            opt = re.match(r'(\-\w)(\d+)', argument)
            # Split assign switches (-DCFG_ASIC=1)
            assign = re.search(r'(\-\w)(\w+\=\w+)', argument)
            # Split plusargs (+incdir+/path)
            plusarg = re.search(r'(\+\w+\+)(.*)', argument)
            if opt:
                scargs.append(opt.group(1))
                scargs.append(opt.group(2))
            elif plusarg:
                scargs.append(plusarg.group(1))
                scargs.append(plusarg.group(2))
            elif assign:
                scargs.append(assign.group(1))
                scargs.append(assign.group(2))
            else:
                scargs.append(argument)

        # Grab argument from pre-process sysargs
        cmdargs = vars(parser.parse_args(scargs))

        # Set loglevel if set at command line
        do_print_banner = True
        if 'option_loglevel' in cmdargs:
            log_level = cmdargs['option_loglevel']
            if isinstance(log_level, list):
                # if multiple found, pick the first one
                log_level = log_level[0]
            if log_level == 'quiet':
                do_print_banner = False
            if logger:
                logger.setLevel(log_level.split()[-1].upper())

        if print_banner and do_print_banner:
            print_banner()

        extra_params = None
        if additional_args:
            # Grab user specified arguments
            extra_params = {}
            for arg in additional_args:
                if arg in cmdargs:
                    val = cmdargs[arg]
                    if print_additional_arg_value[arg] and val and logger:
                        logger.info(
                            f'Command line argument entered: "{arg}" Value: {val}')
                    extra_params[arg] = val
                    # Remove from cmdargs
                    del cmdargs[arg]

        # Read in all cfg files
        if 'option_cfg' in cmdargs.keys():
            for item in cmdargs['option_cfg']:
                self.read_manifest(item)

        if input_map_handler:
            # Map sources to ['input'] keypath.
            if 'source' in cmdargs:
                input_map_handler(cmdargs['source'])
                # we don't want to handle this in the next loop
                del cmdargs['source']

        # Cycle through all command args and write to manifest
        for dest, vals in sorted(cmdargs.items(), key=lambda d: d[0]):
            keypath, param = argument_map[dest]

            # Turn everything into a list for uniformity
            if not isinstance(vals, list):
                vals = [vals]

            # Cycle through all items
            for item in vals:
                if preprocess_keys:
                    item = preprocess_keys(keypath, item)

                valkeypath, step, index, item = param.parse_commandline_arguments(item, *keypath)

                if logger:
                    msg = f'Command line argument entered: [{",".join(valkeypath)}] Value: {item}'
                    if step is not None:
                        msg += f' step: {step}'
                    if index is not None:
                        msg += f' index: {index}'
                    logger.info(msg)

                # Storing in manifest
                if param.is_list():
                    self.add(*valkeypath, item, step=step, index=index)
                else:
                    self.set(*valkeypath, item, step=step, index=index)

        if post_process:
            extra_params = post_process(cmdargs, extra_params)

        return extra_params


class CommandLineSchema(BaseSchema):
    '''
    Class to provide the :meth:`create_cmdline` option to a schema object.

    This class should not be instantiated by itself.

    Examples:
        class NewSchema(BaseSchema, CommandLineSchema):
            creates a new class with the commandline options available
    '''
    def _add_commandline_argument(self, name, type, help, switch, defvalue=None, **kwargs):
        '''
        Adds a parameter to the commandline definition.

        Args:
            name (str): name of parameter
            type (str): schema type of the parameter
            help (str): help string for this parameter
            defvalue (any): default value for the parameter
        '''
        if isinstance(help, str):
            # grab first line for short help
            help = trim(help)
            shorthelp = help.splitlines()[0].strip()
        else:
            raise TypeError("help must be a string")

        kwargs["scope"] = Scope.GLOBAL
        kwargs["pernode"] = PerNode.NEVER
        kwargs["shorthelp"] = shorthelp
        kwargs["help"] = help
        kwargs["switch"] = switch
        if defvalue is not None:
            kwargs["defvalue"] = defvalue

        EditableSchema(self).insert("cmdarg", name, Parameter(type, **kwargs))

    @classmethod
    def create_cmdline(cls,
                       progname: str = None,
                       description: str = None,
                       switchlist: Set[str] = None,
                       version: str = None,
                       print_banner: bool = True,
                       use_cfg: bool = False,
                       use_sources: bool = True):
        """
        Creates an SC command line interface.

        Exposes parameters in the SC schema as command line switches,
        simplifying creation of SC apps with a restricted set of schema
        parameters exposed at the command line. The order of command
        line switch settings parsed from the command line is as follows:

         1. read_manifest (-cfg), if specified by `use_cfg`
         2. read commandline inputs
         3. all other switches

        The cmdline interface is implemented using the Python argparse package
        and the following use restrictions apply.

        * Help is accessed with the '-h' switch.
        * Arguments that include spaces must be enclosed with double quotes.
        * List parameters are entered individually. (ie. -y libdir1 -y libdir2)
        * For parameters with Boolean types, the switch implies "true".
        * Special characters (such as '-') must be enclosed in double quotes.

        Args:
            progname (str): Name of program to be executed.
            description (str): Short program description.
            switchlist (list of str): List of SC parameter switches to expose
                at the command line. By default all SC schema switches are
                available. Parameter switches should be entered based on the
                parameter 'switch' field in the schema. For parameters with
                multiple switches, both will be accepted if any one is included
                in this list.
            version (str): version of this program.
            print_banner (bool): if True, will print the siliconcompiler banner
            use_cfg (bool): if True, add and parse the -cfg flag
            use_sources (bool): if True, add positional arguments for files

        Returns:
            new project object

        Examples:
            >>> chip.create_cmdline(progname='sc-show',switchlist=['-input','-cfg'])
            Creates a command line interface for 'sc-show' app.

            >>> chip.create_cmdline(progname='sc')
        """

        if progname and os.path.isfile(progname):
            progname = os.path.basename(progname)

        parser = argparse.ArgumentParser(
            prog=progname,
            description=description,
            prefix_chars='-+',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            allow_abbrev=False)

        cfg_file = None
        if use_cfg:
            parser.add_argument(
                '-cfg',
                metavar='<file>',
                help="configuration manifest")

            # Grab config from argv
            try:
                cfg_index = sys.argv.index("-cfg", 1)
                if cfg_index < len(sys.argv):
                    cfg_file = sys.argv[cfg_index + 1]
            except ValueError:
                pass

        if cfg_file:
            schema = cls.from_manifest(filepath=cfg_file)
        else:
            # Create new schema
            schema = cls()

        # Create empty schema for parameter generation
        keyschema = schema.__class__()

        if use_sources:
            # Add commandline key for input files
            for s in (schema, keyschema):
                s._add_commandline_argument("input", "[file]", "input files", None)

        # Get logger if available
        logger = getattr(schema, "logger", None)

        # Track arguments
        argumentmap = {}
        arguments = set()

        # Iterate over all keys from an empty schema to add parser arguments
        for keypath in sorted(keyschema.allkeys()):
            if keypath == ("option", "cfg"):  # TODO: remove this when cfg is removed from schema
                continue

            param = keyschema.get(*keypath, field=None)

            dest, switches = param.add_commandline_arguments(
                parser,
                *keypath,
                switchlist=switchlist)

            if switches:
                argumentmap[dest] = (keypath, param)
                arguments.update(switches)

        # Check if there are invalid switches
        if switchlist:
            switchlist = set(switchlist)
            unsed_switches = switchlist.difference(arguments)
            if unsed_switches:
                raise ValueError(f'{", ".join(unsed_switches)} is/are not a valid '
                                 'commandline arguments')

        prog_version = ""
        if progname:
            prog_version = f"{progname}"
            if version is not None:
                prog_version = f"{prog_version} {version}"
            prog_version += " / "

        parser.add_argument(
            # '-v',
            '-version',
            # '--version',
            action='version',
            version=f"{prog_version}SiliconCompiler {_metadata.version}")

        if use_sources:
            parser.add_argument('source',
                                nargs='*',
                                help='Input files')

        # Preprocess sys.argv to enable linux commandline switch formats
        # (gcc, verilator, etc)
        scargs = []

        # Iterate from index 1, otherwise we end up with script name as a
        # 'source' positional argument
        for argument in sys.argv[1:]:
            # Split switches with one character and a number after (O0,O1,O2)
            opt = re.match(r'(\-\w)(\d+)', argument)
            # Split assign switches (-DCFG_ASIC=1)
            assign = re.search(r'(\-\w)(\w+\=\w+)', argument)
            # Split plusargs (+incdir+/path)
            plusarg = re.search(r'(\+\w+\+)(.*)', argument)
            if opt:
                scargs.append(opt.group(1))
                scargs.append(opt.group(2))
            elif plusarg:
                scargs.append(plusarg.group(1))
                scargs.append(plusarg.group(2))
            elif assign:
                scargs.append(assign.group(1))
                scargs.append(assign.group(2))
            else:
                scargs.append(argument)

        # Grab argument from pre-process sysargs
        cmdargs = vars(parser.parse_args(scargs))

        if print_banner:
            print(_metadata.banner)
            authors = []
            for name in _metadata.authors:
                name = name.split(" ")
                authors.append(f"{name[0][0]}. {' '.join(name[1:])}")
            print("Authors:", ", ".join(authors))
            print("Version:", _metadata.version, "\n")
            print("-" * 80)

        if 'source' in cmdargs:
            if cmdargs['source']:
                schema.set("cmdarg", "input", cmdargs['source'])
            # we don't want to handle this in the next loop
            del cmdargs['source']

        # Cycle through all command args and write to manifest
        for dest, vals in list(sorted(cmdargs.items(), key=lambda d: d[0])):
            if dest not in argumentmap:
                continue

            keypath, param = argumentmap[dest]
            del cmdargs[dest]

            # Turn everything into a list for uniformity
            if not isinstance(vals, list):
                vals = [vals]

            # Cycle through all items
            for item in vals:
                valkeypath, step, index, item = param.parse_commandline_arguments(item, *keypath)

                if logger:
                    msg = f'Command line argument entered: [{",".join(valkeypath)}] Value: {item}'
                    if step is not None:
                        msg += f' step: {step}'
                    if index is not None:
                        msg += f' index: {index}'
                    logger.info(msg)

                # Storing in manifest
                if param.is_list():
                    schema.add(*valkeypath, item, step=step, index=index)
                else:
                    schema.set(*valkeypath, item, step=step, index=index)

        return schema
