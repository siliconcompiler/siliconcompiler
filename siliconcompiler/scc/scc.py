# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import sys
import argparse
import os
import re
import json

############################
# FUNCTIONS
############################

def run(config_file, stage, input_dir, output_dir):

    #Read scc_args from json file
    with open(os.path.abspath(config_file), "r") as f:
        scc_args = json.load(f)

    #Moving to working directory
    cwd = os.getcwd()
    os.makedirs(os.path.abspath(output_dir), exist_ok=True)
    os.chdir(os.path.abspath(output_dir))

    #Dump TCL (EDA tcl lacks support for json)
    with open("scc_setup.tcl", 'w') as f:
        for key in sorted(scc_args.keys()):
            print('set ', key , scc_args[key], file=f)
    
    #Execute EDA tool
    tool    = scc_args['scc_' + stage + '_tool']
    script  = os.path.abspath(scc_args['scc_' + stage + '_script'])
    cmd = tool + " " + script
    print(cmd)
    error   = subprocess.run(cmd, shell=True)
    
    #Return to CWD
    os.chdir(cwd)

def design_import(config_file, output_dir):

    #Read scc_args from json file
    with open(os.path.abspath(config_file), "r") as f:
        scc_args = json.load(f)

    #Constructing verilator command
    cmd_fields = ["verilator --lint-only --debug"]

    for value in scc_args['scc_ydir']:
        cmd_fields.append('-y ' + os.path.abspath(value))
    for value in scc_args['scc_vlib']:
        cmd_fields.append('-v ' + os.path.abspath(value))
    for value in scc_args['scc_idir']:
        cmd_fields.append('-I ' + os.path.abspath(value))
    for value in scc_args['scc_define']:
        cmd_fields.append('-D ' + value)
    for value in scc_args['scc_source']:
        cmd_fields.append(os.path.abspath(value))   

    cmd = ' '.join(cmd_fields);
    
    #Working directory
    cwd = os.getcwd()
    os.makedirs(os.path.abspath(output_dir), exist_ok=True)
    os.chdir(os.path.abspath(output_dir))
      
    #Execute Parser/Linter
    error = subprocess.run(cmd, shell=True)
    error = subprocess.run('cat obj_dir/*.vpp > output.vpp', shell=True)
    
    #Return to CWD
    os.chdir(cwd)


def cfg_default():
    
    install_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir    = re.sub("siliconcompiler/siliconcompiler", "siliconcompiler",install_dir,1)
    pdklib      = root_dir + "/third_party/pdklib/virtual/nangate45/r1p0/pnr/"
    iplib       = root_dir + "/third_party/iplib/virtual/nangate45/NangateOpenCellLibrary/r1p0/lib/"


    scc_args={}

    ###############
    #Technology
    scc_args['scc_techfile']={}
    scc_args['scc_techfile']['help']     = "Place and route tehnology files"
    scc_args['scc_techfile']['values']   =  [pdklib + "nangate45.tech.lef"]
    scc_args['scc_techfile']['switch']   = "-techfile"

    scc_args['scc_minlayer']={}
    scc_args['scc_minlayer']['help']     = "Minimum routing layer"
    scc_args['scc_minlayer']['values']   = ["M2"]
    scc_args['scc_minlayer']['switch']   = "-minlayer"

    scc_args['scc_maxlayer']={}
    scc_args['scc_maxlayer']['help']     = "Maximum routing layer"
    scc_args['scc_maxlayer']['values']   = ["M7"]
    scc_args['scc_maxlayer']['switch']   = "-maxlayer"

    scc_args['scc_scenario']={}
    scc_args['scc_scenario']['help']     = "Process, voltage, temp scenarios for compilation"
    scc_args['scc_scenario']['values']   = ["all,timing,tt,0.7,25"]
    scc_args['scc_scenario']['switch']   = "-scenario"

    
    ###############
    #Libraries
    scc_args['scc_lib']={}
    scc_args['scc_lib']['help']          = "Standard cell libraries (liberty)"    
    scc_args['scc_lib']['values']        = [iplib + "NangateOpenCellLibrary_typical.lib"]
    scc_args['scc_lib']['switch']        = "-lib"

    scc_args['scc_libheight']={}
    scc_args['scc_libheight']['help']    = "Height of library (in grids)"
    scc_args['scc_libheight']['values']  = [12]
    scc_args['scc_libheight']['switch']  = "-libheight"

    scc_args['scc_libdriver']={}
    scc_args['scc_libdriver']['help']    = "Name of default driver cell"
    scc_args['scc_libdriver']['values']  = []
    scc_args['scc_libdriver']['switch']  = "-libdriver"


    cell_lists = ["icg", "dontuse", "antenna", "dcap", "filler", "tielo", "tiehi"]

    for value in cell_lists:
        scc_args['scc_' + value]={}
        scc_args['scc_' + value]['help']   = "List of " + value + " cells"
        scc_args['scc_' + value]['values'] = []
        scc_args['scc_' + value]['switch'] = value
    
    ###############
    # Tool Definitions
    
    all_stages = ["import", "syn", "place", "cts", "route", "signoff", "export"]

    for stage in all_stages:
        #init dict
        scc_args['scc_' + stage + '_tool']={}
        scc_args['scc_' + stage + '_opt']={}
        scc_args['scc_' + stage + '_dir']={}
        scc_args['scc_' + stage + '_script']={}
        #descriptions
        scc_args['scc_' + stage + '_tool']['help']       = "Name of " + stage + " tool"
        scc_args['scc_' + stage + '_opt']['help']        = "Options for " + stage + " tool"
        scc_args['scc_' + stage + '_dir']['help']        = "Build diretory for " + stage
        scc_args['scc_' + stage + '_script']['help']     = "TCL script for " + stage + "tool"
        #command line switches
        scc_args['scc_' + stage + '_tool']['switch']     = "-" + stage + "_tool"
        scc_args['scc_' + stage + '_opt']['switch']      = "-" + stage + "_opt"
        scc_args['scc_' + stage + '_dir']['switch']      = "-" + stage + "_dir"
        scc_args['scc_' + stage + '_script']['switch']   = "-" + stage + "_script"        
        #scc defaults
        scc_args['scc_' + stage + '_script']['values']   = ["build/" + stage]
        scc_args['scc_' + stage + '_dir']['values']      = [install_dir + "asic/" + stage + ".tcl"]
        if(stage=="import"):
            scc_args['scc_import_tool']['values']        = ["verilator"]
            scc_args['scc_import_opt']['values']         = ["--lint-only", "--debug"]
        elif(stage=="syn"):
            scc_args['scc_syn_tool']['values']           = ["yosys"]
            scc_args['scc_syn_opt']['values']            = ["-c"]
        else:
            scc_args['scc_' + stage + '_tool']['values'] = ["openroad"]
            scc_args['scc_' + stage + '_opt']['values']  = ["-no_init", "-exit"]
    
    ###############
    #Execution Options
    scc_args['scc_jobs']={}
    scc_args['scc_jobs']['values']      = ["4"]
    scc_args['scc_jobs']['switch']      = "-j"
    scc_args['scc_jobs']['help']        = "Number of jobs to run simultaneously"

    scc_args['scc_effort']={}
    scc_args['scc_effort']['values']    = ["high"]
    scc_args['scc_effort']['switch']    = "-effort"
    scc_args['scc_effort']['help']      = "Compilation effort (low, medium, high)"

    scc_args['scc_priority']={}
    scc_args['scc_priority']['values']  = ["speed"]
    scc_args['scc_priority']['switch']  = "-priority"
    scc_args['scc_priority']['help']    = "Optimization priority (speed, area, power)"

    scc_args['scc_start']={}
    scc_args['scc_start']['values']     = ["import"]
    scc_args['scc_start']['switch']     = "-start"
    scc_args['scc_start']['help']       = "Stage to start with"

    scc_args['scc_stop']={}
    scc_args['scc_stop']['values']      = ["export"]
    scc_args['scc_stop']['switch']      = "-stop"
    scc_args['scc_stop']['help']        = "Stage to stop after"        

            
    ###############
    #Design
    scc_args['scc_source']={}
    scc_args['scc_source']['values']    = []
    scc_args['scc_source']['switch']    = ""
    scc_args['scc_source']['help']      = "Verilog source files (minimum one)"

    scc_args['scc_topmodule']={}
    scc_args['scc_topmodule']['values'] = []
    scc_args['scc_topmodule']['switch'] = "-topmodule"
    scc_args['scc_topmodule']['help']   = "Top module name"

    scc_args['scc_clk']={}
    scc_args['scc_clk']['values']       = []
    scc_args['scc_clk']['switch']       = "-clk"
    scc_args['scc_clk']['help']         = "Clock defintions"
    
    scc_args['scc_def']={}
    scc_args['scc_def']['values']       = []
    scc_args['scc_def']['switch']       = "-def"
    scc_args['scc_def']['help']         = "Physical floorplan (DEF) file"

    scc_args['scc_sdc']={}
    scc_args['scc_sdc']['values']       = []
    scc_args['scc_sdc']['switch']       = "-sdc"
    scc_args['scc_sdc']['help']         = "Constraints (SDC) file"

    scc_args['scc_upf']={}
    scc_args['scc_upf']['values']       = []
    scc_args['scc_upf']['switch']       = "-upf"
    scc_args['scc_upf']['help']         = "Unified power format (UPF) file"

    scc_args['scc_ydir']={}
    scc_args['scc_ydir']['values']      = []
    scc_args['scc_ydir']['switch']      = "-y"
    scc_args['scc_ydir']['help']        = "Directory to search for modules"

    scc_args['scc_vlib']={}
    scc_args['scc_vlib']['values']      = []
    scc_args['scc_vlib']['switch']      = "-v"
    scc_args['scc_vlib']['help']        = "Verilog library"

    scc_args['scc_libext']={}
    scc_args['scc_libext']['values']    = [".v", ".vh"]
    scc_args['scc_libext']['switch']    = "+libext"
    scc_args['scc_libext']['help']      = "Extensions for finding modules"

    scc_args['scc_idir']={}
    scc_args['scc_idir']['values']      = []
    scc_args['scc_idir']['switch']      = "-I"
    scc_args['scc_idir']['help']        = "Directory to search for includes"

    scc_args['scc_define']={}
    scc_args['scc_define']['values']    = []
    scc_args['scc_define']['switch']    = "-D"
    scc_args['scc_define']['help']      = "Defines for Verilog preprocessor"

    scc_args['scc_cmdfile']={}
    scc_args['scc_cmdfile']['values']   = []
    scc_args['scc_cmdfile']['switch']   = "-f"
    scc_args['scc_cmdfile']['help']     = "Parse options from file"

    scc_args['scc_wall']={}
    scc_args['scc_wall']['values']      = []
    scc_args['scc_wall']['switch']      = "-Wall"
    scc_args['scc_wall']['help']        = "Enable all style warnings"

    scc_args['scc_wno']={}
    scc_args['scc_wno']['values']       = []
    scc_args['scc_wno']['switch']       = "-Wno"
    scc_args['scc_wno']['help']         = "Disables a warning -Woo-<message>"

    return(scc_args)

def cfg_env():
    scc_args = {}
    scc_args['scc_ydir']      = os.getenv('SCC_YDIR')
    scc_args['scc_vlib']      = os.getenv('SCC_VLIB')
    scc_args['scc_idir']      = os.getenv('SCC_IDIR')
    scc_args['scc_libext']    = os.getenv('SCC_LIBEXT')
    scc_args['scc_cmdfile']   = os.getenv('SCC_CMDFILE')
    scc_args['scc_sdcfile']   = os.getenv('SCC_SDCFILE')
    scc_args['scc_flowname']  = os.getenv('SCC_FLOWNAME')
    scc_args['scc_techfile']  = os.getenv('SCC_TECHFILE')
    scc_args['scc_layermap']  = os.getenv('SCC_LAYERMAP')
    scc_args['scc_minlayer']  = os.getenv('SCC_MINLAYER')
    scc_args['scc_maxlayer']  = os.getenv('SCC_MAXLAYER')
    scc_args['scc_lib']       = os.getenv('SCC_LIB')
    scc_args['scc_scenario']  = os.getenv('SCC_SCENARIO')
    args['scc_effort']    = os.getenv('SCC_EFFORT')
    print(args)
    return(args)
def cfg_file():
    print("file")
def cfg_cmdline():
    print("command")
def cfg_merge(all_args):
    scc_args = {}
    print("merge")
    return(scc_args)
def cfg_print(scc_args):
    print(json.dumps(scc_args, sort_keys=True, indent=4))


############################
# COMMAND LINE SCRIPT
############################
if __name__ == "__main__":

    script_path = os.path.dirname(os.path.abspath(__file__))

    #1. Reading of config by priority
    scc_args  = {}
    scc_args  = cfg_default()          # set in scc.py 
    cfg_print(scc_args)                # print config
    sys.exit()

    scc_args  = cfg_env(scc_args)      # set in .bashrc
    scc_args  = cfg_cmdline(scc_args)  # set by all others 
 
    #2. Setup design
    design_import(scc_args, scc_args['scc_import_dir'])

    #3. Run compiler
    run(scc_args, "syn",     scc_args['scc_import_dir'],scc_args['scc_syn_dir'])
    run(scc_args, "place",   scc_args['scc_syn_dir'],scc_args['scc_place_dir'])
    run(scc_args, "cts",     scc_args['scc_place_dir'],scc_args['scc_cts_dir'])
    run(scc_args, "route",   scc_args['scc_cts_dir'],scc_args['scc_route_dir'])
    run(scc_args, "signoff", scc_args['scc_route_dir'],scc_args['scc_signoff_dir'])
    run(scc_args, "export",  scc_args['scc_signoff_dir'],scc_args['scc_export_dir'])


  
    ###########################################################################
    # Environment Configuration
    ###########################################################################
    
  
    
    print(scc_args)
    exit

    SCC_HOME     = os.getenv('SCC_HOME')
    SCC_YDIR     = os.getenv('SCC_YDIR')
    SCC_VLIST    = os.getenv('SCC_VLIST')
    SCC_IDIR     = os.getenv('SCC_IDIR')
    SCC_LIBXEXT  = os.getenv('SCC_LIBEXT')
    SCC_CMDFILE  = os.getenv('SCC_CMDFILE')

    SCC_SDCFILE  = os.getenv('SCC_SDCFILE')
    SCC_DEFFILE  = os.getenv('SCC_DEFFILE')
    SCC_UPFFILE  = os.getenv('SCC_UPFFILE')
    SCC_NDRFILE  = os.getenv('SCC_NDRFILE')

    SCC_FLOWNAME = os.getenv('SCC_FLOWNAME')
    SCC_TECHFILE = os.getenv('SCC_TECHFILE')
    SCC_MINLAYER = os.getenv('SCC_MINLAYER')
    SCC_MAXLAYER = os.getenv('SCC_MAXLAYER')
    SCC_LIBLIST  = os.getenv('SCC_LIBLIST')
    SCC_LIBPATHS = os.getenv('SCC_LIBPATHS')
    SCC_START    = os.getenv('SCC_START')
    SCC_END      = os.getenv('SCC_END')
    SCC_EFFORT   = os.getenv('SCC_EFFORT')

    SCC_FLOWNAME = os.getenv('SCC_FLOWNAME')
    
    ###########################################################################
    # Argument parser
    ###########################################################################

    parser = argparse.ArgumentParser(prog='scc',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=42),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection (SCC)")

    ###########################################################################
    # Source files (at least one required)
    ###########################################################################

    parser.add_argument('sourcefiles',
                        nargs='*',
                        help='Verilog source files')

    ###########################################################################
    # Optional Global Arguments
    ###########################################################################

    #-t option needed in all but trivial "hello world single module designs
    parser.add_argument('-t',
                        dest='module',
                        action='store',
                        help='Top module name ("design")')

    parser.add_argument('-cfg',
                        dest='cfgfile',
                        action="store",
                        help='Configuration in json file format')
    
    parser.add_argument('-o',
                        dest='output',
                        action="store",
                        help='Root name for output files')
        
    parser.add_argument('-j',
                        dest='jobs',
                        action='store',
                        help='Number of jobs to run simultaneously')

    ###########################################################################
    # Optional Verilator Arguments
    ###########################################################################

    parser.add_argument('-y',
                        dest='ydir',
                        action='append',
                        help='Directory to search for modules')

    parser.add_argument('+libext', 
                        dest='libext',
                        action='append',
                        help='Specify signal as a clock')
    
    parser.add_argument('-v', 
                        dest='vlist',
                        action='append',
                        help='Verilog library files')

    parser.add_argument('-I', 
                        dest='idir',
                        action='append',
                        help='Directory to search for includes')
        
    parser.add_argument('-D',
                        dest='define',
                        action='append',
                        help='Set preprocessor define')

    parser.add_argument('-Wno-', 
                        dest='message',
                        action='append',
                        help='Disables warning <MESSAGE> !!!!FIX!!!!!')

    parser.add_argument('-clk', 
                        dest='clkname',
                        action='append',
                        help='Specify signal as a clock')

    parser.add_argument('-f', 
                        dest='cmdfile',
                        action='store',
                        help='Parse options from a file')

    ###########################################################################
    # Synthesis/Place and Route Arguments
    ###########################################################################

    parser.add_argument('-sdc', 
                        dest='sdcfile',
                        action='append',
                        help='Timing constraints in SDC format')

    parser.add_argument('-def',
                        dest='deffile',
                        action='append',
                        help='Floor-plan in DEF format')

    parser.add_argument('-upf', 
                        dest='upffile',
                        action='append',
                        help='Power file in UPF format')

    parser.add_argument('-ndr',
                        dest='ndrsignal',
                        action='append',
                        help='Non-default routed signals')
    
    parser.add_argument('-techfile',
                        dest='techfile',
                        action='store',
                        help='Place and route setup file')
    
    parser.add_argument('-flow', 
                        dest='flowname',
                        action='store',
                        help='Named eda/compiler flow')

    parser.add_argument('-min', 
                        dest='minlayer',
                        action='store',
                        help='Minimum routing layer')

    parser.add_argument('-max', 
                        dest='maxlayer',
                        action='store',
                        help='Maximum routing layer')
    
    parser.add_argument('-lib', 
                        dest='liblist',
                        action='append',
                        help='Synthesis Libary')

    parser.add_argument('-libpath', 
                        dest='libpathlist',
                        action='append',
                        help='Synthesis Libary Search Paths')

    parser.add_argument('-start', 
                        dest='startstep',
                        action='store',
                        help=' Name of PNR starting step')

    parser.add_argument('-end',
                        dest='endstep',
                        action='store',
                        help=' Name of PNR ending step')

    parser.add_argument('-effort',
                        dest='effort',
                        action='store',
                        help='Compilation effort')
    
    ###########################################################################
    # Library Arguments
    ###########################################################################
    
    parser.add_argument('-height', 
                        dest='libheight',
                        action='store',
                        help='Height of library (in grids)')

    parser.add_argument('-driver', 
                        dest='defaultdriver',
                        action='store',
                        help='Name of default driver cell')

    parser.add_argument('-icg', 
                        dest='icglist',
                        action='append',
                        help='List of ICG cells')
    
    parser.add_argument('-tielo', 
                        dest='tielolist',
                        action='append',
                        help='List of tie to 0 cells')
    
    parser.add_argument('-tielhi', 
                        dest='tiehilist',
                        action='append',
                        help='List of tie to 1 cells')
    
    parser.add_argument('-antenna', 
                        dest='antennalist',
                        action='append',
                        help='List of antenna fix cells')

    parser.add_argument('-dcap', 
                        dest='dcaplist',
                        action='append',
                        help='List of decoupling-cap cells')

    parser.add_argument('-filler', 
                        dest='fillerlist',
                        action='append',
                        help='List of filler cells')
    
    parser.add_argument('-dontuse', 
                        dest='dontuselist',
                        action='append',
                        help='List of cells to ignore')
    
    ###########################################################################
    # Parse arguments
    ###########################################################################
   
    args = parser.parse_args()

    ###########################################################################
    # Merge Command Line, Environment, and Configuration Into One Structure
    ###########################################################################

    print(args)

    mytcl = "generated_setup.tcl"

    f = open(mytcl, "w")
    
    f.write("Woops! I have deleted the content!")
    f.close()
    
    ###########################################################################
    # Run Verilator Preprocessor/Linter
    ###########################################################################
    #stdout=subprocess.DEVNULL,
    #stderr=subprocess.DEVNULL)
    
    #Creating a verilator compatible command based on arguments
    verilator_cmd = ' '.join(['verilator',
                              '--lint-only',
                              '--debug',
                              ' '.join(args.sourcefiles),
                              ' -y '.join(args.ydir),
                              ' -v '.join(args.vlist),
                              ' -I'.join(args.idir)])

    error = subprocess.run(verilator_cmd, shell=True)

    #Concatenating all pre-processed files for synthesis
    cat_cmd = 'cat obj_dir/*.vpp > output.vpp'
    error = subprocess.run(cat_cmd, shell=True)

    ###########################################################################
    # Run Synthesis
    #
    ###########################################################################
        
    cmd_file = SCC_HOME + "/third_party/edalib/yosys/default.tcl"

    yosys_cmd = ' '.join(['yosys', '-c', cmd_file])
                          
    error = subprocess.run(yosys_cmd, shell=True)






