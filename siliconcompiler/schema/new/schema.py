# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

import argparse
import copy
import json
import re
import shlex
import sys

from siliconcompiler.schema.new.baseschema import BaseSchema
from siliconcompiler.schema.new.editableschema import EditableSchema
from siliconcompiler.schema.new.safeschema import SafeSchema
from siliconcompiler.schema.new.parameter import Parameter, PerNode

from siliconcompiler.schema.new.schema_cfg import schema_cfg


class Schema(BaseSchema):
    def __init__(self):
        super().__init__()

        self.__history = {}

        schema_cfg(self)

        schema = EditableSchema(self)
        schema.add("library", BaseSchema())
        schema.add("history", BaseSchema())

    def _from_dict(self, manifest, keypath, version=None):
        # find schema version
        schema_version = manifest.get("schemaversion", None)
        if not version and schema_version:
            param = Parameter.from_dict(schema_version, ["schemaversion"], None)
            version = param.get()

        current_verison = self.get("schemaversion")
        if current_verison != version:
            self.logger.warning(f"Mismatch in schema versions: {current_verison} != {version}")

        super()._from_dict(manifest, keypath, version=version)

    def get(self, *keypath, field='value', job=None, step=None, index=None):
        if job is not None:
            job_data = EditableSchema(self).search("history", job)
            return job_data.get(*keypath, field=field, step=step, index=index)
        return super().get(*keypath, field=field, step=step, index=index)


class SchemaTmp(Schema):
    # TMP until cleanup
    GLOBAL_KEY = Parameter.GLOBAL_KEY

    def __init__(self, logger=None):
        super().__init__()

        self.__logger = logger

        self._stop_journal()

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        if super().set(*args, field=field, clobber=clobber, step=step, index=index):
            *keypath, value = args
            self.__record_journal("set", keypath, value=value, field=field, step=step, index=index)
            return True
        return False

    def add(self, *args, field='value', step=None, index=None):
        if super().add(*args, field=field, step=step, index=index):
            *keypath, value = args
            self.__record_journal("add", keypath, value=value, field=field, step=step, index=index)
            return True
        return False

    def unset(self, *keypath, step=None, index=None):
        self.__record_journal("unset", keypath, step=step, index=index)
        super().unset(*keypath, step=step, index=index)

    def remove(self, *keypath):
        self.__record_journal("remove", keypath)
        super().remove(*keypath)

    # TMP needed until clean
    def __record_journal(self, record_type, key, value=None, field=None, step=None, index=None):
        '''
        Record the schema transaction
        '''
        if self.__journal is None:
            return

        self.__journal.append({
            "type": record_type,
            "key": key,
            "value": value,
            "field": field,
            "step": step,
            "index": index
        })

    # TMP needed until clean
    def _import_group(self, group, name, obj):
        if self.valid(group, name):
            self.logger.warning(f'Overwriting existing {group} {name}')
        EditableSchema(self).add(group, name, obj, clobber=True)

    # TMP needed until clean
    def is_empty(self, *keypath):
        return self.get(*keypath, field=None).is_empty()

    # TMP needed until clean
    def has_field(self, *args):
        *keypath, field = args
        return self.get(*keypath, field=field) is not None

    # TMP needed until clean
    def _getvals(self, *keypath):
        return self.get(*keypath, field=None).getvalues()

    # TMP needed until clean
    def _start_journal(self):
        '''
        Start journaling the schema transactions
        '''
        self.__journal = []

    # TMP needed until clean
    def _stop_journal(self):
        '''
        Stop journaling the schema transactions
        '''
        self.__journal = None

    # TMP needed until clean
    def read_journal(self, filename):
        '''
        Reads a manifest and replays the journal
        '''

        with open(filename) as f:
            data = json.load(f)

        self._import_journal(self.from_manifest(cfg=data))

    # TMP needed until clean
    def _import_journal(self, schema):
        '''
        Import the journaled transactions from a different schema
        '''
        if not schema.__journal:
            return

        for action in schema.__journal:
            record_type = action['type']
            keypath = action['key']
            value = action['value']
            field = action['field']
            step = action['step']
            index = action['index']
            try:
                if record_type == 'set':
                    self.set(*keypath, value, field=field, step=step, index=index)
                elif record_type == 'add':
                    self.add(*keypath, value, field=field, step=step, index=index)
                elif record_type == 'unset':
                    self.unset(*keypath, step=step, index=index)
                elif record_type == 'remove':
                    self.remove(*keypath)
                else:
                    raise ValueError(f'Unknown record type {record_type}')
            except Exception as e:
                self.logger.error(f'Exception: {e}')

    # TMP needed until clean
    def _start_record_access(self):
        pass

    # TMP needed until clean
    def _do_record_access(self):
        pass

    # TMP needed until clean
    def _stop_record_access(self):
        pass

    def _from_dict(self, manifest, keypath, version=None):
        if "__journal__" in manifest:
            self.__journal = manifest["__journal__"]
            del manifest["__journal__"]

        super()._from_dict(manifest, keypath, version=version)

    def getdict(self, *keypath, include_default=True):
        manifest = super().getdict(*keypath, include_default=include_default)

        if self.__journal:
            manifest["__journal__"] = copy.deepcopy(self.__journal)

        return manifest

    # TMP needed until clean
    def write_json(self, fout):
        json.dump(self.getdict(), fout, indent=2)

    def write_tcl(self, fout, prefix="", step=None, index=None, template=None):
        from siliconcompiler.schema.new.parameter import escape_val_tcl
        import os.path

        tcl_set_cmds = []
        for key in self.allkeys():
            # print out all non default values
            if 'default' in key:
                continue

            param = self.get(*key, field=None)

            # create a TCL dict
            keystr = ' '.join([escape_val_tcl(keypart, 'str') for keypart in key])

            valstr = param.gettcl(step=step, index=index)
            if valstr is None:
                continue

            # Ensure empty values get something
            if valstr == '':
                valstr = '{}'

            tcl_set_cmds.append(f"{prefix} {keystr} {valstr}")

        if template:
            fout.write(template.render(manifest_dict='\n'.join(tcl_set_cmds),
                                       scroot=os.path.abspath(
                                              os.path.join(os.path.dirname(__file__), '..')),
                                       record_access=self._do_record_access(),
                                       record_access_id="123456"))
        else:
            for cmd in tcl_set_cmds:
                fout.write(cmd + '\n')
            fout.write('\n')

    @property
    def logger(self):
        return self.__logger or super().logger

    ###########################################################################
    def create_cmdline(self,
                       progname,
                       description=None,
                       switchlist=None,
                       input_map=None,
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

        if not logger:
            logger = self.logger

        # Argparse
        parser = argparse.ArgumentParser(prog=progname,
                                         prefix_chars='-+',
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description=description,
                                         allow_abbrev=False)

        # Get a new schema, in case values have already been set
        schema_class = type(self)
        schema = schema_class(logger=self.logger)

        # Iterate over all keys from an empty schema to add parser arguments
        used_switches = set()
        for keypath in schema.allkeys():
            # Fetch fields from leaf cell
            helpstr = schema.get(*keypath, field='shorthelp')
            typestr = schema.get(*keypath, field='type')
            pernodestr = schema.get(*keypath, field='pernode')

            # argparse 'dest' must be a string, so join keypath with commas
            dest = '_'.join(keypath)

            switchstrs, metavar = self.__get_switches(schema, *keypath)

            # Three switch types (bool, list, scalar)
            if switchlist is None or any(switch in switchlist for switch in switchstrs):
                used_switches.update(switchstrs)
                if typestr == 'bool':
                    # Boolean type arguments
                    if pernodestr.is_never():
                        parser.add_argument(*switchstrs,
                                            nargs='?',
                                            metavar=metavar,
                                            dest=dest,
                                            const='true',
                                            help=helpstr,
                                            default=argparse.SUPPRESS)
                    else:
                        parser.add_argument(*switchstrs,
                                            metavar=metavar,
                                            nargs='?',
                                            dest=dest,
                                            action='append',
                                            help=helpstr,
                                            default=argparse.SUPPRESS)
                elif '[' in typestr or not pernodestr.is_never():
                    # list type arguments
                    parser.add_argument(*switchstrs,
                                        metavar=metavar,
                                        dest=dest,
                                        action='append',
                                        help=helpstr,
                                        default=argparse.SUPPRESS)
                else:
                    # all the rest
                    parser.add_argument(*switchstrs,
                                        metavar=metavar,
                                        dest=dest,
                                        help=helpstr,
                                        default=argparse.SUPPRESS)

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
                used_switches.add(arg)
            # rewrite additional_args with new dest information
            additional_args = arg_dests

        if version:
            parser.add_argument('-version', action='version', version=version)

        # Check if there are invalid switches
        if switchlist:
            for switch in switchlist:
                if switch not in used_switches:
                    raise ValueError(f'{switch} is not a valid commandline argument')

        if input_map is not None and input_map_handler:
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
        if 'option_loglevel' in cmdargs.keys():
            log_level = cmdargs['option_loglevel']
            if isinstance(log_level, list):
                # if multiple found, pick the first one
                log_level = log_level[0]
            if log_level == 'quiet':
                do_print_banner = False
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
                    if print_additional_arg_value[arg] and val:
                        msg = f'Command line argument entered: "{arg}" Value: {val}'
                        self.logger.info(msg)
                    extra_params[arg] = val
                    # Remove from cmdargs
                    del cmdargs[arg]

        # Read in all cfg files
        if 'option_cfg' in cmdargs.keys():
            for item in cmdargs['option_cfg']:
                self.read_manifest(item, clobber=True, clear=True, allow_missing_keys=True)

        if input_map_handler:
            # Map sources to ['input'] keypath.
            if 'source' in cmdargs:
                input_map_handler(cmdargs['source'])
                # we don't want to handle this in the next loop
                del cmdargs['source']

        # Cycle through all command args and write to manifest
        for dest, vals in cmdargs.items():
            keypath = dest.split('_')

            # Turn everything into a list for uniformity
            if not isinstance(vals, list):
                vals = [vals]

            # Cycle through all items
            for item in vals:
                if item is None:
                    # nargs=? leaves a None for booleans
                    item = ''

                if preprocess_keys:
                    item = preprocess_keys(keypath, item)

                num_free_keys = keypath.count('default')

                switches, metavar = self.__get_switches(schema, *keypath)
                switchstr = '/'.join(switches)

                if len(item.split(' ')) < num_free_keys + 1:
                    # Error out if value provided doesn't have enough words to
                    # fill in 'default' keys.
                    raise ValueError(f'Invalid value {item} for switch {switchstr}. '
                                     f'Expected format {metavar}.')

                # We replace 'default' in keypath with first N words in provided
                # value.
                *free_keys, remainder = item.split(' ', num_free_keys)
                args = [free_keys.pop(0) if key == 'default' else key for key in keypath]

                # Remainder is the value we want to set, possibly with a step/index value beforehand
                sctype = self.get(*keypath, field='type')
                pernode = self.get(*keypath, field='pernode')
                step, index = None, None
                if pernode == PerNode.REQUIRED:
                    try:
                        step, index, val = remainder.split(' ', 2)
                    except ValueError:
                        self.logger.error(f"Invalid value '{item}' for switch {switchstr}. "
                                          "Requires step and index before final value.")
                elif pernode == PerNode.OPTIONAL:
                    # Split on spaces, preserving items that are grouped in quotes
                    items = shlex.split(remainder)
                    if len(items) > 3:
                        self.logger.error(f"Invalid value '{item}'' for switch {switchstr}. "
                                          "Too many arguments, please wrap multiline "
                                          "strings in quotes.")
                        continue
                    if sctype == 'bool':
                        if len(items) == 3:
                            step, index, val = items
                        elif len(items) == 2:
                            step, val = items
                            if val != 'true' and val != 'false':
                                index = val
                                val = True
                        elif len(items) == 1:
                            val, = items
                            if val != 'true' and val != 'false':
                                step = val
                                val = True
                        else:
                            val = True
                    else:
                        if len(items) == 3:
                            step, index, val = items
                        elif len(items) == 2:
                            step, val = items
                        else:
                            val, = items
                else:
                    val = remainder

                msg = f'Command line argument entered: {args} Value: {val}'
                if step is not None:
                    msg += f' Step: {step}'
                if index is not None:
                    msg += f' Index: {index}'
                self.logger.info(msg)

                # Storing in manifest
                typestr = schema.get(*keypath, field='type')
                if typestr.startswith('['):
                    if self.valid(*args):
                        self.add(*args, val, step=step, index=index)
                    else:
                        self.set(*args, val, step=step, index=index, clobber=True)
                else:
                    self.set(*args, val, step=step, index=index, clobber=True)

        if post_process:
            extra_params = post_process(cmdargs, extra_params)

        return extra_params

    def __get_switches(self, schema, *keypath):
        '''Helper function for parsing switches and metavars for a keypath.'''
        # Switch field fully describes switch format
        switch = schema.get(*keypath, field='switch')

        if switch is None:
            switches = []
        elif isinstance(switch, list):
            switches = switch
        else:
            switches = [switch]
        switchstrs = []

        # parse out switch from metavar
        # TODO: should we validate that metavar matches for each switch?
        for switch in switches:
            switchmatch = re.match(r'(-[\w_]+)\s+(.*)', switch)
            gccmatch = re.match(r'(-[\w_]+)(.*)', switch)
            plusmatch = re.match(r'(\+[\w_\+]+)(.*)', switch)

            if switchmatch:
                switchstr = switchmatch.group(1)
                metavar = switchmatch.group(2)
            elif gccmatch:
                switchstr = gccmatch.group(1)
                metavar = gccmatch.group(2)
            elif plusmatch:
                switchstr = plusmatch.group(1)
                metavar = plusmatch.group(2)
            switchstrs.append(switchstr)

        return switchstrs, metavar

    def read_manifest(self, filename, clear=True, clobber=True, allow_missing_keys=True):
        super().read_manifest(filename)

    def record_history(self):
        job = self.get("option", "jobname")
        EditableSchema(self).add("history", job, self.copy(), clobber=True)


if __name__ == "__main__":
    schema = Schema()
    schema.set("pdk", "sky", "node", "5")
    schema.write_manifest("test.json")

    # safe = SafeSchema.from_manifest(filepath="test.json")
    safe = SafeSchema.from_manifest(cfg=schema.getdict())
    # safe.unlock()
    # safe.set('option', 'var', 'blah', 'blah')
    # safe.lock()
    # safe.set('option', 'var', 'blah', 'blah')
    safe.write_manifest("test2.json")
