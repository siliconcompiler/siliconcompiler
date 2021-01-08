# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import sys
import os
import re
import json
import argparse
import glob
import numpy
import logging
import webbrowser

class Chip:

    ####################
    def __init__(self,loglevel="DEBUG"):

        ######################################
        # Logging
        
        #INFO:(all except for debug)
        #DEBUG:(all)
        #CRITICAL:(error, critical)
        #ERROR: (error, critical)

        self.logger    = logging.getLogger()
        self.handler   = logging.StreamHandler()
        self.formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

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
            self.cfg[key]['values'] = default_cfg[key]['values']
            self.cfg[key]['help']   = default_cfg[key]['help']
            self.cfg[key]['switch'] = default_cfg[key]['switch']

        ###############
        # Configuration locking variable
        self.cfg_locked = False
            
    #################################
    def readargs(self, args):
        self.logger.info('Reading command line variables')
        if(not self.cfg_locked):
            for arg in vars(args):
                if(arg in self.cfg):
                    var = getattr(args, arg)
                    if(var != None):
                        self.cfg[arg]['values'] = var
        else:
            self.logger.error('Trying to change configuration while locked')       
                        
        if(self.cfg['sc_locked']['values'] == "True"):
            self.cfg_locked =  True

    #################################
    def readenv(self):
        self.logger.info('Reading environment variables')
        if(not self.cfg_locked):
            for key in self.cfg.keys():
                var=os.getenv(key.upper())
                if(var != None):
                    self.cfg[key]['values']= var
        else:
            self.logger.error('Trying to change configuration while locked')        
                    
        if(self.cfg['sc_locked']['values'] == "True"):
            self.cfg_locked =  True
            
    #################################
    def readjson(self,filename):
        self.logger.info('Reading JSON format configuration file %s',os.path.abspath(filename))
        #Read arguments from file    
        with open(os.path.abspath(filename), "r") as f:
            json_args = json.load(f)

        if(not self.cfg_locked):
            for key in json_args:
                #Only allow merging of keys that already exist (no new keys!)
                if key in self.cfg:
                    self.cfg[key]['values'] = json_args[key]['values']
                else:
                    print("ERROR: Merging of unknown keys not allowed,", key)
        else:
             self.logger.error('Trying to change configuration while locked')

        if(self.cfg['sc_locked']['values'] == "True"):
            self.cfg_locked =  True
                    
    ##################################
    def writejson(self, filename=None):
        self.logger.info('Writing JSON format configuration file %s',os.path.abspath(filename))
        if(filename==None):
            print(json.dumps(self.cfg, sort_keys=True, indent=4))
        else:
            if not os.path.exists(os.path.dirname(filename)):                
                os.makedirs(os.path.dirname(filename))
            with open(os.path.abspath(filename), 'w') as f:
                print(json.dumps(self.cfg, sort_keys=True, indent=4), file=f)
            f.close()

    ##################################
    def writetcl(self, filename=None):
        self.logger.info('Writing TCL format configuration file %s',os.path.abspath(filename))
        with open(os.path.abspath(filename), 'w') as f:
            print("#!!!! AUTO-GENEREATED FILE. DO NOT EDIT!!!!!!", file=f)
            for key in self.cfg:
                #print(key, self.cfg[key]['values'])
                keystr  = "set " + key.upper()
                #Put quotes around all list entries
                valstr = "[ list \""
                if(type(self.cfg[key]['values'])!=bool):
                    valstr = valstr + '\" \"'.join(self.cfg[key]['values'])
                    valstr = valstr + "\"]"
                    print('{:10s} {:100s}'.format(keystr, valstr), file=f)
        f.close()

    ##################################
    def lock(self):

        #Aggregating abs paths in one place
        source_list = ["sc_source",
                       "sc_sdc",
                       "sc_upf",
                       "sc_floorplan",
                       "sc_ydir",
                       "sc_cmdfile",
                       "sc_idir",
                       "sc_vlib",
                       "sc_build_dir",
                       "sc_lib",
                       "sc_techfile"]
        
        for stage in self.cfg['sc_stages']['values']:
            source_list.append("sc_"+stage+"_script")

        for source in source_list:
            for i,val in enumerate(self.cfg[source]['values']):
                self.cfg[source]['values'][i] = os.path.abspath(val)

        #Locking the configuration
        self.cfg_locked = True
                
    ###################################
    def run(self, stage):

        #Hard coded directory structure is
        #sc_build_dir/stage/job{id}
        
        cwd     = os.getcwd()
        
        #Looking up stage numbers 
        current = self.cfg['sc_stages']['values'].index(stage)
        start   = self.cfg['sc_stages']['values'].index(self.cfg['sc_start']['values'][0]) 
        stop    = self.cfg['sc_stages']['values'].index(self.cfg['sc_stop']['values'][0])
        
        if stage not in self.cfg['sc_stages']['values']:
            self.logger.error('Illegal stage name',stage)
        elif((current < start) | (current > stop)):
            self.logger.info('Skipping stage: %s',stage)
        else:            
            self.logger.info('Running stage: %s',stage)

            #Updating jobindex
            self.cfg['sc_' + stage + '_jobid']['values'][0] = str(int(self.cfg['sc_' + stage + '_jobid']['values'][0]) + 1)

            #Moving to working directory
            jobdir = (self.cfg['sc_build_dir']['values'][0] +
                     "/" +
                     stage +
                     "/job" +
                     self.cfg['sc_' + stage + '_jobid']['values'][0])

            if(os.path.isdir(jobdir)):
                os.system("rm -rf " +  jobdir)
            os.makedirs(jobdir, exist_ok=True)
            os.chdir(jobdir)
            
            #Prepare tool command
            tool       = self.cfg['sc_' + stage + '_tool']['values'][0] #scalar
            cmd_fields = [tool]
            for value in self.cfg['sc_' + stage + '_opt']['values']:
                cmd_fields.append(value)        
                
            if(tool=="verilator"):       
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
        
                #Adding tcl script to comamnd line
                script  = self.cfg['sc_'+stage+'_script']['values'][0] #scalar!
                cmd_fields.append(script)           
            
            #Execute cmd if current stage is within range of start and stop
            cmd_fields.append("> " + tool + ".log")
            cmd   = ' '.join(cmd_fields)
            
            #Create a shells cript for rerun purposes
            with open("run.sh", 'w') as f:
                print("#!/bin/bash", file=f)
                print(cmd, file=f)
            f.close()
            os.chmod("run.sh", 0o755)
                
            #run command
            self.logger.info('%s', cmd)
            subprocess.run(cmd, shell=True)

            #Post process (only for verilator for now)
            if(tool=="verilator"):
                #hack: use the --debug feature in verilator to output .vpp files
                #hack: count number of vpp files to find it module==1            
                topmodule = self.cfg['sc_topmodule']['values'][0]
                #hack: workaround yosys parser error
                cmd = 'grep -h -v \`begin_keywords obj_dir/*.vpp > ' + topmodule + '.v'
                self.logger.info('%s', cmd)
                subprocess.run(cmd, shell=True)

            #TODO
            if(self.cfg['sc_gui']['values']):
                webbrowser.open("https://google.com")
                
            #Return to CWD
            os.chdir(cwd)

###########################
def cmdline():

    default_cfg = defaults()

    os.environ["COLUMNS"]='100'

    # Argument Parser
    parser = argparse.ArgumentParser(prog='siliconcompiler',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=42),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SC)")
            
    # Source files
    parser.add_argument('sc_source',
                        nargs='+',
                        help=default_cfg['sc_source']['help'])
    
    # All other arguments
    for key in default_cfg.keys():
        if(key=='sc_gui' or key== 'sc_locked'):
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                action="store_true",
                                help=default_cfg[key]['help'])
        elif(key!='sc_source'):
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                action='append',
                                help=default_cfg[key]['help'])
            
    args=parser.parse_args()
            
    return(args)


########################### 
def defaults():

    install_dir = os.path.dirname(os.path.abspath(__file__))
   
    root_dir  = re.sub("siliconcompiler/siliconcompiler","siliconcompiler",install_dir,1)
    asic_dir  = root_dir + "/edalib/asic/"
    fpga_dir  = root_dir + "/edalib/fpga/"
    pdklib    = root_dir + "/pdklib/virtual/nangate45/r1p0/pnr/"
    iplib     = root_dir + "/iplib/virtual/nangate45/NangateOpenCellLibrary/r1p0/lib/"

    #Core dictionary
    default_cfg = {}

    ###############
    # Boolean Switches

    default_cfg['sc_gui']                 = {}
    default_cfg['sc_gui']['help']         = "Launches GUI at every stage"
    default_cfg['sc_gui']['values']       = False
    default_cfg['sc_gui']['switch']       = "-gui"

    #Enable locking through config
    default_cfg['sc_locked']              = {}
    default_cfg['sc_locked']['help']      = "Congiruation lock state (True/False)"
    default_cfg['sc_locked']['values']    = False
    default_cfg['sc_locked']['switch']    = "-lock"
    
    ###############
    #Config file

    default_cfg['sc_cfgfile']             = {}
    default_cfg['sc_cfgfile']['help']     = "Loads switches from json file"
    default_cfg['sc_cfgfile']['values']   =  []
    default_cfg['sc_cfgfile']['switch']   = "-cfgfile"

    ###############
    # Process Technology

    default_cfg['sc_mode']                 = {}
    default_cfg['sc_mode']['help']         = "Implementation mode (ASICor or FPGA)"
    default_cfg['sc_mode']['values']       =  ["ASIC"]
    default_cfg['sc_mode']['switch']       = "-mode"

    default_cfg['sc_techfile']             = {}
    default_cfg['sc_techfile']['help']     = "Place and route tehnology files"
    default_cfg['sc_techfile']['values']   =  [pdklib + "nangate45.tech.lef"]
    default_cfg['sc_techfile']['switch']   = "-techfile"
    
    default_cfg['sc_minlayer']             = {}
    default_cfg['sc_minlayer']['help']     = "Minimum routing layer"
    default_cfg['sc_minlayer']['values']   = ["M2"]
    default_cfg['sc_minlayer']['switch']   = "-minlayer"
    
    default_cfg['sc_maxlayer']             = {}
    default_cfg['sc_maxlayer']['help']     = "Maximum routing layer"
    default_cfg['sc_maxlayer']['values']   = ["M10"]
    default_cfg['sc_maxlayer']['switch']   = "-maxlayer"
    
    default_cfg['sc_scenario']             = {}
    default_cfg['sc_scenario']['help']     = "Process,voltage,temp scenario"
    default_cfg['sc_scenario']['values']   = ["all timing tt 0.7 25"]
    default_cfg['sc_scenario']['switch']   = "-scenario"
    
    ###############
    #Libraries
    
    default_cfg['sc_lib']                  = {}
    default_cfg['sc_lib']['help']          = "Standard cell libraries (liberty)"    
    default_cfg['sc_lib']['values']        = [iplib + "NangateOpenCellLibrary_typical.lib"]
    default_cfg['sc_lib']['switch']        = "-lib"
    
    default_cfg['sc_libheight']            = {}
    default_cfg['sc_libheight']['help']    = "Height of library (in grids)"
    default_cfg['sc_libheight']['values']  = ["12"]
    default_cfg['sc_libheight']['switch']  = "-libheight"
    
    default_cfg['sc_libdriver']            = {}
    default_cfg['sc_libdriver']['help']    = "Name of default driver cell"
    default_cfg['sc_libdriver']['values']  = []
    default_cfg['sc_libdriver']['switch']  = "-libdriver"
    
    default_cfg['sc_cell_lists']            = {}
    default_cfg['sc_cell_lists']['help']    = "Name of default driver cell"
    default_cfg['sc_cell_lists']['values']  = ["icg", "dontuse", "antenna", "dcap", "filler", "tielo", "tiehi"]
    default_cfg['sc_cell_lists']['switch']  = "-cell_lists"
    
    for value in default_cfg['sc_cell_lists']['values']:
        default_cfg['sc_' + value]           = {}
        default_cfg['sc_' + value]['help']   = "List of " + value + " cells"
        default_cfg['sc_' + value]['values'] = []
        default_cfg['sc_' + value]['switch'] =  "-" + value


    #################
    #Execution Options

    default_cfg['sc_debug']               = {}
    default_cfg['sc_debug']['values']     = ["4"]
    default_cfg['sc_debug']['switch']     = "-debug"
    default_cfg['sc_debug']['help']       = "Debug level: INFO/DEBUG/WARNING/ERROR/CRITICAL"

    default_cfg['sc_jobs']                = {}
    default_cfg['sc_jobs']['values']      = ["4"]
    default_cfg['sc_jobs']['switch']      = "-j"
    default_cfg['sc_jobs']['help']        = "Number of jobs to run simultaneously"

    default_cfg['sc_build_dir']           = {}
    default_cfg['sc_build_dir']['values'] = ["build"]
    default_cfg['sc_build_dir']['switch'] = "-build_dir"
    default_cfg['sc_build_dir']['help']   = "Name of build directory"
       
    default_cfg['sc_effort']              = {}
    default_cfg['sc_effort']['values']    = ["high"]
    default_cfg['sc_effort']['switch']    = "-effort"
    default_cfg['sc_effort']['help']      = "Compilation effort(low,medium,high)"
    
    default_cfg['sc_priority']            = {}
    default_cfg['sc_priority']['values']  = ["speed"]
    default_cfg['sc_priority']['switch']  = "-priority"
    default_cfg['sc_priority']['help']    = "Optimization priority(speed,area,power)"
    
    default_cfg['sc_start']               = {}
    default_cfg['sc_start']['values']     = ["import"]
    default_cfg['sc_start']['switch']     = "-start"
    default_cfg['sc_start']['help']       = "Stage to start with"
    
    default_cfg['sc_stop']                = {}
    default_cfg['sc_stop']['values']      = ["export"]
    default_cfg['sc_stop']['switch']      = "-stop"
    default_cfg['sc_stop']['help']        = "Stage to stop after"        
    
    default_cfg['sc_cont']                = {}
    default_cfg['sc_cont']['values']      = []
    default_cfg['sc_cont']['switch']      = "-cont"
    default_cfg['sc_cont']['help']        = "Continue from last completed stage"           
        
    ###############
    #Design Parameters
    default_cfg['sc_source']              = {}
    default_cfg['sc_source']['values']    = []
    default_cfg['sc_source']['switch']    = ""
    default_cfg['sc_source']['help']      = "Verilog source files, minimum one"
    
    default_cfg['sc_topmodule']           = {}
    default_cfg['sc_topmodule']['values'] = ["top"]
    default_cfg['sc_topmodule']['switch'] = "-topmodule"
    default_cfg['sc_topmodule']['help']   = "Top module name"
    
    default_cfg['sc_clk']                 = {}
    default_cfg['sc_clk']['values']       = []
    default_cfg['sc_clk']['switch']       = "-clk"
    default_cfg['sc_clk']['help']         = "Clock defintions"
    
    default_cfg['sc_floorplan']           = {}
    default_cfg['sc_floorplan']['values'] = []
    default_cfg['sc_floorplan']['switch'] = "-floorplan"
    default_cfg['sc_floorplan']['help']   = "Floorplan .PY or DEF file"
    
    default_cfg['sc_sdc']                 = {}
    default_cfg['sc_sdc']['values']       = []
    default_cfg['sc_sdc']['switch']       = "-sdc"
    default_cfg['sc_sdc']['help']         = "Constraints (SDC) file"
    
    default_cfg['sc_upf']                 = {}
    default_cfg['sc_upf']['values']       = []
    default_cfg['sc_upf']['switch']       = "-upf"
    default_cfg['sc_upf']['help']         = "Unified power format (UPF) file"
    
    default_cfg['sc_ydir']                = {}
    default_cfg['sc_ydir']['values']      = []
    default_cfg['sc_ydir']['switch']      = "-y"
    default_cfg['sc_ydir']['help']        = "Directory to search for modules"
    
    default_cfg['sc_vlib']                = {}
    default_cfg['sc_vlib']['values']      = []
    default_cfg['sc_vlib']['switch']      = "-v"
    default_cfg['sc_vlib']['help']        = "Verilog library"
    
    default_cfg['sc_libext']              = {}
    default_cfg['sc_libext']['values']    = [".v", ".vh"]
    default_cfg['sc_libext']['switch']    = "+libext"
    default_cfg['sc_libext']['help']      = "Extensions for finding modules"
    
    default_cfg['sc_idir']                = {}
    default_cfg['sc_idir']['values']      = []
    default_cfg['sc_idir']['switch']      = "-I"
    default_cfg['sc_idir']['help']        = "Directory to search for includes"
    
    default_cfg['sc_define']              = {}
    default_cfg['sc_define']['values']    = []
    default_cfg['sc_define']['switch']    = "-D"
    default_cfg['sc_define']['help']      = "Defines for Verilog preprocessor"
    
    default_cfg['sc_cmdfile']             = {}
    default_cfg['sc_cmdfile']['values']   = []
    default_cfg['sc_cmdfile']['switch']   = "-f"
    default_cfg['sc_cmdfile']['help']     = "Parse options from file"
    
    default_cfg['sc_wall']                = {}
    default_cfg['sc_wall']['values']      = []
    default_cfg['sc_wall']['switch']      = "-Wall"
    default_cfg['sc_wall']['help']        = "Enable all style warnings"
    
    default_cfg['sc_wno']                 = {}
    default_cfg['sc_wno']['values']       = []
    default_cfg['sc_wno']['switch']       = "-Wno"
    default_cfg['sc_wno']['help']         = "Disables a warning -Woo-<message>"

    ##################
    # Tool Flow Configuration
    
    default_cfg['sc_stages']            = {}
    default_cfg['sc_stages']['help']    = "List of all compilation stages"
    default_cfg['sc_stages']['values']  = ["import", "syn", "floorplan", "place", "cts", "route", "signoff", "export"]
    default_cfg['sc_stages']['switch']  = "-stages"
        
    for stage in default_cfg['sc_stages']['values']:
        #init dict
        default_cfg['sc_' + stage + '_tool']   = {}
        default_cfg['sc_' + stage + '_opt']    = {}
        default_cfg['sc_' + stage + '_script'] = {}
        default_cfg['sc_' + stage + '_jobid']  = {}
        #descriptions
        default_cfg['sc_' + stage + '_tool']['help']         = "Name of " + stage + " tool"
        default_cfg['sc_' + stage + '_opt']['help']          = "Options for " + stage + " tool"
        default_cfg['sc_' + stage + '_script']['help']       = "TCL script for " + stage + " tool"
        default_cfg['sc_' + stage + '_jobid']['help']        = "Job index of last job" + stage
        #command line switches
        default_cfg['sc_' + stage + '_tool']['switch']       = "-" + stage + "_tool"
        default_cfg['sc_' + stage + '_opt']['switch']        = "-" + stage + "_opt"
        default_cfg['sc_' + stage + '_script']['switch']     = "-" + stage + "_script"
        default_cfg['sc_' + stage + '_jobid']['switch']      = "-" + stage + "_jobid"
        #build dir
        default_cfg['sc_' + stage + '_jobid']['values']      = ["0"]
        if(stage=="import"):
            default_cfg['sc_import_tool']['values']          = ["verilator"]
            default_cfg['sc_import_opt']['values']           = ["--lint-only", "--debug"]
            default_cfg['sc_import_script']['values']        = [" "]
        elif(stage=="syn"):
            default_cfg['sc_syn_tool']['values']             = ["yosys"]
            default_cfg['sc_syn_opt']['values']              = ["-c"]
            default_cfg['sc_syn_script']['values']           = [asic_dir + stage + ".tcl"]
        else:
            default_cfg['sc_' + stage + '_tool']['values']   = ["openroad"]
            default_cfg['sc_' + stage + '_opt']['values']    = ["-no_init", "-exit"]
            default_cfg['sc_' + stage + '_script']['values'] = [asic_dir + stage + ".tcl"]

    
    return(default_cfg)
