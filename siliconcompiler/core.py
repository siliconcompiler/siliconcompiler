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

    ####################
    def __init__(self, loglevel="DEBUG"):
        '''init method for Chip class.
        
        '''

        ######################################
        # Logging

        #INFO:(all except for debug)
        #DEBUG:(all)
        #CRITICAL:(error, critical)
        #ERROR: (error, critical)

        self.logger = logging.getLogger()
        self.handler = logging.StreamHandler()
        self.formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(str(loglevel))

        ###############
        # Single setup dict for all tools
        default_cfg = defaults()

        # Copying defaults every time a new constructor is made
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

        #instance starts unlocked
        self.cfg_locked = False

        #setting up process stages
        #for stage in self.cfg['sc_stages']['values']:
        #self.status = {}
        
        
    #################################
    def set(self,key,val):
        if self.cfg[key]['type'] == "list":
            self.cfg[key]['values'] = [val]
        elif self.cfg[key]['type'] == "file":
            self.cfg[key]['values'] = [os.path.abspath(val)]
        else:
            self.cfg[key]['values'] = val

    #################################
    def get(self,key,attr='values'):
        return self.cfg[key][attr]
            
    #################################
    def add(self,key,val):
        if self.cfg[key]['type'] == "file":
            self.cfg[key]['values'].append(os.path.abspath(val))
        else:
            self.cfg[key]['values'].append(val)
           
    #################################
    def readargs(self, args):
        '''Copies the arg structure from the command line into the Chip cfg dictionary.

        '''
      
        self.logger.info('Reading command line variables')

        #Copying the parse_arg Namespace object into the dictorary
        #Converting True/False into [""] for consistency
        for arg in vars(args):
            if arg in self.cfg:
                var = getattr(args, arg)
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
        '''Reads the SC environment variables set by the O/S and copies them into the Chip cfg
        dictionary.

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
    def readjson(self, filename):
        '''Reads a json file formatted according to the Chip cfg dictionary
        structure

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
    def writejson(self, filename=None, mode="all"):
        '''Writes out the Chip cfg dictionary to a the display or to a file on disk in the JSON
         format.

        '''

        if filename != None:
            abspath = os.path.abspath(filename)
            self.logger.info('Writing JSON format configuration file %s',abspath)
            
        # Get defaults
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

        # Create 'diff' dictionary
        diff_cfg = {}
        for key in diff_list:
            diff_cfg[key] = {}
            diff_cfg[key]['help'] = self.cfg[key]['help']
            diff_cfg[key]['type'] = self.cfg[key]['type']
            if self.cfg[key]['type'] == "list":
                diff_cfg[key]['values'] = self.cfg[key]['values'].copy()
            elif self.cfg[key]['type'] == "file":
                diff_cfg[key]['values'] = self.cfg[key]['values'].copy()
                diff_cfg[key]['hash'] = self.cfg[key]['hash'].copy() 
            else:
                diff_cfg[key]['values'] = self.cfg[key]['values']

        # Write out dictionary
        if filename == None:
            print(json.dumps(diff_cfg, sort_keys=True, indent=4))
        else:
            if not os.path.exists(os.path.dirname(abspath)):
                os.makedirs(os.path.dirname(abspath))
            with open(abspath, 'w') as f:
                print(json.dumps(diff_cfg, sort_keys=True, indent=4), file=f)
            f.close()
            with open("my.yaml", 'w') as f:
                print(yaml.dump(diff_cfg, default_flow_style = False), file=f)

#    def writeyaml(self,cfg,filename):
#        with open(filename, 'w') as f:
#            print(yaml.dump(diff_cfg), file=f)


    
            
    ##################################
    def writetcl(self, filename=None):
        '''Writes out the Chip cfg dictionary as TC lists used by EDA tools. All keys
         are written as uppercase in accordance to common EDA ethodologies.  The list is 
        the basic Tcl data structure. A list is simply an ordered collection of stuff; 
        numbers, words, strings, or other lists. Even commands in Tcl are just lists 
        in which the first list entry is the name of a proc, and subsequent members of the 
        list are the arguments to the proc.

        '''
        
        self.logger.info('Writing TCL format configuration file %s', os.path.abspath(filename))
        with open(os.path.abspath(filename), 'w') as f:
            print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
            for key in self.cfg:
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
        '''Locks the Chip cfg dictionary to prevent unwarranted configuration updates during the
        compilation flow.

        '''
        for key in self.cfg:
            if self.cfg[key]['type'] == "file":
                for i, val in enumerate(self.cfg[key]['values']):
                    self.cfg[key]['values'][i] = str(os.path.abspath(val))
                    
        #Locking the configuration
        self.cfg_locked = True


    ##################################
    def sync(self):
        '''Waits for all processes to complete
        '''
        pass

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
        '''Compares all keys and values of two json setup files
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
                self.writetcl("sc_setup.tcl")

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

