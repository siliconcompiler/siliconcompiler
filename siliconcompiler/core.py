# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import os
import sys
import re
import json
import yaml
import logging
import hashlib
import webbrowser
from siliconcompiler.config import defaults, cmdline

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
    def __init__(self, cmdargs, loglevel="DEBUG"):
        '''
        Init method for Chip object
        
        '''

        # Initialize logger
        self.logger = logging.getLogger()
        self.handler = logging.StreamHandler()
        self.formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(str(loglevel))

        # Initialize dict
        default_cfg = defaults()

        self.cfg = {}
        for key in default_cfg.keys():
            self.cfg[key] = {}
            self.cfg[key]['help'] = default_cfg[key]['help']
            self.cfg[key]['switch'] = default_cfg[key]['switch']
            self.cfg[key]['type'] = default_cfg[key]['type']
            if default_cfg[key]['type'] == "list":
                self.cfg[key]['values'] = default_cfg[key]['values'].copy()
            elif default_cfg[key]['type'] == "file":
                self.cfg[key]['values'] = default_cfg[key]['values'].copy()
                self.cfg[key]['hash'] = default_cfg[key]['hash'].copy()   
            else:
                self.cfg[key]['values'] = default_cfg[key]['values']

        # instance starts unlocked
        self.cfg_locked = False

        # setting up an empty status dictionary for each stage 
        self.status = {}
        for stage in self.cfg['sc_stages']['values']:
            self.status[stage] = ["idle"]

        #Read environment variables
        self.readenv()

        #Read in json files based on cfg
          
        #Overide with command line arguments
        self.copyargs(cmdargs)

        #Resolve all source files as absolute paths (should be a switch)
        self.abspath()
          
    ###################################
    def get(self, param):
        '''Gets value for supplied Chip parameter
       
        Args:
            param (string): Configuration parameter to fetch

        Returns:
            list: List of Chip configuration values

        '''
        
        return self.cfg[param]['values']

    ####################################   
    def set(self, param, val):
        '''Sets an Chip configuration parameter

        Args:
            param (string): Configuration parameter to set
            val (list): Value(s) to assign to param 

        '''
        
        if self.cfg[param]['type'] == "list":
            self.cfg[param]['values'] = [val]
        elif self.cfg[param]['type'] == "file":
            self.cfg[param]['values'] = [os.path.abspath(val)]
        else:
            self.cfg[param]['values'] = val

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
    def append(self,param, val):
        '''Appends values to an existing Chip configuration parameter

        Args:
            param (string): Configuration parameter to set
            val (list) : Value(s) to assign to param 

        '''

        if self.cfg[param]['type'] == "file":
            self.cfg[param]['values'].append(os.path.abspath(val))
        else:
            self.cfg[param]['values'].append(val)
           
    #################################
    def copyargs(self, cmdargs):
        '''Copies attributes from the ArgumentsParser object to the current Chip configuration.

        Args:
            cmdargs (ArgumentParser) : ArgumentsParser object

        '''
            
        self.logger.info('Reading command line variables')

        #Copying the parse_arg Namespace object into the dictorary
        #Converting True/False into [""] for consistency??? TODO
        for arg in vars(cmdargs):
            if arg in self.cfg:
                var = getattr(cmdargs, arg)
                if var != None:
                    if var == True:
                        self.cfg[arg]['values'] = ["True"]
                    elif var == False:
                        self.cfg[arg]['values'] = ["False"]
                    else:
                        #should work for both scalar and vlists
                        self.cfg[arg]['values'] = var
        
        if self.cfg['sc_lock']['values']:
            self.cfg_locked = True
            
    #################################
    def readenv(self):
        '''Reads Chip environment variables and copies them to the current configuration.
        Environment variables are assumed to be the upper case of the Chip parameters.
        For example, the parameter sc_foundry will be read as $env(SC_FOUNDRY).  
        '''

        self.logger.info('Reading environment variables')
        
        if not self.cfg_locked:
            for key in self.cfg.keys():
                var = os.getenv(key.upper())
                if var != None:
                    self.cfg[key]['values'] = var
        else:
            self.logger.error('Trying to change configuration while locked')

        if self.cfg['sc_lock']['values']:
            self.cfg_locked = True

    #################################
    def readcfg(self, filename):
        '''Reads a json formatted config file into the Chip current Chip configuration

        Args:
            filename (string): JSON formatted configuration file to read

        Returns:
            dict: Returns a dictionary found in JSON file for all keys found in
                  in the current Chip configuration

        '''

        abspath = os.path.abspath(filename)

        self.logger.info('Reading JSON format configuration file %s', abspath)

        #Read arguments from file
        with open(abspath, "r") as f:
            json_args = json.load(f)

        if not self.cfg_locked:
            for key in json_args:
                #Only allow merging of keys that already exist (no new keys!)
                if key in self.cfg:
                    #ask if scalar
                    self.cfg[key]['values'] = json_args[key]['values'].copy()
                else:
                    print("ERROR: Merging of unknown keys not allowed,", key)
        else:
            self.logger.error('Trying to change configuration while locked')

        if self.cfg['sc_lock']['values']:
            self.cfg_locked = True

        return json_args
            
    ##################################
    def writecfg(self, filename, mode="all"):
        '''Writes out the current Chip configuration dictionary to a file

        Args:
            filename (string): Output filename. File-suffix indicates format (json, yaml, tcl)
            mode (string): Write the whole configuration when mode=diff, otherwise writes
            the complete current Chip configuration.

        '''
        abspath = os.path.abspath(filename)
        self.logger.info('Writing configuration to file %s',abspath)

        # Resolve path and make directory if it doesn't exist        
        if not os.path.exists(os.path.dirname(abspath)):
            os.makedirs(os.path.dirname(abspath))

        # Get delta dictionary
        diff_cfg = self.delta(mode)

        # Write out configuration based on file type
        
        if abspath.endswith('.json'):
            with open(abspath, 'w') as f:
                print(json.dumps(diff_cfg, sort_keys=True, indent=4), file=f)
        elif abspath.endswith('.yaml'):
            with open(abspath, 'w') as f:
                print(yaml.dump(diff_cfg, default_flow_style = False), file=f)
        else:
            self.writetcl(diff_cfg,abspath)
                
    ##################################
    def delta(self, mode):
        '''Compute the delta between the current Chip onfig and the default

        Args:
            filename (string): JSON formatted configuration file to read

        Returns:
            dict: Returns the difference between the current Chip configuration
                  and the default configuration

        '''

        #Get default config
        default_cfg = defaults()
        
        # Extract all keys with non-default values
        diff_list = []
        for key in default_cfg.keys():
            if mode=="all":
                diff_list.append(key)  
            elif default_cfg[key]['type'] in {"list", "file"}:                
                for value in self.cfg[key]['values']:
                    if value not in default_cfg[key]['values']:
                        diff_list.append(key)
                        break
            elif self.cfg[key]['values'] != default_cfg[key]['values']:
                diff_list.append(key)
                
        diff_cfg = self.copy(diff_list)                

        return diff_cfg

    ##################################
    def copy(self, keylist):
        '''Create a subset of the current Chip configuration based on the given param list

        Args:
            keylist (string): List of configuratin parameters to copy

        Returns:
            dict: Chip configuration dictionary

        '''
        
        cfg = {}
        for key in keylist:
            cfg[key] = {}
            cfg[key]['help'] = self.cfg[key]['help']
            cfg[key]['type'] = self.cfg[key]['type']
            if self.cfg[key]['type'] == "list":
                cfg[key]['values'] = self.cfg[key]['values'].copy()
            elif self.cfg[key]['type'] == "file":
                cfg[key]['values'] = self.cfg[key]['values'].copy()
                cfg[key]['hash'] = self.cfg[key]['hash'].copy() 
            else:
                cfg[key]['values'] = self.cfg[key]['values']

        return cfg
    
    ##################################
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
                    for value in self.cfg[key]['values']:
                        valstr = valstr + " {" + value + "}"
                else:
                    valstr = valstr + " {" + str(self.cfg[key]['values']) + "}"           
                valstr = valstr + "}"
                print('{:10s} {:100s}'.format(keystr, valstr), file=f)
        f.close()

    ##################################
    def lock(self):
        '''Locks the Chip configuration to prevent unwarranted configuration updates
        '''                    
        self.cfg_locked = True

    ##################################
    def abspath(self):
         '''Resolves all configuration paths to be absolute paths
        '''
         for key in self.cfg:
            if self.cfg[key]['type'] == "file":
                for i, val in enumerate(self.cfg[key]['values']):
                    self.cfg[key]['values'][i] = str(os.path.abspath(val))

    ##################################
    def sync(self, stage,jobid):
        '''Waits for jobs for the stage and jobid specified to complete
        Much work to do here!!

        '''
        
    ##################################
    def hash(self):
        '''Creates hashes for all files sourced by Chip class

        '''

        for key in self.cfg:        
            if self.cfg[key]['type'] == "file":
                for filename in self.cfg[key]['values']:
                   if os.path.isfile(filename):
                       with open(filename,"rb") as f:
                           bytes = f.read() # read entire file as bytes
                           hash_value = hashlib.sha256(bytes).hexdigest();
                           self.cfg[key]['hash'].append(hash_value)
        
    ##################################
    def compare(self, file1, file2):
        '''Compares Chip configurations contained in two different json files
        Useful??

        '''                      

        abspath1 = os.path.abspath(file1)
        abspath2 = os.path.abspath(file2)

        self.logger.info('Comparing JSON format configuration file %s and %s ', abspath1, abspath2)

        #Read arguments from file
        with open(abspath1, "r") as f:
            file1_args = json.load(f)
        with open(abspath2, "r") as f:
            file2_args = json.load(f)  
            
        same =  True
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
                            self.logger.error('Comparison difference found for key %s', key)
                elif file1_args[key]['values'] != file2_args[key]['values']:
                        same = False
                        self.logger.error('Comparison difference found for key %s', key)
            else:
                same = False

        return same


    ###################################
    def summary(self, stage, jobid, filename=None):
        '''Creates a summary dictionary of the results of the specified stage and jobid

         Args:
            stage: The stage to report on (eg. cts)
            jobid: Index of job to report on (1, 2, etc)
        '''    
        summary = 1
        return summary

    
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
    def run(self, stage, mode="sync", machine="local"):
        '''The common execution method for all compilation stages compilation flow.
        The job executes on the local machine by default, but can be execute as a remote
        job as well. If executed in synthconorus mode, the run command waits at the end of the
        function call before returning to main. If the job is executed in async mode,
        flags are set in the Class state and the function cal returns to main.

        '''

        #Hard coded directory structure is
        #sc_build/stage/job{id}

        cwd = os.getcwd()

        #Looking up stage numbers
        current = self.cfg['sc_stages']['values'].index(stage)
        start = self.cfg['sc_stages']['values'].index(self.cfg['sc_start']['values'])
        stop = self.cfg['sc_stages']['values'].index(self.cfg['sc_stop']['values'])

        if stage not in self.cfg['sc_stages']['values']:
            self.logger.error('Illegal stage name', stage)
        elif (current < start) | (current > stop):
            self.logger.info('Skipping stage: %s', stage)
        else:
            self.logger.info('Running stage: %s', stage)

            #Updating jobindex
            self.cfg['sc_' + stage + '_jobid']['values'] = str(int(self.cfg['sc_' + stage + '_jobid']['values']) + 1)

            #Moving to working directory
            jobdir = (self.cfg['sc_build']['values'] +
                      "/" +
                      stage +
                      "/job" +
                      self.cfg['sc_' + stage + '_jobid']['values'])

            if os.path.isdir(jobdir):
                os.system("rm -rf " +  jobdir)
            os.makedirs(jobdir, exist_ok=True)
            self.logger.info('Entering workig directory %s', jobdir)
            os.chdir(jobdir)

            #Prepare tool command
            tool = self.cfg['sc_' + stage + '_tool']['values']
            cmd_fields = [tool]
            for value in self.cfg['sc_' + stage + '_opt']['values']:
                cmd_fields.append(value)

            if tool == "verilator":
                for value in self.cfg['sc_ydir']['values']:
                    cmd_fields.append('-y ' + value)
                for value in self.cfg['sc_vlib']['values']:
                    cmd_fields.append('-v ' + value)
                for value in self.cfg['sc_idir']['values']:
                    cmd_fields.append('-I ' + value)
                for value in self.cfg['sc_define']['values']:
                    cmd_fields.append('-D ' + value)
                for value in self.cfg['sc_source']['values']:
                    cmd_fields.append(value)
            else:
                #Write out CFG as TCL (EDA tcl lacks support for json)
                self.writetcl(self.cfg, "sc_setup.tcl")

            #Adding tcl scripts to comamnd line
            for value in self.cfg['sc_' + stage + '_script']['values']:
                cmd_fields.append(value)

            #Execute cmd if current stage is within range of start and stop
            logfile  = tool + ".log"
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
            if tool == "verilator":
                #hack: use the --debug feature in verilator to output .vpp files
                #hack: workaround yosys parser error
                cmd = ('grep -h -v \`begin_keywords obj_dir/*.vpp > verilator.v')
                subprocess.run(cmd, shell=True)
                #hack: extracting topmodule from concatenated verilator files 
                modules=0
                with open("verilator.v", "r") as open_file:
                    for line in open_file:
                        modmatch = re.match('^module\s+(\w+)', line)
                        if modmatch:
                            modules = modules + 1
                            topmodule = modmatch.group(1)
                # Only setting sc_design when appropriate
                if (modules > 1) & (self.cfg['sc_design']['values'] == ""):
                    self.logger.error('Multiple modules found during import, but sc_design was not set')
                    sys.exit()
                else:
                    self.logger.info('Setting design (topmodule) to %s', topmodule)
                    self.cfg['sc_design']['values'] =  topmodule
                    cmd = "cp verilator.v " + topmodule + ".v"
                    subprocess.run(cmd, shell=True)
                    
                    
            if self.cfg['sc_gui']['values'] == "True":
                webbrowser.open("https://google.com")

            #Return to CWD
            os.chdir(cwd)

  
        
