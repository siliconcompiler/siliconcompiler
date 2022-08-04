# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
import base64
import time
import datetime
import multiprocessing
import tarfile
import traceback
import asyncio
from subprocess import run, PIPE
import os
import glob
import pathlib
import sys
import gzip
import re
import json
import logging
import hashlib
import shutil
import copy
import importlib
import textwrap
import math
import pandas
import yaml
import graphviz
import time
import uuid
import shlex
import platform
import getpass
import csv
import distro
import netifaces
import webbrowser
import codecs
import packaging.version
import packaging.specifiers
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from timeit import default_timer as timer
from siliconcompiler.client import *
from siliconcompiler.schema import *
from siliconcompiler.scheduler import _deferstep
from siliconcompiler import leflib
from siliconcompiler import utils
from siliconcompiler import _metadata
import psutil

class TaskStatus():
    # Could use Python 'enum' class here, but that doesn't work nicely with
    # schema.
    PENDING = 'pending'
    SUCCESS = 'success'
    ERROR = 'error'

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
        self.cwd = os.getcwd()
        self._error = False
        self.cfg = schema_cfg()
        # The 'status' dictionary can be used to store ephemeral config values.
        # Its contents will not be saved, and can be set by parent scripts
        # such as a web server or supervisor process. Currently supported keys:
        # * 'jobhash': A hash or UUID which can identify jobs in a larger system.
        # * 'remote_cfg': Dictionary containing remote server configurations
        #                 (address, credentials, etc.)
        # * 'slurm_account': User account ID in a connected slurm HPC cluster.
        # * 'slurm_partition': Name of the partition in which a task should run
        #                      on a connected slurm HPC cluster.
        # * 'watchdog': Activity-monitoring semaphore for jobs scheduled on an
        #               HPC cluster; expects a 'threading.Event'-like object.
        # * 'max_fs_bytes': A limit on how much disk space a job is allowed
        #                   to consume in a connected HPC cluster's storage.
        self.status = {}

        self.builtin = ['minimum','maximum',
                        'nop', 'mux', 'join', 'verify']

        # We set 'design' and 'loglevel' directly in the config dictionary
        # because of a chicken-and-egg problem: self.set() relies on the logger,
        # but the logger relies on these values.
        self.cfg['design']['value'] = design
        if loglevel:
            self.cfg['option']['loglevel']['value'] = loglevel

        self._init_logger()

        self._loaded_modules = {
            'flows': [],
            'pdks': [],
            'libs': [],
            'checklists': []
        }

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
    def _init_logger(self, step=None, index=None, in_run=False):

        self.logger = logging.getLogger(uuid.uuid4().hex)

        # Don't propagate log messages to "root" handler (we get duplicate
        # messages without this)
        # TODO: this prevents us from being able to capture logs with pytest:
        # we should revisit it
        self.logger.propagate = False

        loglevel = self.get('option', 'loglevel')

        if loglevel=='DEBUG':
            prefix = '| %(levelname)-7s | %(funcName)-10s | %(lineno)-4s'
        else:
            prefix = '| %(levelname)-7s'

        if in_run:
            flow = self.get('option', 'flow')

            # Figure out how wide to make step and index fields
            max_step_len = 2
            max_index_len = 2
            for future_step in self.getkeys('flowgraph', flow):
                max_step_len = max(len(future_step) + 1, max_step_len)
                for future_index in self.getkeys('flowgraph', flow, future_step):
                    max_index_len = max(len(future_index) + 1, max_index_len)

            jobname = self.get('option', 'jobname')

            if step is None:
                step = '-' * max(max_step_len // 4, 1)
            if index is None:
                index = '-' * max(max_index_len // 4, 1)

            run_info = f'%s  | %-{max_step_len}s | %-{max_index_len}s' % (jobname, step, index)
            logformat = ' | '.join([prefix, run_info, '%(message)s'])
        else:
            logformat = ' | '.join([prefix, '%(message)s'])

        handler = logging.StreamHandler()
        formatter = logging.Formatter(logformat)

        handler.setFormatter(formatter)

        # Clear any existing handlers so we don't end up with duplicate messages
        # if repeat calls to _init_logger are made
        if len(self.logger.handlers) > 0:
            self.logger.handlers.clear()

        self.logger.addHandler(handler)
        self.logger.setLevel(loglevel)

    ###########################################################################
    def _deinit_logger(self):
        self.logger = None

    ###########################################################################
    def _get_switches(self, *keypath):
        '''Helper function for parsing switches and metavars for a keypath.'''
        #Switch field fully describes switch format
        switch = self.get(*keypath, field='switch')

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

    ###########################################################################
    def create_cmdline(self, progname, description=None, switchlist=None, input_map=None):
        """Creates an SC command line interface.

        Exposes parameters in the SC schema as command line switches,
        simplifying creation of SC apps with a restricted set of schema
        parameters exposed at the command line. The order of command
        line switch settings parsed from the command line is as follows:

         1. loglevel
         2. fpga_partname
         3. load_target('target')
         4. read_manifest([cfg])
         5. all other switches

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
                source arguments to ['input', ...] keypaths based on their file
                extension. If None, the CLI will not accept positional source
                arguments.

        Examples:
            >>> chip.create_cmdline(progname='sc-show',switchlist=['-input','-cfg'])
            Creates a command line interface for 'sc-show' app.

            >>> chip.create_cmdline(progname='sc', input_map={'v': 'verilog'})
            All sources ending in .v will be stored in ['input', 'verilog']
        """

        # Argparse
        parser = argparse.ArgumentParser(prog=progname,
                                         prefix_chars='-+',
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description=description)

        # Get all keys from global dictionary or override at command line
        allkeys = self.getkeys()

        # Iterate over all keys to add parser arguments
        for keypath in allkeys:
            #Fetch fields from leaf cell
            helpstr = self.get(*keypath, field='shorthelp')
            typestr = self.get(*keypath, field='type')

            # argparse 'dest' must be a string, so join keypath with commas
            dest = '_'.join(keypath)

            switchstrs, metavar = self._get_switches(*keypath)

            # Three switch types (bool, list, scalar)
            if not switchlist or any(switch in switchlist for switch in switchstrs):
                if typestr == 'bool':
                    parser.add_argument(*switchstrs,
                                        nargs='?',
                                        metavar=metavar,
                                        dest=dest,
                                        const='true',
                                        help=helpstr,
                                        default=argparse.SUPPRESS)
                #list type arguments
                elif re.match(r'\[', typestr):
                    #all the rest
                    parser.add_argument(*switchstrs,
                                        metavar=metavar,
                                        dest=dest,
                                        action='append',
                                        help=helpstr,
                                        default=argparse.SUPPRESS)
                else:
                    #all the rest
                    parser.add_argument(*switchstrs,
                                        metavar=metavar,
                                        dest=dest,
                                        help=helpstr,
                                        default=argparse.SUPPRESS)

        if input_map is not None:
            parser.add_argument('source',
                                nargs='*',
                                help='Input files with filetype inferred by extension')

        #Preprocess sys.argv to enable linux commandline switch formats
        #(gcc, verilator, etc)
        scargs = []

        # Iterate from index 1, otherwise we end up with script name as a
        # 'source' positional argument
        for item in sys.argv[1:]:
            #Split switches with one character and a number after (O0,O1,O2)
            opt = re.match(r'(\-\w)(\d+)', item)
            #Split assign switches (-DCFG_ASIC=1)
            assign = re.search(r'(\-\w)(\w+\=\w+)', item)
            #Split plusargs (+incdir+/path)
            plusarg = re.search(r'(\+\w+\+)(.*)', item)
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
                scargs.append(item)

        parser.add_argument('-version', action='version', version=_metadata.version)

        #Grab argument from pre-process sysargs
        cmdargs = vars(parser.parse_args(scargs))

        # Print banner
        print(_metadata.banner)
        print("Authors:", ", ".join(_metadata.authors))
        print("Version:", _metadata.version, "\n")
        print("-"*80)

        os.environ["COLUMNS"] = '80'

        # 1. set loglevel if set at command line
        if 'option_loglevel' in cmdargs.keys():
            self.logger.setLevel(cmdargs['option_loglevel'])

        # 2. read in target if set
        if 'option_target' in cmdargs.keys():
            if 'arg_pdk' in cmdargs.keys():
                raise NotImplementedError("NOT IMPLEMENTED: ['arg', 'pdk'] parameter with target")
            if 'arg_flow' in cmdargs.keys():
                raise NotImplementedError("NOT IMPLEMENTED: ['arg', 'flow'] parameter with target")
            if 'fpga_partname' in cmdargs.keys():
                self.set('fpga', 'partname', cmdargs['fpga_partname'], clobber=True)
            # running target command
            self.load_target(cmdargs['option_target'])

        # 4. read in all cfg files
        if 'option_cfg' in cmdargs.keys():
            for item in cmdargs['option_cfg']:
                self.read_manifest(item, clobber=True, clear=True)

        # Map sources to ['input'] keypath.
        if 'source' in cmdargs:
            for source in cmdargs['source']:
                _, ext = os.path.splitext(source)
                ext = ext.lstrip('.')
                if ext in input_map:
                    filetype = input_map[ext]
                    if self.valid('input', filetype, quiet=True):
                        self.add('input', filetype, source)
                    else:
                        self.set('input', filetype, source)
                    self.logger.info(f'Source {source} inferred as {filetype}')
                else:
                    self.logger.warning('Unable to infer input type for '
                        f'{source} based on file extension, ignoring. Use the '
                        '-input flag to provide it explicitly.')
            # we don't want to handle this in the next loop
            del cmdargs['source']

        # 5. Cycle through all command args and write to manifest
        for dest, vals in cmdargs.items():
            keypath = dest.split('_')

            # Turn everything into a list for uniformity
            if not isinstance(vals, list):
                vals = [vals]

            # Cycle through all items
            for item in vals:
                # Hack to handle the fact that we want optmode stored with an 'O'
                # prefix.
                if keypath == ['option', 'optmode']:
                    item = 'O' + item

                num_free_keys = keypath.count('default')

                if len(item.split(' ')) < num_free_keys + 1:
                    # Error out if value provided doesn't have enough words to
                    # fill in 'default' keys.
                    switches, metavar = self._get_switches(*keypath)
                    switchstr = '/'.join(switches)
                    self.error(f'Invalid value {item} for switch {switchstr}. Expected format {metavar}.', fatal=True)

                # We replace 'default' in keypath with first N words in provided
                # value. Remainder is the actual value we want to store in the
                # parameter.
                *free_keys, val = item.split(' ', num_free_keys)
                args = [free_keys.pop(0) if key == 'default' else key for key in keypath]

                # Storing in manifest
                self.logger.info(f"Command line argument entered: {args} Value: {val}")
                typestr = self.get(*keypath, field='type')
                if typestr.startswith('['):
                    if self.valid(*args, quiet=True):
                        self.add(*args, val)
                    else:
                        self.set(*args, val, clobber=True)
                else:
                    self.set(*args, val, clobber=True)

    #########################################################################
    def find_function(self, modulename, funcname, moduletype=None):
        '''
        Returns a function attribute from a module on disk.

        Searches the SC root directory and the 'scpath' parameter for the
        modulename provided and imports the module if found. If the funcname
        provided is found in the module, a callable function attribute is
        returned, otherwise None is returned.

        The function assumes the following directory structure:

        * tools/modulename/modulename.py
        * flows/modulename.py
        * pdks/modulname.py

        If the moduletype is None, the module paths are search in the
        order: 'targets'->'flows'->'tools'->'pdks'->'libs'->'checklists'):


        Supported functions include:

        * targets (make_docs, setup)
        * pdks (make_docs, setup)
        * flows (make_docs, setup)
        * tools (make_docs, setup, check_version, runtime_options,
          pre_process, post_process)
        * libs (make_docs, setup)

        Args:
            modulename (str): Name of module to import.
            funcname (str): Name of the function to find within the module.
            moduletype (str): Type of module (flows, pdks, libs, checklists, targets).

        Examples:
            >>> setup_pdk = chip.find_function('freepdk45', 'setup', 'pdks')
            >>> setup_pdk()
            Imports the freepdk45 module and runs the setup_pdk function

        '''

        # module search path depends on modtype
        if moduletype is None:
            for item in ('targets', 'flows', 'tools', 'pdks', 'libs', 'checklists'):
                fullpath = self.find_function(modulename, funcname, module_type=item)
                if fullpath:
                    break
        elif moduletype in ('targets','flows', 'pdks', 'libs'):
            fullpath = self._find_sc_file(f"{moduletype}/{modulename}.py", missing_ok=True)
        elif moduletype in ('tools', 'checklists'):
            fullpath = self._find_sc_file(f"{moduletype}/{modulename}/{modulename}.py", missing_ok=True)
        else:
            self.error(f"Illegal module type '{moduletype}'.")
            return None

        if not fullpath:
            self.error(f'Could not find module {modulename}')
            return None

        # try loading module if found
        self.logger.debug(f"Loading function '{funcname}' from module '{modulename}'")

        try:
            spec = importlib.util.spec_from_file_location(modulename, fullpath)
            imported = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imported)

            if hasattr(imported, funcname):
                function = getattr(imported, funcname)
            else:
                function = None
            return function
        except:
            traceback.print_exc()
            self.error(f"Module setup failed for '{modulename}'")

    ##########################################################################
    def load_target(self, name):
        """
        Loads a target module and runs the setup() function.

        The function searches the $SCPATH for targets/<name>.py and runs
        the setup function in that module if found.

        Args:
            name (str): Module name
            flow (str): Target flow to

        Examples:
            >>> chip.load_target('freepdk45_demo')
            Loads the 'freepdk45_demo' target

        """

        self.set('option', 'target', name)

        func = self.find_function(name, 'setup', 'targets')
        if func is not None:
            func(self)
        else:
            self.error(f'Target module {name} not found in $SCPATH or siliconcompiler/targets/.')

    ##########################################################################
    def load_pdk(self, name):
        """
        Loads a PDK module and runs the setup() function.

        The function searches the $SCPATH for pdks/<name>.py and runs
        the setup function in that module if found.

        Args:
            name (str): Module name

        Examples:
            >>> chip.load_pdk('freepdk45_pdk')
            Loads the 'freepdk45' pdk

        """

        func = self.find_function(name, 'setup', 'pdks')
        if func is not None:
            self.logger.info(f"Loading PDK '{name}'")
            self._loaded_modules['pdks'].append(name)
            func(self)
        else:
            self.error(f'PDK module {name} not found in $SCPATH or siliconcompiler/pdks/.')

    ##########################################################################
    def load_flow(self, name):
        """
        Loads a flow  module and runs the setup() function.

        The function searches the $SCPATH for flows/<name>.py and runs
        the setup function in that module if found.

        Args:
            name (str): Module name

        Examples:
            >>> chip.load_flow('asicflow')
            Loads the 'asicflow' flow

        """

        func = self.find_function(name, 'setup', 'flows')
        if func is not None:
            self.logger.info(f"Loading flow '{name}'")
            self._loaded_modules['flows'].append(name)
            func(self)
        else:
            self.error(f'Flow module {name} not found in $SCPATH or siliconcompiler/flows/.')

    ##########################################################################
    def load_lib(self, name):
        """
        Loads a library module and runs the setup() function.

        The function searches the $SCPATH for libs/<name>.py and runs
        the setup function in that module if found.

        Args:
            name (str): Module name

        Examples:
            >>> chip.load_lib('nangate45')
            Loads the 'nangate45' library

        """

        func = self.find_function(name, 'setup', 'libs')
        if func is not None:
            self.logger.info(f"Loading library '{name}'")
            self._loaded_modules['libs'].append(name)
            func(self)
        else:
            self.error(f'Library module {name} not found in $SCPATH or siliconcompiler/libs/.')

    ##########################################################################
    def load_checklist(self, name):
        """
        Loads a checklist module and runs the setup() function.

        The function searches the $SCPATH for checklist/<name>/<name>.py and runs
        the setup function in that module if found.

        Args:
            name (str): Module name

        Examples:
            >>> chip.load_checklist('oh_tapeout')
            Loads the 'oh_tapeout' checklist

        """

        func = self.find_function(name, 'setup', 'checklists')
        if func is not None:
            self.logger.info(f"Loading checklist '{name}'")
            self._loaded_modules['checklists'].append(name)
            func(self)
        else:
            self.error(f'Checklist module {name} not found in $SCPATH or siliconcompiler/checklists/.')

    ###########################################################################
    def list_metrics(self):
        '''
        Returns a list of all metrics in the schema.

        '''

        return self.getkeys('metric','default','default')

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

        #Fetch Values

        description = self.get(*keypath, field='shorthelp')
        typestr = self.get(*keypath, field='type')
        switchstr = str(self.get(*keypath, field='switch'))
        defstr = str(self.get(*keypath, field='defvalue'))
        requirement = str(self.get(*keypath, field='require'))
        helpstr = self.get(*keypath, field='help')
        example = self.get(*keypath, field='example')

        examplestr = ("\nExamples:    " + example[0] + ''.join(
                     ["\n             " + ex for ex in example[1:]]))

        #Removing multiple spaces and newlines
        helpstr = helpstr.rstrip()
        helpstr = helpstr.replace("\n", "")
        helpstr = ' '.join(helpstr.split())

        for idx, item in enumerate(example):
            example[idx] = ' '.join(item.split())
            example[idx] = example[idx].replace(", ", ",")

        #Wrap text
        para = textwrap.TextWrapper(width=60)
        para_list = para.wrap(text=helpstr)

        #Full Doc String
        fullstr = ("-"*80 +
                   "\nDescription: " + description +
                   "\nSwitch:      " + switchstr +
                   "\nType:        " + typestr  +
                   "\nRequirement: " + requirement   +
                   "\nDefault:     " + defstr   +
                   examplestr +
                   "\nHelp:        " + para_list[0] + "\n")
        for line in para_list[1:]:
            fullstr = (fullstr +
                       " "*13 + line.lstrip() + "\n")

        return fullstr


    ###########################################################################
    def valid(self, *args, valid_keypaths=None, quiet=True, default_valid=False):
        """
        Checks validity of a keypath.

        Checks the validity of a parameter keypath and returns True if the
        keypath is valid and False if invalid.

        Args:
            keypath(list str): Variable length schema key list.
            valid_keypaths (list of list): List of valid keypaths as lists. If
                None, check against all keypaths in the schema.
            quiet (bool): If True, don't display warnings for invalid keypaths.

        Returns:
            Boolean indicating validity of keypath.

        Examples:
            >>> check = chip.valid('design')
            Returns True.
            >>> check = chip.valid('blah')
            Returns False.
        """

        keypathstr = ','.join(args)
        keylist = list(args)
        if default_valid:
            default = 'default'
        else:
            default = None

        if valid_keypaths is None:
            valid_keypaths = self.getkeys()

        # Look for a full match with default playing wild card
        for valid_keypath in valid_keypaths:
            if len(keylist) != len(valid_keypath):
                continue

            ok = True
            for i in range(len(keylist)):
                if valid_keypath[i] not in (keylist[i], default):
                    ok = False
                    break
            if ok:
                return True

        # Match not found
        if not quiet:
            self.logger.warning(f"Keypath [{keypathstr}] is not valid")
        return False

    ###########################################################################
    def get(self, *keypath, field='value', job=None, cfg=None):
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
            cfg(dict): Alternate dictionary to access in place of the default
                chip object schema dictionary.

        Returns:
            Value found for the keypath and field provided.

        Examples:
            >>> foundry = chip.get('pdk', 'foundry')
            Returns the name of the foundry from the PDK.

        """

        if cfg is None:
            if job is not None:
                cfg = self.cfg['history'][job]
            else:
                cfg = self.cfg

        keypathstr = f'{keypath}'

        self.logger.debug(f"Reading from {keypathstr}. Field = '{field}'")
        return self._search(cfg, keypathstr, *keypath, field=field, mode='get')

    ###########################################################################
    def getkeys(self, *keypath, cfg=None, job=None):
        """
        Returns a list of schema dictionary keys.

        Searches the schema for the keypath provided and returns a list of
        keys found, excluding the generic 'default' key. Accessing a
        non-existent keypath produces a logger error message and raises the
        Chip object error flag.

        Args:
            keypath (list str): Variable length ordered schema key list
            cfg (dict): Alternate dictionary to access in place of self.cfg
            job (str): Jobname to use for dictionary access in place of the
                current active jobname.

        Returns:
            List of keys found for the keypath provided.

        Examples:
            >>> keylist = chip.getkeys('pdk')
            Returns all keys for the 'pdk' keypath.
            >>> keylist = chip.getkeys()
            Returns all list of all keypaths in the schema.
        """

        if cfg is None:
            if job is None:
                cfg = self.cfg
            else:
                cfg = self.cfg['history'][job]

        if len(list(keypath)) > 0:
            keypathstr = f'{keypath}'
            self.logger.debug('Getting schema parameter keys for: %s', keypathstr)
            keys = list(self._search(cfg, keypathstr, *keypath, mode='getkeys'))
            if 'default' in keys:
                keys.remove('default')
        else:
            self.logger.debug('Getting all schema parameter keys.')
            keys = list(self._allkeys(cfg))

        return keys

    ###########################################################################
    def getdict(self, *keypath, cfg=None):
        """
        Returns a schema dictionary.

        Searches the schema for the keypath provided and returns a complete
        dictionary. Accessing a non-existent keypath produces a logger error
        message and raises the Chip object error flag.

        Args:
            keypath(list str): Variable length ordered schema key list
            cfg(dict): Alternate dictionary to access in place of self.cfg

        Returns:
            A schema dictionary

        Examples:
            >>> pdk = chip.getdict('pdk')
            Returns the complete dictionary found for the keypath 'pdk'
        """

        if cfg is None:
            cfg = self.cfg

        if len(list(keypath)) > 0:
            keypathstr = ','.join(keypath)
            self.logger.debug('Getting cfg for: %s', keypathstr)
            localcfg = self._search(cfg, keypathstr, *keypath, mode='getcfg')

        return copy.deepcopy(localcfg)

    ###########################################################################
    def set(self, *args, field='value', clobber=True, cfg=None):
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
            cfg(dict): Alternate dictionary to access in place of self.cfg

        Examples:
            >>> chip.set('design', 'top')
            Sets the name of the design to 'top'
        '''

        if cfg is None:
            cfg = self.cfg

        keypathstr = f'{args[:-1]}'
        all_args = list(args)

        # Special case to ensure loglevel is updated ASAP
        if len(args) == 3 and args[1] == 'loglevel' and field == 'value':
            self.logger.setLevel(args[2])

        self.logger.debug(f"Setting {keypathstr} to {args[-1]}")
        return self._search(cfg, keypathstr, *all_args, field=field, mode='set', clobber=clobber)

    ###########################################################################
    def add(self, *args, cfg=None, field='value'):
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
            cfg(dict): Alternate dictionary to access in place of self.cfg
            field (str): Parameter field to set.

        Examples:
            >>> chip.add('source', 'hello.v')
            Adds the file 'hello.v' to the list of sources.
        '''

        if cfg is None:
            cfg = self.cfg

        keypathstr = f'{args[:-1]}'
        all_args = list(args)

        self.logger.debug(f'Appending value {args[-1]} to {keypathstr}')
        return self._search(cfg, keypathstr, *all_args, field=field, mode='add')


    ###########################################################################
    def _allkeys(self, cfg, keys=None, keylist=None):
        '''
        Returns list of all keypaths in the schema.
        '''

        if keys is None:
            keylist = []
            keys = []
        for k in cfg:
            newkeys = keys.copy()
            newkeys.append(k)
            if 'defvalue' in cfg[k]:
                keylist.append(newkeys)
            else:
                self._allkeys(cfg[k], keys=newkeys, keylist=keylist)
        return keylist

    ###########################################################################
    def _search(self, cfg, keypath, *args, field='value', mode='get', clobber=True):
        '''
        Internal recursive function that searches the Chip schema for a
        match to the combination of *args and fields supplied. The function is
        used to set and get data within the dictionary.

        Args:
            cfg(dict): The cfg schema to search
            keypath (str): Concatenated keypath used for error logging.
            args (str): Keypath/value variable list used for access
            field(str): Leaf cell field to access.
            mode(str): Action (set/get/add/getkeys/getkeys)
            clobber(bool): Specifies to clobber (for set action)

        '''

        all_args = list(args)
        param = all_args[0]
        val = all_args[-1]
        empty = [None, 'null', [], 'false']

        # Ensure that all keypath values are strings.
        # Scripts may accidentally pass in [None] if a prior schema entry was unexpectedly empty.
        keys_to_check = args
        if mode in ['set', 'add']:
            # Ignore the value parameter for 'set' and 'add' operations.
            keys_to_check = args[:-1]
        for key in keys_to_check:
            if not isinstance(key, str):
                self.error(
                    f'Invalid keypath: {keypath}\n'
                    'Your Chip configuration may be missing a parameter which is expected by your build script.')
                return None

        #set/add leaf cell (all_args=(param,val))
        if (mode in ('set', 'add')) & (len(all_args) == 2):
            # clean error if key not found
            if (not param in cfg) & (not 'default' in cfg):
                self.error(f"Set/Add keypath {keypath} does not exist.")
            else:
                # making an 'instance' of default if not found
                if (not param in cfg) & ('default' in cfg):
                    cfg[param] = copy.deepcopy(cfg['default'])
                list_type =bool(re.match(r'\[', cfg[param]['type']))
                # checking for illegal fields
                if not field in cfg[param] and (field != 'value'):
                    self.error(f"Field '{field}' for keypath {keypath}' is not a valid field.")
                # check legality of value
                if field == 'value':
                    (type_ok,type_error) = self._typecheck(cfg[param], param, val)
                    if not type_ok:
                        self.error("%s", type_error)
                # converting python True/False to lower case string
                if (field == 'value') and (cfg[param]['type'] == 'bool'):
                    if val == True:
                        val = "true"
                    elif val == False:
                        val = "false"
                # checking if value has been set
                # TODO: fix clobber!!
                selval = cfg[param]['value']
                # updating values
                if cfg[param]['lock'] == "true":
                    self.logger.debug("Ignoring {mode}{} to {keypath}. Lock bit is set.")
                elif (mode == 'set'):
                    if (field != 'value') or (selval in empty) or clobber:
                        if field in ('copy', 'lock'):
                            # boolean fields
                            if val is True:
                                cfg[param][field] = "true"
                            elif val is False:
                                cfg[param][field] = "false"
                            else:
                                self.error(f'{field} must be set to boolean.')
                        elif field in ('hashalgo', 'scope', 'require', 'type', 'unit',
                                       'shorthelp', 'notes', 'switch', 'help'):
                            # awlays string scalars
                            cfg[param][field] = val
                        elif field in ('example'):
                            # list from default schema (already a list)
                            cfg[param][field] = val
                        elif field in ('signature', 'filehash', 'date', 'author'):
                            # convert to list if appropriate
                            if isinstance(val, list) | (not list_type):
                                cfg[param][field] = val
                            else:
                                cfg[param][field] = [val]
                        elif (not list_type) & (val is None):
                            # special case for None
                            cfg[param][field] = None
                        elif (not list_type) & (not isinstance(val, list)):
                            # convert to string for scalar value
                            cfg[param][field] = str(val)
                        elif list_type & (not isinstance(val, list)):
                            # convert to string for list value
                            cfg[param][field] = [str(val)]
                        elif list_type & isinstance(val, list):
                            # converting tuples to strings
                            if re.search(r'\(', cfg[param]['type']):
                                cfg[param][field] = list(map(str,val))
                            else:
                                cfg[param][field] = val
                        else:
                            self.error(f"Assigning list to scalar for {keypath}")
                    else:
                        self.logger.debug(f"Ignoring set() to {keypath}, value already set. Use clobber=true to override.")
                elif (mode == 'add'):
                    if field in ('filehash', 'date', 'author', 'signature'):
                        cfg[param][field].append(str(val))
                    elif field in ('copy', 'lock'):
                        self.error(f"Illegal use of add() for scalar field {field}.")
                    elif list_type & (not isinstance(val, list)):
                        cfg[param][field].append(str(val))
                    elif list_type & isinstance(val, list):
                        cfg[param][field].extend(val)
                    else:
                        self.error(f"Illegal use of add() for scalar parameter {keypath}.")
                return cfg[param][field]
        #get leaf cell (all_args=param)
        elif len(all_args) == 1:
            if not param in cfg:
                self.error(f"Get keypath {keypath} does not exist.")
            elif mode == 'getcfg':
                return cfg[param]
            elif mode == 'getkeys':
                return cfg[param].keys()
            else:
                if not (field in cfg[param]) and (field!='value'):
                    self.error(f"Field '{field}' not found for keypath {keypath}")
                elif field == 'value':
                    #Select default if no value has been set
                    if field not in cfg[param]:
                        selval = cfg[param]['defvalue']
                    else:
                        selval =  cfg[param]['value']
                    #check for list
                    if bool(re.match(r'\[', cfg[param]['type'])):
                        sctype = re.sub(r'[\[\]]', '', cfg[param]['type'])
                        return_list = []
                        if selval is None:
                            return None
                        for item in selval:
                            if sctype == 'int':
                                return_list.append(int(item))
                            elif sctype == 'float':
                                return_list.append(float(item))
                            elif sctype.startswith('(str,'):
                                if isinstance(item,tuple):
                                    return_list.append(item)
                                else:
                                    tuplestr = re.sub(r'[\(\)\'\s]','',item)
                                    return_list.append(tuple(tuplestr.split(',')))
                            elif sctype.startswith('(float,'):
                                if isinstance(item,tuple):
                                    return_list.append(item)
                                else:
                                    tuplestr = re.sub(r'[\(\)\s]','',item)
                                    return_list.append(tuple(map(float, tuplestr.split(','))))
                            else:
                                return_list.append(item)
                        return return_list
                    else:
                        if selval is None:
                            # Unset scalar of any type
                            scalar = None
                        elif cfg[param]['type'] == "int":
                            #print(selval, type(selval))
                            scalar = int(float(selval))
                        elif cfg[param]['type'] == "float":
                            scalar = float(selval)
                        elif cfg[param]['type'] == "bool":
                            scalar = (selval == 'true')
                        elif re.match(r'\(', cfg[param]['type']):
                            tuplestr = re.sub(r'[\(\)\s]','',selval)
                            scalar = tuple(map(float, tuplestr.split(',')))
                        else:
                            scalar = selval
                        return scalar
                #all non-value fields are strings (or lists of strings)
                else:
                    if cfg[param][field] == 'true':
                        return True
                    elif cfg[param][field] == 'false':
                        return False
                    else:
                        return cfg[param][field]
        #if not leaf cell descend tree
        else:
            ##copying in default tree for dynamic trees
            if not param in cfg and 'default' in cfg:
                cfg[param] = copy.deepcopy(cfg['default'])
            elif not param in cfg:
                self.error(f"Get keypath {keypath} does not exist.")
                return None
            all_args.pop(0)
            return self._search(cfg[param], keypath, *all_args, field=field, mode=mode, clobber=clobber)

    ###########################################################################
    def _prune(self, cfg, top=True, keeplists=False):
        '''
        Internal recursive function that creates a local copy of the Chip
        schema (cfg) with only essential non-empty parameters retained.

        '''

        # create a local copy of dict
        if top:
            localcfg = copy.deepcopy(cfg)
        else:
            localcfg = cfg

        #10 should be enough for anyone...
        maxdepth = 10
        i = 0

        #Prune when the default & value are set to the following
        if keeplists:
            empty = ("null", None)
        else:
            empty = ("null", None, [])

        # When at top of tree loop maxdepth times to make sure all stale
        # branches have been removed, not elegant, but stupid-simple
        # "good enough"
        while i < maxdepth:
            #Loop through all keys starting at the top
            for k in list(localcfg.keys()):
                #removing all default/template keys
                # reached a default subgraph, delete it
                if k == 'default':
                    del localcfg[k]
                # reached leaf-cell
                elif 'help' in localcfg[k].keys():
                    del localcfg[k]['help']
                elif 'example' in localcfg[k].keys():
                    del localcfg[k]['example']
                elif 'defvalue' in localcfg[k].keys():
                    if localcfg[k]['defvalue'] in empty:
                        if 'value' in localcfg[k].keys():
                            if localcfg[k]['value'] in empty:
                                del localcfg[k]
                        else:
                            del localcfg[k]
                #removing stale branches
                elif not localcfg[k]:
                    localcfg.pop(k)
                #keep traversing tree
                else:
                    self._prune(cfg=localcfg[k], top=False, keeplists=keeplists)
            if top:
                i += 1
            else:
                break

        return localcfg

    ###########################################################################
    def _find_sc_file(self, filename, missing_ok=False):
        """
        Returns the absolute path for the filename provided.

        Searches the SC root directory and the 'scpath' parameter for the
        filename provided and returns the absolute path. If no valid absolute
        path is found during the search, None is returned.

        Shell variables ('$' followed by strings consisting of numbers,
        underscores, and digits) are replaced with the variable value.

        Args:
            filename (str): Relative or absolute filename.

        Returns:
            Returns absolute path of 'filename' if found, otherwise returns
            None.

        Examples:
            >>> chip._find_sc_file('flows/asicflow.py')
           Returns the absolute path based on the sc installation directory.

        """

        # Replacing environment variables
        filename = self._resolve_env_vars(filename)

        # If we have a path relative to our cwd or an abs path, pass-through here
        if os.path.exists(os.path.abspath(filename)):
            return os.path.abspath(filename)

        # Otherwise, search relative to scpaths
        scpaths = [self.scroot, self.cwd]
        scpaths.extend(self.get('option', 'scpath'))
        if 'SCPATH' in os.environ:
            scpaths.extend(os.environ['SCPATH'].split(os.pathsep))

        searchdirs = ', '.join(scpaths)
        self.logger.debug(f"Searching for file {filename} in {searchdirs}")

        result = None
        for searchdir in scpaths:
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
    def find_files(self, *keypath, cfg=None, missing_ok=False, job=None):
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
            cfg (dict): Alternate dictionary to access in place of the default
                chip object schema dictionary.
            missing_ok (bool): If True, silently return None when files aren't
                found. If False, print an error and set the error flag.
            job (str): Jobname to use for dictionary access in place of the
                current active jobname.

        Returns:
            If keys points to a scalar entry, returns an absolute path to that
            file/directory, or None if not found. It keys points to a list
            entry, returns a list of either the absolute paths or None for each
            entry, depending on whether it is found.

        Examples:
            >>> chip.find_files('source')
            Returns a list of absolute paths to source files, as specified in
            the schema.

        """
        if cfg is None:
            cfg = self.cfg

        copyall = self.get('option', 'copyall', cfg=cfg, job=job)
        paramtype = self.get(*keypath, field='type', cfg=cfg, job=job)

        if 'file' in paramtype:
            copy = self.get(*keypath, field='copy', cfg=cfg, job=job)
        else:
            copy = False

        if 'file' not in paramtype and 'dir' not in paramtype:
            self.error('Can only call find_files on file or dir types')
            return None

        is_list = bool(re.match(r'\[', paramtype))

        paths = self.get(*keypath, cfg=cfg, job=job)
        # Convert to list if we have scalar
        if not is_list:
            paths = [paths]

        result = []

        # Special cases for various ['eda', ...] files that may be implicitly
        # under the workdir (or refdir in the case of scripts).
        # TODO: it may be cleaner to have a file resolution scope flag in schema
        # (e.g. 'scpath', 'workdir', 'refdir'), rather than harcoding special
        # cases.
        if keypath[0] == 'tool' and keypath[2] in ('input', 'output', 'report'):
            step = keypath[3]
            index = keypath[4]
            if keypath[2] == 'report':
                io = ""
            else:
                io = keypath[2] + 's'
            iodir = os.path.join(self._getworkdir(jobname=job, step=step, index=index), io)
            for path in paths:
                abspath = os.path.join(iodir, path)
                if os.path.isfile(abspath):
                    result.append(abspath)
            return result
        elif keypath[0] == 'tool' and keypath[2] == 'script':
            tool = keypath[1]
            step = keypath[3]
            index = keypath[4]
            refdirs = self.find_files('tool', tool, 'refdir', step, index)
            for path in paths:
                for refdir in refdirs:
                    abspath = os.path.join(refdir, path)
                    if os.path.isfile(abspath):
                        result.append(abspath)
                        break

            return result

        for path in paths:
            if (copyall or copy) and ('file' in paramtype):
                name = self._get_imported_filename(path)
                abspath = os.path.join(self._getworkdir(jobname=job, step='import'), 'inputs', name)
                if os.path.isfile(abspath):
                    # if copy is True and file is found in import inputs,
                    # continue. Otherwise, fall through to _find_sc_file (the
                    # file may not have been gathered in imports yet)
                    result.append(abspath)
                    continue
            result.append(self._find_sc_file(path, missing_ok=missing_ok))
        # Convert back to scalar if that was original type
        if not is_list:
            return result[0]

        return result

    ###########################################################################
    def find_result(self, filetype, step, jobname=None, index='0'):
        """
        Returns the absolute path of a compilation result.

        Utility function that returns the absolute path to a results
        file based on the provided arguments. The result directory
        structure is:

        <dir>/<design>/<jobname>/<step>/<index>/outputs/<design>.filetype

        Args:
            filetype (str): File extension (.v, .def, etc)
            step (str): Task step name ('syn', 'place', etc)
            jobname (str): Jobid directory name
            index (str): Task index

        Returns:
            Returns absolute path to file.

        Examples:
            >>> manifest_filepath = chip.find_result('.vg', 'syn')
           Returns the absolute path to the manifest.
        """
        if jobname is None:
            jobname = self.get('option', 'jobname')

        workdir = self._getworkdir(jobname, step, index)
        design = self.top()
        filename = f"{workdir}/outputs/{design}.{filetype}"

        self.logger.debug("Finding result %s", filename)

        if os.path.isfile(filename):
            return filename
        else:
            return None

    ###########################################################################
    def _abspath(self, cfg):
        '''
        Internal function that goes through provided dictionary and resolves all
        relative paths where required.
        '''

        for keypath in self.getkeys(cfg=cfg):
            paramtype = self.get(*keypath, cfg=cfg, field='type')
            value = self.get(*keypath, cfg=cfg)
            if value:
                #only do something if type is file or dir
                if 'file' in paramtype or 'dir' in paramtype:
                    abspaths = self.find_files(*keypath, cfg=cfg, missing_ok=True)
                    self.set(*keypath, abspaths, cfg=cfg)

    ###########################################################################
    def _print_csv(self, cfg, fout):
        csvwriter = csv.writer(fout)
        csvwriter.writerow(['Keypath', 'Value'])

        allkeys = self.getkeys(cfg=cfg)
        for key in allkeys:
            keypath = ','.join(key)
            value = self.get(*key, cfg=cfg)
            if isinstance(value,list):
                for item in value:
                    csvwriter.writerow([keypath, item])
            else:
                csvwriter.writerow([keypath, value])

    ###########################################################################
    def _escape_val_tcl(self, val, typestr):
        '''Recursive helper function for converting Python values to safe TCL
        values, based on the SC type string.'''
        if val is None:
            return ''
        elif typestr.startswith('('):
            # Recurse into each item of tuple
            subtypes = typestr.strip('()').split(',')
            valstr = ' '.join(self._escape_val_tcl(v, subtype.strip())
                              for v, subtype in zip(val, subtypes))
            return f'[list {valstr}]'
        elif typestr.startswith('['):
            # Recurse into each item of list
            subtype = typestr.strip('[]')
            valstr = ' '.join(self._escape_val_tcl(v, subtype) for v in val)
            return f'[list {valstr}]'
        elif typestr == 'bool':
            return 'true' if val else 'false'
        elif typestr == 'str':
            # Escape string by surrounding it with "" and escaping the few
            # special characters that still get considered inside "". We don't
            # use {}, since this requires adding permanent backslashes to any
            # curly braces inside the string.
            # Source: https://www.tcl.tk/man/tcl8.4/TclCmd/Tcl.html (section [4] on)
            escaped_val = (val.replace('\\', '\\\\') # escape '\' to avoid backslash substition (do this first, since other replaces insert '\')
                              .replace('[', '\\[')   # escape '[' to avoid command substition
                              .replace('$', '\\$')   # escape '$' to avoid variable substition
                              .replace('"', '\\"'))  # escape '"' to avoid string terminating early
            return '"' + escaped_val + '"'
        elif typestr in ('file', 'dir'):
            # Replace $VAR with $env(VAR) for tcl
            val = re.sub(r'\$(\w+)', r'$env(\1)', val)
            # Same escapes as applied to string, minus $ (since we want to resolve env vars).
            escaped_val = (val.replace('\\', '\\\\') # escape '\' to avoid backslash substition (do this first, since other replaces insert '\')
                              .replace('[', '\\[')   # escape '[' to avoid command substition
                              .replace('"', '\\"'))  # escape '"' to avoid string terminating early
            return '"' +  escaped_val + '"'
        else:
            # floats/ints just become strings
            return str(val)

    ###########################################################################
    def _print_tcl(self, cfg, fout=None, prefix=""):
        '''
        Prints out schema as TCL dictionary
        '''
        manifest_header = os.path.join(self.scroot, 'data', 'sc_manifest_header.tcl')
        with open(manifest_header, 'r') as f:
            fout.write(f.read())
        fout.write('\n')

        allkeys = self.getkeys(cfg=cfg)

        for key in allkeys:
            typestr = self.get(*key, cfg=cfg, field='type')
            value = self.get(*key, cfg=cfg)

            #create a TCL dict
            keystr = ' '.join(key)

            valstr = self._escape_val_tcl(value, typestr)

            if not (typestr.startswith('[') or typestr.startswith('(')):
                # treat scalars as lists as well
                valstr = f'[list {valstr}]'

            outstr = f"{prefix} {keystr} {valstr}\n"

            #print out all non default values
            if 'default' not in key:
                fout.write(outstr)

    ###########################################################################

    def merge_manifest(self, cfg, job=None, clobber=True, clear=True, check=False):
        """
        Merges an external manifest with the current compilation manifest.

        All value fields in the provided schema dictionary are merged into the
        current chip object. Dictionaries with non-existent keypath produces a
        logger error message and raises the Chip object error flag.

        Args:
            job (str): Specifies non-default job to merge into
            clear (bool): If True, disables append operations for list type
            clobber (bool): If True, overwrites existing parameter value
            check (bool): If True, checks the validity of each key
            partial (bool): If True, perform a partial merge, only merging
                keypaths that may have been updated during run().

        Examples:
            >>> chip.merge_manifest('my.pkg.json')
           Merges all parameters in my.pk.json into the Chip object

        """
        self._merge_manifest(cfg, job, clobber, clear, check)

    def _key_may_be_updated(self, keypath):
        '''Helper that returns whether `keypath` can be updated mid-run.'''
        # TODO: cleaner way to manage this?
        if keypath[0] in ('metric', 'record'):
            return True
        if keypath[0] == 'flowgraph' and keypath[4] in ('select', 'status'):
            return True
        return False

    ###########################################################################
    def _merge_manifest(self, cfg, job=None, clobber=True, clear=True, check=False, partial=False):
        """
        Internal merge_manifest() implementation with `partial` arg.

        partial (bool): If True, perform a partial merge, only merging keypaths
        that may have been updated during run().
        """
        if job is not None:
            # fill ith default schema before populating
            self.cfg['history'][job] = schema_cfg()
            dst = self.cfg['history'][job]
        else:
            dst = self.cfg

        for keylist in self.getkeys(cfg=cfg):
            if partial and not self._key_may_be_updated(keylist):
                continue
            if keylist[0] in ('history', 'library'):
                continue
            #only read in valid keypaths without 'default'
            key_valid = True
            if check:
                key_valid = self.valid(*keylist, quiet=False, default_valid=True)
            if key_valid and 'default' not in keylist:
                # update value, handling scalars vs. lists
                typestr = self.get(*keylist, cfg=cfg, field='type')
                val = self.get(*keylist, cfg=cfg)
                arg = keylist.copy()
                arg.append(val)
                if bool(re.match(r'\[', typestr)) & bool(not clear):
                    self.add(*arg, cfg=dst)
                else:
                    self.set(*arg, cfg=dst, clobber=clobber)

                # update other fields that a user might modify
                for field in self.getdict(*keylist, cfg=cfg).keys():
                    if field in ('value', 'switch', 'type', 'require', 'defvalue',
                                 'shorthelp', 'example', 'help'):
                        # skip these fields (value handled above, others are static)
                        continue
                    v = self.get(*keylist, cfg=cfg, field=field)
                    self.set(*keylist, v, cfg=dst, field=field)

    ###########################################################################
    def _keypath_empty(self, key):
        '''
        Utility function to check key for an empty list.
        '''

        emptylist = ("null", None, [])

        value = self.get(*key)
        defvalue = self.get(*key, field='defvalue')
        value_empty = (defvalue in emptylist) and (value in emptylist)

        return value_empty

    ###########################################################################
    def _check_files(self):
        allowed_paths = [os.path.join(self.cwd, self.get('option', 'builddir'))]
        allowed_paths.extend(os.environ['SC_VALID_PATHS'].split(os.pathsep))

        for keypath in self.getkeys():
            if 'default' in keypath:
                continue

            paramtype = self.get(*keypath, field='type')
            #only do something if type is file or dir
            if ('history' not in keypath and 'library' not in keypath) and ('file' in paramtype or 'dir' in paramtype):

                if self.get(*keypath) is None:
                    # skip unset values (some directories are None by default)
                    continue

                abspaths = self.find_files(*keypath, missing_ok=True)
                if not isinstance(abspaths, list):
                    abspaths = [abspaths]

                for abspath in abspaths:
                    ok = False

                    if abspath is not None:
                        for allowed_path in allowed_paths:
                            if os.path.commonpath([abspath, allowed_path]) == allowed_path:
                                ok = True
                                continue

                    if not ok:
                        self.logger.error(f'Keypath {keypath} contains path(s) '
                            'that do not exist or resolve to files outside of '
                            'allowed directories.')
                        return False

        return True

    ###########################################################################
    def check_filepaths(self):
        '''
        Verifies that paths to all files in manifest are valid.

        Returns:
            True if all file paths are valid, otherwise False.
        '''

        allkeys = self.getkeys()
        for keypath in allkeys:
            allpaths = []
            paramtype = self.get(*keypath, field='type')
            if 'file' in paramtype or 'dir' in paramtype:
                if 'dir' not in keypath and self.get(*keypath):
                    allpaths = list(self.get(*keypath))
                for path in allpaths:
                    #check for env var
                    m = re.match(r'\$(\w+)(.*)', path)
                    if m:
                        prefix_path = os.environ[m.group(1)]
                        path = prefix_path + m.group(2)
                    file_error = 'file' in paramtype and not os.path.isfile(path)
                    dir_error = 'dir' in paramtype and not os.path.isdir(path)
                    if file_error or dir_error:
                        self.logger.error(f"Paramater {keypath} path {path} is invalid")
                        return False

        return True

    ###########################################################################
    def _check_manifest_dynamic(self, step, index):
        '''Runtime checks called from _runtask().

        - Make sure expected inputs exist.
        - Make sure all required filepaths resolve correctly.
        '''
        error = False

        flow = self.get('option', 'flow')
        tool = self.get('flowgraph', flow, step, index, 'tool')
        if self.valid('tool', tool, 'input', step, index):
            required_inputs = self.get('tool', tool, 'input', step, index)
        else:
            required_inputs = []
        input_dir = os.path.join(self._getworkdir(step=step, index=index), 'inputs')
        for filename in required_inputs:
            path = os.path.join(input_dir, filename)
            if not os.path.isfile(path):
                self.logger.error(f'Required input {filename} not received for {step}{index}.')
                error = True

        if (not tool in self.builtin) and self.valid('tool', tool, 'require', step, index):
            all_required = self.get('tool', tool, 'require', step, index)
            for item in all_required:
                keypath = item.split(',')
                paramtype = self.get(*keypath, field='type')
                if ('file' in paramtype) or ('dir' in paramtype):
                    abspath = self.find_files(*keypath, missing_ok=True)
                    if abspath is None or (isinstance(abspath, list) and None in abspath):
                        self.logger.error(f"Required file keypath {keypath} can't be resolved.")
                        error = True

        # Need to run this check here since file resolution can change in
        # _runtask().
        if 'SC_VALID_PATHS' in os.environ:
            if not self._check_files():
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
        jobname = self.get('option', 'jobname')
        steplist = self.get('option', 'steplist')
        if not steplist:
            steplist = self.list_steps()

        #1. Checking that flowgraph and steplist are legal
        if flow not in self.getkeys('flowgraph'):
            error = True
            self.logger.error(f"flowgraph {flow} not defined.")
        legal_steps = self.getkeys('flowgraph',flow)

        if 'import' not in legal_steps:
            error = True
            self.logger.error("Flowgraph doesn't contain import step.")

        indexlist = {}
        #TODO: refactor
        for step in steplist:
            if self.get('option', 'indexlist'):
                indexlist[step] = self.get('option', 'indexlist')
            else:
                indexlist[step] = self.getkeys('flowgraph', flow, step)

        for step in steplist:
            for index in indexlist[step]:
                in_job = None
                if (step in self.getkeys('option', 'jobinput') and
                    index in self.getkeys('option', 'jobinput', step)):
                    in_job = self.get('option', 'jobinput', step, index)

                for in_step, in_index in self.get('flowgraph', flow, step, index, 'input'):
                    if in_job is not None:
                        workdir = self._getworkdir(jobname=in_job, step=in_step, index=in_index)
                        cfg = os.path.join(workdir, 'outputs', f'{design}.pkg.json')
                        if not os.path.isfile(cfg):
                            self.logger.error(f'{step}{index} relies on {in_step}{in_index} from job {in_job}, '
                                'but this task has not been run.')
                            error = True
                        continue
                    if in_step in steplist and in_index in indexlist[in_step]:
                        # we're gonna run this step, OK
                        continue
                    if self.get('flowgraph', flow, in_step, in_index, 'status') == TaskStatus.SUCCESS:
                        # this task has already completed successfully, OK
                        continue
                    self.logger.error(f'{step}{index} relies on {in_step}{in_index}, '
                        'but this task has not been run and is not in the current steplist.')
                    error = True

        #2. Check libary names
        for item in self.get('asic', 'logiclib'):
            if item not in self.getkeys('library'):
                error = True
                self.logger.error(f"Target library {item} not found.")

        #3. Check requirements list
        allkeys = self.getkeys()
        for key in allkeys:
            keypath = ",".join(key)
            if 'default' not in key and 'history' not in key and 'library' not in key:
                key_empty = self._keypath_empty(key)
                requirement = self.get(*key, field='require')
                if key_empty and (str(requirement) == 'all'):
                    error = True
                    self.logger.error(f"Global requirement missing for [{keypath}].")
                elif key_empty and (str(requirement) == self.get('option', 'mode')):
                    error = True
                    self.logger.error(f"Mode requirement missing for [{keypath}].")

        #4. Check per tool parameter requirements (when tool exists)
        for step in steplist:
            for index in self.getkeys('flowgraph', flow, step):
                tool = self.get('flowgraph', flow, step, index, 'tool')
                if (tool not in self.builtin) and (tool in self.getkeys('tool')):
                    # checking that requirements are set
                    if self.valid('tool', tool, 'require', step, index):
                        all_required = self.get('tool', tool, 'require', step, index)
                        for item in all_required:
                            keypath = item.split(',')
                            if self._keypath_empty(keypath):
                                error = True
                                self.logger.error(f"Value empty for [{keypath}] for {tool}.")

                    if (self._keypath_empty(['tool', tool, 'exe']) and
                        self.find_function(tool, 'run', 'tools') is None):
                        error = True
                        self.logger.error(f'No executable or run() function specified for tool {tool}')

        if 'SC_VALID_PATHS' in os.environ:
            if not self._check_files():
                error = True

        if not self._check_flowgraph_io():
            error = True

        return not error

    ###########################################################################
    def _gather_outputs(self, step, index):
        '''Return set of filenames that are guaranteed to be in outputs
        directory after a successful run of step/index.'''

        flow = self.get('option', 'flow')
        tool = self.get('flowgraph', flow, step, index, 'tool')

        outputs = set()
        if tool in self.builtin:
            in_tasks = self.get('flowgraph', flow, step, index, 'input')
            in_task_outputs = [self._gather_outputs(*task) for task in in_tasks]

            if tool in ('minimum', 'maximum'):
                if len(in_task_outputs) > 0:
                    outputs = in_task_outputs[0].intersection(*in_task_outputs[1:])
            elif tool in ('join', 'nop'):
                if len(in_task_outputs) > 0:
                    outputs = in_task_outputs[0].union(*in_task_outputs[1:])
            else:
                # TODO: logic should be added here when mux/verify builtins are implemented.
                self.logger.error(f'Builtin {tool} not yet implemented')
        else:
            # Not builtin tool
            if self.valid('tool', tool, 'output', step, index):
                outputs = set(self.get('tool', tool, 'output', step, index))
            else:
                outputs = set()

        if step == 'import':
            imports = {self._get_imported_filename(p) for p in self._collect_paths()}
            outputs.update(imports)

        return outputs

    ###########################################################################
    def _check_flowgraph_io(self):
        '''Check if flowgraph is valid in terms of input and output files.

        Returns True if valid, False otherwise.
        '''

        flow = self.get('option', 'flow')
        steplist = self.get('option', 'steplist')

        if not steplist:
            steplist = self.list_steps()

        for step in steplist:
            for index in self.getkeys('flowgraph', flow, step):
                # For each task, check input requirements.
                tool = self.get('flowgraph', flow, step, index, 'tool')
                if tool in self.builtin:
                    # We can skip builtins since they don't have any particular
                    # input requirements -- they just pass through what they
                    # receive.
                    continue

                # Get files we receive from input tasks.
                in_tasks = self.get('flowgraph', flow, step, index, 'input')
                all_inputs = set()
                for in_step, in_index in in_tasks:
                    if in_step not in steplist:
                        # If we're not running the input step, the required
                        # inputs need to already be copied into the build
                        # directory.
                        jobname = self.get('option', 'jobname')
                        if self.valid('option', 'jobinput', step, index):
                            in_job = self.get('option', 'jobinput', step, index)
                        else:
                            in_job = jobname
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
                        if inp in all_inputs:
                            self.logger.error(f'Invalid flow: {step}{index} '
                                f'receives {inp} from multiple input tasks')
                            return False
                        all_inputs.add(inp)

                if self.valid('tool', tool, 'input', step, index):
                    requirements = self.get('tool', tool, 'input', step, index)
                else:
                    requirements = []
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

        filepath = os.path.abspath(filename)
        self.logger.debug(f"Reading manifest {filepath}")
        if not os.path.isfile(filepath):
            self.error(f"Manifest file not found {filepath}", fatal=True)

        #Read arguments from file based on file type

        if filepath.endswith('.gz'):
            fin = gzip.open(filepath, 'r')
        else:
            fin = open(filepath, 'r')

        try:
            if re.search(r'(\.json|\.sup)(\.gz)*$', filepath):
                localcfg = json.load(fin)
            elif re.search(r'(\.yaml|\.yml)(\.gz)*$', filepath):
                localcfg = yaml.load(fin, Loader=yaml.SafeLoader)
            else:
                self.error('File format not recognized %s', filepath)
        finally:
            fin.close()

        if self.get('schemaversion') != localcfg['schemaversion']['value']:
            self.logger.warning('Attempting to read manifest with incompatible '
            'schema version into current chip object. Skipping...')
            return

        # Merging arguments with the Chip configuration
        self._merge_manifest(localcfg, job=job, clear=clear, clobber=clobber, partial=partial)

        # Read history
        if 'history' in localcfg and not partial:
            for historic_job in localcfg['history'].keys():
                self._merge_manifest(localcfg['history'][historic_job],
                                        job=historic_job,
                                        clear=clear,
                                        clobber=clobber,
                                        partial=False)

        if 'library' in localcfg and not partial:
            for libname in localcfg['library'].keys():
                if libname in self.cfg['library']:
                    # TODO: should we make this a proper merge?
                    self.logger.warning(f'Overwriting existing library {libname} '
                        f'in object with values read from {filename}.')
                self._import_library(libname, localcfg['library'][libname])

    ###########################################################################
    def write_manifest(self, filename, prune=True, abspath=False, job=None):
        '''
        Writes the compilation manifest to a file.

        The write file format is determined by the filename suffix. Currently
        json (*.json), yaml (*.yaml), tcl (*.tcl), and (*.csv) formats are
        supported.

        Args:
            filename (filepath): Output filepath
            prune (bool): If True, essential non-empty parameters from the
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

        if prune:
            self.logger.debug('Pruning dictionary before writing file %s', filepath)
            # Keep empty lists to simplify TCL coding
            if filepath.endswith('.tcl'):
                keeplists = True
            else:
                keeplists = False
            cfgcopy = self._prune(self.cfg, keeplists=keeplists)
        else:
            cfgcopy = copy.deepcopy(self.cfg)

        # resolve absolute paths
        if abspath:
            self._abspath(cfgcopy)

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
                fout.write(json.dumps(cfgcopy, indent=4, sort_keys=True))
            elif re.search(r'(\.yaml|\.yml)(\.gz)*$', filepath):
                fout.write(yaml.dump(cfgcopy, Dumper=YamlIndentDumper, default_flow_style=False))
            elif re.search(r'(\.tcl)(\.gz)*$', filepath):
                self._print_tcl(cfgcopy, prefix="dict set sc_cfg", fout=fout)
            elif is_csv:
                self._print_csv(cfgcopy, fout=fout)
            else:
                self.error('File format not recognized %s', filepath)
        finally:
            fout.close()

    ###########################################################################
    def check_checklist(self, standard, items=None, check_ok=False):
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

        Returns:
            Status of item check.

        Examples:
            >>> status = chip.check_checklist('iso9000', 'd000')
            Returns status.
        '''
        error = False

        self.logger.info(f'Checking checklist {standard}')

        if items is None:
            items = self.getkeys('checklist', standard)

        flow = self.get('option', 'flow')

        for item in items:
            all_criteria = self.get('checklist', standard, item, 'criteria')
            for criteria in all_criteria:
                m = re.match(r'(\w+)([\>\=\<]+)(\w+)', criteria)
                if not m:
                    self.error(f"Illegal checklist criteria: {criteria}")
                    return False
                elif m.group(1) not in self.getkeys('metric', 'default', 'default'):
                    self.error(f"Critera must use legal metrics only: {criteria}")
                    return False

                metric = m.group(1)
                op = m.group(2)
                goal = float(m.group(3))

                tasks = self.get('checklist', standard, item, 'task')
                for job, step, index in tasks:
                    # Automated checks
                    flow = self.get('option', 'flow', job=job)
                    tool = self.get('flowgraph', flow, step, index, 'tool', job=job)

                    value = self.get('metric', step, index, metric,  job=job)
                    criteria_ok = self._safecompare(value, op, goal)
                    if metric in self.getkeys('checklist', standard, item, 'waiver'):
                        waivers = self.get('checklist', standard, item, 'waiver', metric)
                    else:
                        waivers = []

                    criteria_str = f'{metric}{op}{goal}'
                    if not criteria_ok and waivers:
                        self.logger.warning(f'{item} criteria {criteria_str} unmet by task {step}{index}, but found waivers.')
                    elif not criteria_ok:
                        self.logger.error(f'{item} criteria {criteria_str} unmet by task {step}{index}.')
                        error = True

                    if (step in self.getkeys('tool', tool, 'report', job=job) and
                        index in self.getkeys('tool', tool, 'report', step, job=job) and
                        metric in self.getkeys('tool', tool, 'report', step, index, job=job)):
                        eda_reports = self.find_files('tool', tool, 'report', step, index, metric, job=job)
                    else:
                        eda_reports = None

                    if not eda_reports:
                        self.logger.error(f'No EDA reports generated for metric {metric} in task {step}{index}')
                        error = True

                    for report in eda_reports:
                        if report not in self.get('checklist', standard, item, 'report'):
                            self.add('checklist', standard, item, 'report', report)

            if len(self.get('checklist', standard, item, 'report')) == 0:
                # TODO: validate that report exists?
                self.logger.error(f'No report documenting item {item}')
                error = True

            if check_ok and not self.get('checklist', standard, item, 'ok'):
                self.logger.error(f"Item {item} 'ok' field not checked")
                error = True

        self.logger.info('Check succeeded!')

        return not error

    ###########################################################################
    def read_file(self, filename, step='import', index='0'):
        '''
        Read file defined in schema. (WIP)
        '''
        return(0)

    ###########################################################################
    def update(self):
        '''
        Update the chip dependency graph.

        1. Finds all packages in the local cache
        2. Fetches all packages in the remote registry
        3. Creates a dependency graph based on current chip dependencies and
           dependencies read from dependency json objects.
        4. If autoinstall is set, copy registry packages to local cache.
        5. Error out if package is not found in local cache or in registry.
        6. Error out if autoinstall is set and registry package is missing.

        '''

        # schema settings
        design = self.get('design')
        reglist = self.get('option', 'registry')
        auto = self.get('option','autoinstall')

        # environment settings
        # Local cache location
        if 'SC_HOME' in os.environ:
            home = os.environ['SC_HOME']
        else:
            home = os.environ['HOME']

        cache = os.path.join(home,'.sc','registry')

        # Indexing all local cache packages
        local = self._build_index(cache)
        remote = self._build_index(reglist)

        # Cycle through current chip dependencies
        deps = {}
        for dep in self.getkeys('package', 'dependency'):
            deps[dep] = self.get('package', 'dependency', dep)

        depgraph = self._find_deps(cache, local, remote, design, deps, auto)

        # Update dependency graph
        for dep in depgraph:
            self.set('package', 'depgraph', dep, depgraph[dep])

        return depgraph

    ###########################################################################
    def _build_index(self, dirlist):
        '''
        Build a package index for a registry.
        '''

        if not isinstance(dirlist, list):
            dirlist = [dirlist]

        index = {}
        for item in dirlist:
            if re.match(r'http', item):
                #TODO
                pass
            else:
                packages = os.listdir(item)
                for i in packages:
                    versions = os.listdir(os.path.join(item, i))
                    index[i] = {}
                    for j in versions:
                        index[i][j] = item

        return index

    ###########################################################################
    def _install_package(self, cache, dep, ver, remote):
        '''
        Copies a package from remote to local.
        The remote and local arguments are package indices of format:
        index['dirname']['dep']
        '''

        package = f"{dep}-{ver}.sup.gz"

        self.logger.info(f"Installing package {package} in {cache}")

        # Check that package exists in remote registry
        if dep in remote.keys():
            if ver not in list(remote[dep].keys()):
                self.error(f"Package {dep}-{ver} not found in registry.")

        ifile = os.path.join(remote[dep][ver],dep,ver,package)
        odir = os.path.join(cache,dep,ver)
        ofile = os.path.join(odir,package)

        # Install package
        os.makedirs(odir, exist_ok=True)
        shutil.copyfile(ifile, ofile)

    ###########################################################################
    def _find_deps(self, cache, local, remote, design, deps, auto, depgraph={}, upstream={}):
        '''
        Recursive function to find and install dependencies.
        '''

        # install missing dependencies
        depgraph[design] = []
        for dep in deps.keys():
            #TODO: Proper PEP semver matching
            ver = list(deps[dep])[0]
            depgraph[design].append((dep,ver))
            islocal = False
            if dep in local.keys():
                if ver in local[dep]:
                    islocal = True

            # install and update local index
            if auto and islocal:
                self.logger.info(f"Found package {dep}-{ver} in cache")
            elif auto and not islocal:
                self._install_package(cache, dep, ver, remote)
                local[dep]=ver

            # look through dependency package files
            package = os.path.join(cache,dep,ver,f"{dep}-{ver}.sup.gz")
            if not os.path.isfile(package):
                self.error("Package missing. Try 'autoinstall' or install manually.")
            with gzip.open(package, 'r') as f:
                localcfg = json.load(f)

            # done if no more dependencies
            if 'dependency' in localcfg['package']:
                subdeps = {}
                subdesign = localcfg['design']['value']
                depgraph[subdesign] = []
                for item in localcfg['package']['dependency'].keys():
                    subver = localcfg['package']['dependency'][item]['value']
                    if (item in upstream) and (upstream[item] == subver):
                        # Circular imports are not supported.
                        self.error(f'Cannot process circular import: {dep}-{ver} <---> {item}-{subver}.', fatal=True)
                    subdeps[item] = subver
                    upstream[item] = subver
                    depgraph[subdesign].append((item, subver))
                    self._find_deps(cache, local, remote, subdesign, subdeps, auto, depgraph, upstream)

        return depgraph

    ###########################################################################
    def import_library(self, lib_chip):
        '''Import a Chip object into current Chip as a library.

        Args:
            lib_chip (Chip): An instance of Chip to import.
        '''
        self._import_library(lib_chip.design, lib_chip.cfg)

    ###########################################################################
    def _import_library(self, libname, libcfg):
        '''Helper to import library with config 'libconfig' as a library
        'libname' in current Chip object.'''
        self.cfg['library'][libname] = copy.deepcopy(libcfg)
        if 'pdk' in self.cfg['library'][libname]:
            del self.cfg['library'][libname]['pdk']

    ###########################################################################
    def write_depgraph(self, filename):
        '''
        Writes the package dependency tree to disk.

        Supported graphical render formats include png, svg, gif, pdf and a
        few others. (see https://graphviz.org for more information).

        Supported text formats include .md, .rst. (see the Linux 'tree'
        command for more information).

        '''

        return(0)

    ###########################################################################

    def write_flowgraph(self, filename, flow=None,
                        fillcolor='#ffffff', fontcolor='#000000',
                        fontsize='14', border=True, landscape=False):
        '''Renders and saves the compilation flowgraph to a file.

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
        for step in self.getkeys('flowgraph',flow):
            irange = 0
            for index in self.getkeys('flowgraph', flow, step):
                irange = irange +1
            for i in range(irange):
                index = str(i)
                node = step+index
                # create step node
                tool =  self.get('flowgraph', flow, step, index, 'tool')
                if tool in self.builtin:
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
                for in_step, in_index in self.get('flowgraph', flow, step, index, 'input'):
                    all_inputs.append(in_step + in_index)
                for item in all_inputs:
                    dot.edge(item, node)
        dot.render(filename=fileroot, cleanup=True)

    ########################################################################
    def _collect_paths(self):
        '''
        Returns list of paths to files that will be collected by import step.

        See docstring for _collect() for more details.
        '''
        paths = []

        copyall = self.get('option', 'copyall')
        allkeys = self.getkeys()
        for key in allkeys:
            if key[0] == 'history':
                continue
            leaftype = self.get(*key, field='type')
            if re.search('file', leaftype):
                copy = self.get(*key, field='copy')
                value = self.get(*key)
                if copyall or copy:
                    for item in value:
                        paths.append(item)

        return paths

    ########################################################################
    def _collect(self, step, index):
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

        indir = 'inputs'

        if not os.path.exists(indir):
            os.makedirs(indir)

        self.logger.info('Collecting input sources')

        for path in self._collect_paths():
            filename = self._get_imported_filename(path)
            abspath = self._find_sc_file(path)
            if abspath:
                self.logger.info(f"Copying {abspath} to '{indir}' directory")
                shutil.copy(abspath, os.path.join(indir, filename))
            else:
                self._haltstep(step, index)

    ###########################################################################
    def archive(self, step=None, index=None, all_files=False):
        '''Archive a job directory.

        Creates a single compressed archive (.tgz) based on the design,
        jobname, and flowgraph in the current chip manifest. Individual
        steps and/or indices can be archived based on argumnets specified.
        By default, all steps and indices in the flowgraph are archived.
        By default, only the outputs directory content and the log file
        are archived.

        Args:
            step(str): Step to archive.
            index (str): Index to archive
            all_files (bool): If True, all files are archived.

        '''

        design = self.get('design')
        jobname = self.get('option', 'jobname')
        buildpath = self.get('option', 'builddir')
        flow = self.get('option', 'flow')

        if step:
            steplist = [step]
        elif self.get('arg', 'step'):
            steplist = [self.get('arg', 'step')]
        elif self.get('option', 'steplist'):
            steplist = self.get('option', 'steplist')
        else:
            steplist = self.list_steps()

        if step:
            archive_name = f"{design}_{jobname}_{step}.tgz"
        else:
            archive_name = f"{design}_{jobname}.tgz"

        with tarfile.open(archive_name, "w:gz") as tar:
            for step in steplist:
                if index:
                    indexlist = [index]
                else:
                    indexlist = self.getkeys('flowgraph', flow, step)
                for item in indexlist:
                    basedir = os.path.join(buildpath, design, jobname, step, item)
                    if all_files:
                         tar.add(os.path.abspath(basedir), arcname=basedir)
                    else:
                        outdir = os.path.join(basedir,'outputs')
                        logfile = os.path.join(basedir, step+'.log')
                        tar.add(os.path.abspath(outdir), arcname=outdir)
                        if os.path.isfile(logfile):
                            tar.add(os.path.abspath(logfile), arcname=logfile)

        return archive_name

    ###########################################################################
    def hash_files(self, *keypath, algo='sha256', update=True):
        '''Generates hash values for a list of parameter files.

        Generates a a hash value for each file found in the keypath.
        If the  update variable is True, the has values are recorded in the
        'filehash' field of the parameter, following the order dictated by
        the files within the 'values' parameter field.

        Files are located using the find_files() function.

        The file hash calculation is performed basd on the 'algo' setting.
        Supported algorithms include SHA1, SHA224, SHA256, SHA384, SHA512,
        and MD5.

        Args:
            *keypath(str): Keypath to parameter.
            algo (str): Algorithm to use for file hash calculation
            update (bool): If True, the hash values are recorded in the
                chip object manifest.

        Returns:
            A list of hash values.

        Examples:
            >>> hashlist = hash_files('sources')
             Hashlist gets list of hash values computed from 'sources' files.
        '''

        keypathstr = ','.join(keypath)
        #TODO: Insert into find_files?
        if 'file' not in self.get(*keypath, field='type'):
            self.error(f"Illegal attempt to hash non-file parameter [{keypathstr}].")
        else:
            filelist = self.find_files(*keypath)
            #cycle through all paths
            hashlist = []
            if filelist:
                self.logger.info(f'Computing hash value for [{keypathstr}]')
            for filename in filelist:
                if os.path.isfile(filename):
                    #TODO: Implement algo selection
                    hashobj = hashlib.sha256()
                    with open(filename, "rb") as f:
                        for byte_block in iter(lambda: f.read(4096), b""):
                            hashobj.update(byte_block)
                    hash_value = hashobj.hexdigest()
                    hashlist.append(hash_value)
                else:
                    self.error(f"Internal hashing error, file not found")
            # compare previous hash to new hash
            oldhash = self.get(*keypath,field='filehash')
            for i,item in enumerate(oldhash):
                if item != hashlist[i]:
                    self.error(f"Hash mismatch for [{keypath}]")
            self.set(*keypath, hashlist, field='filehash', clobber=True)


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
    def calc_area(self):
        '''Calculates the area of a rectilinear diearea.

        Uses the shoelace formulate to calculate the design area using
        the (x,y) point tuples from the 'diearea' parameter. If only diearea
        paramater only contains two points, then the first and second point
        must be the lower left and upper right points of the rectangle.
        (Ref: https://en.wikipedia.org/wiki/Shoelace_formula)

        Returns:
            Design area (float).

        Examples:
            >>> area = chip.calc_area()

        '''

        vertices = self.get('asic', 'diearea')

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
    def calc_yield(self, model='poisson'):
        '''Calculates raw die yield.

        Calculates the raw yield of the design as a function of design area
        and d0 defect density. Calculation can be done based on the poisson
        model (default) or the murphy model. The die area and the d0
        parameters are taken from the chip dictionary.

        * Poisson model: dy = exp(-area * d0/100).
        * Murphy model: dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.

        Args:
            model (string): Model to use for calculation (poisson or murphy)

        Returns:
            Design yield percentage (float).

        Examples:
            >>> yield = chip.calc_yield()
            Yield variable gets yield value based on the chip manifest.
        '''

        d0 = self.get('pdk', 'd0')
        diearea = self.calc_area()

        if model == 'poisson':
            dy = math.exp(-diearea * d0/100)
        elif model == 'murphy':
            dy = ((1-math.exp(-diearea * d0/100))/(diearea * d0/100))**2

        return dy

    ##########################################################################
    def calc_dpw(self):
        '''Calculates dies per wafer.

        Calculates the gross dies per wafer based on the design area, wafersize,
        wafer edge margin, and scribe lines. The calculation is done by starting
        at the center of the wafer and placing as many complete design
        footprints as possible within a legal placement area.

        Returns:
            Number of gross dies per wafer (int).

        Examples:
            >>> dpw = chip.calc_dpw()
            Variable dpw gets gross dies per wafer value based on the chip manifest.
        '''

        #PDK information
        wafersize = self.get('pdk', 'wafersize')
        edgemargin = self.get('pdk', 'edgemargin')
        hscribe = self.get('pdk', 'hscribe')
        vscribe = self.get('pdk', 'vscribe')

        #Design parameters
        diesize = self.get('asic', 'diesize').split()
        diewidth = (diesize[2] - diesize[0])/1000
        dieheight = (diesize[3] - diesize[1])/1000

        #Derived parameters
        radius = wafersize/2 -edgemargin
        stepwidth = (diewidth + hscribe)
        stepheight = (dieheight + vscribe)

        #Raster dies out from center until you touch edge margin
        #Work quadrant by quadrant
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
            #loop through all y values from center
            while math.hypot(0, y) < radius:
                y = y + yincr
                while math.hypot(x, y) < radius:
                    x = x + xincr
                    dies = dies + 1
                x = 0

        return int(dies)

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
            '-v' : False, # Invert the sense of matching
            '-i' : False, # Ignore case distinctions in patterns and data
            '-E' : False, # Interpret PATTERNS as extended regular expressions.
            '-e' : False, # Safe interpretation of pattern starting with "-"
            '-x' : False, # Select only matches that exactly match the whole line.
            '-o' : False, # Print only the match parts of a matching line
            '-w' : False} # Select only lines containing matches that form whole words.

        # Split into repeating switches and everything else
        match = re.match(r'\s*((?:\-\w\s)*)(.*)', args)

        pattern = match.group(2)

        # Split space separated switch string into list
        switches = match.group(1).strip().split(' ')

        # Find special -e switch update the pattern
        for i in range(len(switches)):
            if switches[i] == "-e":
                if i != (len(switches)):
                    pattern = ' '.join(switches[i+1:]) + " " + pattern
                    switches = switches[0:i+1]
                    break
                options["-e"] = True
            elif switches[i] in options.keys():
                options[switches[i]] = True
            elif switches[i] !='':
                print("ERROR",switches[i])

        #REGEX
        #TODO: add all the other optinos
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
        '<design>.<suffix>' in the current directory. The matches are logged
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

        tool = self.get('flowgraph', flow, step, index, 'tool')

        # Creating local dictionary (for speed)
        # self.get is slow
        checks = {}
        matches = {}
        regex_list = []
        if self.valid('tool', tool, 'regex', step, index, 'default'):
            regex_list = self.getkeys('tool', tool, 'regex', step, index)
        for suffix in regex_list:
            checks[suffix] = {}
            checks[suffix]['report'] = open(f"{step}.{suffix}", "w")
            checks[suffix]['args'] = self.get('tool', tool, 'regex', step, index, suffix)
            matches[suffix] = 0

        # Looping through patterns for each line
        with open(logfile, errors='ignore_with_warning') as f:
            for line in f:
                for suffix in checks:
                    string = line
                    for item in checks[suffix]['args']:
                        if string is None:
                            break
                        else:
                            string = self.grep(item, string)
                    if string is not None:
                        matches[suffix] += 1
                        #always print to file
                        print(string.strip(), file=checks[suffix]['report'])
                        #selectively print to display
                        if display:
                                if suffix == 'errors':
                                    self.logger.error(string.strip())
                                elif suffix == 'warnings':
                                    self.logger.warning(string.strip())
                                else:
                                    self.logger.info(f'{suffix}: {string.strip()}')

        for suffix in checks:
            checks[suffix]['report'].close()

        return matches

    ###########################################################################
    def _find_leaves(self, steplist):
        '''Helper to find final (leaf) tasks for a given steplist.'''
        flow = self.get('option', 'flow')

        # First, iterate over the tasks to generate a set of non-leaf tasks.
        all_tasks = set()
        non_leaf_tasks = set()
        for step in steplist:
            for index in self.getkeys('flowgraph', flow, step):
                all_tasks.add((step, index))
                for in_step, in_index in self.get('flowgraph', flow, step, index, 'input'):
                    if in_step in steplist:
                        non_leaf_tasks.add((in_step, in_index))

        # Then, find all leaf tasks by elimination.
        return all_tasks.difference(non_leaf_tasks)

    ###########################################################################
    def summary(self, steplist=None, show_all_indices=False):
        '''
        Prints a summary of the compilation manifest.

        Metrics from the flowgraph steps, or steplist parameter if
        defined, are printed out on a per step basis. All metrics from the
        metric dictionary with weights set in the flowgraph dictionary are
        printed out.

        Args:
            show_all_indices (bool): If True, displays metrics for all indices
                of each step. If False, displays metrics only for winning
                indices.

        Examples:
            >>> chip.summary()
            Prints out a summary of the run to stdout.
        '''

        # display whole flowgraph if no steplist specified
        flow = self.get('option', 'flow')
        if not steplist:
            if self.get('option', 'steplist'):
                steplist = self.get('option', 'steplist')
            else:
                steplist = self.list_steps()

        # Find all tasks that are part of a "winning" path.
        selected_tasks = set()
        to_search = []

        # Start search with any successful leaf tasks.
        leaf_tasks = self._find_leaves(steplist)
        for task in leaf_tasks:
            if self.get('flowgraph', flow, *task, 'status') == TaskStatus.SUCCESS:
                selected_tasks.add(task)
                to_search.append(task)

        # Search backwards, saving anything that was selected by leaf tasks.
        while len(to_search) > 0:
            task = to_search.pop(-1)
            for selected in self.get('flowgraph', flow, *task, 'select'):
                if selected not in selected_tasks:
                    selected_tasks.add(selected)
                    to_search.append(selected)

        # only report tool based steps functions
        for step in steplist.copy():
            if self.get('flowgraph',flow, step,'0','tool') in self.builtin:
                index = steplist.index(step)
                del steplist[index]

        # job directory
        jobdir = self._getworkdir()

        # Custom reporting modes
        paramlist = []
        for item in self.getkeys('option', 'param'):
            paramlist.append(item+"="+self.get('option', 'param', item))

        if paramlist:
            paramstr = ', '.join(paramlist)
        else:
            paramstr = "None"

        info_list = ["SUMMARY:\n",
                     "design : " + self.top(),
                     "params : " + paramstr,
                     "jobdir : "+ jobdir,
                     ]

        if self.get('option', 'mode') == 'asic':
            pdk = self.get('option', 'pdk')
            info_list.extend(["foundry : " + self.get('pdk', pdk, 'foundry'),
                              "process : " + pdk,
                              "targetlibs : "+" ".join(self.get('asic', 'logiclib'))])
        elif self.get('option', 'mode') == 'fpga':
            info_list.extend(["partname : "+self.get('fpga','partname')])

        info = '\n'.join(info_list)


        print("-"*135)
        print(info, "\n")

        # Stepping through all steps/indices and printing out metrics
        data = []

        #Creating Header
        header = []
        indices_to_show = {}
        colwidth = 8
        for step in steplist:
            if show_all_indices:
                indices_to_show[step] = self.getkeys('flowgraph', flow, step)
            else:
                indices_to_show[step] = []
                for index in self.getkeys('flowgraph', flow, step):
                    if (step, index) in selected_tasks:
                        indices_to_show[step].append(index)

        # header for data frame
        for step in steplist:
            for index in indices_to_show[step]:
                header.append(f'{step}{index}'.center(colwidth))

        # Gather data and determine which metrics to show
        # We show a metric if:
        # - it is not in ['option', 'metricoff'] -AND-
        # - at least one step in the steplist has a non-zero weight for the metric -OR -
        #   at least one step in the steplist set a value for it
        metrics_to_show = []
        for metric in self.getkeys('metric', 'default', 'default'):
            if metric in self.get('option', 'metricoff'):
                continue

            row = []
            show_metric = False
            for step in steplist:
                for index in indices_to_show[step]:
                    if (
                        metric in self.getkeys('flowgraph', flow, step, index, 'weight') and
                        self.get('flowgraph', flow, step, index, 'weight', metric)
                    ):
                        show_metric = True

                    value = self.get('metric', step, index, metric)
                    if value is None:
                        value = '---'
                    else:
                        value = str(value)
                        show_metric = True

                    row.append(" " + value.center(colwidth))

            if show_metric:
                metrics_to_show.append(metric)
                data.append(row)

        pandas.set_option('display.max_rows', 500)
        pandas.set_option('display.max_columns', 500)
        pandas.set_option('display.width', 100)
        metrics = [" " + metric for metric in metrics_to_show]
        df = pandas.DataFrame(data, metrics, header)
        print(df.to_string())
        print("-"*135)

        # Create a report for the Chip object which can be viewed in a web browser.
        # Place report files in the build's root directory.
        web_dir = self._getworkdir()
        if os.path.isdir(web_dir):
            # Gather essential variables.
            templ_dir = os.path.join(self.scroot, 'templates', 'report')
            design = self.top()
            flow = self.get('option', 'flow')
            flow_steps = steplist
            flow_tasks = {}
            for step in flow_steps:
                flow_tasks[step] = self.getkeys('flowgraph', flow, step)

            # Call 'show()' to generate a low-res PNG of the design.
            img_data = None
            # Need to be able to search for something showable by KLayout,
            # otherwise the extra_options don't make sense.
            filename = self._find_showable_output('klayout')
            if filename and not self.get('option', 'nodisplay'):
                success = self.show(filename, ['-rd', 'screenshot=1', '-rd', 'scr_w=1024', '-rd', 'scr_h=1024', '-z'])
                result_file = os.path.join(web_dir, f'{design}.png')
                # Result might not exist if there is no display
                if success and os.path.isfile(result_file):
                    with open(result_file, 'rb') as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')

            # Generate results page by passing the Chip manifest into the Jinja2 template.
            env = Environment(loader=FileSystemLoader(templ_dir))
            results_page = os.path.join(web_dir, 'report.html')
            pruned_cfg = self._prune(self.cfg)
            if 'history' in pruned_cfg:
                del pruned_cfg['history']
            if 'library' in pruned_cfg:
                del pruned_cfg['library']

            # Hardcode the encoding, since there's a Unicode character in a
            # Bootstrap CSS file inlined in this template. Without this setting,
            # this write may raise an encoding error on machines where the
            # default encoding is not UTF-8.
            with open(results_page, 'w', encoding='utf-8') as wf:
                wf.write(env.get_template('sc_report.j2').render(
                    manifest = self.cfg,
                    pruned_cfg = pruned_cfg,
                    metric_keys = metrics_to_show,
                    metrics = self.cfg['metric'],
                    tasks = flow_tasks,
                    img_data = img_data,
                ))

            # Try to open the results and layout only if '-nodisplay' is not set.
            if not self.get('option', 'nodisplay'):
                try:
                    webbrowser.get(results_page)
                except webbrowser.Error:
                    # Python 'webbrowser' module includes a limited number of popular defaults.
                    # Depending on the platform, the user may have defined their own with $BROWSER.
                    if 'BROWSER' in os.environ:
                        subprocess.run([os.environ['BROWSER'], results_page])
                    else:
                        self.logger.warning('Unable to open results page in web browser:\n' +
                                            os.path.abspath(os.path.join(web_dir, "report.html")))

    ###########################################################################
    def list_steps(self, flow=None):
        '''
        Returns an ordered list of flowgraph steps.

        All step keys from the flowgraph dictionary are collected and the
        distance from the root node (ie. without any inputs defined) is
        measured for each step. The step list is then sorted based on
        the distance from root and returned.

        Returns:
            A list of steps sorted by distance from the root node.

        Example:
            >>> steplist = chip.list_steps()
            Variable steplist gets list of steps sorted by distance from root.
        '''

        if flow is None:
            flow = self.get('option', 'flow')

        #Get length of paths from step to root
        depth = {}
        for step in self.getkeys('flowgraph', flow):
            depth[step] = 0
            for path in self._allpaths(self.cfg, flow, step, str(0)):
                if len(list(path)) > depth[step]:
                    depth[step] = len(path)

        #Sort steps based on path lenghts
        sorted_dict = dict(sorted(depth.items(), key=lambda depth: depth[1]))
        return list(sorted_dict.keys())

    ###########################################################################
    def _allpaths(self, cfg, flow, step, index, path=None):
        '''Recursive helper for finding all paths from provided step, index to
        root node(s) with no inputs.

        Returns a list of lists.
        '''

        if path is None:
            path = []

        inputs = self.get('flowgraph', flow, step, index, 'input', cfg=cfg)

        if not self.get('flowgraph', flow, step, index, 'input', cfg=cfg):
            return [path]
        else:
            allpaths = []
            for in_step, in_index in inputs:
                newpath = path.copy()
                newpath.append(in_step + in_index)
                allpaths.extend(self._allpaths(cfg, flow, in_step, in_index, path=newpath))

        return allpaths

    ###########################################################################
    def clock(self, pin, period, jitter=0):
        """
        Clock configuration helper function.

        A utility function for setting all parameters associated with a
        single clock definition in the schema.

        The method modifies the following schema parameters:

        ['datasheet', name, 'pin']
        ['datasheet', name, 'period']
        ['datasheet', name, 'jitter']

        Args:
            pin (str): Full hiearchical path to clk pin.
            period (float): Clock period specified in ns.
            jitter (float): Clock jitter specified in ns.

        Examples:
            >>> chip.clock('clk, period=1.0)
           Create a clock named 'clk' with a 1.0ns period.
        """
        design = self.top()
        self.set('datasheet', design, 'pin', pin, 'type', 'global', 'clk')

        period_range = (period * 1e-9, period * 1e-9, period * 1e-9)
        self.set('datasheet', design, 'pin', pin, 'tperiod', 'global', period_range)

        jitter_range = (jitter * 1e-9, jitter * 1e-9, jitter * 1e-9)
        self.set('datasheet', design, 'pin', pin, 'tjitter', 'global', jitter_range)

    ###########################################################################
    def node(self, flow, step, tool, index=0):
        '''
        Creates a flowgraph node.

        Creates a flowgraph node by binding a tool to a task. A task is defined
        as the combination of a step and index. A tool can be an external
        exeuctable or one of the built in functions in the SiliconCompiler
        framework). Built in functions include: minimum, maximum, join, mux,
        verify.

        The method modifies the following schema parameters:

        ['flowgraph', flow, step, index, 'tool', tool]
        ['flowgraph', flow, step, index, 'weight', metric]

        Args:
            flow (str): Flow name
            step (str): Task step name
            tool (str): Tool (or builtin function) to associate with task.
            index (int): Task index

        Examples:
            >>> chip.node('asicflow', 'place', 'openroad', index=0)
            Creates a task with step='place' and index=0 and binds it to the 'openroad' tool.
        '''

        # bind tool to node
        self.set('flowgraph', flow, step, str(index), 'tool', tool)
        # set default weights
        for metric in self.getkeys('metric', 'default', 'default'):
            self.set('flowgraph', flow, step, str(index), 'weight', metric, 0)

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

        # Handling connecting edges between graphs
        # Not completely name space safe, but feels like this limitation
        # is a non-issue

        module_tail = f"{tail}.export"
        module_head = f"{head}.import"
        if module_tail in self.getkeys('flowgraph',flow):
            tail = module_tail
        if module_head in self.getkeys('flowgraph',flow):
            head = module_head
        #TODO: add error checking
        # Adding
        self.add('flowgraph', flow, head, str(head_index), 'input', (tail, str(tail_index)))

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
            Instantiates Creates a directed edge from place to cts.
        '''

        if flow not in self.getkeys('flowgraph'):
            self.cfg['flowgraph'][flow] ={}

        # uniquify each step
        for step in self.getkeys('flowgraph',subflow):
            if name is None:
                newstep = step
            else:
                newstep = name + "." + step
            if newstep not in self.getkeys('flowgraph', flow):
                self.cfg['flowgraph'][flow][newstep] ={}
            # recursive copy
            for key in self._allkeys(self.cfg['flowgraph'][subflow][step]):
                self._copyparam(self.cfg['flowgraph'][subflow][step],
                                self.cfg['flowgraph'][flow][newstep],
                                key)
            # update step names
            for index in self.getkeys('flowgraph', flow, newstep):
                all_inputs = self.get('flowgraph', flow, newstep, index,'input')
                self.set('flowgraph', flow, newstep, index,'input',[])
                for in_step, in_index in all_inputs:
                    newin = name + "." + in_step
                    self.add('flowgraph', flow, newstep, index,'input',(newin,in_index))


    ###########################################################################
    def pipe(self, flow, plan):
        '''
        Creates a pipeline based on an order list of key values pairs.
        '''

        for item in plan:
            step = list(item.keys())[0]
            tool = list(item.values())[0]
            self.node(flow, step, tool)
            if step != 'import':
                self.edge(flow, prevstep, step)
            prevstep = step

    ###########################################################################
    def join(self, *tasks):
        '''
        Merges outputs from a list of input tasks.

        Args:
            tasks(list): List of input tasks specified as (step,index) tuples.

        Returns:
            Input list

        Examples:
            >>> select = chip.join([('lvs','0'), ('drc','0')])
           Select gets the list [('lvs','0'), ('drc','0')]
        '''

        tasklist = list(tasks)
        sel_inputs = tasklist

        # no score for join, so just return 0
        return sel_inputs

    ###########################################################################
    def nop(self, *task):
        '''
        A no-operation that passes inputs to outputs.

        Args:
            task(list): Input task specified as a (step,index) tuple.

        Returns:
            Input task

        Examples:
            >>> select = chip.nop(('lvs','0'))
           Select gets the tuple [('lvs',0')]
        '''

        return list(task)

    ###########################################################################
    def minimum(self, *tasks):
        '''
        Selects the task with the minimum metric score from a list of inputs.

        Sequence of operation:

        1. Check list of input tasks to see if all metrics meets goals
        2. Check list of input tasks to find global min/max for each metric
        3. Select MIN value if all metrics are met.
        4. Normalize the min value as sel = (val - MIN) / (MAX - MIN)
        5. Return normalized value and task name

        Meeting metric goals takes precedence over compute metric scores.
        Only goals with values set and metrics with weights set are considered
        in the calculation.

        Args:
            tasks(list): List of input tasks specified as (step,index) tuples.

        Returns:
            tuple containing

            - score (float): Minimum score
            - task (tuple): Task with minimum score

        Examples:
            >>> (score, task) = chip.minimum([('place','0'),('place','1')])

        '''
        return self._minmax(*tasks, op="minimum")

    ###########################################################################
    def maximum(self, *tasks):
        '''
        Selects the task with the maximum metric score from a list of inputs.

        Sequence of operation:

        1. Check list of input tasks to see if all metrics meets goals
        2. Check list of input tasks to find global min/max for each metric
        3. Select MAX value if all metrics are met.
        4. Normalize the min value as sel = (val - MIN) / (MAX - MIN)
        5. Return normalized value and task name

        Meeting metric goals takes precedence over compute metric scores.
        Only goals with values set and metrics with weights set are considered
        in the calculation.

        Args:
            tasks(list): List of input tasks specified as (step,index) tuples.

        Returns:
            tuple containing

            - score (float): Maximum score.
            - task (tuple): Task with minimum score

        Examples:
            >>> (score, task) = chip.maximum([('place','0'),('place','1')])

        '''
        return self._minmax(*tasks, op="maximum")

    ###########################################################################
    def _minmax(self, *steps, op="minimum", **selector):
        '''
        Shared function used for min and max calculation.
        '''

        if op not in ('minimum', 'maximum'):
            raise ValueError('Invalid op')

        flow = self.get('option', 'flow')
        steplist = list(steps)

        # Keeping track of the steps/indexes that have goals met
        failed = {}
        for step, index in steplist:
            if step not in failed:
                failed[step] = {}
            failed[step][index] = False

            if self.get('flowgraph', flow, step, index, 'status') == TaskStatus.ERROR:
                failed[step][index] = True
            else:
                for metric in self.getkeys('metric', step, index):
                    if self.valid('flowgraph', flow, step, index, 'goal', metric):
                        goal = self.get('flowgraph', flow, step, index, 'goal', metric)
                        real = self.get('metric', step, index, metric)
                        if real is None:
                            self.error(f'Metric {metric} has goal for {step}{index} '
                                'but it has not been set.', fatal=True)
                        if abs(real) > goal:
                            self.logger.warning(f"Step {step}{index} failed "
                                f"because it didn't meet goals for '{metric}' "
                                "metric.")
                            failed[step][index] = True

        # Calculate max/min values for each metric
        max_val = {}
        min_val = {}
        for metric in self.getkeys('flowgraph', flow, step, '0', 'weight'):
            max_val[metric] = 0
            min_val[metric] = float("inf")
            for step, index in steplist:
                if not failed[step][index]:
                    real = self.get('metric', step, index, metric)
                    if real is None:
                        continue
                    max_val[metric] = max(max_val[metric], real)
                    min_val[metric] = min(min_val[metric], real)

        # Select the minimum index
        best_score = float('inf') if op == 'minimum' else float('-inf')
        winner = None
        for step, index in steplist:
            if failed[step][index]:
                continue

            score = 0.0
            for metric in self.getkeys('flowgraph', flow, step, index, 'weight'):
                weight = self.get('flowgraph', flow, step, index, 'weight', metric)
                if not weight:
                    # skip if weight is 0 or None
                    continue

                real = self.get('metric', step, index, metric)
                if real is None:
                    self.error(f'Metric {metric} has weight for {step}{index} '
                        'but it has not been set.', fatal=True)

                if not (max_val[metric] - min_val[metric]) == 0:
                    scaled = (real - min_val[metric]) / (max_val[metric] - min_val[metric])
                else:
                    scaled = max_val[metric]
                score = score + scaled * weight

            if ((op == 'minimum' and score < best_score) or
                (op == 'maximum' and score > best_score)):
                best_score = score
                winner = (step,index)

        return (best_score, winner)

    ###########################################################################
    def verify(self, *tasks, **assertion):
        '''
        Tests an assertion on a list of input tasks.

        The provided steplist is verified to ensure that all assertions
        are True. If any of the assertions fail, False is returned.
        Assertions are passed in as kwargs, with the key being a metric
        and the value being a number and an optional conditional operator.
        The allowed conditional operators are: >, <, >=, <=

        Args:
            *steps (str): List of steps to verify
            **assertion (str='str'): Assertion to check on metric

        Returns:
            True if all assertions hold True for all steps.

        Example:
            >>> pass = chip.verify(['drc','lvs'], errors=0)
            Pass is True if the error metrics in the drc, lvs steps is 0.
        '''
        #TODO: implement
        return True

    ###########################################################################
    def mux(self, *tasks, **selector):
        '''
        Selects a task from a list of inputs.

        The selector criteria provided is used to create a custom function
        for selecting the best step/index pair from the inputs. Metrics and
        weights are passed in and used to select the step/index based on
        the minimum or maximum score depending on the 'op' argument.

        The function can be used to bypass the flows weight functions for
        the purpose of conditional flow execution and verification.

        Args:
            *steps (str): List of steps to verify
            **selector: Key value selection criteria.

        Returns:
            True if all assertions hold True for all steps.

        Example:
            >>> sel_stepindex = chip.mux(['route'], wirelength=0)
            Selects the routing stepindex with the shortest wirelength.
        '''

        #TODO: modify the _minmax function to feed in alternate weight path
        return None

    ###########################################################################
    def _runtask(self, step, index, status):
        '''
        Private per step run method called by run().

        The method takes in a step string and index string to indicated what
        to run.

        Execution flow:
        - Start wall timer
        - Defer job to compute node if using job scheduler
        - Set up working directory + chdir
        - Merge manifests from all input dependancies
        - Write manifest to input directory for convenience
        - Select inputs
        - Copy data from previous step outputs into inputs
        - Check manifest
        - Run pre_process() function
        - Set environment variables
        - Check EXE version
        - Save manifest as TCL/YAML
        - Start CPU timer
        - Run EXE
        - stop CPU timer
        - Run post_process()
        - Check log file
        - Hash all task files
        - Stop Wall timer
        - Make a task record
        - Save manifest to disk
        - Halt if any errors found
        - Clean up
        - chdir

        Note that since _runtask occurs in its own process with a separate
        address space, any changes made to the `self` object will not
        be reflected in the parent. We rely on reading/writing the chip manifest
        to the filesystem to communicate updates between processes.
        '''

        self._init_logger(step, index, in_run=True)

        ##################
        # Shared parameters (long function!)
        design = self.get('design')
        top = self.top()
        flow = self.get('option', 'flow')
        tool = self.get('flowgraph', flow, step, index, 'tool')
        quiet = self.get('option', 'quiet') and (step not in self.get('option', 'bkpt'))

        ##################
        # Start wall timer
        wall_start = time.time()

        ##################
        # Defer job to compute node
        # If the job is configured to run on a cluster, collect the schema
        # and send it to a compute node for deferred execution.
        # (Run the initial 'import' stage[s] locally)

        if self.get('option', 'jobscheduler') and \
           self.get('flowgraph', flow, step, index, 'input'):
            # Note: The _deferstep method blocks until the compute node
            # finishes processing this step, and it sets the active/error bits.
            _deferstep(self, step, index, status)
            return

        ##################
        # Directory setup
        # support for sharing data across jobs
        job = self.get('option', 'jobname')
        in_job = job
        if step in self.getkeys('option', 'jobinput'):
            if index in self.getkeys('option', 'jobinput', step):
                in_job = self.get('option', 'jobinput', step, index)

        workdir = self._getworkdir(step=step,index=index)
        cwd = os.getcwd()
        if os.path.isdir(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir, exist_ok=True)

        os.chdir(workdir)
        os.makedirs('outputs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        ##################
        # Merge manifests from all input dependancies

        all_inputs = []
        if not self.get('option', 'remote'):
            for in_step, in_index in self.get('flowgraph', flow, step, index, 'input'):
                in_task_status = status[in_step + in_index]
                self.set('flowgraph', flow, in_step, in_index, 'status', in_task_status)
                if in_task_status != TaskStatus.ERROR:
                    cfgfile = f"../../../{in_job}/{in_step}/{in_index}/outputs/{design}.pkg.json"
                    self._read_manifest(cfgfile, clobber=False, partial=True)

        ##################
        # Write manifest prior to step running into inputs

        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)
        os.makedirs('inputs', exist_ok=True)
        #self.write_manifest(f'inputs/{design}.pkg.json')

        ##################
        # Select inputs

        args = self.get('flowgraph', flow, step, index, 'args')
        inputs = self.get('flowgraph', flow, step, index, 'input')

        sel_inputs = []
        score = 0

        if tool in self.builtin:
            self.logger.info(f"Running built in task '{tool}'")
            # Figure out which inputs to select
            if tool == 'minimum':
                (score, sel_inputs) = self.minimum(*inputs)
            elif tool == "maximum":
                (score, sel_inputs) = self.maximum(*inputs)
            elif tool == "mux":
                (score, sel_inputs) = self.mux(*inputs, selector=args)
            elif tool == "join":
                sel_inputs = self.join(*inputs)
            elif tool == "verify":
                if not self.verify(*inputs, assertion=args):
                    self._haltstep(step, index)
        else:
            sel_inputs = self.get('flowgraph', flow, step, index, 'input')

        if sel_inputs == None:
            self.logger.error(f'No inputs selected after running {tool}')
            self._haltstep(step, index)

        self.set('flowgraph', flow, step, index, 'select', sel_inputs)

        ##################
        # Copy (link) output data from previous steps

        if step == 'import' and self.get('option', 'remote'):
            # Collect inputs into import directory only for remote runs, since
            # we need to send inputs up to the server. Otherwise, it's simpler
            # for debugging to leave inputs in place.
            self._collect(step, index)

        if not self.get('flowgraph', flow, step, index,'input'):
            all_inputs = []
        elif not self.get('flowgraph', flow, step, index, 'select'):
            all_inputs = self.get('flowgraph', flow, step, index,'input')
        else:
            all_inputs = self.get('flowgraph', flow, step, index, 'select')
        for in_step, in_index in all_inputs:
            if self.get('flowgraph', flow, in_step, in_index, 'status') == TaskStatus.ERROR:
                self.logger.error(f'Halting step due to previous error in {in_step}{in_index}')
                self._haltstep(step, index)

            # Skip copying pkg.json files here, since we write the current chip
            # configuration into inputs/{design}.pkg.json earlier in _runstep.
            utils.copytree(f"../../../{in_job}/{in_step}/{in_index}/outputs", 'inputs/', dirs_exist_ok=True,
                ignore=[f'{design}.pkg.json'], link=True)

        ##################
        # Check manifest
        self.set('arg', 'step', step, clobber=True)
        self.set('arg', 'index', index, clobber=True)

        if not self.get('option', 'skipcheck'):
            if not self.check_manifest():
                self.logger.error(f"Fatal error in check_manifest()! See previous errors.")
                self._haltstep(step, index)

        ##################
        # Run preprocess step for tool
        if tool not in self.builtin:
            func = self.find_function(tool, "pre_process", 'tools')
            if func:
                func(self)
                if self._error:
                    self.logger.error(f"Pre-processing failed for '{tool}'")
                    self._haltstep(step, index)

        ##################
        # Set environment variables

        # License file configuration.
        for item in self.getkeys('tool', tool, 'licenseserver'):
            license_file = self.get('tool', tool, 'licenseserver', item)
            if license_file:
                os.environ[item] = ':'.join(license_file)

        # Tool-specific environment variables for this task.
        if (step in self.getkeys('tool', tool, 'env')) and \
           (index in self.getkeys('tool', tool, 'env', step)):
            for item in self.getkeys('tool', tool, 'env', step, index):
                os.environ[item] = self.get('tool', tool, 'env', step, index, item)

        run_func = None
        if tool not in self.builtin:
            run_func = self.find_function(tool, 'run', 'tools')

        ##################
        # Check exe version

        vercheck = not self.get('option', 'novercheck')
        veropt = self.get('tool', tool, 'vswitch')
        exe = self._getexe(tool)
        version = None
        toolpath = exe # For record
        if exe is not None:
            exe_path, exe_base = os.path.split(exe)
            if veropt:
                cmdlist = [exe]
                cmdlist.extend(veropt)
                proc = subprocess.run(cmdlist, stdout=PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                parse_version = self.find_function(tool, 'parse_version', 'tools')
                if parse_version is None:
                    self.logger.error(f'{tool} does not implement parse_version.')
                    self._haltstep(step, index)
                version = parse_version(proc.stdout)

                self.logger.info(f"Tool '{exe_base}' found with version '{version}' in directory '{exe_path}'")
                if vercheck and not self._check_version(version, tool):
                    self._haltstep(step, index)
            else:
                self.logger.info(f"Tool '{exe_base}' found in directory '{exe_path}'")
        elif tool not in self.builtin and run_func is None:
            exe_base = self.get('tool', tool, 'exe')
            self.logger.error(f'Executable {exe_base} not found')
            self._haltstep(step, index)

        ##################
        # Write manifest (tool interface) (Don't move this!)
        suffix = self.get('tool', tool, 'format')
        if suffix:
            pruneopt = bool(suffix!='tcl')
            self.write_manifest(f"sc_manifest.{suffix}", prune=pruneopt, abspath=True)

        ##################
        # Start CPU Timer
        self.logger.debug(f"Starting executable")
        cpu_start = time.time()

        ##################
        # Run executable (or copy inputs to outputs for builtin functions)

        # TODO: Currently no memory usage tracking in breakpoints, builtins, or unexpected errors.
        max_mem_bytes = 0

        retcode = 0
        if tool in self.builtin:
            utils.copytree(f"inputs", 'outputs', dirs_exist_ok=True, link=True)
        elif run_func and not self.get('option', 'skipall'):
            retcode = run_func(self)
        elif not self.get('option', 'skipall'):
            cmdlist = self._makecmd(tool, step, index)
            exe_base = os.path.basename(cmdlist[0])
            cmdstr = ' '.join([exe_base] + cmdlist[1:])
            self.logger.info('Running in %s', workdir)
            self.logger.info('%s', cmdstr)
            timeout = self.get('flowgraph', flow, step, index, 'timeout')
            logfile = step + '.log'
            if sys.platform in ('darwin', 'linux') and step in self.get('option', 'bkpt'):
                # When we break on a step, the tool often drops into a shell.
                # However, our usual subprocess scheme seems to break terminal
                # echo for some tools. On POSIX-compatible systems, we can use
                # pty to connect the tool to our terminal instead. This code
                # doesn't handle quiet/timeout logic, since we don't want either
                # of these features for an interactive session. Logic for
                # forwarding to file based on
                # https://docs.python.org/3/library/pty.html#example.
                logfile = step + '.log'
                with open(logfile, 'wb') as log_writer:
                    def read(fd):
                        data = os.read(fd, 1024)
                        log_writer.write(data)
                        return data
                    import pty # Note: this import throws exception on Windows
                    retcode = pty.spawn(cmdlist, read)
            else:
                stdout_file = ''
                stdout_suffix = self.get('tool', tool, 'stdout', step, index, 'suffix')
                if self.get('tool', tool, 'stdout', step, index, 'destination') == 'log':
                    stdout_file = step + "." + stdout_suffix
                elif self.get('tool', tool, 'stdout', step, index, 'destination') == 'output':
                    stdout_file =  os.path.join('outputs', top + "." + stdout_suffix)
                elif self.get('tool', tool, 'stdout', step, index, 'destination') == 'none':
                    stdout_file =  os.devnull
                else:
                    destination = self.get('tool', tool, 'stdout', step, index, 'destination')
                    self.logger.error(f'stdout/destination has no support for {destination}. Use [log|output|none].')
                    self._haltstep(step, index)
                stderr_file = ''
                stderr_suffix = self.get('tool', tool, 'stderr', step, index, 'suffix')
                if self.get('tool', tool, 'stderr', step, index, 'destination') == 'log':
                    stderr_file = step + "." + stderr_suffix
                elif self.get('tool', tool, 'stderr', step, index, 'destination') == 'output':
                    stderr_file =  os.path.join('outputs', top + "." + stderr_suffix)
                elif self.get('tool', tool, 'stderr', step, index, 'destination') == 'none':
                    stderr_file =  os.devnull
                else:
                    destination = self.get('tool', tool, 'stderr', step, index, 'destination')
                    self.logger.error(f'stderr/destination has no support for {destination}. Use [log|output|none].')
                    self._haltstep(step, index)

                with open(stdout_file, 'w') as stdout_writer, \
                    open(stdout_file, 'r', errors='replace_with_warning') as stdout_reader,  \
                    open(stderr_file, 'w') as stderr_writer,  \
                    open(stderr_file, 'r', errors='replace_with_warning') as stderr_reader:
                    # Use separate reader/writer file objects as hack to display
                    # live output in non-blocking way, so we can monitor the
                    # timeout. Based on https://stackoverflow.com/a/18422264.
                    is_stdout_log = self.get('tool', tool, 'stdout', step, index, 'destination') == 'log'
                    is_stderr_log = self.get('tool', tool, 'stderr', step, index, 'destination') == 'log' and stderr_file != stdout_file
                    # if STDOUT and STDERR are to be redirected to the same file,
                    # use a single writer
                    if stderr_file == stdout_file:
                        stderr_writer.close()
                        stderr_reader.close()
                        stderr_writer = subprocess.STDOUT

                    cmd_start_time = time.time()
                    proc = subprocess.Popen(cmdlist,
                                            stdout=stdout_writer,
                                            stderr=stderr_writer)

                    while proc.poll() is None:
                        # Gather subprocess memory usage.
                        try:
                            pproc = psutil.Process(proc.pid)
                            max_mem_bytes = max(max_mem_bytes, pproc.memory_full_info().uss)
                        except psutil.Error:
                            # Process may have already terminated or been killed.
                            # Retain existing memory usage statistics in this case.
                            pass

                        # Loop until process terminates
                        if not quiet:
                            if is_stdout_log:
                                sys.stdout.write(stdout_reader.read())
                            if is_stderr_log:
                                sys.stdout.write(stderr_reader.read())
                        if timeout is not None and time.time() - cmd_start_time > timeout:
                            self.logger.error(f'Step timed out after {timeout} seconds')
                            proc.terminate()
                            self._haltstep(step, index)
                        time.sleep(0.1)

                    # Read the remaining
                    if not quiet:
                        if is_stdout_log:
                            sys.stdout.write(stdout_reader.read())
                        if is_stderr_log:
                            sys.stdout.write(stderr_reader.read())
                    retcode = proc.returncode

        if retcode != 0:
            self.logger.warning('Command failed with code %d. See log file %s', retcode, os.path.abspath(logfile))
            self._haltstep(step, index)

        ##################
        # Capture cpu runtime and memory footprint.
        cpu_end = time.time()
        cputime = round((cpu_end - cpu_start),2)
        self.set('metric', step, index, 'exetime', cputime)
        self.set('metric', step, index, 'memory', max_mem_bytes)

        ##################
        # Post process
        if (tool not in self.builtin) and (not self.get('option', 'skipall')) :
            func = self.find_function(tool, 'post_process', 'tools')
            if func:
                func(self)

        ##################
        # Check log file (must be after post-process)
        if (tool not in self.builtin) and (not self.get('option', 'skipall')) and (run_func is None):
            matches = self.check_logfile(step=step, index=index, display=not quiet)
            if 'errors' in matches:
                errors = self.get('metric', step, index, 'errors')
                if errors is None:
                    errors = 0
                errors += matches['errors']
                self.set('metric', step, index, 'errors', errors)
            if 'warnings' in matches:
                warnings = self.get('metric', step, index, 'warnings')
                if warnings is None:
                    warnings = 0
                warnings += matches['warnings']
                self.set('metric', step, index, 'warnings', warnings)

        ##################
        # Hash files
        if self.get('option', 'hash') and (tool not in self.builtin):
            # hash all outputs
            self.hash_files('tool', tool, 'output', step, index)
            # hash all requirements
            if self.valid('tool', tool, 'require', step, index, quiet=True):
                for item in self.get('tool', tool, 'require', step, index):
                    args = item.split(',')
                    if 'file' in self.get(*args, field='type'):
                        self.hash_files(*args)

        ##################
        # Capture wall runtime and cpu cores
        wall_end = time.time()
        walltime = round((wall_end - wall_start),2)
        self.set('metric',step, index, 'tasktime', walltime)
        self.logger.info(f"Finished task in {walltime}s")

        ##################
        # Make a record if tracking is enabled
        if self.get('option', 'track'):
            self._make_record(step, index, wall_start, wall_end, version, toolpath, cmdlist[1:])

        ##################
        # Save a successful manifest
        self.set('flowgraph', flow, step, index, 'status', TaskStatus.SUCCESS)
        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)

        self.write_manifest(os.path.join("outputs", f"{design}.pkg.json"))

        ##################
        # Stop if there are errors
        errors = self.get('metric', step, index, 'errors')
        if errors and not self.get('option', 'flowcontinue'):
            # TODO: should we warn if errors is not set?
            self.logger.error(f'{tool} reported {errors} errors during {step}{index}')
            self._haltstep(step, index)

        ##################
        # Clean up non-essential files
        if self.get('option', 'clean'):
            self._eda_clean(tool, step, index)

        ##################
        # return to original directory
        os.chdir(cwd)

    ###########################################################################
    def _haltstep(self, step, index, log=True):
        if log:
            self.logger.error(f"Halting step '{step}' index '{index}' due to errors.")
        sys.exit(1)

    ###########################################################################
    def _eda_clean(self, tool, step, index):
        '''Cleans up work directory of unecessary files.

        Assumes our cwd is the workdir for step and index.
        '''

        keep = ['inputs', 'outputs', 'reports', f'{step}.log', 'replay.sh']

        manifest_format = self.get('tool', tool, 'format')
        if manifest_format:
            keep.append(f'sc_manifest.{manifest_format}')

        if self.valid('tool', tool, 'regex', step, index, 'default'):
            for suffix in self.getkeys('tool', tool, 'regex', step, index):
                keep.append(f'{step}.{suffix}')

        # Tool-specific keep files
        if self.valid('tool', tool, 'keep', step, index):
            keep.extend(self.get('tool', tool, 'keep', step, index))

        for path in os.listdir():
            if path in keep:
                continue
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    ###########################################################################
    def _setup_tool(self, tool, step, index):
        self.set('arg','step', step)
        self.set('arg','index', index)

        func = self.find_function(tool, 'setup', 'tools')
        if func is None:
            self.logger.error(f'setup() not found for tool {tool}')
            sys.exit(1)
        func(self)

        # Add logfile as a report for errors/warnings if they have associated
        # regexes.
        if self.valid('tool', tool, 'regex', step, index, 'default'):
            re_keys = self.getkeys('tool', tool, 'regex', step, index)
            logfile = f'{step}.log'
            if (
                'errors' in re_keys and
                (not self.valid('tool', tool, 'report', step, index, 'errors') or
                 logfile not in self.get('tool', tool, 'report', step, index, 'errors'))
            ):
                self.add('tool', tool, 'report', step, index, 'errors', logfile)

            if (
                'warnings' in re_keys and
                (not self.valid('tool', tool, 'report', step, index, 'warnings') or
                 logfile not in self.get('tool', tool, 'report', step, index, 'warnings'))
            ):
                self.add('tool', tool, 'report', step, index, 'warnings', logfile)

        # Need to clear index, otherwise we will skip setting up other indices.
        # Clear step for good measure.
        self.set('arg','step', None)
        self.set('arg','index', None)

    ###########################################################################
    def run(self):
        '''
        Executes tasks in a flowgraph.

        The run function sets up tools and launches runs for every index
        in a step defined by a steplist. The steplist is taken from the schema
        steplist parameter if defined, otherwise the steplist is defined
        as the list of steps within the schema flowgraph dictionary. Before
        starting  the process, tool modules are loaded and setup up for each
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

        flow = self.get('option', 'flow')
        if flow is None:
            self.error("['option', 'flow'] must be set before calling run()",
                       fatal=True)

        # Auto-update jobname if ['option', 'jobincr'] is True
        # Do this before initializing logger so that it picks up correct jobname
        if self.get('option', 'jobincr'):
            workdir = self._getworkdir()
            if os.path.isdir(workdir):
                # Strip off digits following jobname, if any
                stem = self.get('option', 'jobname').rstrip('0123456789')

                designdir = os.path.dirname(workdir)
                jobid = 0
                for job in os.listdir(designdir):
                    m = re.match(stem + r'(\d+)', job)
                    if m:
                        jobid = max(jobid, int(m.group(1)))
                self.set('option', 'jobname', f'{stem}{jobid+1}')

        # Re-init logger to include run info after setting up flowgraph.
        self._init_logger(in_run=True)

        # Run steps if set, otherwise run whole graph
        if self.get('arg', 'step'):
            steplist = [self.get('arg', 'step')]
        elif self.get('option', 'steplist'):
            steplist = self.get('option', 'steplist')
        else:
            steplist = self.list_steps()

            if not self.get('option', 'resume'):
                # If no step(list) was specified, the whole flow is being run
                # start-to-finish. Delete the build dir to clear stale results.
                cur_job_dir = self._getworkdir()
                if os.path.isdir(cur_job_dir):
                    shutil.rmtree(cur_job_dir)

        # List of indices to run per step. Precomputing this ensures we won't
        # have any problems if [arg, index] gets clobbered, and reduces logic
        # repetition.
        indexlist = {}
        for step in steplist:
            if self.get('arg', 'index'):
                indexlist[step] = [self.get('arg', 'index')]
            elif self.get('option', 'indexlist'):
                indexlist[step] = self.get("option", 'indexlist')
            else:
                indexlist[step] = self.getkeys('flowgraph', flow, step)

        # Reset flowgraph/records/metrics by probing build directory. We need
        # to set values to None for steps we may re-run so that merging
        # manifests from _runtask() actually updates values.
        should_resume = self.get("option", 'resume')
        for step in self.getkeys('flowgraph', flow):
            all_indices_failed = True
            for index in self.getkeys('flowgraph', flow, step):
                stepdir = self._getworkdir(step=step, index=index)
                cfg = f"{stepdir}/outputs/{self.get('design')}.pkg.json"

                in_steplist = step in steplist and index in indexlist[step]
                if not os.path.isdir(stepdir) or (in_steplist and not should_resume):
                    # If stepdir doesn't exist, we need to re-run this task. If
                    # we're not running with -resume, we also re-run anything
                    # in the steplist.
                    self.set('flowgraph', flow, step, index, 'status', None)
                    for metric in self.getkeys('metric', 'default', 'default'):
                        self.set('metric', step, index, metric, None)
                    for record in self.getkeys('record', 'default', 'default'):
                        self.set('record', step, index, record, None)
                elif os.path.isfile(cfg):
                    self.set('flowgraph', flow, step, index, 'status', TaskStatus.SUCCESS)
                    all_indices_failed = False
                else:
                    self.set('flowgraph', flow, step, index, 'status', TaskStatus.ERROR)

            if should_resume and all_indices_failed and step in steplist:
                # When running with -resume, we re-run any step in steplist that
                # had all indices fail.
                for index in self.getkeys('flowgraph', flow, step):
                    if index in indexlist[step]:
                        self.set('flowgraph', flow, step, index, 'status', None)
                        for metric in self.getkeys('metric', 'default', 'default'):
                            self.set('metric', step, index, metric,  None)
                        for record in self.getkeys('record', 'default', 'default'):
                            self.set('record', step, index, record, None)

        # Set env variables
        for envvar in self.getkeys('option', 'env'):
            val = self.get('option', 'env', envvar)
            os.environ[envvar] = val

        # Remote workflow: Dispatch the Chip to a remote server for processing.
        if self.get('option','remote'):
            # Load the remote storage config into the status dictionary.
            if self.get('option','credentials'):
                # Use the provided remote credentials file.
                cfg_file = self.get('option','credentials')[-1]
                cfg_dir = os.path.dirname(cfg_file)
            else:
                # Use the default config file path.
                cfg_dir = os.path.join(Path.home(), '.sc')
                cfg_file = os.path.join(cfg_dir, 'credentials')
            if (not os.path.isdir(cfg_dir)) or (not os.path.isfile(cfg_file)):
                self.error('Could not find remote server configuration - '
                    'please run "sc-configure" and enter your server address and '
                    'credentials.', fatal=True)
            with open(cfg_file, 'r') as cfgf:
                self.status['remote_cfg'] = json.loads(cfgf.read())
            if (not 'address' in self.status['remote_cfg']):
                self.error('Improperly formatted remote server configuration - '
                    'please run "sc-configure" and enter your server address and '
                    'credentials.', fatal=True)

            # Pre-process: Run an 'import' stage locally, and upload the
            # in-progress build directory to the remote server.
            # Data is encrypted if user / key were specified.
            # run remote process
            remote_preprocess(self)

            # Run the job on the remote server, and wait for it to finish.
            remote_run(self)

            # Fetch results (and delete the job's data from the server).
            fetch_results(self)

            # Read back configuration from final manifest.
            cfg = os.path.join(self._getworkdir(),f"{self.get('design')}.pkg.json")
            if os.path.isfile(cfg):
                local_dir = self.get('option','builddir')
                self.read_manifest(cfg, clobber=True, clear=True)
                self.set('option', 'builddir', local_dir)
            else:
                # Hack to find first failed step by checking for presence of
                # output manifests.
                # TODO: fetch_results() should return info about step failures.
                failed_step = steplist[-1]
                for step in steplist[:-1]:
                    step_has_cfg = False
                    for index in indexlist[step]:
                        stepdir = self._getworkdir(step=step, index=index)
                        cfg = f"{stepdir}/outputs/{self.get('design')}.pkg.json"
                        if os.path.isfile(cfg):
                            step_has_cfg = True
                            break

                    if not step_has_cfg:
                        failed_step = step
                        break

                stepdir = self._getworkdir(step=failed_step)[:-1]
                self.error(f'Run() failed on step {failed_step}! '
                    f'See logs in {stepdir} for error details.', fatal=True)
        else:
            status = {}

            # Populate status dict with any flowgraph status values that have already
            # been set.
            for step in self.getkeys('flowgraph', flow):
                for index in self.getkeys('flowgraph', flow, step):
                    stepstr = step + index
                    task_status = self.get('flowgraph', flow, step, index, 'status')
                    if task_status is not None:
                        status[step + index] = task_status
                    else:
                        status[step + index] = TaskStatus.PENDING

            # Setup tools for all tasks to run.
            for step in steplist:
                for index in indexlist[step]:
                    # Setting up tool is optional
                    tool = self.get('flowgraph', flow, step, index, 'tool')
                    if tool not in self.builtin:
                        self._setup_tool(tool, step, index)

            # Check validity of setup
            self.logger.info("Checking manifest before running.")
            check_ok = True
            if not self.get('option','skipcheck'):
                check_ok = self.check_manifest()

            # Check if there were errors before proceeding with run
            if not check_ok:
                self.error('Manifest check failed. See previous errors.', fatal=True)
            if self._error:
                self.error('Implementation errors encountered. See previous errors.', fatal=True)

            # For each task to run, prepare a process and store its dependencies
            jobname = self.get('option','jobname')
            tasks_to_run = {}
            processes = {}
            for step in steplist:
                for index in indexlist[step]:
                    if status[step+index] != TaskStatus.PENDING:
                        continue

                    inputs = [step+index for step, index in self.get('flowgraph', flow, step, index, 'input')]

                    if (step in self.getkeys('option','jobinput') and
                        index in self.getkeys('option','jobinput', step) and
                        self.get('option','jobinput', step, index) != jobname):
                        # If we specify a different job as input to this task,
                        # we assume we are good to run it.
                        tasks_to_run[step+index] = []
                    else:
                        tasks_to_run[step+index] = inputs

                    processes[step+index] = multiprocessing.Process(target=self._runtask,
                                                                    args=(step, index, status))


            # We have to deinit the chip's logger before spawning the processes
            # since the logger object is not serializable. _runtask_safe will
            # reinitialize the logger in each new process, and we reinitialize
            # the primary chip's logger after the processes complete.
            self._deinit_logger()

            running_tasks = []
            while len(tasks_to_run) > 0 or len(running_tasks) > 0:
                # Check for new tasks that can be launched.
                for task, deps in list(tasks_to_run.items()):
                    # TODO: breakpoint logic:
                    # if task is bkpt, then don't launch while len(running_tasks) > 0

                    # Clear any tasks that have finished from dependency list.
                    for in_task in deps.copy():
                        if status[in_task] != TaskStatus.PENDING:
                            deps.remove(in_task)

                    # If there are no dependencies left, launch this task and
                    # remove from tasks_to_run.
                    if len(deps) == 0:
                        processes[task].start()
                        running_tasks.append(task)
                        del tasks_to_run[task]

                # Check for situation where we have stuff left to run but don't
                # have any tasks running. This shouldn't happen, but we will get
                # stuck in an infinite loop if it does, so we want to break out
                # with an explicit error.
                if len(tasks_to_run) > 0 and len(running_tasks) == 0:
                    self.error('Tasks left to run, but no '
                        'running tasks. Steplist may be invalid.', fatal=True)

                # Check for completed tasks.
                # TODO: consider staying in this section of loop until a task
                # actually completes.
                for task in running_tasks.copy():
                    if not processes[task].is_alive():
                        running_tasks.remove(task)
                        if processes[task].exitcode > 0:
                            status[task] = TaskStatus.ERROR
                        else:
                            status[task] = TaskStatus.SUCCESS

                # TODO: exponential back-off with max?
                time.sleep(0.1)

            self._init_logger()

            # Make a clean exit if one of the steps failed
            for step in steplist:
                index_succeeded = False
                for index in indexlist[step]:
                    stepstr = step + index
                    if status[stepstr] != TaskStatus.ERROR:
                        index_succeeded = True
                        break

                if not index_succeeded:
                    self.error('Run() failed, see previous errors.', fatal=True)

            # On success, write out status dict to flowgraph status. We do this
            # since certain scenarios won't be caught by reading in manifests (a
            # failing step doesn't dump a manifest). For example, if the
            # steplist's final step has two indices and one fails.
            for step in steplist:
                for index in indexlist[step]:
                    stepstr = step + index
                    if status[stepstr] != TaskStatus.PENDING:
                        self.set('flowgraph', flow, step, index, 'status', status[stepstr])


            # Merge cfg back from last executed tasks.
            for step, index in self._find_leaves(steplist):
                lastdir = self._getworkdir(step=step, index=index)

                # This no-op listdir operation is important for ensuring we have
                # a consistent view of the filesystem when dealing with NFS.
                # Without this, this thread is often unable to find the final
                # manifest of runs performed on job schedulers, even if they
                # completed successfully. Inspired by:
                # https://stackoverflow.com/a/70029046.

                os.listdir(os.path.dirname(lastdir))

                lastcfg = f"{lastdir}/outputs/{self.get('design')}.pkg.json"
                if status[step+index] == TaskStatus.SUCCESS:
                    self._read_manifest(lastcfg, clobber=False, partial=True)
                else:
                    self.set('flowgraph', flow, step, index, 'status', TaskStatus.ERROR)

        # Clear scratchpad args since these are checked on run() entry
        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)

        # Store run in history
        self.record_history()

        # Storing manifest in job root directory
        filepath =  os.path.join(self._getworkdir(),f"{self.get('design')}.pkg.json")
        self.write_manifest(filepath)

    ##########################################################################
    def record_history(self):
        '''
        Copies all non-empty parameters from current job into the history
        dictionary.
        '''

        # initialize new dict
        jobname = self.get('option','jobname')
        self.cfg['history'][jobname] = {}

        # copy in all empty values of scope job
        allkeys = self.getkeys()
        for key in allkeys:
            # ignore history in case of cumulative history
            if key[0] != 'history':
                scope = self.get(*key, field='scope')
                if not self._keypath_empty(key) and (scope == 'job'):
                    self._copyparam(self.cfg,
                                    self.cfg['history'][jobname],
                                    key)

    ###########################################################################
    def _copyparam(self, cfgsrc, cfgdst, keypath):
        '''
        Copies a parameter into the manifest history dictionary.
        '''

        # 1. decend keypath, pop each key as its used
        # 2. create key if missing in destination dict
        # 3. populate leaf cell when keypath empty
        if keypath:
            key = keypath[0]
            keypath.pop(0)
            if key not in cfgdst.keys():
                cfgdst[key] = {}
            self._copyparam(cfgsrc[key], cfgdst[key], keypath)
        else:
            for key in cfgsrc.keys():
                if key not in ('example', 'switch', 'help'):
                    cfgdst[key] = copy.deepcopy(cfgsrc[key])

    ###########################################################################
    def _find_showable_output(self, tool=None):
        '''
        Helper function for finding showable layout based on schema.

        This code is used by show() and HTML report generation in summary().

        We could potentially refine this but for now it returns the first file
        in 'output' that has a showtool. If the optional 'tool' arg is defined,
        this showtool must match 'tool'. Returns None if no match found.

        Considered using ['model', 'layout', ...], but that includes abstract
        views (and we probably want to prioritize final layouts like
        DEF/GDS/OAS).
        '''
        for key in self.getkeys('output'):
            for output in self.find_files('output', key):
                file_ext = utils.get_file_ext(output)
                if file_ext in self.getkeys('option', 'showtool'):
                    if not tool or self.get('option', 'showtool', file_ext) == tool:
                        return output
        return None

    ###########################################################################
    def show(self, filename=None, extra_options=None):
        '''
        Opens a graphical viewer for the filename provided.

        The show function opens the filename specified using a viewer tool
        selected based on the file suffix and the 'showtool' schema setup.  The
        'showtool' parameter binds tools with file suffixes, enabling the
        automated dynamic loading of tool setup functions. Display settings and
        technology settings for viewing the file are read from the in-memory
        chip object schema settings. All temporary render and display files are
        saved in the <build_dir>/_show directory.

        Filenames with .gz extensions are automatically unpacked before being
        displayed.

        Args:
            filename: Name of file to display

        Examples:
            >>> show('build/oh_add/job0/export/0/outputs/oh_add.gds')
            Displays gds file with a viewer assigned by 'showtool'
        '''

        if extra_options is None:
            extra_options = []

        # Finding last layout if no argument specified
        if filename is None:
            self.logger.info('Searching build directory for layout to show.')
            design = self.top()
            # TODO: keeping the below logic for backwards compatibility. Once
            # all flows/examples register their outputs in ['output', ...], we
            # can fully switch over to the generic logic.
            laststep = 'export'
            lastindex = '0'
            lastdir = self._getworkdir(step=laststep, index=lastindex)
            gds_file= f"{lastdir}/outputs/{design}.gds"
            def_file = f"{lastdir}/outputs/{design}.def"
            if os.path.isfile(gds_file):
                filename = gds_file
            elif os.path.isfile(def_file):
                filename = def_file
            else:
                # Generic logic
                filename = self._find_showable_output()

        if filename is None:
            self.logger.error('Unable to automatically find layout in build directory.')
            self.logger.error('Try passing in a full path to show() instead.')
            return False

        self.logger.info('Showing file %s', filename)

        # Parsing filepath
        filepath = os.path.abspath(filename)
        filetype = utils.get_file_ext(filepath)
        localfile = os.path.basename(filepath)
        if localfile.endswith('.gz'):
            localfile = os.path.splitext(localfile)[0]

        #Check that file exists
        if not os.path.isfile(filepath):
            self.logger.error(f"Invalid filepath {filepath}.")
            return False

        # Opening file from temp directory
        cwd = os.getcwd()
        showdir = self.get('option','builddir') + "/_show"
        os.makedirs(showdir, exist_ok=True)
        os.chdir(showdir)

        # Uncompress file if necessary
        if os.path.splitext(filepath)[1].lower() == ".gz":
            with gzip.open(filepath, 'rb') as f_in:
                with open(localfile, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy(filepath, localfile)

        #Figure out which tool to use for opening data
        if filetype in self.getkeys('option','showtool'):
            # Using env variable and manifest to pass arguments
            os.environ['SC_FILENAME'] = localfile
            # Setting up tool
            tool = self.get('option','showtool', filetype)
            step = 'show'+filetype
            index = "0"
            self.set('arg', 'step', step)
            self.set('arg', 'index', index)
            setup_tool = self.find_function(tool, 'setup', 'tools')
            setup_tool(self, mode='show')
            self.write_manifest("sc_manifest.tcl", abspath=True)
            self.write_manifest("sc_manifest.json", abspath=True)
            self.set('arg', 'step', None)
            self.set('arg', 'index', None)

            exe = self._getexe(tool)
            if shutil.which(exe) is None:
                self.logger.error(f'Executable {exe} not found.')
                success = False
            else:
                # Running command
                cmdlist = self._makecmd(tool, step, index, extra_options=extra_options)
                proc = subprocess.run(cmdlist)
                success = proc.returncode == 0
        else:
            self.logger.error(f"Filetype '{filetype}' not set up in 'showtool' parameter.")
            success = False

        # Returning to original directory
        os.chdir(cwd)
        return success

    def read_lef(self, path, pdkname, stackup):
        '''Reads tech LEF and imports data into schema.

        This function reads layer information from a provided tech LEF and uses
        it to fill out the 'pdk', <pdkname>, 'grid' keypaths of the current chip
        object.

        Args:
            path (str): Path to LEF file.
            pdkname (str): Name of PDK associated with LEF file.
            stackup (str): Stackup associated with LEF file.
        '''
        data = leflib.parse(path)
        layer_index = 1
        for name, layer in data['layers'].items():
            if layer['type'] != 'ROUTING':
                # Skip non-routing layers
                continue

            sc_name = f'm{layer_index}'
            layer_index += 1
            self.set('pdk', pdkname, 'grid', stackup, name, 'name', sc_name)

            direction = None
            if 'direction' in layer:
                direction = layer['direction'].lower()
                self.set('pdk', pdkname, 'grid', stackup, name, 'dir', direction)

            if 'offset' in layer:
                offset = layer['offset']
                if isinstance(offset, float):
                    # Per LEF spec, a single offset value applies to the
                    # preferred routing direction. If one doesn't exist, we'll
                    # just ignore.
                    if direction == 'vertical':
                        self.set('pdk', pdkname, 'grid', stackup, name, 'xoffset', offset)
                    elif direction == 'horizontal':
                        self.set('pdk', pdkname, 'grid', stackup, name, 'yoffset', offset)
                else:
                    xoffset, yoffset = offset
                    self.set('pdk', pdkname, 'grid', stackup, name, 'xoffset', xoffset)
                    self.set('pdk', pdkname, 'grid', stackup, name, 'yoffset', yoffset)

            if 'pitch' in layer:
                pitch = layer['pitch']
                if isinstance(pitch, float):
                    # Per LEF spec, a single pitch value applies to both
                    # directions.
                    self.set('pdk', pdkname, 'grid', stackup, name, 'xpitch', pitch)
                    self.set('pdk', pdkname, 'grid', stackup, name, 'ypitch', pitch)
                else:
                    xpitch, ypitch = pitch
                    self.set('pdk', pdkname, 'grid', stackup, name, 'xpitch', xpitch)
                    self.set('pdk', pdkname, 'grid', stackup, name, 'ypitch', ypitch)

    ############################################################################
    # Chip helper Functions
    ############################################################################
    def _typecheck(self, cfg, leafkey, value):
        ''' Schema type checking
        '''
        ok = True
        valuetype = type(value)
        errormsg = ""
        if (not re.match(r'\[',cfg['type'])) & (valuetype==list):
            errormsg = "Value must be scalar."
            ok = False
            # Iterate over list
        else:
            # Create list for iteration
            if valuetype == list:
                valuelist = value
            else:
                valuelist = [value]
                # Make type python compatible
            cfgtype = re.sub(r'[\[\]]', '', cfg['type'])
            for item in valuelist:
                valuetype =  type(item)
                if ((cfgtype != valuetype.__name__) and (item is not None)):
                    tupletype = re.match(r'\([\w\,]+\)',cfgtype)
                    #TODO: check tuples!
                    if tupletype:
                        pass
                    elif cfgtype == 'bool':
                        if not item in ['true', 'false']:
                            errormsg = "Valid boolean values are True/False/'true'/'false'"
                            ok = False
                    elif cfgtype == 'file':
                        pass
                    elif cfgtype == 'dir':
                        pass
                    elif (cfgtype == 'float'):
                        try:
                            float(item)
                        except:
                            errormsg = "Type mismatch. Cannot cast item to float."
                            ok = False
                    elif (cfgtype == 'int'):
                        try:
                            int(item)
                        except:
                            errormsg = "Type mismatch. Cannot cast item to int."
                            ok = False
                    elif item is not None:
                        errormsg = "Type mismach."
                        ok = False

        # Logger message
        if type(value) == list:
            printvalue = ','.join(map(str, value))
        else:
            printvalue = str(value)
        errormsg = (errormsg +
                    " Key=" + str(leafkey) +
                    ", Expected Type=" + cfg['type'] +
                    ", Entered Type=" + valuetype.__name__ +
                    ", Value=" + printvalue)


        return (ok, errormsg)

    #######################################
    def _getexe(self, tool):
        path = self.get('tool', tool, 'path')
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
    def _makecmd(self, tool, step, index, extra_options=None):
        '''
        Constructs a subprocess run command based on eda tool setup.
        Creates a replay script in current directory.
        '''

        fullexe = self._getexe(tool)

        options = []
        is_posix = (sys.platform != 'win32')

        for option in self.get('tool', tool, 'option', step, index):
            options.extend(shlex.split(option, posix=is_posix))

        # Add scripts files
        if self.valid('tool', tool, 'script', step, index):
            scripts = self.find_files('tool', tool, 'script', step, index)
        else:
            scripts = []

        cmdlist = [fullexe]
        if extra_options:
            cmdlist.extend(extra_options)
        cmdlist.extend(options)
        cmdlist.extend(scripts)
        runtime_options = self.find_function(tool, 'runtime_options', 'tools')
        if runtime_options:
            for option in runtime_options(self):
                cmdlist.extend(shlex.split(option, posix=is_posix))

        envvars = {}
        for key in self.getkeys('option','env'):
            envvars[key] = self.get('option','env', key)
        for item in self.getkeys('tool', tool, 'licenseserver'):
            license_file = self.get('tool', tool, 'licenseserver', item)
            if license_file:
                envvars[item] = ':'.join(license_file)
        if self.get('tool', tool, 'path'):
            envvars['PATH'] = self.get('tool', tool, 'path') + os.pathsep + '$PATH'
        else:
            envvars['PATH'] = os.environ['PATH']
        if (step in self.getkeys('tool', tool, 'env') and
            index in self.getkeys('tool', tool, 'env', step)):
            for key in self.getkeys('tool', tool, 'env', step, index):
                envvars[key] = self.get('tool', tool, 'env', step, index, key)

        #create replay file
        script_name = 'replay.sh'
        with open(script_name, 'w') as f:
            print('#!/bin/bash', file=f)

            envvar_cmd = 'export'
            for key, val in envvars.items():
                print(f'{envvar_cmd} {key}={val}', file=f)

            replay_cmdlist = [os.path.basename(cmdlist[0])] + cmdlist[1:]
            print(' '.join(f'"{arg}"' if ' ' in arg else arg for arg in replay_cmdlist), file=f)
        os.chmod(script_name, 0o755)

        return cmdlist

    #######################################
    def _get_cloud_region(self):
        # TODO: add logic to figure out if we're running on a remote cluster and
        # extract the region in a provider-specific way.
        return 'local'

    #######################################
    def _make_record(self, step, index, start, end, toolversion, toolpath, cli_args):
        '''
        Records provenance details for a runstep.
        '''
        self.set('record', step, index, 'scversion', _metadata.version)

        start_date = datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S')
        end_date = datetime.datetime.fromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S')

        userid = getpass.getuser()
        self.set('record', step, index, 'userid', userid)

        if toolversion:
            self.set('record', step, index, 'toolversion', toolversion)

        self.set('record', step, index, 'starttime', start_date)
        self.set('record', step, index, 'endtime', end_date)

        machine = platform.node()
        self.set('record', step, index, 'machine', machine)

        self.set('record', step, index, 'region', self._get_cloud_region())

        try:
            gateways = netifaces.gateways()
            ipaddr, interface = gateways['default'][netifaces.AF_INET]
            macaddr = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
            self.set('record', step, index, 'ipaddr', ipaddr)
            self.set('record', step, index, 'macaddr', macaddr)
        except KeyError:
            self.logger.warning('Could not find default network interface info')

        system = platform.system()
        if system == 'Darwin':
            lower_sys_name = 'macos'
        else:
            lower_sys_name = system.lower()
        self.set('record', step, index, 'platform', lower_sys_name)

        if system == 'Linux':
            distro_name = distro.id()
            self.set('record', step, index, 'distro', distro_name)

        if system == 'Darwin':
            osversion, _, _ = platform.mac_ver()
        elif system == 'Linux':
            osversion = distro.version()
        else:
            osversion = platform.release()
        self.set('record', step, index, 'osversion', osversion)

        if system == 'Linux':
            kernelversion = platform.release()
        elif system == 'Windows':
            kernelversion = platform.version()
        elif system == 'Darwin':
            kernelversion = platform.release()
        else:
            kernelversion = None
        if kernelversion:
            self.set('record', step, index, 'kernelversion', kernelversion)

        arch = platform.machine()
        self.set('record', step, index, 'arch', arch)

        self.set('record', step, index, 'toolpath', toolpath)

        toolargs = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cli_args)
        self.set('record', step, index, 'toolargs', toolargs)

    #######################################
    def _safecompare(self, value, op, goal):
        # supported relational oprations
        # >, >=, <=, <. ==, !=
        if op == ">":
            return(bool(value>goal))
        elif op == ">=":
            return(bool(value>=goal))
        elif op == "<":
            return(bool(value<goal))
        elif op == "<=":
            return(bool(value<=goal))
        elif op == "==":
            return(bool(value==goal))
        elif op == "!=":
            return(bool(value!=goal))
        else:
            self.error(f"Illegal comparison operation {op}")


    #######################################
    def _getworkdir(self, jobname=None, step=None, index='0'):
        '''Create a step directory with absolute path
        '''

        if jobname is None:
            jobname = self.get('option','jobname')

        dirlist =[self.cwd,
                  self.get('option','builddir'),
                  self.get('design'),
                  jobname]

        # Return jobdirectory if no step defined
        # Return index 0 by default
        if step is not None:
            dirlist.append(step)
            dirlist.append(index)

        return os.path.join(*dirlist)

    #######################################
    def _resolve_env_vars(self, filepath):
        resolved_path = os.path.expandvars(filepath)

        # variables that don't exist in environment get ignored by `expandvars`,
        # but we can do our own error checking to ensure this doesn't result in
        # silent bugs
        envvars = re.findall(r'\$(\w+)', resolved_path)
        for var in envvars:
            self.logger.warning(f'Variable {var} in {filepath} not defined in environment')

        return resolved_path

    #######################################
    def _get_imported_filename(self, pathstr):
        ''' Utility to map collected file to an unambigious name based on its path.

        The mapping looks like:
        path/to/file.ext => file_<md5('path/to/file.ext')>.ext
        '''
        path = pathlib.Path(pathstr)
        ext = ''.join(path.suffixes)

        # strip off all file suffixes to get just the bare name
        while path.suffix:
            path = pathlib.Path(path.stem)
        filename = str(path)

        pathhash = hashlib.sha1(pathstr.encode('utf-8')).hexdigest()

        return f'{filename}_{pathhash}{ext}'

    def _check_version(self, reported_version, tool):
        # Based on regex for deprecated "legacy specifier" from PyPA packaging
        # library. Use this to parse PEP-440ish specifiers with arbitrary
        # versions.
        _regex_str = r"""
            (?P<operator>(==|!=|<=|>=|<|>|~=))
            \s*
            (?P<version>
                [^,;\s)]* # Since this is a "legacy" specifier, and the version
                          # string can be just about anything, we match everything
                          # except for whitespace, a semi-colon for marker support,
                          # a closing paren since versions can be enclosed in
                          # them, and a comma since it's a version separator.
            )
            """
        _regex = re.compile(r"^\s*" + _regex_str + r"\s*$", re.VERBOSE | re.IGNORECASE)

        normalize_version = self.find_function(tool, 'normalize_version', 'tools')
        # Version is good if it matches any of the specifier sets in this list.
        spec_sets = self.get('tool', tool, 'version')

        for spec_set in spec_sets:
            split_specs = [s.strip() for s in spec_set.split(",") if s.strip()]
            specs_list = []
            for spec in split_specs:
                match = re.match(_regex, spec)
                if match is None:
                    self.logger.warning(f'Invalid version specifier {spec}. Defaulting to =={spec}.')
                    operator = '=='
                    spec_version = spec
                else:
                    operator = match.group('operator')
                    spec_version = match.group('version')
                specs_list.append((operator, spec_version))

            if normalize_version is None:
                normalized_version = reported_version
                normalized_specs = ','.join([f'{op}{ver}' for op, ver in specs_list])
            else:
                normalized_version = normalize_version(reported_version)
                normalized_specs = ','.join([f'{op}{normalize_version(ver)}' for op, ver in specs_list])

            try:
                version = packaging.version.Version(normalized_version)
            except packaging.version.InvalidVersion:
                self.logger.error(f'Version {reported_version} reported by {tool} does not match standard.')
                if normalize_version is None:
                    self.logger.error('Tool driver should implement normalize_version().')
                else:
                    self.logger.error(f'normalize_version() returned invalid version {normalized_version}')

                return False

            try:
                spec_set = packaging.specifiers.SpecifierSet(normalized_specs)
            except packaging.specifiers.InvalidSpecifier:
                self.logger.error(f'Version specifier set {normalized_specs} does not match standard.')
                return False

            if version in spec_set:
                return True

        allowedstr = '; '.join(spec_sets)
        self.logger.error(f"Version check failed for {tool}. Check installation.")
        self.logger.error(f"Found version {reported_version}, did not satisfy any version specifier set {allowedstr}.")
        return False

    def error(self, msg, fatal=False):
        '''Raises error.

        If fatal is False and :keypath:`option, continue` is set to True, this
        will log an error and set an internal error flag that will cause run()
        to quit. Otherwise, this will raise a SiliconCompilerError.

        Args:
            msg (str): Message associated with error
            fatal (bool): Whether error is always fatal
        '''
        if not fatal and self.get('option', 'continue'):
            self.logger.error(msg)
            self._error = True
            return

        raise SiliconCompilerError(msg)

###############################################################################
# Package Customization classes
###############################################################################

class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)

class SiliconCompilerError(Exception):
    ''' Minimal Exception wrapper used to raise sc runtime errors.
    '''
    def __init__(self, message):
        super(Exception, self).__init__(message)
