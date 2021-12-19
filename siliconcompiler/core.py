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
from pathlib import Path
from timeit import default_timer as timer
from siliconcompiler.client import *
from siliconcompiler.schema import *
from siliconcompiler.scheduler import _deferstep
from siliconcompiler import utils

from siliconcompiler import _metadata

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
    def __init__(self, design=None, loglevel="INFO"):

        # Local variables
        self.scroot = os.path.dirname(os.path.abspath(__file__))
        self.cwd = os.getcwd()
        self.error = 0
        self.cfg = schema_cfg()
        self.cfghistory = {}
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
                        'mux', 'join', 'verify']

        # We set 'design' and 'loglevel' directly in the config dictionary
        # because of a chicken-and-egg problem: self.set() relies on the logger,
        # but the logger relies on these values.
        self.cfg['design']['value'] = design
        self.cfg['loglevel']['value'] = loglevel
        # We set scversion directly because it has its 'lock' flag set by default.
        self.cfg['version']['sc']['value'] = _metadata.version

        self._init_logger()

    ###########################################################################
    def _init_logger(self, step=None, index=None):

        self.logger = logging.getLogger(uuid.uuid4().hex)

        # Don't propagate log messages to "root" handler (we get duplicate
        # messages without this)
        # TODO: this prevents us from being able to capture logs with pytest:
        # we should revisit it
        self.logger.propagate = False

        loglevel = self.get('loglevel')

        jobname = self.get('jobname')
        if jobname == None:
            jobname = '---'

        if step == None:
            step = '---'
        if index == None:
            index = '-'

        run_info = '%-7s | %-12s | %-3s' % (jobname, step, index)

        if loglevel=='DEBUG':
            logformat = '| %(levelname)-7s | %(funcName)-10s | %(lineno)-4s | ' + run_info + ' | %(message)s'
        else:
            logformat = '| %(levelname)-7s | ' + run_info + ' | %(message)s'

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
    def create_cmdline(self, progname, description=None, switchlist=[]):
        """Creates an SC command line interface.

        Exposes parameters in the SC schema as command line switches,
        simplifying creation of SC apps with a restricted set of schema
        parameters exposed at the command line. The order of command
        line switch settings parsed from the command line is as follows:

         1. design
         2. loglevel
         3. mode
         4. target('target')
         5. read_manifest([cfg])
         6. all other switches

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
                 available.  Parameter switches should be entered without
                 '-', based on the parameter 'switch' field in the 'schema'.

        Examples:
            >>> chip.create_cmdline(progname='sc-show',switchlist=['source','cfg'])
            Creates a command line interface for 'sc-show' app.

        """

        # Argparse
        parser = argparse.ArgumentParser(prog=progname,
                                         prefix_chars='-+',
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         description=description)



        # Get all keys from global dictionary or override at command line
        allkeys = self.getkeys()

        # Iterate over all keys to add parser argument
        for key in allkeys:
            #Fetch fields from leaf cell
            helpstr = self.get(*key, field='shorthelp')
            typestr = self.get(*key, field='type')
            #Switch field fully describes switch format
            switch = self.get(*key, field='switch')
            if switch is not None:
                switchmatch = re.match(r'(-[\w_]+)\s+(.*)', switch)
                gccmatch = re.match(r'(-[\w_]+)(.*)', switch)
                plusmatch = re.match(r'(\+[\w_\+]+)(.*)', switch)
                if switchmatch:
                    switchstr = switchmatch.group(1)
                    if re.search('_', switchstr):
                        dest = re.sub('-','',switchstr)
                    else:
                        dest = key[0]
                elif gccmatch:
                    switchstr = gccmatch.group(1)
                    dest = key[0]
                elif plusmatch:
                    switchstr = plusmatch.group(1)
                    dest = key[0]
            else:
                switchstr = None
                dest = None

            #Four switch types (source, scalar, list, bool)
            if ('source' not in key) & ((switchlist == []) | (dest in switchlist)):
                if typestr == 'bool':
                    parser.add_argument(switchstr,
                                        metavar='',
                                        dest=dest,
                                        action='store_const',
                                        const="true",
                                        help=helpstr,
                                        default=argparse.SUPPRESS)
                #list type arguments
                elif re.match(r'\[', typestr):
                    #all the rest
                    parser.add_argument(switchstr,
                                        metavar='',
                                        dest=dest,
                                        action='append',
                                        help=helpstr,
                                        default=argparse.SUPPRESS)
                else:
                    #all the rest
                    parser.add_argument(switchstr,
                                        metavar='',
                                        dest=dest,
                                        help=helpstr,
                                        default=argparse.SUPPRESS)


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


        # exit on version check
        if '-version' in scargs:
            print(_metadata.version)
            sys.exit(0)

        # Required positional source file argument
        if ((switchlist == []) &
            (not '-cfg' in scargs)) | ('source' in switchlist) :
            parser.add_argument('source',
                                nargs='+',
                                help=self.get('source', field='shorthelp'))

        #Grab argument from pre-process sysargs
        #print(scargs)
        cmdargs = vars(parser.parse_args(scargs))
        #print(cmdargs)
        #sys.exit()

        # Print banner
        print(_metadata.banner)
        print("Authors:", ", ".join(_metadata.authors))
        print("Version:", _metadata.version, "\n")
        print("-"*80)

        os.environ["COLUMNS"] = '80'

        # 1. set design name (override default)
        if 'design' in cmdargs.keys():
            self.name = cmdargs['design']

        # 2. set loglevel if set at command line
        if 'loglevel' in cmdargs.keys():
            self.logger.setLevel(cmdargs['loglevel'])

        # 3. read in target if set
        if 'target' in cmdargs.keys():
            if 'mode' in cmdargs.keys():
                self.set('mode', cmdargs['mode'], clobber=True)
            if 'techarg' in cmdargs.keys():
                print("NOT IMPLEMENTED")
                sys.exit()
            if 'flowarg' in cmdargs.keys():
                print("NOT IMPLEMENTED")
                sys.exit()
            if 'arg_step' in cmdargs.keys():
                self.set('arg', 'step', cmdargs['arg_step'], clobber=True)
            # running target command
            self.target(cmdargs['target'])

        # 4. read in all cfg files
        if 'cfg' in cmdargs.keys():
            for item in cmdargs['cfg']:
                self.read_manifest(item, update=True, clobber=True, clear=True)

        # insert all parameters in dictionary
        self.logger.info('Setting commandline arguments')
        allkeys = self.getkeys()

        for key, val in cmdargs.items():



            # Unifying around no underscores for now
            keylist = key.split('_')

            orderhash = {}
            # Find keypath with matching keys
            for keypath in allkeys:
                match = True
                for item in keylist:
                    if item in keypath:
                        orderhash[item] = keypath.index(item)
                    else:
                        match = False
                if match:
                    chosenpath = keypath
                    break

            # Turn everything into a list for uniformity
            if isinstance(val, list):
                val_list = val
            else:
                val_list = [val]

            for item in val_list:
                #space used to separate values!
                extrakeys = item.split(' ')
                for i in range(len(extrakeys)):
                    # look for the first default statement
                    # "delete' default in temp list by setting to None
                    if 'default' in chosenpath:
                        next_default = chosenpath.index('default')
                        orderhash[extrakeys[i]] = next_default
                        chosenpath[next_default] = None
                    else:
                        # Creating a sorted list based on key placement
                        args = list(dict(sorted(orderhash.items(),
                                                key=lambda orderhash: orderhash[1])))
                        # Adding data value
                        args = args + [extrakeys[i]]
                        # Set/add value based on type

                        #Check that keypath is valid
                        if self.valid(*args[:-1], quiet=True):
                            if re.match(r'\[', self.get(*args[:-1], field='type')):
                                self.add(*args)
                            else:
                                self.set(*args, clobber=True)
                        else:
                            self.set(*args, clobber=True)

    #########################################################################
    def create_env(self):
        '''
        Creates a working environment for interactive design.

        Sets environment variables and initializees tools specific
        setup files based on paramater set loaded.

        Actions taken:

          * Append values found in eda 'path' parameter to current path
          *

        '''

        # Add paths
        env_path = os.environ['PATH']
        for tool in self.getkeys('eda'):
            for path in self.get('eda', tool):
                env_path = env_path +  os.pathsep + path

        # Call setup_env functions
        for tool in self.getkeys('eda'):
            for step in self.getkeys('eda', tool):
                setup_env = self.find_function(tool, 'tool', 'setup_env')
                if setup_env:
                    setup_env(self)


    #########################################################################
    def find_function(self, modulename, functype, funcname):
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

        Supported functions include:

        * pdk (make_docs, setup_pdk)
        * flow (make_docs, setup_flow)
        * tool (make_docs, setup_tool, check_version, runtime_options,
          pre_process, post_process)

        Args:
            modulename (str): Name of module to import.
            functype (str): Type of function to import (tool,flow, pdk).
            funcname (str): Name of the function to find within the module.

        Examples:
            >>> setup_pdk = chip.find_function('freepdk45','pdk','setup_pdk')
            >>> setup_pdk()
            Imports the freepdk45 module and runs the setup_pdk function

        '''

        # module search path depends on functype
        if functype == 'tool':
            fullpath = self._find_sc_file(f"tools/{modulename}/{modulename}.py", missing_ok=True)
        elif functype == 'flow':
            fullpath = self._find_sc_file(f"flows/{modulename}.py", missing_ok=True)
        elif functype == 'pdk':
            fullpath = self._find_sc_file(f"pdks/{modulename}.py", missing_ok=True)
        elif functype == 'project':
            fullpath = self._find_sc_file(f"projects/{modulename}.py", missing_ok=True)
        else:
            self.logger.error(f"Illegal module type '{functype}'.")
            self.error = 1
            return

        # try loading module if found
        if fullpath:
            if functype == 'tool':
                self.logger.debug(f"Loading function '{funcname}' from module '{modulename}'")
            else:
                self.logger.info(f"Loading function '{funcname}' from module '{modulename}'")
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
                self.logger.error(f"Module setup failed for '{modulename}'")
                self.error = 1

    ###########################################################################
    def target(self, name=None):
        """
        Configures the compilation manifest based on pre-defined target modules.

        The target function imports and executes a set of setup functions based
        on a '_' separated string. The following target string combinations are
        permitted:

        * <projname>
        * <flowname>
        * <flowname>_<pdkname>
        * <flowname>_<partname> (for fpga flows)
        * <pdk>
        * <tool>
        * <tool>_<pdkname>

        If no target name is provided, the target will be read from the
        'target' schema parameter. Calling target() with no target name provided
        and an undefined 'target' parameter results in an error.

        The target function uses the find_function() method to import and
        execute setup functions based on the 'scpath' search parameter.


        Args:
            name (str): Name of target combination to load.

        Examples:
            >>> chip.target("asicflow_freepdk45")
            Loads the 'freepdk45' and 'asicflow' setup functions.
            >>> chip.target()
            Loads target based on result from chip.get('target')

        """

        #Sets target in dictionary if string is passed in
        if name is not None:
            self.set('target', name)

        # Error checking
        if not self.get('target'):
            self.logger.error('Target not defined.')
            sys.exit(1)
        elif len(self.get('target').split('_')) > 2:
            self.logger.error('Target should have zero or one underscore')
            sys.exit(1)

        target = self.get('target')
        self.logger.info(f"Loading target '{target}'")

        # search for module matches
        targetlist = target.split('_')

        for i, item in enumerate(targetlist):
            if i == 0:
                func_project = self.find_function(item, 'project', 'setup_project')
                if func_project is not None:
                    func_project(self)
                    if len(targetlist) > 1:
                        self.logger.error('Target string beginning with a project name '
                                          'must only have one entry')
                        sys.exit(1)
                    break

                func_flow = self.find_function(item, 'flow', 'setup_flow')
                if func_flow is not None:
                    func_flow(self)
                    continue

                func_pdk = self.find_function(item, 'pdk', 'setup_pdk')
                if func_pdk is not None:
                    func_pdk(self)
                    if len(targetlist) > 1:
                        self.logger.error('Target string beginning with a PDK name '
                                          'must only have one entry')
                        sys.exit(1)
                    break

                func_tool = self.find_function(item, 'tool', 'setup_tool')
                if func_tool is not None:
                    step = self.get('arg','step')
                    self.set('flowgraph', step, '0', 'tool', item)
                    self.set('flowgraph', step, '0', 'weight', 'errors', 0)
                    self.set('flowgraph', step, '0', 'weight', 'warnings', 0)
                    self.set('flowgraph', step, '0', 'weight', 'runtime', 0)

                    # We must always have an import step, so add a default no-op
                    # if need be.
                    if step != 'import':
                        self.set('flowgraph', 'import', '0', 'tool', 'join')
                        self.set('flowgraph', step, '0', 'input', ('import','0'))

                    self.set('arg', 'step', None)

                    continue

                self.logger.error(f'Target {item} not found')
                sys.exit(1)
            else:
                func_pdk = self.find_function(item, 'pdk', 'setup_pdk')
                if func_pdk is not None:
                    func_pdk(self)
                    break

                # Only an error if we're not in FPGA mode. Otherwise, we assume
                # the second item is a partname, which will be read directly
                # from the target by the FPGA flow logic.
                if self.get('mode') != 'fpga':
                    self.logger.error(f'PDK {item} not found')
                    sys.exit(1)

        if self.get('mode') is not None:
            self.logger.info(f"Operating in '{self.get('mode')}' mode")
        else:
            self.logger.warning(f"No mode set")


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
                   "\nExamples:    " + example[0] +
                   "\n             " + example[1] +
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

        Returns a schema parameter filed based on the keypath and value provided
        in the ``*args``. The returned type is consistent with the type field of
        the parameter. Fetching parameters with empty or undefined value files
        returns None for scalar types and [] (empty list) for list types.
        Accessing a non-existent keypath produces a logger error message and
        raises the Chip object error flag.

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
                cfg = self.cfghistory[job]
            else:
                cfg = self.cfg

        keypathstr = ','.join(keypath)

        self.logger.debug(f"Reading from [{keypathstr}]. Field = '{field}'")
        return self._search(cfg, keypathstr, *keypath, field=field, mode='get')

    ###########################################################################
    def getkeys(self, *keypath, cfg=None):
        """
        Returns a list of schema dictionary keys.

        Searches the schema for the keypath provided and returns a list of
        keys found, excluding the generic 'default' key. Accessing a
        non-existent keypath produces a logger error message and raises the
        Chip object error flag.

        Args:
            keypath(list str): Variable length ordered schema key list
            cfg(dict): Alternate dictionary to access in place of self.cfg

        Returns:
            List of keys found for the keypath provided.

        Examples:
            >>> keylist = chip.getkeys('pdk')
            Returns all keys for the 'pdk' keypath.
            >>> keylist = chip.getkeys()
            Returns all list of all keypaths in the schema.
        """

        if cfg is None:
            cfg = self.cfg

        if len(list(keypath)) > 0:
            keypathstr = ','.join(keypath)
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

        Sets a schema parameter field based on the keypath and value provided
        in the ``*args``. New schema dictionaries are automatically created for
        keypaths that overlap with 'default' dictionaries. The write action
        is ignored if the parameter value is non-empty and the clobber
        option is set to False.

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

        # Verify that all keys are strings
        for key in args[:-1]:
            if not isinstance(key,str):
                self.logger.error(f"Key [{key}] is not a string [{args}]")

        keypathstr = ','.join(args[:-1])
        all_args = list(args)

        # Special case to ensure loglevel is updated ASAP
        if len(args) == 2 and args[0] == 'loglevel' and field == 'value':
            self.logger.setLevel(args[1])

        self.logger.debug(f"Setting [{keypathstr}] to {args[-1]}")
        return self._search(cfg, keypathstr, *all_args, field=field, mode='set', clobber=clobber)

    ###########################################################################
    def add(self, *args, cfg=None, field='value'):
        '''
        Adds item(s) to a schema parameter list.

        Adds item(s) to schema parameter list based on the keypath and value
        provided in the ``*args``. New schema dictionaries are
        automatically created for keypaths that overlap with 'default'
        dictionaries.

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

        # Verify that all keys are strings
        for key in args[:-1]:
            if not isinstance(key,str):
                self.logger.error(f"Key [{key}] is not a string [{args}]")

        keypathstr = ','.join(args[:-1])
        all_args = list(args)

        self.logger.debug(f'Appending value {args[-1]} to [{keypathstr}]')
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

        #set/add leaf cell (all_args=(param,val))
        if (mode in ('set', 'add')) & (len(all_args) == 2):
            # clean error if key not found
            if (not param in cfg) & (not 'default' in cfg):
                self.logger.error(f"Set/Add keypath [{keypath}] does not exist.")
                self.error = 1
            else:
                # making an 'instance' of default if not found
                if (not param in cfg) & ('default' in cfg):
                    cfg[param] = copy.deepcopy(cfg['default'])
                list_type =bool(re.match(r'\[', cfg[param]['type']))
                # copying over defvalue if value doesn't exist
                if 'value' not in cfg[param]:
                    cfg[param]['value'] = copy.deepcopy(cfg[param]['defvalue'])
                # checking for illegal fields
                if not field in cfg[param] and (field != 'value'):
                    self.logger.error(f"Field '{field}' for keypath [{keypath}]' is not a valid field.")
                    self.error = 1
                # check legality of value
                if field == 'value':
                    (type_ok,type_error) = self._typecheck(cfg[param], param, val)
                    if not type_ok:
                        self.logger.error("%s", type_error)
                        self.error = 1
                # converting python True/False to lower case string
                if (field == 'value') and (cfg[param]['type'] == 'bool'):
                    if val == True:
                        val = "true"
                    elif val == False:
                        val = "false"
                # checking if value has been set
                if field not in cfg[param]:
                    selval = cfg[param]['defvalue']
                else:
                    selval = cfg[param]['value']
                # updating values
                if cfg[param]['lock'] == "true":
                    self.logger.debug("Ignoring {mode}{} to [{keypath}]. Lock bit is set.")
                elif (mode == 'set'):
                    if (selval in empty) | clobber:
                        if field in ('copy', 'lock'):
                            # boolean fields
                            if val is True:
                                cfg[param][field] = "true"
                            elif val is False:
                                cfg[param][field] = "false"
                            else:
                                self.logger.error(f'{field} must be set to boolean.')
                                self.error = 1
                        elif field in ('filehash', 'date', 'author', 'signature'):
                            if isinstance(val, list):
                                cfg[param][field] = val
                            else:
                                cfg[param][field] = [val]
                        elif (not list_type) & (val is None):
                            cfg[param][field] = None
                        elif (not list_type) & (not isinstance(val, list)):
                            cfg[param][field] = str(val)
                        elif list_type & (not isinstance(val, list)):
                            cfg[param][field] = [str(val)]
                        elif list_type & isinstance(val, list):
                            if re.search(r'\(', cfg[param]['type']):
                                cfg[param][field] = list(map(str,val))
                            else:
                                cfg[param][field] = val
                        else:
                            self.logger.error(f"Assigning list to scalar for [{keypath}]")
                            self.error = 1
                    else:
                        self.logger.debug(f"Ignoring set() to [{keypath}], value already set. Use clobber=true to override.")
                elif (mode == 'add'):
                    if field in ('filehash', 'date', 'author', 'signature'):
                        cfg[param][field].append(str(val))
                    elif field in ('copy', 'lock'):
                        self.logger.error(f"Illegal use of add() for scalar field {field}.")
                        self.error = 1
                    elif list_type & (not isinstance(val, list)):
                        cfg[param][field].append(str(val))
                    elif list_type & isinstance(val, list):
                        cfg[param][field].extend(val)
                    else:
                        self.logger.error(f"Illegal use of add() for scalar parameter [{keypath}].")
                        self.error = 1
                return cfg[param][field]
        #get leaf cell (all_args=param)
        elif len(all_args) == 1:
            if not param in cfg:
                self.error = 1
                self.logger.error(f"Get keypath [{keypath}] does not exist.")
            elif mode == 'getcfg':
                return cfg[param]
            elif mode == 'getkeys':
                return cfg[param].keys()
            else:
                if not (field in cfg[param]) and (field!='value'):
                    self.error = 1
                    self.logger.error(f"Field '{field}' not found for keypath [{keypath}]")
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
                            elif sctype == '(str,str)':
                                if isinstance(item,tuple):
                                    return_list.append(item)
                                else:
                                    tuplestr = re.sub(r'[\(\)\'\s]','',item)
                                    return_list.append(tuple(tuplestr.split(',')))
                            elif sctype == '(float,float)':
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
            if not param in cfg:
                cfg[param] = copy.deepcopy(cfg['default'])
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
        vars = re.findall(r'\$(\w+)', filename)
        for item in vars:
            varpath = os.getenv(item)
            filename = filename.replace("$"+item, varpath)

        # If we have a path relative to our cwd or an abs path, pass-through here
        if os.path.exists(os.path.abspath(filename)):
            return os.path.abspath(filename)

        # Otherwise, search relative to scpaths
        scpaths = [self.scroot, self.cwd]
        scpaths.extend(self.get('scpath'))
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
            self.error = 1
            self.logger.error(f"File {filename} was not found")

        return result

    ###########################################################################
    def find_files(self, *keypath, cfg=None, missing_ok=False):
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

        copyall = self.get('copyall', cfg=cfg)
        paramtype = self.get(*keypath, field='type', cfg=cfg)

        if 'file' in paramtype:
            copy = self.get(*keypath, field='copy', cfg=cfg)
        else:
            copy = False

        if 'file' not in paramtype and 'dir' not in paramtype:
            self.logger.error('Can only call find_files on file or dir types')
            self.error = 1
            return None

        is_list = bool(re.match(r'\[', paramtype))

        paths = self.get(*keypath, cfg=cfg)
        # Convert to list if we have scalar
        if not is_list:
            paths = [paths]

        result = []

        # Special case where we're looking to find tool outputs: check the
        # output directory and return those files directly
        if len(keypath) == 5 and keypath[0] == 'eda' and keypath[2] == 'output':
            step = keypath[2]
            index = keypath[3]
            outdir = os.path.join(self._getworkdir(step=step, index=index), 'outputs')
            for path in paths:
                abspath = os.path.join(outdir, path)
                if os.path.isfile(abspath):
                    result.append(abspath)
            return result

        for path in paths:
            if (copyall or copy) and ('file' in paramtype):
                name = self._get_imported_filename(path)
                abspath = os.path.join(self._getworkdir(step='import'), 'outputs', name)
                if os.path.isfile(abspath):
                    # if copy is True and file is found in import outputs,
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
    def find_result(self, filetype, step, jobname='job0', index='0'):
        """
        Returns the absolute path of a compilation result.

        Utility function that returns the absolute path to a results
        file based on the provided arguments. The result directory
        structure is:

        <dir>/<design>/<jobname>/<step>/<index>/outputs/<design>.filetype

        Args:
            filetype (str): File extension (.v, .def, etc)
            step (str): Task step name ('syn', 'place', etc)
            jobid (str): Jobid directory name
            index (str): Task index

        Returns:
            Returns absolute path to file.

        Examples:
            >>> manifest_filepath = chip.find_result('.vg', 'syn')
           Returns the absolute path to the manifest.
        """

        workdir = self._getworkdir(jobname, step, index)
        design = self.get('design')
        filename = f"{workdir}/outputs/{design}.{filetype}"

        self.logger.debug("Finding result %s", filename)

        if os.path.isfile(filename):
            return filename
        else:
            self.error = 1
            return None

    ###########################################################################
    def _abspath(self, cfg):
        '''
        Internal function that goes through provided dictionary and resolves all
        relative paths where required.
        '''

        for keypath in self.getkeys(cfg=cfg):
            paramtype = self.get(*keypath, cfg=cfg, field='type')

            #only do something if type is file or dir
            if 'file' in paramtype or 'dir' in paramtype:
                abspaths = self.find_files(*keypath, cfg=cfg, missing_ok=True)
                self.set(*keypath, abspaths, cfg=cfg)

    ###########################################################################
    def _print_csv(self, cfg, file=None):
        allkeys = self.getkeys(cfg=cfg)
        for key in allkeys:
            keypath = f'"{",".join(key)}"'
            value = self.get(*key, cfg=cfg)
            if isinstance(value,list):
                for item in value:
                    print(f"{keypath},{item}", file=file)
            else:
                print(f"{keypath},{value}", file=file)

    ###########################################################################
    def _print_tcl(self, cfg, keys=None, file=None, prefix=""):
        '''
        Prints out schema as TCL dictionary
        '''

        #TODO: simplify, no need for recursion
        if keys is None:
            keys = []
        for k in cfg:
            newkeys = keys.copy()
            newkeys.append(k)
            #detect leaf cell
            if 'defvalue' in cfg[k]:
                if 'value' not in cfg[k]:
                    selval = cfg[k]['defvalue']
                else:
                    selval =  cfg[k]['value']
                if bool(re.match(r'\[', str(cfg[k]['type']))):
                    alist = selval
                else:
                    alist = [selval]
                for i, val in enumerate(alist):
                    #replace $VAR with env(VAR) for tcl
                    m = re.match(r'\$(\w+)(.*)', str(val))
                    if m:
                        alist[i] = ('$env(' +
                                    m.group(1) +
                                    ')' +
                                    m.group(2))

                #create a TCL dict
                keystr = ' '.join(newkeys)
                valstr = ' '.join(map(str, alist)).replace(';', '\\;')
                outlst = [prefix,
                          keystr,
                          '[list ',
                          valstr,
                          ']']
                outstr = ' '.join(outlst)
                outstr = outstr + '\n'
                #print out value
                if file is None:
                    print(outstr)
                else:
                    print(outstr, file=file)
            else:
                self._print_tcl(cfg[k],
                               keys=newkeys,
                               file=file,
                               prefix=prefix)

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

        Examples:
            >>> chip.merge_manifest('my.pkg.json')
           Merges all parameters in my.pk.json into the Chip object

        """

        if job is not None:
            # fill ith default schema before populating
            self.cfghistory[job] = schema_cfg()
            dst = self.cfghistory[job]
        else:
            dst = self.cfg

        for keylist in self.getkeys(cfg=cfg):
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

    def _check_files(self):
        allowed_paths = [os.path.join(self.cwd, self.get('dir'))]
        allowed_paths.extend(os.environ['SC_VALID_PATHS'].split(os.pathsep))

        for keypath in self.getkeys():
            if 'default' in keypath:
                continue

            paramtype = self.get(*keypath, field='type')
            #only do something if type is file or dir
            if 'file' in paramtype or 'dir' in paramtype:

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

        steplist = self.get('steplist')
        if steplist is None:
            steplist = self.list_steps()

        #1. Checking that flowgraph is legal
        if not self.getkeys('flowgraph'):
            self.error = 1
            self.logger.error(f"No flowgraph defined.")
        legal_steps = self.getkeys('flowgraph')

        if 'import' not in legal_steps:
            self.error = 1
            self.logger.error("Flowgraph doesn't contain import step.")

        #2. Check requirements list
        allkeys = self.getkeys()
        for key in allkeys:
            keypath = ",".join(key)
            if 'default' not in key:
                key_empty = self._keypath_empty(key)
                requirement = self.get(*key, field='require')
                if key_empty and (str(requirement) == 'all'):
                    self.error = 1
                    self.logger.error(f"Global requirement missing for [{keypath}].")
                elif key_empty and (str(requirement) == self.get('mode')):
                    self.error = 1
                    self.logger.error(f"Mode requirement missing for [{keypath}].")

        #3. Check per tool parameter requirements (when tool exists)
        for step in steplist:
            for index in self.getkeys('flowgraph', step):
                tool = self.get('flowgraph', step, index, 'tool')
                if tool not in self.builtin:
                    # checking that requirements are set
                    if self.valid('eda', tool, 'require', step, index):
                        all_required = self.get('eda', tool, 'require', step, index)
                        for item in all_required:
                            keypath = item.split(',')
                            if self._keypath_empty(keypath):
                                self.error = 1
                                self.logger.error(f"Value empty for [{keypath}].")
                    if self._keypath_empty(['eda', tool, 'exe']):
                        self.error = 1
                        self.logger.error(f'Executable not specified for tool {tool}')

        if 'SC_VALID_PATHS' in os.environ:
            if not self._check_files():
                self.error = 1

        return self.error

    ###########################################################################
    def read_manifest(self, filename, job=None, update=True, clear=True, clobber=True):
        """
        Reads a manifest from disk and merges it with the current compilation manifest.

        The file format read is determined by the filename suffix. Currently
        json (*.json) and yaml(*.yaml) formats are supported.

        Args:
            filename (filepath): Path to a manifest file to be loaded.
            update (bool): If True, manifest is merged into chip object.
            clear (bool): If True, disables append operations for list type.
            clobber (bool): If True, overwrites existing parameter value.

        Returns:
            A manifest dictionary.

        Examples:
            >>> chip.read_manifest('mychip.json')
            Loads the file mychip.json into the current Chip object.
        """

        abspath = os.path.abspath(filename)
        self.logger.debug('Reading manifest %s', abspath)

        #Read arguments from file based on file type
        with open(abspath, 'r') as f:
            if abspath.endswith('.json'):
                localcfg = json.load(f)
            elif abspath.endswith('.yaml') | abspath.endswith('.yml'):
                localcfg = yaml.load(f, Loader=yaml.SafeLoader)
            else:
                self.error = 1
                self.logger.error('Illegal file format. Only json/yaml supported')
        f.close()

        #Merging arguments with the Chip configuration
        if update:
            self.merge_manifest(localcfg, job=job, clear=clear, clobber=clobber)

        return localcfg

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
        self.logger.info('Writing manifest to %s', filepath)

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

        # TODO: fix
        #remove long help (adds no value)
        #allkeys = self.getkeys(cfg=cfgcopy)
        #for key in allkeys:
        #    self.set(*key, "...", cfg=cfgcopy, field='help')

        # format specific dumping
        with open(filepath, 'w') as f:
            if filepath.endswith('.json'):
                print(json.dumps(cfgcopy, indent=4, sort_keys=True), file=f)
            elif filepath.endswith('.yaml') | filepath.endswith('yml'):
                print(yaml.dump(cfgcopy, Dumper=YamlIndentDumper, default_flow_style=False), file=f)
            elif filepath.endswith('.core'):
                cfgfuse = self._dump_fusesoc(cfgcopy)
                print("CAPI=2:", file=f)
                print(yaml.dump(cfgfuse, Dumper=YamlIndentDumper, default_flow_style=False), file=f)
            elif filepath.endswith('.tcl'):
                print("#############################################", file=f)
                print("#!!!! AUTO-GENERATED FILE. DO NOT EDIT!!!!!!", file=f)
                print("#############################################", file=f)
                self._print_tcl(cfgcopy, prefix="dict set sc_cfg", file=f)
            elif filepath.endswith('.csv'):
                self._print_csv(cfgcopy, file=f)
            else:
                self.logger.error('File format not recognized %s', filepath)
                self.error = 1

    ###########################################################################
    def read_file(self, filename, step='import', index='0'):
        '''
        Read file defined in schema. (WIP)
        '''
        return(0)

    ###########################################################################
    def package(self, filename, prune=True):
        '''
        Create sanitized project package. (WIP)

        The SiliconCompiler project is filtered and exported as a JSON file.
        If the prune option is set to True, then all metrics, records and
        results are pruned from the package file.

        Args:
            filename (filepath): Output filepath
            prune (bool): If True, only essential source parameters are
                 included in the package.

        Examples:
            >>> chip.package('package.json')
            Write project information to 'package.json'
        '''

        return(0)

    ###########################################################################
    def publish(self, filename):
        '''
        Publishes package to registry. (WIP)

        The filename is uploaed to a central package registry based on the
        the user credentials found in ~/.sc/credentials.

        Args:
            filename (filepath): Package filename

        Examples:
            >>> chip.publish('hello.json')
            Publish hello.json to central repository.
        '''

        return(0)


    ###########################################################################
    def _dump_fusesoc(self, cfg):
        '''
        Internal function for dumping core information from chip object.
        '''

        fusesoc = {}

        toplevel = self.get('design', cfg=cfg)

        if self.get('name'):
            name = self.get('name', cfg=cfg)
        else:
            name = toplevel

        version = self.get('projversion', cfg=cfg)

        # Basic information
        fusesoc['name'] = f"{name}:{version}"
        fusesoc['description'] = self.get('description', cfg=cfg)
        fusesoc['filesets'] = {}

        # RTL
        #TODO: place holder fix with pre-processor list
        files = []
        for item in self.get('source', cfg=cfg):
            files.append(item)

        fusesoc['filesets']['rtl'] = {}
        fusesoc['filesets']['rtl']['files'] = files
        fusesoc['filesets']['rtl']['depend'] = {}
        fusesoc['filesets']['rtl']['file_type'] = {}

        # Constraints
        files = []
        for item in self.get('constraint', cfg=cfg):
            files.append(item)

        fusesoc['filesets']['constraints'] = {}
        fusesoc['filesets']['constraints']['files'] = files

        # Default Target
        fusesoc['targets'] = {}
        fusesoc['targets']['default'] = {
            'filesets' : ['rtl', 'constraints', 'tb'],
            'toplevel' : toplevel
        }

        return fusesoc

    ###########################################################################

    def write_flowgraph(self, filename, fillcolor='#ffffff',
                        fontcolor='#000000', fontsize='14',
                        border=True, landscape=False):
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

        Examples:
            >>> chip.write_flowgraph('mydump.png')
            Renders the object flowgraph and writes the result to a png file.
        '''
        filepath = os.path.abspath(filename)
        self.logger.debug('Writing flowgraph to file %s', filepath)
        fileroot, ext = os.path.splitext(filepath)
        fileformat = ext.replace(".", "")

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
        for step in self.getkeys('flowgraph'):
            irange = 0
            for index in self.getkeys('flowgraph', step):
                irange = irange +1
            for i in range(irange):
                index = str(i)
                node = step+index
                # create step node
                tool =  self.get('flowgraph', step, index, 'tool')
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
                for in_step, in_index in self.get('flowgraph', step, index, 'input'):
                    all_inputs.append(in_step + in_index)
                for item in all_inputs:
                    dot.edge(item, node)
        dot.render(filename=fileroot, cleanup=True)

    ########################################################################
    def _collect(self, step, index, active):
        '''
        Collects files found in the configuration dictionary and places
        them in 'dir'. The function only copies in files that have the 'copy'
        field set as true. If 'copyall' is set to true, then all files are
        copied in.

        1. indexing like in run, job1
        2. chdir package
        3. run tool to collect files, pickle file in output/design.v
        4. copy in rest of the files below
        5. record files read in to schema

        Args:
           dir (filepath): Destination directory

        '''

        indir = 'inputs'

        if not os.path.exists(indir):
            os.makedirs(indir)

        self.logger.info('Collecting input sources')

        #copy all parameter take from self dictionary
        copyall = self.get('copyall')
        for key in self.getkeys():
            if 'file' in self.get(*key,field='type'):
                copy = self.get(*key, field='copy')
                value = self.get(*key)
                if copyall or copy:
                    for item in value:
                        filename = self._get_imported_filename(item)
                        filepath = self._find_sc_file(item)
                        if filepath:
                            self.logger.info(f"Copying {filepath} to '{indir}' directory")
                            shutil.copy(filepath, os.path.join(indir, filename))
                        else:
                            self._haltstep(step,index,active)

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

        jobname = self.get('jobname')
        design = self.get('design')
        buildpath = self.get('dir')

        if step:
            steplist = [step]
        elif self.get('arg', 'step'):
            steplist = [self.get('arg', 'step')]
        elif self.get('steplist'):
            steplist = self.get('steplist')
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
                    indexlist = self.getkeys('flowgraph', step)
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
            self.logger.error(f"Illegal attempt to hash non-file parameter [{keypathstr}].")
            self.error = 1
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
                    self.error = 1
                    self.logger.info(f"Internal hashing error, file not found")
            # compare previous hash to new hash
            oldhash = self.get(*keypath,field='filehash')
            for i,item in enumerate(oldhash):
                if item != hashlist[i]:
                    self.logger.error(f"Hash mismatch for [{keypath}]")
                    self.error = 1
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
        if not steplist:
            steplist = self.list_steps()

        #only report tool based steps functions
        for step in steplist:
            if self.get('flowgraph',step,'0','tool') in self.builtin:
                index = steplist.index(step)
                del steplist[index]

        # job directory
        jobdir = self._getworkdir()

        # Custom reporting modes
        paramlist = []
        for item in self.getkeys('param'):
            paramlist.append(item+"="+self.get('param',item))

        if paramlist:
            paramstr = ', '.join(paramlist)
        else:
            paramstr = "None"

        info_list = ["SUMMARY:\n",
                     "design : " + self.get('design'),
                     "params : " + paramstr,
                     "jobdir : "+ jobdir,
                     ]

        if self.get('mode') == 'asic':
            info_list.extend(["foundry : " + self.get('pdk', 'foundry'),
                              "process : " + self.get('pdk', 'process'),
                              "targetlibs : "+" ".join(self.get('asic', 'targetlib'))])
        elif self.get('mode') == 'fpga':
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
                indices_to_show[step] = self.getkeys('flowgraph', step)
            else:
                # Default for last step in list (could be tool or function)
                indices_to_show[step] = ['0']

                # Find winning index
                for index in self.getkeys('flowgraph', step):
                    stepindex = step + index
                    for i in  self.getkeys('flowstatus'):
                        for j in  self.getkeys('flowstatus',i):
                            for in_step, in_index in self.get('flowstatus',i,j,'select'):
                                if (in_step + in_index) == stepindex:
                                    indices_to_show[step] = index

        # header for data frame
        for step in steplist:
            for index in indices_to_show[step]:
                header.append(f'{step}{index}'.center(colwidth))

        # figure out which metrics have non-zero weights
        metric_list = []
        for step in steplist:
            for metric in self.getkeys('metric','default','default'):
                if metric in self.getkeys('flowgraph', step, '0', 'weight'):
                    if self.get('flowgraph', step, '0', 'weight', metric) is not None:
                        if metric not in metric_list:
                            metric_list.append(metric)

        # print out all metrics
        metrics = []
        for metric in metric_list:
            metrics.append(" " + metric)
            row = []
            for step in steplist:
                for index in indices_to_show[step]:
                    value = None
                    if 'real' in self.getkeys('metric', step, index, metric):
                        value = self.get('metric', step, index, metric, 'real')

                    if value is None:
                        value = 'ERR'
                    else:
                        value = str(value)

                    row.append(" " + value.center(colwidth))
            data.append(row)

        pandas.set_option('display.max_rows', 500)
        pandas.set_option('display.max_columns', 500)
        pandas.set_option('display.width', 100)
        df = pandas.DataFrame(data, metrics, header)
        print(df.to_string())
        print("-"*135)

    ###########################################################################
    def list_steps(self):
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

        cfg = self.cfg

        #Get length of paths from step to root
        depth = {}
        for step in self.getkeys('flowgraph', cfg=cfg):
            depth[step] = 0
            for path in self._allpaths(cfg, step, str(0)):
                if len(list(path)) > depth[step]:
                    depth[step] = len(path)

        #Sort steps based on path lenghts
        sorted_dict = dict(sorted(depth.items(), key=lambda depth: depth[1]))
        return list(sorted_dict.keys())


    ###########################################################################
    def _allpaths(self, cfg, step, index, path=None, allpaths=None):

        if path is None:
            path = []
            allpaths = []

        inputs = self.get('flowgraph', step, index, 'input', cfg=cfg)

        if not self.get('flowgraph', step, index, 'input', cfg=cfg):
            allpaths.append(path)
        else:
            for in_step, in_index in inputs:
                newpath = path.copy()
                newpath.append(in_step + in_index)
                return self._allpaths(cfg, in_step, in_index, path=newpath, allpaths=allpaths)

        return list(allpaths)

    ###########################################################################
    def clock(self, *, name, pin, period, jitter=0):
        """
        Clock configuration helper function.

        A utility function for setting all parameters associated with a
        single clock definition in the schema.

        The method modifies the following schema parameters:

        ['clock', name, 'pin']
        ['clock', name, 'period']
        ['clock', name, 'jitter']

        Args:
            name (str): Clock reference name.
            pin (str): Full hiearchical path to clk pin.
            period (float): Clock period specified in ns.
            jitter (float): Clock jitter specified in ns.

        Examples:
            >>> chip.clock(name='clk', pin='clk, period=1.0)
           Create a clock namedd 'clk' with a 1.0ns period.
        """

        self.set('clock', name, 'pin', pin)
        self.set('clock', name, 'period', period)
        self.set('clock', name, 'jitter', jitter)

    ###########################################################################
    def node(self, step, tool, index=0):
        '''
        Creates a flowgraph node.

        Creates a flowgraph node by binding a tool to a task. A task is defined
        as the combination of a step and index. A tool can be an external
        exeuctable or one of the built in functions in the SiliconCompiler
        framework). Built in functions include: minimum, maximum, join, mux,
        verify.

        The method modifies the following schema parameters:

        ['flowgraph', step, index, 'tool', tool]
        ['flowgraph', step, index, 'weight', metric]

        Args:
            step (str): Task step name
            tool (str): Tool (or builtin function) to associate with task.
            index (int): Task index

        Examples:
            >>> chip.node('place', 'openroad', index=0)
            Creates a task with step='place' and index=0 and binds it to the 'openroad' tool.
        '''

        # bind tool to node
        self.set('flowgraph', step, str(index), 'tool', tool)
        # set default weights
        for metric in self.getkeys('metric', 'default', 'default'):
            self.set('flowgraph', step, str(index), 'weight', metric, 0)

    ###########################################################################
    def edge(self, tail, head, tail_index=0, head_index=0):
        '''
        Creates a directed edge from a tail node to a head node.

        Connects the output of a tail node with the input of a head node by
        setting the 'input' field of the head node in the schema flowgraph.

        The method modifies the following parameters:

        ['flowgraph', head, str(head_index), 'input']

        Args:
            tail (str): Name of tail node
            head (str): Name of head node
            tail_index (int): Index of tail node to connect
            head_index (int): Index of head node to connect

        Examples:
            >>> chip.edge('place', 'cts')
            Creates a directed edge from place to cts.
        '''

        self.add('flowgraph', head, str(head_index), 'input', (tail, str(tail_index)))

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

        steplist = list(steps)

        # Keeping track of the steps/indexes that have goals met
        failed = {}
        for step, index in steplist:
            if step not in failed:
                failed[step] = {}
            failed[step][index] = False

            if self.get('flowstatus', step, index, 'error'):
                failed[step][index] = True
            else:
                for metric in self.getkeys('metric', step, index):
                    if 'goal' in self.getkeys('metric', step, index, metric):
                        goal = self.get('metric', step, index, metric, 'goal')
                        real = self.get('metric', step, index, metric, 'real')
                        if abs(real) > goal:
                            self.logger.warning(f"Step {step}{index} failed "
                                f"because it didn't meet goals for '{metric}' "
                                "metric.")
                            failed[step][index] = True

        # Calculate max/min values for each metric
        max_val = {}
        min_val = {}
        for metric in self.getkeys('flowgraph', step, '0', 'weight'):
            max_val[metric] = 0
            min_val[metric] = float("inf")
            for step, index in steplist:
                if not failed[step][index]:
                    real = self.get('metric', step, index, metric, 'real')
                    max_val[metric] = max(max_val[metric], real)
                    min_val[metric] = min(min_val[metric], real)

        # Select the minimum index
        best_score = float('inf') if op == 'minimum' else float('-inf')
        winner = None
        for step, index in steplist:
            if failed[step][index]:
                continue

            score = 0.0
            for metric in self.getkeys('flowgraph', step, index, 'weight'):
                weight = self.get('flowgraph', step, index, 'weight', metric)
                if not weight:
                    # skip if weight is 0 or None
                    continue

                real = self.get('metric', step, index, metric, 'real')

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
    def _runtask_safe(self, step, index, active, error):
        try:
            self._init_logger(step, index)
        except:
            traceback.print_exc()
            print(f"Uncaught exception while initializing logger for step {step}")
            self.error = 1
            self._haltstep(step, index, active, log=False)

        try:
            self._runtask(step, index, active, error)
        except SystemExit:
            # calling sys.exit() in _haltstep triggers a "SystemExit"
            # exception, but we can ignore these -- if we call sys.exit(), we've
            # already handled the error.
            pass
        except:
            traceback.print_exc()
            self.logger.error(f"Uncaught exception while running step {step}.")
            self.error = 1
            self._haltstep(step, index, active)

    ###########################################################################
    def _runtask(self, step, index, active, error):
        '''
        Private per step run method called by run().
        The method takes in a step string and index string to indicated what
        to run. Execution state coordinated through the active/error
        multiprocessing Manager dicts.

        Execution flow:
        T1. Wait in loop until all previous steps/indexes have completed
        T2. Defer job to compute node if using job scheduler
        T3. Start task timer
        T4. Set up working directory + chdir
        T5. Merge manifests from all input dependancies
        T6. Write manifest to input directory for convenience
        T7. Resetting all metrics to 0 (consider removing)
        T8. Select inputs
        T9. Copy data from previous step outputs into inputs
        T10. Copy reference script directory
        T11. Check manifest
        T12. Run pre_process() function
        T13. Set license file
        T14. Check EXE version
        T15. Save manifest as TCL/YAML
        T16. Run EXE
        T17. Run post_process()
        T18. Hash all task files
        T19. Make a task record
        T20. Measure run time
        T21. Save manifest to disk
        T22. chdir
        T23. clear error/active bits and return control to run()

        Note that since _runtask occurs in its own process with a separate
        address space, any changes made to the `self` object will not
        be reflected in the parent. We rely on reading/writing the chip manifest
        to the filesystem to communicate updates between processes.
        '''

        ##################
        # Shared parameters (long function!)
        design = self.get('design')
        tool = self.get('flowgraph', step, index, 'tool')

        ##################
        # 1. Wait loop
        self.logger.info('Waiting for inputs...')
        while True:
            # Checking that there are no pending jobs
            pending = 0
            for in_step, in_index in self.get('flowgraph', step, index, 'input'):
                pending = pending + active[in_step + in_index]
            # beak out of loop when no all inputs are done
            if not pending:
                break
            # Short sleep
            time.sleep(0.1)

        ##################
        # 2. Defer job to compute node
        # If the job is configured to run on a cluster, collect the schema
        # and send it to a compute node for deferred execution.
        # (Run the initial 'import' stage[s] locally)
        if self.get('jobscheduler') and \
           self.get('flowgraph', step, index, 'input'):
            # Note: The _deferstep method blocks until the compute node
            # finishes processing this step, and it sets the active/error bits.
            _deferstep(self, step, index, active, error)
            return

        ##################
        # 3. Start Task Timer
        self.logger.debug(f"Starting process")
        start = time.time()

        ##################
        # 4. Directory setup

        # support for sharing data across jobs
        job = self.get('jobname')
        if job in self.getkeys('jobinput'):
            if step in self.getkeys('jobinput',job):
                if index in self.getkeys('jobinput',job,step):
                    job = self.get('jobinput', job, step, index)

        workdir = self._getworkdir(step=step,index=index)
        cwd = os.getcwd()
        if os.path.isdir(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir, exist_ok=True)

        os.chdir(workdir)
        os.makedirs('outputs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        ##################
        # 5. Merge manifests from all input dependancies

        all_inputs = []
        if not self.get('remote'):
            for in_step, in_index in self.get('flowgraph', step, index, 'input'):
                index_error = error[in_step + in_index]
                self.set('flowstatus', in_step, in_index, 'error', index_error)
                if not index_error:
                    cfgfile = f"../../../{job}/{in_step}/{in_index}/outputs/{design}.pkg.json"
                    self.read_manifest(cfgfile, clobber=False)

        ##################
        # 6. Write configuration prior to step running into inputs

        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)
        os.makedirs('inputs', exist_ok=True)
        #self.write_manifest(f'inputs/{design}.pkg.json')

        ##################
        # 7. Resetting metrics to zero
        # TODO: There should be no need for this, but need to fix
        # without it we need to be more careful with flows to make sure
        # things like the builtin functions don't look at None values
        for metric in self.getkeys('metric', 'default', 'default'):
            self.set('metric', step, index, metric, 'real', 0)

        ##################
        # 8. Select inputs

        args = self.get('flowgraph', step, index, 'args')
        inputs = self.get('flowgraph', step, index, 'input')

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
                    self._haltstep(step, index, active)
        else:
            sel_inputs = self.get('flowgraph', step, index, 'input')

        if sel_inputs == None:
            self.logger.error(f'No inputs selected after running {tool}')
            self._haltstep(step, index, active)

        self.set('flowstatus', step, index, 'select', sel_inputs)

        ##################
        # 9. Copy outputs from previous steps

        if step == 'import':
            self._collect(step, index, active)

        if not self.get('flowgraph', step, index,'input'):
            all_inputs = []
        elif not self.get('flowstatus', step, index, 'select'):
            all_inputs = self.get('flowgraph', step, index,'input')
        else:
            all_inputs = self.get('flowstatus', step, index, 'select')
        for in_step, in_index in all_inputs:
            if self.get('flowstatus', in_step, in_index, 'error') == 1:
                self.logger.error(f'Halting step due to previous error in {in_step}{in_index}')
                self._haltstep(step, index, active)

            # Skip copying pkg.json files here, since we write the current chip
            # configuration into inputs/{design}.pkg.json earlier in _runstep.
            utils.copytree(f"../../../{job}/{in_step}/{in_index}/outputs", 'inputs/', dirs_exist_ok=True,
                ignore=[f'{design}.pkg.json'], link=True)

        ##################
        # 10. Copy Reference Scripts
        if tool not in self.builtin:
            if self.get('eda', tool, 'copy'):
                refdir = self.find_files('eda', tool, 'refdir', step, index)
                utils.copytree(refdir, ".", dirs_exist_ok=True)

        ##################
        # 11. Check that all requirements met
        if self.check_manifest():
            self.logger.error(f"Fatal error in check()! See previous errors.")
            self._haltstep(step, index, active)


        ##################
        # 12. Run preprocess step for tool
        self.set('arg', 'step', step, clobber=True)
        self.set('arg', 'index', index, clobber=True)

        if tool not in self.builtin:
            func = self.find_function(tool, "tool", "pre_process")
            if func:
                func(self)
                if self.error:
                    self.logger.error(f"Pre-processing failed for '{tool}'")
                    self._haltstep(step, index, active)

        ##################
        # 13. Set license variable

        for item in self.getkeys('eda', tool, 'licenseserver'):
            license_file = self.get('eda', tool, 'licenseserver', item)
            if license_file:
                os.environ[item] = license_file

        ##################
        # 14. Check exe version

        vercheck = self.get('vercheck')
        veropt = self.get('eda', tool, 'vswitch')
        exe = self.get('eda', tool, 'exe')
        version = None
        if vercheck and (veropt is not None) and (exe is not None):
            fullexe = self._resolve_env_vars(exe)
            cmdlist = [fullexe] + veropt.split()
            self.logger.info("Checking version of tool '%s'", tool)
            proc = subprocess.run(cmdlist, stdout=PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            parse_version = self.find_function(tool, 'tool', 'parse_version')
            if parse_version is None:
                self.logger.error(f'{tool} does not implement parse_version.')
                self._haltstep(step, index, active)

            version = parse_version(proc.stdout)
            allowed_versions = self.get('eda', tool, 'version')
            if allowed_versions and version not in allowed_versions:
                allowedstr = ', '.join(allowed_versions)
                self.logger.error(f"Version check failed for {tool}. Check installation.")
                self.logger.error(f"Found version {version}, expected one of [{allowedstr}].")
                self._haltstep(step, index, active)


        ##################
        # 15. Interface with tools (Don't move this!)
        suffix = self.get('eda', tool, 'format')
        if suffix:
            self.write_manifest(f"sc_manifest.{suffix}", abspath=True)

        ##################
        # 16. Run executable (or copy inputs to outputs for builtin functions)

        if tool in self.builtin:
            utils.copytree(f"inputs", 'outputs', dirs_exist_ok=True, link=True)
        else:
            cmdlist = self._makecmd(tool, step, index)
            cmdstr = ' '.join(cmdlist)
            self.logger.info("Running in %s", workdir)
            self.logger.info('%s', cmdstr)
            timeout = self.get('flowgraph', step, index, 'timeout')
            logfile = step + '.log'
            with open(logfile, 'w') as log_writer, open(logfile, 'r') as log_reader:
                # Use separate reader/writer file objects as hack to display
                # live output in non-blocking way, so we can monitor the
                # timeout. Based on https://stackoverflow.com/a/18422264.
                quiet = self.get('quiet') and (step not in self.get('bkpt'))
                cmd_start_time = time.time()
                proc = subprocess.Popen(cmdlist,
                                        stdout=log_writer,
                                        stderr=subprocess.STDOUT)
                while proc.poll() is None:
                    # Loop until process terminates
                    if not quiet:
                        sys.stdout.write(log_reader.read())
                    if timeout is not None and time.time() - cmd_start_time > timeout:
                        self.logger.error(f'Step timed out after {timeout} seconds')
                        proc.terminate()
                        self._haltstep(step, index, active)
                    time.sleep(0.1)

                # Read the remaining
                if not quiet:
                    sys.stdout.write(log_reader.read())

            if proc.returncode != 0:
                self.logger.warning('Command failed. See log file %s', os.path.abspath(logfile))
                if not self.get('eda', tool, 'continue'):
                    self._haltstep(step, index, active)

        ##################
        # 17. Post process (could fail)
        post_error = 0
        if tool not in self.builtin:
            func = self.find_function(tool, "tool", "post_process")
            if func:
                post_error = func(self)
                if post_error:
                    self.logger.error('Post-processing check failed')
                    self._haltstep(step, index, active)

        ##################
        # 18. Hash files
        if self.get('hash') and (tool not in self.builtin):
            # hash all outputs
            self.hash_files('eda', tool, 'output', step, index)
            # hash all requirements
            if self.valid('eda', tool, 'require', step, index, quiet=True):
                for item in self.get('eda', tool, 'require', step, index):
                    args = item.split(',')
                    if 'file' in self.get(*args, field='type'):
                        self.hash_files(*args)

        ##################
        # 19. Make a record if tracking is enabled
        if self.get('track'):
            self._make_record(job, step, index, version)

        ##################
        # 20. Capture total runtime

        end = time.time()
        elapsed_time = round((end - start),2)
        self.set('metric',step, index, 'runtime', 'real', elapsed_time)

        ##################
        # 21. Save a successful manifest

        self.set('flowstatus', step, str(index), 'error', 0)
        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)

        self.write_manifest("outputs/" + self.get('design') +'.pkg.json')

        ##################
        # 22. Clean up non-essential files
        if self.get('clean'):
            self.logger.error('Self clean not implemented')

        ##################
        # 22. return fo original directory
        os.chdir(cwd)

        ##################
        # 23. clearing active and error bits
        # !!Do not move this code!!
        error[step + str(index)] = 0
        active[step + str(index)] = 0

    ###########################################################################
    def _haltstep(self, step, index, active, log=True):
        if log:
            self.logger.error(f"Halting step '{step}' index '{index}' due to errors.")
        active[step + str(index)] = 0
        sys.exit(1)

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

        # We package SC wheels with a precompiled copy of Surelog installed to
        # tools/surelog/bin. Add this path to the system path before attempting to
        # execute Surelog so the system checks here.
        surelog_path = f'{os.path.dirname(__file__)}/tools/surelog/bin'
        try:
            ospath = os.environ['PATH'] + os.pathsep
        except KeyError:
            ospath = ''
        ospath += f'{surelog_path}'
        os.environ['PATH'] = ospath

        # Run steps if set, otherwise run whole graph
        if self.get('arg', 'step'):
            steplist = [self.get('arg', 'step')]
        elif self.get('steplist'):
            steplist = self.get('steplist')
        else:
            steplist = self.list_steps()

            # If no step(list) was specified, the whole flow is being run
            # start-to-finish. Delete the build dir to clear stale results.
            cur_job_dir = f'{self.get("dir")}/{self.get("design")}/'\
                          f'{self.get("jobname")}'
            if os.path.isdir(cur_job_dir):
                shutil.rmtree(cur_job_dir)

        # Remote workflow: Dispatch the Chip to a remote server for processing.
        if self.get('remote'):
            # Load the remote storage config into the status dictionary.
            if self.get('credentials'):
                # Use the provided remote credentials file.
                cfg_file = self.get('credentials')[-1]
                cfg_dir = os.path.dirname(cfg_file)
            else:
                # Use the default config file path.
                cfg_dir = os.path.join(Path.home(), '.sc')
                cfg_file = os.path.join(cfg_dir, 'credentials')
            if (not os.path.isdir(cfg_dir)) or (not os.path.isfile(cfg_file)):
                self.logger.error('Could not find remote server configuration - please run "sc-configure" and enter your server address and credentials.')
                sys.exit(1)
            with open(cfg_file, 'r') as cfgf:
                self.status['remote_cfg'] = json.loads(cfgf.read())
            if (not 'address' in self.status['remote_cfg']):
                self.logger.error('Improperly formatted remote server configuration - please run "sc-configure" and enter your server address and credentials.')
                sys.exit(1)

            # Pre-process: Run an 'import' stage locally, and upload the
            # in-progress build directory to the remote server.
            # Data is encrypted if user / key were specified.
            # run remote process
            remote_preprocess(self)

            # Run the job on the remote server, and wait for it to finish.
            remote_run(self)

            # Fetch results (and delete the job's data from the server).
            fetch_results(self)
        else:
            manager = multiprocessing.Manager()
            error = manager.dict()
            active = manager.dict()

            # Launch a thread for eact step in flowgraph
            # Use a shared even for errors
            # Use a manager.dict for keeping track of active processes
            # (one unqiue dict entry per process),
            # Set up tools and processes
            for step in self.getkeys('flowgraph'):
                for index in self.getkeys('flowgraph', step):
                    stepstr = step + index
                    if self.get('arg', 'index'):
                        indexlist = [self.get('arg', 'index')]
                    elif self.get('indexlist'):
                        indexlist = self.get('indexlist')
                    else:
                        indexlist = self.getkeys('flowgraph', step)
                    if (step in steplist) & (index in indexlist):
                        self.set('flowstatus', step, str(index), 'error', 1)
                        error[stepstr] = self.get('flowstatus', step, str(index), 'error')
                        active[stepstr] = 1
                        # Setting up tool is optional
                        tool = self.get('flowgraph', step, index, 'tool')
                        if tool not in self.builtin:
                            self.set('arg','step', step)
                            self.set('arg','index', index)
                            func = self.find_function(tool, 'tool', 'setup_tool')
                            if func is None:
                                self.logger.error(f'setup_tool() not found for tool {tool}')
                                sys.exit(1)
                            func(self)
                            # Need to clear index, otherwise we will skip
                            # setting up other indices. Clear step for good
                            # measure.
                            self.set('arg','step', None)
                            self.set('arg','index', None)
                    else:
                        self.set('flowstatus', step, str(index), 'error', 0)
                        error[stepstr] = self.get('flowstatus', step, str(index), 'error')
                        active[stepstr] = 0

            # Implement auto-update of jobincrement
            try:
                alljobs = os.listdir(self.get('dir') + "/" + self.get('design'))
                if self.get('jobincr'):
                    jobid = 0
                    for item in alljobs:
                        m = re.match(self.get('jobname')+r'(\d+)', item)
                        if m:
                            jobid = max(jobid, int(m.group(1)))
                    self.set('jobid', str(jobid + 1))
            except:
                pass

            # Check validity of setup
            self.check_manifest()

            # Check if there were errors before proceeding with run
            if self.error:
                self.logger.error(f"Check failed. See previous errors.")
                sys.exit()

            # Enable checkonly mode
            if self.get('checkonly'):
                self.logger.info("Exiting after static check(), checkonly=True")
                sys.exit()

            # Create all processes
            processes = []
            for step in steplist:
                if self.get('arg', 'index'):
                    indexlist = [self.get('arg', 'index')]
                else:
                    indexlist = self.getkeys('flowgraph', step)
                for index in indexlist:
                    processes.append(multiprocessing.Process(target=self._runtask_safe,
                                                             args=(step, index, active, error,)))


            # We have to deinit the chip's logger before spawning the processes
            # since the logger object is not serializable. _runtask_safe will
            # reinitialize the logger in each new process, and we reinitialize
            # the primary chip's logger after the processes complete.
            self._deinit_logger()

            # Start all processes
            for p in processes:
                p.start()
            # Mandatory process cleanup
            for p in processes:
                p.join()

            self._init_logger()

            # Make a clean exit if one of the steps failed
            halt = 0
            for step in steplist:
                index_error = 1
                if self.get('arg', 'index'):
                    indexlist = [self.get('arg', 'index')]
                else:
                    indexlist = self.getkeys('flowgraph', step)
                for index in indexlist:
                    stepstr = step + index
                    index_error = index_error & error[stepstr]
                halt = halt + index_error
            if halt:
                self.logger.error('Run() failed, exiting! See previous errors.')
                sys.exit(1)

        # Clear scratchpad args since these are checked on run() entry
        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)

        # Merge cfg back from last executed runstep.
        # (Only if the index-0 run's results exist.)
        laststep = steplist[-1]
        lastindex = '0'
        lastdir = self._getworkdir(step=laststep, index=lastindex)
        lastcfg = f"{lastdir}/outputs/{self.get('design')}.pkg.json"
        if os.path.isfile(lastcfg):
            local_dir = self.get('dir')
            self.read_manifest(lastcfg, clobber=True, clear=True)
            self.set('dir', local_dir)
        else:
            # Hack to find first failed step by checking for presence of output
            # manifests.
            failed_step = laststep
            for step in steplist[:-1]:
                step_has_cfg = False
                for index in self.getkeys('flowgraph', step):
                    stepdir = self._getworkdir(step=step, index=lastindex)
                    cfg = f"{stepdir}/outputs/{self.get('design')}.pkg.json"
                    if os.path.isfile(cfg):
                        step_has_cfg = True
                        break

                if not step_has_cfg:
                    failed_step = step
                    break

            stepdir = self._getworkdir(step=failed_step)[:-1]
            self.logger.error(f'Run() failed on step {failed_step}, exiting! '
                f'See logs in {stepdir} for error details.')
            sys.exit(1)

        # Store run in history
        self.cfghistory[self.get('jobname')] = copy.deepcopy(self.cfg)

    ###########################################################################
    def show(self, filename=None):
        '''
        Opens a graphical viewer for the filename provided.

        The show function opens the filename specified using a viewer tool
        selected based on the file suffix and the 'showtool' schema setup.
        The 'showtool' parameter binds tools with file suffixes, enabling the
        automated dynamic loading of tool setup functions from
        siliconcompiler.tools.<tool>/<tool>.py. Display settings and
        technology settings for viewing the file are read from the
        in-memory chip object schema settings. All temporary render and
        display files are saved in the <build_dir>/_show directory.

        The show() command can also be used to display content from an SC
        schema .json filename provided. In this case, the SC schema is
        converted to html and displayed as a 'dashboard' in the browser.

        Filenames with .gz and .zip extensions are automatically unpacked
        before being displayed.

        Args:
            filename: Name of file to display

        Examples:
            >>> show('build/oh_add/job0/export/0/outputs/oh_add.gds')
            Displays gds file with a viewer assigned by 'showtool'
            >>> show('build/oh_add/job0/export/0/outputs/oh_add.pkg.json')
            Displays manifest in the browser
        '''

        self.logger.info("Showing file %s", filename)

        # Finding lasts layout if no argument specified
        if filename is None:
            design = self.get('design')
            laststep = self.list_steps()[-1]
            lastindex = '0'
            lastdir = self._getworkdir(step=laststep, index=lastindex)
            gds_file= f"{lastdir}/outputs/{design}.gds"
            def_file = f"{lastdir}/outputs/{design}.def"
            if os.path.isfile(gds_file):
                filename = gds_file
            elif os.path.isfile(def_file):
                filename = def_file

        # Parsing filepath
        filepath = os.path.abspath(filename)
        basename = os.path.basename(filepath)
        localfile = basename.replace(".gz","")
        filetype = os.path.splitext(localfile)[1].lower().replace(".","")

        #Check that file exists
        if not os.path.isfile(filepath):
            self.logger.error(f"Invalid filepath {filepath}.")
            return 1

        # Opening file from temp directory
        cwd = os.getcwd()
        showdir = self.get('dir') + "/_show"
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
        if filetype in self.getkeys('showtool'):
            # Using env variable and manifest to pass arguments
            os.environ['SC_FILENAME'] = localfile
            self.write_manifest("sc_manifest.tcl", abspath=True)
            self.write_manifest("sc_manifest.json", abspath=True)
            # Setting up tool
            tool = self.get('showtool', filetype)
            step = 'show'+filetype
            index = "0"
            self.set('arg', 'step', step)
            self.set('arg', 'index', index)
            setup_tool = self.find_function(tool, 'tool', 'setup_tool')
            setup_tool(self, mode='show')

            exe = self.get('eda', tool, 'exe')
            if shutil.which(exe) is None:
                self.logger.error(f'Executable {exe} not found.')
                success = False
            else:
                # Running command
                cmdlist = self._makecmd(tool, step, index)
                proc = subprocess.run(cmdlist)
                success = proc.returncode == 0
        else:
            self.logger.error(f"Filetype '{filetype}' not set up in 'showtool' parameter.")
            success = False

        # Returning to original directory
        os.chdir(cwd)
        return success

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
                if (cfgtype != valuetype.__name__):
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
    def _makecmd(self, tool, step, index):
        '''
        Constructs a subprocess run command based on eda tool setup.
        Creates a replay.sh command in current directory.
        '''

        exe = self.get('eda', tool, 'exe')
        fullexe = self._resolve_env_vars(exe)

        options = []
        is_posix = ('win' not in sys.platform)

        for option in self.get('eda', tool, 'option', step, index):
            options.extend(shlex.split(option, posix=is_posix))

        # Add scripts files
        if self.valid('eda', tool, 'script', step, index):
            scripts = self.find_files('eda', tool, 'script', step, index)
        else:
            scripts = []

        cmdlist = [fullexe]
        logfile = step + ".log"
        cmdlist.extend(options)
        cmdlist.extend(scripts)
        runtime_options = self.find_function(tool, 'tool', 'runtime_options')
        if runtime_options:
            #print(runtime_options(self))
            for option in runtime_options(self):
                cmdlist.extend(shlex.split(option, posix=is_posix))

        #create replay file
        with open('replay.sh', 'w') as f:
            print('#!/bin/bash\n', ' '.join(cmdlist), file=f)
        os.chmod("replay.sh", 0o755)

        return cmdlist

    #######################################
    def _make_record(self, job, step, index, toolversion):
        '''
        Records provenance details for a runstep.
        '''

        #start_date = datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S')

        for key in self.getkeys('record', 'default', 'default'):
            if key == 'starttime':
                self.set('record', step, index,'starttime', start)
            elif key == 'endtime':
                self.set('record', step, index, 'endtime', end)
            elif key == 'input':
                #TODO
                pass
            elif key == 'hash':
                #TODO
                pass
            elif key == 'version':
                #TODO
                pass
            elif self.get(key):
                self.set('record', step, index, key, self.get(key))
            else:
                self.logger.debug(f"Record ignored for {key}, parameter not set up")


    #######################################
    def _getworkdir(self, jobname=None, step=None, index='0'):
        '''Create a step directory with absolute path
        '''

        if jobname is None:
            jobname = self.get('jobname')

        dirlist =[self.cwd,
                  self.get('dir'),
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
        vars = re.findall(r'\$(\w+)', filepath)
        for item in vars:
            varpath = os.getenv(item)
            filepath = filepath.replace("$"+item, varpath)

        return filepath

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

        pathhash = hashlib.md5(pathstr.encode('utf-8')).hexdigest()

        return f'{filename}_{pathhash}{ext}'

###############################################################################
# Package Customization classes
###############################################################################

class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)
