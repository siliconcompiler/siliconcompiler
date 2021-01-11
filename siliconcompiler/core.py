# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import os
import re
import json
import argparse
import logging
import webbrowser

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
            print(key)
            self.cfg[key] = {}
            self.cfg[key]['help'] = default_cfg[key]['help']
            self.cfg[key]['switch'] = default_cfg[key]['switch']
            self.cfg[key]['type'] = default_cfg[key]['type']
            if default_cfg[key]['type']=="list":
                self.cfg[key]['values'] = default_cfg[key]['values'].copy()
            else:
                self.cfg[key]['values'] = default_cfg[key]['values']

        #instance starts unlocked
        self.cfg_locked = False
            
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
        
        self.logger.info('Reading JSON format configuration file %s', os.path.abspath(filename))
        #Read arguments from file
        with open(os.path.abspath(filename), "r") as f:
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

    ##################################
    def writejson(self, filename=None):
        '''Writes out the Chip cfg dictionary to a the display or to a file on disk in the JSON
         format.

        '''
        self.logger.info('Writing JSON format configuration file %s', os.path.abspath(filename))
        if filename == None:
            print(json.dumps(self.cfg, sort_keys=True, indent=4))
        else:
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            with open(os.path.abspath(filename), 'w') as f:
                print(json.dumps(self.cfg, sort_keys=True, indent=4), file=f)
            f.close()

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
                #print(key, self.cfg[key]['values'])
                keystr = "set " + key.upper()
                #Put quotes around all list entries
                valstr = "{"
                print(key)
                if self.cfg[key]['type'] == "list":
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
        #Aggregating abs paths in one place
        source_list = ["sc_source",
                       "sc_constraints",
                       "sc_upf",
                       "sc_floorplan",
                       "sc_ydir",
                       "sc_cmdfile",
                       "sc_idir",
                       "sc_vlib",
                       "sc_build",
                       "sc_lib",
                       "sc_gdslib",
                       "sc_leflib",
                       "sc_techfile"]

        for stage in self.cfg['sc_stages']['values']:
            source_list.append("sc_"+stage+"_script")

        #for source in source_list:
        #    for i, val in enumerate(self.cfg[source]['values']):
        #        self.cfg[source]['values'][i] = os.path.abspath(val)

        for key in self.cfg:
            print(key)
            if ((self.cfg[key]['type']=="list") | (self.cfg[key]['type']=="string")):
                for i, val in enumerate(self.cfg[key]['values']):
                    print(self.cfg[key]['values'][i],val)

        #Locking the configuration
        self.cfg_locked = True

    ###################################
    def run(self, stage):
        '''The commonn execution method for all compilation stages compilation flow.

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

                #Adding tcl script to comamnd line
                script = self.cfg['sc_'+stage+'_script']['values']
                cmd_fields.append(script)

            #Execute cmd if current stage is within range of start and stop
            cmd_fields.append("> " + tool + ".log")
            cmd = ' '.join(cmd_fields)

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
            if tool == "verilator":
                #hack: use the --debug feature in verilator to output .vpp files
                #hack: count number of vpp files to find it module==1
                topmodule = self.cfg['sc_topmodule']['values']
                #hack: workaround yosys parser error
                cmd = 'grep -h -v \`begin_keywords obj_dir/*.vpp > ' + topmodule + '.v'
                self.logger.info('%s', cmd)
                subprocess.run(cmd, shell=True)

            if self.cfg['sc_gui']['values']=="True":
                webbrowser.open("https://google.com")

            #Return to CWD
            os.chdir(cwd)

###########################
def cmdline():
    '''Handles the command line arguments usign argparse. All configuration parameters are exposed
    at the command line interface.

    '''
    default_cfg = defaults()

    os.environ["COLUMNS"] = '100'

    # Argument Parser
    
    parser = argparse.ArgumentParser(prog='siliconcompiler',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=42),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SC)")

    # Source files
    parser.add_argument('sc_source',
                        nargs='+',
                        help=default_cfg['sc_source']['help'])

    # All other arguments
    for key in default_cfg.keys():
        if default_cfg[key]['type'] == "bool":
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                action='store_true',
                                help=default_cfg[key]['help'])
        elif default_cfg[key]['type'] != "list":
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                help=default_cfg[key]['help'])
        elif key != "sc_source":
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                action='append',
                                help=default_cfg[key]['help'])

    args = parser.parse_args()

    return args

###########################
def defaults():
    '''Method for setting the default values for the Chip dictionary. 
    The default setings are not manufacturable.

    '''
    install_dir = os.path.dirname(os.path.abspath(__file__))

    root_dir = re.sub("siliconcompiler/siliconcompiler", "siliconcompiler", install_dir, 1)
    asic_dir = root_dir + "/edalib/asic/"
    fpga_dir = root_dir + "/edalib/fpga/"
    pdklib = root_dir + "/pdklib/virtual/nangate45/r1p0/pnr/"
    iplib = root_dir + "/iplib/virtual/nangate45/NangateOpenCellLibrary/r1p0/"

    #Core dictionary
    default_cfg = {}

    ############################################
    # General Settings
    #############################################

    default_cfg['sc_mode'] = {
        'help' : "Implementation mode (asic or fpga)",
        'type' : "string",
        'switch' : "-mode",
        'values' : "asic"
    }

    default_cfg['sc_process'] = {
        'help' : "Name of target process node",
        'type' : "string",
        'switch' : "-process",
        'values' : "nangate45"
    }

    default_cfg['sc_cfgfile'] = {
        'help' : "Loads configurations from a json file",
        'type' : "list",
        'switch' : "-cfgfile",
        'values' : []
    }
    
    ############################################
    # Place and Route Setup
    #############################################

    default_cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file (lef or tf)",
        'type' : "string",
        'switch' : "-techfile",
        'values' : pdklib + "nangate45.tech.lef"
    }

    default_cfg['sc_layer'] = {
        'help' : "Routing layer definitions (eg: metal1 X 0.095 0.19) ",
        'type' : "list",
        'switch' : "-layer",
        'values' : ["metal1 X 0.095 0.19",
                    "metal1 Y 0.07  0.14",
                    "metal2 X 0.095 0.19",
                    "metal2 Y 0.07  0.14",
                    "metal3 X 0.095 0.19",
                    "metal3 Y 0.07  0.14",
                    "metal4 X 0.095 0.28",
                    "metal4 Y 0.07  0.28",
                    "metal5 X 0.095 0.28",
                    "metal5 Y 0.07  0.28",
                    "metal6 X 0.095 0.28",
                    "metal6 Y 0.07  0.28",
                    "metal7 X 0.095 0.8",
                    "metal7 Y 0.07  0.8",
                    "metal8 X 0.095 0.8",
                    "metal8 Y 0.07  0.8",
                    "metal9 X 0.095 1.6",
                    "metal9 Y 0.07  1.6",
                    "metal10 X 0.095 1.6",
                    "metal10 Y 0.07 1.6"]
    }
    
    
    ############################################
    # Simulation setup
    #############################################

    default_cfg['sc_model'] = {
        'help' : "Spice model file",
        'type' : "string",
        'switch' : "-model",
        'values' : ""
    }
     
    default_cfg['sc_scenario'] = {
        'help' : "Process,voltage,temp scenario (eg: tt 0.7 25 setup)",
        'type' : "list",
        'switch' : "-scenario",
        'values' : ["tt 0.7 25 setup"]
    }


    ############################################
    # Standard Cell Libraries
    #############################################

    default_cfg['sc_lib'] = {
        'help' : "Standard cell libraries",
        'type' : "list",
        'switch' : "-lib",
        'values' : [iplib + "lib/NangateOpenCellLibrary_typical.lib"]
    }

    default_cfg['sc_lef'] = {
        'help' : "LEF files",
        'type' : "list",
        'switch' : "-lef",
        'values' : [iplib + "lef/NangateOpenCellLibrary.macro.lef"]
    }

    default_cfg['sc_gds'] = {
        'help' : "GDS files",
        'type' : "list",
        'switch' : "-gds",
        'values' : [iplib + "gds/NangateOpenCellLibrary.gds"]
    }

    default_cfg['sc_libdriver'] = {
        'help' : "Name of default driver cell",
        'type' : "string",
        'switch' : "-libdriver",
        'values' : "BUF_X1"
    }

    default_cfg['sc_site'] = {
        'help' : "Site name for automated floor-planning",
        'type' : "string",
        'switch' : "-site",
        'values' : "FreePDK45_38x28_10R_NP_162NW_34O"
    }
    
    default_cfg['sc_cell_list'] = {
        'help' : "List of cell lists needed for PNR setup",
        'type' : "list",
        'switch' : "-cell_list",
        'values' : ["icg", "dontuse", "antenna", "dcap", "filler", "tielo", "tiehi"]
    }
        
    for value in default_cfg['sc_cell_list']['values']:
        default_cfg['sc_' + value] = {
            'help' : "List of " + value + " cells",
            'type' : "list",
            'switch' : "-" + value,
            'values' : []
        }
        
    ############################################
    # Execute Options
    #############################################

    default_cfg['sc_debug'] = {
        'help' : "Debug level (INFO/DEBUG/WARNING/ERROR/CRITICAL)",
        'type' : "string",
        'switch' : "-debug",
        'values' : "INFO"
    }

    default_cfg['sc_build'] = {
        'help' : "Name of build directory",
        'type' : "string",
        'switch' : "-build",
        'values' : "build"
    }
    
    default_cfg['sc_effort'] = {
        'help' : "Compilation effort (low,medium,high)",
        'type' : "string",
        'switch' : "-effort",
        'values' : "high"
    }

    default_cfg['sc_priority'] = {
        'help' : "Optimization priority (performance, power, area)",
        'type' : "string",
        'switch' : "-priority",
        'values' : "performance"
    }

    default_cfg['sc_priority'] = {
        'help' : "Optimization priority (performance, power, area)",
        'type' : "string",
        'switch' : "-priority",
        'values' : "performance"
    }

    default_cfg['sc_cont'] = {
        'help' : "Continues from last completed stage",
        'type' : "bool",
        'switch' : "-cont",
        'values' : False
    }
        
    default_cfg['sc_gui'] = {
        'help' : "Launches GUI at every stage",
        'type' : "bool",
        'switch' : "-gui",
        'values' : False
    }

    default_cfg['sc_lock'] = {
        'help' : "Switch to lock configuration from further modification",
        'type' : "bool",
        'switch' : "-lock",
        'values' : False
    }
    
    default_cfg['sc_start'] = {
        'help' : "Compilation starting stage",
        'type' : "string",
        'switch' : "-start",
        'values' : "import"
    }

    default_cfg['sc_stop'] = {
        'help' : "Compilation ending stage",
        'type' : "string",
        'switch' : "-stop",
        'values' : "export"
    }

    ############################################
    # Design Specific Source Code Parameters
    #############################################

    default_cfg['sc_source'] = {
        'help' : "Source files (.v/.vh/.sv/.vhd)",
        'type' : "list",
        'switch' : "None",
        'values' : []
    }

    default_cfg['sc_topmodule'] = {
        'help' : "Design top module name",
        'type' : "string",
        'switch' : "-topmodule",
        'values' : ""
    }

    default_cfg['sc_clk'] = {
        'help' : "Clock defintion tuple (<clkname> <period(ns)>)",
        'type' : "list",
        'switch' : "-clk",
        'values' : []
    }


    default_cfg['sc_define'] = {
        'help' : "Define variables for Verilog preprocessor",
        'type' : "list",
        'switch' : "-D",
        'values' : []
    }
    
    default_cfg['sc_ydir'] = {
        'help' : "Directory to search for modules",
        'type' : "list",
        'switch' : "-y",
        'values' : []
    }

    default_cfg['sc_idir'] = {
        'help' : "Directory to search for inclodes",
        'type' : "list",
        'switch' : "-I",
        'values' : []
    }

    default_cfg['sc_vlib'] = {
        'help' : "Library file",
        'type' : "list",
        'switch' : "-v",
        'values' : []
    }

    default_cfg['sc_libext'] = {
        'help' : "Extension for finding modules",
        'type' : "list",
        'switch' : "+libext",
        'values' : [".v", ".vh", ".sv", ".vhd"]
    }

    default_cfg['sc_cmdfile'] = {
        'help' : "Parse source options from command file",
        'type' : "list",
        'switch' : "-f",
        'values' : []
    }

    default_cfg['sc_wall'] = {
        'help' : "Enable all lint style warnings",
        'type' : "string",
        'switch' : "-Wall",
        'values' : []
    }

    default_cfg['sc_wno'] = {
        'help' : "Disables a warning -Woo-<message>",
        'type' : "list",
        'switch' : "-Wno",
        'values' : []
    }

    ############################################
    # Design specific PD Parameters
    #############################################

    default_cfg['sc_minlayer'] = {
        'help' : "Minimum routing layer (integer)",
        'type' : "int",
        'switch' : "-minlayer",
        'values' : 2
    }

    default_cfg['sc_maxlayer'] = {
        'help' : "Maximum routing layer (integer)",
        'type' : "int",
        'switch' : "-maxlayer",
        'values' : 5
    }
    
    default_cfg['sc_maxfanout'] = {
        'help' : "Maximum fanout",
        'type' : "int",
        'switch' : "-maxfanout",
        'values' : 64
    }

    default_cfg['sc_density'] = {
        'help' : "Target density for automated floor-planning (percent)",
        'type' : "int",
        'switch' : "-density",
        'values' : 30
    }

    default_cfg['sc_aspectratio'] = {
        'help' : "Aspect ratio for density driven floor-planning",
        'type' : "float",
        'switch' : "-aspect_ratio",
        'values' : 1
    }

    default_cfg['sc_coremargin'] = {
        'help' : "Margin around core for density driven floor-planning (um)",
        'type' : "float",
        'switch' : "-coremargin",
        'values' : 2
    }

    default_cfg['sc_diesize'] = {
        'help' : "Die size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-diesize",
        'values' : ""
    }

    default_cfg['sc_coresize'] = {
        'help' : "Core size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-coresize",
        'values' : ""
    }

    default_cfg['sc_floorplan'] = {
        'help' : "User supplied python based floorplaning script",
        'type' : "string",
        'switch' : "-floorplan",
        'values' : ""
    }
    
    default_cfg['sc_def'] = {
        'help' : "User supplied hard-coded floorplan (DEF)",
        'type' : "string",
        'switch' : "-def",
        'values' : ""
    }
    
    default_cfg['sc_constraints'] = {
        'help' : "Timing constraints file (SDC)",
        'type' : "string",
        'switch' : "-constraints",
        'values' : asic_dir + "/default.sdc"
    }
    
    default_cfg['sc_ndr'] = {
        'help' : "Non-default net routing file",
        'type' : "string",
        'switch' : "-ndr",
        'values' : ""
    }

    default_cfg['sc_upf'] = {
        'help' : "Unified power format (UPF) file",
        'type' : "string",
        'switch' : "-upf",
        'values' : ""
    }

    ############################################
    # Tool Configuration
    #############################################

    default_cfg['sc_stages'] = {
        'help' : "List of all compilation stages",
        'type' : "list",
        'switch' : "-stages",
        'values' : ["import",
                    "syn",
                    "floorplan",
                    "place",
                    "cts",
                    "route",
                    "signoff",
                    "lec",
                    "sta",
                    "pi",
                    "si",
                    "drc",
                    "lvs",
                    "export"]
    }

    for stage in default_cfg['sc_stages']['values']:
        
        #init dict
        default_cfg['sc_' + stage + '_tool'] = {}
        default_cfg['sc_' + stage + '_opt'] = {}
        default_cfg['sc_' + stage + '_script'] = {}
        default_cfg['sc_' + stage + '_jobid'] = {}
        default_cfg['sc_' + stage + '_np'] = {}

        #descriptions
        default_cfg['sc_' + stage + '_tool']['help'] = "Name of " + stage + " tool "
        default_cfg['sc_' + stage + '_opt']['help'] = "Options for " + stage + " tool"
        default_cfg['sc_' + stage + '_script']['help'] = "Tool run script" + stage + " tool"
        default_cfg['sc_' + stage + '_jobid']['help'] = "Job index of last executed job" + stage
        default_cfg['sc_' + stage + '_np']['help'] = "Thread parallelism for" + stage

        #type
        default_cfg['sc_' + stage + '_tool']['type'] = "string"
        default_cfg['sc_' + stage + '_opt']['type'] = "list"
        default_cfg['sc_' + stage + '_script']['type'] = "string"
        default_cfg['sc_' + stage + '_jobid']['type'] = "int"
        default_cfg['sc_' + stage + '_np']['type'] = "int"
        
        #command line switches
        default_cfg['sc_' + stage + '_tool']['switch'] = "-" + stage + "_tool"
        default_cfg['sc_' + stage + '_opt']['switch'] = "-" + stage + "_opt"
        default_cfg['sc_' + stage + '_script']['switch'] = "-" + stage + "_script"
        default_cfg['sc_' + stage + '_jobid']['switch'] = "-" + stage + "_jobid"
        default_cfg['sc_' + stage + '_np']['switch'] = "-" + stage + "_np"

        #Tool specific values
        default_cfg['sc_' + stage + '_jobid']['values'] = 0
        if stage == "import":
            default_cfg['sc_import_tool']['values'] = "verilator"
            default_cfg['sc_import_opt']['values'] = ["--lint-only", "--debug"]
            default_cfg['sc_import_script']['values'] = [""]
            default_cfg['sc_import_np']['values'] = 4
        elif stage == "syn":
            default_cfg['sc_syn_tool']['values'] = "yosys"
            default_cfg['sc_syn_opt']['values'] = ["-c"]
            default_cfg['sc_syn_script']['values'] = [asic_dir + stage + ".tcl"]
            default_cfg['sc_syn_np']['values'] = 4
        else:
            default_cfg['sc_' + stage + '_tool']['values'] = "openroad"
            default_cfg['sc_' + stage + '_opt']['values'] = ["-no_init", "-exit"]
            default_cfg['sc_' + stage + '_script']['values'] = [asic_dir + stage + ".tcl"]
            default_cfg['sc_' + stage + '_np']['values'] = 4
            
    return default_cfg
