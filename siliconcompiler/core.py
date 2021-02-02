# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import os
import sys
import re
import json
import logging as log
import hashlib
import webbrowser
import yaml
import copy
from collections import defaultdict

from siliconcompiler.schema import schema

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
        
        # Instance starts with all default stages in idle
        self.status = {}
        for stage in self.cfg['sc_stages']['defvalue']:
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
        self.logger.info('Retrieving config dictionary value: %s', args)

        return list(self.search(self.cfg, *args, mode='getkeys'))

    ####################################
    # sc_stdcell, <dynamic>, nldm, <dynamic>, val (4)
    # sc_pdk_pnrdir, <stackup>, <lib>, <vendor>, val(4)
    # sc_stdcell, <dynamic>, lef, val (3)
    # sc_pdk_display, <dynamic>, <dynamic>, val(2)
    # sc_pdk_models, <dynamic>, val (2)
    # sc_design, val (1)

    def add(self, *args, clear=False):
        '''Sets a value in the Chip configuration dictionary 
        '''
        self.logger.info('Setting config dictionary value: %s', args)
                
        all_args = list(args)
        param = all_args[0]

        #Option for clearing list before adding value
        if clear:
            mode = 'set'
        else:
            mode = 'add'
        
        # Convert val to list if not a list
        if type(all_args[-1]) != list:
            all_args[-1] = [all_args[-1]]

        # Deepcopy library from default template if it doesn't exist
        # Can't be done recursively since we have to copy from template
        # piece by piece? Need to reach back and over to template into the right
        # place in the structure. How to do that elegantly?

        #Code for dynamically copying default sub trees where needed
        if param in self.cfg.keys():
            if len(all_args) > 2:
                k1 = all_args[1]
                if not (k1 in self.cfg[param]):
                    self.cfg[param][k1] = {}
                    self.cfg[param][k1] = copy.deepcopy(self.cfg[param]['default'])
            if len(all_args) > 3:
                k2 = all_args[2]
                if not (k2 in self.cfg[param][k1]):
                    if len(self.cfg[param]['default']) > 1:
                        view = k2
                    else:
                        view = 'default'  
                    self.cfg[param][k1][k2] = {}
                    self.cfg[param][k1][k2] = copy.deepcopy(self.cfg[param]['default'][view])
            if len(all_args) > 4:
                k3 = all_args[3]
                if len(self.cfg[param]['default']) > 1:
                    view = k2
                else:
                    view = 'default'  
                # If there is only one view, that view should be default
                print(k1,k2,k3)
                if not (k3 in self.cfg[param][k1][k2]):
                    self.cfg[param][k1][k2][k3] = {}                    
                    self.cfg[param][k1][k2][k3] = copy.deepcopy(self.cfg[param]['default'][view]['default'])
        else:
            self.logger.error('Parameter is not valid: %s', param)        

        return self.search(self.cfg, *all_args, mode=mode)
    
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
        if param in cfg.keys():
            #indicates leaf cell
            if (mode=='add') & (len(all_args) == 2):
                cfg[param][field] = val
                return cfg[param][field]
            elif (mode=='set') & (len(all_args) == 2):
                return cfg[param][field].extend(val)
            elif (len(all_args) == 1):
                if(mode=='getkeys'):
                    return cfg[param].keys()
                else:
                    return cfg[param][field]
            else:
                all_args.pop(0)
                return self.search(cfg[param], *all_args, field=field, mode=mode)
        else:
            self.logger.error('Param %s not found in dictionary', param)  

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
    def rename(self, cfg, stage):
        '''Creates a copy of the dictionary with renamed primary keys
        '''

        cfgout =  {}
        keymap = {}
        
        #Create a dynamic keymap from string pairs
        string_list = self.cfg['sc_tool'][stage]['keymap']['value']
        for string in string_list:
            k,v = string.split()
            keymap[k]=v

        #Cycle through all primary params and rename keys
        for key in cfg:        
            if key in keymap:
                newkey = keymap[key]
                self.logger.info('Keymap renaming from %s to %s', key, newkey)
            else:
                newkey = key
            cfgout[newkey] = cfg[key].copy() 
    
        return cfgout
    
    ##################################
    def abspath(self,cfg=None):
        '''Resolves all configuration paths to be absolute paths
        '''
        #Setting initial dict so user doesn't have to
        if cfg is None:
            self.logger.info('Creating absolute file paths')
            cfg = self.cfg        
        #Recursively going through dict to set abspaths for files
        for k, v in cfg.items():
            if isinstance(v, dict):
                #indicates leaf cell
                if 'value' in cfg[k].keys():
                    #only do something if a file is found
                    if(cfg[k]['type'][-1] == 'file'):
                        for i, v in enumerate(cfg[k]['value']):
                            cfg[k]['value'][i] = os.path.abspath(v)
                else:
                    self.abspath(cfg=cfg[k])

    ##################################
    def printcfg (self, cfg, keys=None, f=None, prefix=""):
        '''Prints out flattened dictionary
        '''
        if keys is None:
            keys = []
        for k in cfg:
            newkeys =  keys.copy()
            newkeys.append(k)
            if 'value' in cfg[k]:
                lst = cfg[k]['value']
                keystr = ' '.join(newkeys)
                for i in range(len(lst)):
                    if f is None:
                        print(prefix, keystr, i, lst[i])
                    else:
                        print(prefix, keystr, i, lst[i], file=f)
            else:
                self.printcfg(cfg[k], keys=newkeys, f=f, prefix=prefix)

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
    def check(self):
        '''Checks all values set in Chip configuration for legality.
        Also checks for missing values.

        Args:
            stage (string): Stage name to get status for
            jobid (int): Job index

        Returns:
            : Status (pending, running, done, or error)

        '''
        
        #1. All values of configuration
        #2. If lengths match, check each item using foor loop
        #legal values are (file|string), int, float
        #if cfg['type'] == "int":
        error = 1
        return error

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
                read_args = yaml.load(f)
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

        if self.cfg['sc_lock']['value'] == "True":
            self.cfg_locked = True


    ##################################
    def writecfg(self, filename):
        '''Writes out the current Chip configuration dictionary to a file

        Args:
            filename (string): Output filename. File-suffix indicates format
                               (json, yaml, tcl)

        '''

        filepath = os.path.abspath(filename)

        self.logger.info('Writing configuration to file %s', filepath)

        # Resolve path and make directory if it doesn't exist
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        
        # Write out configuration based on file type
        if filepath.endswith('.json'):
            with open(filepath, 'w') as f:
                print(json.dumps(self.cfg, sort_keys=True, indent=4), file=f)

    ##################################
    def writetcl(self, stage, filename, cfg=None):
        '''Writes out the Chip cfg dictionary in TCL format

        Args:
            cfg (dict): Dictionary to print out in TCL format
            filename (string): Output filename.

        '''
        filepath = os.path.abspath(filename)
        
        self.logger.info('Writing configuration in TCL format: %s', filepath)
        
        if cfg is None:
            cfg = self.cfg

        #Creating a copy of cfg with name remap based on stage
        cfg = self.rename(cfg, stage)
        
        # Writing out file
        with open(filepath, 'w') as f:
            print("#############################################", file=f)
            print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
            print("#############################################", file=f)
            self.printcfg(cfg, prefix="dict set sc_cfg", f=f)
        f.close()  

    ##################################
    def readtcl(self, filename):
        '''Reads in the a Chip configuration in in TCL format

        Args:
            filename (string): Input filename.

        '''
        return(1)

    ##################################
    def writemake(self, cfg, filename):
        '''Writes out the Chip cfg dictionary in Make format

        Args:
            cfg (dict): Dictionary to print out in Make format
            filename (string): Output filename.

        '''
        pass
    
    
    ##################################
    def readmake(self, filename):
        '''Reads in the a Chip configuration in in Make format

        Args:
            filename (string): Input filename.

        '''
        return(1)

    
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
    def hash(self):
        '''Creates hashes for all files sourced by Chip class

        '''
        #TODO: modify to run on directory recursively if found
        #don't follow links
        #for root, dirs, files in os.walk(directory):
        #read files
        for key in self.cfg:
            if self.cfg[key]['type'] == "file":
                for filename in self.cfg[key]['value']:
                    if os.path.isfile(filename):
                        sha256_hash = hashlib.sha256()
                        with open(filename, "rb") as f:
                            for byte_block in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(byte_block)
                            hash_value = sha256_hash.hexdigest()
                            self.cfg[key]['hash'].append(hash_value)

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
    def metrics(self):
        '''Displays the metrics of all jobs in a web browser

         Args:
            stage: The stage to report on (eg. cts)
            jobid: Index of job to report on (1, 2, etc)
        '''
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

        #Hard coded directory structure is
        #sc_build/stage/job{id}

        cwd = os.getcwd()

        #Looking up stage numbers
        stages = self.cfg['sc_stages']['value']
        current = stages.index(stage)
        start = stages.index(self.cfg['sc_start']['value'][-1]) #scalar
        stop = stages.index(self.cfg['sc_stop']['value'][-1]) #scalar

        if stage not in self.cfg['sc_stages']['value']:
            self.logger.error('Illegal stage name %s', stage)
        elif (current < start) | (current > stop):
            self.logger.info('Skipping stage: %s', stage)
        else:
            self.logger.info('Running stage: %s', stage)

            #Updating jobindex
            jobid = int(self.cfg['sc_tool'][stage]['jobid']['value'][-1]) + 1 #scalar
            
            #Moving to working directory
            jobdir = (str(self.cfg['sc_build']['value'][-1]) + #scalar
                      "/" +
                      str(stage) +
                      "/job" +
                      str(jobid))

            if os.path.isdir(jobdir):
                os.system("rm -rf " +  jobdir)
            os.makedirs(jobdir, exist_ok=True)
            self.logger.info('Entering workig directory %s', jobdir)
            os.chdir(jobdir)

            #Prepare tool command
            exe = self.cfg['sc_tool'][stage]['exe']['value'][-1] #scalar
            cmd_fields = [exe]
            for opt in self.cfg['sc_tool'][stage]['opt']['value']:
                cmd_fields.append(opt)

            if exe == "verilator":
                for value in self.cfg['sc_ydir']['value']:
                    cmd_fields.append('-y ' + value)
                for value in self.cfg['sc_vlib']['value']:
                    cmd_fields.append('-v ' + value)
                for value in self.cfg['sc_idir']['value']:
                    cmd_fields.append('-I ' + value)
                for value in self.cfg['sc_define']['value']:
                    cmd_fields.append('-D ' + value)
                for value in self.cfg['sc_source']['value']:
                    cmd_fields.append(value)
            else:
                #Write out CFG dictionary as TCL
                self.writetcl(stage, "sc_setup.tcl")

            #Adding tcl scripts to comamnd line
            for value in self.cfg['sc_tool'][stage]['script']['value']:
                cmd_fields.append(value)

            #Execute cmd if current stage is within range of start and stop
            logfile = exe + ".log"
            cmd_fields.append("> " + logfile)
            cmd = ' '.join(cmd_fields)

            #Create a shells cript for rerun purposes
            with open("run.sh", 'w') as f:
                print("#!/bin/bash", file=f)
                print(cmd, file=f)
            f.close()
            os.chmod("run.sh", 0o755)

            #run command
            self.logger.info('%s', cmd)
            error = subprocess.run(cmd, shell=True)
            if error.returncode:
                self.logger.error('Command failed. See log file %s', os.path.abspath(logfile))
                sys.exit()

            #Post process (only for verilator for now)
            if exe == "verilator":
                #hack: use the --debug feature in verilator to output .vpp files
                #hack: workaround yosys parser error
                cmd = ('grep -h -v \`begin_keywords obj_dir/*.vpp > verilator.v')
                subprocess.run(cmd, shell=True)
                #hack: extracting topmodule from concatenated verilator files
                modules = 0
                with open("verilator.v", "r") as open_file:
                    for line in open_file:
                        modmatch = re.match('^module\s+(\w+)', line)
                        if modmatch:
                            modules = modules + 1
                            topmodule = modmatch.group(1)
                # Only setting sc_design when appropriate
                if (modules > 1) & (self.cfg['sc_design']['value'] == ""):
                    self.logger.error('Multiple modules found during import, but sc_design was not set')
                    sys.exit()
                else:
                    self.logger.info('Setting design (topmodule) to %s', topmodule)
                    self.cfg['sc_design']['value'].append(topmodule)
                    cmd = "cp verilator.v " + topmodule + ".v"
                    subprocess.run(cmd, shell=True)

            #Updating jobid when complete
            self.cfg['sc_tool'][stage]['jobid']['value'] = [str(jobid)]
            #Return to CWD
            os.chdir(cwd)
