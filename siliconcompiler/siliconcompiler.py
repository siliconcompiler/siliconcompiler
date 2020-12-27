# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

if __name__ == "__main__":
    
    import argparse
    
    #Creating parser
    parser = argparse.ArgumentParser(description="Silicon Compiler")

    ###########################################################################
    # Positional Argument (required)
    ###########################################################################

    parser.add_argument("file(s).v", 
                        help='Verilog source files')

    ###########################################################################
    # Optional Global Arguments
    ###########################################################################

    #-t option needed in all but trivial "hello world single module designs
    parser.add_argument('-t', action='store',
                        dest='module',
                        default="",
                        help='Top module name ("design")')

    parser.add_argument('-cfg', action="store",
                        dest='jsoncfg',
                        default="",
                        help='Name of Root name for output files')
    
    
    parser.add_argument('-o', action="store",
                        dest='output',
                        default="output",
                        help='Root name for output files')
        
    parser.add_argument('-j', action='store',
                        dest='jobs',
                        default=1,
                        help='Number of jobs (commands) to run simultaneously')

    ###########################################################################
    # Optional Verilator Arguments
    ###########################################################################

    parser.add_argument('-y', action='append',
                        dest='ydir',
                        default=[],
                        help='Directory to search for modules')
    
    parser.add_argument('-v', action='append',
                        dest='vlist',
                        default=[],
                        help='Verilog library files')

    parser.add_argument('-I', action='append',
                        dest='idir',
                        default=[],
                        help='Directory to search for includes')
    
    parser.add_argument('-f', action='store',
                        dest='cmdfile',
                        default=[],
                        help='Parse options from a file')
    
    parser.add_argument('-D', action='store',
                        dest='define',
                        default=[],
                        help='Set preprocessor define')

    parser.add_argument('-Wno-', action='append',
                        dest='message',
                        default=[],
                        help='Disables warning <MESSAGE> !!!!FIX!!!!!')

    parser.add_argument('-clk', action='append',
                        dest='message',
                        default=[],
                        help='Specify signal as a clock')
    
    ###########################################################################
    # Synthesis/PD Arguments
    ###########################################################################

    parser.add_argument('-sdc', action='store',
                        dest='sdcfile',
                        default="",
                        help='Timing constraints in SDC format')

    parser.add_argument('-def', action='store',
                        dest='deffile',
                        default="",
                        help='Floor-plan in DEF format')

    parser.add_argument('-upf', action='append',
                        dest='upffile',
                        default="",
                        help='Power file in UPF format')

    parser.add_argument('-ndr', action='append',
                        dest='ndrsignal',
                        default=[],
                        help='Non-default routed signals')
    
    parser.add_argument('-techfile', action='store',
                        dest='techfile',
                        default="",
                        help='Place and route setup file')
    
    parser.add_argument('-flow', action='store',
                        dest='edaflow',
                        default="openroad",
                        help='Name of synthesis and place and route flow')

    parser.add_argument('-min', action='store',
                        dest='minlayer',
                        default="M2",
                        help='Minimum routing layer')

    parser.add_argument('-max', action='store',
                        dest='maxlayer',
                        default="",
                        help='Maximum routing layer')
    
    parser.add_argument('-lib', action='append',
                        dest='liblist',
                        default=[],
                        help='Synthesis/PNR Libary')

    parser.add_argument('-libpath', action='append',
                        dest='libpathlist',
                        default=[],
                        help='Synthesis/PNR Libary Search Paths')

    parser.add_argument('-start', action='append',
                        dest='startstep',
                        default=[],
                        help=' Name of PNR starting step')

    parser.add_argument('-end', action='append',
                        dest='endstep',
                        default=[],
                        help=' Name of PNR ending step')

    parser.add_argument('-effort', action='store',
                        dest='effort',
                        help='Compilation effort')
    
    ###########################################################################
    # Library Arguments
    ###########################################################################
    
    parser.add_argument('-height', action='store',
                        dest='libheight',
                        help='Height of library (in grids)')

    parser.add_argument('-driver', action='store',
                        dest='defaultdriver',
                        help='Name of default driver cell')

    parser.add_argument('-icg', action='append',
                        dest='icglist',
                        default=[],
                        help='List of ICG cells')
    
    parser.add_argument('-tielo', action='append',
                        dest='tielolist',
                        default=[],
                        help='List of tie to 0 cells')
    
    parser.add_argument('-tielhi', action='append',
                        dest='tiehilist',
                        default=[],
                        help='List of tie to 1 cells')
    
    parser.add_argument('-antenna', action='append',
                        dest='antennalist',
                        default=[],
                        help='List of antenna fix cells')

    parser.add_argument('-dcap', action='append',
                        dest='dcaplist',
                        default=[],
                        help='List of decoupling-cap cells')

    parser.add_argument('-filler', action='append',
                        dest='fillerlist',
                        default=[],
                        help='List of filler cells')
    
    parser.add_argument('-dontuse', action='append',
                        dest='dontuselist',
                        default=[],
                        help='List of cells to ignore')
    

    ###########################################################################
    # Parse arguments
    ###########################################################################
   
    args = parser.parse_args()

    print(args)
