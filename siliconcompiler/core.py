# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import tarfile
import os
import pathlib
import sys
import gzip
import re
import logging
import hashlib
import shutil
import importlib
import inspect
import textwrap
import math
import pkgutil
import graphviz
import codecs
from siliconcompiler.remote import client
from siliconcompiler.schema import Schema, SCHEMA_VERSION
from siliconcompiler import utils
from siliconcompiler import units
from siliconcompiler import _metadata
from siliconcompiler import NodeStatus, SiliconCompilerError
from siliconcompiler.report import _show_summary_table
from siliconcompiler.report import _generate_summary_image, _open_summary_image
from siliconcompiler.report import _generate_html_report, _open_html_report
from siliconcompiler.report import Dashboard
from siliconcompiler import package as sc_package
from siliconcompiler import sc_open
import glob
from siliconcompiler.scheduler import run as sc_runner
from siliconcompiler.flowgraph import _get_flowgraph_nodes, _get_flowgraph_node_inputs, \
    _check_execution_nodes_inputs, _get_execution_entry_nodes, _unreachable_steps_to_execute, \
    _get_execution_exit_nodes, _nodes_to_execute, _get_pruned_node_inputs, \
    _get_flowgraph_exit_nodes, gather_resume_failed_nodes, get_executed_nodes, \
    _get_flowgraph_execution_order
from siliconcompiler.tools._common import input_file_node_name


class Chip:
    """Object for configuring and executing hardware design flows.

    This is the main object used for configuration, data, and
    execution within the SiliconCompiler platform.

    Args:
        design (string): Name of the top level chip design module.

    Examples:
        >>> siliconcompiler.Chip(design="top")
        Creates a chip object with name "top".
    """

    ###########################################################################
    def __init__(self, design, loglevel=None):
        # version numbers
        self.scversion = _metadata.version
        self.schemaversion = SCHEMA_VERSION

        # Local variables
        self.scroot = os.path.dirname(os.path.abspath(__file__))
        self._error = False
        try:
            self.cwd = os.getcwd()
        except FileNotFoundError:
            self.error("""SiliconCompiler must be run from a directory that exists.
If you are sure that your working directory is valid, try running `cd $(pwd)`.""", fatal=True)

        # Initialize custom error handling for codecs. This has to be called
        # by each spawned (as opposed to forked) subprocess
        self._init_codecs()

        self._init_logger()

        self.schema = Schema(logger=self.logger)

        self.register_package_source('siliconcompiler',
                                     'python://siliconcompiler')

        # Cache of python modules
        self.modules = {}

        # Cache of python packages loaded
        self._packages = {}

        # Cache of file hashes
        self.__hashes = {}

        # Controls whether find_files returns an abspath or relative to this
        # this is primarily used when generating standalone testcases
        self._relative_path = None

        self.set('design', design)
        if loglevel:
            self.set('option', 'loglevel', loglevel)

        self._loaded_modules = {
            'flows': [],
            'pdks': [],
            'fpgas': [],
            'libs': [],
            'checklists': []
        }

    ###########################################################################
    @property
    def design(self):
        '''Design name of chip object.

        This is an immutable property.'''
        return self.get('design')

    ###########################################################################
    def top(self):
        '''Gets the name of the design's entrypoint for compilation and
        simulation.

        This method should be used to name input and output files in tool
        drivers, rather than relying on chip.get('design') directly.

        Returns :keypath:`option, entrypoint` if it has been set, otherwise
        :keypath:`design`.
        '''
        entrypoint = self.get('option', 'entrypoint')
        if not entrypoint:
            return self.design
        return entrypoint

    ###########################################################################
    def _load_module(self, module_name, raise_error=False):
        if module_name in self.modules:
            return self.modules[module_name]

        try:
            self.modules[module_name] = importlib.import_module(module_name)
            return self.modules[module_name]
        except Exception as e:
            if raise_error:
                raise e

        return None

    ###########################################################################
    def _get_loaded_modules(self):
        return self.modules

    ###########################################################################
    def _get_tool_task(self, step, index, flow=None):
        '''
        Helper function to get the name of the tool and task associated with a given step/index.
        '''
        if not flow:
            flow = self.get('option', 'flow')

        tool = self.get('flowgraph', flow, step, index, 'tool')
        task = self.get('flowgraph', flow, step, index, 'task')
        return tool, task

    def _get_task(self, step, index, flow=None):
        '''
        Helper function to get the name of the task associated with a given step/index.
        '''
        _, task = self._get_tool_task(step, index, flow=flow)
        return task

    def _get_tool_module(self, step, index, flow=None, error=True):
        if not flow:
            flow = self.get('option', 'flow')

        tool, _ = self._get_tool_task(step, index, flow=flow)

        taskmodule = self.get('flowgraph', flow, step, index, 'taskmodule')
        module_path = taskmodule.split('.')

        tool_module_base = module_path[0:-1]

        module = None
        tool_module_names = ['.'.join([*tool_module_base, tool]), '.'.join(tool_module_base)]
        for tool_module in tool_module_names:
            if module:
                break

            module = self._load_module(tool_module)

        if error and not module:
            self.error(f'Unable to load {", ".join(tool_module_names)} for {tool}', fatal=True)
        else:
            return module

    def _get_task_module(self, step, index, flow=None, error=True):
        if not flow:
            flow = self.get('option', 'flow')

        taskmodule = self.get('flowgraph', flow, step, index, 'taskmodule')

        module = self._load_module(taskmodule)

        if error and not module:
            tool, task = self._get_tool_task(step, index, flow=flow)
            self.error(f'Unable to load {taskmodule} for {tool}/{task}', fatal=True)
        else:
            return module

    def _get_tool_tasks(self, tool):
        tool_dir = os.path.dirname(tool.__file__)
        tool_base_module = tool.__name__.split('.')[0:-1]
        tool_name = tool.__name__.split('.')[-1]

        task_candidates = []
        for task_mod in pkgutil.iter_modules([tool_dir]):
            if task_mod.name == tool_name:
                continue
            task_candidates.append(task_mod.name)

        tasks = []
        for task in sorted(task_candidates):
            task_module = '.'.join([*tool_base_module, task])
            if getattr(self._load_module(task_module), 'setup', None):
                tasks.append(task)

        return tasks

    def _add_file_logger(self, filename):
        # Add a file handler for logging
        logformat = self.logger.handlers[0].formatter

        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(logformat)

        self.logger.addHandler(file_handler)

    ###########################################################################
    def _init_logger(self, step=None, index=None, in_run=False):

        # Check if the logger exists and create
        if not hasattr(self, 'logger') or not self.logger:
            self.logger = logging.getLogger(f'sc_{id(self)}')

        self.logger.propagate = False

        loglevel = 'INFO'
        if hasattr(self, 'schema'):
            loglevel = self.schema.get('option', 'loglevel', step=step, index=index)
        else:
            in_run = False

        log_format = ['%(levelname)-7s']
        if loglevel == 'DEBUG':
            log_format.append('%(funcName)-10s')
            log_format.append('%(lineno)-4s')

        if in_run:
            # Figure out how wide to make step and index fields
            max_step_len = 1
            max_index_len = 1
            nodes_to_run = _get_flowgraph_nodes(self, flow=self.get('option', 'flow'))
            if self.get('option', 'remote'):
                nodes_to_run.append((client.remote_step_name, '0'))
            for future_step, future_index in nodes_to_run:
                max_step_len = max(len(future_step), max_step_len)
                max_index_len = max(len(future_index), max_index_len)

            jobname = self.get('option', 'jobname')

            if step is None:
                step = '-' * max(max_step_len // 4, 1)
            if index is None:
                index = '-' * max(max_index_len // 4, 1)

            log_format.append(jobname)
            log_format.append(f'{step: <{max_step_len}}')
            log_format.append(f'{index: >{max_index_len}}')

        log_format.append('%(message)s')
        logformat = '| ' + ' | '.join(log_format)

        if not self.logger.hasHandlers():
            stream_handler = logging.StreamHandler(stream=sys.stdout)
            self.logger.addHandler(stream_handler)

        for handler in self.logger.handlers:
            formatter = logging.Formatter(logformat)
            handler.setFormatter(formatter)

        self.logger.setLevel(loglevel)

    ###########################################################################
    def _init_codecs(self):
        # Custom error handlers used to provide warnings when invalid characters
        # are encountered in a file for a given encoding. The names
        # 'replace_with_warning' and 'ignore_with_warning' are supplied to
        # open() via the 'errors' kwarg.

        # Warning message/behavior for invalid characters while running tool
        def display_error_handler(e):
            self.logger.warning('Invalid character in tool output, displaying as �')
            return codecs.replace_errors(e)
        codecs.register_error('replace_with_warning', display_error_handler)

        # Warning message/behavior for invalid characters while processing log
        def log_error_handler(e):
            self.logger.warning('Ignoring invalid character found while reading log')
            return codecs.ignore_errors(e)
        codecs.register_error('ignore_with_warning', log_error_handler)

    ###########################################################################
    def create_cmdline(self,
                       progname=None,
                       description=None,
                       switchlist=None,
                       input_map=None,
                       additional_args=None):
        """Creates an SC command line interface.

        Exposes parameters in the SC schema as command line switches,
        simplifying creation of SC apps with a restricted set of schema
        parameters exposed at the command line. The order of command
        line switch settings parsed from the command line is as follows:

         1. loglevel
         2. read_manifest([cfg])
         3. read compiler inputs
         4. all other switches
         5. load_target('target')

        The cmdline interface is implemented using the Python argparse package
        and the following use restrictions apply.

        * Help is accessed with the '-h' switch.
        * Arguments that include spaces must be enclosed with double quotes.
        * List parameters are entered individually. (ie. -y libdir1 -y libdir2)
        * For parameters with Boolean types, the switch implies "true".
        * Special characters (such as '-') must be enclosed in double quotes.
        * Compiler compatible switches include: -D, -I, -O{0,1,2,3}
        * Verilog legacy switch formats are supported: +libext+, +incdir+

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

        Returns:
            None if additional_args is not provided, otherwise a dictionary with the
                command line options detected from the additional_args

        Examples:
            >>> chip.create_cmdline(progname='sc-show',switchlist=['-input','-cfg'])
            Creates a command line interface for 'sc-show' app.

            >>> chip.create_cmdline(progname='sc', input_map={'v': ('rtl', 'verilog')})
            All sources ending in .v will be stored in ['input', 'rtl', 'verilog']

            >>> extra = chip.create_cmdline(progname='sc',
                                            additional_args={'-demo': {'action': 'store_true'}})
            Returns extra = {'demo': False/True}
        """

        def print_banner():
            print(_metadata.banner)
            print("Authors:", ", ".join(_metadata.authors))
            print("Version:", _metadata.version, "\n")
            print("-" * 80)

        def input_map_handler(sources):
            for source in sources:
                self.input(source, iomap=input_map)

        def preprocess_keys(keypath, item):
            if tuple(keypath) == ('option', 'optmode') and not item.startswith('O'):
                return 'O' + item
            return item

        def post_process(cmdargs):
            # Read in target if set
            if 'option_target' in cmdargs:
                # running target command
                self.load_target(cmdargs['option_target'])

        if not progname:
            progname = self.design

        try:
            return self.schema.create_cmdline(
                progname=progname,
                description=description,
                switchlist=switchlist,
                input_map=input_map,
                additional_args=additional_args,
                version=_metadata.version,
                print_banner=print_banner,
                input_map_handler=input_map_handler,
                preprocess_keys=preprocess_keys,
                post_process=post_process,
                logger=self.logger)
        except ValueError as e:
            self.error(f'{e}', fatal=True)

    def register_package_source(self, name, path, ref=None, clobber=True):
        """
        Registers a package by its name with the source path and reference

        Registered package sources are stored in the package section of the schema.

        Args:
            name (str): Package name
            path (str): Path to the sources, can be file, git url, archive url
            ref (str): Reference of the sources, can be commitid, branch name, tag

        Examples:
            >>> chip.register_package_source('siliconcompiler_data',
                    'git+https://github.com/siliconcompiler/siliconcompiler',
                    'dependency-caching-rebase')
        """

        preset_path = self.get('package', 'source', name, 'path')
        preset_ref = self.get('package', 'source', name, 'ref')
        if preset_path and preset_path != path or preset_ref and preset_ref != ref:
            self.logger.warning(f'The data source {name} already exists.')
            self.logger.warning(f'Overwriting path {preset_path} with {path}.')
            self.logger.warning(f'Overwriting ref {preset_ref} with {ref}.')
        self.set('package', 'source', name, 'path', path, clobber=clobber)
        if ref:
            self.set('package', 'source', name, 'ref', ref, clobber=clobber)

    ##########################################################################
    def load_target(self, module, **kwargs):
        """
        Loads a target module and runs the setup() function.

        The function searches the installed Python packages for <name> and
        siliconcompiler.targets.<name> and runs the setup function in that module
        if found.

        Args:
            module (str or module): Module name
            **kwargs (str): Options to pass along to the target

        Examples:
            >>> chip.load_target('freepdk45_demo', syn_np=5)
            Loads the 'freepdk45_demo' target with 5 parallel synthesis tasks
        """

        if not inspect.ismodule(module):
            # Search order "{name}", and "siliconcompiler.targets.{name}"
            modules = []
            for mod_name in [module, f'siliconcompiler.targets.{module}']:
                mod = self._load_module(mod_name)
                if mod:
                    modules.append(mod)

            if len(modules) == 0:
                self.error(f'Could not find target {module}', fatal=True)
        else:
            modules = [module]

        # Check for setup in modules
        load_function = None
        for mod in modules:
            load_function = getattr(mod, 'setup', None)
            if load_function:
                module_name = mod.__name__
                break

        if not load_function:
            self.error(f'Could not find setup function for {module} target', fatal=True)

        try:
            load_function(self, **kwargs)
        except Exception as e:
            self.logger.error(f'Failed to load target {module}')
            raise e

        # Record target
        self.set('option', 'target', module_name)

    ##########################################################################
    def use(self, module, **kwargs):
        '''
        Loads a SiliconCompiler module into the current chip object.

        The behavior of this function is described in the table below

        .. list-table:: Use behavior
           :header-rows: 1

           * - Input type
             - Action
           * - Module with setup function
             - Call `setup()` and import returned objects
           * - Chip
             - Import as a library
           * - Library
             - Import as a library
           * - PDK
             - Import as a pdk
           * - FPGA
             - Import as a fpga
           * - Flow
             - Import as a flow
           * - Checklist
             - Import as a checklist
        '''

        # Load supported types here to avoid cyclic import
        from siliconcompiler import PDK
        from siliconcompiler import FPGA
        from siliconcompiler import Flow
        from siliconcompiler import Library
        from siliconcompiler import Checklist

        setup_func = getattr(module, 'setup', None)
        if (setup_func):
            # Call the module setup function.
            try:
                use_modules = setup_func(self, **kwargs)
            except Exception as e:
                self.logger.error(f'Unable to run setup() for {module.__name__}')
                raise e
        else:
            # Import directly
            use_modules = module

        # Make it a list for consistency
        if not isinstance(use_modules, list):
            use_modules = [use_modules]

        for use_module in use_modules:
            if isinstance(use_module, PDK):
                self._loaded_modules['pdks'].append(use_module.design)
                self._use_import('pdk', use_module)

            elif isinstance(use_module, FPGA):
                self._loaded_modules['fpgas'].append(use_module.design)
                self._use_import('fpga', use_module)

            elif isinstance(use_module, Flow):
                self._loaded_modules['flows'].append(use_module.design)
                self._use_import('flowgraph', use_module)

            elif isinstance(use_module, Checklist):
                self._loaded_modules['checklists'].append(use_module.design)
                self._use_import('checklist', use_module)

            elif isinstance(use_module, (Library, Chip)):
                self._loaded_modules['libs'].append(use_module.design)
                self._import_library(use_module.design, use_module.schema.cfg)

            else:
                module_name = module.__name__
                class_name = use_module.__class__.__name__
                raise ValueError(f"{module_name} returned an object with an "
                                 f"unsupported type: {class_name}")

    def __import_data_sources(self, cfg):
        if 'package' not in cfg or 'source' not in cfg['package']:
            return

        for source, config in cfg['package']['source'].items():
            if source == 'default':
                continue

            if 'path' not in config or \
               Schema.GLOBAL_KEY not in config['path']['node'] or \
               Schema.GLOBAL_KEY not in config['path']['node'][Schema.GLOBAL_KEY]:
                continue

            path = config['path']['node'][Schema.GLOBAL_KEY][Schema.GLOBAL_KEY]['value']

            ref = None
            if 'ref' in config and \
               Schema.GLOBAL_KEY in config['ref']['node'] and \
               Schema.GLOBAL_KEY in config['ref']['node'][Schema.GLOBAL_KEY]:
                ref = config['ref']['node'][Schema.GLOBAL_KEY][Schema.GLOBAL_KEY]['value']

            self.register_package_source(
                name=source,
                path=path,
                ref=ref)

    def _use_import(self, group, module):
        '''
        Imports the module into the schema

        Args:
            group (str): Top group to copy information into
            module (class): Chip object to import
        '''

        importname = module.design

        src_cfg = self.schema.cfg[group]

        if importname in src_cfg:
            self.logger.warning(f'Overwriting existing {group} {importname}')
            del src_cfg[importname]

        # Copy
        src_cfg[importname] = module.getdict(group, importname)
        self.__import_data_sources(module.schema.cfg)

    ###########################################################################
    def help(self, *keypath):
        """
        Returns a schema parameter description.

        Args:
            *keypath(str): Keypath to parameter.

        Returns:
            A formatted multi-line help paragraph for the parameter provided.

        Examples:
            >>> print(chip.help('asic','diearea'))
            Displays help information about the 'asic, diearea' parameter

        """

        self.logger.debug('Fetching help for %s', keypath)

        # Fetch Values

        description = self.get(*keypath, field='shorthelp')
        typestr = self.get(*keypath, field='type')
        switchstr = str(self.get(*keypath, field='switch'))
        defstr = str(self.schema.get_default(*keypath))
        requirement = str(self.get(*keypath, field='require'))
        helpstr = self.get(*keypath, field='help')
        example = self.get(*keypath, field='example')

        examplestr = ("\nExamples:    " + example[0] + ''.join(
                      ["\n             " + ex for ex in example[1:]]))

        # Removing multiple spaces and newlines
        helpstr = helpstr.rstrip()
        helpstr = helpstr.replace("\n", "")
        helpstr = ' '.join(helpstr.split())

        for idx, item in enumerate(example):
            example[idx] = ' '.join(item.split())
            example[idx] = example[idx].replace(", ", ",")

        # Wrap text
        para = textwrap.TextWrapper(width=60)
        para_list = para.wrap(text=helpstr)

        # Full Doc String
        fullstr = "-" * 80
        fullstr += "\nDescription: " + description
        fullstr += "\nSwitch:      " + switchstr
        fullstr += "\nType:        " + typestr
        fullstr += "\nRequirement: " + requirement
        fullstr += "\nDefault:     " + defstr
        fullstr += examplestr
        fullstr += "\nHelp:        " + para_list[0] + "\n"
        for line in para_list[1:]:
            fullstr = fullstr + " " * 13 + line.lstrip() + "\n"

        return fullstr

    ###########################################################################
    def valid(self, *keypath, default_valid=False, job=None):
        """
        Checks validity of a keypath.

        Checks the validity of a parameter keypath and returns True if the
        keypath is valid and False if invalid.

        Args:
            default_valid (bool): Whether to consider "default" in valid
            keypaths as a wildcard. Defaults to False.
            job (str): Jobname to use for dictionary access in place of the
                current active jobname.

        Returns:
            Boolean indicating validity of keypath.

        Examples:
            >>> check = chip.valid('design')
            Returns True.
            >>> check = chip.valid('blah')
            Returns False.
            >>> check = chip.valid('metric', 'foo', '0', 'tasktime', default_valid=True)
            Returns True, even if "foo" and "0" aren't in current configuration.
        """
        return self.schema.valid(*keypath, default_valid=default_valid, job=job)

    ###########################################################################
    def get(self, *keypath, field='value', job=None, step=None, index=None):
        """
        Returns a schema parameter field.

        Returns a schema parameter field based on the keypath provided in the
        ``*keypath``. See the :ref:`Schema Reference Manual<SiliconCompiler
        Schema>` for documentation of all supported keypaths. The returned type
        is consistent with the type field of the parameter. Fetching parameters
        with empty or undefined value files returns None for scalar types and []
        (empty list) for list types.  Accessing a non-existent keypath produces
        a logger error message and raises the Chip object error flag.

        Args:
            keypath(list str): Variable length schema key list.
            field(str): Parameter field to fetch.
            job (str): Jobname to use for dictionary access in place of the
                current active jobname.
            step (str): Step name to access for parameters that may be specified
                on a per-node basis.
            index (str): Index name to access for parameters that may be specified
                on a per-node basis.

        Returns:
            Value found for the keypath and field provided.

        Examples:
            >>> foundry = chip.get('pdk', 'foundry')
            Returns the name of the foundry from the PDK.

        """
        self.logger.debug(f"Reading from {keypath}. Field = '{field}'")

        try:
            strict = self.schema.get('option', 'strict')
            if field == 'value' and strict:
                pernode = self.schema.get(*keypath, field='pernode')
                if pernode == 'optional' and \
                   (step is None or index is None) and \
                   (Schema.GLOBAL_KEY not in (step, index)):  # allow explicit access to global
                    self.error(
                        f"Invalid args to get() of keypath {keypath}: step and "
                        "index are required for reading from this parameter "
                        "while ['option', 'strict'] is True."
                    )
                    return None

            return self.schema.get(*keypath, field=field, job=job, step=step, index=index)
        except (ValueError, TypeError) as e:
            self.error(str(e))
            return None

    ###########################################################################
    def getkeys(self, *keypath, job=None):
        """
        Returns a list of schema dictionary keys.

        Searches the schema for the keypath provided and returns a list of
        keys found, excluding the generic 'default' key. Accessing a
        non-existent keypath produces a logger error message and raises the
        Chip object error flag.

        Args:
            keypath (list str): Variable length ordered schema key list
            job (str): Jobname to use for dictionary access in place of the
                current active jobname.

        Returns:
            List of keys found for the keypath provided.

        Examples:
            >>> keylist = chip.getkeys('pdk')
            Returns all keys for the 'pdk' keypath.
        """
        if len(keypath) > 0:
            self.logger.debug(f'Getting schema parameter keys for {keypath}')
        else:
            self.logger.debug('Getting all schema parameter keys.')

        try:
            return self.schema.getkeys(*keypath, job=job)
        except (ValueError, TypeError) as e:
            self.error(str(e))
            return None

    ###########################################################################
    def allkeys(self, *keypath_prefix):
        '''Returns all keypaths in the schema as a list of lists.

        Arg:
            keypath_prefix (list str): Keypath prefix to search under. The
                returned keypaths do not include the prefix.
        '''
        return self.schema.allkeys(*keypath_prefix)

    ###########################################################################
    def getdict(self, *keypath):
        """
        Returns a schema dictionary.

        Searches the schema for the keypath provided and returns a complete
        dictionary. Accessing a non-existent keypath produces a logger error
        message and raises the Chip object error flag.

        Args:
            keypath(list str): Variable length ordered schema key list

        Returns:
            A schema dictionary

        Examples:
            >>> pdk = chip.getdict('pdk')
            Returns the complete dictionary found for the keypath 'pdk'
        """
        self.logger.debug(f'Getting cfg for: {keypath}')

        try:
            return self.schema.getdict(*keypath)
        except (ValueError, TypeError) as e:
            self.error(str(e))
            return None

    ###########################################################################
    def __add_set_package(self, keypath, value, package, step, index, clobber, add):
        sc_type = self.get(*keypath, field='type')
        if 'file' in sc_type or 'dir' in sc_type:
            value_list = isinstance(value, (list, tuple))
            package_list = isinstance(package, (list, tuple))
            if value_list != package_list:
                if value_list:
                    package = len(value) * [package]
                else:
                    raise ValueError()

            if add:
                self.schema.add(*keypath, package, field='package',
                                step=step, index=index)
            else:
                self.schema.set(*keypath, package, field='package',
                                step=step, index=index, clobber=clobber)

    ###########################################################################
    def set(self, *args, field='value', clobber=True, step=None, index=None, package=None):
        '''
        Sets a schema parameter field.

        Sets a schema parameter field based on the keypath and value provided in
        the ``*args``. See the :ref:`Schema Reference Manual<SiliconCompiler
        Schema>` for documentation of all supported keypaths. New schema
        dictionaries are automatically created for keypaths that overlap with
        'default' dictionaries. The write action is ignored if the parameter
        value is non-empty and the clobber option is set to False.

        The value provided must agree with the dictionary parameter 'type'.
        Accessing a non-existent keypath or providing a value that disagrees
        with the parameter type produces a logger error message and raises the
        Chip object error flag.

        Args:
            args (list): Parameter keypath followed by a value to set.
            field (str): Parameter field to set.
            clobber (bool): Existing value is overwritten if True.
            step (str): Step name to set for parameters that may be specified
                on a per-node basis.
            index (str): Index name to set for parameters that may be specified
                on a per-node basis.
            package (str): Package that this file/dir depends on. Available packages
                are listed in the package source section of the schema.

        Examples:
            >>> chip.set('design', 'top')
            Sets the name of the design to 'top'
        '''
        keypath = args[:-1]
        value = args[-1]
        self.logger.debug(f'Setting {keypath} to {value}')

        # Special case to ensure loglevel is updated ASAP
        if keypath == ['option', 'loglevel'] and field == 'value' and \
           step == self.get('arg', 'step') and index == self.get('arg', 'index'):
            self.logger.setLevel(value)

        try:
            value_success = self.schema.set(*keypath, value, field=field, clobber=clobber,
                                            step=step, index=index)
            if field == 'value' and value_success:
                self.__add_set_package(keypath, value, package, step, index, True, False)

        except (ValueError, TypeError) as e:
            self.error(e)

    ###########################################################################
    def unset(self, *keypath, step=None, index=None):
        '''
        Unsets a schema parameter.

        This method effectively undoes any previous calls to ``set()`` made to
        the given keypath and step/index. For parameters with required or no
        per-node values, unsetting a parameter always causes it to revert to its
        default value, and future calls to ``set()`` with ``clobber=False`` will
        once again be able to modify the value.

        If you unset a particular step/index for a parameter with optional
        per-node values, note that the newly returned value will be the global
        value if it has been set. To completely return the parameter to its
        default state, the global value has to be unset as well.

        ``unset()`` has no effect if called on a parameter that has not been
        previously set.

        Args:
            keypath (list): Parameter keypath to clear.
            step (str): Step name to unset for parameters that may be specified
                on a per-node basis.
            index (str): Index name to unset for parameters that may be specified
                on a per-node basis.
        '''
        self.logger.debug(f'Unsetting {keypath}')

        if not self.schema.unset(*keypath, step=step, index=index):
            self.logger.debug(f'Failed to unset value for {keypath}: parameter is locked')

    ###########################################################################
    def add(self, *args, field='value', step=None, index=None, package=None):
        '''
        Adds item(s) to a schema parameter list.

        Adds item(s) to schema parameter list based on the keypath and value
        provided in the ``*args``.  See the :ref:`Schema Reference
        Manual<SiliconCompiler Schema>` for documentation of all supported
        keypaths. New schema dictionaries are automatically created for keypaths
        that overlap with 'default' dictionaries.

        The value provided must agree with the dictionary parameter 'type'.
        Accessing a non-existent keypath, providing a value that disagrees
        with the parameter type, or using add with a scalar parameter produces
        a logger error message and raises the Chip object error flag.

        Args:
            args (list): Parameter keypath followed by a value to add.
            field (str): Parameter field to modify.
            step (str): Step name to modify for parameters that may be specified
                on a per-node basis.
            index (str): Index name to modify for parameters that may be specified
                on a per-node basis.
            package (str): Package that this file/dir depends on. Available packages
                are listed in the package source section of the schema.

        Examples:
            >>> chip.add('input', 'rtl', 'verilog', 'hello.v')
            Adds the file 'hello.v' to the list of sources.
        '''
        keypath = args[:-1]
        value = args[-1]
        self.logger.debug(f'Appending value {value} to {keypath}')

        try:
            value_success = self.schema.add(*args, field=field, step=step, index=index)

            if field == 'value' and value_success:
                self.__add_set_package(keypath, value, package, step, index, True, True)
        except (ValueError, TypeError) as e:
            self.error(str(e))

    ###########################################################################
    def input(self, filename, fileset=None, filetype=None, iomap=None, package=None):
        '''
        Adds file to a filset. The default behavior is to infer filetypes and
        filesets based on the suffix of the file extensions. The method is
        a wrapper function for set.add('input', filset, filetype,...)

        Default filetype and filset based on suffix:

        .. code:: none

            {iotable}

        Args:
            fileset (str): File grouping
            filetype (str): File type
            iomap (dict of tuple(set, type)): File set and type mapping based on file extension

        '''

        self._add_input_output('input', filename, fileset, filetype, iomap, package=package)
    # Replace {iotable} in __doc__ with actual table for fileset/filetype and extension mapping
    input.__doc__ = input.__doc__.replace("{iotable}",
                                          utils.format_fileset_type_table())

    ###########################################################################
    def output(self, filename, fileset=None, filetype=None, iomap=None):
        '''Same as input'''

        self._add_input_output('output', filename, fileset, filetype, iomap)
    # Copy input functions __doc__ and replace 'input' with 'output' to make constant
    output.__doc__ = input.__doc__.replace("input", "output")

    ###########################################################################
    def _add_input_output(self, category, filename, fileset, filetype, iomap, package=None):
        '''
        Adds file to input or output groups.
        Performs a lookup in the io map for the fileset and filetype
        and will use those if they are not provided in the arguments
        '''
        # Normalize value to string in case we receive a pathlib.Path
        filename = str(filename)

        ext = utils.get_file_ext(filename)

        default_fileset = None
        default_filetype = None
        if not iomap:
            iomap = utils.get_default_iomap()

        if ext in iomap:
            default_fileset, default_filetype = iomap[ext]

        if not fileset:
            use_fileset = default_fileset
        else:
            use_fileset = fileset

        if not filetype:
            use_filetype = default_filetype
        else:
            use_filetype = filetype

        if not use_fileset or not use_filetype:
            self.logger.error(f'Unable to infer {category} fileset and/or filetype for '
                              f'{filename} based on file extension.')
        elif not fileset and not filetype:
            self.logger.info(f'{filename} inferred as {use_fileset}/{use_filetype}')
        elif not filetype:
            self.logger.info(f'{filename} inferred as filetype {use_filetype}')
        elif not fileset:
            self.logger.info(f'{filename} inferred as fileset {use_fileset}')

        self.add(category, use_fileset, use_filetype, filename, package=package)

    ###########################################################################
    def _find_sc_file(self, filename, missing_ok=False, search_paths=None):
        """
        Returns the absolute path for the filename provided.

        Searches the for the filename provided and returns the absolute path.
        If no valid absolute path is found during the search, None is returned.

        Shell variables ('$' followed by strings consisting of numbers,
        underscores, and digits) are replaced with the variable value.

        Args:
            filename (str): Relative or absolute filename.
            missing_ok (bool): If False, error out if no valid absolute path
                found, rather than returning None.
            search_paths (list): List of directories to search under instead of
                the defaults.

        Returns:
            Returns absolute path of 'filename' if found, otherwise returns
            None.

        Examples:
            >>> chip._find_sc_file('flows/asicflow.py')
           Returns the absolute path based on the sc installation directory.

        """

        if not filename:
            return None

        # Replacing environment variables
        filename = self._resolve_env_vars(filename)

        # If we have an absolute path, pass-through here
        if os.path.isabs(filename) and os.path.exists(filename):
            return filename

        # Otherwise, search relative to search_paths
        if search_paths is None:
            search_paths = [self.cwd]

        searchdirs = ', '.join([str(p) for p in search_paths])
        self.logger.debug(f"Searching for file {filename} in {searchdirs}")

        result = None
        for searchdir in search_paths:
            if not os.path.isabs(searchdir):
                searchdir = os.path.join(self.cwd, searchdir)

            abspath = os.path.abspath(os.path.join(searchdir, filename))
            if os.path.exists(abspath):
                result = abspath
                break

        if result is None and not missing_ok:
            self.error(f"File {filename} was not found")

        return result

    ###########################################################################
    def find_files(self, *keypath, missing_ok=False, job=None, step=None, index=None):
        """
        Returns absolute paths to files or directories based on the keypath
        provided.

        By default, this function first checks if the keypath provided has its
        `copy` parameter set to True. If so, it returns paths to the files in
        the build directory. Otherwise, it resolves these files based on the
        current working directory and SC path.

        The keypath provided must point to a schema parameter of type file, dir,
        or lists of either. Otherwise, it will trigger an error.

        Args:
            keypath (list str): Variable length schema key list.
            missing_ok (bool): If True, silently return None when files aren't
                found. If False, print an error and set the error flag.
            job (str): Jobname to use for dictionary access in place of the
                current active jobname.
            step (str): Step name to access for parameters that may be specified
                on a per-node basis.
            index (str): Index name to access for parameters that may be specified
                on a per-node basis.

        Returns:
            If keys points to a scalar entry, returns an absolute path to that
            file/directory, or None if not found. It keys points to a list
            entry, returns a list of either the absolute paths or None for each
            entry, depending on whether it is found.

        Examples:
            >>> chip.find_files('input', 'verilog')
            Returns a list of absolute paths to source files, as specified in
            the schema.

        """
        strict = self.get('option', 'strict')
        pernode = self.get(*keypath, field='pernode')
        if strict and pernode == 'optional' and (step is None or index is None):
            self.error(
                f"Invalid args to find_files() of keypath {keypath}: step and "
                "index are required for reading from this parameter while "
                "['option', 'strict'] is True."
            )
            return []
        return self._find_files(*keypath, missing_ok=missing_ok, job=job, step=step, index=index)

    def __convert_paths_to_posix(self, paths):
        posix_paths = []
        for p in paths:
            if p:
                # Cast everything to a windows path and convert to posix.
                # https://stackoverflow.com/questions/73682260
                posix_paths.append(pathlib.PureWindowsPath(p).as_posix())
            else:
                posix_paths.append(p)
        return posix_paths

    ###########################################################################
    def _find_files(self,
                    *keypath,
                    missing_ok=False,
                    job=None,
                    step=None,
                    index=None,
                    list_index=None,
                    abs_path_only=False):
        """Internal find_files() that allows you to skip step/index for optional
        params, regardless of [option, strict]."""

        paramtype = self.get(*keypath, field='type', job=job)

        if 'file' not in paramtype and 'dir' not in paramtype:
            self.error('Can only call find_files on file or dir types')
            return None

        is_list = bool(re.match(r'\[', paramtype))

        paths = self.schema.get(*keypath, job=job, step=step, index=index)
        dependencies = self.schema.get(*keypath, job=job,
                                       step=step, index=index, field='package')
        # Convert to list if we have scalar
        if not is_list:
            # Dependencies are always specified as list with default []
            # If paths is a scalar we convert the default [] to [None]
            # to have a matching list with one element
            if dependencies == []:
                dependencies = [None]
            paths = [paths]

        if list_index is not None:
            # List index is set, so we only want to check a particular path in the key
            paths = [paths[list_index]]
            dependencies = [dependencies[list_index]]

        paths = self.__convert_paths_to_posix(paths)
        dependencies = self.__convert_paths_to_posix(dependencies)

        result = []

        # Special cases for various ['tool', ...] files that may be implicitly
        # under the workdir (or refdir in the case of scripts).
        # TODO: it may be cleaner to have a file resolution scope flag in schema
        # (e.g. 'workdir', 'refdir'), rather than hardcoding special
        # cases.

        search_paths = None
        if len(keypath) >= 5 and \
           keypath[0] == 'tool' and \
           keypath[4] in ('input', 'output', 'report'):
            if keypath[4] == 'report':
                io = ""
            else:
                io = keypath[4] + 's'
            iodir = os.path.join(self._getworkdir(jobname=job, step=step, index=index), io)
            search_paths = [iodir]
        elif len(keypath) >= 5 and keypath[0] == 'tool' and keypath[4] == 'script':
            tool = keypath[1]
            task = keypath[3]
            refdirs = self._find_files('tool', tool, 'task', task, 'refdir',
                                       step=step, index=index,
                                       abs_path_only=True)
            search_paths = refdirs

        if search_paths:
            search_paths = self.__convert_paths_to_posix(search_paths)

        for (dependency, path) in zip(dependencies, paths):
            if not search_paths:
                import_path = self._find_sc_imported_file(path,
                                                          dependency,
                                                          self._getcollectdir(jobname=job))
                if import_path:
                    result.append(import_path)
                    continue
            if dependency:
                depdendency_path = os.path.abspath(
                    os.path.join(sc_package.path(self, dependency), path))
                if os.path.exists(depdendency_path):
                    result.append(depdendency_path)
                else:
                    result.append(None)
                    if not missing_ok:
                        self.error(f'Could not find {path} in {dependency}.')
                continue
            result.append(self._find_sc_file(path,
                                             missing_ok=missing_ok,
                                             search_paths=search_paths))

        if self._relative_path and not abs_path_only:
            rel_result = []
            for path in result:
                if path:
                    rel_result.append(os.path.relpath(path, self._relative_path))
                else:
                    rel_result.append(path)
            result = rel_result

        # Convert back to scalar if that was original type
        if not is_list:
            return result[0]

        return result

    ###########################################################################
    def _find_sc_imported_file(self, path, package, collected_dir):
        """
        Returns the path to an imported file if it is available in the import directory
        or in a directory that was imported

        Returns none if not found
        """
        if not path:
            return None

        path_paths = pathlib.PurePosixPath(path).parts
        for n in range(len(path_paths)):
            # Search through the path elements to see if any of the previous path parts
            # have been imported

            n += 1
            basename = str(pathlib.PurePosixPath(*path_paths[0:n]))
            endname = str(pathlib.PurePosixPath(*path_paths[n:]))

            abspath = os.path.join(collected_dir, self._get_imported_filename(basename, package))
            if endname:
                abspath = os.path.join(abspath, endname)
            abspath = os.path.abspath(abspath)
            if os.path.exists(abspath):
                return abspath

        return None

    ###########################################################################
    def find_result(self, filetype, step, jobname=None, index='0'):
        """
        Returns the absolute path of a compilation result.

        Utility function that returns the absolute path to a results
        file based on the provided arguments. The result directory
        structure is:

        <dir>/<design>/<jobname>/<step>/<index>/outputs/<design>.filetype

        Args:
            filetype (str): File extension (v, def, etc)
            step (str): Task step name ('syn', 'place', etc)
            jobname (str): Jobid directory name
            index (str): Task index

        Returns:
            Returns absolute path to file.

        Examples:
            >>> manifest_filepath = chip.find_result('vg', 'syn')
           Returns the absolute path to the manifest.
        """
        if jobname is None:
            jobname = self.get('option', 'jobname')

        workdir = self._getworkdir(jobname, step, index)
        design = self.top()
        filename = f"{workdir}/outputs/{design}.{filetype}"

        self.logger.debug("Finding result %s", filename)

        if os.path.exists(filename):
            return filename
        else:
            return None

    ###########################################################################
    def _abspath(self):
        '''
        Internal function that returns a copy of the chip schema with all
        relative paths resolved where required.
        '''
        schema = self.schema.copy()
        for keypath in self.allkeys():
            paramtype = self.get(*keypath, field='type')
            if not ('file' in paramtype or 'dir' in paramtype):
                # only do something if type is file or dir
                continue

            values = self.schema._getvals(*keypath)
            for value, step, index in values:
                if not value:
                    continue
                abspaths = self._find_files(*keypath, missing_ok=True, step=step, index=index)
                if isinstance(abspaths, list) and None in abspaths:
                    # Lists may not contain None
                    schema.set(*keypath, [], step=step, index=index)
                else:
                    schema.set(*keypath, abspaths, step=step, index=index)
        return schema

    ###########################################################################
    def _key_may_be_updated(self, keypath):
        '''Helper that returns whether `keypath` can be updated mid-run.'''
        # TODO: cleaner way to manage this?
        if keypath[0] in ('metric', 'record'):
            return True
        if keypath[0] == 'flowgraph' and keypath[4] in ('select', 'status'):
            return True
        if keypath[0] == 'tool':
            return True
        if self.get(*keypath, field='type') in ['file', '[file]']:
            return True
        return False

    ###########################################################################
    def _merge_manifest(self, src, job=None, clobber=True, clear=True, check=False, partial=False):
        """
        Merges a given manifest with the current compilation manifest.

        All value fields in the provided schema dictionary are merged into the
        current chip object. Dictionaries with non-existent keypath produces a
        logger error message and raises the Chip object error flag.

        Args:
            src (Schema): Schema object to merge
            job (str): Specifies non-default job to merge into
            clear (bool): If True, disables append operations for list type
            clobber (bool): If True, overwrites existing parameter value
            check (bool): If True, checks the validity of each key
            partial (bool): If True, perform a partial merge, only merging
                keypaths that may have been updated during run().
        """
        if job is not None:
            dest = self.schema.history(job)
        else:
            dest = self.schema

        for keylist in src.allkeys():
            if keylist[0] in ('history', 'library'):
                continue
            if partial and not self._key_may_be_updated(keylist):
                continue
            # only read in valid keypaths without 'default'
            key_valid = True
            if check:
                key_valid = dest.valid(*keylist, default_valid=True)
                if not key_valid:
                    self.logger.warning(f'Keypath {keylist} is not valid')
            if key_valid and 'default' not in keylist:
                typestr = src.get(*keylist, field='type')
                should_append = re.match(r'\[', typestr) and not clear
                key_cfg = src._search(*keylist)
                for val, step, index in src._getvals(*keylist, return_defvalue=False):
                    # update value, handling scalars vs. lists
                    if should_append:
                        dest.add(*keylist, val, step=step, index=index)
                    else:
                        dest.set(*keylist, val, step=step, index=index, clobber=clobber)

                    # update other pernode fields
                    # TODO: only update these if clobber is successful
                    step_key = Schema.GLOBAL_KEY if not step else step
                    idx_key = Schema.GLOBAL_KEY if not index else index
                    for field in key_cfg['node'][step_key][idx_key].keys():
                        if field == 'value':
                            continue
                        v = src.get(*keylist, step=step, index=index, field=field)
                        if should_append:
                            dest.add(*keylist, v, step=step, index=index, field=field)
                        else:
                            dest.set(*keylist, v, step=step, index=index, field=field)

                # update other fields that a user might modify
                for field in key_cfg.keys():
                    if field in ('node', 'switch', 'type', 'require',
                                 'shorthelp', 'example', 'help'):
                        # skip these fields (node handled above, others are static)
                        continue
                    # TODO: should we be taking into consideration clobber for these fields?
                    v = src.get(*keylist, field=field)
                    dest.set(*keylist, v, field=field)

    ###########################################################################
    def check_filepaths(self):
        '''
        Verifies that paths to all files in manifest are valid.

        Returns:
            True if all file paths are valid, otherwise False.
        '''

        allkeys = self.allkeys()
        error = False
        for keypath in allkeys:
            paramtype = self.get(*keypath, field='type')
            is_file = 'file' in paramtype
            is_dir = 'dir' in paramtype
            is_list = paramtype.startswith('[')

            if is_file or is_dir:
                if keypath[-2:] == ('option', 'builddir'):
                    # Skip ['option', 'builddir'] since it will get created by run() if it doesn't
                    # exist
                    continue

                for check_files, step, index in self.schema._getvals(*keypath):
                    if not check_files:
                        continue

                    if not is_list:
                        check_files = [check_files]

                    for idx, check_file in enumerate(check_files):
                        found_file = self._find_files(*keypath,
                                                      missing_ok=True,
                                                      step=step, index=index,
                                                      list_index=idx)
                        if is_list:
                            found_file = found_file[0]
                        if not found_file:
                            self.logger.error(f"Parameter {keypath} path {check_file} is invalid")
                            error = True

        return not error

    ###########################################################################
    def _check_manifest_dynamic(self, step, index):
        '''Runtime checks called from _runtask().

        - Make sure expected inputs exist.
        - Make sure all required filepaths resolve correctly.
        '''
        error = False

        flow = self.get('option', 'flow')
        tool, task = self._get_tool_task(step, index, flow=flow)

        required_inputs = self.get('tool', tool, 'task', task, 'input', step=step, index=index)
        input_dir = os.path.join(self._getworkdir(step=step, index=index), 'inputs')
        for filename in required_inputs:
            path = os.path.join(input_dir, filename)
            if not os.path.exists(path):
                self.logger.error(f'Required input {filename} not received for {step}{index}.')
                error = True

        all_required = self.get('tool', tool, 'task', task, 'require', step=step, index=index)
        for item in all_required:
            keypath = item.split(',')
            if not self.valid(*keypath):
                self.logger.error(f'Cannot resolve required keypath {keypath}.')
                error = True
            else:
                paramtype = self.get(*keypath, field='type')
                if ('file' in paramtype) or ('dir' in paramtype):
                    for val, step, index in self.schema._getvals(*keypath):
                        abspath = self._find_files(*keypath,
                                                   missing_ok=True,
                                                   step=step, index=index)
                        unresolved_paths = val
                        if not isinstance(abspath, list):
                            abspath = [abspath]
                            unresolved_paths = [unresolved_paths]
                        for i, path in enumerate(abspath):
                            if path is None:
                                unresolved_path = unresolved_paths[i]
                                self.logger.error(f'Cannot resolve path {unresolved_path} in '
                                                  f'required file keypath {keypath}.')
                                error = True

        return not error

    ###########################################################################
    def check_manifest(self):
        '''
        Verifies the integrity of the pre-run compilation manifest.

        Checks the validity of the current schema manifest in
        memory to ensure that the design has been properly set up prior
        to running compilation. The function is called inside the run()
        function but can also be called separately. Checks performed by the
        check_manifest() function include:

        * Has a flowgraph been defined?
        * Does the manifest satisfy the schema requirement field settings?
        * Are all flowgraph input names legal step/index pairs?
        * Are the tool parameter setting requirements met?

        Returns:
            Returns True if the manifest is valid, else returns False.

        Examples:
            >>> manifest_ok = chip.check_manifest()
            Returns True of the Chip object dictionary checks out.

        '''
        error = False

        # Dynamic checks
        # We only perform these if arg, step and arg, index are set.
        # We don't check inputs for skip all
        # TODO: Need to add skip step

        cur_step = self.get('arg', 'step')
        cur_index = self.get('arg', 'index')
        if cur_step and cur_index and not self.get('option', 'skipall'):
            return self._check_manifest_dynamic(cur_step, cur_index)

        design = self.get('design')
        flow = self.get('option', 'flow')

        # 1. Checking that flowgraph and nodes to execute are legal
        if flow not in self.getkeys('flowgraph'):
            error = True
            self.logger.error(f"flowgraph {flow} not defined.")

        nodes_to_execute = self.nodes_to_execute()
        for (step, index) in nodes_to_execute:
            in_job = self._get_in_job(step, index)

            for in_step, in_index in _get_pruned_node_inputs(self, flow, (step, index)):
                if in_job != self.get('option', 'jobname'):
                    workdir = self._getworkdir(jobname=in_job, step=in_step, index=in_index)
                    cfg = os.path.join(workdir, 'outputs', f'{design}.pkg.json')
                    if not os.path.isfile(cfg):
                        self.logger.error(f'{step}{index} relies on {in_step}{in_index} '
                                          f'from job {in_job}, but this task has not been run.')
                        error = True
                    continue
                if (in_step, in_index) in nodes_to_execute:
                    # we're gonna run this step, OK
                    continue
                if self.get('flowgraph', flow, in_step, in_index, 'status') == NodeStatus.SUCCESS:
                    # this task has already completed successfully, OK
                    continue
                self.logger.error(f'{step}{index} relies on {in_step}{in_index}, '
                                  'but this task has not been run and is not in the '
                                  'current nodes to execute.')
                error = True

        # 2. Check library names
        libraries = set()
        libs_to_check = []
        if self.get('option', 'mode') == 'asic':
            libs_to_check.append(('asic', 'logiclib'))
            libs_to_check.append(('asic', 'macrolib'))
        libs_to_check.append(('option', 'library'))
        # Create a list of nodes that include global and step only
        lib_node_check = [(None, None)]
        for step, _ in nodes_to_execute:
            lib_node_check.append((step, None))
        lib_node_check.extend(nodes_to_execute)
        for lib_key in libs_to_check:
            for val, step, index in self.schema._getvals(*lib_key):
                if (step, index) in lib_node_check:
                    libraries.update(val)

        for library in libraries:
            if library not in self.getkeys('library'):
                error = True
                self.logger.error(f"Target library {library} not found.")

        # 3. Check requirements list
        allkeys = self.allkeys()
        for key in allkeys:
            keypath = ",".join(key)
            if 'default' not in key and 'history' not in key and 'library' not in key:
                key_empty = self.schema._is_empty(*key)
                requirement = self.get(*key, field='require')
                if key_empty and (str(requirement) == 'all'):
                    error = True
                    self.logger.error(f"Global requirement missing for [{keypath}].")
                elif key_empty and (str(requirement) == self.get('option', 'mode')):
                    error = True
                    self.logger.error(f"Mode requirement missing for [{keypath}].")

        # 4. Check if tool/task modules exists
        for (step, index) in nodes_to_execute:
            tool = self.get('flowgraph', flow, step, index, 'tool')
            task = self.get('flowgraph', flow, step, index, 'task')
            tool_name, task_name = self._get_tool_task(step, index, flow=flow)

            if not self._get_tool_module(step, index, flow=flow, error=False):
                error = True
                self.logger.error(f"Tool module {tool_name} could not be found or "
                                  f"loaded for {step}{index}.")
            if not self._get_task_module(step, index, flow=flow, error=False):
                error = True
                task_module = self.get('flowgraph', flow, step, index, 'taskmodule')
                self.logger.error(f"Task module {task_module} for {tool_name}/{task_name} "
                                  f"could not be found or loaded for {step}{index}.")

        # 5. Check per tool parameter requirements (when tool exists)
        for (step, index) in nodes_to_execute:
            tool, task = self._get_tool_task(step, index, flow=flow)
            task_module = self._get_task_module(step, index, flow=flow, error=False)
            if self._is_builtin(tool, task):
                continue

            if tool not in self.getkeys('tool'):
                error = True
                self.logger.error(f'{tool} is not configured.')
                continue

            if task not in self.getkeys('tool', tool, 'task'):
                error = True
                self.logger.error(f'{tool}/{task} is not configured.')
                continue

            if self.valid('tool', tool, 'task', task, 'require'):
                all_required = self.get('tool', tool, 'task', task, 'require',
                                        step=step, index=index)
                for item in all_required:
                    keypath = item.split(',')
                    if self.schema._is_empty(*keypath):
                        error = True
                        self.logger.error(f"Value empty for {keypath} for {tool}.")

            task_run = getattr(task_module, 'run', None)
            if self.schema._is_empty('tool', tool, 'exe') and not task_run:
                error = True
                self.logger.error(f'No executable or run() function specified for {tool}/{task}')

        if not self._check_flowgraph_io():
            error = True

        return not error

    ###########################################################################
    def _gather_outputs(self, step, index):
        '''Return set of filenames that are guaranteed to be in outputs
        directory after a successful run of step/index.'''

        flow = self.get('option', 'flow')
        task_gather = getattr(self._get_task_module(step, index, flow=flow, error=False),
                              '_gather_outputs',
                              None)
        if task_gather:
            return set(task_gather(self, step, index))

        tool, task = self._get_tool_task(step, index, flow=flow)
        return set(self.get('tool', tool, 'task', task, 'output', step=step, index=index))

    ###########################################################################
    def _check_flowgraph(self, flow=None):
        '''
        Check if flowgraph is valid.

        * Checks if all edges have valid nodes
        * Checks that there are no duplicate edges
        * Checks if from/to is valid

        Returns True if valid, False otherwise.
        '''

        if not flow:
            flow = self.get('option', 'flow')

        error = False

        nodes = set()
        for (step, index) in _get_flowgraph_nodes(self, flow):
            nodes.add((step, index))
            input_nodes = _get_flowgraph_node_inputs(self, flow, (step, index))
            nodes.update(input_nodes)

            for node in set(input_nodes):
                if input_nodes.count(node) > 1:
                    in_step, in_index = node
                    self.logger.error(f'Duplicate edge from {in_step}{in_index} to '
                                      f'{step}{index} in the {flow} flowgraph')
                    error = True

        for step, index in nodes:
            # For each task, check input requirements.
            tool, task = self._get_tool_task(step, index, flow=flow)

            if not tool:
                self.logger.error(f'{step}{index} is missing a tool definition in the {flow} '
                                  'flowgraph')
                error = True

            if not task:
                self.logger.error(f'{step}{index} is missing a task definition in the {flow} '
                                  'flowgraph')
                error = True

        for step in self.get('option', 'from'):
            if step not in self.getkeys('flowgraph', flow):
                self.logger.error(f'{step} is not defined in the {flow} flowgraph')
                error = True

        for step in self.get('option', 'to'):
            if step not in self.getkeys('flowgraph', flow):
                self.logger.error(f'{step} is not defined in the {flow} flowgraph')
                error = True

        if not _check_execution_nodes_inputs(self, flow):
            error = True

        unreachable_steps = _unreachable_steps_to_execute(self, flow)
        if unreachable_steps:
            self.logger.error(f'These final steps in {flow} can not be reached: '
                              f'{list(unreachable_steps)}')
            error = True

        return not error

    ###########################################################################
    def _check_flowgraph_io(self):
        '''Check if flowgraph is valid in terms of input and output files.

        Returns True if valid, False otherwise.
        '''

        flow = self.get('option', 'flow')
        flowgraph_nodes = self.nodes_to_execute()
        for (step, index) in flowgraph_nodes:
            # For each task, check input requirements.
            tool, task = self._get_tool_task(step, index, flow=flow)

            if self._is_builtin(tool, task):
                # We can skip builtins since they don't have any particular
                # input requirements -- they just pass through what they
                # receive.
                continue

            # Get files we receive from input nodes.
            in_nodes = _get_flowgraph_node_inputs(self, flow, (step, index))
            all_inputs = set()
            requirements = self.get('tool', tool, 'task', task, 'input', step=step, index=index)
            for in_step, in_index in in_nodes:
                if (in_step, in_index) not in flowgraph_nodes:
                    # If we're not running the input step, the required
                    # inputs need to already be copied into the build
                    # directory.
                    in_job = self._get_in_job(step, index)
                    workdir = self._getworkdir(jobname=in_job, step=in_step, index=in_index)
                    in_step_out_dir = os.path.join(workdir, 'outputs')

                    if not os.path.isdir(in_step_out_dir):
                        # This means this step hasn't been run, but that
                        # will be flagged by a different check. No error
                        # message here since it would be redundant.
                        inputs = []
                        continue

                    design = self.get('design')
                    manifest = f'{design}.pkg.json'
                    inputs = [inp for inp in os.listdir(in_step_out_dir) if inp != manifest]
                else:
                    inputs = self._gather_outputs(in_step, in_index)

                for inp in inputs:
                    node_inp = input_file_node_name(inp, in_step, in_index)
                    if node_inp in requirements:
                        inp = node_inp
                    if inp in all_inputs:
                        self.logger.error(f'Invalid flow: {step}{index} '
                                          f'receives {inp} from multiple input tasks')
                        return False
                    all_inputs.add(inp)

            for requirement in requirements:
                if requirement not in all_inputs:
                    self.logger.error(f'Invalid flow: {step}{index} will '
                                      f'not receive required input {requirement}.')
                    return False

        return True

    ###########################################################################
    def read_manifest(self, filename, job=None, clear=True, clobber=True):
        """
        Reads a manifest from disk and merges it with the current compilation manifest.

        The file format read is determined by the filename suffix. Currently
        json (*.json) and yaml(*.yaml) formats are supported.

        Args:
            filename (filepath): Path to a manifest file to be loaded.
            job (str): Specifies non-default job to merge into.
            clear (bool): If True, disables append operations for list type.
            clobber (bool): If True, overwrites existing parameter value.

        Examples:
            >>> chip.read_manifest('mychip.json')
            Loads the file mychip.json into the current Chip object.
        """
        self._read_manifest(filename, job=job, clear=clear, clobber=clobber)

    ###########################################################################
    def _read_manifest(self, filename, job=None, clear=True, clobber=True, partial=False):
        """
        Internal read_manifest() implementation with `partial` arg.

        partial (bool): If True, perform a partial merge, only merging keypaths
        that may have been updated during run().
        """
        # Read from file into new schema object
        schema = Schema(manifest=filename, logger=self.logger)

        # Merge data in schema with Chip configuration
        self._merge_manifest(schema, job=job, clear=clear, clobber=clobber, partial=partial)

        # Read history, if we're not already reading into a job
        if 'history' in schema.cfg and not partial and not job:
            for historic_job in schema.cfg['history'].keys():
                self._merge_manifest(schema.history(historic_job),
                                     job=historic_job,
                                     clear=clear,
                                     clobber=clobber,
                                     partial=False)

        # TODO: better way to handle this?
        if 'library' in schema.cfg and not partial:
            for libname in schema.cfg['library'].keys():
                self._import_library(libname, schema.cfg['library'][libname],
                                     job=job,
                                     clobber=clobber)

    ###########################################################################
    def write_manifest(self, filename, prune=False, abspath=False):
        '''
        Writes the compilation manifest to a file.

        The write file format is determined by the filename suffix. Currently
        json (*.json), yaml (*.yaml), tcl (*.tcl), and (*.csv) formats are
        supported.

        Args:
            filename (filepath): Output filepath
            prune (bool): If True, only essential fields from the
                 the Chip object schema are written to the output file.
            abspath (bool): If set to True, then all schema filepaths
                 are resolved to absolute filepaths.

        Examples:
            >>> chip.write_manifest('mydump.json')
            Prunes and dumps the current chip manifest into mydump.json
        '''

        filepath = os.path.abspath(filename)
        self.logger.debug('Writing manifest to %s', filepath)

        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        # resolve absolute paths
        if abspath:
            schema = self._abspath()
        else:
            schema = self.schema.copy()

        if prune:
            self.logger.debug('Pruning dictionary before writing file %s', filepath)
            schema.prune()

        is_csv = re.search(r'(\.csv)(\.gz)*$', filepath)

        # format specific dumping
        if filepath.endswith('.gz'):
            fout = gzip.open(filepath, 'wt', encoding='UTF-8')
        elif is_csv:
            # Files written using csv library should be opened with newline=''
            # https://docs.python.org/3/library/csv.html#id3
            fout = open(filepath, 'w', newline='')
        else:
            fout = open(filepath, 'w')

        # format specific printing
        try:
            if re.search(r'(\.json|\.sup)(\.gz)*$', filepath):
                schema.write_json(fout)
            elif re.search(r'(\.yaml|\.yml)(\.gz)*$', filepath):
                schema.write_yaml(fout)
            elif re.search(r'(\.tcl)(\.gz)*$', filepath):
                # TCL only gets values associated with the current node.
                step = self.get('arg', 'step')
                index = self.get('arg', 'index')
                schema.write_tcl(fout,
                                 prefix="dict set sc_cfg",
                                 step=step,
                                 index=index,
                                 template=utils.get_file_template('tcl/manifest.tcl.j2'))
            elif is_csv:
                schema.write_csv(fout)
            else:
                self.error('File format not recognized %s', filepath)
        finally:
            fout.close()

    ###########################################################################
    def check_checklist(self, standard, items=None,
                        check_ok=False, verbose=False, require_reports=True):
        '''
        Check items in a checklist.

        Checks the status of items in a checklist for the standard provided. If
        a specific list of items is unspecified, all items are checked.

        All items have an associated 'task' parameter, which indicates which
        tasks can be used to automatically validate the item. For an item to be
        checked, all tasks must satisfy the item's criteria, unless waivers are
        provided. In addition, that task must have generated EDA report files
        for each metric in the criteria.

        For items without an associated task, the only requirement is that at
        least one report has been added to that item.

        When 'check_ok' is True, every item must also have its 'ok' parameter
        set to True, indicating that a human has reviewed the item.

        Args:
            standard (str): Standard to check.
            items (list of str): Items to check from standard.
            check_ok (bool): Whether to check item 'ok' parameter.
            verbose (bool): Whether to print passing criteria.
            require_reports (bool): Whether to assert the presence of reports.

        Returns:
            Status of item check.

        Examples:
            >>> status = chip.check_checklist('iso9000', 'd000')
            Returns status.
        '''
        error = False

        self.logger.info(f'Checking checklist {standard}')

        if standard not in self.getkeys('checklist'):
            self.logger.error(f'{standard} has not been loaded.')
            return False

        if items is None:
            items = self.getkeys('checklist', standard)

        # these tasks are recorded by SC so there are no reports
        metrics_without_reports = (
            'tasktime',
            'exetime',
            'memory')

        for item in items:
            if item not in self.getkeys('checklist', standard):
                self.logger.error(f'{item} is not a check in {standard}.')
                error = True
                continue

            allow_missing_reports = True

            all_criteria = self.get('checklist', standard, item, 'criteria')
            for criteria in all_criteria:
                m = re.match(r'^(\w+)\s*([\>\=\<]+)\s*([+\-]?\d+(\.\d+)?(e[+\-]?\d+)?)$',
                             criteria.strip())
                if not m:
                    self.error(f"Illegal checklist criteria: {criteria}")
                    return False
                elif m.group(1) not in self.getkeys('metric'):
                    self.error(f"Criteria must use legal metrics only: {criteria}")
                    return False

                metric = m.group(1)
                op = m.group(2)
                if self.get('metric', metric, field='type') == 'int':
                    goal = int(m.group(3))
                    number_format = 'd'
                else:
                    goal = float(m.group(3))

                    if goal == 0.0 or (abs(goal) > 1e-3 and abs(goal) < 1e5):
                        number_format = '.3f'
                    else:
                        number_format = '.3e'

                if metric not in metrics_without_reports:
                    allow_missing_reports = False

                tasks = self.get('checklist', standard, item, 'task')
                for job, step, index in tasks:
                    if job not in self.getkeys('history'):
                        self.error(f'{job} not found in history')

                    flow = self.get('option', 'flow', job=job)

                    if step not in self.getkeys('flowgraph', flow, job=job):
                        self.error(f'{step} not found in flowgraph')

                    if index not in self.getkeys('flowgraph', flow, step, job=job):
                        self.error(f'{step}{index} not found in flowgraph')

                    # Automated checks
                    flow = self.get('option', 'flow', job=job)
                    tool = self.get('flowgraph', flow, step, index, 'tool', job=job)
                    task = self.get('flowgraph', flow, step, index, 'task', job=job)

                    value = self.get('metric', metric, job=job, step=step, index=index)
                    criteria_ok = self._safecompare(value, op, goal)
                    if metric in self.getkeys('checklist', standard, item, 'waiver'):
                        waivers = self.get('checklist', standard, item, 'waiver', metric)
                    else:
                        waivers = []

                    criteria_str = f'{metric}{op}{goal:{number_format}}'
                    compare_str = f'{value:{number_format}}{op}{goal:{number_format}}'
                    step_desc = f'job {job} with step {step}{index} and task {tool}/{task}'
                    if not criteria_ok and waivers:
                        self.logger.warning(f'{item} criteria {criteria_str} ({compare_str}) unmet '
                                            f'by {step_desc}, but found waivers.')
                    elif not criteria_ok:
                        self.logger.error(f'{item} criteria {criteria_str} ({compare_str}) unmet '
                                          f'by {step_desc}.')
                        error = True
                    elif verbose and criteria_ok:
                        self.logger.info(f'{item} criteria {criteria_str} met by {step_desc}.')

                    has_reports = \
                        self.valid('tool', tool, 'task', task, 'report', metric, job=job) and \
                        self.get('tool', tool, 'task', task, 'report', metric, job=job,
                                 step=step, index=index)

                    if metric in metrics_without_reports and not has_reports:
                        # No reports available and it is allowed
                        continue

                    try:
                        reports = self.find_files('tool', tool, 'task', task, 'report', metric,
                                                  job=job,
                                                  step=step, index=index,
                                                  missing_ok=not require_reports)
                    except SiliconCompilerError:
                        reports = []
                        continue

                    if require_reports and not reports:
                        self.logger.error(f'No EDA reports generated for metric {metric} in '
                                          f'{step_desc}')
                        error = True

                    for report in reports:
                        if not report:
                            continue

                        report = os.path.relpath(report, self.cwd)
                        if report not in self.get('checklist', standard, item, 'report'):
                            self.add('checklist', standard, item, 'report', report)

            if require_reports and \
               not allow_missing_reports and \
               not self.get('checklist', standard, item, 'report'):
                # TODO: validate that report exists?
                self.logger.error(f'No report documenting item {item}')
                error = True

            if check_ok and not self.get('checklist', standard, item, 'ok'):
                self.logger.error(f"Item {item} 'ok' field not checked")
                error = True

        if not error:
            self.logger.info('Check succeeded!')

        return not error

    ###########################################################################
    def _import_library(self, libname, libcfg, job=None, clobber=True):
        '''Helper to import library with config 'libconfig' as a library
        'libname' in current Chip object.'''
        if job:
            cfg = self.schema.cfg['history'][job]['library']
        else:
            cfg = self.schema.cfg['library']

        if 'library' in libcfg:
            for sublib_name, sublibcfg in libcfg['library'].items():
                self._import_library(sublib_name, sublibcfg, job=job, clobber=clobber)

            del libcfg['library']

        if libname in cfg:
            if not clobber:
                return

        cfg[libname] = libcfg
        self.__import_data_sources(libcfg)

        if 'pdk' in cfg[libname]:
            del cfg[libname]['pdk']

    ###########################################################################
    def write_flowgraph(self, filename, flow=None,
                        fillcolor='#ffffff', fontcolor='#000000',
                        fontsize='14', border=True, landscape=False):
        r'''
        Renders and saves the compilation flowgraph to a file.

        The chip object flowgraph is traversed to create a graphviz (\*.dot)
        file comprised of node, edges, and labels. The dot file is a
        graphical representation of the flowgraph useful for validating the
        correctness of the execution flow graph. The dot file is then
        converted to the appropriate picture or drawing format based on the
        filename suffix provided. Supported output render formats include
        png, svg, gif, pdf and a few others. For more information about the
        graphviz project, see see https://graphviz.org/

        Args:
            filename (filepath): Output filepath
            flow (str): Name of flowgraph to render
            fillcolor(str): Node fill RGB color hex value
            fontcolor (str): Node font RGB color hex value
            fontsize (str): Node text font size
            border (bool): Enables node border if True
            landscape (bool): Renders graph in landscape layout if True

        Examples:
            >>> chip.write_flowgraph('mydump.png')
            Renders the object flowgraph and writes the result to a png file.
        '''
        filepath = os.path.abspath(filename)
        self.logger.debug('Writing flowgraph to file %s', filepath)
        fileroot, ext = os.path.splitext(filepath)
        fileformat = ext.replace(".", "")

        if flow is None:
            flow = self.get('option', 'flow')

        if flow not in self.getkeys('flowgraph'):
            self.logger.error(f'{flow} is not a value flowgraph')
            return

        # controlling border width
        if border:
            penwidth = '1'
        else:
            penwidth = '0'

        # controlling graph direction
        if landscape:
            rankdir = 'LR'
        else:
            rankdir = 'TB'

        dot = graphviz.Digraph(format=fileformat)
        dot.graph_attr['rankdir'] = rankdir
        dot.attr(bgcolor='transparent')
        for (step, index) in _get_flowgraph_nodes(self, flow):
            node = f'{step}{index}'
            # create step node
            tool, task = self._get_tool_task(step, index, flow=flow)
            if self._is_builtin(tool, task):
                labelname = step
            elif tool is not None:
                labelname = f"{step}{index}\n({tool})"
            else:
                labelname = f"{step}{index}"
            dot.node(node, label=labelname, bordercolor=fontcolor, style='filled',
                     fontcolor=fontcolor, fontsize=fontsize, ordering="in",
                     penwidth=penwidth, fillcolor=fillcolor)
            # get inputs
            all_inputs = []
            for in_step, in_index in _get_flowgraph_node_inputs(self, flow, (step, index)):
                all_inputs.append(in_step + in_index)
            for item in all_inputs:
                dot.edge(item, node)
        try:
            dot.render(filename=fileroot, cleanup=True)
        except graphviz.ExecutableNotFound as e:
            self.logger.error(f'Unable to save flowgraph: {e}')

    ########################################################################
    def _collect(self, directory=None, verbose=True):
        '''
        Collects files found in the configuration dictionary and places
        them in inputs/. The function only copies in files that have the 'copy'
        field set as true. If 'copyall' is set to true, then all files are
        copied in.

        1. indexing like in run, job1
        2. chdir package
        3. run tool to collect files, pickle file in output/design.v
        4. copy in rest of the files below
        5. record files read in to schema

        '''

        if not directory:
            directory = os.path.join(self._getcollectdir())

        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)

        if verbose:
            self.logger.info('Collecting input sources')

        dirs = {}
        files = {}

        copyall = self.get('option', 'copyall')
        for key in self.allkeys():
            if key[-2:] == ('option', 'builddir'):
                # skip builddir
                continue
            if key[-2:] == ('option', 'cache'):
                # skip cache
                continue
            if key[0] == 'history':
                # skip history
                continue
            leaftype = self.get(*key, field='type')
            is_dir = re.search('dir', leaftype)
            is_file = re.search('file', leaftype)
            if is_dir or is_file:
                copy = self.get(*key, field='copy')
                if copyall or copy:
                    for value, step, index in self.schema._getvals(*key):
                        if not value:
                            continue
                        packages = self.get(*key, field='package', step=step, index=index)
                        key_dirs = self._find_files(*key, step=step, index=index)
                        if not isinstance(key_dirs, list):
                            key_dirs = [key_dirs]
                            value = [value]
                            packages = [packages]
                        for path, package, abspath in zip(value, packages, key_dirs):
                            if not package:
                                # Ensure package is an empty string
                                package = ''
                            if is_dir:
                                dirs[(package, path)] = abspath
                            else:
                                files[(package, path)] = abspath

        for package, path in sorted(dirs.keys()):
            posix_path = self.__convert_paths_to_posix([path])[0]
            if self._find_sc_imported_file(posix_path, package, directory):
                # File already imported in directory
                continue

            abspath = dirs[(package, path)]
            if abspath:
                filename = self._get_imported_filename(posix_path, package)
                dst_path = os.path.join(directory, filename)
                if os.path.exists(dst_path):
                    continue
                if verbose:
                    self.logger.info(f"Copying directory {abspath} to '{directory}' directory")
                shutil.copytree(abspath, dst_path)
            else:
                self.error(f'Failed to copy {path}', fatal=True)

        for package, path in sorted(files.keys()):
            posix_path = self.__convert_paths_to_posix([path])[0]
            if self._find_sc_imported_file(posix_path, package, directory):
                # File already imported in directory
                continue

            abspath = files[(package, path)]
            if abspath:
                filename = self._get_imported_filename(posix_path, package)
                dst_path = os.path.join(directory, filename)
                if verbose:
                    self.logger.info(f"Copying {abspath} to '{directory}' directory")
                shutil.copy(abspath, dst_path)
            else:
                self.error(f'Failed to copy {path}', fatal=True)

    ###########################################################################
    def _archive_node(self, tar, step=None, index=None, include=None):
        basedir = self._getworkdir(step=step, index=index)

        def arcname(path):
            return os.path.relpath(path, self.cwd)

        if include:
            for pattern in include:
                for path in glob.iglob(os.path.join(basedir, pattern)):
                    tar.add(path, arcname=arcname(path))
        else:
            for folder in ('reports', 'outputs'):
                path = os.path.join(basedir, folder)
                tar.add(path, arcname=arcname(path))

            logfile = os.path.join(basedir, f'{step}.log')
            if os.path.isfile(logfile):
                tar.add(logfile, arcname=arcname(logfile))

    ###########################################################################
    def __archive_job(self, tar, job, flowgraph_nodes, index=None, include=None):
        design = self.get('design')

        jobdir = self._getworkdir(jobname=job)
        manifest = os.path.join(jobdir, f'{design}.pkg.json')
        if os.path.isfile(manifest):
            arcname = os.path.relpath(manifest, self.cwd)
            tar.add(manifest, arcname=arcname)
        else:
            self.logger.warning('Archiving job with failed or incomplete run.')

        for (step, idx) in flowgraph_nodes:
            self.logger.info(f'Archiving {step}{idx}...')
            self._archive_node(tar, step, idx, include=include)

    ###########################################################################
    def archive(self, jobs=None, step=None, index=None, include=None, archive_name=None):
        '''Archive a job directory.

        Creates a single compressed archive (.tgz) based on the design,
        jobname, and flowgraph in the current chip manifest. Individual
        steps and/or indices can be archived based on arguments specified.
        By default, all steps and indices in the flowgraph are archived.
        By default, only outputs, reports, log files, and the final manifest
        are archived.

        Args:
            jobs (list of str): List of jobs to archive. By default, archives only the current job.
            step(str): Step to archive.
            index (str): Index to archive
            include (list of str): Override of default inclusion rules. Accepts list of glob
                patterns that are matched from the root of individual step/index directories. To
                capture all files, supply "*".
            archive_name (str): Path to the archive
        '''
        design = self.get('design')
        if not jobs:
            jobname = self.get('option', 'jobname')
            jobs = [jobname]
        else:
            jobname = '_'.join(jobs)

        if step and index:
            flowgraph_nodes = [(step, index)]
        elif step:
            flow = self.get('option', 'flow')
            flowgraph_nodes = _get_flowgraph_nodes(self, flow=flow, steps=[step])
        else:
            flowgraph_nodes = self.nodes_to_execute()

        if not archive_name:
            if step and index:
                archive_name = f"{design}_{jobname}_{step}{index}.tgz"
            elif step:
                archive_name = f"{design}_{jobname}_{step}.tgz"
            else:
                archive_name = f"{design}_{jobname}.tgz"

        self.logger.info(f'Creating archive {archive_name}...')

        with tarfile.open(archive_name, "w:gz") as tar:
            for job in jobs:
                if len(jobs) > 0:
                    self.logger.info(f'Archiving job {job}...')
                self.__archive_job(tar, job, flowgraph_nodes, include=include)
        return archive_name

    ###########################################################################
    def hash_files(self, *keypath, update=True, check=True, verbose=True, allow_cache=False,
                   step=None, index=None):
        '''Generates hash values for a list of parameter files.

        Generates a hash value for each file found in the keypath. If existing
        hash values are stored, this method will compare hashes and trigger an
        error if there's a mismatch. If the update variable is True, the
        computed hash values are recorded in the 'filehash' field of the
        parameter, following the order dictated by the files within the 'value'
        parameter field.

        Files are located using the find_files() function.

        The file hash calculation is performed based on the 'algo' setting.
        Supported algorithms include SHA1, SHA224, SHA256, SHA384, SHA512,
        and MD5.

        Args:
            *keypath(str): Keypath to parameter.
            update (bool): If True, the hash values are recorded in the
                chip object manifest.
            check (bool): If True, checks the newly computed hash against
                the stored hash.
            verbose (bool): If True, generates log messages.
            allow_cache (bool): If True, hashing check the cached values
                for specific files, if found, it will use that hash value
                otherwise the hash will be computed.

        Returns:
            A list of hash values.

        Examples:
            >>> hashlist = hash_files('input', 'rtl', 'verilog')
            Computes, stores, and returns hashes of files in :keypath:`input, rtl, verilog`.
        '''

        keypathstr = ','.join(keypath)
        # TODO: Insert into find_files?
        sc_type = self.get(*keypath, field='type')
        if 'file' not in sc_type and 'dir' not in sc_type:
            self.logger.error(f"Illegal attempt to hash non-file parameter [{keypathstr}].")
            return []

        filelist = self._find_files(*keypath, step=step, index=index)
        if not filelist:
            return []

        algo = self.get(*keypath, field='hashalgo')
        hashfunc = getattr(hashlib, algo, None)
        if not hashfunc:
            self.logger.error(f"Unable to use {algo} as the hashing algorithm for [{keypathstr}].")
            return []

        def hash_file(filename, hashobj=None):
            if not hashobj:
                hashobj = hashfunc()
            with open(filename, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    hashobj.update(byte_block)
            return hashobj.hexdigest()

        if any([f is None for f in filelist]):
            # skip if there are missing files
            return []

        # cycle through all paths
        hashlist = []
        if filelist and verbose:
            self.logger.info(f'Computing hash value for [{keypathstr}]')

        for filename in filelist:
            if allow_cache and filename in self.__hashes:
                hashlist.append(self.__hashes[filename])
                continue

            if os.path.isfile(filename):
                hashlist.append(hash_file(filename))
            elif os.path.isdir(filename):
                all_files = []
                for root, dirs, files in os.walk(filename):
                    all_files.extend([os.path.join(root, f) for f in files])
                dirhash = None
                hashobj = hashfunc()
                for file in sorted(all_files):
                    posix_path = self.__convert_paths_to_posix([os.path.relpath(file, filename)])
                    hashobj.update(posix_path[0].encode("utf-8"))
                    dirhash = hash_file(file, hashobj=hashobj)
                hashlist.append(dirhash)
            else:
                self.logger.error("Internal hashing error, file not found")
                continue

            self.__hashes[filename] = hashlist[-1]

        if check:
            # compare previous hash to new hash
            oldhash = self.schema.get(*keypath, step=step, index=index, field='filehash')
            check_failed = False
            for i, item in enumerate(oldhash):
                if item != hashlist[i]:
                    self.logger.error(f"Hash mismatch for [{keypath}]")
                    check_failed = True
            if check_failed:
                self.error("Hash mismatches detected")

        if update:
            index = str(index)

            set_step = None
            set_index = None
            pernode = self.get(*keypath, field='pernode')
            if pernode == 'required':
                set_step = step
                set_index = index
            elif pernode == 'optional':
                for vals, key_step, key_index in self.schema._getvals(*keypath):
                    if key_step == step and key_index == index and vals:
                        set_step = step
                        set_index = index
                    elif key_step == step and key_index is None and vals:
                        set_step = step
                        set_index = None

            self.set(*keypath, hashlist,
                     step=set_step, index=set_index,
                     field='filehash', clobber=True)

        return hashlist

    ###########################################################################
    def audit_manifest(self):
        '''Verifies the integrity of the post-run compilation manifest.

        Checks the integrity of the chip object implementation flow after
        the run() function has been completed. Errors, warnings, and debug
        messages are reported through the logger object.

        Audit checks performed include:

        * Time stamps
        * File modifications
        * Error and warning policy
        * IP and design origin
        * User access
        * License terms
        * Version checks

        Returns:
            Returns True if the manifest has integrity, else returns False.

        Example:
            >>> chip.audit_manifest()
            Audits the Chip object manifest and returns 0 if successful.

        '''

        return 0

    ###########################################################################
    def calc_area(self, step=None, index=None):
        '''Calculates the area of a rectilinear diearea.

        Uses the shoelace formulate to calculate the design area using
        the (x,y) point tuples from the 'diearea' parameter. If only diearea
        parameter only contains two points, then the first and second point
        must be the lower left and upper right points of the rectangle.
        (Ref: https://en.wikipedia.org/wiki/Shoelace_formula)

        Args:
            step (str): name of the step to calculate the area from
            index (str): name of the step to calculate the area from

        Returns:
            Design area (float).

        Examples:
            >>> area = chip.calc_area()

        '''

        if not step:
            step = self.get('arg', 'step')

        if not index:
            index = self.get('arg', 'index')

        vertices = self.get('constraint', 'outline', step=step, index=index)

        if len(vertices) == 2:
            width = vertices[1][0] - vertices[0][0]
            height = vertices[1][1] - vertices[0][1]
            area = width * height
        else:
            area = 0.0
            for i in range(len(vertices)):
                j = (i + 1) % len(vertices)
                area += vertices[i][0] * vertices[j][1]
                area -= vertices[j][0] * vertices[i][1]
            area = abs(area) / 2

        return area

    ###########################################################################
    def calc_yield(self, step=None, index=None, model='poisson'):
        '''Calculates raw die yield.

        Calculates the raw yield of the design as a function of design area
        and d0 defect density. Calculation can be done based on the poisson
        model (default) or the murphy model. The die area and the d0
        parameters are taken from the chip dictionary.

        * Poisson model: dy = exp(-area * d0/100).
        * Murphy model: dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.

        Args:
            step (str): name of the step use for calculation
            index (str): name of the step use for calculation
            model (string): Model to use for calculation (poisson or murphy)

        Returns:
            Design yield percentage (float).

        Examples:
            >>> yield = chip.calc_yield()
            Yield variable gets yield value based on the chip manifest.
        '''

        pdk = self.get('option', 'pdk')
        d0 = self.get('pdk', pdk, 'd0')
        if d0 is None:
            self.error(f"['pdk', {pdk}, 'd0'] has not been set")
        diearea = self.calc_area(step=step, index=index)

        # diearea is um^2, but d0 looking for cm^2
        diearea = diearea / 10000.0**2

        if model == 'poisson':
            dy = math.exp(-diearea * d0 / 100)
        elif model == 'murphy':
            dy = ((1 - math.exp(-diearea * d0 / 100)) / (diearea * d0 / 100))**2
        else:
            self.error(f'Unknown yield model: {model}')

        return dy

    ##########################################################################
    def calc_dpw(self, step=None, index=None):
        '''Calculates dies per wafer.

        Calculates the gross dies per wafer based on the design area, wafersize,
        wafer edge margin, and scribe lines. The calculation is done by starting
        at the center of the wafer and placing as many complete design
        footprints as possible within a legal placement area.

        Args:
            step (str): name of the step use for calculation
            index (str): name of the step use for calculation

        Returns:
            Number of gross dies per wafer (int).

        Examples:
            >>> dpw = chip.calc_dpw()
            Variable dpw gets gross dies per wafer value based on the chip manifest.
        '''

        # PDK information
        pdk = self.get('option', 'pdk')
        wafersize = self.get('pdk', pdk, 'wafersize')
        edgemargin = self.get('pdk', pdk, 'edgemargin')
        hscribe = self.get('pdk', pdk, 'hscribe')
        vscribe = self.get('pdk', pdk, 'vscribe')

        # Design parameters
        diesize = self.get('constraint', 'outline', step=step, index=index)

        # Convert to mm
        diewidth = (diesize[1][0] - diesize[0][0]) / 1000.0
        dieheight = (diesize[1][1] - diesize[0][1]) / 1000.0

        # Derived parameters
        radius = wafersize / 2 - edgemargin
        stepwidth = diewidth + hscribe
        stepheight = dieheight + vscribe

        # Raster dies out from center until you touch edge margin
        # Work quadrant by quadrant
        dies = 0
        for quad in ('q1', 'q2', 'q3', 'q4'):
            x = 0
            y = 0
            if quad == "q1":
                xincr = stepwidth
                yincr = stepheight
            elif quad == "q2":
                xincr = -stepwidth
                yincr = stepheight
            elif quad == "q3":
                xincr = -stepwidth
                yincr = -stepheight
            elif quad == "q4":
                xincr = stepwidth
                yincr = -stepheight
            # loop through all y values from center
            while math.hypot(0, y) < radius:
                y = y + yincr
                x = xincr
                while math.hypot(x, y) < radius:
                    x = x + xincr
                    dies = dies + 1

        return dies

    ###########################################################################
    def grep(self, args, line):
        """
        Emulates the Unix grep command on a string.

        Emulates the behavior of the Unix grep command that is etched into
        our muscle memory. Partially implemented, not all features supported.
        The function returns None if no match is found.

        Args:
            arg (string): Command line arguments for grep command
            line (string): Line to process

        Returns:
            Result of grep command (string).

        """

        # Quick return if input is None
        if line is None:
            return None

        # Partial list of supported grep options
        options = {
            '-v': False,  # Invert the sense of matching
            '-i': False,  # Ignore case distinctions in patterns and data
            '-E': False,  # Interpret PATTERNS as extended regular expressions.
            '-e': False,  # Safe interpretation of pattern starting with "-"
            '-x': False,  # Select only matches that exactly match the whole line.
            '-o': False,  # Print only the match parts of a matching line
            '-w': False}  # Select only lines containing matches that form whole words.

        # Split into repeating switches and everything else
        match = re.match(r'\s*((?:\-\w\s)*)(.*)', args)

        pattern = match.group(2)

        # Split space separated switch string into list
        switches = match.group(1).strip().split(' ')

        # Find special -e switch update the pattern
        for i in range(len(switches)):
            if switches[i] == "-e":
                if i != (len(switches)):
                    pattern = ' '.join(switches[i + 1:]) + " " + pattern
                    switches = switches[0:i + 1]
                    break
                options["-e"] = True
            elif switches[i] in options.keys():
                options[switches[i]] = True
            elif switches[i] != '':
                self.logger.error(switches[i])

        # REGEX
        # TODO: add all the other optinos
        match = re.search(rf"({pattern})", line)
        if bool(match) == bool(options["-v"]):
            return None
        else:
            return line

    ###########################################################################
    def check_logfile(self, jobname=None, step=None, index='0',
                      logfile=None, display=True):
        '''
        Checks logfile for patterns found in the 'regex' parameter.

        Reads the content of the task's log file and compares the content found
        with the task's 'regex' parameter. The matches are stored in the file
        '<step>.<suffix>' in the current directory. The matches are logged
        if display is set to True.

        Args:
            jobname (str): Job directory name. If None, :keypath:`option, jobname` is used.
            step (str): Task step name ('syn', 'place', etc). If None, :keypath:`arg, step` is used.
            index (str): Task index. Default value is 0. If None, :keypath:`arg, index` is used.
            logfile (str): Path to logfile. If None, the default task logfile is used.
            display (bool): If True, logs matches.

        Returns:
            Dictionary mapping suffixes to number of matches for that suffix's
            regex.

        Examples:
            >>> chip.check_logfile(step='place')
            Searches for regex matches in the place logfile.
        '''

        # Using manifest to get defaults

        flow = self.get('option', 'flow')

        if jobname is None:
            jobname = self.get('option', 'jobname')
        if step is None:
            step = self.get('arg', 'step')
            if step is None:
                raise ValueError("Must provide 'step' or set ['arg', 'step']")
        if index is None:
            index = self.get('arg', 'index')
            if index is None:
                raise ValueError("Must provide 'index' or set ['arg', 'index']")
        if logfile is None:
            logfile = os.path.join(self._getworkdir(jobname=jobname, step=step, index=index),
                                   f'{step}.log')

        tool, task = self._get_tool_task(step, index, flow=flow)

        # Creating local dictionary (for speed)
        # self.get is slow
        checks = {}
        matches = {}
        for suffix in self.getkeys('tool', tool, 'task', task, 'regex'):
            regexes = self.get('tool', tool, 'task', task, 'regex', suffix, step=step, index=index)
            if not regexes:
                continue

            checks[suffix] = {}
            checks[suffix]['report'] = open(f"{step}.{suffix}", "w")
            checks[suffix]['args'] = regexes
            matches[suffix] = 0

        # Order suffixes as follows: [..., 'warnings', 'errors']
        ordered_suffixes = list(filter(lambda key:
                                       key not in ['warnings', 'errors'], checks.keys()))
        if 'warnings' in checks:
            ordered_suffixes.append('warnings')
        if 'errors' in checks:
            ordered_suffixes.append('errors')

        # Looping through patterns for each line
        with sc_open(logfile) as f:
            line_count = sum(1 for _ in f)
            right_align = len(str(line_count))
            for suffix in ordered_suffixes:
                # Start at the beginning of file again
                f.seek(0)
                for num, line in enumerate(f, start=1):
                    string = line
                    for item in checks[suffix]['args']:
                        if string is None:
                            break
                        else:
                            string = self.grep(item, string)
                    if string is not None:
                        matches[suffix] += 1
                        # always print to file
                        line_with_num = f'{num: >{right_align}}: {string.strip()}'
                        print(line_with_num, file=checks[suffix]['report'])
                        # selectively print to display
                        if display:
                            if suffix == 'errors':
                                self.logger.error(line_with_num)
                            elif suffix == 'warnings':
                                self.logger.warning(line_with_num)
                            else:
                                self.logger.info(f'{suffix}: {line_with_num}')

        for suffix in ordered_suffixes:
            self.logger.info(f'Number of {suffix}: {matches[suffix]}')
            checks[suffix]['report'].close()

        return matches

    ###########################################################################
    def _dashboard(self, wait=True, port=None, graph_chips=None):
        '''
        Open a session of the dashboard.

        The dashboard can be viewed in any webbrowser and can be accessed via:
        http://localhost:8501/

        Args:
            wait (bool): If True, this call will wait in this method
                until the dashboard has been closed.
            port (int): An integer specifying which port to display the
                dashboard to.
            graph_chips (list): A list of dictionaries of the format
                {'chip': chip object, 'name': chip name}

        Examples:
            >>> chip._dashboard()
            Opens a sesison of the dashboard.
        '''
        dash = Dashboard(self, port=port, graph_chips=graph_chips)
        dash.open_dashboard()
        if wait:
            try:
                dash.wait()
            except KeyboardInterrupt:
                dash._sleep()
            finally:
                dash.stop()
            return None

        return dash

    ###########################################################################
    def summary(self, show_all_indices=False, generate_image=True, generate_html=True):
        '''
        Prints a summary of the compilation manifest.

        Metrics from the flowgraph nodes, or from/to parameter if
        defined, are printed out on a per step basis. All metrics from the
        metric dictionary with weights set in the flowgraph dictionary are
        printed out.

        Args:
            show_all_indices (bool): If True, displays metrics for all indices
                of each step. If False, displays metrics only for winning
                indices.
            generate_image (bool): If True, generates a summary image featuring
                a layout screenshot and a subset of metrics. Requires that the
                current job has an ending node that generated a PNG file.
            generate_html (bool): If True, generates an HTML report featuring a
                metrics summary table and manifest tree view. The report will
                include a layout screenshot if the current job has an ending node
                that generated a PNG file.

        Examples:
            >>> chip.summary()
            Prints out a summary of the run to stdout.
        '''

        # display whole flowgraph if no from/to specified
        flow = self.get('option', 'flow')
        nodes_to_execute = get_executed_nodes(self, flow)

        _show_summary_table(self, flow, nodes_to_execute, show_all_indices=show_all_indices)

        # Create a report for the Chip object which can be viewed in a web browser.
        # Place report files in the build's root directory.
        work_dir = self._getworkdir()
        if os.path.isdir(work_dir):
            # Mark file paths where the reports can be found if they were generated.
            results_html = os.path.join(work_dir, 'report.html')
            results_img = os.path.join(work_dir, f'{self.design}.png')

            if generate_image:
                _generate_summary_image(self, results_img)

            if generate_html:
                _generate_html_report(self, flow, nodes_to_execute, results_html)

            # Try to open the results and layout only if '-nodisplay' is not set.
            # Priority: PNG, PDF, HTML.
            if (not self.get('option', 'nodisplay')):
                if os.path.isfile(results_img):
                    _open_summary_image(results_img)
                elif os.path.isfile(results_html):
                    _open_html_report(self, results_html)

    ###########################################################################
    def clock(self, pin, period, jitter=0, mode='global'):
        """
        Clock configuration helper function.

        A utility function for setting all parameters associated with a
        single clock definition in the schema.

        The method modifies the following schema parameters:

        ['datasheet', 'pin', pin, 'type', mode]
        ['datasheet', 'pin', pin, 'tperiod', mode]
        ['datasheet', 'pin', pin, 'tjitter', mode]

        Args:
            pin (str): Full hierarchical path to clk pin.
            period (float): Clock period specified in ns.
            jitter (float): Clock jitter specified in ns.
            mode (str): Mode of operation (from datasheet).

        Examples:
            >>> chip.clock('clk', period=1.0)
           Create a clock named 'clk' with a 1.0ns period.
        """

        self.set('datasheet', 'pin', pin, 'type', mode, 'clock')

        period_range = (period * 1e-9, period * 1e-9, period * 1e-9)
        self.set('datasheet', 'pin', pin, 'tperiod', mode, period_range)

        jitter_range = (jitter * 1e-9, jitter * 1e-9, jitter * 1e-9)
        self.set('datasheet', 'pin', pin, 'tjitter', mode, jitter_range)

    ###########################################################################
    def node(self, flow, step, task, index=0):
        '''
        Creates a flowgraph node.

        Creates a flowgraph node by binding a step to a tool specific task.
        A tool can be an external executable or one of the built in functions
        in the SiliconCompiler framework). Built in functions include: minimum,
        maximum, join, mux, verify. The task is set to 'step' if unspecified.

        The method modifies the following schema parameters:

        * ['flowgraph', flow, step, index, 'tool', tool]
        * ['flowgraph', flow, step, index, 'task', task]
        * ['flowgraph', flow, step, index, 'task', taskmodule]
        * ['flowgraph', flow, step, index, 'weight', metric]

        Args:
            flow (str): Flow name
            step (str): Step name
            task (module/str): Task to associate with this node
            index (int): Step index

        Examples:
            >>> import siliconcomiler.tools.openroad.place as place
            >>> chip.node('asicflow', 'apr_place', place, index=0)
            Creates a 'place' task with step='apr_place' and index=0 and binds it to the
            'openroad' tool.
        '''

        if step in (Schema.GLOBAL_KEY, 'default', 'sc_collected_files'):
            self.error(f'Illegal step name: {step} is reserved')
            return

        index = str(index)

        # Determine task name and module
        task_module = None
        if (isinstance(task, str)):
            task_module = task
        elif inspect.ismodule(task):
            task_module = task.__name__
            self.modules[task_module] = task
        else:
            self.error(f"{task} is not a string or module and cannot be used to setup a task.",
                       fatal=True)

        task_parts = task_module.split('.')
        if len(task_parts) < 2:
            self.error(f"{task} is not a valid task, it must be associated with a tool "
                       "'<tool>.<task>'.", fatal=True)
        tool_name, task_name = task_parts[-2:]

        # bind tool to node
        self.set('flowgraph', flow, step, index, 'tool', tool_name)
        self.set('flowgraph', flow, step, index, 'task', task_name)
        self.set('flowgraph', flow, step, index, 'taskmodule', task_module)

        # set default weights
        for metric in self.getkeys('metric'):
            self.set('flowgraph', flow, step, index, 'weight', metric, 0)

    ###########################################################################
    def edge(self, flow, tail, head, tail_index=0, head_index=0):
        '''
        Creates a directed edge from a tail node to a head node.

        Connects the output of a tail node with the input of a head node by
        setting the 'input' field of the head node in the schema flowgraph.

        The method modifies the following parameters:

        ['flowgraph', flow, head, str(head_index), 'input']

        Args:
            flow (str): Name of flow
            tail (str): Name of tail node
            head (str): Name of head node
            tail_index (int): Index of tail node to connect
            head_index (int): Index of head node to connect

        Examples:
            >>> chip.edge('place', 'cts')
            Creates a directed edge from place to cts.
        '''
        head_index = str(head_index)
        tail_index = str(tail_index)

        for step in (head, tail):
            if step in (Schema.GLOBAL_KEY, 'default'):
                self.error(f'Illegal step name: {step} is reserved')
                return

        tail_node = (tail, tail_index)
        if tail_node in _get_flowgraph_node_inputs(self, flow, (head, head_index)):
            self.logger.warning(f'Edge from {tail}{tail_index} to {head}{head_index} already '
                                'exists, skipping')
            return

        self.add('flowgraph', flow, head, head_index, 'input', tail_node)

    ###########################################################################
    def _remove_node(self, flow, step, index=None):
        '''
        Remove a flowgraph node.

        Args:
            flow (str): Flow name
            step (str): Step name
            index (int): Step index
        '''
        if index is None:
            # Iterate over all indexes
            for index in self.getkeys('flowgraph', flow, step):
                self._remove_node(flow, step, index)
            return

        index = str(index)

        # Save input edges
        node = (step, index)
        node_inputs = self.get('flowgraph', flow, step, index, 'input')
        self.schema._remove('flowgraph', flow, step, index)

        if len(self.getkeys('flowgraph', flow, step)) == 0:
            self.schema._remove('flowgraph', flow, step)

        for flow_step in self.getkeys('flowgraph', flow):
            for flow_index in self.getkeys('flowgraph', flow, flow_step):
                inputs = self.get('flowgraph', flow, flow_step, flow_index, 'input')
                if node in inputs:
                    inputs = [inode for inode in inputs if inode != node]
                    inputs.extend(node_inputs)
                    self.set('flowgraph', flow, flow_step, flow_index, 'input', set(inputs))

    ###########################################################################
    def graph(self, flow, subflow, name=None):
        '''
        Instantiates a named flow as a graph in the current flowgraph.

        Args:
            flow (str): Name of current flow.
            subflow (str): Name of flow to instantiate
            name (str): Name of instance

        Examples:
            >>> chip.graph('asicflow')
            Instantiates a flow named 'asicflow'.
        '''
        for step in self.getkeys('flowgraph', subflow):
            # uniquify each step
            if name is None:
                newstep = step
            else:
                newstep = name + "." + step

            for keys in self.allkeys('flowgraph', subflow, step):
                val = self.get('flowgraph', subflow, step, *keys)
                self.set('flowgraph', flow, newstep, *keys, val)

            if name is None:
                continue

            for index in self.getkeys('flowgraph', flow, newstep):
                # rename inputs
                all_inputs = _get_flowgraph_node_inputs(self, flow, (newstep, index))
                self.set('flowgraph', flow, newstep, index, 'input', [])
                for in_step, in_index in all_inputs:
                    newin = name + "." + in_step
                    self.add('flowgraph', flow, newstep, index, 'input', (newin, in_index))

    ###########################################################################
    def pipe(self, flow, plan):
        '''
        Creates a pipeline based on an order list of key values pairs.
        '''

        prevstep = None
        for item in plan:
            step = list(item.keys())[0]
            task = list(item.values())[0]
            self.node(flow, step, task)
            if prevstep:
                self.edge(flow, prevstep, step)
            prevstep = step

    def clean_build_dir(self):
        if self.get('record', 'remoteid'):
            return

        if self.get('arg', 'step'):
            return

        if self.get('option', 'resume'):
            for step, index in gather_resume_failed_nodes(self,
                                                          self.get('option', 'flow'),
                                                          self.nodes_to_execute()):
                # Remove stale outputs that will be rerun
                cur_node_dir = self._getworkdir(step=step, index=index)
                if os.path.isdir(cur_node_dir):
                    shutil.rmtree(cur_node_dir)
        elif self.get('option', 'from'):
            # Remove stale outputs that will be rerun
            for step, index in self.nodes_to_execute():
                cur_node_dir = self._getworkdir(step=step, index=index)
                if os.path.isdir(cur_node_dir):
                    shutil.rmtree(cur_node_dir)
        else:
            # If no step or nodes to start from were specified, the whole flow is being run
            # start-to-finish. Delete the build dir to clear stale results.
            cur_job_dir = self._getworkdir()
            if os.path.isdir(cur_job_dir):
                shutil.rmtree(cur_job_dir)

    ###########################################################################
    def run(self):
        '''
        Executes tasks in a flowgraph.

        The run function sets up tools and launches runs for every node
        in the flowgraph starting with 'from' steps and ending at 'to' steps.
        From/to are taken from the schema from/to parameters if defined,
        otherwise from/to are defined as the entry/exit steps of the flowgraph.
        Before starting the process, tool modules are loaded and setup up for each
        step and index based on on the schema eda dictionary settings.
        Once the tools have been set up, the manifest is checked using the
        check_manifest() function and files in the manifest are hashed based
        on the 'hashmode' schema setting.

        Once launched, each process waits for preceding steps to complete,
        as defined by the flowgraph 'inputs' parameter. Once a all inputs
        are ready, previous steps are checked for errors before the
        process entered a local working directory and starts to run
        a tool or to execute a built in Chip function.

        Fatal errors within a step/index process cause all subsequent
        processes to exit before start, returning control to the the main
        program which can then exit.

        Examples:
            >>> run()
            Runs the execution flow defined by the flowgraph dictionary.
        '''

        sc_runner(self)

    ###########################################################################
    def nodes_to_execute(self, flow=None):
        '''
        Returns an ordered list of flowgraph nodes which will be executed.
        This takes the from/to options into account if flow is the current flow or None.

        Returns:
            A list of nodes that will get executed during run() (or a specific flow).

        Example:
            >>> nodes = chip.nodes_to_execute()
        '''
        if flow is None:
            flow = self.get('option', 'flow')

        from_nodes = _get_execution_entry_nodes(self, flow)
        to_nodes = _get_execution_exit_nodes(self, flow)
        prune_nodes = self.get('option', 'prune')
        if from_nodes == to_nodes:
            return list(filter(lambda node: node not in prune_nodes, from_nodes))
        return _nodes_to_execute(self, flow, set(from_nodes), set(to_nodes), set(prune_nodes))

    ###########################################################################
    def show(self, filename=None, screenshot=False, extension=None):
        '''
        Opens a graphical viewer for the filename provided.

        The show function opens the filename specified using a viewer tool
        selected based on the file suffix and the 'showtool' schema setup.  The
        'showtool' parameter binds tools with file suffixes, enabling the
        automated dynamic loading of tool setup functions. Display settings and
        technology settings for viewing the file are read from the in-memory
        chip object schema settings. All temporary render and display files are
        saved in the <build_dir>/_show_<jobname> directory.

        Args:
            filename (path): Name of file to display
            screenshot (bool): Flag to indicate if this is a screenshot or show
            extension (str): extension of file to show

        Examples:
            >>> show('build/oh_add/job0/write_gds/0/outputs/oh_add.gds')
            Displays gds file with a viewer assigned by 'showtool'
        '''

        sc_step = self.get('arg', 'step')
        sc_index = self.get('arg', 'index')
        sc_job = self.get('option', 'jobname')

        has_filename = filename is not None
        # Finding last layout if no argument specified
        if filename is None:
            self.logger.info('Searching build directory for layout to show.')

            search_nodes = []
            if sc_step and sc_index:
                search_nodes.append((sc_step, sc_index))
            elif sc_step:
                for check_step, check_index in self.nodes_to_execute(self.get('option', 'flow')):
                    if sc_step == check_step:
                        search_nodes.append((check_step, check_index))
            else:
                for nodes in _get_flowgraph_execution_order(self,
                                                            self.get('option', 'flow'),
                                                            reverse=True):
                    search_nodes.extend(nodes)

            for ext in self.getkeys('option', 'showtool'):
                if extension and extension != ext:
                    continue
                for step, index in search_nodes:
                    for search_ext in (ext, f"{ext}.gz"):
                        filename = self.find_result(search_ext,
                                                    step=step,
                                                    index=index,
                                                    jobname=sc_job)
                        if filename:
                            sc_step = step
                            sc_index = index
                            break
                    if filename:
                        break
                if filename:
                    break

        if filename is None:
            self.logger.error('Unable to automatically find layout in build directory.')
            self.logger.error('Try passing in a full path to show() instead.')
            return False

        if not has_filename:
            self.logger.info(f'Showing file {filename}')

        filepath = os.path.abspath(filename)

        # Check that file exists
        if not os.path.exists(filepath):
            self.logger.error(f"Invalid filepath {filepath}.")
            return False

        filetype = utils.get_file_ext(filepath)

        if filetype not in self.getkeys('option', 'showtool'):
            self.logger.error(f"Filetype '{filetype}' not set up in 'showtool' parameter.")
            return False

        saved_config = self.schema.copy()

        taskname = 'show'
        if screenshot:
            taskname = 'screenshot'

        try:
            from siliconcompiler.flows import showflow
            self.use(showflow, filetype=filetype, screenshot=screenshot)
        except Exception as e:
            self.logger.debug(f"Flow setup failed: {e}")
            # restore environment
            self.schema = saved_config
            return False

        # Override environment
        self.set('option', 'flow', 'showflow', clobber=True)
        self.set('option', 'track', False, clobber=True)
        self.set('option', 'hash', False, clobber=True)
        self.set('option', 'nodisplay', False, clobber=True)
        self.set('option', 'flowcontinue', True, clobber=True)
        self.set('option', 'quiet', False, clobber=True)
        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)
        self.unset('option', 'to')
        self.unset('option', 'prune')
        self.unset('option', 'from')
        # build new job name
        self.set('option', 'jobname', f'_{taskname}_{sc_job}_{sc_step}{sc_index}', clobber=True)

        # Setup in step/index variables
        for (step, index) in _get_flowgraph_nodes(self, 'showflow'):
            if step != taskname:
                continue
            show_tool, _ = self._get_tool_task(step, index, flow='showflow')
            self.set('tool', show_tool, 'task', taskname, 'var', 'show_filetype', filetype,
                     step=step, index=index)
            self.set('tool', show_tool, 'task', taskname, 'var', 'show_filepath', filepath,
                     step=step, index=index)
            if sc_step:
                self.set('tool', show_tool, 'task', taskname, 'var', 'show_step', sc_step,
                         step=step, index=index)
            if sc_index:
                self.set('tool', show_tool, 'task', taskname, 'var', 'show_index', sc_index,
                         step=step, index=index)
            if sc_job:
                self.set('tool', show_tool, 'task', taskname, 'var', 'show_job', sc_job,
                         step=step, index=index)

        # run show flow
        try:
            self.run()
            if screenshot:
                step, index = _get_flowgraph_exit_nodes(self, flow='showflow')[0]
                success = self.find_result('png', step=step, index=index)
            else:
                success = True
        except SiliconCompilerError as e:
            self.logger.error(e)
            success = False

        # restore environment
        self.schema = saved_config

        return success

    ############################################################################
    # Chip helper Functions
    ############################################################################
    def _getexe(self, tool, step, index):
        path = self.get('tool', tool, 'path', step=step, index=index)
        exe = self.get('tool', tool, 'exe')
        if exe is None:
            return None

        syspath = os.getenv('PATH', os.defpath)
        if path:
            # Prepend 'path' schema var to system path
            syspath = self._resolve_env_vars(path) + os.pathsep + syspath

        fullexe = shutil.which(exe, path=syspath)

        return fullexe

    #######################################
    def _safecompare(self, value, op, goal):
        # supported relational operations
        # >, >=, <=, <. ==, !=
        if op == ">":
            return bool(value > goal)
        elif op == ">=":
            return bool(value >= goal)
        elif op == "<":
            return bool(value < goal)
        elif op == "<=":
            return bool(value <= goal)
        elif op == "==":
            return bool(value == goal)
        elif op == "!=":
            return bool(value != goal)
        else:
            self.error(f"Illegal comparison operation {op}")

    #######################################
    def _is_builtin(self, tool, task):
        '''
        Check if tool and task is a builtin
        '''
        return tool == 'builtin'

    #######################################
    def _getcollectdir(self, jobname=None):
        '''
        Get absolute path to collected files directory
        '''

        return os.path.join(self._getworkdir(jobname=jobname), 'sc_collected_files')

    #######################################
    def _getworkdir(self, jobname=None, step=None, index=None):
        '''
        Get absolute path to work directory for a given step/index,
        if step/index not given, job directory is returned
        '''

        if jobname is None:
            jobname = self.get('option', 'jobname')

        dirlist = [self.cwd,
                   self.get('option', 'builddir'),
                   self.get('design'),
                   jobname]

        # Return jobdirectory if no step defined
        # Return index 0 by default
        if step is not None:
            dirlist.append(step)

            if not index:
                index = '0'

            dirlist.append(index)

        return os.path.join(*dirlist)

    #######################################
    def _resolve_env_vars(self, filepath):
        if not filepath:
            return None

        env_save = os.environ.copy()
        for env in self.getkeys('option', 'env'):
            os.environ[env] = self.get('option', 'env', env)
        resolved_path = os.path.expandvars(filepath)
        os.environ.clear()
        os.environ.update(env_save)

        # variables that don't exist in environment get ignored by `expandvars`,
        # but we can do our own error checking to ensure this doesn't result in
        # silent bugs
        envvars = re.findall(r'\$(\w+)', resolved_path)
        for var in envvars:
            self.logger.warning(f'Variable {var} in {filepath} not defined in environment')

        return resolved_path

    #######################################
    def _get_imported_filename(self, pathstr, package=None):
        ''' Utility to map collected file to an unambiguous name based on its path.

        The mapping looks like:
        path/to/file.ext => file_<md5('path/to/file.ext')>.ext
        '''
        path = pathlib.PurePosixPath(pathstr)
        ext = ''.join(path.suffixes)

        # strip off all file suffixes to get just the bare name
        barepath = path
        while barepath.suffix:
            barepath = pathlib.PurePosixPath(barepath.stem)
        filename = str(barepath.parts[-1])

        if not package:
            package = ''
        else:
            package = f'{package}:'
        path_to_hash = f'{package}{str(path)}'
        pathhash = hashlib.sha1(path_to_hash.encode('utf-8')).hexdigest()

        return f'{filename}_{pathhash}{ext}'

    def _get_in_job(self, step, index):
        # Get name of job that provides input to a given step and index.
        job = self.get('option', 'jobname')
        in_job = job
        if step in self.getkeys('option', 'jobinput'):
            if index in self.getkeys('option', 'jobinput', step):
                in_job = self.get('option', 'jobinput', step, index)

        return in_job

    def error(self, msg, fatal=False):
        '''Raises error.

        If fatal is False and :keypath:`option, continue` is set to True, this
        will log an error and set an internal error flag that will cause run()
        to quit. Otherwise, this will raise a SiliconCompilerError.

        Args:
            msg (str): Message associated with error
            fatal (bool): Whether error is always fatal
        '''

        if hasattr(self, 'logger'):
            self.logger.error(msg)

        if not fatal:
            # Keep all get() calls in this block so we can still call with
            # fatal=True before the logger exists
            step = self.get('arg', 'step')
            index = self.get('arg', 'index')
            if self.schema.get('option', 'continue', step=step, index=index):
                self._error = True
                return

        raise SiliconCompilerError(msg) from None

    #######################################
    def _record_metric(self, step, index, metric, value, source, source_unit=None):
        '''
        Records a metric from a given step and index.

        This function ensures the metrics are recorded in the correct units
        as specified in the schema, additionally, this will record the source
        of the value if provided.

        Args:
            step (str): step to record the metric into
            index (str): index to record the metric into
            metric (str): metric to record
            value (float/int): value of the metric that is being recorded
            source (str): file the value came from
            source_unit (str): unit of the value, if not provided it is assumed to have no units

        Examples:
            >>> chip._record_metric('floorplan', '0', 'cellarea', 500.0, 'reports/metrics.json', \\
                source_units='um^2')
            Records the metric cell area under 'floorplan0' and notes the source as
            'reports/metrics.json'
        '''
        metric_unit = None
        if self.schema._has_field('metric', metric, 'unit'):
            metric_unit = self.get('metric', metric, field='unit')

        if metric_unit:
            value = units.convert(value, from_unit=source_unit, to_unit=metric_unit)

        self.set('metric', metric, value, step=step, index=index)

        if source:
            flow = self.get('option', 'flow')
            tool, task = self._get_tool_task(step, index, flow=flow)

            self.add('tool', tool, 'task', task, 'report', metric, source, step=step, index=index)

    #######################################
    def _clear_metric(self, step, index, metric, preserve=None):
        '''
        Helper function to clear metrics records
        '''

        # This function is often called in a loop; don't clear
        # metrics which the caller wants to preserve.
        if preserve and metric in preserve:
            return

        flow = self.get('option', 'flow')
        tool, task = self._get_tool_task(step, index, flow=flow)

        self.unset('metric', metric, step=step, index=index)
        self.unset('tool', tool, 'task', task, 'report', metric, step=step, index=index)

    #######################################
    def _clear_record(self, step, index, record, preserve=None):
        '''
        Helper function to clear record parameters
        '''

        # This function is often called in a loop; don't clear
        # records which the caller wants to preserve.
        if preserve and record in preserve:
            return

        if self.get('record', record, field='pernode') == 'never':
            self.unset('record', record)
        else:
            self.unset('record', record, step=step, index=index)

    #######################################
    def __getstate__(self):
        # Called when generating a serial stream of the object
        attributes = self.__dict__.copy()

        # Modules are not serializable, so save without cache
        attributes['modules'] = {}

        # We have to remove the chip's logger before serializing the object
        # since the logger object is not serializable.
        del attributes['logger']
        return attributes

    #######################################
    def __setstate__(self, state):
        self.__dict__ = state

        # Reinitialize logger on restore
        self._init_logger()
        self.schema._init_logger(self.logger)
