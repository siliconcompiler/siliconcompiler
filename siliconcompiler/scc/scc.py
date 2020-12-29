# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import sys
import argparse
import os
import re

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

    args = {}
    args['scc_import_dir']     = "build/import"
    args['scc_syn_tool']       = "yosys -c"
    args['scc_syn_script']     = install_dir + "asic/syn.tcl"
    args['scc_syn_dir']        = "build/syn"
    args['scc_place_tool']     = "openroad -no_init -exit"
    args['scc_place_dir']      = "build/place"
    args['scc_place_script']   = install_dir + "asic/place.tcl"
    args['scc_cts_tool']       = "openroad -no_init -exit"
    args['scc_cts_script']     = install_dir + "asic/cts.tcl"
    args['scc_cts_dir']        = "build/cts"
    args['scc_route_tool']     = "openroad -no_init -exit"
    args['scc_route_script']   = install_dir + "asic/route.tcl"
    args['scc_route_dir']      = "build/route"
    args['scc_signoff_tool']   = "openroad -no_init -exit"
    args['scc_signoff_script'] = install_dir + "asic/signoff.tcl"
    args['scc_signoff_dir']    = "build/signoff"
    args['scc_export_tool']    = "openroad -no_init -exit"
    args['scc_export_script']  = install_dir + "asic/export.tcl"
    args['scc_export_dir']     = "build/export"
    args['scc_techfile']       = pdklib + "nangate45.tech.lef"
    args['scc_lib']            = iplib + "NangateOpenCellLibrary_typical.lib"
    args['scc_minlayer']       = "M2"
    args['scc_maxlayer']       = "M5"
    args['scc_effort']         = "high"
    args['scc_output']         = "output"
    args['scc_jobs']           = 4
    args['scc_start']          = "init"
    args['scc_end']            = "export"

    print(args)
    return(args)

def cfg_env():
    args = {}
    args['scc_ydir']      = os.getenv('SCC_YDIR')
    args['scc_vlib']      = os.getenv('SCC_VLIB')
    args['scc_idir']      = os.getenv('SCC_IDIR')
    args['scc_libext']    = os.getenv('SCC_LIBEXT')
    args['scc_cmdfile']   = os.getenv('SCC_CMDFILE')
    args['scc_sdcfile']   = os.getenv('SCC_SDCFILE')
    args['scc_flowname']  = os.getenv('SCC_FLOWNAME')
    args['scc_techfile']  = os.getenv('SCC_TECHFILE')
    args['scc_layermap']  = os.getenv('SCC_LAYERMAP')
    args['scc_minlayer']  = os.getenv('SCC_MINLAYER')
    args['scc_maxlayer']  = os.getenv('SCC_MAXLAYER')
    args['scc_lib']       = os.getenv('SCC_LIB')
    args['scc_scenario']  = os.getenv('SCC_SCENARIO')
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
def cfg_print():
    print("print")

############################
# COMMAND LINE SCRIPT
############################
if __name__ == "__main__":

    script_path = os.path.dirname(os.path.abspath(__file__))

    #1. Reading of config into mega dictionary
    all_args = {}
    all_args['default']  = cfg_default()  # set in scc.py 
    all_args['env']      = cfg_env()      # set in .bashrc
    all_args['file']     = cfg_file()     # set by -cfg
    all_args['cmdline']  = cfg_cmdline()  # set by all others 
 
    #2. Prioritized merge of all values
    scc_args = cfg_merge(all_args)

    #3. Setup design
    design_import(scc_args, scc_args['scc_import_dir'])

    #4. Run thhrough compiler
    run(scc_args, "syn",     scc_args['scc_import_dir'],scc_args['scc_syn_dir'])
    run(scc_args, "place",   scc_args['scc_syn_dir'],scc_args['scc_place_dir'])
    run(scc_args, "cts",     scc_args['scc_place_dir'],scc_args['scc_cts_dir'])
    run(scc_args, "route",   scc_args['scc_cts_dir'],scc_args['scc_route_dir'])
    run(scc_args, "signoff", scc_args['scc_route_dir'],scc_args['scc_signoff_dir'])
    run(scc_args, "export",  scc_args['scc_signoff_dir'],scc_args['scc_export_dir'])
    sys.exit()
  
    
    ###########################################################################
    # Shared argument structure for all tools
    # 1. SCC Default (lowest)
    # 2. Environment
    # 3. -cfg json file
    # 4. Command line flags (highest)    
    ###########################################################################

    scc_args = {}

    ###########################################################################
    # Defaults
    ###########################################################################

    scc_args['default'] = {}

  
    
    
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






