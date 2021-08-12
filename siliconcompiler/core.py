# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import asyncio
import subprocess
import os
import sys
import re
import json
import logging as log
import hashlib
import time
import shutil
import copy
import importlib
import code
import textwrap
import uuid
import math
import pandas
import yaml
import argparse
import graphviz
import threading
from time import sleep
import multiprocessing

from argparse import ArgumentParser, HelpFormatter

from importlib.machinery import SourceFileLoader

from siliconcompiler.schema import *
from siliconcompiler.client import *

class Chip:
    """Siliconcompiler Compiler Chip Object Class"""

    ###########################################################################
    def __init__(self, loglevel="INFO", defaults=True):
        '''Initializes Chip object

        Args:
            loglevel (str): Level of debugging (INFO, DEBUG, WARNING,
                CRITICAL, ERROR).
        '''

        # Create a default dict ("spec")
        self.cfg = schema_cfg()

        # Initialize logger
        self.logger = log.getLogger(uuid.uuid4().hex)
        self.handler = log.StreamHandler()
        self.formatter = log.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(str(loglevel))

        # Set Environment Variable if not already set
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
        self.logger.info("SC search path %s", os.environ['SCPATH'])
        self.logger.info("Python search path %s", sys.path)

        # Copy 'defvalue' to 'value'
        self._reset(defaults)

        # Status placeholder dictionary
        # TODO, should be defined!
        self.status = {}

        self.error = 0


    ###########################################################################
    def cmdline(self, prog=None, description=None, paramlist=[]):
        '''
        A command line interface for the SiliconCompiler project. The method
        exposes parameters in the SC echema as command line switchs.  Exact
        format for all command line switches can be found in the example and help
        fields of the schema parameter within the 'schema.py'. module The
        cmdline interface is implemented using the Python argparase package and
        the following user restrictions apply. Custom command line apps can
        be created by restricting the schema parameters exposed at the command
        line. The priority of command line switch settings is: 1.) -loglevel
        2.) -target, 3.) -cfg, 3.) all others.

        * Help is accessed with the '-h' switch
        * Arguments that include spaces must be enclosed with double quotes.
        * List parameters are entered indidually (ie. -y libdir1 -y libdir2)
        * For parameters with boolean types, the switch implies "true".
        * Special characters (such as '-') must be enclosed in double quotes.

        Args:
            prog (string): Name of program to be exeucted at the command
                 line. The default program name is 'sc'.
            description (string): Header help function to be displayed
                 by the command line program. By default a short
                 description of the main sc program is displayed.
            paramlist (list): List of SC schema parameters to expose
                 at the command line. By default all SC scema params are
                 exposed as switches.

        Examples:
            >>> cmdline()
            Creates the default sc command line interface
            >>> cmdline(prog='sc-display', paramlist=['show'])
            Creates a command line interface called sc-display with a
            a single switch parameter ('show').

        '''

        os.environ["COLUMNS"] = '80'
        # defaults to the sc application
        if prog == None:
            prog = 'sc'
            description = '''
            --------------------------------------------------------------
            SiliconCompiler (SC)
            SiliconCompiler is an open source Python based hardware
            compiler project that aims to fully automate the translation
            of high level source code into manufacturable hardware.

            Website: https://www.siliconcompiler.com
            Documentation: https://www.siliconcompiler.com/docs
            Community: https://www.siliconcompiler.com/community
            '''
        elif description == None:
            description = '''
            '''

        # Argparse
        parser = argparse.ArgumentParser(prog='sc',
                                         prefix_chars='-+',
                                         description=description,
                                         formatter_class=RawFormatter)

        # Required positional source file argument

        parser.add_argument('source',
                            nargs='+',
                            help=self.get('source',field='short_help'))

        # Get all keys from global dictionary or override at command line
        if paramlist:
            allkeys = paramlist
        else:
            allkeys = self.getkeys()

        argmap = {}
        # Iterate over all keys to add parser argument
        for key in allkeys:

            #Fetch fields from leaf cell
            helpstr = self._search(self.cfg, *key, mode='get', field='short_help')
            typestr = self._search(self.cfg, *key, mode='get', field='type')
            paramstr = self._search(self.cfg, *key, mode='get', field='param_help')
            switchstr = self._search(self.cfg, *key, mode='get', field='switch')

            #Create a map from parser args back to dictionary
            #Special gcc/verilator compatible short switches get mapped to
            #the key, all others get mapped to switch
            if '_' in switchstr:
                dest = switchstr.replace('-','')
            else:
                dest = key[0]

            if 'source' in key:
                argmap['source'] = paramstr
            elif typestr == 'bool':
                argmap[dest] = paramstr
                parser.add_argument(switchstr,
                                    metavar='',
                                    dest=dest,
                                    action='store_const',
                                    const="true",
                                    help=helpstr,
                                    default = argparse.SUPPRESS)
            #list type arguments
            elif re.match(r'\[',typestr):
                #all the rest
                argmap[dest] = paramstr
                parser.add_argument(switchstr,
                                    metavar='',
                                    dest=dest,
                                    action='append',
                                    help=helpstr,
                                    default = argparse.SUPPRESS)

            else:
                #all the rest
                argmap[dest] = paramstr
                parser.add_argument(switchstr,
                                    metavar='',
                                    dest=dest,
                                    help=helpstr,
                                    default = argparse.SUPPRESS)


        #Preprocess sys.argv to enable linux commandline switch formats
        #(gcc, verilator, etc)
        scargs = []

        # Iterate from index 1, otherwise we end up with script name as a
        # 'source' positional argument
        for item in sys.argv[1:]:
            #Split switches with one character and a number after (O0,O1,O2)
            opt = re.match(r'(\-\w)(\d+)',item)
            #Split assign switches (-DCFG_ASIC=1)
            assign = re.search(r'(\-\w)(\w+\=\w+)',item)
            #Split plusargs (+incdir+/path)
            plusarg = re.search(r'(\+\w+\+)(.*)',item)
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

        #Grab argument from pre-process sysargs
        cmdargs = vars(parser.parse_args(scargs))

        # set loglevel if set at command line
        if 'loglevel' in cmdargs.keys():
            self.logger.setLevel(cmdargs['loglevel'])

        # read in target if set
        if 'target' in cmdargs.keys():
            self.target(cmdargs['target'])

        # read in all cfg files
        if 'cfg' in cmdargs.keys():
            for item in cmdargs['cfg']:
                self.readcfg(item)

        # insert all parameters in dictionary
        for key, val in cmdargs.items():
            if type(val)==list:
                val_list = val
            else:
                val_list = [val]
            for item in val_list:
                args = schema_reorder_keys(argmap[key], item)
                self._search(self.cfg, *args, mode='add')

    ###########################################################################
    def target(self, arg=None):
        '''
        Searches the SCPATH and PYTHON paths for the target specified by the
        Chip 'target' parameter. The target is supplied as a  two alphanumeric
        strings separated by an underscore ('_'). The first string part
        represents the technology platform, while the second string part
        represents the eda flow.

        In order of priority,  the search path sequence is:
        1.) Try finding the target in the built in directory
        2.) Search the rest of the paths

        The dynamically loaded target platform module must contain three
        standard functions. There is no functionality requirements on the
        three functions.

            setup_platform(chip) : Sets up basic PDK information

            setup_libs(chip) : Setups of PDK specific IP/Libraries

            setup_design(chip) : Setups up recommended design flows

        The dynamically loaded target eda module contains a single
        standard functions:

            setup_eda(chip): Defines the implementation flow,

        The setup_eda further loads setup_tool modules on a per step basis.
        The dynamically loaded per step module must contain for standard
        functions.

            setup_tool(chip): A one time setup of the 'flow' dictionary per step

            setup_options(chip,step): Run-time options driver

            pre_process(chip,step): Pre-processing to run before executable

            post_process(chip,step): Post-processing to run before executable

        Args:
            arg (string): If the argument is supplied, the set('target', name)
                is called before dynamically loading the target platform

        Examples:
            >>> chip.target()
        '''

        #Sets target in dictionary if string is passed in
        if arg is not None:
            self.set('target', arg)

        # Error checking
        if not self.get('target'):
            self.logger.error('Target not defined.')
            sys.exit()
        elif len(self.get('target').split('_')) > 2:
            self.logger.error('Target format should be one or two strings sepaated by underscore')
            sys.exit()

        # Technology platform
        platform = self.get('target').split('_')[0]
        if self.get('mode') == 'asic':
            try:
                searchdir = 'siliconcompiler.foundries'
                module = importlib.import_module('.'+platform, package=searchdir)
                setup_platform = getattr(module, "setup_platform")
                setup_platform(self)
                setup_libs = getattr(module, "setup_libs")
                setup_libs(self)
                setup_design = getattr(module, "setup_design")
                setup_design(self)
                self.logger.info("Loaded platform '%s'", platform)
            except ModuleNotFoundError:
                self.logger.critical("Platform %s not found.", platform)
                sys.exit()
        else:
            self.set('fpga','partname', platform)


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
                sys.exit()

    ###########################################################################
    def help(self, *args, file=None, mode='full', format='txt'):
        '''
        Prints out detailed or summary help for the schema key path provided.
        The function is used to auto-generate documentation and is accessible
        at diretly by the user.

        Args:
            file (filehandle): If 'None', help is printed to stdout, else
               help is printed to the filehandle
            mode (str): When 'full',
               is specified, the complete help description is printed out. When
               'table' is specified, a one-line table row descripton is printed.
            format (str): Format out output ('txt', 'md', 'rst').

        Examples:
            >>> help('target')
            Prints out the complet descripton of 'target' to stdout
            >>> help('target', mode='table')
            Prints out a one-line table row descripton of 'target' to stdout
        '''

        self.logger.debug('Fetching help for %s', args)

        #Fetch Values
        description = self._search(self.cfg, *args, mode='get', field='short_help')
        param = self._search(self.cfg, *args, mode='get', field='param_help')
        typestr = ' '.join(self._search(self.cfg, *args, mode='get', field='type'))
        defstr = ' '.join(self._search(self.cfg, *args, mode='get', field='defvalue'))
        requirement = self._search(self.cfg, *args, mode='get', field='requirement')
        helpstr = self._search(self.cfg, *args, mode='get', field='help')
        example = self._search(self.cfg, *args, mode='get', field='example')

        #Removing multiple spaces and newlines
        helpstr = helpstr.rstrip()
        helpstr = helpstr.replace("\n", "")
        helpstr = ' '.join(helpstr.split())

        #Removing extra spaces in example string
        cli = ' '.join(example[0].split())

        for idx, item in enumerate(example):
            example[idx] = ' '.join(item.split())
            example[idx] = example[idx].replace(", ", ",")

        #Wrap text
        para = textwrap.TextWrapper(width=60)
        para_list = para.wrap(text=helpstr)

        #Full Doc String
        fullstr = ("-"*3 +
                   "\nDescription: " + description.lstrip() + "\n" +
                   "\nParameter:   " + param.lstrip() + "\n"  +
                   "\nExamples:    " + example[0].lstrip() +
                   "\n             " + example[1].lstrip() + "\n" +
                   "\nHelp:        " + para_list[0].lstrip() + "\n")
        for line in para_list[1:]:
            fullstr = (fullstr +
                       " "*13 + line.lstrip() + "\n")

        #Refcard String
        #Need to escape dir to get pdf to print in pandoc?
        outlst = [param.replace("<dir>", "\\<dir\\>"),
                  description,
                  typestr,
                  requirement,
                  defstr]
        shortstr = "|{: <52}|{: <30}|{: <15}|{: <10}|{: <10}|".format(*outlst)

        #Selecting between full help and one liner
        if mode == "full":
            outstr = fullstr
        else:
            outstr = shortstr

        #Print to screen or file
        if file is None:
            print(outstr)
        else:
            print(outstr, file=file)

    ###########################################################################
    def get(self, *args, cfg=None, field='value'):
        '''
        Returns value from the Chip dictionary based on the key tree supplied.

        Args:
            *args (string): A non-keyworded variable length argument list to
                used to look up non-leaf key tree in the Chip dictionary.
                Specifying a non-existent key tree results in a program exit.
            field (string): Specifies the leaf-key value to fetch.

        Returns:
            Value(s) found for the key tree supplied. The returned value
        can be a boolean, list, or string depending on the parameter type.

        Examples:
            >>> get('pdk', 'foundry')
            Returns the name of the foundry in the Chip dictionary.

        '''

        self.logger.debug('Reading config dictionary value: %s', args)

        if cfg is None:
            cfg = self.cfg

        keys = list(args)
        for k in keys:
            if isinstance(k, list):
                self.logger.critical("Illegal format, keys cannot be lists. Keys=%s", k)
                sys.exit()
        return self._search(cfg, *args, field=field, mode='get')

    ###########################################################################
    def getkeys(self, *args, cfg=None):
        '''
        Returns a list of keys from the Chip dicionary based on the key
        tree supplied.

        Args:
            *args (string): A non-keyworded variable length argument list to
                used to look up non-leaf key tree in the Chip dictionary.
                The key-tree is supplied in order. If the argument list is empty,
                all Chip dictionary trees are returned as as a list of lists.
                Specifying a non-existent key tree results in a program exit.
ss
        Returns:
            A list of keys found for the key tree supplied.

        Examples:
            >>> getkeys('pdk')
            Returns all keys associated for the 'pdk' dictionary.
            >>> getkeys()
            Returns all key trees in the dictionary as a list of lists.
        '''

        if cfg is None:
            cfg = self.cfg

        if len(list(args)) > 0:
            self.logger.debug('Getting schema parameter keys for: %s', args)
            keys = list(self._search(cfg, *args, mode='getkeys'))
            if 'default' in keys:
                keys.remove('default')
        else:
            self.logger.debug('Getting all schema parameter keys.')
            keys = list(self._allkeys(cfg))

        return keys

    ###########################################################################
    def _allkeys(self, cfg, keys=None, allkeys=None):
        '''
        A recursive function that returns all the non-leaf keys in the Chip
        dictionary.

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
                self._allkeys(cfg[k], keys=newkeys, allkeys=allkeys)
        return allkeys

    ###########################################################################
    def set(self, *args, cfg=None, field='value'):
        '''
        Sets the value field of the key-tree in the argument list to the
        data list supplied.

        Args:
            *args (string): A non-keyworded variable length argument list to
                used to look up non-leaf key tree in the Chip dictionary.The
                key-tree is supplied in order, with the data list supplied as
                the last argument. Specifying a non-existent key tree
                results in a program exit.

        Examples:
            >>> set('design', 'mydesign')
            Sets the Chip 'design' name to 'mydesign'
        '''

        self.logger.debug('Setting config dictionary value: %s', args)

        if cfg is None:
            cfg = self.cfg

        all_args = list(args)

        return self._search(cfg, *all_args, field=field, mode='set')

    ###########################################################################
    def add(self, *args, cfg=None, field='value'):
        '''
        Appends the data list supplied to the list currently in the leaf-value
        of the key-tree in the argument list.

        Args:
            *args (string): A non-keyworded variable length argument list to
                used to look up non-leaf key tree in the Chip dictionary. The
                key-tree is supplied in order, with the data list supplied as
                the last argument. Specifying a non-existent key tree
                results in a program exit.

        Examples:
            >>> add('source', 'mydesign.v')
            Adds the file 'mydesign.v' to the list of sources.
        '''

        self.logger.debug('Adding config dictionary value: %s', args)

        if cfg is None:
            cfg = self.cfg

        all_args = list(args)

        # Convert val to list if not a list
        return self._search(cfg, *all_args, field=field, mode='add')


    ###########################################################################
    def _search(self, cfg, *args, field='value', mode='get'):
        '''
        Recursive function that searches a Chip dictionary for a match to
        the combination of *args and fields supplied. The function is used
        to set and get data within the dictionary.
        '''

        all_args = list(args)
        param = all_args[0]
        val = all_args[-1]
        #set/add leaf cell (all_args=(param,val))
        if (mode in ('set', 'add')) & (len(all_args) == 2):
            #making an 'instance' of default if not found
            if not param in cfg:
                if not 'default' in cfg:
                    self.logger.error('Search failed. \'%s\' is not a valid key', all_args)
                    self.error = 1
                else:
                    cfg[param] = copy.deepcopy(cfg['default'])
            #setting or extending value based on set/get mode
            if not field in cfg[param]:
                self.logger.error('Search failed. Field not found for \'%s\'', param)
                self.error = 1
            #check legality of value
            if schema_typecheck(self, cfg[param], param, val):
                #promote value to list for list types
                if (type(val) != list) & (field == 'value') & bool(re.match(r'\[',cfg[param]['type'])):
                    val = [str(val)]
                #set value based on scalar/list/set/add
                if (mode == 'add') & (type(val) == list):
                    cfg[param][field].extend(val)
                elif (mode == 'set') & (type(val) == list):
                    cfg[param][field] = val
                #ignore add commmand for scalars
                elif (type(val) != list):
                    cfg[param][field] =  str(val)
            #return field
            return cfg[param][field]
        #get leaf cell (all_args=param)
        elif len(all_args) == 1:
            if mode == 'getkeys':
                return cfg[param].keys()
            else:
                if not field in cfg[param]:
                    self.logger.error('Key error, leaf param not found %s', field)
                    self.error = 1
                elif field == 'value':
                        #check for list/vs scalar
                    if bool(re.match(r'\[',cfg[param]['type'])):
                        return_list = []
                        for item in cfg[param]['value']:
                            if re.search('int', cfg[param]['type']):
                                return_list.append(int(item))
                            elif re.search('float', cfg[param]['type']):
                                return_list.append(float(item))
                            else:
                                return_list.append(item)
                        return return_list
                    else:
                        if cfg[param]['value'] is None:
                            # Unset scalar of any type
                            scalar = None
                        elif cfg[param]['type'] == "int":
                            scalar = int(cfg[param]['value'])
                        elif cfg[param]['type'] == "float":
                            scalar = float(cfg[param]['value'])
                        elif cfg[param]['type'] == "bool":
                            scalar = (cfg[param]['value'] == 'true')
                        else:
                            scalar = cfg[param]['value']
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
            return self._search(cfg[param], *all_args, field=field, mode=mode)

    ###########################################################################
    def _prune(self, cfg=None, top=True):
        '''
        Recursive function that creates a copy of the Chip dictionary and
        then removes all sub trees with non-set values and sub-trees
        that contain a 'default' key.
        '''

        #10 should be enough for anyone...
        maxdepth = 10
        i = 0

        if cfg is None:
            cfg = copy.deepcopy(self.cfg)

        #When at top of tree loop maxdepth times to make sure all stale
        #branches have been removed, not eleagnt, but stupid-simple
        while i < maxdepth:
            #Loop through all keys starting at the top
            for k in list(cfg.keys()):
                #removing all default/template keys
                if k == 'default':
                    del cfg[k]
                #remove long help from printing
                elif 'help' in cfg[k].keys():
                    del cfg[k]['help']
                #removing empty values from json file
                elif 'value' in cfg[k].keys():
                    if (not cfg[k]['value']) | (cfg[k]['value'] == None):
                        del cfg[k]
                #removing stale branches
                elif not cfg[k]:
                    cfg.pop(k)
                #keep traversing tree
                else:
                    self._prune(cfg[k], top=False)
            if top:
                i += 1
            else:
                break
        return cfg

    ###########################################################################
    def _abspath(self, cfg):
        '''Recursive function that goes through Chip dictionary and
        resolves all relative paths where required.
        '''

        #Recursively going through dict to set abspaths for files
        for k, v in cfg.items():
            #print("abspath", k,v)
            if isinstance(v, dict):
                #indicates leaf cell
                if 'value' in cfg[k].keys():
                    #print(cfg[k]['value'])
                    #print("dict=",cfg[k])
                    #only do something if type is file
                    if re.search('file|dir', cfg[k]['type']):
                        #iterate if list
                        if re.match(r'\[', cfg[k]['type']):
                            for i, v in enumerate(list(cfg[k]['value'])):
                                #Look for relative paths in search path
                                cfg[k]['value'][i] = schema_path(v)
                        else:
                            cfg[k]['value'] = schema_path(cfg[k]['value'])
                else:
                    self._abspath(cfg[k])

    ###########################################################################
    def _printcfg(self, cfg, keys=None, file=None, mode="", field='value', prefix=""):
        '''Recursive function that goes through Chip dictionary and prints out
        configuration commands with one line per value. Currently only TCL is
        supported.
        '''

        if keys is None:
            keys = []
        for k in cfg:
            newkeys = keys.copy()
            newkeys.append(k)
            #detect leaf cell
            if 'defvalue' in cfg[k]:
                if mode == 'tcl':
                    if bool(re.match(r'\[',str(cfg[k]['type']))) & (field == 'value'):
                        alist = cfg[k][field].copy()
                    else:
                        alist = [cfg[k][field]]
                    for i, val in enumerate(alist):
                        #replace $VAR with env(VAR) for tcl
                        m = re.match(r'\$(\w+)(.*)', str(val))
                        if m:
                            print("env replace")
                            alist[i] = ('$env(' +
                                        m.group(1) +
                                        ')' +
                                        m.group(2))

                    #create a TCL dict
                    keystr = ' '.join(newkeys)
                    valstr = ' '.join(map(str,alist)).replace(';', '\\;')
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
    def mergecfg(self, d2, d1=None):
        '''Recursively copies values in dictionary d2 to the Chip dictionary.
        '''

        if d1 is None:
            d1 = self.cfg
        for k, v in d2.items():
            #Checking if dict exists in self.cfg and new dict
            if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], dict):
                #if we reach a leaf copy d2 to d1
                if 'value' in d1[k].keys():
                    if ('type' in d1[k].keys()) and ('[' in d1[k]['type']):
                        #only add items that are not in the current list
                        new_items = []
                        for i in range(len(d2[k]['value'])):
                            if d2[k]['value'][i] not in d1[k]['value']:
                                new_items.append(d2[k]['value'][i])
                        d1[k]['value'].extend(new_items)
                    else:
                        # Scalar copy.
                        d1[k]['value'] = d2[k]['value']
                    #if not in leaf keep descending
                else:
                    self.mergecfg(d2[k], d1=d1[k])
                #if a new d2 key is found do a deep copy
            else:
                d1[k] = d2[k].copy()

    ###########################################################################
    def check(self):
        '''
        Performs a validity check for Chip dictionary, printing out warnings
        and error messages to stdout.

        Returns:
            Returns True of if the Chip dictionary is valid, else returns
            False.

        Examples:
            >>> check()
           Returns True of the Chip dictionary checks out.
        '''

        error = False

        #1. Get all keys
        #2. For all keys:
        #   -Get values
        #   -Check requirements equation


        if not self.get('design'):
            self.logger.error('Design name has not been set.')
            error = True
        elif not self.getkeys('flowgraph'):
            self.logger.error('Flowgraph has not been defined.')
            error = True

        if error:

            sys.exit()

    ###########################################################################
    def readcfg(self, filename):
        '''Reads a json or yaml formatted file into the Chip dictionary.

        Args:
            filename (file): A relative or absolute path toe a file to load
                into dictionary.

        Examples:
            >>> readcfg('mychip.json')
            Loads the file mychip.json into the current Chip dictionary.
        '''

        abspath = os.path.abspath(filename)

        self.logger.debug('Reading configuration file %s', abspath)

        #Read arguments from file based on file type
        if abspath.endswith('.json'):
            with open(abspath, 'r') as f:
                read_args = json.load(f)
        elif abspath.endswith('.yaml'):
            with open(abspath, 'r') as f:
                read_args = yaml.load(f, Loader=yaml.SafeLoader)
        elif abspath.endswith('.tcl'):
            read_args = self.readtcl(abspath)
        else:
            read_args = self.readmake(abspath)

        #Merging arguments with the Chip configuration
        self.mergecfg(read_args)

    ###########################################################################
    def writecfg(self, filename, step=None, cfg=None, prune=True, abspath=False):
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

        filepath = os.path.abspath(filename)
        self.logger.debug('Writing configuration to file %s', filepath)

        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        #prune cfg if option set
        if (cfg is None) & (prune==True):
            cfgcopy = self._prune(self.cfg)
        elif (cfg is not None) & (prune==True):
            cfgcopy = self._prune(cfg)
        elif (cfg is None) & (prune==False):
            cfgcopy = copy.deepcopy(self.cfg)
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
                print("#############################################", file=f)
                print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
                print("#############################################", file=f)
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
    def score(self, step):
        '''Return the sum of product of all metrics for measure step multiplied
        by the values in a weight dictionary input.

        '''

        score = 0
        for metric in self.getkeys('metric', 'default', 'default'):
            value = self.get(self.get(cfg['metric'][step]['real'][metric]))
            if metric in (self.getkey(cfg['flowgraph'][step]['weight'])):
                product = value * self.get(self.getkey(cfg['flowgraph'][step]['weight']))
            else:
                product = value * 1.0
            score = score + product

        return score

    ###########################################################################
    def writegraph(self, filename):
        '''Exports the execution flow graph using the graphviz library.
        For graphviz formats supported, see https://graphviz.org/.
        For rendering
        '''
        filepath = os.path.abspath(filename)
        self.logger.debug('Writing flowgraph to file %s', filepath)
        fileroot, ext = os.path.splitext(filepath)
        fileformat = ext.replace(".","")
        gvfile = fileroot+".gv"
        dot = graphviz.Digraph(format=fileformat)
        for step in self.getkeys('flowgraph'):
            if self.get('flowgraph',step, 'tool'):
                labelname = step+'\\n('+self.get('flowgraph',step, 'tool')+")"
            else:
                labelname = step
            dot.node(step,label=labelname)
            for prev_step in self.get('flowgraph',step,'input'):
                dot.edge(prev_step, step)
        dot.render(filename=fileroot, cleanup=True)

    ###########################################################################
    def _reset(self, defaults, cfg=None):
        '''Recursively copies 'defvalue' to 'value' for all configuration
        parameters
        '''
        #Setting initial dict so user doesn't have to
        if cfg is None:
            self.logger.debug('Loading default values into Chip configuration')
            cfg = self.cfg
        for k, v in cfg.items():
            if isinstance(v, dict):
                if 'defvalue' in cfg[k].keys():
                    #list type
                    if re.match(r'\[',cfg[k]['type']):
                        if defaults:
                            cfg[k]['value'] = cfg[k]['defvalue'].copy()
                        else:
                            cfg[k]['value'] = []
                    #scalars
                    elif defaults & bool(cfg[k]['defvalue']):
                        cfg[k]['value'] = cfg[k]['defvalue']
                    else:
                        cfg[k]['value'] = None
                else:
                    self._reset(defaults, cfg=cfg[k])

    ###########################################################################
    def wait(self, step=None):
        '''Waits for specific step to complete
        '''

        if step is None:
            steplist =self.getkeys('flowgraph')
        else:
            steplist = [step]

        while True:
            busy = False
            for step in steplist:
                if self.get('status', step, 'active'):
                    self.logger.info("Step '%s' is still active", step)
                    busy = True
            if busy:
                #TODO: Change this timeout
                self.logger.info("Waiting 10sec for step to finish")
                time.sleep(10)
            else:
                break


    ########################################################################
    def package(self, dir='output'):
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

        if not os.path.exists(dir):
            os.makedirs(dir)
        allkeys = self.getkeys()
        copyall = self.get('copyall')
        for key in allkeys:
            leaftype = self._search(self.cfg, *key, mode='get', field='type')
            if leaftype == 'file':
                copy = self._search(self.cfg, *key, mode='get', field='copy')
                value = self._search(self.cfg, *key, mode='get', field='value')
                if copyall | (copy == 'true'):
                    if type(value) != list:
                        value = [value]
                    for item in value:
                        if item:
                            filepath = schema_path(item)
                            shutil.copy(filepath, dir)

    ###########################################################################
    def hash(self, cfg=None):
        '''Rescursive function that computes the hash values for files in the
        Chip dictionary based on the setting of the hashmode.
        '''

        #checking to see how much hashing to do
        hashmode = self.get('hashmode')
        if hashmode != 'NONE':
            if cfg is None:
                self.logger.info('Computing file hashes with mode %s', hashmode)
                cfg = self.cfg
            #Recursively going through dict
            for k, v in cfg.items():
                if isinstance(v, dict):
                    #indicates leaf cell/file to act on
                    if 'filehash' in cfg[k].keys():
                        #clear out old values (do comp?)
                        cfg[k]['hash'] = []
                        for i, v in enumerate(cfg[k]['value']):
                            filename = schema_path(v)
                            self.logger.debug('Computing hash value for %s', filename)
                            if os.path.isfile(filename):
                                sha256_hash = hashlib.sha256()
                                with open(filename, "rb") as f:
                                    for byte_block in iter(lambda: f.read(4096), b""):
                                        sha256_hash.update(byte_block)
                                hash_value = sha256_hash.hexdigest()
                                cfg[k]['hash'].append(hash_value)
                    else:
                        self.hash(cfg=cfg[k])

    ###########################################################################
    def _compare(self, file1, file2):
        '''Compares Chip configurations contained in two different json files
        Useful??

        '''

        #TODO: Solve recursively
        pass

        abspath1 = os.path.abspath(file1)
        abspath2 = os.path.abspath(file2)

        self.logger.info('Comparing JSON format configuration file %s and %s ',
                         abspath1,
                         abspath2)

        #Read arguments from file
        with open(abspath1, "r") as f:
            file1_args = json.load(f)
        with open(abspath2, "r") as f:
            file2_args = json.load(f)

        file1_keys = self.getkeys(cfg=file1_args)
        file2_keys = self.getkeys(cfg=file2_args)
        same = True
        ##TODO: Implement...
        #1. Sorted key list should be identical
        #2. If keylists are identical, then compare values


    ###########################################################################
    def audit(self, filename=None):
        '''Performance an an audit of each step in the flow
        '''

        pass


    ###########################################################################
    def calcyield(self, model='poisson'):
        '''Calculates the die yield
        '''

        d0 = self.get('pdk','d0')
        diesize = self.get('asic','diesize').split()
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
        wafersize = self.get('pdk', 'wafersize', 'value')
        edgemargin = self.get('pdk', 'edgemargin', 'value')
        hscribe = self.get('pdk', 'hscribe', 'value')
        vscribe = self.get('pdk', 'vscribe', 'value')

        #Design parameters
        diesize = self.get('asic','diesize').split()
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

        return cost

    ###########################################################################
    def summary(self, steplist=None, filename=None):
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

        if steplist == None:
            steplist = self.getkeys('flowgraph')

        design = self.get('design')

        #TODO, FIX FOR GRAPH!!
        startindex = 0
        stopindex = len(steplist)-1

        jobdir = (self.get('build_dir') +
                  "/" + design + "/" +
                  self.get('jobname') +
                  str(self.get('jobid')))

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

        # Stepping through all directories
        # for remote running, metrics are not in memory, must be read from file
        for stepindex in range(startindex, stopindex + 1):
            step = steplist[stepindex]
            metricsfile = "/".join([jobdir,
                                    step,
                                    "outputs",
                                    design + "_manifest.json"])

            #Load results from file (multi-thread safe)
            with open(metricsfile, 'r') as f:
                sc_results = json.load(f)
            #Copy results into step
            self.cfg['metric'][step] = copy.deepcopy(sc_results['metric'][step])

        #Creating step index
        data = []
        steps = []
        colwidth = 8
        #Creating header row
        for stepindex in range(startindex, stopindex + 1):
            step = steplist[stepindex]
            steps.append(step.center(colwidth))

        #Creating table of real values
        metrics = []
        for metric in  self.getkeys('metric', 'default', 'default'):
            metrics.append(" " + metric)
            row = []
            for stepindex in range(startindex, stopindex + 1):
                step = steplist[stepindex]
                row.append(" " +
                           str(self.get('metric', step, 'real', metric)).center(colwidth))
            data.append(row)

        pandas.set_option('display.max_rows', 500)
        pandas.set_option('display.max_columns', 500)
        pandas.set_option('display.width', 100)
        df = pandas.DataFrame(data, metrics, steps)
        if filename is None:
            print(df.to_string())
            print("-"*135)

    ###########################################################################
    def runstep(self, step, active):

        # Explicit wait loop until inputs have been resolved
        # This should be a shared object to not be messy
        while True:
            pending = 0
            for item in self.get('flowgraph', step, 'input'):
                pending = pending + active[item]
            if not pending:
                break
            self.logger.info('Step %s waiting on inputs', step)
            sleep(1)

        self.logger.info('Starting step %s', step)

        # Build directory
        stepdir = "/".join([self.get('build_dir'),
                            self.get('design'),
                            self.get('jobname') + str(self.get('jobid')),
                            step])

        # Directory manipulation
        cwd = os.getcwd()
        if os.path.isdir(stepdir) and (not self.get('remote','addr')):
            shutil.rmtree(stepdir)
        os.makedirs(stepdir, exist_ok=True)
        os.chdir(stepdir)
        os.makedirs('outputs', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        # Copy files from previous step unless first step
        # Package/import step is special in that it has no inputs
        if not self.get('flowgraph', step, 'input'):
            self.package(dir='inputs')
        elif not self.get('remote','addr'):
            for item in self.get('flowgraph', step, 'input'):
                shutil.copytree("../"+item+"/outputs", 'inputs/'+item)

        # Dynamic EDA tool module load
        tool = self.get('flowgraph', step, 'tool')
        searchdir = "siliconcompiler.tools." + tool
        modulename = '.'+tool+'_setup'
        module = importlib.import_module(modulename, package=searchdir)
        setup_tool = getattr(module, "setup_tool")
        setup_tool(self, step)

        # Check installation
        exe = self.get('eda', tool, step, 'exe')
        exepath = subprocess.run("command -v "+exe+">/dev/null", shell=True)
        if exepath.returncode > 0:
            self.logger.critical('Executable %s not installed.', exe)
            sys.exit()

        #Copy Reference Scripts
        if self.get('eda', tool, step, 'copy'):
            refdir = schema_path(self.get('eda', tool, step, 'refdir'))
            shutil.copytree(refdir, ".", dirs_exist_ok=True)

        # Construct command line
        exe = self.get('eda', tool, step, 'exe')
        logfile = exe + ".log"
        options = self.get('eda', tool, step, 'option')

        scripts = []
        if 'script' in self.getkeys('eda', tool, step):
            for value in self.get('eda', tool, step, 'script'):
                abspath = schema_path(value)
                scripts.append(abspath)

        cmdlist =  [exe]
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
            print('#!/bin/bash\n',cmdstr, file=f)
        os.chmod("run.sh", 0o755)

        # Init Metrics Table
        for metric in self.getkeys('metric', 'default', 'default'):
            self.set('metric', step, 'real', metric, 0)

        # Save config files required by EDA tools
        # Create a local copy with arguments set
        # The below snippet is how we communicate thread local data needed
        # for scripts. Anything done to the cfgcopy is only seen by this thread

        # Passing local arguments to EDA tool!
        cfglocal = copy.deepcopy(self.cfg)
        self.set('arg', 'step', step, cfg=cfglocal)
        # Writing out files
        self.writecfg("sc_manifest.json", cfg=cfglocal, prune=False)
        self.writecfg("sc_manifest.yaml", cfg=cfglocal, prune=False)
        self.writecfg("sc_manifest.tcl", cfg=cfglocal, abspath=True)

        # Run exeucutable
        self.logger.info("Running %s in %s", step, os.path.abspath(stepdir))
        self.logger.info('%s', cmdstr)
        error = subprocess.run(cmdstr, shell=True, executable='/bin/bash')

        # Post Process (and error checking)
        post_process = getattr(module, "post_process")
        post_error = post_process(self, step)

        # Check for errors
        if (error.returncode | post_error):
            self.logger.error('Command failed. See log file %s', os.path.abspath(logfile))
            self.set('status', step, 'error', 1)
            self.set('status', step, 'active', 0)
            sys.exit()

        # save output manifest
        self.writecfg("outputs/" + self.get('design') +'_manifest.json')

        # upload files
        #if remote:
        #    upload_sources_to_cluster(self)

        # return fo original directory
        os.chdir(cwd)

        # clearing active bit
        active[step] = 0

    ###########################################################################
    def run(self, steplist=None):

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
        self.check()

        # default is to launch whole graph
        if steplist == None:
            steplist = self.getkeys('flowgraph')

        # Set all threads to active before launching to avoid races
        # Sequence matters, do NOT merge this loop with loop below!

        # Launch a thread for eact step in flowgraph
        manager = multiprocessing.Manager()
        # Create a shared
        active = manager.dict()
        # Set all procs to active
        for step in steplist:
            active[step] = 1
        # Create procs
        processes = []
        for step in steplist:
            processes.append(multiprocessing.Process(target=self.runstep, args=(step, active)))
        # Start all procs
        for p in processes:
            p.start()
        # Mandatory procs cleanup
        for p in processes:
            p.join()

    ###########################################################################
    def show(self, step=None, filetype=None):
        '''
        Display output of a step. File to be displayed and program used for display
        is configured in the EDA directory.
        TODO: Should we support viewing multiple outputs for a step?
        Would need to pass in parameters to the tcl scripts to accomplish this.
        '''

        if step==None:
            if self.get('show'):
                step = self.get('show')
            else:
                self.logger.error("Running show commmand with no showsteps defined.")
                sys.exit()

        # Dynamic EDA tool module load
        showtool = self.get('flowgraph', step, 'showtool')
        searchdir = "siliconcompiler.tools." + showtool
        modulename = '.'+showtool+'_setup'
        module = importlib.import_module(modulename, package=searchdir)
        setup_tool = getattr(module, "setup_tool")
        setup_tool(self, 'show')

        # construct command string
        cmdlist =  [self.get('eda', showtool, 'show', 'exe')]
        cmdlist.extend(self.get('eda', showtool, 'show', 'option'))

        if 'script' in self.getkeys('eda', showtool, 'show'):
            for value in self.get('eda', showtool, 'show', 'script'):
                abspath = schema_path(value)
                cmdlist.extend([abspath])

        cmdstr = ' '.join(cmdlist)

        # Check setup
        self.check()

        #Enabling show on old run directory
        if self.get('jobid'):
            jobid = self.get('jobid');
        else:
            jobid = 1

        print(self.get('build_dir'))
        stepdir = "/".join([self.get('build_dir'),
                            self.get('design'),
                            self.get('jobname') + str(jobid),
                            step])

        self.logger.info("Showing output from %s", os.path.abspath(stepdir))

        # execute show command from output directory
        cwd = os.getcwd()
        os.chdir(stepdir)
        subprocess.run(cmdstr, shell=True, executable='/bin/bash')
        os.chdir(cwd)

    ###########################################################################
    def set_jobid(self):

        # Return if jobid is already set.
        if self.get('jobid'):
            return

        design = self.get('design')
        dirname = self.get('build_dir')
        jobname = self.get('jobname')

        try:
            alljobs = os.listdir(dirname + "/" + design)
            if self.get('jobincr'):
                jobid = 0
                for item in alljobs:
                    m = re.match(jobname+r'(\d+)', item)
                    if m:
                        jobid = max(jobid, int(m.group(1)))
                jobid = jobid + 1
                self.set('jobid', jobid)
        except FileNotFoundError:
            pass

################################################################################
# Annoying helper classes

class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)

class RawFormatter(HelpFormatter):
    def _fill_text(self, text, width, indent):
        return "\n".join([textwrap.fill(line, width) for line in textwrap.indent(textwrap.dedent(text), indent).splitlines()])

################################################################################
def get_permutations(base_chip, cmdlinecfg):
    '''Helper method to generate one or more Chip objects depending on
       whether a permutations file was passed in.
    '''

    chips = []
    cmdkeys = cmdlinecfg.keys()

    # Set default target if not set and there is nothing set
    if not base_chip.get('target'):
        base_chip.logger.info('No target set, setting to %s','freepdk45_asicflow')
        base_chip.set('target', 'freepdk45_asicflow')

    # Assign a new 'job_hash' to the chip if necessary.
    if not base_chip.get('remote', 'hash'):
        job_hash = uuid.uuid4().hex
        base_chip.set('remote', 'hash', job_hash)

    loglevel = cmdlinecfg['loglevel'] \
        if 'loglevel' in cmdkeys else "INFO"

    # Fetch the generator for multiple job permutations if necessary.
    if 'permutations' in cmdkeys:
        # TODO: should there be different behavior for >1 permutations file?
        perm_path = os.path.abspath(cmdlinecfg['permutations'][0])
        perm_script = SourceFileLoader('job_perms', perm_path).load_module()
        perms = perm_script.permutations(base_chip.cfg)
    else:
        perms = [base_chip.cfg]

    # Set '-remote_start' to '-start' if only '-start' is passed in at cmdline.
    if (not 'remote_start' in cmdkeys) and \
       ('start' in cmdkeys):
        base_chip.set('remote', 'start', cmdlinecfg['start'])
        base_chip.set('start', cmdlinecfg['start'])
    # Ditto for '-remote_stop' and '-stop'.
    if (not 'remote_stop' in cmdkeys) and \
       ('stop' in cmdkeys):
        base_chip.set('remote', 'stop', cmdlinecfg['stop'])
        base_chip.set('stop', cmdlinecfg['stop'])
    # Mark whether a local 'import' stage should be run.
    base_chip.status['local_import'] = (not base_chip.get('start') or \
                                       (base_chip.get('start') == 'import'))

    # Fetch an initial 'jobid' value for the first permutation.
    base_chip.set_jobid()
    cur_jobid = base_chip.get('jobid')
    base_chip.cfg['jobid']['value'] = None
    perm_ids = []

    # Create a new Chip object with the same job hash for each permutation.
    for chip_cfg in perms:
        new_chip = Chip(loglevel=loglevel)

        # JSON dump/load is a simple way to deep-copy a Python
        # dictionary which does not contain custom classes/objects.
        new_chip.status = json.loads(json.dumps(base_chip.status))
        new_chip.cfg = json.loads(json.dumps(chip_cfg))

        # Avoid re-setting values if the Chip was loaded from an existing config.
        if not 'cfg' in cmdkeys:
            # Set values for the new Chip's PDK/target.
            new_chip.target()

        # Skip the 'import' stage for remote jobs; it will be run locally and uploaded.
        if new_chip.get('remote', 'addr'):
            new_chip.set('start', new_chip.get('remote', 'start'))
            new_chip.set('stop', new_chip.get('remote', 'stop'))
        elif new_chip.get('remote', 'key'):
            # If 'remote_key' exists without 'remote_addr', it represents an
            # encoded key string in an ongoing remote job. It should be
            # moved from the config dictionary to the status one to avoid logging.
            new_chip.status['decrypt_key'] = new_chip.get('remote', 'key')
            new_chip.cfg['remote']['key']['value'] = []

        # Set and increment the "job ID" so multiple chips don't share the same directory.
        new_chip.set('jobid', int(cur_jobid))
        perm_ids.append(cur_jobid)
        cur_jobid = str(int(cur_jobid) + 1)

        chips.append(new_chip)

    # Mark permutations associated with the job in each Chip object.
    for chip in chips:
        chip.status['perm_ids'] = perm_ids

    # Done; return the list of Chips.
    return chips
