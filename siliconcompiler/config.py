# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import re
import argparse

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
        'default' : ["import",
                     "syn",
                     "floorplan",
                     "place",
                     "cts",
                     "route",
                     "signoff",
                     "export",
                     "lec",
                     "pex",
                     "sta",
                     "pi",
                     "si",
                     "drc",
                     "antenna",
                     "density",
                     "erc",                    
                     "lvs",
                     "tapeout"],
        'value' : []
    }

    ############################################
    # General Settings
    #############################################

    default_cfg['sc_cfgfile'] = {
        'help' : "Loads configurations from a json file",
        'type' : "file",
        'switch' : "-cfgfile",
        'default' : [],
        'value' : [],
        'hash'   : []
    }

    default_cfg['sc_mode'] = {
        'help' : "Implementation mode (asic or fpga)",
        'type' : "string",
        'switch' : "-mode",
        'default' : "asic",
        'value' : []        
    }

    ############################################
    # Framework Adoption/Translation
    #############################################
    
    
    default_cfg['sc_custom'] = {
        'help' : "Custom EDA pass through variables",
        'type' : "list",
        'switch' : "-custom",
        'default' : [],
        'value' : []        
    }

    default_cfg['sc_keymap'] = {
        'help' : "Framwork keyword translation table",
        'type' : "list",
        'switch' : "-keymap",
        'default' : [],
        'value' : []        
    }
      
    ############################################
    # Remote exeuction settings
    #############################################

    default_cfg['sc_remote'] = {
        'help' : "Name of remote server address (https://acme.com:8080)",
        'type' : "string",
        'switch' : "-remote",
        'default' : "",
        'value' : ""
        
    }
  
    default_cfg['sc_ref'] = {
        'help' : "Reference methodology name ",
        'type' : "string",
        'switch' : "-ref",
        'default' : "nangate45",
        'value' : ""
    }
    
    ############################################
    # Technology setup
    #############################################
      
    default_cfg['sc_foundry'] = {
        'help' : "Foundry name (eg: virtual, tsmc, gf, samsung)",
        'type' : "string",
        'switch' : "-foundry",
        'default' : "virtual",
        'value' : ""
    }
    
    default_cfg['sc_process'] = {
        'help' : "Process name",
        'type' : "string",
        'switch' : "-process",
        'default' : "nangate45",
        'value' : ""
    }

    default_cfg['sc_node'] = {
        'help' : "Effective process node in nm (180, 90, 22, 12, 7 etc)",
        'type' : "string",
        'switch' : "-node",
        'default' : "45",
        'value' : ""
    }
    
    default_cfg['sc_metalstack'] = {
        'help' : "Metal stack as named in the PDK",
        'type' : "string",
        'switch' : "-metalstack",
        'default' : "",
        'value' : ""
    }
    
    default_cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file (lef or tf)",
        'type' : "file",
        'switch' : "-techfile",
        'default' : [pdklib + "nangate45.tech.lef"],
        'value' : [],
        'hash'   : []
    }

    default_cfg['sc_rcfile'] = {
        'help' : "RC extraction file",
        'type' : "file",
        'switch' : "-rcfile",
        'default' : [],
        'value' : [],
        'hash'   : []
    }

    default_cfg['sc_layer'] = {
        'help' : "Routing layer definitions (eg: metal1 X 0.095 0.19) ",
        'type' : "list",
        'switch' : "-layer",
        'default' : ["metal1 X 0.095 0.19",
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
                     "metal10 Y 0.07 1.6"],
        'value' : []
    }
    #TODO: Fix, layer
    default_cfg['sc_scenario'] = {
        'help' : "Process,voltage,temp scenario (eg: tt 0.7 25 setup)",
        'type' : "list",
        'switch' : "-scenario",
               #     procr  #voltage  #temp #opt/signoff  #setup/hold/power     
        'default' : ["tt      1.0       25    all           all",
                    "ff      1.1       -40   opt           hold",
                    "ff      1.1       125   opt           power",
                     "ss      0.9       125   signoff       setup"],
        'value' : []

    }

    default_cfg['sc_layermap'] = {
        'help' : "GDS layer map",
        'type' : "file",
        'switch' : "-layermap",
        'default' : [],
        'value' : [],
        'hash' : []
    }

    default_cfg['sc_model'] = {
        'help' : "Spice model file",
        'type' : "file",
        'switch' : "-model",
        'default' : [],
        'value' : [],
        'hash'   : []
    }
           
    ############################################
    # Standard Cell Libraries
    #############################################
    #NOTE: 'default' is a reserved word for hierarchical dictionaries
    
    libname = 'default'
    corner = 'default'
    
    default_cfg['sc_stdlib'] = {}
    default_cfg['sc_stdlib']['type'] = "nested"
    default_cfg['sc_stdlib'][libname] = {}

    default_cfg['sc_stdlib'][libname]['liberty'] = {
        'help' : "Library, <libname pvt filename>",
        'type' : "nested",
        'switch' : "-stdlib_liberty",
        }

    default_cfg['sc_stdlib'][libname]['liberty'][corner] = {
        'type' : "file",
        'default' : [iplib + "lib/NangateOpenCellLibrary_typical.lib"],
        'value' : [],
        'hash' : []
    }

    default_cfg['sc_stdlib'][libname]['lef'] = {
        'help' : "LEF, <libname filename>",
        'type' : "file",
        'switch' : "-stdlib_lef",
        'default' : [iplib + "lef/NangateOpenCellLibrary.macro.lef"],
        'value' : [],
        'hash'   : []
    }

    default_cfg['sc_stdlib'][libname]['gds'] = {
        'help' : "GDS file, <libname filename>",
        'type' : "file",
        'switch' : "-stdlib_gds",
        'default' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'value' : [],
        'hash'   : []
    } 

    default_cfg['sc_stdlib'][libname]['cdl'] = {
        'help' : "CDL file, <libname filename> ",
        'type' : "file",
        'switch' : "-stdlib_cdl",
        'default' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'value' : [],
        'hash'   : []
    } 

    default_cfg['sc_stdlib'][libname]['setup'] = {
        'help' : "Setup file, <libname filename> ",
        'type' : "file",
        'switch' : "-stdlib_setup",
        'default' : [],
        'value' : [],
        'hash'   : []
    } 

    default_cfg['sc_stdlib'][libname]['driver'] = {
        'help' : "Default driver cell, <libname driver>",
        'type' : "string",
        'switch' : "-stdlib_driver",
        'default' : ["BUF_X1"],
        'value' : []
    } 

    default_cfg['sc_stdlib'][libname]['site'] = {
        'help' : "Site name for automated floor-planning, <libname site>",
        'type' : "list",
        'switch' : "-stdlib_site",
        'default' : ["FreePDK45_38x28_10R_NP_162NW_34O"],
        'value' : []
    } 

    default_cfg['sc_cell_list'] = {
        'help' : "List of cell lists needed for PNR setup",
        'type' : "list",
        'switch' : "-cell_list",
        'default' : ["icg",
                    "dontuse",
                    "antenna",
                    "dcap",
                    "filler",
                    "tielo",
                     "tiehi"],
        'value' : []
    }
        
    for value in default_cfg['sc_cell_list']['default']:
        default_cfg['sc_stdlib'][libname][value] = {
            'help' : "List of " + value + " cells, <libname cells>",
            'type' : "list",
            'switch' : "-" + "stdlib_" + value,            
            'default' : [],
            'value' : [],
        }


    ############################################
    # Macro Libraries
    #############################################

    macroname = 'default'
    corner = 'default'
    
    default_cfg['sc_macro'] = {}
    default_cfg['sc_macro']['type'] = "nested"
    default_cfg['sc_macro'][macroname] = {}

    default_cfg['sc_macro'][macroname]['liberty'] = {
        'help' : "Library tuple, <macroname pvt filename>",
        'type' : "nested",
        'switch' : "-macro_liberty",
        }
    
    default_cfg['sc_macro'][macroname]['liberty'][corner] = {
        'type' : "file",
        'default' : [iplib + "lib/NangateOpenCellLibrary_typical.lib"],
        'value' : [],
        'hash'   : []
    }

    default_cfg['sc_macro'][macroname]['lef'] = {
        'help' : "LEF file, <macroname filename>",
        'type' : "file",
        'switch' : "-macro_lef",
        'default' : [iplib + "lef/NangateOpenCellLibrary.macro.lef"],
        'value' : [],
        'hash'   : []
    } 

    default_cfg['sc_macro'][macroname]['gds'] = {
        'help' : "GDS file tuple, <macroname filename>",
        'type' : "file",
        'switch' : "-macro_gds",
        'default' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'hash'   : []
    } 

    default_cfg['sc_macro'][macroname]['cdl'] = {
        'help' : "CDL file tuple, <macroname filename> ",
        'type' : "file",
        'switch' : "-macro_cdl",
        'default' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'hash'   : []
    } 

    default_cfg['sc_macro'][macroname]['setup'] = {
        'help' : "Setup file tuple, <macroname filename> ",
        'type' : "file",
        'switch' : "-macro_setup",
        'default' : [],
        'hash'   : []
    } 
                                          
                                          
    ############################################
    # Execute Options
    #############################################

    default_cfg['sc_debug'] = {
        'help' : "Debug level (INFO/DEBUG/WARNING/ERROR/CRITICAL)",
        'type' : "string",
        'switch' : "-debug",
        'default' : "INFO"
    }

    default_cfg['sc_build'] = {
        'help' : "Name of build directory",
        'type' : "string",
        'switch' : "-build",
        'default' : "build"
    }
    
    default_cfg['sc_effort'] = {
        'help' : "Compilation effort (low,medium,high)",
        'type' : "string",
        'switch' : "-effort",
        'default' : "high"
    }

    default_cfg['sc_priority'] = {
        'help' : "Optimization priority (performance, power, area)",
        'type' : "string",
        'switch' : "-priority",
        'default' : "performance"
    }

    default_cfg['sc_cont'] = {
        'help' : "Continues from last completed stage",
        'type' : "bool",
        'switch' : "-cont",
        'default' : False
    }
        
    default_cfg['sc_gui'] = {
        'help' : "Launches GUI at every stage",
        'type' : "bool",
        'switch' : "-gui",
        'default' : False
    }

    default_cfg['sc_lock'] = {
        'help' : "Switch to lock configuration from further modification",
        'type' : "bool",
        'switch' : "-lock",
        'default' : False
    }
    
    default_cfg['sc_start'] = {
        'help' : "Compilation starting stage",
        'type' : "string",
        'switch' : "-start",
        'default' : "import"
    }

    default_cfg['sc_stop'] = {
        'help' : "Compilation ending stage",
        'type' : "string",
        'switch' : "-stop",
        'default' : "export"
    }
    
    default_cfg['sc_message_event'] = {
        'help' : "List of stages that triggermessages",
        'type' : "list",
        'switch' : "-message_event",
        'default' : ["export"]
    }

    default_cfg['sc_message_recipient'] = {
        'help' : "Message address (phone #/email addr)",
        'type' : "string",
        'switch' : "-message_address",
        'default' : ""
    }

    ############################################
    # Design Specific Source Code Parameters
    #############################################

    default_cfg['sc_source'] = {
        'help' : "Source files (.v/.vh/.sv/.vhd)",
        'type' : "file",
        'switch' : "None",
        'default' : [],
        'hash'   : []
    }

    default_cfg['sc_design'] = {
        'help' : "Design top module name",
        'type' : "string",
        'switch' : "-design",
        'default' : ""
    }

    default_cfg['sc_nickname'] = {
        'help' : "Design nickname",
        'type' : "string",
        'switch' : "-nickname",
        'default' : ""
    }

    default_cfg['sc_clk'] = {
        'help' : "Clock defintion tuple (<clkname> <period(ns)>)",
        'type' : "list",
        'switch' : "-clk",
        'default' : []
    }


    default_cfg['sc_define'] = {
        'help' : "Define variables for Verilog preprocessor",
        'type' : "list",
        'switch' : "-D",
        'default' : []
    }
    
    default_cfg['sc_ydir'] = {
        'help' : "Directory to search for modules",
        'type' : "file",
        'switch' : "-y",
        'default' : [],
        'hash'   : []
    }

    default_cfg['sc_idir'] = {
        'help' : "Directory to search for inclodes",
        'type' : "file",
        'switch' : "-I",
        'default' : [],
        'hash'   : []
    }

    default_cfg['sc_vlib'] = {
        'help' : "Library file",
        'type' : "file",
        'switch' : "-v",
        'default' : [],
        'hash'   : []
    }

    default_cfg['sc_libext'] = {
        'help' : "Extension for finding modules",
        'type' : "list",
        'switch' : "+libext",
        'default' : [".v", ".vh", ".sv", ".vhd"]
    }

    default_cfg['sc_cmdfile'] = {
        'help' : "Parse source options from command file",
        'type' : "file",
        'switch' : "-f",
        'default' : [],
        'hash'   : []
    }

    default_cfg['sc_wall'] = {
        'help' : "Enable all lint style warnings",
        'type' : "string",
        'switch' : "-Wall",
        'default' : ""
    }

    default_cfg['sc_wno'] = {
        'help' : "Disables a warning -Woo-<message>",
        'type' : "list",
        'switch' : "-Wno",
        'default' : []
    }

    ############################################
    # Design specific PD Parameters
    #############################################

    default_cfg['sc_minlayer'] = {
        'help' : "Minimum routing layer (integer)",
        'type' : "int",
        'switch' : "-minlayer",
        'default' : 2
    }

    default_cfg['sc_maxlayer'] = {
        'help' : "Maximum routing layer (integer)",
        'type' : "int",
        'switch' : "-maxlayer",
        'default' : 5
    }
    
    default_cfg['sc_maxfanout'] = {
        'help' : "Maximum fanout",
        'type' : "int",
        'switch' : "-maxfanout",
        'default' : 64
    }

    default_cfg['sc_density'] = {
        'help' : "Target density for automated floor-planning (percent)",
        'type' : "int",
        'switch' : "-density",
        'default' : 30
    }

    default_cfg['sc_aspectratio'] = {
        'help' : "Aspect ratio for density driven floor-planning",
        'type' : "float",
        'switch' : "-aspectratio",
        'default' : 1
    }

    default_cfg['sc_coremargin'] = {
        'help' : "Margin around core for density driven floor-planning (um)",
        'type' : "float",
        'switch' : "-coremargin",
        'default' : 2
    }

    default_cfg['sc_diesize'] = {
        'help' : "Die size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-diesize",
        'default' : ""
    }

    default_cfg['sc_coresize'] = {
        'help' : "Core size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-coresize",
        'default' : ""
    }

    default_cfg['sc_floorplan'] = {
        'help' : "User supplied python based floorplaning script",
        'type' : "file",
        'switch' : "-floorplan",
        'default' : [],
        'hash'   : []
    }
    
    default_cfg['sc_def'] = {
        'help' : "User supplied hard-coded floorplan (DEF)",
        'type' : "file",
        'switch' : "-def",
        'default' : [],
        'hash'   : []
    }
    
    default_cfg['sc_constraints'] = {
        'help' : "Constraints file)",
        'type' : "file",
        'switch' : "-constraints",
        'default' : [],
        'hash'   : []
    }
    
    default_cfg['sc_ndr'] = {
        'help' : "Non-default net routing file",
        'type' : "file",
        'switch' : "-ndr",
        'default' : [],
        'hash'   : []
    }

    default_cfg['sc_upf'] = {
        'help' : "Power intent file",
        'type' : "file",
        'switch' : "-upf",
        'default' : [],
        'hash'   : []
    }

    default_cfg['sc_vcd'] = {
        'help' : "Value Change Dump (VCD) file for power analysis",
        'type' : "file",
        'switch' : "-vcd",
        'default' : [],
        'hash'   : []
    }

    ############################################
    # Tool Configuration
    #############################################

    for stage in default_cfg['sc_stages']['default']:
        
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

        #Common default
        default_cfg['sc_' + stage + '_jobid']['default'] = 0
        default_cfg['sc_' + stage + '_np']['default'] = 4

        #Tool specific default
        default_script = scripts_dir + default_cfg['sc_mode']['default'] + "/sc_" + stage + ".tcl"
        if stage == "import":
            default_cfg['sc_import_tool']['default'] = "verilator"
            default_cfg['sc_import_opt']['default'] = ["--lint-only", "--debug"]
            default_cfg['sc_import_script']['default'] = []
        elif stage == "syn":
            default_cfg['sc_syn_tool']['default'] = "yosys"
            default_cfg['sc_syn_opt']['default'] = ["-c"]
            default_cfg['sc_syn_script']['default'] = [default_script]
        else:
            default_cfg['sc_' + stage + '_tool']['default'] = "openroad"
            default_cfg['sc_' + stage + '_opt']['default'] = ["-no_init", "-exit"]
            default_cfg['sc_' + stage + '_script']['default'] = [default_script]
            
    return default_cfg

