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


from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_layout
from siliconcompiler.schema import schema_path
from siliconcompiler.schema import schema_istrue
from siliconcompiler.setup import setup_cmd

class Chip:
    """
    The core class for the siliconcompiler package with central control of
    compilation configuration and state tracking. The class includes a
    a collection of suport methods operating on the class attributes

    Parameters
    ----------
    loglevel (string) : Level of debugging (DEBUG, INFO, WARNING, ERROR)

    Attributes
    ----------
    cfg (dict): Configuration dictionary
    status (dict) : Step and job ID based status dictionary

    """

    ####################
    def __init__(self, loglevel="DEBUG"):
        '''
        Init method for Chip object

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
        
        # Set Environment Variable if not already set
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        rootdir =  re.sub('siliconcompiler/siliconcompiler',
                          'siliconcompiler',
                          scriptdir)

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
        
        # Instance starts unlocked
        self.cfg_locked = False

    ###################################
    def target(self, name):
        '''Loading config values based on a named target. 

        '''

        #Selecting fpga or asic mode
        mode = self.cfg['mode']['value'][-1]
            
        # Checking that target is the right format
        # <process/device>
        # <process/device>_<eda>
        
        targetlist = name.split('_')
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

        #Load library target definitions for ASICs
        mode = self.cfg['mode']['value'][-1]
        if  len(targetlist) == 2:
            edaflow = targetlist[1]
        else:
            edaflow = mode

        if mode == 'asic':
            setup_libs = getattr(module,"setup_libs")
            setup_libs(self)

        #Load EDA
        packdir = "eda.targets"
        self.logger.debug("Loading EDA module %s from %s", edaflow, packdir)        
        module = importlib.import_module('.'+edaflow, package=packdir)
        setup_eda = getattr(module,"setup_eda")
        setup_eda(self, name=platform)
        
    ###################################
    def get(self, *args):
        '''Gets value in the Chip configuration dictionary

        Args:
            args (string): Configuration parameter to fetch

        Returns:
            list: List of Chip configuration values

        '''
        self.logger.debug('Reading config dictionary value: %s', args)

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

        keys = list(self.search(self.cfg, *args, mode='getkeys'))

        if 'default' in keys:
            keys.remove('default')
        
        return keys

    ####################################
    def add(self, *args):
        '''Sets a value in the Chip configuration dictionary 
        '''
        self.logger.debug('Adding config dictionary value: %s', args)
                
        all_args = list(args)
        param = all_args[0]
        
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
        param = all_args[0]
    
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
        else:
            cfg = copy.deepcopy(cfg)

        #When at top of tree loop maxdepth times to make sure all stale
        #branches have been removed, not eleagnt, but stupid-simple
        while(i < maxdepth):
            #Loop through all keys starting at the top
            for k in list(cfg.keys()):
                #print(k)
                #removing all default/template keys
                if k == 'default':
                    del cfg[k]
                #delete all keys with empty/default values
                elif 'value' in cfg[k].keys():
                    if not cfg[k]['value']:
                        del cfg[k]
                #removing stale branches
                elif not cfg[k]:
                    cfg.pop(k)
                #keep traversing tree
                else:
                    self.prune(cfg=cfg[k], top=False)
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
    def rename(self, cfg, keymap):
        '''Creates a copy of the dictionary with renamed primary keys
        '''

        cfgout =  {}
        keydict = {}
        
        #Create a dynamic keymap from string pairs
        for string in keymap:
            k,v = string.split()
            keydict[k]=v
        #Cycle through all primary params and rename keys
        for key in cfg:
            if key in keymap:
                cfgout[keydict[key]] = cfg[key].copy()
                self.logger.debug('Keymap renaming from %s to %s', key, newkey)
            else:
                cfgout[key] = cfg[key].copy() 

        return cfgout
    
    ##################################
    def abspath(self,cfg=None):
        '''Resolves all configuration paths to be absolute paths
        '''
        #Setting initial dict so user doesn't have to
        if cfg is None:
            self.logger.debug('Creating absolute file paths')
            cfg = copy.deepcopy(self.cfg)
        #List of paths to search for files in to resolve
        scpaths = str(os.environ['SCPATH']).split()
        #Recursively going through dict to set abspaths for files
        for k, v in cfg.items():
            #print("abspath", k,v)
            if isinstance(v, dict):
                #indicates leaf cell
                if 'value' in cfg[k].keys():
                    #print("dict=",cfg[k])
                    #only do something if type is file
                    if cfg[k]['type'][-1] in  ('file', 'dir'):
                        for i, v in enumerate(cfg[k]['value']):
                            #Look for relative paths in search path
                            cfg[k]['value'][i] = schema_path(v)
                else:
                    self.abspath(cfg=cfg[k])
        return cfg
    
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
                    outlst = [cfg[k]['param_help'],
                              cfg[k]['short_help'],
                              typestr,
                              cfg[k]['requirement'],
                              defstr,
                              valstr]
                    outstr = " | {: <45} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlst)
                #print out content
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
        #!(def | floorplan | (diesze & coresize)

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
        
    ###################################
    def getstatus(self, step, jobid):
        '''Gets status of a job for a specific compilaton step

        Args:
            step (string): Step name to get status for
            jobid (int): Job index

        Returns:
            string: Status (pending, running, done, or error)

        '''

        return self.status[step][jobid]

    #################################
    def readenv(self):
        '''Reads Chip environment variables and copies them to the current
        configuration. Environment variables are assumed to be the upper case
        of the Chip parameters. For example, the parameter sc_foundry will be
        read as $env(SC_FOUNDRY).
        '''

        self.logger.debug('Reading environment variables')
        
        #TODO: Complete later
        for key in self.cfg.keys():
            var = os.getenv(key.upper())
            if var != None:
                self.cfg[key]['value'] = var

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
        self.logger.info('Writing configuration to file %s', filepath)

        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        #use self if no argument is specified
        if cfg is None:
            cfg = copy.deepcopy(self.cfg)
        else:
            cfg = copy.deepcopy(cfg)

        #prune if option is set
        if prune:
            cfg = self.prune()

        #rename parameters as needed
        if keymap:
            cfg = self.rename(cfg, keymap)

        #resolve absolute paths
        if abspath:
            cfg = self.abspath(cfg)
            
        # Write out configuration based on file type
        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                print(json.dumps(cfg, sort_keys=True, indent=4), file=f)
        elif filepath.endswith('.yaml'):
            with open(filepath, 'w') as f:
                print(yaml.dump(cfg, sort_keys=True, indent=4), file=f)
        elif filepath.endswith('.tcl'):
            with open(filepath, 'w') as f:
                print("#############################################", file=f)
                print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
                print("#############################################", file=f)
                self.printcfg(cfg, mode="tcl", prefix="dict set sc_cfg", file=f)
        elif filepath.endswith('.md'):
            with open(filepath, 'w') as f:
                outlist = ['param', 'desription', 'type', 'required', 'default', 'value']
                outstr = " | {: <45} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlist)
                print(outstr, file=f)
                outlist = [':----',
                          ':----',
                          ':----',
                          ':----',
                          ':----']
                outstr = " | {: <45} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlist)
                print(outstr, file=f)
                self.printcfg(cfg, mode='md', field='requirement' , file=f)  
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
    def sync(self, step, jobid):
        '''Waits for jobs for the step and jobid specified to complete
        Much work to do here!!

        '''
    ##################################
    def hash(self, cfg=None):
        '''Creates hashes for all files sourced by Chip class

        '''

        if cfg is None:
            self.logger.info('Computing hash values for all files')
            cfg = self.cfg

        #checking to see how much hashing to do
        hashmode = self.cfg['hash']['value'][-1]   
        if hashmode != 'NONE':
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
                        self.hash(cfg=cfg[k], mode=mode)
        
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
    def summary(self, step, jobid, filename=None):
        '''Creates a summary dictionary of the results of the specified step
        and jobid

         Args:
            step: The step to report on (eg. cts)
            jobid: Index of job to report on (1, 2, etc)
        '''
        return step

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
    def metrics(self, step):
        '''Extract metrics on a per step basis from logs.
        Likely strategy for implementtion includes.
        '''

        #1. Look at vendor platform
        #2. Based on target platform load wrapper
        #3. In wrapper load proprietary modules
        
        vendor = self.cfg['flow'][step]['vendor']['value'][-1]

        pass

    ###################################
    def run(self, step):
        '''The common execution method for all compilation steps compilation
        flow. The job executes on the local machine by default, but can be
        execute as a remote job as well. If executed in synthconorus mode, the
        run command waits at the end of the function call before returning to
        main. If the job is executed in async mode, flags are set in the Class
        state and the function cal returns to main.
        '''

        #####################
        # Run Setup
        ##################### 

        vendor = self.cfg['flow'][step]['vendor']['value'][-1]
        tool = self.cfg['flow'][step]['exe']['value'][-1]
        refdir = schema_path(self.cfg['flow'][step]['refdir']['value'][-1])
        
        steplist = self.cfg['steps']['value']
        stepindex = steplist.index(step)
        laststep = steplist[stepindex-1]
        start = steplist.index(self.cfg['start']['value'][-1]) #scalar
        stop = steplist.index(self.cfg['stop']['value'][-1]) #scalar
        skip = step in self.cfg['skip']['value']
        
        #####################
        # Dynamic Module Load
        #####################    

        module = importlib.import_module('.'+vendor,
                                         package="eda." + vendor)
        
        #####################
        # Conditional Execution
        #####################    

        if step not in steplist:
            self.logger.error('Illegal step name %s', step)
        elif (stepindex < start) | (stepindex > stop) | skip:
            self.logger.info('Skipping step: %s', step)
        else:
            self.logger.info('Running step: %s', step)

            #Updating jobindex
            jobid = int(self.cfg['flow'][step]['jobid']['value'][-1]) + 1

            #Moving to working directory
            jobdir = (str(self.cfg['dir']['value'][-1]) + #scalar
                      "/" +
                      str(step) +
                      "/job" +
                      str(jobid))

            #Creating Temporary Working Dir
            if os.path.isdir(jobdir):
                os.system("rm -rf " +  jobdir)
            os.makedirs(jobdir, exist_ok=True)
            cwd = os.getcwd()
            os.chdir(jobdir)

            #make output directories
            os.makedirs('outputs', exist_ok=True)
            os.makedirs('reports', exist_ok=True)

            #Create Logcal copuesLocal configuration files
            self.writecfg("sc_setup.json")
            self.writecfg("sc_setup.tcl", abspath=True)
            
            #Copy outputs from last step unless import                        
            if stepindex > 0:              
                lastjobid = self.cfg['flow'][laststep]['jobid']['value'][-1]
                lastdir = '/'.join(['../../',                
                                    steplist[stepindex-1],
                                    'job'+lastjobid,
                                    'outputs'])
                shutil.copytree(lastdir, 'inputs')
                
            #Copy Reference Scripts
            if schema_istrue(self.cfg['flow'][step]['copy']['value']):
                shutil.copytree(refdir,
                                ".",
                                dirs_exist_ok=True)
            
            #####################
            # Pre Process
            #####################

            pre_process = getattr(module,"pre_process")
            pre_process(self,step)

            #####################
            # Run Executable
            #####################

            cmd = self.getcmd(step)

            with open("run.sh", 'w') as f:
                print("#!/bin/bash", file=f)
                print(cmd, file=f)
            f.close()
            os.chmod("run.sh", 0o755)
            
            self.logger.info('%s', cmd)
            error = subprocess.run(cmd, shell=True)

            if error.returncode:
                self.logger.error('Command failed. See log file %s',
                                  os.path.abspath(logfile))
                sys.exit()

            #####################
            # Post Process
            #####################        
            
            #run tool specific post process
            post_process = getattr(module,"post_process")
            post_process(self, step)

            #Updating jobid when complete
            self.cfg['flow'][step]['jobid']['value'] = [str(jobid)]

            #Return to CWD
            os.chdir(cwd)

    ###################################
    def getcmd(self,step):

        #Set Executable
        exe = self.cfg['flow'][step]['exe']['value'][-1] #scalar
        cmd_fields = [exe]

        #Dynamically generate options
        vendor = self.cfg['flow'][step]['vendor']['value'][-1]
        tool  = self.cfg['flow'][step]['exe']['value'][-1]
        module = importlib.import_module('.'+vendor,
                                         package="eda." + vendor)
        setup_options = getattr(module,"setup_options")
        options = setup_options(self, step)

        #Add options to cmd list
        cmd_fields.extend(options)        

        #Resolve Paths
        if schema_istrue(self.cfg['flow'][step]['copy']['value']):
            for value in self.cfg['flow'][step]['script']['value']:
                abspath = schema_path(value)
                cmd_fields.append(abspath)
        else:
            for value in self.cfg['flow'][step]['script']['value']:
                cmd_fields.append(value)      

        #Piping to log file
        logfile = exe + ".log"
        if schema_istrue(self.cfg['quiet']['value']):
            cmd_fields.append("> " + logfile)
        else:
            cmd_fields.append("| tee " + logfile)
        cmd = ' '.join(cmd_fields)

        return cmd
