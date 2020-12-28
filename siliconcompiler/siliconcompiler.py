# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import subprocess
import sys
import argparse
import os

if __name__ == "__main__":

    ###########################################################################
    # Variable Priorities
    ###########################################################################

    # 1. Environment (lowest)
    # 2. -cfg json file
    # 3. Command line flags (higheset)
        
    ###########################################################################
    # Environment Variables
    ###########################################################################

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
                        default="",
                        action='store',
                        help='Top module name ("design")')

    parser.add_argument('-cfg',
                        dest='cfgfile',
                        default="",
                        action="store",
                        help='Configuration in json file format')
    
    parser.add_argument('-o',
                        dest='output',
                        default="output",
                        action="store",
                        help='Root name for output files')
        
    parser.add_argument('-j',
                        dest='jobs',
                        default=1,
                        action='store',
                        help='Number of jobs to run simultaneously')

    ###########################################################################
    # Optional Verilator Arguments
    ###########################################################################

    parser.add_argument('-y',
                        dest='ydir',
                        default=[],
                        action='append',
                        help='Directory to search for modules')

    parser.add_argument('+libext', 
                        dest='libext',
                        default=[],
                        action='append',
                        help='Specify signal as a clock')
    
    parser.add_argument('-v', 
                        dest='vlist',
                        default=[],
                        action='append',
                        help='Verilog library files')

    parser.add_argument('-I', 
                        dest='idir',
                        default=[],
                        action='append',
                        help='Directory to search for includes')
        
    parser.add_argument('-D',
                        dest='define',
                        default=[],
                        action='append',
                        help='Set preprocessor define')

    parser.add_argument('-Wno-', 
                        dest='message',
                        default=[],
                        action='append',
                        help='Disables warning <MESSAGE> !!!!FIX!!!!!')

    parser.add_argument('-clk', 
                        dest='clkname',
                        default=[],
                        action='append',
                        help='Specify signal as a clock')

    parser.add_argument('-f', 
                        dest='cmdfile',
                        default=[],
                        action='store',
                        help='Parse options from a file')

    ###########################################################################
    # Synthesis/Place and Route Arguments
    ###########################################################################

    parser.add_argument('-sdc', 
                        dest='sdcfile',
                        default=[],
                        action='append',
                        help='Timing constraints in SDC format')

    parser.add_argument('-def',
                        dest='deffile',
                        default=[],
                        action='append',
                        help='Floor-plan in DEF format')

    parser.add_argument('-upf', 
                        dest='upffile',
                        default=[],
                        action='append',
                        help='Power file in UPF format')

    parser.add_argument('-ndr',
                        dest='ndrsignal',
                        default=[],
                        action='append',
                        help='Non-default routed signals')
    
    parser.add_argument('-techfile',
                        dest='techfile',
                        default="",
                        action='store',
                        help='Place and route setup file')
    
    parser.add_argument('-flow', 
                        dest='flowname',
                        default="openroad",
                        action='store',
                        help='Named eda/compiler flow')

    parser.add_argument('-min', 
                        dest='minlayer',
                        default="",
                        action='store',
                        help='Minimum routing layer')

    parser.add_argument('-max', 
                        dest='maxlayer',
                        default="",
                        action='store',
                        help='Maximum routing layer')
    
    parser.add_argument('-lib', 
                        dest='liblist',
                        default=[],
                        action='append',
                        help='Synthesis Libary')

    parser.add_argument('-libpath', 
                        dest='libpathlist',
                        default=[],
                        action='append',
                        help='Synthesis Libary Search Paths')

    parser.add_argument('-start', 
                        dest='startstep',
                        default="init",
                        action='store',
                        help=' Name of PNR starting step')

    parser.add_argument('-end',
                        dest='endstep',
                        default="export",
                        action='store',
                        help=' Name of PNR ending step')

    parser.add_argument('-effort',
                        dest='effort',
                        default="high",
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
                        default=[],
                        action='append',
                        help='List of ICG cells')
    
    parser.add_argument('-tielo', 
                        dest='tielolist',
                        default=[],
                        action='append',
                        help='List of tie to 0 cells')
    
    parser.add_argument('-tielhi', 
                        dest='tiehilist',
                        default=[],
                        action='append',
                        help='List of tie to 1 cells')
    
    parser.add_argument('-antenna', 
                        dest='antennalist',
                        default=[],
                        action='append',
                        help='List of antenna fix cells')

    parser.add_argument('-dcap', 
                        dest='dcaplist',
                        default=[],
                        action='append',
                        help='List of decoupling-cap cells')

    parser.add_argument('-filler', 
                        dest='fillerlist',
                        default=[],
                        action='append',
                        help='List of filler cells')
    
    parser.add_argument('-dontuse', 
                        dest='dontuselist',
                        default=[],
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
    exit

    ###########################################################################
    # Run Verilator Preprocessor/Linter
    ###########################################################################

    #Creating a verilator compatible command based on arguments
    verilator_cmd = ' '.join(['verilator',
                              '--lint-only',
                              '--debug',
                              ' '.join(args.sourcefiles),
                              ' -y '.join(args.ydir),
                              ' -v '.join(args.vlist),
                              ' -I'.join(args.idir)])

    error = subprocess.run(verilator_cmd,
                           shell=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
                           
    #Concatenating all pre-processed files for synthesis
    error = subprocess.run('cat obj_dir/*.vpp > output.vpp',
                           shell=True)

    ###########################################################################
    # Run Synthesis
    ###########################################################################
    
