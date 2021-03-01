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

from siliconcompiler.schema import schema
from siliconcompiler.schema import schema_path
from siliconcompiler.schema import schema_istrue
from siliconcompiler.setup  import setup_cmd

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
    status (dict) : Stage and job ID based status dictionary

    """

    ####################
    def __init__(self, loglevel="DEBUG"):
        '''
        Init method for Chip object

        '''

        # Set Environment Variable if not already set
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        rootdir =  re.sub('siliconcompiler/siliconcompiler',
                          'siliconcompiler',
                          scriptdir)
        if os.getenv('SCPATH') == None:
            os.environ['SCPATH'] = rootdir
        elif not re.match(rootdir,os.environ['SCPATH']):  
            os.environ['SCPATH'] = rootdir + " " + str(os.environ['SCPATH'])
        # Adding current working directory to search path
        # don't duplicate if running out of install dir
        if not re.match(rootdir,str(os.getcwd())):   
            os.environ['SCPATH'] = os.getcwd() + " " + os.environ['SCPATH']            
        # Initialize logger
        self.logger = log.getLogger()
        self.handler = log.StreamHandler()
        self.formatter = log.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(str(loglevel))
       
        # Create a default dict 
        self.cfg = schema()

        # Copy 'defvalue' to 'value'
        self.reset()
        
        # Instance starts unlocked
        self.cfg_locked = False

        #Use built-in target
        self.builtin_target = False
        
        # Instance starts with all default stages in idle
        self.status = {}
        all_stages = (self.cfg['compile_stages']['defvalue'] +
                      self.cfg['dv_stages']['defvalue'])
        for stage in all_stages:
            self.status[stage] = ["idle"]

    ###################################
    def get(self, *args):
        '''Gets value in the Chip configuration dictionary

        Args:
            args (string): Configuration parameter to fetch

        Returns:
            list: List of Chip configuration values

        '''
        self.logger.info('Retrieving config dictionary value: %s', args)

        return self.search(self.cfg, *args, mode='get')

    ###################################
    def getkeys(self, *args):
        '''Gets all keys for the specified Chip args

        Args:
            args (string): Configuration keys to quqery

        Returns:
            list: List of Chip configuration values

        '''
        self.logger.info('Retrieving config dictionary keys: %s', args)

        keys = list(self.search(self.cfg, *args, mode='getkeys'))

        if 'default' in keys:
            keys.remove('default')
        
        return keys

    ####################################
    def add(self, *args):
        '''Sets a value in the Chip configuration dictionary 
        '''
        self.logger.info('Adding config dictionary value: %s', args)
                
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
        self.logger.info('Setting config dictionary value: %s', args)
                
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
        '''Prunes all empty branches from cfg
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
                #removing all default/template keys
                if k == 'default':
                    del cfg[k]
                #delete all keys with empty/default values
                elif 'value' in cfg[k].keys():
                    if ((not cfg[k]['value']) or
                        (cfg[k]['value'] == cfg[k]['defvalue'])):
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
            self.logger.info('Retrieving dictionary slice from %s and %s:', key1, key2)
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
                self.logger.info('Keymap renaming from %s to %s', key, newkey)
            else:
                cfgout[key] = cfg[key].copy() 

        return cfgout
    
    ##################################
    def abspath(self,cfg=None):
        '''Resolves all configuration paths to be absolute paths
        '''
        #Setting initial dict so user doesn't have to
        if cfg is None:
            self.logger.info('Creating absolute file paths')
            cfg = copy.deepcopy(self.cfg)
        #List of paths to search for files in to resolve
        scpaths = str(os.environ['SCPATH']).split()
        #Recursively going through dict to set abspaths for files
        for k, v in cfg.items():
            #print(k,v)
            if isinstance(v, dict):
                #indicates leaf cell
                if 'value' in cfg[k].keys():
                    #only do something if type is file
                    if(cfg[k]['type'][-1] == 'file'):
                        for i, v in enumerate(cfg[k]['value']):
                            #Look for relative paths in search path
                            cfg[k]['value'][i] = schema_path(v)
                else:
                    self.abspath(cfg=cfg[k])
        return cfg
    
    ##################################
    def printcfg (self, cfg, keys=None, f=None, mode="", field='value', prefix=""):
        '''Prints out flattened dictionary
        '''
        if keys is None:
            keys = []
        for k in cfg:
            newkeys =  keys.copy()
            newkeys.append(k)
            if 'value' in cfg[k]:
                keystr = ' '.join(newkeys)
                if (mode=='tcl'):
                    #replace $VAR with env(VAR)
                    for i, val in enumerate(cfg[k][field]):
                        m = re.match('\$(\w+)(.*)', val)
                        if m:
                            cfg[k][field][i] = ('$env(' +
                                                m.group(1) +
                                                ')' +
                                                m.group(2))
                    valstr = ' '.join(cfg[k][field])
                    outlst = [prefix,keystr,'[list ', valstr,']']
                    outstr = ' '.join(outlst)
                else:
                    valstr = ' '.join(cfg[k][field])
                    outlst = [prefix,keystr, valstr]
                    outstr = ' '.join(outlst)
                if f is None:
                    print(outstr+'\n')
                else:
                    print(outstr+'\n', file=f)
            else:
                self.printcfg(cfg[k], keys=newkeys, f=f, mode=mode, field=field, prefix=prefix)

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
    def getstatus(self, stage, jobid):
        '''Gets status of a job for a specific compilaton stage

        Args:
            stage (string): Stage name to get status for
            jobid (int): Job index

        Returns:
            string: Status (pending, running, done, or error)

        '''

        return self.status[stage][jobid]

    #################################
    def readenv(self):
        '''Reads Chip environment variables and copies them to the current
        configuration. Environment variables are assumed to be the upper case
        of the Chip parameters. For example, the parameter sc_foundry will be
        read as $env(SC_FOUNDRY).
        '''

        self.logger.info('Reading environment variables')
        
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

        self.logger.info('Reading configuration file %s', abspath)

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
    def writecfg(self, filename, mode=None):
        '''Writes out the current Chip configuration dictionary to a file

        Args:
            filename (string): Output filename. File-suffix indicates format
                               (json, yaml)

        '''

        filepath = os.path.abspath(filename)

        self.logger.info('Writing configuration to file %s', filepath)

        # Create option to only write out a dict with values set
        # value!=defvalue and not empty

        if mode == 'prune':
            cfg = self.prune(self.cfg)
        else:
            cfg = self.cfg

        # Write out configuration based on file type
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
            
        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                print(json.dumps(cfg, sort_keys=True, indent=4), file=f)
        elif filepath.endswith('.yaml'):
            with open(filepath, 'w') as f:
                print(yaml.dump(cfg, sort_keys=True, indent=4), file=f)
        else:
            self.logger.error('File format not recognized %s', filepath)
            
    ##################################
    def writetcl(self, filename, cfg=None, keymap=[]):
        '''Writes out the Chip cfg dictionary in TCL format

        Args:
            cfg (dict): Dictionary to print out in TCL format
            filename (string): Output filename.

        '''
        filepath = os.path.abspath(filename)
        
        self.logger.info('Writing configuration in TCL format: %s', filepath)
        
        #Prune CFG before writing out result
        if cfg is None:
            cfg = self.prune()

        #Resolve absolute paths (to simplify eda tcl code)
        cfg = self.abspath(cfg)

        #Renaming keys/attribute names before printing
        if(keymap):
            cfg = self.rename(cfg, keymap)
            
        # Writing out file
        with open(filepath, 'w') as f:
            print("#############################################", file=f)
            print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
            print("#############################################", file=f)
            self.printcfg(cfg, mode="tcl", prefix="dict set sc_cfg", f=f)
        f.close()  

    
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
            self.logger.info('Loading default values into Chip configuration')
            cfg = self.cfg
        for k, v in cfg.items():            
            if isinstance(v, dict):
                if 'defvalue' in cfg[k].keys():
                    cfg[k]['value'] = cfg[k]['defvalue'].copy()
                else:
                    self.reset(cfg=cfg[k])

    ##################################
    def sync(self, stage, jobid):
        '''Waits for jobs for the stage and jobid specified to complete
        Much work to do here!!

        '''
    ##################################
    def hash(self, cfg=None):
        '''Creates hashes for all files sourced by Chip class

        '''
        if cfg is None:
            self.logger.info('Computing hash values for all files')
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
    def summary(self, stage, jobid, filename=None):
        '''Creates a summary dictionary of the results of the specified stage
        and jobid

         Args:
            stage: The stage to report on (eg. cts)
            jobid: Index of job to report on (1, 2, etc)
        '''
        return stage

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
    def metrics(self, stage):
        '''Extract metrics on a per stage basis from logs.
        Likely strategy for implementtion includes.
        '''

        #1. Look at vendor platform
        #2. Based on target platform load wrapper
        #3. In wrapper load proprietary modules
        
        vendor = self.cfg['tool'][stage]['vendor']['value'][-1]

        pass

    ###################################
    def run(self, stage):
        '''The common execution method for all compilation stages compilation
        flow. The job executes on the local machine by default, but can be
        execute as a remote job as well. If executed in synthconorus mode, the
        run command waits at the end of the function call before returning to
        main. If the job is executed in async mode, flags are set in the Class
        state and the function cal returns to main.
        '''

        #####################
        # Run Setup
        ##################### 

        vendor = self.cfg['tool'][stage]['vendor']['value'][-1]
        tool = self.cfg['tool'][stage]['exe']['value'][-1]
        refdir = schema_path(self.cfg['tool'][stage]['refdir']['value'][-1])
        
        stages = (self.cfg['compile_stages']['value'] +
                  self.cfg['dv_stages']['value'])
        current = stages.index(stage)
        laststage = stages[current-1]
        start = stages.index(self.cfg['start']['value'][-1]) #scalar
        stop = stages.index(self.cfg['stop']['value'][-1]) #scalar
        skip = stage in self.cfg['skip']['value']

        #####################
        # Dynamic Module Load
        #####################    

        module = importlib.import_module('.'+tool,
                                         package="eda." + vendor)
        
        #####################
        # Conditional Execution
        #####################    

        if stage not in stages:
            self.logger.error('Illegal stage name %s', stage)
        elif (current < start) | (current > stop) | skip:
            self.logger.info('Skipping stage: %s', stage)
        else:
            self.logger.info('Running stage: %s', stage)

            #Updating jobindex
            jobid = int(self.cfg['tool'][stage]['jobid']['value'][-1]) + 1

            #Moving to working directory
            jobdir = (str(self.cfg['build']['value'][-1]) + #scalar
                      "/" +
                      str(stage) +
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
            self.writetcl("sc_setup.tcl")
            self.writecfg("sc_setup.json")
            
            #Copy outputs from last stage unless import                        
            if stage != "import":              
                lastjobid = self.cfg['tool'][laststage]['jobid']['value'][-1]
                lastdir = '/'.join(['../../',                
                                    stages[current-1],
                                    'job'+lastjobid,
                                    'outputs'])
                shutil.copytree(lastdir, 'inputs')
                
            #Copy Reference Scripts
            if schema_istrue(self.cfg['tool'][stage]['copy']['value']):
                shutil.copytree(refdir,
                                ".",
                                dirs_exist_ok=True)
            
            #####################
            # Pre Process
            #####################

            pre_process = getattr(module,"pre_process")
            pre_process(self,stage)

            #####################
            # Run Executable
            #####################

            cmd = setup_cmd(self,stage)

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
            post_process(self,stage)

            #Updating jobid when complete
            self.cfg['tool'][stage]['jobid']['value'] = [str(jobid)]

            #Return to CWD
            os.chdir(cwd)
