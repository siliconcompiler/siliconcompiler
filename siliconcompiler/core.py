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

        # Copy 'default' to 'value'
        self.reset()
        
        # Instance starts unlocked
        self.cfg_locked = False
        
        # Instance starts with all default stages in idle
        self.status = {}
        for stage in self.cfg['sc_stages']['defvalue']:
            self.status[stage] = ["idle"]
            
    ###################################
    def get(self, *args):
        '''Gets value for supplied Chip parameter

        Args:
            param (string): Configuration parameter to fetch

        Returns:
            list: List of Chip configuration values

        '''
        val = 1
        return val

    ####################################
    #set2('sc_design', 'top')
    #set2('sc_clk', 'clkname', '1ns')
    #set2('sc_tool', 'stagename', 'exe', 'openroad')
    #set2('sc_stdlib', 'libname', 'timing', corner, 'libname.lib')
    
    def set2(self, *args):
        '''Sets a value in the Chip configuration dictionary 
        '''
        self.logger.info('Setting config %s',args)

        tot_args = len(args)
        val = args[-1]
        keys = args[:-1]
        print("tot=",tot_args,"keys=", keys,"val=",val)

        
        
        
    ####################################
    def set(self, val, param, *keys):
        '''Sets a value in the Chip configuration dictionary 
        '''
        self.logger.info('Setting config %s %s %s',val,param,keys)

        #TODO:
        #Use the keys and value to create a small dict
        #Use the merge function to merge with self.cfg!
        #!!!!This function gets deleted!
        
        tot_keys = len(keys)

        key1 = None
        key2 = None
        key3 = None
        value_exists = True
        value_clobbered = False
        
        # Single level parameters
        if tot_keys == 0 :
            value_exists = 'value' in self.cfg[param]            
            if self.cfg[param]['type'] in {"list", "file"}:
                if value_exists:
                    self.cfg[param]['value'].append(val)
                else:
                    self.cfg[param]['value'] = val
            else:
                value_clobbered = value_exists
                self.cfg[param]['value'] = val
        # Nested structure parameters with sub keys
        elif tot_keys > 1:
            key1 = keys[0]
            key2 = keys[1]
            if tot_keys > 2:
                key3 = keys[2]
            # Dynamic dictionary entries for stdlib means we have to check
            # the default dict.
            # Create dictionary if it doesn't exist
            if key1 not in self.cfg[param]:
                value_exists = False
                self.cfg[param][key1] = {}                
            if key2 not in self.cfg[param][key1]:
                value_exists = False
                self.cfg[param][key1][key2] = {}
            if (tot_keys > 2) & (key3 not in self.cfg[param][key1][key2]):
                 value_exists = False
                 self.cfg[param][key1][key2][key3] = {}                 
            if tot_keys > 2:
                print(param,key1,key2,key3)
                if self.cfg[param]['deflib'][key2]['defcorner']['type'] in {"list", "file"}:
                    if value_exists:
                        self.cfg[param][key1][key2][key3]['value'].append(val)
                    else:
                        self.cfg[param][key1][key2][key3]['value'] = val
                else:                    
                    value_clobbered = value_exists
                    self.cfg[param][key1][key2][key3]['value'] = val
            else:
                if self.cfg[param]['deflib'][key2]['type'] in {"list", "file"}:
                    if value_exists:
                        self.cfg[param][key1][key2]['value'].append(val)
                    else:
                        self.cfg[param][key1][key2]['value'] = val
                else:                    
                    value_clobbered = value_exists
                    self.cfg[param][key1][key2]['value'] = val

        # Warn on clobber
        if value_clobbered:
            self.logger.warning('Overwriting existing value for %s', param)
        

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

        #if self.cfg['sc_lock']['values']:
        #    self.cfg_locked = True

    #################################
    def readcfg(self, filename, keymap=None):
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
            self.merge(read_args, abspath)
        else:
            self.logger.error('Trying to change configuration while locked')

        if self.cfg['sc_lock']['value']:
            self.cfg_locked = True


    ##################################
    def writecfg(self, filename, keymap=None):
        '''Writes out the current Chip configuration dictionary to a file

        Args:
            filename (string): Output filename. File-suffix indicates format
                               (json, yaml, tcl)

        '''
        abspath = os.path.abspath(filename)
        self.logger.info('Writing configuration to file %s', abspath)

        # Resolve path and make directory if it doesn't exist
        if not os.path.exists(os.path.dirname(abspath)):
            os.makedirs(os.path.dirname(abspath))

        # Write out configuration based on file type
        if abspath.endswith('.json'):
            with open(abspath, 'w') as f:
                print(json.dumps(self.cfg, sort_keys=True, indent=4), file=f)
        elif abspath.endswith('.yaml'):
            with open(abspath, 'w') as f:
                print(yaml.dump(self.cfg, default_flow_style=False), file=f)
        else:
            self.writetcl(self.cfg, abspath)

    ##################################
    def copycfg (self, keylist, keymap=None):
        '''Create a subset of the current Chip configuration based on the given
        param list

        Args:
            keylist (string): List of configuration parameters to copy
            keymap (dict): Translates Chip configuration key names to a new set
            of names based on a key lookup.

        Returns:
            dict: Chip configuration dictionary

        '''
        pass

    ##################################
    #TODO: Need a hierarchical TCL writer!
    def writetcl(self, cfg, filename):
        '''Writes out the Chip cfg dictionary in TCL format

        Args:
            cfg (dict): Dictionary to print out in TCL format
            filename (string): Output filename.

        '''
        with open(os.path.abspath(filename), 'w') as f:
            print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
            for key in cfg:
                keystr = "set " + key.upper()
                #Put quotes around all list entries
                valstr = "{"
                if self.cfg[key]['type'] in {"list", "file"}:
                    for value in self.cfg[key]['value']:
                        valstr = valstr + " {" + value + "}"
                else:
                    valstr = valstr + " {" + str(self.cfg[key]['values']) + "}"
                valstr = valstr + "}"
                print('{:10s} {:100s}'.format(keystr, valstr), file=f)
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
            self.logger.info('Setting Configuration to Default Values')
            cfg = self.cfg
        for k, v in cfg.items():            
            if isinstance(v, dict):
                if 'defvalue' in cfg[k].keys():
                    cfg[k]['value'] = cfg[k]['defvalue'].copy()
                else:
                    self.reset(cfg=cfg[k])
        
    ##################################
    def abspath(self,cfg=None):
        '''Resolves all configuration paths to be absolute paths
        '''
        #Setting initial dict so user doesn't have to
        if cfg is None:
            self.logger.info('Resolving all paths to absolute paths')
            cfg = self.cfg        
        #Recursively going through dict to set abspaths for files
        for k, v in cfg.items():
            if isinstance(v, dict):
                if 'defvalue' in cfg[k].keys():
                    if(cfg[k]['type'] == 'file'):
                        for i, v in enumerate(cfg[k]['value']):
                            cfg[k]['value'][i] = os.path.abspath(v)
                else:
                    self.abspath(cfg=cfg[k])

    ##################################
    def mergecfg(self, d2, src, d1=None):
        '''Merges dictionary with the Chip configuration dictionary
        '''
        if d1 is None:
            self.logger.info('Merging %s dictionary into Chip instance configuration', src)
            d1 = self.cfg
        for k, v in d2.items():
            #Checking if dub dict exists in self.cfg and new dict
            if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], dict):
                #if we reach a leaf copy d2 to d1
                if 'defvalue' in d1[k].keys():
                    d1[k]['setter'] = src
                    d1[k]['value'].extend(d2[k]['value'])
                #if not in leaf keep descending
                else:
                    self.mergecfg(d2[k], src, d1=d1[k])
            #if a new d2 key is found do a deep copy
            else:
                d1[k] = d2[k].copy()
                    
    ##################################
    def sync(self, stage, jobid):
        '''Waits for jobs for the stage and jobid specified to complete
        Much work to do here!!

        '''
    ##################################
    def hash(self):
        '''Creates hashes for all files sourced by Chip class

        '''

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
    def show(self, stage, jobid):
        '''Shows the layout of the specified stage and jobid

         Args:
            stage: The stage to report on (eg. cts)
            jobid: Index of job to report on (1, 2, etc)
        '''
        pass

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
        print("STAGE", current, start, stop)

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
                #Write out CFG as TCL (EDA tcl lacks support for json)
                self.writetcl(self.cfg, "sc_setup.tcl")

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
                    self.cfg['sc_design']['value'] = topmodule
                    cmd = "cp verilator.v " + topmodule + ".v"
                    subprocess.run(cmd, shell=True)


            if self.cfg['sc_gui']['value'] == "True":
                webbrowser.open("https://google.com")

            #Updating jobid when complete
            #TODO:fix
            self.cfg['sc_tool'][stage]['jobid']['value'] = jobid
            #Return to CWD
            os.chdir(cwd)
