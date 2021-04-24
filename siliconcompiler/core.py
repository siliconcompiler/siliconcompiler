# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import aiohttp
import asyncio
import subprocess
import os
import sys
import re
import json
import logging as log
import hashlib
import time
import webbrowser
import yaml
import shutil
import copy
import importlib
import glob
import pandas
import code
import textwrap

from importlib.machinery import SourceFileLoader

from siliconcompiler.client import remote_run
from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_layout
from siliconcompiler.schema import schema_path
from siliconcompiler.schema import schema_istrue

class Chip:
    """Siliconcompiler configuration and flow tracking class"""

    ####################
    def __init__(self, loglevel="DEBUG"):
        '''Initializes Chip object

        Args:
            loglevel (str): Level of debugging
        '''

        # Create a default dict ("spec")
        self.cfg = schema_cfg()
        self.layout = schema_layout()
        
        # Initialize logger
        self.logger = log.getLogger()
        self.handler = log.StreamHandler()
        self.formatter = log.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(str(loglevel))

        # Special tracking variable for async run status. This could
        # go in the config dictionary, but internal thread states don't
        # need to be exposed to TCL scripts / etc.
        self.active_thread = None

        # Set Environment Variable if not already set
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        rootdir =  re.sub('siliconcompiler/siliconcompiler',
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

        self.logger.debug("Python search path set to %s", sys.path)
        self.logger.debug("SC search path set to %s", os.environ['SCPATH'])     
        
        # Copy 'defvalue' to 'value'
        self.reset()

        # Status placeholder dictionary
        # TODO, should be defined!
        self.status =  {}

    ###################################
    def target(self):
        '''Searches the SCPATH and PYTHON path for setup modules that match
        the target string. The setup string 
        
        config values based on a named target. 

        '''

        #Selecting fpga or asic mode
        mode = self.get('mode')
            
        # Checking that target is the right format
        # <process/device>
        # <process/device>_<eda>

        targetlist = str(self.get('target')[0]).split('_')
        platform = targetlist[0]

        #Load Platform (PDK or FPGA)
        try:
            packdir = "asic.targets"
            self.logger.debug("Loading platform module %s from %s", platform, packdir)
            module = importlib.import_module('.'+platform, package=packdir)
        except ImportError:
            packdir = "fpga.targets"
            self.logger.debug("Loading platform module %s from %s", platform, packdir)
            module = importlib.import_module('.'+platform, package=packdir)

        setup_platform = getattr(module,"setup_platform")
        setup_platform(self)

        # Load library target definitions for ASICs
        # Note the default fpga/asic flow when eda is left out in target name
        mode = self.cfg['mode']['value'][-1]
        if  len(targetlist) == 2:
            edaflow = targetlist[1]
        else:
            edaflow = mode

        if mode == 'asic':
            setup_libs = getattr(module,"setup_libs")
            setup_libs(self)
            setup_design = getattr(module,"setup_design")
            setup_design(self)

        #Load EDA
        packdir = "eda.targets"
        self.logger.debug("Loading EDA module %s from %s", edaflow, packdir)        
        module = importlib.import_module('.'+edaflow, package=packdir)
        setup_eda = getattr(module,"setup_eda")
        setup_eda(self, name=platform)

   
    ###################################
    def help(self,  *args, file=None, mode='full'):
        '''Prints help of a parameter
        '''

        self.logger.debug('Fetching help for %s', args)

        #Fetch Values
        description = self.search(self.cfg, *args, mode='get', field='short_help')
        param = self.search(self.cfg, *args, mode='get', field='param_help')
        typestr = ' '.join(self.search(self.cfg, *args, mode='get', field='type'))
        defstr = ' '.join(self.search(self.cfg, *args, mode='get', field='defvalue'))
        requirement = self.search(self.cfg, *args, mode='get', field='requirement')
        helpstr = self.search(self.cfg, *args, mode='get', field='help')
        example = self.search(self.cfg, *args, mode='get', field='example')
    
        #Removing multiple spaces and newlines
        helpstr = helpstr.rstrip()
        helpstr = helpstr.replace("\n","")
        helpstr = ' '.join(helpstr.split())
        
        #Removing extra spaces in example string
        cli = ' '.join(example[0].split())
        
        for idx, item in enumerate(example):
            example[idx] = ' '.join(item.split())
            example[idx] = example[idx].replace(", ",",")
        
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
        outlst = [param.replace("<dir>","\<dir\>"),
                  description,
                  typestr,
                  requirement,
                  defstr]
        shortstr = " | {: <52} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlst)

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
            

    ###################################
    def get(self, *args):
        '''Gets value in the Chip configuration dictionary

        Args:
            args (string): Configuration parameter to fetch

        Returns:
            list: List of Chip configuration values

        '''
        self.logger.debug('Reading config dictionary value: %s', args)

        keys = list(args)
        for k in keys:
            if isinstance(k, list):
                self.logger.critical("List keys not allowed, key=%s. Dictionary keys should be strings!", k)
                sys.exit()
        return self.search(self.cfg, *args, mode='get')

    ###################################
    def getkeys(self, *args):
        '''Gets all keys for the specified Chip args

        Args:
            args (string): Configuration keys to quqery

        Returns:
            list: List of Chip configuration values

        '''
        self.logger.debug('Retrieving config dictionary keys: %s', args)

        if len(list(args)) > 0:        
            keys = list(self.search(self.cfg, *args, mode='getkeys'))
            if 'default' in keys:
                keys.remove('default')
        else:
            keys = list(self.allkeys(self.cfg))
        
        return keys

    ###################################
    def allkeys(self, cfg, keys=None, allkeys=None):
        if keys is None:
            allkeys = []
            keys = []
        for k in cfg:
            newkeys =  keys.copy()
            newkeys.append(k)
            if 'defvalue' in cfg[k]:
                allkeys.append(newkeys)
            else:
                self.allkeys(cfg[k],keys=newkeys, allkeys=allkeys)
        return allkeys
    ####################################
    def add(self, *args):
        '''Sets a value in the Chip configuration dictionary 
        '''
        self.logger.debug('Adding config dictionary value: %s', args)
                
        all_args = list(args)
        
        # Convert val to list if not a list
        if type(all_args[-1]) != list:
            all_args[-1] = [str(all_args[-1])]

        return self.search(self.cfg, *all_args, mode='add')

    ####################################
    def set(self, *args):
        '''Sets a value in the Chip configuration dictionary 
        '''
        self.logger.debug('Setting config dictionary value: %s', args)
                
        all_args = list(args)
    
        # Convert val to list if not a list
        if type(all_args[-1]) != list:
            all_args[-1] = [all_args[-1]]

        return self.search(self.cfg, *all_args, mode='set')
    
    ##################################
    def search(self, cfg, *args, field='value', mode='get'):
        '''Recursively searches the nested dictionary for a key match

        Args:
            keys (string): Keys to match to.
            value (list): List to replace match with if mode is set
            mode (string): None, extend,replace
        
        Returns:
            list: Returns list if match is found

        '''

        all_args = list(args)
        param = all_args[0]
        val = all_args[-1]
        #set/add leaf cell (all_args=(param,val))
        if ((mode in ('set', 'add')) & (len(all_args) == 2)):
            #making an 'instance' of default if not found
            if not (param in cfg):
                if not ('default' in cfg):
                    self.logger.error('Search failed, \'%s\' is not a valid key', param)
                else:
                    cfg[param] = copy.deepcopy(cfg['default'])
            #setting or extending value based on set/get mode
            if not (field in cfg[param]):
                self.logger.error('Search failed, \'%s\' is not a valid leaf cell key', param)
                sys.exit()
            if(mode=='set'):
                cfg[param][field] = val
            else:
                cfg[param][field].extend(val)
            return cfg[param][field]
        #get leaf cell (all_args=param)
        elif (len(all_args) == 1):
            if(mode=='getkeys'):
                return cfg[param].keys()
            else:
                if not (field in cfg[param]):
                    self.logger.error('Key error, leaf param not found %s', field)
                return cfg[param][field]
        #if not leaf cell descend tree
        else:
            ##copying in default tree for dynamic trees
            if not (param in cfg):
                cfg[param] = copy.deepcopy(cfg['default'])
            all_args.pop(0)
            return self.search(cfg[param], *all_args, field=field, mode=mode)

    ##################################
    def prune(self, cfg=None, top=True):  
        '''Prunes all empty branches from cfg. Modifies the original config
        '''

        #10 should be enough for anyone...
        maxdepth = 10
        i=0
        
        if cfg is None:
            cfg = copy.deepcopy(self.cfg)
      
        #When at top of tree loop maxdepth times to make sure all stale
        #branches have been removed, not eleagnt, but stupid-simple
        while(i < maxdepth):
            #Loop through all keys starting at the top
            for k in list(cfg.keys()):
                #print(k)
                #removing all default/template keys
                if k == 'default':
                    del cfg[k]
                #remove long help from printing
                elif 'help' in cfg[k].keys():
                    del cfg[k]['help']
                #removing empty values from json file
                elif 'value' in cfg[k].keys():
                    if not cfg[k]['value']:
                        del cfg[k]
                #removing stale branches
                elif not cfg[k]:
                    cfg.pop(k)
                #keep traversing tree
                else:
                    self.prune(cfg[k], top=False)
            if(top):
                i+=1
            else:
                break
        return cfg
    
    ##################################
    def slice(self, key1, key2, cfg=None, result=None):
        '''Returns list of all vals matchinng key1 and key2
        '''
        # Using self if cfg is not specified
        if cfg is None:
            cfg = self.cfg
        # Special recursion entry conditon
        # #1.init list
        # #2.select key1 sub tree
        if result is None:
            self.logger.debug('Retrieving dictionary slice from %s and %s:', key1, key2)
            result = []
            cfg = cfg[key1]
        for k,v in cfg.items():
            if isinstance(v, dict):
                if k == key2:
                    result.extend(cfg[key2]['value'])
                else:
                    self.slice(key1, key2, cfg=cfg[k], result=result)
        return result

    ##################################
    def abspath(self, cfg):
        '''Resolves all configuration paths to be absolute paths
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
                    if cfg[k]['type'][-1] in  ('file', 'dir'):
                        for i, v in enumerate(cfg[k]['value']):
                            #Look for relative paths in search path
                            cfg[k]['value'][i] = schema_path(v)
                else:
                    self.abspath(cfg[k])
    
    ##################################
    def printcfg (self, cfg, keys=None, file=None, mode="", field='value', prefix=""):
        '''Prints out flattened dictionary in various formats. Formats supported
        include tcl, csv, md
        '''
        if keys is None:
            keys = []
        for k in cfg:
            newkeys =  keys.copy()
            newkeys.append(k)
            #detect leaf cell
            if 'defvalue' in cfg[k]:               
                if mode=='tcl':
                    for i, val in enumerate(cfg[k][field]):
                        #replace $VAR with env(VAR) for tcl
                        m = re.match('\$(\w+)(.*)', val)
                        if m:
                            cfg[k][field][i] = ('$env(' +
                                                m.group(1) +
                                                ')' +
                                                m.group(2))
                    #create a TCL dict
                    keystr = ' '.join(newkeys)
                    valstr = ' '.join(cfg[k][field])
                    outlst = [prefix,
                              keystr,
                              '[list ',
                              valstr,']']
                    outstr = ' '.join(outlst)
                    outstr = outstr + '\n'
                elif mode == 'md':
                    #create a comma separated file
                    keystr = ' '.join(newkeys)
                    valstr = ' '.join(cfg[k][field])
                    typestr = ' '.join(cfg[k]['type'])
                    defstr  = ' '.join(cfg[k]['defvalue'])
                    #Need to escape dir to get pdf to print in pandoc?
                    outlst = [cfg[k]['param_help'].replace("<dir>","\<dir\>"),
                              cfg[k]['short_help'],
                              typestr,
                              cfg[k]['requirement'],
                              defstr]
                    outstr = " | {: <52} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlst)
                if file is None:
                    print(outstr)
                else:
                    print(outstr, file=file)
            else:
                self.printcfg(cfg[k], keys=newkeys, file=file, mode=mode, field=field, prefix=prefix)

    ##################################
    def mergecfg(self, d2, d1=None):
        '''Merges dictionary with the Chip configuration dictionary
        '''
        if d1 is None:
            d1 = self.cfg
        for k, v in d2.items():
            #Checking if dub dict exists in self.cfg and new dict
            if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], dict):
                #if we reach a leaf copy d2 to d1
                if 'value' in d1[k].keys():
                    #only add items that are not in the current list
                    new_items = []
                    for i in range(len(d2[k]['value'])):
                        if(d2[k]['value'][i] not in d1[k]['value']):
                           new_items.append(d2[k]['value'][i])
                    d1[k]['value'].extend(new_items)
                #if not in leaf keep descending
                else:
                    self.mergecfg(d2[k], d1=d1[k])
            #if a new d2 key is found do a deep copy
            else:
                d1[k] = d2[k].copy()
    
    ###################################
    def check(self, group=None):
        '''Checks all values set in Chip configuration for legality.
        Also checks for missing values.

        Args:
            group (string): fpga, pdk, libs, eda, design

        Returns:
            : Status (pending, running, done, or error)

        '''

        error = 1

        #-check 
        #


        
        #1. Check for missing combinations
        #!(def-file | floorplan | (diesze & coresize)

        # notechlef
        # no site
        # no targetlib        
        # no libarch
        # no stackup

        #if no errors
        
        #Exit on error
        error = 0
        if error:
            sys.exit()
        
    #################################
    def readcfg(self, filename):
        '''Reads a json formatted config file into the Chip current Chip
        configuration

        Args:
            filename (string): Input filename. File-suffix indicates format
                               (json, yaml, tcl, mk)
            keymap (dict): Translates Chip configuration key names to a new set
                           of names based on a key lookup.x

        Returns:
            dict: Returns a dictionary found in JSON file for all keys found in
                  in the current Chip configuration

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
            
        #Rename dictionary based on keymap
        #Customize based on the types
        if not self.cfg_locked:
            #Merging arguments with the Chip configuration
            self.mergecfg(read_args)
        else:
            self.logger.error('Trying to change configuration while locked')

        if self.cfg['lock']['value'] == "True":
            self.cfg_locked = True

    ##################################
    def writecfg(self, filename, cfg=None, prune=True, abspath=False, keymap=[]):
        '''Writes out the current Chip configuration dictionary to a file

        Args:
            filename (string): Output filename. File-suffix indicates format
                               (json, yaml, csv, md)

        '''

        filepath = os.path.abspath(filename)
        self.logger.debug('Writing configuration to file %s', filepath)

        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        #prune cfg if option set
        if cfg is not None:
            cfgcopy = copy.deepcopy(cfg)
        elif prune:
            cfgcopy = self.prune()
        else:
            cfgcopy = copy.deepcopy(self.cfg)
            
        #resolve absolute paths
        if abspath:
            self.abspath(cfgcopy)
            
        # Write out configuration based on file type
        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                print(json.dumps(cfgcopy, sort_keys=True, indent=4), file=f)
        elif filepath.endswith('.yaml'):
            with open(filepath, 'w') as f:
                print("#############################################", file=f)
                print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
                print("#############################################", file=f)
                print(yaml.dump(cfgcopy, Dumper=YamlIndentDumper, default_flow_style=False), file=f)
                #print(yaml.dump(cfgcopy, sort_keys=True, indent=4), file=f)
        elif filepath.endswith('.tcl'):
            with open(filepath, 'w') as f:
                print("#############################################", file=f)
                print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
                print("#############################################", file=f)
                self.printcfg(cfgcopy, mode="tcl", prefix="dict set sc_cfg", file=f)
        elif filepath.endswith('.md'):
            with open(filepath, 'w') as f:
                outlist = ['param', 'desription', 'type', 'required', 'default', 'value']
                outstr = " | {: <52} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlist)
                print(outstr, file=f)
                outlist = [':----',
                           ':----',
                           ':----',
                           ':----',
                           ':----']
                outstr = " | {: <52} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlist)
                print(outstr, file=f)
                self.printcfg(cfgcopy, mode='md', field='requirement' , file=f)
        elif filepath.endswith('.doc'):
            with open(filepath, 'w') as f:
                self.printcfg(cfgcopy, mode='doc', field='value' , file=f)
        else:
            self.logger.error('File format not recognized %s', filepath)
            
    ##################################
    def lock(self):
        '''Locks the Chip configuration to prevent unwarranted configuration
        updates. Copies defvalue into value if value is not set.
        
        '''
        self.cfg_locked = True

    ##################################
    def reset(self,cfg=None):
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
                    cfg[k]['value'] = cfg[k]['defvalue'].copy()
                else:
                    self.reset(cfg=cfg[k])

    ##################################
    def wait(self, step=None):
        '''Waits for specific step to complete
        '''

        if step is None:
            steplist = self.get('steplist')
        else:
            steplist = [step]

        while True:
            busy = False
            for step in steplist:
                if schema_istrue(self.cfg['status'][step]['active']):
                    self.logger.info("Step '%s' is still active", step)
                    busy = True
            if busy:
                #TODO: Change this timeout
                self.logger.info("Waiting 10sec for step to finish")
                time.sleep(10)
            else:
                break
        
    ##################################
    def hash(self, cfg=None):
        '''Creates hashes for all files sourced by Chip class

        '''
        #checking to see how much hashing to do
        hashmode = self.cfg['hashmode']['value'][-1]   
        if hashmode != 'NONE':
            if cfg is None:
                self.logger.info('Computing file hashes with mode %s', hashmode)
                cfg = self.cfg
            #Recursively going through dict
            for k, v in cfg.items():
                if isinstance(v, dict):
                    #indicates leaf cell/file to act on
                    if 'hash' in cfg[k].keys():
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
        
    ##################################
    def compare(self, file1, file2):
        '''Compares Chip configurations contained in two different json files
        Useful??

        '''

        #TODO: Solve recursively
        
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

        same = True
        for key in self.cfg:
            # check that both files have all the keys
            # checking that all values and scalars are identical
            # list compare implicitly checks for list lengths as well
            if (key in file1_args) & (key in file2_args):
                if self.cfg[key]['type'] in {"list", "file"}:
                    #seems that sort needs to be done before doing list compare?
                    #can't be combined?
                    file1_args[key]['values'].sort()
                    file2_args[key]['values'].sort()
                    if file1_args[key]['values'] != file2_args[key]['values']:
                        same = False
                        self.logger.error('File difference found for key %s', key)
                    if self.cfg[key]['type'] in {"file"}:
                        file1_args[key]['hash'].sort()
                        file2_args[key]['hash'].sort()
                        if file1_args[key]['hash'] != file2_args[key]['hash']:
                            same = False
                            self.logger.error('Comparison difference for key %s',
                                              key)
                elif file1_args[key]['values'] != file2_args[key]['values']:
                    same = False
                    self.logger.error('Comparison difference found for key %s',
                                      key)
            else:
                same = False

        return same


    

    ###################################
    def audit(self, filename=None):
        '''Performance an an audit of each step in the flow
        '''
      
        
        
        
        pass

    ###################################
    def summary(self, filename=None):
        '''Creates a summary dictionary of the results of the specified step
        and jobid

         Args:
            step: The step to report on (eg. cts)
            jobid: Index of job to report on (1, 2, etc)
        '''
        
        info = '\n'.join(["SUMMARY:\n",
                          "design = "+self.get('design')[0],
                          "foundry = "+self.get('pdk', 'foundry')[0],
                          "process = "+self.get('pdk', 'process')[0],
                          "targetlibs = "+" ".join(self.get('asic','targetlib'))])
        
        print("-"*135)
        print(info, "\n")

        steplist = self.get('steplist')
        start = self.get('start')[-1]
        stop = self.get('stop')[-1]
        startindex = steplist.index(start)
        stopindex = steplist.index(stop)
       
        #Creating step index
        data = []
        steps = []
        colwidth = 8
        #Creating header row
        for stepindex in range(startindex, stopindex + 1):
            step = steplist[stepindex]
            steps.append(step.center(colwidth))

        #Creating bulk
        metrics = []
        for metric in  self.getkeys('real', 'default'):
            metrics.append(" " + metric)
            row = []
            for stepindex in range(startindex, stopindex + 1):
                step = steplist[stepindex]
                row.append(" " +
                           str(self.get('real', step, metric)[-1]).center(colwidth))
            data.append(row)

        pandas.set_option('display.max_rows', 500)
        pandas.set_option('display.max_columns', 500)
        pandas.set_option('display.width', 100)
        df = pandas.DataFrame(data, metrics, steps)
        if filename is None:
            print(df.to_string())
            print("-"*135)
            
    ###################################
    def display(self, *args, index=0):
      '''Displays content related keys provided  
        '''
      self.logger.info('Displaying file contents: %s', args)

      EDITOR = os.environ.get('EDITOR')
      
      cfgtype = self.search(self.cfg, *args, field="type")
      if(str(cfgtype[0]) == 'file'):
          filename = self.search(self.cfg, *args )
          cmd = EDITOR + " " + filename[index]
          error = subprocess.run(cmd, shell=True)

    ###################################
    def start_async_run(self, start=None, stop=None, jobid=None):
        '''Helper method to start an asynchronous 'run' command, and update
           a tracking semaphore when it starts/finishes.
        '''
        loop = asyncio.get_event_loop()
        self.active_thread = loop.create_task(self.run(start=start,
                                                       stop=stop,
                                                       jobid=jobid))

    ###################################
    async def run(self, start=None, stop=None, jobid=None):

        '''The common execution method for all compilation steps compilation
        flow. The job executes on the local machine by default, but can be
        execute as a remote job as well. If executed in synthconorus mode, the
        run command waits at the end of the function call before returning to
        main. If the job is executed in async mode, flags are set in the Class
        state and the function cal returns to main.
        '''
               
        ###########################
        # Run Setup
        ###########################

        remote = len(self.cfg['remote']['value']) > 0
        steplist = self.cfg['steplist']['value']
        buildroot = str(self.cfg['dir']['value'][-1])
        design = str(self.cfg['design']['value'][-1])

        cwd = os.getcwd()
        
        ###########################
        # Jobdir
        ###########################
        
        if (len(self.cfg['jobname']['value']) > 0):
            jobname = self.cfg['jobname']['value'][-1]
        else:
            alljobs = os.listdir(buildroot +
                                 "/" +
                                 design)
            jobid = 0   
            for item in alljobs:
                m = re.match('job(\d+)', item)
                if m:
                    jobid = max(jobid, int(m.group(1)))
            jobid = jobid+1
            jobname = "job" + str(jobid)

        ###########################
        # Defining Pipeline
        ###########################

        if start is None:
            start = self.get('start')[-1]
        if stop is None:
            stop = self.get('stop')[-1]

        startindex = steplist.index(start)
        stopindex = steplist.index(stop)

        ###########################
        # Execute pipeline
        ###########################
        for stepindex in range(startindex, stopindex + 1):
                        
            #step lookup (active state!)
            step = steplist[stepindex]
            laststep = steplist[stepindex-1]           
            importstep = (stepindex==0)

            #update step status
            self.set('status', 'step', step)
            
            if step not in steplist:
                self.logger.error('Illegal step name %s', step)
                sys.exit()

            #####################
            # Job Directory
            #####################

            jobdir = '/'.join([buildroot,
                               design,
                               jobname,
                               step])
                                   
            #####################
            # Dynamic EDA setup
            #####################
            
            vendor = self.cfg['flow'][step]['vendor']['value'][-1]
            packdir = "eda." + vendor
            modulename = '.'+vendor+'_setup'
            module = importlib.import_module(modulename, package=packdir)
        
            #####################
            # Init Metrics Table
            #####################
            for metric in self.getkeys('real', 'default'):
                self.add('real', step, metric, 0)

            #####################
            # Execution
            #####################
            if ((step in self.cfg['skip']['value']) |
                (self.cfg['skipall']['value'][-1] =='true')):
                self.logger.info('Skipping step: %s', step)
            else:
                self.logger.info("Running step '%s' in dir '%s'", step, jobdir)  
                # Copying in Files (local only)
                if os.path.isdir(jobdir) and (not remote):
                    shutil.rmtree(jobdir)
                os.makedirs(jobdir, exist_ok=True)
                os.chdir(jobdir)
                os.makedirs('outputs', exist_ok=True)
                os.makedirs('reports', exist_ok=True)
                # First stage after import always copies from same place
                if stepindex==0:
                    pass
                elif not remote:
                    shutil.copytree("../"+laststep+"/outputs", 'inputs')
                
                #Copy Reference Scripts
                if schema_istrue(self.cfg['flow'][step]['copy']['value']):
                    refdir = schema_path(self.cfg['flow'][step]['refdir']['value'][-1])                    
                    shutil.copytree(refdir,
                                    ".",
                                    dirs_exist_ok=True)
                
                #####################
                # Save CFG locally
                #####################

                self.writecfg("sc_schema.json")
                self.writecfg("sc_schema.yaml")
                self.writecfg("sc_schema.tcl", abspath=True)

                #####################
                # Generate CMD
                #####################

                #Set Executable
                exe = self.cfg['flow'][step]['exe']['value'][-1] #scalar
                cmd_fields = [exe]

                #Add options to cmd list
                setup_options = getattr(module,"setup_options")
                options = setup_options(self, step)
                cmd_fields.extend(options)        

                #Resolve Paths
                #TODO: Fix this later, still using abspaths..
                #with local copy, should copy in top level script and
                #source from local directory,
                #onnly keep the end of the file?
                for value in self.cfg['flow'][step]['script']['value']:
                    abspath = schema_path(value)
                    cmd_fields.append(abspath)

                #Piping to log file
                logfile = exe + ".log"
                
                if (schema_istrue(self.cfg['quiet']['value'])) & (step not in self.cfg['bkpt']['value']):
                    cmd_fields.append("> " + logfile)
                else:
                    cmd_fields.append(" 2>&1 | tee " + logfile)

                #Final command line
                cmd = ' '.join(cmd_fields)

                #Create run file
                with open("run.sh", 'w') as f:
                    print("#!/bin/bash", file=f)
                    print(cmd, file=f)
                f.close()
                os.chmod("run.sh", 0o755)
                #####################
                # Execute
                #####################
                if (stepindex != 0) and remote:
                    self.logger.info('Remote server call')
                    await remote_run(self, step)
                else:
                    # Local builds must be processed synchronously, because
                    # they use calls such as os.chdir which are not thread-safe.
                    # Tool Pre Process
                    pre_process = getattr(module,"pre_process")
                    pre_process(self,step)

                    # Tool Executable
                    self.logger.info('%s', cmd)
                    error = subprocess.run(cmd, shell=True)
                    if error.returncode:
                        self.logger.error('Command failed. See log file %s',
                                          os.path.abspath(logfile))
                        sys.exit()

                    # Tool Post Process
                    post_process = getattr(module,"post_process")
                    post_process(self, step)
                    #Drop into python shell if command line tool
                    if step in self.cfg['bkpt']['value']:
                        format = self.cfg['flow'][step]['format']['value'][0]
                        print(format)
                        if format=='cmdline':
                            code.interact(local=dict(globals(), **locals()))
                    
            ########################
            # Return to $CWD
            ########################       
            os.chdir(cwd)

        # Mark completion of async run if applicable.
        self.active_thread = None
 

############################################
# Annoying helper class b/c yaml..
# Do we actually have to support a class?
class YamlIndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(YamlIndentDumper, self).increase_indent(flow, False)

########################
def get_permutations(base_chip, cmdlinecfg):
    '''Helper method to generate one or more Chip objects depending on
       whether a permutations file was passed in.
    '''

    chips = []
    if 'permutations' in cmdlinecfg.keys():
        perm_path = os.path.abspath(cmdlinecfg['permutations']['value'][-1])
        perm_script = SourceFileLoader('job_perms', perm_path).load_module()
        jobid = 0
        loglevel = cmdlinecfg['loglevel']['value'][-1] \
            if 'loglevel' in cmdlinecfg.keys() else "INFO"
        # Create a new Chip object with the same job hash for each permutation.
        for chip_cfg in perm_script.permutations(base_chip.cfg):
            new_chip = Chip(loglevel=loglevel)
            # JSON dump/load is a simple way to deep-copy a Python
            # dictionary which does not contain custom classes/objects.
            new_chip.status = json.loads(json.dumps(base_chip.status))
            new_chip.cfg = json.loads(json.dumps(chip_cfg))
            # set incrementing job IDs to avoid overwriting other jobs.
            for step in new_chip.cfg['steplist']['value']:
                new_chip.set('status', step, 'jobid', str(jobid))
            if 'remote' in cmdlinecfg.keys():
                new_chip.set('start', 'syn')
            chips.append(new_chip)
            jobid = jobid + 1
    else:
        # If no permutations script is configured, simply run the design once.
        chips.append(base_chip)

    # Done; return the list of Chips.
    return chips

