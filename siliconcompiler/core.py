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
            self.cfg[key] = {}
            self.cfg[key]['help'] = default_cfg[key]['help']
            self.cfg[key]['switch'] = default_cfg[key]['switch']
            self.cfg[key]['values'] = default_cfg[key]['values'].copy()


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
                        self.cfg[arg]['values'] = var
        
        if self.cfg['sc_lock']['values'][0] == "True":
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

        if self.cfg['sc_lock']['values'][0] == "True":
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
                    self.cfg[key]['values'] = json_args[key]['values'].copy()
                else:
                    print("ERROR: Merging of unknown keys not allowed,", key)
        else:
            self.logger.error('Trying to change configuration while locked')

        if self.cfg['sc_locked']['values'][0] == "True":
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
                for value in self.cfg[key]['values']:
                    valstr = valstr + " {" + value + "}"
                valstr = valstr + "}"
                #valstr = "[ list \""
                #valstr = valstr + '\" \"'.join(self.cfg[key]['values'])
                #valstr = valstr + "\"]"
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

        for source in source_list:
            for i, val in enumerate(self.cfg[source]['values']):
                self.cfg[source]['values'][i] = os.path.abspath(val)

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
        start = self.cfg['sc_stages']['values'].index(self.cfg['sc_start']['values'][0])
        stop = self.cfg['sc_stages']['values'].index(self.cfg['sc_stop']['values'][0])

        if stage not in self.cfg['sc_stages']['values']:
            self.logger.error('Illegal stage name', stage)
        elif (current < start) | (current > stop):
            self.logger.info('Skipping stage: %s', stage)
        else:
            self.logger.info('Running stage: %s', stage)

            #Updating jobindex
            self.cfg['sc_' + stage + '_jobid']['values'][0] = str(int(self.cfg['sc_' + stage + '_jobid']['values'][0]) + 1)

            #Moving to working directory
            jobdir = (self.cfg['sc_build']['values'][0] +
                      "/" +
                      stage +
                      "/job" +
                      self.cfg['sc_' + stage + '_jobid']['values'][0])

            if os.path.isdir(jobdir):
                os.system("rm -rf " +  jobdir)
            os.makedirs(jobdir, exist_ok=True)
            self.logger.info('Entering workig directory %s', jobdir)
            os.chdir(jobdir)

            #Prepare tool command
            tool = self.cfg['sc_' + stage + '_tool']['values'][0] #scalar
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
                script = self.cfg['sc_'+stage+'_script']['values'][0] #scalar
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
                topmodule = self.cfg['sc_topmodule']['values'][0]
                #hack: workaround yosys parser error
                cmd = 'grep -h -v \`begin_keywords obj_dir/*.vpp > ' + topmodule + '.v'
                self.logger.info('%s', cmd)
                subprocess.run(cmd, shell=True)

            if self.cfg['sc_gui']['values'][0]=="True":
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
        if key == 'sc_gui':
            parser.add_argument(default_cfg[key]['switch'],
                                dest=key,
                                action='store_true',
                                help=default_cfg[key]['help'])
        elif key == 'sc_lock':
            pass 
        elif key != 'sc_source':
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

    ###############
    # Boolean Switches

    default_cfg['sc_gui'] = {}
    default_cfg['sc_gui']['help'] = "Launches GUI at every stage"
    default_cfg['sc_gui']['values'] = ["False"]
    default_cfg['sc_gui']['switch'] = "-gui"

    #Enable locking through config
    default_cfg['sc_lock'] = {}
    default_cfg['sc_lock']['help'] = "Congiruation lock state (True/False)"
    default_cfg['sc_lock']['values'] = ["False"]
    default_cfg['sc_lock']['switch'] = "-lock"

    ###############
    #Config file

    default_cfg['sc_cfgfile'] = {}
    default_cfg['sc_cfgfile']['help'] = "Loads switches from json file"
    default_cfg['sc_cfgfile']['values'] = []
    default_cfg['sc_cfgfile']['switch'] = "-cfgfile"

    ###############
    # Process Technology

    default_cfg['sc_mode'] = {}
    default_cfg['sc_mode']['help'] = "Implementation mode (asic or fpga)"
    default_cfg['sc_mode']['values'] = ["asic"]
    default_cfg['sc_mode']['switch'] = "-mode"

    default_cfg['sc_process'] = {}
    default_cfg['sc_process']['help'] = "Name of target process node"
    default_cfg['sc_process']['values'] = ["nangate45"]
    default_cfg['sc_process']['switch'] = "-process"

    default_cfg['sc_techfile'] = {}
    default_cfg['sc_techfile']['help'] = "Place and route tehnology files"
    default_cfg['sc_techfile']['values'] = [pdklib + "nangate45.tech.lef"]
    default_cfg['sc_techfile']['switch'] = "-techfile"

    default_cfg['sc_site'] = {}
    default_cfg['sc_site']['help'] = "Site name for automated floor-planning"
    default_cfg['sc_site']['values'] = ["FreePDK45_38x28_10R_NP_162NW_34O"]
    default_cfg['sc_site']['switch'] = "-site"
    
    default_cfg['sc_layer'] = {}
    default_cfg['sc_layer']['help'] = "Routing layer definitionss"
    default_cfg['sc_layer']['values'] = ["metal1 X 0.095 0.19",
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
    default_cfg['sc_layer']['switch'] = "-layer"
    
    default_cfg['sc_minlayer'] = {}
    default_cfg['sc_minlayer']['help'] = "Minimum routing layer"
    default_cfg['sc_minlayer']['values'] = ["M2"]
    default_cfg['sc_minlayer']['switch'] = "-minlayer"

    default_cfg['sc_maxlayer'] = {}
    default_cfg['sc_maxlayer']['help'] = "Maximum routing layer"
    default_cfg['sc_maxlayer']['values'] = ["M5"]
    default_cfg['sc_maxlayer']['switch'] = "-maxlayer"

    default_cfg['sc_scenario'] = {}
    default_cfg['sc_scenario']['help'] = "Process,voltage,temp scenario"
    default_cfg['sc_scenario']['values'] = ["all timing tt 0.7 25"]
    default_cfg['sc_scenario']['switch'] = "-scenario"

    default_cfg['sc_maxfanout'] = {}
    default_cfg['sc_maxfanout']['help'] = "Maximum fanout "
    default_cfg['sc_maxfanout']['values'] = ["100"]
    default_cfg['sc_maxfanout']['switch'] = "-maxfanout"

    ###############
    #Libraries

    default_cfg['sc_lib'] = {}
    default_cfg['sc_lib']['help'] = "Standard cell libraries"
    default_cfg['sc_lib']['values'] = [iplib + "lib/NangateOpenCellLibrary_typical.lib"]
    default_cfg['sc_lib']['switch'] = "-lib"

    default_cfg['sc_leflib'] = {}
    default_cfg['sc_leflib']['help'] = "GDS files"
    default_cfg['sc_leflib']['values'] = [iplib + "lef/NangateOpenCellLibrary.macro.lef"]
    default_cfg['sc_leflib']['switch'] = "-lef"

    default_cfg['sc_gdslib'] = {}
    default_cfg['sc_gdslib']['help'] = "GDS files"
    default_cfg['sc_gdslib']['values'] = [iplib + "gds/NangateOpenCellLibrary.gds"]
    default_cfg['sc_gdslib']['switch'] = "-gds"

    default_cfg['sc_libheight'] = {}
    default_cfg['sc_libheight']['help'] = "Height of library (in grids)"
    default_cfg['sc_libheight']['values'] = ["12"]
    default_cfg['sc_libheight']['switch'] = "-libheight"

    default_cfg['sc_libdriver'] = {}
    default_cfg['sc_libdriver']['help'] = "Name of default driver cell"
    default_cfg['sc_libdriver']['values'] = []
    default_cfg['sc_libdriver']['switch'] = "-libdriver"

    default_cfg['sc_cell_lists'] = {}
    default_cfg['sc_cell_lists']['help'] = "Name of default driver cell"
    default_cfg['sc_cell_lists']['values'] = ["icg", "dontuse", "antenna", "dcap", "filler", "tielo", "tiehi"]
    default_cfg['sc_cell_lists']['switch'] = "-cell_lists"

    for value in default_cfg['sc_cell_lists']['values']:
        default_cfg['sc_' + value] = {}
        default_cfg['sc_' + value]['help'] = "List of " + value + " cells"
        default_cfg['sc_' + value]['values'] = []
        default_cfg['sc_' + value]['switch'] = "-" + value

    #################
    #Execution Options

    default_cfg['sc_debug'] = {}
    default_cfg['sc_debug']['help'] = "Debug level: INFO/DEBUG/WARNING/ERROR/CRITICAL"
    default_cfg['sc_debug']['values'] = ["4"]
    default_cfg['sc_debug']['switch'] = "-debug"

    default_cfg['sc_np'] = {}
    default_cfg['sc_np']['help'] = "Number of tasks to run in parallel"
    default_cfg['sc_np']['values'] = ["4"]
    default_cfg['sc_np']['switch'] = "-np"

    default_cfg['sc_build'] = {}
    default_cfg['sc_build']['help'] = "Name of build directory"
    default_cfg['sc_build']['values'] = ["build"]
    default_cfg['sc_build']['switch'] = "-build"

    default_cfg['sc_effort'] = {}
    default_cfg['sc_effort']['help'] = "Compilation effort(low,medium,high)"
    default_cfg['sc_effort']['values'] = ["high"]
    default_cfg['sc_effort']['switch'] = "-effort"

    default_cfg['sc_priority'] = {}
    default_cfg['sc_priority']['help'] = "Optimization priority(speed,area,power)"
    default_cfg['sc_priority']['values'] = ["speed"]
    default_cfg['sc_priority']['switch'] = "-priority"

    default_cfg['sc_start'] = {}
    default_cfg['sc_start']['help'] = "Stage to start with"
    default_cfg['sc_start']['values'] = ["import"]
    default_cfg['sc_start']['switch'] = "-start"

    default_cfg['sc_stop'] = {}
    default_cfg['sc_stop']['help'] = "Stage to stop after"
    default_cfg['sc_stop']['values'] = ["export"]
    default_cfg['sc_stop']['switch'] = "-stop"

    default_cfg['sc_cont'] = {}
    default_cfg['sc_cont']['help'] = "Continue from last completed stage"
    default_cfg['sc_cont']['values'] = []
    default_cfg['sc_cont']['switch'] = "-cont"

    ###############
    #Design Source Parameters

    default_cfg['sc_source'] = {}
    default_cfg['sc_source']['help'] = "Source files (.v/.vh/.sv/.vhd)"
    default_cfg['sc_source']['values'] = []
    default_cfg['sc_source']['switch'] = ""

    default_cfg['sc_topmodule'] = {}
    default_cfg['sc_topmodule']['help'] = "Top module name"
    default_cfg['sc_topmodule']['values'] = ["top"]
    default_cfg['sc_topmodule']['switch'] = "-topmodule"

    default_cfg['sc_clk'] = {}
    default_cfg['sc_clk']['help'] = "Clock defintion tuple (<clkname> <period>)"
    default_cfg['sc_clk']['values'] = ["clk 100"]
    default_cfg['sc_clk']['switch'] = "-clk"

    default_cfg['sc_ydir'] = {}
    default_cfg['sc_ydir']['help'] = "Directory to search for modules"
    default_cfg['sc_ydir']['values'] = []
    default_cfg['sc_ydir']['switch'] = "-y"

    default_cfg['sc_vlib'] = {}
    default_cfg['sc_vlib']['help'] = "Library file"
    default_cfg['sc_vlib']['values'] = []
    default_cfg['sc_vlib']['switch'] = "-v"

    default_cfg['sc_libext'] = {}
    default_cfg['sc_libext']['help'] = "Extension for finding modules"
    default_cfg['sc_libext']['values'] = [".v", ".vh", ".sv", ".vhd"]
    default_cfg['sc_libext']['switch'] = "+libext"

    default_cfg['sc_idir'] = {}
    default_cfg['sc_idir']['help'] = "Directory to search for includes"
    default_cfg['sc_idir']['values'] = []
    default_cfg['sc_idir']['switch'] = "-I"

    default_cfg['sc_define'] = {}
    default_cfg['sc_define']['help'] = "Defines for Verilog preprocessor"
    default_cfg['sc_define']['values'] = []
    default_cfg['sc_define']['switch'] = "-D"

    default_cfg['sc_cmdfile'] = {}
    default_cfg['sc_cmdfile']['values'] = []
    default_cfg['sc_cmdfile']['switch'] = "-f"
    default_cfg['sc_cmdfile']['help'] = "Parse options from file"

    default_cfg['sc_wall'] = {}
    default_cfg['sc_wall']['values'] = []
    default_cfg['sc_wall']['switch'] = "-Wall"
    default_cfg['sc_wall']['help'] = "Enable all style warnings"

    default_cfg['sc_wno'] = {}
    default_cfg['sc_wno']['values'] = []
    default_cfg['sc_wno']['switch'] = "-Wno"
    default_cfg['sc_wno']['help'] = "Disables a warning -Woo-<message>"

    ##################
    # Physical Design Setup
      
    default_cfg['sc_density'] = {}
    default_cfg['sc_density']['help'] = "Target density for automated floor-planning (percent)"
    default_cfg['sc_density']['values'] = ["30"]
    default_cfg['sc_density']['switch'] = "-density"

    default_cfg['sc_aspectratio'] = {}
    default_cfg['sc_aspectratio']['help'] = "Aspect ratio for density driven floor-planning"
    default_cfg['sc_aspectratio']['values'] = ["1"]
    default_cfg['sc_aspectratio']['switch'] = "-aspectratio"
    
    default_cfg['sc_margin'] = {}
    default_cfg['sc_margin']['help'] = "Maring around core for density driven floor-planning (um)"
    default_cfg['sc_margin']['values'] = ["2.0"]
    default_cfg['sc_margin']['switch'] = "-coremargin"
    
    default_cfg['sc_diesize'] = {}
    default_cfg['sc_diesize']['help'] = "Die size (x0 y0 x1 y1) for automated floor-planning (um)"
    default_cfg['sc_diesize']['values'] = [""]
    default_cfg['sc_diesize']['switch'] = "-diesize"

    default_cfg['sc_coresize'] = {}
    default_cfg['sc_coresize']['help'] = "Core size  (x0 y0 x1 y1) for automated floor-planning (um)"
    default_cfg['sc_coresize']['values'] = [""]
    default_cfg['sc_coresize']['switch'] = "-coresize"

    default_cfg['sc_floorplan'] = {}
    default_cfg['sc_floorplan']['help'] = "User supplied floorplaning program"
    default_cfg['sc_floorplan']['values'] = []
    default_cfg['sc_floorplan']['switch'] = "-floorplan"

    default_cfg['sc_def'] = {}
    default_cfg['sc_def']['help'] = "User supplied hard-coded DEF floorplan"
    default_cfg['sc_def']['values'] = []
    default_cfg['sc_def']['switch'] = "-def"

    default_cfg['sc_constraints'] = {}
    default_cfg['sc_constraints']['help'] = "Timing constraints file"
    default_cfg['sc_constraints']['values'] = [asic_dir + "/default.sdc" ]
    default_cfg['sc_constraints']['switch'] = "-constraints"

    default_cfg['sc_ndr'] = {}
    default_cfg['sc_ndr']['help'] = "Non-default net routing file"
    default_cfg['sc_ndr']['values'] = []
    default_cfg['sc_ndr']['switch'] = "-ndr"

    default_cfg['sc_upf'] = {}
    default_cfg['sc_upf']['help'] = "Unified power format (UPF) file"
    default_cfg['sc_upf']['values'] = []
    default_cfg['sc_upf']['switch'] = "-upf" 
    
    ##################
    # Tool Flow Configuration

    default_cfg['sc_stages'] = {}
    default_cfg['sc_stages']['help'] = "List of all compilation stages"
    default_cfg['sc_stages']['values'] = ["import", "syn",
                                          "floorplan", "place",
                                          "cts", "route",
                                          "signoff", "export"]
    default_cfg['sc_stages']['switch'] = "-stages"

    for stage in default_cfg['sc_stages']['values']:
        #init dict
        default_cfg['sc_' + stage + '_tool'] = {}
        default_cfg['sc_' + stage + '_opt'] = {}
        default_cfg['sc_' + stage + '_script'] = {}
        default_cfg['sc_' + stage + '_jobid'] = {}
        #descriptions
        default_cfg['sc_' + stage + '_tool']['help'] = "Name of " + stage + " tool"
        default_cfg['sc_' + stage + '_opt']['help'] = "Options for " + stage + " tool"
        default_cfg['sc_' + stage + '_script']['help'] = "TCL script for " + stage + " tool"
        default_cfg['sc_' + stage + '_jobid']['help'] = "Job index of last job" + stage
        #command line switches
        default_cfg['sc_' + stage + '_tool']['switch'] = "-" + stage + "_tool"
        default_cfg['sc_' + stage + '_opt']['switch'] = "-" + stage + "_opt"
        default_cfg['sc_' + stage + '_script']['switch'] = "-" + stage + "_script"
        default_cfg['sc_' + stage + '_jobid']['switch'] = "-" + stage + "_jobid"
        #build dir
        default_cfg['sc_' + stage + '_jobid']['values'] = ["0"]
        if stage == "import":
            default_cfg['sc_import_tool']['values'] = ["verilator"]
            default_cfg['sc_import_opt']['values'] = ["--lint-only", "--debug"]
            default_cfg['sc_import_script']['values'] = [""]
        elif stage == "syn":
            default_cfg['sc_syn_tool']['values'] = ["yosys"]
            default_cfg['sc_syn_opt']['values'] = ["-c"]
            default_cfg['sc_syn_script']['values'] = [asic_dir + stage + ".tcl"]
        else:
            default_cfg['sc_' + stage + '_tool']['values'] = ["openroad"]
            default_cfg['sc_' + stage + '_opt']['values'] = ["-no_init", "-exit"]
            default_cfg['sc_' + stage + '_script']['values'] = [asic_dir + stage + ".tcl"]

    return default_cfg
