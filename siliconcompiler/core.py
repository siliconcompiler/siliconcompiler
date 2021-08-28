# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
import time
import multiprocessing
import traceback
import asyncio
import subprocess
import os
import sys
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

from siliconcompiler.client import *
from siliconcompiler.schema import *
from siliconcompiler.schema_utils import *

class Chip:
    """
    Core Siliconcompiler Class

    This is the main object used to interact with configuration, data, and
    execution flow for the SiliconCompiler API.

    Args:
        design (string): Name of the top level chip design object.
        loglevel (string): Level of logging for the chip object. Valid
            levels are "DEBUG", "INFO", "WARNING", "ERROR".
        defaults (bool)": If True, schema dictionary values are loaded with
            default values, else they are left as empty lists/None.

    Examples:
        >>> siliconcompiler.Chip(design="top", loglevel="DEBUG")
        Creates a chip object with name "top" and sets loglevel to "DEBUG".
    """

    ###########################################################################
    def __init__(self, design="root", loglevel="INFO"):
        """Initializes Chip object
        """

        # Local variables
        self.version = "0.0.1"
        self.design = design
        self.status = {}
        self.error = 0
        self.cfg = schema_cfg()

        # Setting design variable
        self.cfg['design']['value'] = self.design
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
        """Command line interface method for the SiliconCompiler project.

        The method exposes parameters in the SC schema as command line switches.
        Exact format for all command line switches can be found in the example
        and help fields of the schema parameters within the 'schema.py' module.
        Custom command line apps can be created by restricting the schema
        parameters exposed at the command line. The priority of command line
        switch settings is:

         1. design
         2. loglevel
         3. mode (asic/fpga)
         4. target
         5. cfg
         6. (all others)

        The cmdline interface is implemented using the Python
        argparse package and the following use restrictions apply.

        * Help is accessed with the '-h' switch
        * Arguments that include spaces must be enclosed with double quotes.
        * List parameters are entered indidually (ie. -y libdir1 -y libdir2)
        * For parameters with boolean types, the switch implies "true".
        * Special characters (such as '-') must be enclosed in double quotes.
        * Compiler comptaible switces include: -D, -I, -O{0,1,2,3}
        * Some Vrilog legacy switches: +libext+, +incdir+

        Args:
            progname (string): Name of program to be exeucted at the command
                 line. The default program name is 'sc'.
            description (string): Header help function to be displayed
                 by the command line program. By default a short
                 description of the main sc program is displayed.
            switchlist (list): List of SC parameter switches to expose
                 at the command line. By default all SC scema switches
                 are available. The switchlist entries should ommit
                 the '-'. To include a non-switch source file,
                 use 'source' as the switch.

        Examples:
            >>> cmdline(prog='sc-show', paramlist=['source', 'cfg'])
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
            self.set('mode', cmdargs['mode'])

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
        part of the target string. For ASIC flows, the target is used to
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
        library IP for the process. The vendor argument is used to select
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
            >>> target("freepdk45_asicflow")
            Loads the 'freepdk45' and 'asicflow' settings.
            >>> target()
            Loads target settings based on self.get('target')

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
        Returns a formatted help string based on the key-sequence provided.

        Args:
            *args(string): A variable length argument list specifying the
                key sequence for accessing the cfg nested dictionary.
                For a complete description of the valid key sequence,
                see the schema.py module.

        Returns:
            A formatted multi-line help string.

        Examples:
            >>> import siliconcompiler as sc
            >>> chip = sc.Chip()
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
    def get(self, *args, chip=None, cfg=None, field='value'):
        """
        Returns a Chip dictionary value based on key-sequence provided.

        Accesses to non-existing dictionary entries results in a logger error
        and in the setting the 'chip.error' flag to 1.  In the case of int and
        float types, the string value stored in the dictionary are cast
        to the appropriate type base don the dictionary 'type' field.
        In the case of boolean values, a string value of "true" returns True,
        all other values return False.

        Args:
            args(string): A variable length argument list specifying the
                key sequence for accessing the cfg nested dictionary.
                For a complete description of the valid key sequence,
                see the schema.py module.
            chip(object): A valid Chip object to use for cfg query.
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

        if chip is None:
            chip = self

        if cfg is None:
            cfg = chip.cfg

        keypath = ','.join(args)
        if(field != 'value'):
            fieldstr = "Field = " + field
        else:
            fieldstr = ""
        chip.logger.debug(f"Reading from [{keypath}]. Field = '{field}'")

        return self._search(chip, cfg, keypath, *args, field=field, mode='get')

    ###########################################################################
    def getkeys(self, *args, chip=None, cfg=None):
        """
        Returns keys from Chip dictionary based on key-sequence provided.

        Accesses to non-existing dictionary entries results in a logger error
        and in the setting the 'chip.error' flag to 1.

        Args:
            args(string): A variable length argument list specifying the
                key sequence for accessing the cfg nested dictionary.
                For a complete description of he valid key sequence,
                see the schema.py module. If the argument list is empty, all
                dictionary trees are returned as as a list of lists.
            chip (object): A valid Chip object to use for cfg query.
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

        if chip is None:
            chip = self

        if cfg is None:
            cfg = chip.cfg

        if len(list(args)) > 0:
            keypath = ','.join(args[:-1])
            chip.logger.debug('Getting schema parameter keys for: %s', args)
            keys = list(self._search(chip, cfg, keypath, *args, mode='getkeys'))
            if 'default' in keys:
                keys.remove('default')
        else:
            self.logger.debug('Getting all schema parameter keys.')
            keys = list(self._allkeys(chip, cfg))

        return keys

    ###########################################################################
    def set(self, *args, chip=None, cfg=None, clobber=False):
        '''
        Sets a Chip dictionary value based on key-sequence and data provided.

        Accesses to non-existing dictionary entries results in a logger
        error and in the setting the 'chip.error' flag to 1. For built in
        dictionary keys with the 'default' keywork entry, new leaf trees
        are automatically created by the set method by copying the default
        tree to the tree described by the key-sequence as needed.

        The data type provided must agree with the dictionary parameter 'type'.
        Before setting the parameter, the data value is type checked.
        Any type descrepancy results in a logger error and in setting the
        chip.error flag to 1. For descriptions of the legal values for a
        specific parameter, refer to the schema.py documentation. Legal values
        are cast to strings before writing to the dictionary.

        Args:
            args (string): A variable length key list used to look
                up a Chip dictionary entry. For a complete description of the
                valid key lists, see the schema.py module. The key-tree is
                supplied in order.
            chip (object): A valid Chip object to use for cfg query.
            cfg (dict): A dictionary within the Chip object to use for
                key list query.

        Examples:
            >>> set('source', 'mydesign.v')
            Sets the file 'mydesign.v' to the list of sources.
        '''

        if chip is None:
            chip = self
        if cfg is None:
            cfg = chip.cfg

        keypath = ','.join(args[:-1])

        chip.logger.debug(f"Setting [{keypath}] to {args[-1]}")

        all_args = list(args)

        # Convert val to list if not a list
        return self._search(chip, cfg, keypath, *all_args, field='value', mode='set', clobber=clobber)

    ###########################################################################
    def add(self, *args, chip=None, cfg=None):
        '''
        Appends a Chip dictionary value based on key-sequence and data provided.

        Access to non-existing dictionary entries results in a logger error
        and in the setting the 'chip.error' flag to 1. For built in dictionary
        keys with the 'default' keywork entry, new leaf trees are automatically
        created by copying the default tree to the tree described by the
        key-sequence as needed.

        The data type provided must agree with the dictionary parameter
        'type'. Before setting the parameter, the data value is type
        checked. Any type descrepancy results in a logger error and in setting
        the chip.error flag to 1. For descriptions of the legal values for a
        specific parameter, refer to the schema.py documentation.

        The add operation is not legal for scalar types.

        Args:
            args (string): A variable length key list used to look
                up a Chip dictionary entry. For a complete description of the
                valid key lists, see the schema.py module. The key-tree is
                supplied in order.
            chip (object): A valid Chip object to use for cfg query.
            cfg (dict): A dictionary within the Chip object to use for
                key list query.

        Examples:
            >>> add('source', 'mydesign.v')
            Sets the file 'mydesign.v' to the list of sources.
        '''

        if chip is None:
            chip = self
        if cfg is None:
            cfg = chip.cfg

        keypath = ','.join(args[:-1])

        chip.logger.debug('Appending value in config dictionary. Keypath = [%s] Value =%s',
                          keypath,
                          args[-1])


        all_args = list(args)

        return self._search(chip, cfg, keypath, *all_args, field='value', mode='add')

    ###########################################################################
    def _allkeys(self, chip, cfg, keys=None, allkeys=None):
        '''
        Internal recursive function that returns list of all key-lists for
        leaf cells in the dictionary defined by schema.py.
        '''

        if keys is None:
            allkeys = []
            keys = []
        for k in cfg:
            newkeys = keys.copy()
            newkeys.append(k)
            if 'defvalue' in cfg[k]:
                allkeys.append(newkeys)
            else:
                self._allkeys(chip, cfg[k], keys=newkeys, allkeys=allkeys)
        return allkeys

    ###########################################################################
    def _search(self, chip, cfg, keypath, *args, field='value', mode='get', clobber=True):
        '''
        Internal recursive function that searches a Chip dictionary for a
        match to the combination of *args and fields supplied. The function is
        used to set and get data within the dictionary.

        Args:
            args (string): A variable length key list used to look
                up a Chip dictionary entry.
            chip(object): The Chip object to extend
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
                chip.logger.error(f"Keypath [{keypath}] does not exist.")
                chip.error = 1
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
                    chip.logger.error(f"Field '{field}' for keypath [{keypath}]' is not a valid field.")
                    chip.error = 1
                # check legality of value
                if not schema_typecheck(chip, cfg[param], param, val):
                    chip.error = 1
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
                            chip.logger.error(f"Illegal list assignment to scalar for [{keypath}]")
                            chip.error = 1
                    else:
                        chip.logger.warning(f"Ignore set to [{keypath}], value already set. Use clobber option to override.")
                elif (mode == 'add'):
                    if list_type & (not isinstance(val, list)):
                        cfg[param][field].append(str(val))
                    elif list_type & isinstance(val, list):
                        cfg[param][field].extend(val)
                    else:
                        chip.logger.error(f"Illegal use of add() for scalar parameter [{keypath}].")
                        chip.error = 1
                return cfg[param][field]
        #get leaf cell (all_args=param)
        elif len(all_args) == 1:
            if not param in cfg:
                chip.logger.error(f"Keypath [{keypath}] does not exist.")
                chip.error = 1
            elif mode == 'getkeys':
                return cfg[param].keys()
            else:
                if not (field in cfg[param]) and (field!='value'):
                    chip.logger.error(f"Field '{field}' not found for keypath [{keypath}]")
                    chip.error = 1
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
                            scalar = int(selval)
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
            return self._search(chip, cfg[param], keypath, *all_args, field=field, mode=mode, clobber=clobber)


    ###########################################################################
    def extend(self, filename, chip=None, cfg=None):
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
            chip(object): The Chip object to extend
            cfg(dict): The cfg dictionary within the Chip object to extend

        """

        if chip is None:
            chip = self
        if cfg is None:
            cfg = chip.cfg

        abspath = os.path.abspath(filename)

        chip.logger.info('Extending SC schema with file %s', abspath)

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
    def prune(self, cfg, chip=None, top=True):
        '''
        Recursive function that takes a copy of the Chip dictionary and
        then removes all sub trees with non-set values and sub-trees
        that contain a 'default' key.


        Returns the prunted dictionary

        '''

        # enables pruning objects from other objects (hierarchy)
        if chip is None:
            chip = self

        # create a local copy of dict
        if top:
            localcfg = copy.deepcopy(chip.cfg)
        else:
            localcfg = cfg

        #10 should be enough for anyone...
        maxdepth = 10
        i = 0


        #Prune when the default & value are set to the following
        empty = ("null",None,[])

        #When at top of tree loop maxdepth times to make sure all stale
        #branches have been removed, not elegant, but stupid-simple
        #"good enough"
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
                    self.prune(cfg=localcfg[k], chip=chip, top=False)
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
    def merge(self, cfg1, cfg2, path=None):
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
                if re.match(r'\[', typestr):
                    self.add(*arg, cfg=localcfg)
                else:
                    self.set(*arg, cfg=localcfg)

        #returning dict
        return localcfg

    ###########################################################################
    def check(self, step, chip=None, cfg=None):
        '''
        Performs a setup validity check and returns success status.

        Returns:
            Returns True of if the Chip dictionary is valid, else returns
            False.

        Examples:
            >>> check()
           Returns True of the Chip dictionary checks out.
        '''

        if chip is None:
            chip = self
        if cfg is None:
            cfg = chip.cfg

        chip.logger.info("Running check() for step '%s'", step)
        emptylist = ("null",None,[])

        # Checking global requirements specified in schema.py
        allkeys = self.getkeys()
        for key in allkeys:
            keypath = ",".join(key)
            if 'default' not in key:
                requirement = self.get(*key, chip=chip, cfg=cfg, field='requirement')
                value = self.get(*key, chip=chip, cfg=cfg)
                defvalue = self.get(*key, chip=chip, cfg=cfg, field='defvalue')
                value_empty = (defvalue in emptylist) & (value in emptylist)
                if value_empty & (str(requirement) == 'all'):
                    chip.error = 1
                    chip.logger.error(f"Global requirement missing for [{keypath}].")
                elif value_empty & (str(requirement) == self.get('mode')):
                    chip.error = 1
                    chip.logger.error(f"Mode requirement missing for [{keypath}].")

        # Checking flowgraph setup

        # Checking setup of each tool

        # Checking mode based settings

        # Runtime check of inputs being ready

        return self.error

    ###########################################################################
    def readcfg(self, filename, merge=True, chip=None, cfg=None):
        """
        Reads a json or yaml formatted file into the Chip dictionary.

        Args:
            filename (file): A relative or absolute path toe a file to load
                into dictionary.

        Examples:
            >>> readcfg('mychip.json')
            Loads the file mychip.json into the current Chip dictionary.
        """

        if chip is None:
            chip = self
        if cfg is None:
            cfg = chip.cfg

        abspath = os.path.abspath(filename)
        chip.logger.debug('Reading configuration file %s', abspath)

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
            chip.error = 1
            chip.logger.error('Illegal file format. Only json/yaml supported. %s', abspath)


        #Merging arguments with the Chip configuration
        if merge:
            localcfg = self.merge(cfg, localcfg)

        return localcfg

    ###########################################################################
    def writecfg(self, filename, chip=None, cfg=None, prune=True, abspath=False):
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

        if chip is None:
            chip = self
        if cfg is None:
            cfg = chip.cfg

        filepath = os.path.abspath(filename)
        self.logger.debug('Writing configuration to file %s', filepath)

        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        if prune:
            chip.logger.debug('Pruning dictionary before writing file %s', filepath)
            cfgcopy = self.prune(cfg)
        else:
            cfgcopy = copy.deepcopy(cfg)

        #resolve absolute paths
        if abspath:
            self._abspath(cfgcopy)

        # Write out configuration based on file type
        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                print(json.dumps(cfgcopy, indent=4), file=f)
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
    def score(self, step, index, chip=None, cfg=None):
        '''Return the sum of product of all metrics for measure step multiplied
        by the values in a weight dictionary input.

        '''

        if chip is None:
            chip = self

        if cfg is None:
            cfg = chip.cfg

        chip.logger.debug('Calculating score for step %s, index %s', step, index)

        score = 0
        for metric in self.getkeys('metric', 'default', 'default', chip=chip, cfg=cfg):
            value = self.get('metric', step, index, metric, 'real', chip=chip, cfg=cfg)
            product = value * self.get('flowgraph', step, 'weight', metric, chip=chip, cfg=cfg)
            score = score + product

        return score

    ###########################################################################
    def min(self, steplist, chip=None, cfg=None):
        '''Return the the step with the minimum score (best) out of list
        of steps provided.

        '''

        if chip is None:
            chip = self

        if cfg is None:
            cfg = chip.cfg

        chip.logger.debug('Calculating minimum from  %s', steplist)

        minscore = Inf
        minstep = None
        for step in steplist:
            score = self.score(step, chip=chip, cfg=cfg)
            if score < minscore:
                minstep = step

        return minstep

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
    def collect(self, chip=None, outdir='output'):
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

        if chip is None:
            chip = self

        if not os.path.exists(outdir):
            os.makedirs(outdir)
        allkeys = self.getkeys(chip=chip)
        copyall = self.get('copyall', chip=chip)
        for key in allkeys:
            leaftype = self.get(*key, field='type', chip=chip)
            if leaftype == 'file':
                copy = self.get(*key, field='copy', chip=chip)
                value = self.get(*key, field='value', chip=chip)
                if copyall | (copy == 'true'):
                    if not isinstance(value, list):
                        value = [value]
                    for item in value:
                        if item:
                            filepath = schema_path(item)
                            shutil.copy(filepath, outdir)

    ###########################################################################
    def hash(self, step, chip=None, cfg=None):
        '''Computes sha256 hash of files based on hashmode set in cfg dict.

        Valid hashing modes:
        * OFF: No hashing of files
        * ALL: Compute hash of all files in dictionary. This couuld take
        hours for a modern technology node with thousands of large setup
        files.
        * SELECTIVE: Compute hashes only on files accessed by the step
        currently being executed.

        '''

        if chip is None:
            chip = self
        if cfg is None:
            cfg = chip.cfg

        hashmode = self.get('hashmode')
        self.logger.info('Computing file hashes with hashmode=%s', hashmode)

        allkeys = self.getkeys(chip=chip, cfg=cfg)

        for keylist in allkeys:
            if 'filehash' in keylist:
                filelist = self.get(*keylist, chip=chip, cfg=cfg)
                self.set([keylist,[]], chip=chip, cfg=cfg)
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
                self.set([keylist,hashlist], chip=chip, cfg=cfg)

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

        # Stepping through all steps/indices and printing out metrics
        data = []
        steps = []
        colwidth = 8
        for step in steplist:
            #Creating centered columns
            steps.append(step.center(colwidth))
            for index in range(self.get('flowgraph', step, 'nproc')):
                metricsfile = "/".join([jobdir,
                                        step+str(index),
                                        "outputs",
                                        self.get('design') + ".pkg.json"])

                #Load results from file (multi-thread safe)
                with open(metricsfile, 'r') as f:
                    sc_results = json.load(f)

                #Copying over metric one at a time
                for metric in self.getkeys('metric', 'default', 'default'):
                    value = self.get('metric', step, str(index), metric, 'real', cfg=sc_results)
                    self.set('metric', step, str(index), metric, 'real', value)


        #Creating Header
        steps = []
        colwidth = 8
        for step in steplist:
            for index in range(self.get('flowgraph', step, 'nproc')):
                stepstr = step + str(index)
                steps.append(stepstr.center(colwidth))

        #Creating table of real values
        metrics = []
        for metric in self.getkeys('metric', 'default', 'default'):
            metrics.append(" " + metric)
            row = []
            for step in steplist:
                for index in range(self.get('flowgraph', step, 'nproc')):
                    row.append(" " +
                               str(self.get('metric', step, str(index), metric, 'real')).center(colwidth))
            data.append(row)

        #Creating goodness score for step
        metrics.append(" " + '**score**')
        row = []
        for step in steplist:
            for index in range(self.get('flowgraph', step, 'nproc')):
                step_score = round(self.score(step, str(index)), 2)
                row.append(" " + str(step_score).center(colwidth))
        data.append(row)

        pandas.set_option('display.max_rows', 500)
        pandas.set_option('display.max_columns', 500)
        pandas.set_option('display.width', 100)
        df = pandas.DataFrame(data, metrics, steps)
        if filename is None:
            print(df.to_string())
            print("-"*135)


    ###########################################################################
    def flowgraph_outputs(self, step, chip=None, cfg=None):
        '''
        Returns an ordered list based on the flowgraph
        '''

        if chip is None:
            chip = self

        if cfg is None:
            cfg = chip.cfg

        outputs = []
        for item in self.getkeys('flowgraph'):
            if step in self.get('flowgraph', 'input', item, chip=chip, cfg=cfg):
                outputs.append(item)

        return outputs

    ###########################################################################
    def getsteps(self, chip=None, cfg=None):
        '''
        Returns an ordered list based on the flowgraph
        '''

        if chip is None:
            chip = self

        if cfg is None:
            cfg = chip.cfg

        #Get length of paths from step to root
        depth = {}
        for step in self.getkeys('flowgraph', chip=chip, cfg=cfg):
            depth[step] = 0
            for path in self._allpaths(chip, cfg, step):
                if len(list(path)) > depth[step]:
                    depth[step] = len(path)

        #Sort steps based on path lenghts
        sorted_dict = dict(sorted(depth.items(), key=lambda depth: depth[1]))
        return list(sorted_dict.keys())

    ###########################################################################
    def _allpaths(self, chip, cfg, node, path=None, allpaths=None):

        if path is None:
            allpaths = []
            path = []
        if 'source' in self.get('flowgraph', node, 'input', chip=chip, cfg=cfg):
            allpaths.append(path)
        else:
            for nextnode in self.get('flowgraph', node, 'input', chip=chip, cfg=cfg):
                newpath = path.copy()
                newpath.append(nextnode)
                return self._allpaths(chip, cfg, nextnode, path=newpath, allpaths=allpaths)
        return list(allpaths)

    ###########################################################################
    def select(self, step, op='min'):
        '''
        Merges multiple inputs into a single directory 'step/inputs'.
        The operation can be an 'or' operation or 'min' operation.
        '''

        steplist = self.get('flowgraph', step, 'input')
        #TODO: Add logic for stepping through procs, steps and selecting

        index = 0
        return (steplist, index)

    ###########################################################################
    def runstep(self, step, index, active, error):

        # Explicit wait loop until inputs have been resolved
        # This should be a shared object to not be messy

        self.logger.info('Step %s waiting on inputs', step)
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

        #Checking that there were no errors in previous steps
        halt = 0
        for input_step in self.get('flowgraph', step, 'input'):
             if input_step != 'source':
                for input_index in range(self.get('flowgraph', input_step, 'nproc')):
                    input_str = input_step + str(input_index)
                    halt = halt + error[input_str]
        if halt:
            self.logger.error('Halting step %s due to previous errors', step)
            self._halt(step, index, error, active)

        # starting actual step execution
        self.logger.info('Starting step %s', step)

        # Build directory
        stepdir = "/".join([self.get('dir'),
                            self.get('design'),
                            self.get('jobname') + str(self.get('jobid')),
                            step + index])

        stepdir = os.path.abspath(stepdir)

        # Directory manipulation
        cwd = os.getcwd()
        if os.path.isdir(stepdir) and (not self.get('remote', 'addr')):
            shutil.rmtree(stepdir)
        os.makedirs(stepdir, exist_ok=True)
        os.chdir(stepdir)
        os.makedirs('outputs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        # Copy files from previous step unless first step
        # Package/import step is special in that it has no inputs
        if 'source' in self.get('flowgraph', step, 'input'):
            self.collect(outdir='inputs')
        elif not self.get('remote', 'addr'):
            #select the previous step outputs to copy over
            steplist, mindex = self.select(step)
            for item in steplist:
                shutil.copytree("../"+item+str(mindex)+"/outputs", 'inputs/')

        # EDA dynamic module load
        try:
            tool = self.get('flowgraph', step, 'tool')
            searchdir = "siliconcompiler.tools." + tool
            modulename = '.'+tool+'_setup'
            module = importlib.import_module(modulename, package=searchdir)
            setup_tool = getattr(module, "setup_tool")
        except:
            traceback.print_exc()
            self.logger.error("Dynamic module load failed for tool '%s' in step '%s'.", tool, step)
            self._halt(step, index, error, active)

        # EDA tool setup
        try:
            setup_tool(self, step, index)
        except:
            traceback.print_exc()
            self.logger.error("Setup script failed for tool '%s' in step '%s'.", tool, step)
            self._halt(step, index, error, active)

        # Check Version if switch exists
        #if self.getkeys('eda', tool, step, str(index), 'vswitch'):
        exe = self.get('eda', tool, step, index, 'exe')
        veropt =self.get('eda', tool, step, index, 'vswitch')
        if veropt!=None:
            cmdstr = f'{exe} {veropt} > {exe}.log'
            self.logger.info("Checking version of '%s' tool in step '%s'.", tool, step)
            exepath = subprocess.run(cmdstr, shell=True)
            if exepath.returncode > 0:
                self.logger.error('Version check failed for %s.', cmdstr)
                self._halt(step, index, error, active)
        else:
            self.logger.info("Skipping version checking of '%s' tool in step '%s'.", tool, step)

        # Exe version logic
        # TODO: add here

        # Run hash on files consumed by current step
        self.hash(step)

        #Copy Reference Scripts
        if 'cmdline' not in self.get('eda', tool, step, index, 'format'):
            if self.get('eda', tool, step, index, 'copy'):
                refdir = schema_path(self.get('eda', tool, step, index, 'refdir'))
                shutil.copytree(refdir, ".", dirs_exist_ok=True)

        # Construct command line
        logfile = exe + ".log"
        options = self.get('eda', tool, step, index, 'option', 'cmdline')

        scripts = []
        if 'cmdline' not in self.get('eda', tool, step, index, 'format' ):
            for value in self.get('eda', tool, step, index, 'script'):
                abspath = schema_path(value)
                scripts.append(abspath)

        cmdlist = [exe]
        cmdlist.extend(options)
        cmdlist.extend(scripts)

        if self.get('quiet') & (step not in self.get('bkpt')):
            cmdlist.append(" &> " + logfile)
        else:
            # the weird construct at the end ensures that this invocation returns the
            # exit code of the command itself, rather than tee
            # (source: https://stackoverflow.com/a/18295541)
            cmdlist.append(" 2>&1 | tee " + logfile + " ; (exit ${PIPESTATUS[0]} )")

        # Create rerun command
        cmdstr = ' '.join(cmdlist)
        with open('run.sh', 'w') as f:
            print('#!/bin/bash\n', cmdstr, file=f)
        os.chmod("run.sh", 0o755)

        # Save config files required by EDA tools
        self.set('arg', 'step', step)
        self.set('arg', 'index', index)

        # Writing out command file
        self.writecfg("sc_manifest.json")
        self.writecfg("sc_manifest.yaml")
        self.writecfg("sc_manifest.tcl", abspath=True)

        # Resetting metrics
        for metric in self.getkeys('metric', 'default', 'default'):
            self.set('metric', step, index, metric, 'real', 0)

        # Final check() before run
        if self.check(step):
            self.logger.error("Step check() for '%s' failed, exiting! See previous errors.", step)
            self._halt(step, index, error, active)

        # Run executable
        self.logger.info("Running %s in %s", step, stepdir)
        self.logger.info('%s', cmdstr)
        cmd_error = subprocess.run(cmdstr, shell=True, executable='/bin/bash')
        if cmd_error.returncode != 0:
            self.logger.error('Command failed. See log file %s', os.path.abspath(logfile))
            # Override exit code if set
            if not self.get('eda', tool, step, index, 'continue'):
                self._halt(step, index, error, active)

        # Post Process (and error checking)
        post_process = getattr(module, "post_process")
        post_error = post_process(self, step, index)

        # Check for errors
        if post_error:
            self.logger.error('Post-processing check failed for step %s', step)
            self._halt(step, index, error, active)

        # save output manifest
        self.writecfg("outputs/" + self.get('design') +'.pkg.json')

        # return fo original directory
        os.chdir(cwd)

        # clearing active bit
        active[step + str(index)] = 0

    ###########################################################################
    def _halt(self, step, index, error, active):
        error[step + str(index)] = 1
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

        # setup sanity check before you start run
        if self.check('run'):
            self.logger.error('Global check() failed, exiting! See previous errors.')
            sys.exit(1)

        # Remote workflow: Dispatch the Chip to a remote server for processing.
        if self.get('remote', 'addr'):
            # Pre-process: Run an 'import' stage locally, and upload the
            # in-progress build directory to the remote server.
            # Data is encrypted if user / key were specified.
            remote_preprocess(self)

            # Run the async 'remote_run' method.
            asyncio.get_event_loop().run_until_complete(remote_run(self))

            # Fetch results (and delete the job's data from the server).
            fetch_results(self)
        else:
            if self.get('remote', 'key'):
                # If 'remote_key' is present in a local job, it represents an
                # encoded key string to decrypt an in-progress job's data. The key
                # must be removed from the config dictionary to avoid logging.
                self.status['decrypt_key'] = self.get('remote', 'key')
                self.set('remote', 'key', None)
                # Decrypt the job's data for processing.
                client_decrypt(self)

            # Run steps if set, otherwise run whole graph
            if self.get('steplist'):
                steplist = self.get('steplist')
            else:
                steplist = self.getsteps()

            # Launch a thread for eact step in flowgraph
            # Use a shared even for errors
            # Use a manager.dict for keeping track of active processes
            # (one unqiue dict entry per process),
            manager = multiprocessing.Manager()
            error = manager.dict()
            active = manager.dict()

            # Set all procs to active
            for step in self.getkeys('flowgraph'):
                for index in range(self.get('flowgraph', step, 'nproc')):
                    stepstr = step + str(index)
                    error[stepstr] = 0
                    if step in steplist:
                        active[stepstr] = 1
                    else:
                        active[stepstr] = 0

            # Create procs
            processes = []
            for step in steplist:
                for index in range(self.get('flowgraph', step, 'nproc')):
                    processes.append(multiprocessing.Process(target=self.runstep,
                                                             args=(step, str(index), active, error,)))
            # Start all procs
            for p in processes:
                p.start()
            # Mandatory procs cleanup
            for p in processes:
                p.join()

            # Make a clean exit if a process failed
            for step in self.getkeys('flowgraph'):
                for index in range(self.get('flowgraph', step, 'nproc')):
                    stepstr = step + str(index)
                    if  error[stepstr] > 0:
                        self.logger.error('Run() failed, exiting! See previous errors.')
                        sys.exit(1)

            # For local encrypted jobs, re-encrypt and delete the decrypted data.
            if 'decrypt_key' in self.status:
                client_encrypt(self)

    ###########################################################################
    def show(self, filename, kind=None):
        '''
        Displays the filename using the appropriate program. Only files
        taken from a valid SC directory path is supported.

        filename=def,gds,json,etc
        kind=used when there are multiple kinds of data inside like
        metricss, hiearchym flowgraph
        step is taken from args, which is when file was written!
        '''

        self.logger.info("Showing file %s", filename)
        filext = os.path.splitext(filename)[1].lower()

        #Figure out which tool to use for opening data
        if filename.endswith(".json"):
            if kind is None:
                self.logger.error("No 'kind' argument supplied for json file.")
            elif kind == "flowgraph":
                pass
            elif kind == "metric":
                pass
            elif kind == "hier":
                pass
        elif filext in ('.def', '.gds', '.gbr', '.brd'):
            #exrtract step from filename
            #error if trying to show file frmo out of tree

            #load settings for showtool
            showtool = self.get('flowgraph', step, 'showtool')
            searchdir = "siliconcompiler.tools." + showtool
            modulename = '.'+showtool+'_setup'
            module = importlib.import_module(modulename, package=searchdir)
            setup_tool = getattr(module, "setup_tool")
            setup_tool(self, 'show')

            # construct command string
            cmdlist = [self.get('eda', showtool, 'show', 'exe')]
            cmdlist.extend(self.get('eda', showtool, 'show', 'option'))

            if 'script' in self.getkeys('eda', showtool, 'show'):
                for value in self.get('eda', showtool, 'show', 'script'):
                    abspath = schema_path(value)
                    cmdlist.extend([abspath])
            if self.get('quiet'):
                cmdlist.append("> /dev/null")
            cmdstr = ' '.join(cmdlist)
            subprocess.run(cmdstr, shell=True, executable='/bin/bash', check=True)

################################################################################
# Annoying helper classes

class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)

#class CustomFormatter(argparse.HelpFormatter(max_help_position=27),
#                      argparse.RawDescriptionHelpFormatter):
#    pass
