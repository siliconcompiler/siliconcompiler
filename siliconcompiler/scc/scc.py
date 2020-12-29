# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import sys
import argparse
import os
import re

 ###########################################################################
 # Deriving install directory
 ###########################################################################
script_path = os.path.dirname(os.path.abspath(__file__))


if __name__ == "__main__":

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

    install_dir = os.path.dirname(os.path.abspath(__file__))
    install_dir = re.sub("siliconcompiler/siliconcompiler", "siliconcompiler",install_dir,1)
    pdklib      = install_dir + "/third_party/pdklib/"
    iplib       = install_dir + "/third_party/iplib/"
    edalib      = install_dir + "/third_party/edalib/"

    scc_args['default']['scc_flow_init']   = "scc"
    scc_args['default']['scc_flow_syn']    = "scc"
    scc_args['default']['scc_flow_place']  = "scc"
    scc_args['default']['scc_flow_cts']    = "scc"
    scc_args['default']['scc_flow_route']  = "scc"
    scc_args['default']['scc_flow_finish'] = "scc"

    scc_args['default']['scc_techfile']    = pdklib + "virtual/nangate45/r1p0/pnr/nangate45.tech.lef"
    scc_args['default']['scc_lib']         = iplib + "virtual/nangate45/NangateOpenCellLibrary/r1p0/lib/NangateOpenCellLibrary_typical.lib"
    scc_args['default']['scc_minlayer']    = "M2"
    scc_args['default']['scc_maxlayer']    = "M5"
    scc_args['default']['effort']          = "high"
    scc_args['default']['scc_output']      = "output"
    scc_args['default']['scc_jobs']        = 1
    scc_args['default']['scc_start']       = "init"
    scc_args['default']['scc_end']         = "export"
    
    
    ###########################################################################
    # Environment Configuration
    ###########################################################################
    
    scc_args['env']['scc_home']      = os.getenv('SCC_HOME')
    scc_args['env']['scc_ydir']      = os.getenv('SCC_YDIR')
    scc_args['env']['scc_vlib']      = os.getenv('SCC_VLIB')
    scc_args['env']['scc_idir']      = os.getenv('SCC_IDIR')
    scc_args['env']['scc_libext']    = os.getenv('SCC_LIBEXT')
    scc_args['env']['scc_cmdfile']   = os.getenv('SCC_CMDFILE')
    scc_args['env']['scc_sdcfile']   = os.getenv('SCC_SDCFILE')
    scc_args['env']['scc_flowname']  = os.getenv('SCC_FLOWNAME')
    scc_args['env']['scc_techfile']  = os.getenv('SCC_TECHFILE')
    scc_args['env']['scc_layermap']  = os.getenv('SCC_LAYERMAP')
    scc_args['env']['scc_minlayer']  = os.getenv('SCC_MINLAYER')
    scc_args['env']['scc_maxlayer']  = os.getenv('SCC_MAXLAYER')
    scc_args['env']['scc_lib']       = os.getenv('SCC_LIB')
    scc_args['env']['scc_scenario']  = os.getenv('SCC_SCENARIO')
    scc_args['env']['scc_effort']    = os.getenv('SCC_EFFORT')
    
    
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






