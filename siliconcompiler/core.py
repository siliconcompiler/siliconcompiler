# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
import base64
import time
import datetime
import multiprocessing
import traceback
import asyncio
from subprocess import run, PIPE
import os
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
import uuid
import math
import pandas
import yaml
import graphviz
import pyfiglet
import time
from timeit import default_timer as timer
from siliconcompiler.client import *
from siliconcompiler.schema import *

# Fix for multprocessing bug on MacOS
# Source: https://github.com/Koed00/django-q/issues/389#issuecomment-699481976
from multiprocessing import set_start_method
set_start_method("fork")

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
    def __init__(self, design="root", loglevel="INFO"):

        # Local variables
        self.scroot = os.path.dirname(os.path.abspath(__file__))
        self.cwd = os.getcwd()
        self.version = "0.0.1"
        self.design = design
        self.status = {}
        self.error = 0
        self.cfg = schema_cfg()

        # Setting design variable
        self.cfg['design']['value'] = self.design
        self.cfg['scversion']['value'] = self.version
        logname = self.design.center(12)

        # Initialize logger
        self.logger = logging.getLogger(uuid.uuid4().hex)
        self.handler = logging.StreamHandler()
        self.formatter = logging.Formatter('| %(levelname)-7s | %(asctime)s | ' + logname +  ' | %(message)s', datefmt='%Y-%m-%d %H:%M:%S',)
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(str(loglevel))

    ###########################################################################
    def cmdline(self, progname, description=None, switchlist=[]):
        """Creates an SC command line interface.

        The method exposes parameters in the SC schema as command line
        switches. Custom command line apps can be created by restricting
        the schema parameters exposed at the command line. The priority of
        command line switch settings is as follows:

         1. design
         2. loglevel
         3. mode (asic/fpga)
         4. target
         5. cfg
         6. all other switches

        The cmdline interface is implemented using the Python
        argparse package and the following use restrictions apply.

        * Help is accessed with the '-h' switch
        * Arguments that include spaces must be enclosed with double quotes.
        * List parameters are entered indidually (ie. -y libdir1 -y libdir2)
        * For parameters with boolean types, the switch implies "true".
        * Special characters (such as '-') must be enclosed in double quotes.
        * Compiler comptaible switces include: -D, -I, -O{0,1,2,3}
        * Some Verilog legacy switches are supported: +libext+, +incdir+

        Args:
            progname (string): Name of program to be exeucted at the command
                 line.
            description (string): Header help function to be displayed
                 by the command line program.
            switchlist (list): List of SC parameter switches to expose
                 at the command line. By default all SC scema switches
                 are available. The switchlist entries should ommit
                 the '-'. To include a non-switch source file,
                 use 'source' as the switch.

        Examples:
            >>> chip.cmdline(prog='sc-show', paramlist=['source', 'cfg'])
            Creates a command line interface called sc-show that takes
            in a source file to display based on the cfg file provided.

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
            print(self.version)
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
        ascii_banner = pyfiglet.figlet_format("Silicon Compiler")
        print(ascii_banner)

        # Print out SC project authors
        authors = []
        authorfile = self.find("AUTHORS")
        f = open(authorfile, "r")
        for line in f:
            name = re.match(r'^(\w+\s+\w+)', line)
            if name:
                authors.append(name.group(1))
        print("Authors:", ", ".join(authors), "\n")
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
                self.cfg = self.readcfg(item)

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
                        if re.match(r'\[', self.get(*args[:-1], field='type')):
                            self.add(*args)
                        else:
                            self.set(*args, clobber=True)

    #########################################################################
    def loadfunction(self, modname, modtype, funcname):
        '''
        Dynamic load of module based on scpath search parameter.
        '''

        # module search path depends on modtype
        if modtype == 'tool':
            fullpath = self.find(f"tools/{modname}/{modname}.py")
        elif modtype == 'flow':
            fullpath = self.find(f"flows/{modname}.py")
        elif modtype == 'pdk':
            fullpath = self.find(f"foundries/{modname}.py")
        else:
            self.logger.error(f"Illegal module type '{modtype}'.")
            self.error = 1
            return

        # try loading module if found
        if fullpath:
            if modtype == 'tool':
                self.logger.debug(f"Loading function '{funcname}' from module '{modname}'")
            else:
                self.logger.info(f"Loading function '{funcname}' from module '{modname}'")
            try:
                sys.path.append(os.path.dirname(fullpath))
                imported = importlib.import_module(modname)
                if hasattr(imported, funcname):
                    function = getattr(imported, funcname)
                else:
                    function = None
                sys.path.pop()
                return function
            except:
                traceback.print_exc()
                self.logger.error(f"Module setup failed for '{modname}'")
                self.error = 1

    ###########################################################################
    def target(self, arg=None):
        """
        Loads a technology target and EDA flow based on a named target string.

        The eda flow and technology targets are dynamically loaded at runtime
        based on 'target' string specifed as <technology>_<edaflow>.
        The edaflow part of the string is optional. The 'technology' and
        'edaflow' are used to search and dynamically import modules based on
        the PYTHON environment variable.

        The target function supports ASIC as well as FPGA design flows. For
        FPGA flows, the function simply sets the partname to the technology
        field of the target string. For ASIC flows, the target is used to
        bundle and simplify the setup of SC schema parameters en masse. Modern
        silicon process PDKs can contain hundreds of files and setup variables.
        Doing this setup once and creating a named target significantly
        improves the ramp-up time for new users and reduces the chance of
        costly setup errors.

        Imported modules implement a set of functions with standardized
        function names and interfaces as described below.

        **TECHNOLOGY:**

        **setup_pdk (chip):** Configures basic PDK information,
        including setting up wire tracks and setting filesystem pointers to
        things like spice models, runsets, design rules manual. The function
        takes the a Chip object as an input argument and uses the Chip's
        schema acess methods to set/get parameters. To maximize reuse it
        is recommended that the setup_platform function includes only core
        PDK information and does not include settings for IPs such as
        libraries or design methodology settings.

        **EDAFLOW:**

        **setup_flow (chip):** Configures the edaflow by setting
        up the steps of the execution flow (eg. 'flowgraph') and
        binding each step to an EDA tool. The tools are dynamically
        loaded in the 'runstep' method based on the step tool selected.

        Args:
            arg (string): Name of target to load. If None, the target is
                read from the SC schema.

        Examples:
            >>> chip.target("freepdk45_asicflow")
            Loads the 'freepdk45' and 'asicflow' settings.
            >>> chip.target()
            Loads target settings from chip.get('target')

        """

        #Sets target in dictionary if string is passed in
        if arg is not None:
            self.set('target', arg)

        # Error checking
        if not self.get('target'):
            self.logger.error('Target not defined.')
            sys.exit(1)
        elif len(self.get('target').split('_')) > 2:
            self.logger.error('Target should have zero or one underscore')
            sys.exit(1)
        else:

            target = self.get('target')
            self.logger.info(f"Loading target '{target}'")

        # search for module matches
        targetlist = target.split('_')

        for i, item in enumerate(targetlist):
            func_flow = self.loadfunction(item, 'flow', 'setup_flow')
            func_pdk = self.loadfunction(item, 'pdk', 'setup_pdk')
            func_tool = self.loadfunction(item, 'tool', 'setup_tool')
            if (i == 0) & bool(func_flow):
                func_flow(self)
            elif (i == 0) & bool(func_tool):
                step = self.get('arg','step')
                self.set('flowgraph', step, '0', 'tool', item)
                self.set('flowgraph', step, '0', 'weight', 'errors', 1.0)
                self.set('flowgraph', step, '0', 'weight', 'warnings', 1.0)
                self.set('flowgraph', step, '0', 'weight', 'runtime', 1.0)
            elif bool(func_pdk):
                func_pdk(self)
            elif self.get('mode') == 'asic':
                self.logger.error(f'Target {item} not found')
                sys.exit(1)

        self.logger.info(f"Operating in '{self.get('mode')}' mode")

    ###########################################################################
    def getsinks(self, step, index, cfg=None):
        '''
        Finds the destinations of the current step/index.
        Returns a dictionary of step/index.
        '''
        if cfg is None:
            cfg = self.cfg

        sinks ={}
        for a in self.getkeys('flowgraph', cfg=cfg):
            for b in self.getkeys('flowgraph', a, cfg=cfg):
                if self.getkeys('flowgraph', a, b, 'input'):
                    for c in self.getkeys('flowgraph', a, b, 'input'):
                        for d in self.get('flowgraph', a, b, 'input', c):
                            if (step==c) & (index==d):
                                sinks[a] = b

        return sinks

    ###########################################################################
    def fork(self, step, index, n):
        '''
        Clones a flowgraph step to n way. Settings from step/index are copied
        n-way.
        '''

        #clone step/index n ways
        cfglocal = copy.deepcopy(self.cfg['flowgraph'][step][index])
        for i in range(n):
            newindex = str(int(index)+i+1)
            self.cfg['flowgraph'][step][newindex] = copy.deepcopy(cfglocal)

        #finding all steps that depend on this one
        sinks = self.getsinks(step,index)

        #updating the input indexes of those steps
        for k, v in sinks.items():
            for i in range(n):
                print(step, index, k,v,i)
                self.add('flowgraph', str(k), str(v), 'input', step, str(i+1))

    ###########################################################################
    def help(self, *args):
        """
        Returns a formatted help string based on the keypath provided.

        Args:
            *args(string): A variable length argument list specifying the
                keypath for accessing the SC parameter schema.

        Returns:
            A formatted multi-line help string.

        Examples:
            >>> chip.help('asic','diesize')
            Displays help information about the 'asic, diesize' parameter

        """

        self.logger.debug('Fetching help for %s', args)

        #Fetch Values

        description = self.get(*args, field='shorthelp')
        typestr = self.get(*args, field='type')
        switchstr = str(self.get(*args, field='switch'))
        defstr = str(self.get(*args, field='defvalue'))
        requirement = str(self.get(*args, field='requirement'))
        helpstr = self.get(*args, field='help')
        example = self.get(*args, field='example')


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
    def get(self, *args, cfg=None, field='value'):
        """
        Returns a parameter value based on keypath input.

        The method searches the SC cfg-schema for the keypath and field
        provided and returns a paramater value of a type specified by the
        parameter 'type' field. Accesses to non-existing dictionary entries
        results in a logger error and in the setting the 'self.error' flag to 1.

        Args:
            args(string): A variable length argument list specifying the
                keypath for accessing the cfg schema.
            cfg(dict): A dictionary within the Chip object to use for
                key-sequence query.
            field(string): Leaf cell field to fetch. Examples of
                valid fields include 'value', 'defvalue', 'type'. For
                a complete description of the valid entries, see the
                schema.py module.

        Returns:
            Value found for the key sequence and field provided.

        Examples:
            >>> get('pdk', 'foundry')
            Returns the name of the foundry.

        """

        if cfg is None:
            cfg = self.cfg

        keypath = ','.join(args)

        if(field != 'value'):
            fieldstr = "Field = " + field
        else:
            fieldstr = ""

        self.logger.debug(f"Reading from [{keypath}]. Field = '{field}'")
        return self._search(cfg, keypath, *args, field=field, mode='get')

    ###########################################################################
    def getkeys(self, *args, cfg=None):
        """
        Returns keys from Chip dictionary based on key-sequence provided.

        Accesses to non-existing dictionary entries results in a logger error
        and in the setting the 'self.error' flag to 1.

        Args:
            args(string): A variable length argument list specifying the
                key sequence for accessing the cfg nested dictionary.
                For a complete description of he valid key sequence,
                see the schema.py module. If the argument list is empty, all
                dictionary trees are returned as as a list of lists.
            cfg (dict): A dictionary within the Chip object to use for
                key list query.

        Returns:
            List of keys found for the key sequence provided.

        Examples:
            >>> getkeys('pdk')
            Returns all keys for the 'pdk' dictionary.
            >>> getkeys()
            Returns all key trees in the dictionary as a list of lists.
        """

        if cfg is None:
            cfg = self.cfg

        if len(list(args)) > 0:
            keypath = ','.join(args[:-1])
            self.logger.debug('Getting schema parameter keys for: %s', args)
            keys = list(self._search(cfg, keypath, *args, mode='getkeys'))
            if 'default' in keys:
                keys.remove('default')
        else:
            self.logger.debug('Getting all schema parameter keys.')
            keys = list(self._allkeys(cfg))

        return keys

    ###########################################################################
    def getcfg(self, *args, cfg=None):
        """
        Returns sub-dictionary from SC schema based on key-sequence provided.
        """

        if cfg is None:
            cfg = self.cfg

        if len(list(args)) > 0:
            keypath = ','.join(args[:-1])
            self.logger.debug('Getting cfg for: %s', args)
            localcfg = self._search(cfg, keypath, *args, mode='getcfg')

        return copy.deepcopy(localcfg)

    ###########################################################################
    def set(self, *args, cfg=None, clobber=True, field='value'):
        '''
        Sets a Chip dictionary value based on key-sequence and data provided.

        Accesses to non-existing dictionary entries results in a logger
        error and in the setting the 'self.error' flag to 1. For built in
        dictionary keys with the 'default' keywork entry, new leaf trees
        are automatically created by the set method by copying the default
        tree to the tree described by the key-sequence as needed.

        The data type provided must agree with the dictionary parameter 'type'.
        Before setting the parameter, the data value is type checked.
        Any type descrepancy results in a logger error and in setting the
        self.error flag to 1. For descriptions of the legal values for a
        specific parameter, refer to the schema.py documentation. Legal values
        are cast to strings before writing to the dictionary.

        Args:
            args (string): A variable length key list used to look
                up a Chip dictionary entry. For a complete description of the
                valid key lists, see the schema.py module. The key-tree is
                supplied in order.
            cfg (dict): A dictionary within the Chip object to use for
                key list query.

        Examples:
            >>> set('source', 'mydesign.v')
            Sets the file 'mydesign.v' to the list of sources.
        '''

        if cfg is None:
            cfg = self.cfg

        # Verify that all keys are strings
        for key in args[:-1]:
            if not isinstance(key,str):
                self.logger.error(f"Key [{key}] is not a string [{args}]")

        keypath = ','.join(args[:-1])
        all_args = list(args)

        self.logger.debug(f"Setting [{keypath}] to {args[-1]}")
        return self._search(cfg, keypath, *all_args, field=field, mode='set', clobber=clobber)

    ###########################################################################
    def add(self, *args, cfg=None):
        '''
        Appends an item to the parameter value specified by the keypath.

        Access to non-existing dictionary entries results in a logger error
        and in the setting the 'self.error' flag to 1. For built in dictionary
        keys with the 'default' keywork entry, new leaf trees are automatically
        created by copying the default tree to the tree described by the
        key-sequence as needed.

        The data type provided must agree with the dictionary parameter
        'type'. Before setting the parameter, the data value is type
        checked. Any type descrepancy results in a logger error and the
        self.error flag being raised.

        The add operation is not legal for scalar types.

        Args:
            args (string): A variable length argument list consisting of a
                keypath to a schema parameter followed by the item(s) to add
                to the parameter value.
            cfg (dict): A dictionary within the Chip object to use for
                key list query.

        Examples:
            >>> add('source', 'mydesign.v')
            Sets the file 'mydesign.v' to the list of sources.
        '''

        if cfg is None:
            cfg = self.cfg

        # Verify that all keys are strings
        for key in args[:-1]:
            if not isinstance(key,str):
                self.logger.error(f"Key [{key}] is not a string [{args}]")

        keypath = ','.join(args[:-1])
        all_args = list(args)

        self.logger.debug(f'Appending value {args[-1]} to [{keypath}]')
        return self._search(cfg, keypath, *all_args, field='value', mode='add')


    ###########################################################################
    def _allkeys(self, cfg, keys=None, keylist=None):
        '''
        Returns list of all keypaths in the SC schema.
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
        Internal recursive function that searches a Chip dictionary for a
        match to the combination of *args and fields supplied. The function is
        used to set and get data within the dictionary.

        Args:
            args (string): A variable length key list used to look
                up a Chip dictionary entry.
            cfg(dict): The cfg dictionary within the Chip object to extend
            keypath (string): Concatenated keypath used for error logging.
            field(string): Leaf cell field to fetch. Examples of
                valid fields include 'value', 'defvalue', 'type'. For
                a complete description of the valid entries, see the
                schema.py module.
            mode(string): Specifies what to do (set/get/add/getkeys)

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
                    cfg[param]['value'] = cfg[param]['defvalue']
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
                if (cfg[param]['type'] == 'bool' ):
                    if val == True:
                        val = "true"
                    elif val == False:
                        val = "false"
                # checking if value has been set
                if field not in cfg[param]:
                    selval = cfg[param]['defvalue']
                else:
                    selval =  cfg[param]['value']
                # updating values
                if cfg[param]['lock'] == "true":
                    self.logger.debug("Ignoring {mode}{} to [{keypath}]. Lock bit is set.")
                elif (mode == 'set'):
                    if (selval in empty) | clobber:
                        if (not list_type) & (val is None):
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
                        self.logger.info(f"Ignoring set() to [{keypath}], value already set. Use clobber=true to override.")
                elif (mode == 'add'):
                    if list_type & (not isinstance(val, list)):
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
                        for item in selval:
                            if sctype == 'int':
                                return_list.append(int(item))
                            elif sctype == 'float':
                                return_list.append(float(item))
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
                #all non-value fields are strings
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
    def extend(self, filename, cfg=None):
        """
        Extends the SC dictionary based on the provided JSON file.

        Reads in an SC compatible dictionary from a JSON file and copies
        all entries to the dictionary specified by the 'chip' and
        'cfg' arguments. All dictionary entries must include fields for: type,
        defvalue, switch, requirment, type, lock, shorthelp, example, and help.
        In addition, extensions for file/dir types must include fields for
        lock, copy, filehash, data, and signature. For complete information
        about these fields, refer to the schema.py

        Args:
            filename (string): A path to the file containing the json
                dictionary to be processd.
            cfg(dict): The cfg dictionary within the Chip object to extend

        """

        if cfg is None:
            cfg = self.cfg

        abspath = os.path.abspath(filename)

        self.logger.info('Extending SC schema with file %s', abspath)

        with open(abspath, 'r') as f:
            localcfg = json.load(f)

        self.merge(cfg, localcfg)

        return localcfg

    ###########################################################################
    def include(self, name, filename=None):
        '''
        Include a component
        '''

        if filename is None:
            module = importlib.import_module(name)
            setup_design = getattr(module, "setup_design")
            chip = setup_design()
        else:
            chip = siliconcompiler.Chip(design=name)
            chip.readcfg(filename)

        return chip

    ###########################################################################
    def prune(self, cfg, top=True, keeplists=False):
        '''
        Recursive function that takes a copy of the Chip dictionary and
        then removes all sub trees with non-set values and sub-trees
        that contain a 'default' key.


        Returns the pruned dictionary

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
                    self.prune(cfg=localcfg[k], top=False, keeplists=keeplists)
            if top:
                i += 1
            else:
                break

        return localcfg

    ###########################################################################
    def find(self, filename):
        """
        Returns an absolute e path for the provided filename provided.

        The method searches for a match for the relative filename using
        the scpath

        environment variable. Legal shell variables consisting of '$' followed
        by numbers, underscores, and digits are replaced with the variable
        value.
        """

        # Replacing environment variables
        vars = re.findall(r'\$(\w+)', filename)
        for item in vars:
            varpath = os.getenv(item)
            filename = filename.replace("$"+item, varpath)

        # Handling relative path and abspath matches
        if os.path.exists(os.path.abspath(filename)):
            filename = os.path.abspath(filename)
        # Matching paths relative to scpaths
        else:
            scpaths = [self.cwd]
            scpaths.append(self.scroot)
            scpaths.extend(self.get('scpath'))
            found = False
            for searchdir in scpaths:
                abspath = os.path.abspath(searchdir + "/" + filename)
                if os.path.exists(abspath):
                    found = True
                    break
            if found:
                filename = abspath
            else:
                filename = None

        return filename


    ###########################################################################
    def _abspath(self, cfg):
        '''Recursive function that goes through Chip dictionary and
        resolves all relative paths where required.
        '''

        #Recursively going through dict to set abspaths for files
        for k, v in cfg.items():
            if isinstance(v, dict):
                #indicates leaf cell
                if 'value' in cfg[k].keys():
                    #only do something if type is file
                    if re.search('file|dir', cfg[k]['type']):
                        #iterate if list
                        if re.match(r'\[', cfg[k]['type']):
                            for i, val in enumerate(list(cfg[k]['value'])):
                                #Look for relative paths in search path
                                cfg[k]['value'][i] =self.find(val)
                        else:
                            cfg[k]['value'] = self.find(cfg[k]['value'])
                else:
                    self._abspath(cfg[k])

    ###########################################################################
    def _printcfg(self, cfg, keys=None, file=None, mode="", field='value', prefix=""):
        '''
        Prints out Chip dictionary values one command at a time. Currently only
        TCL is supported.
        '''

        if keys is None:
            keys = []
        for k in cfg:
            newkeys = keys.copy()
            newkeys.append(k)
            #detect leaf cell
            if 'defvalue' in cfg[k]:
                if mode == 'tcl':
                    if 'value' not in cfg[k]:
                        selval = cfg[k]['defvalue']
                    else:
                        selval =  cfg[k]['value']
                    if bool(re.match(r'\[', str(cfg[k]['type']))) & (field == 'value'):
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
                if file is None:
                    print(outstr)
                else:
                    print(outstr, file=file)
            else:
                self._printcfg(cfg[k],
                               keys=newkeys,
                               file=file,
                               mode=mode,
                               field=field,
                               prefix=prefix)

    ###########################################################################
    def merge(self, cfg1, cfg2, append=False):
        """
        Merges the SC configuration dict cfg2 into cfg1.

        This is a dict merge routine built for the SC schema. The routine
        takes into account the availabiltiy of the SC dictionary being
        ac combination of static entries and dynamic entries specified by the
        keyword 'default' specified as a key.

        Args:
            cfg1 (dict): Original dict within
            cfg2 (dict): New dict to merge into the original dict
            strict (bool): If True, d1 is considered the golden reference
                and only d2 with identical keylists are merged.
            append (bool): If True, for list variables,the new config valuse
                are appended to the old values.
        """

        #creating local copy of original dict to be overwritten
        #it would be nasty to set a global varaible inside a function
        localcfg = copy.deepcopy(cfg1)

        cfg1_keys = self.getkeys(cfg=localcfg)
        cfg2_keys = self.getkeys(cfg=cfg2)

        for keylist in cfg2_keys:
            if 'default' not in keylist:
                typestr = self.get(*keylist, cfg=cfg2, field='type')
                val = self.get(*keylist, cfg=cfg2)
                arg = keylist.copy()
                arg.append(val)
                if bool(re.match(r'\[', typestr)) & append:
                    self.add(*arg, cfg=localcfg)
                else:
                    self.set(*arg, cfg=localcfg, clobber=True)

        #returning dict
        return localcfg



    ###########################################################################
    def _keypath_empty(self, key, cfg):
        emptylist = ("null", None, [])

        value = self.get(*key, cfg=cfg)
        defvalue = self.get(*key, cfg=cfg, field='defvalue')
        value_empty = (defvalue in emptylist) and (value in emptylist)

        return value_empty

    ###########################################################################
    def check(self, step, index, mode='static', cfg=None):
        '''
        Performs a setup validity check and returns success status.

        Returns:
            Returns True of if the Chip dictionary is valid, else returns
            False.

        Examples:
            >>> check()
           Returns True of the Chip dictionary checks out.
        '''

        if cfg is None:
            cfg = self.cfg

        #1. Checking that flowgraph is legal
        if not self.getkeys('flowgraph'):
            self.error = 1
            self.logger.error(f"No flowgraph defined.")
        legal_steps = self.getkeys('flowgraph')
        for a in self.getkeys('flowgraph'):
            for b in self.getkeys('flowgraph', a):
                for input in self.getkeys('flowgraph', a, b, 'input'):
                    if not input in legal_steps:
                        self.error = 1
                        self.logger.error(f"Input '{a}' is not a legal step.")

        #2. Check requirements list
        allkeys = self.getkeys()
        for key in allkeys:
            keypath = ",".join(key)
            if 'default' not in key:
                key_empty = self._keypath_empty(key, cfg)
                requirement = self.get(*key, cfg=cfg, field='requirement')
                if key_empty and (str(requirement) == 'all'):
                    self.error = 1
                    self.logger.error(f"Global requirement missing for [{keypath}].")
                elif key_empty and (str(requirement) == self.get('mode')):
                    self.error = 1
                    self.logger.error(f"Mode requirement missing for [{keypath}].")

        #3. Check per tool parameter requirements (when tool exists)
        if self.get('flowgraph', step, index, 'tool'):
            tool = self.get('flowgraph', step, index, 'tool')
            if 'req' in  self.getkeys('eda', tool, step, index):
                all_required = self.get('eda', tool, step, index, 'req')
                for item in all_required:
                    keypath = item.split(',')
                    if self._keypath_empty(keypath, cfg):
                        self.error = 1
                        self.logger.error(f"Value empty for [{keypath}].")

            if self._keypath_empty(['eda', tool, step, index, 'exe'], cfg):
                self.error = 1
                self.logger.error(f'Executable not specified for tool {tool} used in flowgraph step {step}')

            if self._keypath_empty(['eda', tool, step, index, 'version'], cfg):
                self.error = 1
                self.logger.error(f'Version not specified for tool {tool} used in flowgraph step {step}')

        return self.error

    ###########################################################################
    def readcfg(self, filename, merge=True, cfg=None):
        """
        Reads a json or yaml formatted file into the Chip dictionary.

        Args:
            filename (file): A relative or absolute path toe a file to load
                into dictionary.

        Examples:
            >>> readcfg('mychip.json')
            Loads the file mychip.json into the current Chip dictionary.
        """

        #TODO: add ability to read in all files set in 'cfg' if no file
        #name is specified

        if cfg is None:
            cfg = self.cfg

        abspath = os.path.abspath(filename)
        self.logger.debug('Reading configuration file %s', abspath)

        #Read arguments from file based on file type
        if abspath.endswith('.json'):
            with open(abspath, 'r') as f:
                localcfg = json.load(f)
            f.close()
        elif abspath.endswith('.yaml'):
            with open(abspath, 'r') as f:
                localcfg = yaml.load(f, Loader=yaml.SafeLoader)
            f.close()
        else:
            self.error = 1
            self.logger.error('Illegal file format. Only json/yaml supported. %s', abspath)


        #Merging arguments with the Chip configuration
        if merge:
            localcfg = self.merge(cfg, localcfg)

        return localcfg

    ###########################################################################
    def writecfg(self, filename, cfg=None, prune=True, keeplists=False, abspath=False):
        '''Writes out Chip dictionary in json, yaml, or TCL file format.

        Args:
            filename (file): A relative or absolute path to a file to dump
                 dictionary into.
            cfg (dict): A dictionary to dump. If 'None' is specified, then
                 the current dictionary is dumped.
            prune (bool): If set to True, then only non-default trees and
                 non empty values are dumped. If set to False, the whole
                 dictionary is dumped.
            abspath (bool): If set to True, then all file paths within the
                 Chip dictionary are resolved to absolute values.

        Examples:
            >>> writecfg('mydump.json')
            Prunes and dumps the current Chip dictionary into mydump.json
            >>> writecfg('bigdump.json', prune=False)
            Dumps the complete current Chip dictionary into bigdump.json
        '''

        if cfg is None:
            cfg = self.cfg

        filepath = os.path.abspath(filename)
        self.logger.debug('Writing configuration to file %s', filepath)

        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        if prune:
            self.logger.debug('Pruning dictionary before writing file %s', filepath)
            cfgcopy = self.prune(cfg, keeplists=keeplists)
        else:
            cfgcopy = copy.deepcopy(cfg)

        # resolve absolute paths
        if abspath:
            self._abspath(cfgcopy)

        # convert to fusesoc
        cfgfuse = self._dump_fusesoc(cfg)


        with open(filepath, 'w') as f:
            if filepath.endswith('.json'):
                print(json.dumps(cfgcopy, indent=4, sort_keys=True), file=f)
            elif filepath.endswith('.yaml'):
                print(yaml.dump(cfgcopy, Dumper=YamlIndentDumper, default_flow_style=False), file=f)
            elif filepath.endswith('.core'):
                print("CAPI=2:", file=f)
                print(yaml.dump(cfgfuse, Dumper=YamlIndentDumper, default_flow_style=False), file=f)
            elif filepath.endswith('.bender.yml'):
                self._write_bender(cfgcopy, file=f)
            elif filepath.endswith('.tcl'):
                print("#############################################", file=f)
                print("#!!!! AUTO-GENERATED FILE. DO NOT EDIT!!!!!!", file=f)
                print("#############################################", file=f)
                self._printcfg(cfgcopy, mode="tcl", prefix="dict set sc_cfg", file=f)
            else:
                self.logger.error('File format not recognized %s', filepath)
                self.error = 1

    ###########################################################################

    def _dump_fusesoc(self, cfg):

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
    def writegraph(self, filename, graphtype='flowgraph'):
        '''Exports the execution flow graph using the graphviz library.
        For graphviz formats supported, see https://graphviz.org/.

        '''
        filepath = os.path.abspath(filename)
        self.logger.debug('Writing flowgraph to file %s', filepath)
        fileroot, ext = os.path.splitext(filepath)
        fileformat = ext.replace(".", "")
        dot = graphviz.Digraph(format=fileformat)
        dot.attr(bgcolor='transparent')
        if graphtype == 'flowgraph':
            for step in self.getkeys('flowgraph'):
                for index in self.getkeys('flowgraph', step):
                    node = step+index
                    # create step node
                    if self.get('flowgraph', step, index, 'tool'):
                        labelname = step+index+'\\n('+self.get('flowgraph', step, index, 'tool')+")"
                    else:
                        labelname = step
                    dot.node(node, label=labelname)
                    # get inputs
                    all_inputs = []
                    for i in self.getkeys('flowgraph', step, index, 'input'):
                        for j in self.get('flowgraph', step, index, 'input', i):
                            all_inputs.append(i+j)
                    for item in all_inputs:
                        dot.edge(item, node)
        elif graphtype == 'hier':
            for parent in self.getkeys('hier'):
                dot.node(parent)
                for child in self.getkeys('hier', parent):
                    dot.edge(parent, child)
        dot.render(filename=fileroot, cleanup=True)

    ########################################################################
    def collect(self, cfg=None):
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
        if cfg is None:
            cfg = self.cfg

        indir = 'inputs'
        step = self.get('arg','step', cfg=cfg)

        if not os.path.exists(indir):
            os.makedirs(indir)

        self.logger.info('Collecting input sources')

        #copy all parameter take from self dictionary
        copyall = self.get('copyall')
        allkeys = self.getkeys(cfg=cfg)
        for key in allkeys:
            leaftype = self.get(*key, cfg=cfg, field='type')
            if re.search('file', leaftype):
                copy = self.get(*key, cfg=cfg, field='copy')
                value = self.get(*key, cfg=cfg)
                if copyall | (copy):
                    for item in value:
                        filepath = self.find(item)
                        self.logger.info(f"Copying {filepath} to '{step}0/inputs' directory")
                        shutil.copy(filepath, indir)

    ###########################################################################
    def hash(self, cfg=None):
        '''Computes sha256 hash of files based on hashmode set in cfg dict.

        Valid hashing modes:
        * OFF: No hashing of files
        * ALL: Compute hash of all files in dictionary. This couuld take
        hours for a modern technology node with thousands of large setup
        files.
        * SELECTIVE: Compute hashes only on files accessed by the step
        currently being executed.

        '''

        if cfg is None:
            cfg = self.cfg

        hashmode = self.get('hashmode')
        self.logger.info('Computing file hashes with hashmode=%s', hashmode)

        allkeys = self.getkeys(cfg=cfg)

        for keylist in allkeys:
            if 'filehash' in keylist:
                filelist = self.get(*keylist, cfg=cfg)
                self.set([keylist,[]], cfg=cfg, clobber=True)
                hashlist = []
                for item in filelist:
                    filename = self.find(item)
                    self.logger.debug('Computing hash value for %s', filename)
                    if os.path.isfile(filename):
                        sha256_hash = hashlib.sha256()
                        with open(filename, "rb") as f:
                            for byte_block in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(byte_block)
                        hash_value = sha256_hash.hexdigest()
                        hashlist.append(hash_value)
                self.set([keylist,hashlist], cfg=cfg, clobber=True)

    ###########################################################################
    def audit(self, filename=None):
        '''Performance an an audit of each step in the flow
        '''
        return filename

    ###########################################################################
    def calcyield(self, model='poisson'):
        '''Calculates raw die yield

        Calcualtes the raw yield of the design as a function of design area
        and d0 defect density. Calculation can be done based ont he poisson
        model (default) or the murphy model. The die area and the d0
        parameters are taken from the chip dictionary.

        * Poisson model: dy = exp(-area * d0/100).
        * Murphy model: dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.

        Args:
            model (string): Model to use for calculation (poission or murphy)

        Returns:
            Design yield percentage (float).

        '''

        d0 = self.get('pdk', 'd0')
        diesize = self.get('asic', 'diearea').split()
        diewidth = (diesize[2] - diesize[0])/1000
        dieheight = (diesize[3] - diesize[1])/1000
        diearea = diewidth * dieheight

        if model == 'poisson':
            dy = math.exp(-diearea * d0/100)
        elif model == 'murphy':
            dy = ((1-math.exp(-diearea * d0/100))/(diearea * d0/100))**2

        return dy

    ###########################################################################

    def dpw(self):
        '''Calculates dies per wafer

        Calcualtes the gross dies per wafer based on the design area, wafersize,
        wafer edge margin, and scribe lines. The calculation is done by starting
        at the center of the wafer and placing as many complete design
        footprints as possible within a legal placement area.

        Returns:
            The number of gross dies per wafer (int).

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
    def diecost(self, n):
        '''Calculates total cost of producing 'n', including design costs,
        mask costs, packaging costs, tooling, characterization, qualifiction,
        test. The exact cost model is given by the formula:

        '''

        return n

    ###########################################################################
    def summary(self):
        '''
        Creates a summary of the run metrics generated from the 'start' step
        to the 'stop' step.

        Args:
            filename (filename): A file to write the summary report to. If
                the value is 'None', the summary is printed to stdout.

        Examples:
            >>> summary()
            Prints out a summary of the run to stdout.
        '''

        if self.get('steplist'):
            steplist = self.get('steplist')
        else:
            steplist = self.getsteps()

        jobdir = "/".join([self.get('dir'),
                           self.get('design'),
                           self.get('jobname') + str(self.get('jobid'))])

        if self.get('mode') == 'asic':
            info = '\n'.join(["SUMMARY:\n",
                              "design = " + self.get('design'),
                              "foundry = " + self.get('pdk', 'foundry'),
                              "process = " + self.get('pdk', 'process'),
                              "targetlibs = "+" ".join(self.get('asic', 'targetlib')),
                              "jobdir = "+ jobdir])
        elif self.get('mode') == 'fpga':
            info = '\n'.join(["SUMMARY:\n",
                              "design = "+self.get('design'),
                              "partname = "+self.get('fpga','partname'),
                              "jobdir = "+ jobdir])
        else:
            info = '\n'.join(["SUMMARY:\n",
                              "design = "+self.get('design'),
                              "jobdir = "+ jobdir])

        print("-"*135)
        print(info, "\n")

        # Stepping through all steps/indices and printing out metrics
        data = []
        steps = []
        colwidth = 8

        #Creating Header
        steps = []
        colwidth = 8
        for step in steplist:
            #TODO, fix for parallel, follow selection
            steps.append(step.center(colwidth))

        #Creating table of real values
        metrics = []

        #Creating index selecto
        metrics.append(" input")
        row = []
        for step in steplist:
            if not self.getkeys('flowgraph', step, '0','input'):
                sel_in = ""
            elif self.get('flowstatus', step, '0', 'select'):
                sel_in = self.get('flowstatus', step, '0', 'select')[0]
                if len(self.get('flowstatus', step, '0', 'select'))>1:
                    sel_in.replace(r"\d+$", "**")
            else:
                stepsel= self.getkeys('flowgraph', step, '0', 'input')[0]
                isel = self.get('flowgraph', step, '0', 'input', stepsel)[0]
                sel_in = stepsel + isel
            row.append(" " + sel_in.center(colwidth))
        data.append(row)

        # only report metrics with weights
        metric_list = []
        for step in steplist:
            for metric in self.getkeys('flowgraph', step, '0', 'weight'):
                if self.get('flowgraph', step, '0', 'weight', metric):
                    if metric not in metric_list:
                        metric_list.append(metric)
        for metric in metric_list:
            metrics.append(" " + metric)
            row = []
            for step in steplist:
                value = str(self.get('metric', step, '0', metric, 'real'))
                row.append(" " + value.center(colwidth))
            data.append(row)

        pandas.set_option('display.max_rows', 500)
        pandas.set_option('display.max_columns', 500)
        pandas.set_option('display.width', 100)
        df = pandas.DataFrame(data, metrics, steps)
        print(df.to_string())
        print("-"*135)

    ###########################################################################
    def getsteps(self, cfg=None):
        '''
        Returns an ordered list based on the flowgraph
        '''

        if cfg is None:
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
    def flowinputs(self, step, index, cfg=None):
        '''
        Returns a list of inputs to the current step as a list of concatenated
        strings step+index.
        '''

        if cfg is None:
            cfg = self.cfg

        all_inputs = []
        for a in self.getkeys('flowgraph'):
            for b in self.getkeys('flowgraph', a):
                for c in self.getkeys('flowgraph', a, b, 'output'):
                    for d in self.get('flowgraph', a, b, 'output', c):
                        if (c == step) & (str(d) == index):
                            all_inputs.append(a + b)

        return all_inputs

    ###########################################################################
    def _allpaths(self, cfg, step, index, path=None, allpaths=None):

        if path is None:
            allpaths = []
            path = []
        all_inputs = []
        for a in self.getkeys('flowgraph', step, index, 'input', cfg=cfg):
            for b in self.get('flowgraph', step, index, 'input', a, cfg=cfg):
                all_inputs.append(a + b)
        if not all_inputs:
            allpaths.append(path)
        else:
            for a in self.getkeys('flowgraph', step, index, 'input', cfg=cfg):
                for b in self.get('flowgraph', step, index, 'input', a, cfg=cfg):
                    newpath = path.copy()
                    newpath.append(a+b)
                    return self._allpaths(cfg, a, b, path=newpath, allpaths=allpaths)
        return list(allpaths)



    ###########################################################################
    def join(self, *steps):
        '''
        Joins all inputs from all indexes of all steps in args as a list.
        The function sets the flowstatus select parameter in the schema
        '''

        steplist = list(steps)
        sel_inputs = []

        for a in steplist:
            for b in self.getkeys('flowgraph', a):
                sel_inputs.append(a+b)

        # no score for join, so just return 0
        return 0, sel_inputs

    ###########################################################################
    def minimum(self, *steps):
        '''
        Wrapper function for minmax, with op = 'minimum'.
        See minmax() function for full help.
        '''
        return self.minmax(*steps, op="minimum")

    ###########################################################################
    def maximum(self, *steps, step=None, index=None):
        '''
        Wrapper function for minmax, with op = 'minimum'
        See minmax() function for full help.
        '''
        return self.minmax(*steps, op="maximim")

    ###########################################################################
    def minmax(self, *args, op="minimum"):
        '''
        Calculates the max value for all indexes of all steps provided.

        Sequence of operation:

        1. Check all steps/indexes to see if all metrics meets goals
        2. Check all steps/indees to find global min/max for each metric
        3. Select MAX value if all metrics are met.
        4. Normalize the max value as sel = (val - MIN) / (MAX - MIN)
        5. Return normalized value and index

        Meeting metric goals takes precedence over compute metric scores.
        Only goals with values set and metrics with weights set are considered
        in the calulation.

        Args:
            args (string): A variable length list of steps

        Returns:
            tuple containing

            - score (float): Maximum score
            - step (str): Winning step
            - index (str): Winning index

        '''

        steplist = list(args)

        # Keeping track of the steps/indexes that have goals met
        failed = {}
        goals_met = False
        for step in steplist:
            failed[step] = {}
            for index in self.getkeys('flowgraph', step):
                if self.get('flowstatus', step, index, 'error'):
                    failed[step][index] = True
                else:
                    failed[step][index] = False
                    for metric in self.getkeys('metric', step, index):
                        if 'goal' in self.getkeys('metric', step, index, metric):
                            goal = self.get('metric', step, index, metric, 'goal')
                            real = self.get('metric', step, index, metric, 'real')
                            if bool(real > goal):
                                failed[step][index] = True
                if not failed[step][index]:
                    goals_met = True

        # Calculate max/min values for each metric
        max_val = {}
        min_val = {}
        for step in steplist:
            max_val[step] = {}
            min_val[step] = {}
            for metric in self.getkeys('flowgraph', step, '0', 'weight'):
                max_val[step][metric] = 0
                min_val[step][metric] = float("inf")
                for index in self.getkeys('flowgraph', step):
                    if not self.get('flowstatus', step, index, 'error'):
                        real = self.get('metric', step, index, metric, 'real')
                        max_val[step][metric] = max(max_val[step][metric], real)
                        min_val[step][metric] = min(min_val[step][metric], real)

        # Select the minimum index
        min_score = {}
        step_winner = ""
        for step in steplist:
            min_score = float("inf")
            step_winner = 0
            for index in self.getkeys('flowgraph', step):
                if not self.get('flowstatus', step, index, 'error'):
                    score = 0.0
                    for metric in self.getkeys('flowgraph', step, index, 'weight'):
                        real = self.get('metric', step, index, metric, 'real')
                        if not (max_val[step][metric] - min_val[step][metric]) == 0:
                            scaled = (real - min_val[step][metric]) / (max_val[step][metric] - min_val[step][metric])
                        else:
                            scaled = max_val[step][metric]
                        score = score + scaled
                    if (score < min_score) & (not (failed[step][index] & goals_met)):
                        min_score = score
                        winner = step+index

        return (score, winner)

    ###########################################################################
    def verify(self, *steps, args=None):
        pass

    ###########################################################################
    def mux(self, *steps, args=None):
        '''
        Mux that selects a single input from the index based on the args.
        '''
        pass


    ###########################################################################
    def _deferstep(self, step, index, active, error):
        '''
        Helper method to run an individual step on a slurm cluster.
        If a base64-encoded 'decrypt_key' is set in the Chip's status
        dictionary, the job's data is assumed to be encrypted,
        and a more complex command is assembled to ensure that the data
        is only decrypted temporarily in the compute node's local storage.
        '''

        # Ensure that error bits are up-to-date in this schema.
        for input_step in self.getkeys('flowgraph', step, index, 'input'):
            for input_index in self.get('flowgraph', step, index, 'input', input_step):
                self.set('flowstatus', input_step, str(input_index), 'error', error[f'{input_step}{input_index}'])

        # Determine which HPC job scheduler being used.
        scheduler_type = self.get('jobscheduler')
        if scheduler_type == 'slurm':
            # The script defining this Chip object may specify feature(s) to
            # ensure that the job runs on a specific subset of available nodes.
            if 'slurm_constraint' in self.status:
                slurm_constraint = self.status['slurm_constraint']
            else:
                slurm_constraint = 'SHARED'
            schedule_cmd = f'srun --constraint {slurm_constraint}'
        elif scheduler_type == 'lsf':
            # TODO: LSF support is untested and currently unsupported.
            schedule_cmd = 'lsrun'

        if 'decrypt_key' in self.status:
            # Job data is encrypted, and it should only be decrypted in the
            # compute node's local storage.
            job_nameid = f"{self.get('jobname')}{self.get('jobid')}"
            cur_build_dir = f"{self.get('dir')}/{self.get('design')}/{job_nameid}"
            tmp_job_dir = f"/tmp/{self.get('remote', 'jobhash')}"
            ctrl_node_dir = self.get('dir')
            self.set('dir', tmp_job_dir, clobber=True)
            tmp_build_dir = "/".join([tmp_job_dir,
                                      self.get('design'),
                                      job_nameid])
            key_bytes = base64.urlsafe_b64decode(self.status['decrypt_key'])
            keystr = key_bytes.decode()
            keypath = f"{tmp_job_dir}/dk"

            # Write the current schema out to an encrypted file in shared storage.
            write_encrypted_cfgfile(self.prune(self.cfg), cur_build_dir, key_bytes, f'{step}{index}')

            # The deferred execution command needs to:
            # * copy encrypted data/key and unencrypted IV into local storage.
            # * store the provided key in local storage.
            # * call 'sc' with the provided key, wait for the job to finish.
            # * copy encrypted data for the completed step into shared storage.
            # * delete all unencrypted data.
            run_cmd  = f'{schedule_cmd} bash -c "'
            run_cmd += f"mkdir -p {tmp_build_dir} ; "
            run_cmd += f"cp -R {ctrl_node_dir}/* {tmp_job_dir}/ ; "
            run_cmd += f"touch {keypath} ; chmod 600 {keypath} ; "
            run_cmd += f"echo -ne '{keystr}' > {keypath} ; "
            run_cmd += f"chmod 400 {keypath} ; "
            run_cmd += f"sc-crypt -mode decrypt_config "\
                           f"-target {tmp_build_dir}/configs/{step}{index}.crypt "\
                           f"-key_file {keypath} ; "
            run_cmd += f"sc-crypt -mode decrypt -target {tmp_build_dir} "\
                           f"-key_file {keypath} ; "
            run_cmd += f"sc -cfg {tmp_build_dir}/configs/{step}{index}.json "\
                           f"-arg_step {step} -arg_index {index} "\
                           f"-dir {tmp_job_dir} -jobscheduler '' "\
                           f"-remote_addr '' -remote_key '' ; "
            run_cmd += f"retcode=\$? ; "
            run_cmd += f"sc-crypt -mode encrypt -target {tmp_build_dir} "\
                           f"-key_file {keypath} ; "
            run_cmd += f"cp -R {tmp_build_dir}/{step}{index}* "\
                           f"{cur_build_dir}/ ; "
            run_cmd += f"rm -rf {tmp_job_dir} ; "
            run_cmd += f"exit \$retcode"
            run_cmd += '"'
        else:
            # Job data is not encrypted, so it can be run in shared storage.
            # Write out the current schema for the compute node to pick up.
            job_dir = "/".join([self.get('dir'),
                                self.get('design'),
                                self.get('jobname') + str(self.get('jobid'))])
            cfg_dir = f'{job_dir}/configs'
            cfg_file = f'{cfg_dir}/{step}{index}.json'
            if not os.path.isdir(cfg_dir):
                os.mkdir(cfg_dir)
            self.writecfg(cfg_file)

            # Create a command to defer execution to a compute node.
            run_cmd  = f'{schedule_cmd} bash -c "'
            run_cmd += f"sc -cfg {cfg_file} -dir {self.get('dir')} "\
                       f"-arg_step {step} -arg_index {index} "\
                        "-jobscheduler '' -remote_addr ''"
            run_cmd += '"'

        # Run the 'srun' command.
        step_result = subprocess.run(run_cmd, shell = True)

        # Clear active bit after the 'srun' command, and set 'error' accordingly.
        error[step + str(index)] = step_result.returncode
        active[step + str(index)] = 0

    ###########################################################################
    def _runstep_safe(self, step, index, active, error):
        try:
            self._runstep(step, index, active, error)
        except SystemExit:
            # calling sys.exit() in _haltstep triggers a "SystemExit"
            # exception, but we can ignore these -- if we call sys.exit(), we've
            # already handled the error.
            pass
        except:
            traceback.print_exc()
            self.logger.error(f"Uncaught exception while running step {step}.")
            self.error = 1
            self._haltstep(step, index, error, active)

    ###########################################################################
    def _runstep(self, step, index, active, error):
        '''
        Private per step run method called by run().
        The method takes in a step string and index string to indicated what
        to run. Execution state coordinated through the active/error
        multiprocessing Manager dicts.

        Execution flow:
        1. Wait in loop until all previous steps/indexes have completed
        2. Set up working directory
        3. Check inputs for errors. Halt if one of the steps yielded
           zero valid results, otherwise merge cfg from previous step
        4. Start job (timer)
        5. Run pre_process
        6. Copy in all input directories selected
        7. Copy in reference scripts to working dir
        8. Save dictionary to be used for running the tool/runstep
        9. Run dynamic check()
        10. Set all metrics for runstep to 0
        11. Check exe version
        12. Run EXE
        13. Post process
        14. Record successful exit
        15. Save package in output dir
        16. Change back to original dir
        17. Lower active bit

        '''

        ##################
        # 1. Wait loop

        self.logger.info(f"Step '{step}' waiting on inputs")

        while True:
            # Checking that there are no pending jobs
            pending = 0
            for input_step in self.getkeys('flowgraph', step, index, 'input'):
                for input_index in self.get('flowgraph', step, index, 'input', input_step):
                    input_str = input_step + input_index
                    pending = pending + active[input_str]

            # beak out of loop when no all inputs are done
            if not pending:
                break
            # Short sleep
            time.sleep(0.1)

        # If the job is configured to run on a cluster, collect the schema
        # and send it to a compute node for deferred execution.
        # (Run the initial 'import' stage[s] locally)
        if self.get('jobscheduler') and \
           self.getkeys('flowgraph', step, index, 'input'):
            # Note: The _deferstep method blocks until the compute node
            # finishes processing this step, and it sets the active/error bits.
            self._deferstep(step, index, active, error)
            return

        # If the job is configured to run on the local machine, run it.
        ##################
        # 2. Directory setup

        workdir = self.getworkdir(step=step,index=index)
        cwd = os.getcwd()
        if os.path.isdir(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir, exist_ok=True)
        os.chdir(workdir)
        os.makedirs('outputs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        ##################
        # 3. Collect run cfg history and check for errors

        design = self.get('design')
        all_inputs = []
        if not self.getkeys('flowgraph', step, index, 'input'):
            self.collect()
        elif not self.get('remote', 'addr'):
            halt = 0
            for input_step in self.getkeys('flowgraph', step, index, 'input'):
                step_error = 1
                for i in self.get('flowgraph', step, index, 'input', input_step):
                    index_error = error[input_step + i]
                    step_error = step_error & index_error
                    self.set('flowstatus', input_step, i, 'error', index_error)
                    if not index_error:
                        cfgfile = f"../{input_step+i}/outputs/{design}.pkg.json"
                        self.cfg = self.readcfg(cfgfile)
                halt = halt + step_error
            if halt:
                self.logger.error('Halting step %s due to previous errors', step)
                self._haltstep(step, index, error, active)

        # Write configuration prior to step running into inputs/
        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)
        os.makedirs('inputs', exist_ok=True)
        self.writecfg(f'inputs/{design}.pkg.json')

        ##################
        # 4. Starting job

        self.logger.debug(f"Starting step '{step}' index '{index}'")
        start = time.time()

        self.set('arg', 'step', step, clobber=True)
        self.set('arg', 'index', index, clobber=True)

        ##################
        # 5. Run builtin function

        if self.get('flowgraph', step, index, 'function'):
            tool = 'builtin'
            func = self.get('flowgraph', step, index, 'function')
            args = self.get('flowgraph', step, index, 'args')
            inputs = self.getkeys('flowgraph', step, index, 'input')
            # Figure out which inputs to select
            if func == 'minimum':
                (score, sel_inputs) = self.minimum(*inputs)
            elif func == "maximum":
                (score, sel_inputs) = self.maximum(*inputs)
            elif func == "join":
                (score, sel_inputs) = self.join(*inputs)
            elif func == "mux":
                (score, sel_inputs) = self.mux(*inputs, args=args)
            elif func == "verify":
                (error, sel_inputs) = self.verify(*inputs, args=args)
                if error:
                    self._haltstep(step, index, error, active)
            self.set('flowstatus', step, index, 'select', sel_inputs)
        else:
            tool = self.get('flowgraph', step, index, 'tool')

        ##################
        # 6 Copy outputs from input steps

        if not self.getkeys('flowgraph', step, index,'input'):
            all_inputs = []
        elif not self.get('flowstatus', step, index, 'select'):
            all_inputs = [self.getkeys('flowgraph', step, index,'input')[0]+'0']
        else:
            all_inputs = self.get('flowstatus', step, index, 'select')
        for input_step in all_inputs:
            # Skip copying pkg.json files here, since we write the current chip
            # configuration into inputs/{design}.pkg.json earlier in _runstep.
            shutil.copytree(f"../{input_step}/outputs", 'inputs/', dirs_exist_ok=True,
                ignore=lambda dir, contents: [f'{design}.pkg.json'])

        ##################
        # 7. Run preprocess step for tool

        if tool != 'builtin':
            func = self.loadfunction(tool, "tool", "pre_process")
            if func:
                func(self)
                if self.error:
                    self.logger.error(f"Pre-processing failed for '{tool}' in step '{step}'")
                    self._haltstep(step, index, error, active)

        ##################
        # 7. Copy Reference Scripts

        if tool != 'builtin':
            if self.get('eda', tool, step, index, 'copy'):
                refdir = self.find(self.get('eda', tool, step, index, 'refdir'))
                shutil.copytree(refdir, ".", dirs_exist_ok=True)

        ##################
        # 8. Save config files required by EDA tools
        # (for tools and slurm)

        self.writecfg("sc_manifest.json")
        self.writecfg("sc_manifest.yaml")
        self.writecfg("sc_manifest.tcl", abspath=True, keeplists=True)

        ##################
        # 9. Final check() before run

        if self.check(step,index, mode='dynamic'):
            self.logger.error(f"Fatal error in check() of '{step}'! See previous errors.")
            self._haltstep(step, index, error, active)

        ##################
        # 10. Resetting metrics (so tool doesn't have to worry about defaults)
        for metric in self.getkeys('metric', 'default', 'default'):
            self.set('metric', step, index, metric, 'real', 0)

        ##################
        # 11. Check exe version

        veropt = self.get('eda', tool, step, index, 'vswitch')
        exe = self.get('eda', tool, step, index, 'exe')
        if (veropt != None) & (exe !=None):
            cmdlist = [exe, veropt]
            self.logger.info("Checking version of '%s' tool in step '%s'.", tool, step)
            version = subprocess.run(cmdlist, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            check_version = self.loadfunction(tool, 'tool', 'check_version')
            if check_version(self, version.stdout):
                self.logger.error(f"Version check failed for {tool}. Check installation]")
                self._haltstep(step, index, error, active)


        ##################
        # 12. Run executable
        if tool != 'builtin':
            cmdlist = self._makecmd(tool, step, index)
            cmdstr = ' '.join(cmdlist)
            self.logger.info("Running %s in %s", step, workdir)
            self.logger.info('%s', cmdstr)
            cmd_error = subprocess.run(cmdstr, shell=True, executable='/bin/bash')
            if cmd_error.returncode != 0:
                self.logger.warning('Command failed. See log file %s', os.path.abspath(cmdlist[-1]))
                if not self.get('eda', tool, step, index, 'continue'):
                    self._haltstep(step, index, error, active)
        else:
            #for builtins, copy selected inputs to outputs
            shutil.copytree(f"inputs", 'outputs', dirs_exist_ok=True)

        ##################
        # 13. Post process (could fail)
        post_error = 0
        if tool != 'builtin':
            func = self.loadfunction(tool, "tool", "post_process")
            if func:
                post_error = func(self)
                if post_error:
                    self.logger.error('Post-processing check failed for step %s', step)
                    self._haltstep(step, index, error, active)

        ##################
        # 14. Record successful exit
        self.set('flowstatus', step, str(index), 'error', 0)
        end = time.time()
        elapsed_time = end - start
        self.set('metric',step,index,'runtime', 'real', round(elapsed_time,2))

        start_date = datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S')
        end_date = datetime.datetime.fromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S')
        self._makerecord(step, index, start_date, end_date)
        ##################
        # 15. save a successful manifest (minus scratch args)
        self.set('arg', 'step', None, clobber=True)
        self.set('arg', 'index', None, clobber=True)

        self.writecfg("outputs/" + self.get('design') +'.pkg.json')

        ##################
        # 16. return fo original directory
        os.chdir(cwd)

        ##################
        # 17. clearing active and error bits
        # !!Do not move this code!!
        error[step + str(index)] = 0
        active[step + str(index)] = 0

    ###########################################################################
    def _haltstep(self, step, index, error, active):
        self.logger.error(f"Halting step '{step}' index '{index}' due to errors.")
        active[step + str(index)] = 0
        sys.exit(1)

    ###########################################################################
    def run(self):
        '''
        A unified thread safe per step execution method for the Chip.
        The options and modes of the run is setup up through the Chip
        dictionary. The run executes on the local machine by default, but can
        be execute remotely if a server is set up and the remote mode is set
        in the Chip dictionary. The run metho executes a pipeline of steps
        from 'start' to 'stop' (inclusive).

        Args:
            steplist: The list of steps to launch. If no list is specified
            all steps int he flowgraph are executed.

        Examples:
            >>> run()
            Runs the pipeline defined by 'steplist'
            >>> run(steplist=['route', 'dfm'])
            Runs the route and dfm steps.
        '''

        # Run steps if set, otherwise run whole graph
        if self.get('arg', 'step'):
            steplist = [self.get('arg', 'step')]
        elif self.get('steplist'):
            steplist = self.get('steplist')
        else:
            steplist = self.getsteps()

        # Hash all files before run
        if self.hash():
            self.logger.error('File hashing failed, exiting')
            sys.exit(1)

        # Remote workflow: Dispatch the Chip to a remote server for processing.
        if self.get('remote', 'addr'):
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
                    else:
                        indexlist = self.getkeys('flowgraph', step)
                    if (step in steplist) & (index in indexlist):
                        self.set('flowstatus', step, str(index), 'error', 1, clobber=False)
                        error[stepstr] = self.get('flowstatus', step, str(index), 'error')
                        active[stepstr] = 1
                        # Setting up tool is optional
                        tool = self.get('flowgraph', step, index, 'tool')
                        if tool:
                            self.set('arg','step', step)
                            self.set('arg','index', index)
                            func = self.loadfunction(tool, 'tool', 'setup_tool')
                            func(self)
                        self.check(step, index, mode='static')
                    else:
                        self.set('flowstatus', step, str(index), 'error', 0, clobber=False)
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
                    self.set('jobid', jobid + 1)
            except:
                pass

            if self.get('remote', 'key'):
                # Decrypt the job's data for processing.
                client_decrypt(self)

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
                    processes.append(multiprocessing.Process(target=self._runstep_safe,
                                                             args=(step, index, active, error,)))
            # Start all processes
            for p in processes:
                p.start()
            # Mandatory process cleanup
            for p in processes:
                p.join()

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

            # For local encrypted jobs, re-encrypt and delete the decrypted data.
            if self.get('remote', 'key'):
                client_encrypt(self)

        # Merge cfg back from last executed runstep.
        # (Only if the index-0 run's results exist.)
        laststep = steplist[-1]
        lastdir = self.getworkdir(step=laststep, index='0')
        lastcfg = f"{lastdir}/outputs/{self.get('design')}.pkg.json"
        if os.path.isfile(lastcfg):
            self.cfg = self.readcfg(lastcfg)
            self.set('flowstatus',laststep,'0', 'select', '0')

    ###########################################################################
    def show(self, filename):
        '''
        Opens a graphical viewer for the filename provided.

        The show function opens the filename specified using a viewer tool
        selected based on the file suffix and the 'showtool' schema setup.
        The 'showtool' parameter binds tools with file suffixes, enabling the
        automated dynamic loading of tool setup functions from
        siliconcompiler.tools.<tool>/tool_setup.py. Display settings and
        technology settings for viewing the file are read read from the
        in-memory chip object schema settings. All temporary render and
        display files are saved in the <build_dir>/_show directory.

        The show() command can also be used to display content from an SC
        schema .json filename provided. In this case, the SC schema is
        converted to html and displayed as a 'dashboard' in the browser.

        Filenames with .gz and .zip extensions are automatically expanded
        before being displayed.

        Args:
            filename: Name of file to display

        Examples:
            >>> show('myfile.def')
            Opens up the def file with a viewer assigneed by 'showtool'
            >>> show('myrun.json')
            Displays SC schema in browser
        '''

        self.logger.info("Showing file %s", filename)

        # Parsing filepaths
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
        if filetype == 'json':
            localcfg = self.readcfg(localfile)
            # bokeh serve selection_histogram.py
            #
            #2. Render metrics per index per step
            #3. Sphinx like tree of all settings with links to files
            #4. Resolution of all ENV_VARS for files
            pass
        elif filetype in self.getkeys('showtool'):
            # Using env variable and manifest to pass arguments
            os.environ['SC_FILENAME'] = localfile
            self.writecfg("sc_manifest.tcl", abspath=True)
            self.writecfg("sc_manifest.json", abspath=True)
            # Setting up tool
            tool = self.get('showtool', filetype)
            step = 'show'+filetype
            index = "0"
            searchdir = "siliconcompiler.tools." + tool
            modulename = '.'+tool+'_setup'
            module = importlib.import_module(modulename, package=searchdir)
            setup_tool = getattr(module, "setup_tool")
            setup_tool(self, step, index, mode='show')
            # Running command
            cmdlist = self._makecmd(tool, step, index)
            cmdstr = ' '.join(cmdlist)
            cmd_error = subprocess.run(cmdstr, shell=True, executable='/bin/bash')
        else:
            self.logger.error("Filetype '{filetype}' not set up in 'showtool' parameter.")

        # Returning to original directory
        os.chdir(cwd)
        return 0

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

        exe = self.get('eda', tool, step, index, 'exe')
        if 'cmdline' in self.getkeys('eda', tool, step, index, 'option'):
            options = self.get('eda', tool, step, index, 'option', 'cmdline')
        else:
            options = []
        scripts = []
        # Add scripts files
        for value in self.get('eda', tool, step, index, 'script'):
            abspath = self.find(value)
            scripts.append(abspath)

        cmdlist = [exe]
        logfile = exe + ".log"
        cmdlist.extend(options)
        cmdlist.extend(scripts)
        runtime_options = self.loadfunction(tool, 'tool', 'runtime_options')
        if runtime_options:
            #print(runtime_options(self))
            cmdlist.extend(runtime_options(self))
        if self.get('quiet') & (step not in self.get('bkpt')):
            cmdlist.extend([" &> ",logfile])
        else:
            # the weird construct at the end ensures that this invocation returns the
            # exit code of the command itself, rather than tee
            # (source: https://stackoverflow.com/a/18295541)
            cmdlist.extend([" 2>&1 | tee ",logfile," ; (exit ${PIPESTATUS[0]} )"])

        #create replay file
        with open('replay.sh', 'w') as f:
            print('#!/bin/bash\n', ' '.join(cmdlist), file=f)
        os.chmod("replay.sh", 0o755)

        return cmdlist

    #######################################
    def _makerecord(self, step, index, start, end):
        '''
        Records provenance details for a runstep.
        '''
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
    def getworkdir(self, step=None, index=None):
        '''Create a step directory with absolute path
        '''

        dirlist =[self.get('dir'),
                  self.get('design'),
                  self.get('jobname') + str(self.get('jobid'))]

        if step is not None:
            dirlist.append(step + index)

        return os.path.abspath("/".join(dirlist))


################################################################################
# Annoying helper classes

class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)

#class CustomFormatter(argparse.HelpFormatter(max_help_position=27),
#                      argparse.RawDescriptionHelpFormatter):
#    pass
