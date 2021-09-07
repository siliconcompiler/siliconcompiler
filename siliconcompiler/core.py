# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
import time
import datetime
import multiprocessing
import traceback
import asyncio
import subprocess
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
from siliconcompiler.schema_utils import *

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

        # Set Environment Variable if not already set
        # TODO: Better solution??
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        rootdir = re.sub('siliconcompiler/siliconcompiler',
                         'siliconcompiler',
                         scriptdir)

        # Set SCPATH to an empty string if it does not exist.
        if not 'SCPATH' in os.environ:
            os.environ['SCPATH'] = ''
        #Getting environment path (highest priority)
        scpaths = str(os.environ['SCPATH']).split(':')

        #Add the root Path
        scpaths.append(rootdir)

        # Adding current working directory if not
        # working out of rootdir
        if not re.match(str(os.getcwd()), rootdir):
            scpaths.append(os.getcwd())

        # Writing back global SCPATH
        os.environ['SCPATH'] = ':'.join(scpaths)

        #Adding scpath to python search path
        sys.path.extend(scpaths)
        self.logger.debug("SC search path %s", os.environ['SCPATH'])
        self.logger.debug("Python search path %s", sys.path)

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
            helpstr = self.get(*key, field='short_help')
            typestr = self.get(*key, field='type')
            #Switch field fully describes switch format
            switch = self.get(*key, field='switch')
            if switch is not None:
                switchmatch = re.match(r'(-[\w_]+)\s+(.*)', switch)
                gccmatch = re.match(r'(-[\w_]+)(.*)', switch)
                plusmatch = re.match(r'(\+[\w_\+]+)(.*)', switch)
                if switchmatch:
                    switchstr = switchmatch.group(1)
                    dest = re.sub('-','',switchstr)
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
                                help=self.get('source', field='short_help'))

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
        authorfile = schema_path("AUTHORS")
        f = open(authorfile, "r")
        for line in f:
            name = re.match(r'^(\w+\s+\w+)', line)
            if name:
                authors.append(name.group(1))
        print("Authors:", ", ".join(authors), "\n")
        print("-"*80)

        os.environ["COLUMNS"] = '80'

        # set design name (override default)
        if 'design' in cmdargs.keys():
            self.name = cmdargs['design']

        # set loglevel if set at command line
        if 'loglevel' in cmdargs.keys():
            self.logger.setLevel(cmdargs['loglevel'])

        # set mode (needed for target)
        if 'mode' in cmdargs.keys():
            self.set('mode', cmdargs['mode'], clobber=True)

        # read in target if set
        if 'target' in cmdargs.keys():
            self.target(cmdargs['target'])

        # read in all cfg files
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

    ###########################################################################
    def target(self, arg=None, libs=True, methodology=True):
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

        **setup_platform (chip):** Configures basic PDK information,
        including setting up wire tracks and setting filesystem pointers to
        things like spice models, runsets, design rules manual. The function
        takes the a Chip object as an input argument and uses the Chip's
        schema acess methods to set/get parameters. To maximize reuse it
        is recommended that the setup_platform function includes only core
        PDK information and does not include settings for IPs such as
        libraries or design methodology settings.

        **setup_libs (chip, vendor=None):** Configures the core digital
        library IP for a process. The vendor argument is used to select
        the vendor for foundry nodes that support multiple IP vendors.
        The function works as an abstraction layer for the designer by
        encapsulating all the low level details of the libraries such as
        filename, directory structures, and cell naming methodologies.

        **EDAFLOW:**

        **setup_flow (platform):** Configures the edaflow by setting
        up the steps of the execution flow (eg. 'flowgraph') and
        binding each step to an EDA tool. The tools are dynamically
        loaded in the 'runstep' method based on the step tool selected.
        The platform argument can be used setup_flow function to
        make selections based on specific platforms.

        Args:
            arg (string): Name of target to load. If None, the target is
                read from the SC schema.
            libs (bool): If True, the setup_libs function is executed
                from the technology target module.
            methodology (bool): If True, the setup_methodology is executd
                from the technology target module.

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
            self.logger.error('Target should have zero or one underscore.')
            sys.exit(1)

        # Technology platform
        platform = self.get('target').split('_')[0]
        if self.get('mode') == 'asic':
            try:
                searchdir = 'siliconcompiler.foundries'
                module = importlib.import_module('.'+platform, package=searchdir)
                setup_platform = getattr(module, "setup_platform")
                setup_platform(self)
                if libs:
                    setup_libs = getattr(module, "setup_libs")
                    setup_libs(self)
                if methodology:
                    setup_methodology = getattr(module, "setup_methodology")
                    setup_methodology(self)
                self.logger.info("Loaded platform '%s'", platform)
            except ModuleNotFoundError:
                self.logger.critical("Platform %s not found.", platform)
                sys.exit(1)
        else:
            self.set('fpga', 'partname', platform)


        # EDA flow
        if len(self.get('target').split('_')) == 2:
            edaflow = self.get('target').split('_')[1]
            try:
                searchdir = 'siliconcompiler.flows'
                module = importlib.import_module('.'+edaflow, package=searchdir)
                setup_flow = getattr(module, "setup_flow")
                setup_flow(self, platform)
                self.logger.info("Loaded edaflow '%s'", edaflow)
            except ModuleNotFoundError:
                self.logger.critical("EDA flow %s not found.", edaflow)
                sys.exit(1)

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
        description = self.get(*args, field='short_help')
        typestr = str(self.get(*args, field='type'))
        defstr = str(self.get(*args, field='defvalue'))
        requirement = self.get(*args, field='requirement')
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
                   "\nDescription: " + description.lstrip() +
                   "\nOrder:       " + param.lstrip() +
                   "\nType:        " + typestr.lstrip()  +
                   "\nRequirement: " + requirement.lstrip()   +
                   "\nDefault:     " + defstr.lstrip()   +
                   "\nExamples:    " + example[0].lstrip() +
                   "\n             " + example[1].lstrip() +
                   "\nHelp:        " + para_list[0].lstrip() + "\n")
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
    def set(self, *args, cfg=None, clobber=True):
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
        return self._search(cfg, keypath, *all_args, field='value', mode='set', clobber=clobber)

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

        # Return early if setting a value to 'None'. The reason for this is that
        # str(None) == 'None', not None. So when we call .add or .set with None
        # as a value, it gets saved in the dictionary as a string, causing bugs.
        if (mode in ('set', 'add')) and (val is None):
            return
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
                if (mode == 'set'):
                    if (selval in empty) | clobber:
                        if (not list_type) & (not isinstance(val, list)):
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
        defvalue, switch, requirment, type, lock, param_help, short_help,
        example, and help. In addition, extensions for file/dir types must
        include fields for lock, copy, filehash, data, and signature. For
        complete information about these fields, refer to the schema.py

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
    def prune(self, cfg, top=True):
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
        empty = ("null",None,[])

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
                    self.prune(cfg=localcfg[k], top=False)
            if top:
                i += 1
            else:
                break

        return localcfg

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
                                cfg[k]['value'][i] = schema_path(val)
                        else:
                            cfg[k]['value'] = schema_path(cfg[k]['value'])
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
    def merge(self, cfg1, cfg2, append=False, path=None):
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
            path (sring): Temporary variable tracking key path

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
        legal_steps.append('source')
        for item in self.getkeys('flowgraph'):
            for step_in in self.get('flowgraph', item, 'input'):
                if step_in not in legal_steps:
                    self.error = 1
                    self.logger.error(f"Input '{item}' is not a legal step.")
        #2. Check requirements list
        emptylist = ("null", None, [])
        allkeys = self.getkeys()
        for key in allkeys:
            keypath = ",".join(key)
            if 'default' not in key:
                requirement = self.get(*key, cfg=cfg, field='requirement')
                value = self.get(*key, cfg=cfg)
                defvalue = self.get(*key, cfg=cfg, field='defvalue')
                value_empty = (defvalue in emptylist) & (value in emptylist)
                if value_empty & (str(requirement) == 'all'):
                    self.error = 1
                    self.logger.error(f"Global requirement missing for [{keypath}].")
                elif value_empty & (str(requirement) == self.get('mode')):
                    self.error = 1
                    self.logger.error(f"Mode requirement missing for [{keypath}].")
        #3. Check per tool parameter requirements
        tool = self.get('flowgraph', step, 'tool')

        if 'req' in  self.getkeys('eda', tool, step, index):
            all_required = self.get('eda', tool, step, index, 'req')
            for item in all_required:
                keypath = item.split(',')
                if not self.get(*keypath):
                    self.error = 1
                    self.logger.error(f"Value empty for [{keypath}].")
        #4. Check that input files exist
        if mode=='dynamic':
            #2. Check per step input requirements
            all_inputs = self.get('eda', tool, step, index, 'input')
            for item in all_inputs:
                infile = f"inputs/{item}"
                if not os.path.isfile(infile):
                    self.error = 1
                    self.logger.error(f"Required input '{infile}' is missing.")

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
    def writecfg(self, filename, cfg=None, prune=True, abspath=False):
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
            cfgcopy = self.prune(cfg)
        else:
            cfgcopy = copy.deepcopy(cfg)

        #resolve absolute paths
        if abspath:
            self._abspath(cfgcopy)

        # Write out configuration based on file type
        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                print(json.dumps(cfgcopy, indent=4, sort_keys=True), file=f)
        elif filepath.endswith('.yaml'):
            with open(filepath, 'w') as f:
                print(yaml.dump(cfgcopy, Dumper=YamlIndentDumper, default_flow_style=False), file=f)
        elif filepath.endswith('.tcl'):
            with open(filepath, 'w') as f:
                print("#############################################", file=f)
                print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
                print("#############################################", file=f)
                self._printcfg(cfgcopy, mode="tcl", prefix="dict set sc_cfg", file=f)
        else:
            self.logger.error('File format not recognized %s', filepath)
            self.error = 1

    ###########################################################################
    def writegraph(self, graph, filename):
        '''Exports the execution flow graph using the graphviz library.
        For graphviz formats supported, see https://graphviz.org/.

        '''
        filepath = os.path.abspath(filename)
        self.logger.debug('Writing flowgraph to file %s', filepath)
        fileroot, ext = os.path.splitext(filepath)
        fileformat = ext.replace(".", "")
        dot = graphviz.Digraph(format=fileformat)
        dot.attr(bgcolor='transparent')
        if graph == 'flowgraph':
            for step in self.getkeys('flowgraph'):
                if self.get('flowgraph', step, 'tool'):
                    labelname = step+'\\n('+self.get('flowgraph', step, 'tool')+")"
                else:
                    labelname = step
                dot.node(step, label=labelname)
                for prev_step in self.get('flowgraph', step, 'input'):
                    dot.edge(prev_step, step)
        elif graph == 'hier':
            for parent in self.getkeys('hier'):
                dot.node(parent)
                for child in self.getkeys('hier', parent):
                    dot.edge(parent, child)
        dot.render(filename=fileroot, cleanup=True)


    ########################################################################
    def collect(self, cfg=None, outdir='output'):
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

        if not os.path.exists(outdir):
            os.makedirs(outdir)

        #copy all parameter take from self dictionary
        copyall = self.get('copyall')
        allkeys = self.getkeys(cfg=cfg)
        for key in allkeys:
            leaftype = self.get(*key, cfg=cfg, field='type')
            if leaftype == 'file':
                copy = self.get(*key, cfg=cfg, field='copy')
                value = self.get(*key, cfg=cfg, field='value')
                if copyall | (copy == 'true'):
                    if not isinstance(value, list):
                        value = [value]
                    for item in value:
                        if item:
                            filepath = schema_path(item)
                            shutil.copy(filepath, outdir)

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
                    filename = schema_path(item)
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
        '''Calculates the die yield
        '''

        d0 = self.get('pdk', 'd0')
        diesize = self.get('asic', 'diesize').split()
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
        '''Calculates dies per wafer, taking into account scribe lines
        and wafer edge margin. The algorithms starts with a center aligned
        wafer and rasters dies uot from the center until a die edge extends
        beyoond the legal value.

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
    def summary(self, filename=None):
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
        else:
            # TODO: pull in relevant summary items for FPGA?
            info = '\n'.join(["SUMMARY:\n",
                              "design = "+self.get('design'),
                              "jobdir = "+ jobdir])

        print("-"*135)
        print(info, "\n")

        #print(json.dumps(self.cfg, indent=4, sort_keys=True))

        # Stepping through all steps/indices and printing out metrics
        data = []
        steps = []
        colwidth = 8

        #Creating Header
        steps = []
        colwidth = 8
        for step in steplist:
            index = self.get('flowstatus', step, 'select')
            stepstr = step + str(index)
            steps.append(stepstr.center(colwidth))

        #Creating table of real values
        metrics = []
        for metric in self.getkeys('metric', 'default', 'default'):
            metrics.append(" " + metric)
            row = []
            for step in steplist:
                index = self.get('flowstatus', step, 'select')
                value = str(self.get('metric', step, str(index), metric, 'real'))
                row.append(" " + value.center(colwidth))
            data.append(row)

        pandas.set_option('display.max_rows', 500)
        pandas.set_option('display.max_columns', 500)
        pandas.set_option('display.width', 100)
        df = pandas.DataFrame(data, metrics, steps)
        if filename is None:
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
            for path in self._allpaths(cfg, step):
                if len(list(path)) > depth[step]:
                    depth[step] = len(path)

        #Sort steps based on path lenghts
        sorted_dict = dict(sorted(depth.items(), key=lambda depth: depth[1]))
        return list(sorted_dict.keys())

    ###########################################################################
    def _allpaths(self, cfg, node, path=None, allpaths=None):

        if path is None:
            allpaths = []
            path = []
        if 'source' in self.get('flowgraph', node, 'input', cfg=cfg):
            allpaths.append(path)
        else:
            for nextnode in self.get('flowgraph', node, 'input', cfg=cfg):
                newpath = path.copy()
                newpath.append(nextnode)
                return self._allpaths(cfg, nextnode, path=newpath, allpaths=allpaths)
        return list(allpaths)

    ###########################################################################
    def minimum(self, step):
        '''
        Returns the index with the 'min' score for a step. The algorithm for
        minimum selection is as follows.
        0. Tag indices as meeting or not meeting all requirements
        1. A max/min value is computed for a metric category across all indices
        2. Metrics are normalized as (metric - min)/(max - min)
        3. An index score is the sum of all normalized metric scores
        4. The index with the lowest score wins

        '''

        self.logger.debug(f"Finding optimal index for step '{step}'")

        # Checking goals for each metric
        index_failed = {}
        goals_met = False
        for i in range(self.get('flowgraph', step, 'nproc')):
            if self.get('flowstatus', step, str(i), 'error'):
                index_failed[i] = True
            else:
                index_failed[i] = False
                for metric in self.getkeys('metric', step, str(i)):
                    if 'goal' in self.getkeys('metric', step, str(i), metric):
                        goal = self.get('metric', step, str(i), metric, 'goal')
                        real = self.get('metric', step, str(i), metric, 'real')
                        if bool(real > goal):
                            index_failed[i] = True
            if not index_failed[i]:
                goals_met = True

        # Calculate max/min values for each metric
        max_val = {}
        min_val = {}
        for metric in self.getkeys('flowgraph', step, 'weight'):
            max_val[metric] = 0
            min_val[metric] = float("inf")
            for i in range(self.get('flowgraph', step, 'nproc')):
                if not self.get('flowstatus', step, str(i), 'error'):
                    real = self.get('metric', step, str(i), metric, 'real')
                    max_val[metric] = max(max_val[metric], real)
                    min_val[metric] = min(min_val[metric], real)

        # Select the minimum score
        min_score = float("inf")
        winner = 0
        goals_met = False
        for i in range(self.get('flowgraph', step, 'nproc')):
            if not self.get('flowstatus', step, str(i), 'error'):
                score = 0.0
                for metric in self.getkeys('flowgraph', step, 'weight'):
                    real = self.get('metric', step, str(i), metric, 'real')
                    if not (max_val[metric] - min_val[metric]) == 0:
                        scaled = (real - min_val[metric]) / (max_val[metric] - min_val[metric])
                    else:
                        scaled = max_val[metric]
                    score = score + scaled
                if (score < min_score) & (not(index_failed[i] & goals_met)):
                    min_score = score
                    winner = i

        return winner

    ###########################################################################
    def _runstep(self, step, index, active, error):
        '''
        Private per step run method called by run().
        The method takes in a step string and index string to indicated what
        to run. Execution state coordinated through the active/error
        multiprocessing Manager dicts.

        Execution flow:
        1. Wait in loop until all previous steps/indexes have completed
        2. Check inputs for errors. Halt if one of the steps yielded
           zero valid results
        3. Create local working directory
        4. Merge in results input steps (all indices).
        5. Select winning index and set flowstatus
        6. Check the execution version
        8. Copy script/refdir to local dir
        9. Construct command line
        10. Set step/index parameters
        11. Write out files
        12. Runtime check to make sure all inputs are present.
        13. Run EXE
        14. Post process
        15. Write out json file in output
        16. Change dir
        17. Lower active bit

        '''

        self.logger.info(f"Step '{step}' waiting on inputs")
        while True:
            # Checking that there are no pending jobs
            pending = 0
            for input_step in self.get('flowgraph', step, 'input'):
                if input_step != 'source':
                    for input_index in range(self.get('flowgraph', input_step, 'nproc')):
                        input_str = input_step + str(input_index)
                        pending = pending + active[input_str]

            # beak out of loop when no all inputs are done
            if not pending:
                break
            # Short sleep
            time.sleep(0.1)

        # Starting Date/Time
        start = time.time()

        # Build directory
        stepdir = "/".join([self.get('dir'),
                            self.get('design'),
                            self.get('jobname') + str(self.get('jobid')),
                            step + index])

        self.logger.debug(f"Stepdir={stepdir}")

        stepdir = os.path.abspath(stepdir)

        # Directory manipulation
        cwd = os.getcwd()
        if os.path.isdir(stepdir) and (not self.get('remote', 'addr')):
            shutil.rmtree(stepdir)
        os.makedirs(stepdir, exist_ok=True)
        os.chdir(stepdir)
        os.makedirs('outputs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        # Collect source files for first step
        design = self.get('design')
        if 'source' in self.get('flowgraph', step, 'input'):
            self.collect(outdir='inputs')
        elif not self.get('remote', 'addr'):
            # Select inputs from previous steps
            for input_step in self.get('flowgraph', step, 'input'):
                # merge in all previous data
                for input_index in range(self.get('flowgraph', input_step, 'nproc')):
                    cfgfile = f"../{input_step}{input_index}/outputs/{design}.pkg.json"
                    if os.path.isfile(cfgfile):
                        self.cfg = self.readcfg(cfgfile)

        #Checking that there were no errors in previous steps
        halt = 0
        for input_step in self.get('flowgraph', step, 'input'):
            if input_step != 'source':
                step_error = 1
                for input_index in range(self.get('flowgraph', input_step, 'nproc')):
                    input_str = input_step + str(input_index)
                    index_error = error[input_str]
                    self.set('flowstatus', input_step, str(input_index), 'error', index_error)
                    step_error = step_error & index_error
                halt = halt + step_error
        if halt:
            self.logger.error('Halting step %s due to previous errors', step)
            self._haltstep(step, index, error, active)

        # starting actual step execution
        self.logger.debug(f"Starting step '{step}'")

        # calculate the minimum index based on index data below
        for input_step in self.get('flowgraph', step, 'input'):
            if input_step != 'source':
                min_index = self.minimum(input_step)
                self.logger.info(f"Step '{step}' selected index '{min_index}' from '{input_step}'.")
                self.set('flowstatus', input_step, 'select', str(min_index), clobber=True)
                # copy files
                shutil.copytree(f"../{input_step}{min_index}/outputs", 'inputs/')

        # Check Version if switch exists
        #if self.getkeys('eda', tool, step, str(index), 'vswitch'):
        tool = self.get('flowgraph', step, 'tool')
        exe = self.get('eda', tool, step, index, 'exe')
        veropt =self.get('eda', tool, step, index, 'vswitch')
        if veropt!=None:
            cmdstr = f'{exe} {veropt} > {exe}.log'
            self.logger.debug("Checking version of '%s' tool in step '%s'.", tool, step)
            exepath = subprocess.run(cmdstr, shell=True)
            if exepath.returncode > 0:
                self.logger.error('Version check failed for %s.', cmdstr)
                self._haltstep(step, index, error, active)
        else:
            self.logger.info("Skipping version checking of '%s' tool in step '%s'.", tool, step)

        # Exe version logic
        # TODO: add check

        #Copy Reference Scripts
        if self.get('eda', tool, step, index, 'copy'):
            refdir = schema_path(self.get('eda', tool, step, index, 'refdir'))
            shutil.copytree(refdir, ".", dirs_exist_ok=True)

        # If it exists, run pre_process in stepdir
        try:
            tool = self.get('flowgraph', step, 'tool')
            searchdir = "siliconcompiler.tools." + tool
            modulename = '.'+tool+'_setup'
            module = importlib.import_module(modulename, package=searchdir)
            if hasattr(module, "pre_process"):
                pre_process = getattr(module, "pre_process")
                pre_process(self, step, index)
        except:
            traceback.print_exc()
            self.logger.error(f"Pre-processing failed for '{tool}' in step '{step}'")
            self._haltstep(step, index, error, active)

        # Create a run commmand
        cmdlist = self._makecmd(tool, step, index)
        cmdstr = ' '.join(cmdlist)

        # Save config files required by EDA tools
        self.set('arg', 'step', step, clobber=True)
        self.set('arg', 'index', index, clobber=True)

        # Writing out command file
        self.writecfg("sc_manifest.json")
        self.writecfg("sc_manifest.yaml")
        self.writecfg("sc_manifest.tcl", abspath=True)

        # Resetting metrics
        for metric in self.getkeys('metric', 'default', 'default'):
            self.set('metric', step, index, metric, 'real', 0)

        # Final check() before run
        if self.check(step,index, mode='dynamic'):
            self.logger.error(f"Fatal error in check() of '{step}'! See previous errors.")
            self._haltstep(step, index, error, active)

        # Run executable
        self.logger.info("Running %s in %s", step, stepdir)
        self.logger.info('%s', cmdstr)
        cmd_error = subprocess.run(cmdstr, shell=True, executable='/bin/bash')
        if cmd_error.returncode != 0:
            self.logger.warning('Command failed. See log file %s', os.path.abspath(cmdlist[-1]))
            self._haltstep(step, index, error, active)
            # Override exit code if set
            if not self.get('eda', tool, step, index, 'continue'):
                self._haltstep(step, index, error, active)

        # Post process (could fail)
        try:
            tool = self.get('flowgraph', step, 'tool')
            searchdir = "siliconcompiler.tools." + tool
            modulename = '.'+tool+'_setup'
            module = importlib.import_module(modulename, package=searchdir)
            post_process = getattr(module, "post_process")
            post_error = post_process(self, step, index)
        except:
            traceback.print_exc()
            self.logger.error(f"Post-processing failed for '{tool}' in step '{step}'")
            self._haltstep(step, index, error, active)

        # Check for non exception post_error
        if post_error:
            self.logger.error('Post-processing check failed for step %s', step)
            self._haltstep(step, index, error, active)

        # clean run completed
        self.set('flowstatus', step, str(index), 'error', 0)
        end = time.time()
        elapsed_time = end - start
        self.set('metric',step,index,'runtime', 'real', round(elapsed_time,2))


        # record runstep provenance data
        start_date = datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d %H:%M:%S')
        end_date = datetime.datetime.fromtimestamp(end).strftime('%Y-%m-%d %H:%M:%S')
        self._makerecord(step, index, start_date, end_date)

        # save a successful manifest
        self.writecfg("outputs/" + self.get('design') +'.pkg.json')

        # return fo original directory
        os.chdir(cwd)

        # clearing active and error bits for multi-processing
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
        if self.get('steplist'):
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
                for index in range(self.get('flowgraph', step, 'nproc')):
                    self.set('flowstatus', step, str(index), 'error', 1)
                    stepstr = step + str(index)
                    if step in steplist:
                        #setting step to active
                        active[stepstr] = 1
                        error[stepstr] = 1
                        # Load module (could fail)
                        try:
                            tool = self.get('flowgraph', step, 'tool')
                            searchdir = "siliconcompiler.tools." + tool
                            modulename = '.'+tool+'_setup'
                            self.logger.info(f"Setting up tool '{tool}' in step '{step}'")
                            module = importlib.import_module(modulename, package=searchdir)
                            setup_tool = getattr(module, "setup_tool")
                            setup_tool(self, step, str(index))
                        except:
                            traceback.print_exc()
                            self.logger.error(f"Setup failed for '{tool}' in step '{step}'")
                            self.error = 1
                        #run check for step, index
                        self.check(step,str(index),mode='static')
                    else:
                        error[stepstr] = 0
                        active[stepstr] = 0

            # Implement auto-update of jobincrement
            dirname = self.get('dir')
            design = self.get('design')
            jobname = self.get('jobname')
            try:
                alljobs = os.listdir(dirname + "/" + design)
                if self.get('jobincr'):
                    jobid = 0
                    for item in alljobs:
                        m = re.match(jobname+r'(\d+)', item)
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
                for index in range(self.get('flowgraph', step, 'nproc')):
                    processes.append(multiprocessing.Process(target=self._runstep,
                                                             args=(step, str(index), active, error,)))
            # Start all processes
            for p in processes:
                p.start()
            # Mandatory process cleanup
            for p in processes:
                p.join()

            # Make a clean exit if one of the steps failed
            halt = 0
            for step in self.getkeys('flowgraph'):
                index_error = 1
                for index in range(self.get('flowgraph', step, 'nproc')):
                    stepstr = step + str(index)
                    index_error = index_error & error[stepstr]
                halt = halt + index_error
            if halt:
                self.logger.error('Run() failed, exiting! See previous errors.')
                sys.exit(1)

            # For local encrypted jobs, re-encrypt and delete the decrypted data.
            if self.get('remote', 'key'):
                client_encrypt(self)

        # Merge cfg back from last executed step
        # last step must have nproc = 1
        laststep = steplist[-1]
        lastdir = "/".join([self.get('dir'),
                            self.get('design'),
                            self.get('jobname') + str(self.get('jobid')),
                            laststep + str(0)])

        self.cfg = self.readcfg(f"{lastdir}/outputs/{self.get('design')}.pkg.json")
        self.set('flowstatus',laststep,'select',0)

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
                    else:
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
        options = self.get('eda', tool, step, index, 'option', 'cmdline')
        scripts = []
        for value in self.get('eda', tool, step, index, 'script'):
            abspath = schema_path(value)
            scripts.append(abspath)

        cmdlist = [exe]
        logfile = exe + ".log"
        cmdlist.extend(options)
        cmdlist.extend(scripts)
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
            elif self.get(key):
                self.set('record', step, index, key, self.get(key))
            else:
                self.logger.debug(f"Record ignored for {key}, parameter not set up")

################################################################################
# Annoying helper classes

class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)

#class CustomFormatter(argparse.HelpFormatter(max_help_position=27),
#                      argparse.RawDescriptionHelpFormatter):
#    pass
