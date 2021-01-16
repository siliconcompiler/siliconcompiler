# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import re
import argparse

###########################
def cmdline():
    '''Handles the command line configuration usign argparse. 
    All configuration parameters are exposed at the command line interface.

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
        elif default_cfg[key]['type'] in {"int", "float", "string"}:
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
    
    ############################################
    # Paths
    #############################################

    install_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = re.sub("siliconcompiler/siliconcompiler", "siliconcompiler", install_dir, 1)
    scripts_dir  = root_dir + "/edalib/"
    pdklib = root_dir + "/pdklib/virtual/nangate45/r1p0/pnr/"
    iplib = root_dir + "/iplib/virtual/nangate45/NangateOpenCellLibrary/r1p0/"

    #Core dictionary
    default_cfg = {}

    ############################################
    # Individual stages supported by "run"
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
                    "pex",
                    "lec",
                    "sta",
                    "pi",
                    "si",
                    "drc",
                    "lvs",
                    "export"]
    }
    
    ############################################
    # General Settings
    #############################################

 
    default_cfg['sc_cfgfile'] = {
        'help' : "Loads configurations from a json file",
        'type' : "file",
        'switch' : "-cfgfile",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_custom'] = {
        'help' : "Custom pass through variables (eg: EDA_EFFORT enable_ludicrous_speed)",
        'type' : "list",
        'switch' : "-custom",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_mode'] = {
        'help' : "Implementation mode (asic or fpga)",
        'type' : "string",
        'switch' : "-mode",
        'values' : "asic"
    }
  
   
    ############################################
    # Remote abstracted exeuction settings
    #############################################

    default_cfg['sc_remote'] = {
        'help' : "Name of remote server address (https://acme.com)",
        'type' : "string",
        'switch' : "-remote",
        'values' : ""
    }
    
    default_cfg['sc_foundry'] = {
        'help' : "Foundry name (eg: virtual, tsmc, gf, samsung)",
        'type' : "string",
        'switch' : "-foundry",
        'values' : "virtual"
    }
    
    default_cfg['sc_process'] = {
        'help' : "Process name",
        'type' : "string",
        'switch' : "-process",
        'values' : "nangate45"
    }

    default_cfg['sc_ref'] = {
        'help' : "Reference methodology name ",
        'type' : "string",
        'switch' : "-ref",
        'values' : ""
    }
    
    ############################################
    # Process Node
    #############################################

    default_cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file (lef or tf)",
        'type' : "file",
        'switch' : "-techfile",
        'values' : [pdklib + "nangate45.tech.lef"],
        'hash'   : []
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
    
    default_cfg['sc_model'] = {
        'help' : "Spice model file",
        'type' : "file",
        'switch' : "-model",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_scenario'] = {
        'help' : "Process,voltage,temp scenario (eg: tt 0.7 25 setup)",
        'type' : "list",
        'switch' : "-scenario",
               #   corner  #voltage  #temp #opt/signoff  #setup/hold/power     
        'values' : ["tt      1.0       25    all           all",
                    "ff      1.1       -40   opt           hold",
                    "ff      1.1       125   opt           power",
                    "ss      0.9       125   signoff       setup"]

    }

    default_cfg['sc_layermap'] = {
        'help' : "GDS layer map",
        'type' : "file",
        'switch' : "-layermap",
        'values' : [],
        'hash' : []
    }

    ############################################
    # Standard Cell Libraries
    #############################################

    default_cfg['sc_lib'] = {
        'help' : "Standard cell libraries",
        'type' : "file",
        'switch' : "-lib",
        'values' : [iplib + "lib/NangateOpenCellLibrary_typical.lib"],
        'hash'   : []
    }

    default_cfg['sc_lef'] = {
        'help' : "LEF files",
        'type' : "file",
        'switch' : "-lef",
        'values' : [iplib + "lef/NangateOpenCellLibrary.macro.lef"],
        'hash'   : []
    }

    default_cfg['sc_gds'] = {
        'help' : "GDS files",
        'type' : "file",
        'switch' : "-gds",
        'values' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'hash'   : []
    }

    default_cfg['sc_cdl'] = {
        'help' : "Netlist files (CDL)",
        'type' : "file",
        'switch' : "-cdl",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_libsetup'] = {
        'help' : "Library setup file for PNR tool",
        'type' : "string",
        'switch' : "-libsetup",
        'values' : [],
        'hash'   : []
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

    default_cfg['sc_msgaddr'] = {
        'help' : "Address (phone/email) for job completion notifications",
        'type' : "string",
        'switch' : "-msgaddr",
        'values' : ""
    }

    default_cfg['sc_msgstage'] = {
        'help' : "List of stages that trigger job completion notifications",
        'type' : "list",
        'switch' : "-msgstage",
        'values' : ["export"]
    }

    ############################################
    # Design Specific Source Code Parameters
    #############################################

    default_cfg['sc_source'] = {
        'help' : "Source files (.v/.vh/.sv/.vhd)",
        'type' : "file",
        'switch' : "None",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_design'] = {
        'help' : "Design top module name",
        'type' : "string",
        'switch' : "-design",
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
        'type' : "file",
        'switch' : "-y",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_idir'] = {
        'help' : "Directory to search for inclodes",
        'type' : "file",
        'switch' : "-I",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_vlib'] = {
        'help' : "Library file",
        'type' : "file",
        'switch' : "-v",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_libext'] = {
        'help' : "Extension for finding modules",
        'type' : "list",
        'switch' : "+libext",
        'values' : [".v", ".vh", ".sv", ".vhd"]
    }

    default_cfg['sc_cmdfile'] = {
        'help' : "Parse source options from command file",
        'type' : "file",
        'switch' : "-f",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_wall'] = {
        'help' : "Enable all lint style warnings",
        'type' : "string",
        'switch' : "-Wall",
        'values' : ""
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
        'switch' : "-aspectratio",
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
        'type' : "file",
        'switch' : "-floorplan",
        'values' : [],
        'hash'   : []
    }
    
    default_cfg['sc_def'] = {
        'help' : "User supplied hard-coded floorplan (DEF)",
        'type' : "file",
        'switch' : "-def",
        'values' : [],
        'hash'   : []
    }
    
    default_cfg['sc_constraints'] = {
        'help' : "Timing constraints file (SDC)",
        'type' : "file",
        'switch' : "-constraints",
        'values' : [],
        'hash'   : []
    }
    
    default_cfg['sc_ndr'] = {
        'help' : "Non-default net routing file",
        'type' : "file",
        'switch' : "-ndr",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_upf'] = {
        'help' : "Unified power format (UPF) file",
        'type' : "file",
        'switch' : "-upf",
        'values' : [],
        'hash'   : []
    }

    default_cfg['sc_vcd'] = {
        'help' : "Value Change Dump (VCD) file for power analysis",
        'type' : "file",
        'switch' : "-vcd",
        'values' : [],
        'hash'   : []
    }

    ############################################
    # Tool Configuration
    #############################################

    for stage in default_cfg['sc_stages']['values']:
        
        #init dict
        default_cfg['sc_' + stage + '_tool'] = {}
        default_cfg['sc_' + stage + '_opt'] = {}
        default_cfg['sc_' + stage + '_script'] = {}
        default_cfg['sc_' + stage + '_jobid'] = {}
        default_cfg['sc_' + stage + '_np'] = {}

        #descriptions
        default_cfg['sc_' + stage + '_tool']['help'] = "Name of tool for " + stage + " stage"
        default_cfg['sc_' + stage + '_opt']['help'] = "Options for " + stage + " stage executable" 
        default_cfg['sc_' + stage + '_script']['help'] = "Run script for " + stage + " stage"
        default_cfg['sc_' + stage + '_jobid']['help'] = "Index of last executed job in " + stage + " stage"
        default_cfg['sc_' + stage + '_np']['help'] = "Thread parallelism for " + stage + " stage"

        #type
        default_cfg['sc_' + stage + '_tool']['type'] = "string"
        default_cfg['sc_' + stage + '_opt']['type'] = "list"
        default_cfg['sc_' + stage + '_script']['type'] = "file"
        default_cfg['sc_' + stage + '_jobid']['type'] = "int"
        default_cfg['sc_' + stage + '_np']['type'] = "int"

        #hash
        default_cfg['sc_' + stage + '_script']['hash'] = []
        
        #command line switches
        default_cfg['sc_' + stage + '_tool']['switch'] = "-" + stage + "_tool"
        default_cfg['sc_' + stage + '_opt']['switch'] = "-" + stage + "_opt"
        default_cfg['sc_' + stage + '_script']['switch'] = "-" + stage + "_script"
        default_cfg['sc_' + stage + '_jobid']['switch'] = "-" + stage + "_jobid"
        default_cfg['sc_' + stage + '_np']['switch'] = "-" + stage + "_np"

        #Common values
        default_cfg['sc_' + stage + '_jobid']['values'] = 0
        default_cfg['sc_' + stage + '_np']['values'] = 4

        #Tool specific values
        default_script = scripts_dir + default_cfg['sc_mode']['values'] + "/sc_" + stage + ".tcl"
        if stage == "import":
            default_cfg['sc_import_tool']['values'] = "verilator"
            default_cfg['sc_import_opt']['values'] = ["--lint-only", "--debug"]
            default_cfg['sc_import_script']['values'] = []
        elif stage == "syn":
            default_cfg['sc_syn_tool']['values'] = "yosys"
            default_cfg['sc_syn_opt']['values'] = ["-c"]
            default_cfg['sc_syn_script']['values'] = [default_script]
        else:
            default_cfg['sc_' + stage + '_tool']['values'] = "openroad"
            default_cfg['sc_' + stage + '_opt']['values'] = ["-no_init", "-exit"]
            default_cfg['sc_' + stage + '_script']['values'] = [default_script]
            
    return default_cfg

