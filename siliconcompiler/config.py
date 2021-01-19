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
    root_dir = re.sub("siliconcompiler/siliconcompiler",
                      "siliconcompiler",
                      install_dir, 1)
    scripts_dir  = root_dir + "/edalib/"
    pdklib = root_dir + "/pdklib/virtual/nangate45/r1p0/pnr/"
    iplib = root_dir + "/iplib/virtual/nangate45/NangateOpenCellLibrary/r1p0/"

    #Core dictionary
    cfg = {}

    ############################################
    # Individual stages supported by "run"
    #############################################

    cfg['sc_stages'] = {
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

    cfg['sc_cfgfile'] = {
        'help' : "Loads configurations from a json file",
        'type' : "file",
        'switch' : "-cfgfile",
        'default' : [],
        'value' : [],
        'hash'   : []
    }

    cfg['sc_mode'] = {
        'help' : "Implementation mode (asic or fpga)",
        'type' : "string",
        'switch' : "-mode",
        'default' : "asic",
        'value' : []        
    }

    ############################################
    # Framework Adoption/Translation
    #############################################
    
    
    cfg['sc_custom'] = {
        'help' : "Custom EDA pass through variables",
        'type' : "list",
        'switch' : "-custom",
        'default' : [],
        'value' : []        
    }

    cfg['sc_keymap'] = {
        'help' : "Framwork keyword translation table",
        'type' : "list",
        'switch' : "-keymap",
        'default' : [],
        'value' : []        
    }
      
    ############################################
    # Remote exeuction settings
    #############################################

    cfg['sc_remote'] = {
        'help' : "Name of remote server address (https://acme.com:8080)",
        'type' : "string",
        'switch' : "-remote",
        'default' : "",
        'value' : ""
        
    }
  
    cfg['sc_ref'] = {
        'help' : "Reference methodology name ",
        'type' : "string",
        'switch' : "-ref",
        'default' : "nangate45",
        'value' : ""
    }
    
    ############################################
    # Technology setup
    #############################################
      
    cfg['sc_foundry'] = {
        'help' : "Foundry name (eg: virtual, tsmc, gf, samsung)",
        'type' : "string",
        'switch' : "-foundry",
        'default' : "virtual",
        'value' : ""
    }
    
    cfg['sc_process'] = {
        'help' : "Process name",
        'type' : "string",
        'switch' : "-process",
        'default' : "nangate45",
        'value' : ""
    }

    cfg['sc_node'] = {
        'help' : "Effective process node in nm (180, 90, 22, 12, 7 etc)",
        'type' : "string",
        'switch' : "-node",
        'default' : "45",
        'value' : ""
    }
    
    cfg['sc_metalstack'] = {
        'help' : "Metal stack as named in the PDK",
        'type' : "string",
        'switch' : "-metalstack",
        'default' : "",
        'value' : ""
    }
    
    cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file (lef or tf)",
        'type' : "file",
        'switch' : "-techfile",
        'default' : [pdklib + "nangate45.tech.lef"],
        'value' : [],
        'hash'   : []
    }

    cfg['sc_rcfile'] = {
        'help' : "RC extraction file",
        'type' : "file",
        'switch' : "-rcfile",
        'default' : [],
        'value' : [],
        'hash'   : []
    }

    cfg['sc_layer'] = {
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
    cfg['sc_scenario'] = {
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

    cfg['sc_layermap'] = {
        'help' : "GDS layer map",
        'type' : "file",
        'switch' : "-layermap",
        'default' : [],
        'value' : [],
        'hash' : []
    }

    cfg['sc_model'] = {
        'help' : "Spice model file",
        'type' : "file",
        'switch' : "-model",
        'default' : [],
        'value' : [],
        'hash'   : []
    }
           
    ############################################
    # Library Configuration (per library)
    #############################################

    # Setting up dicts
    cfg['sc_stdlib'] = {}
    cfg['sc_stdlib']['type'] = "nested"
    cfg['sc_stdlib']['help'] = {}
    cfg['sc_stdlib']['switch'] = {}
    
    # Command line support
    cfg['sc_stdlib']['help']['liberty'] = "Liberty file <libname pvt filename>"
    cfg['sc_stdlib']['switch']['liberty'] = "-stdlib_liberty"

    cfg['sc_stdlib']['help']['cells'] = "Cell list <libname type cells>"
    cfg['sc_stdlib']['switch']['cells'] = "-stdlib_cells"
    
    cfg['sc_stdlib']['help']['lef'] = "LEF file <libname filename>"
    cfg['sc_stdlib']['switch']['lef'] = "-stdlib_lef"

    cfg['sc_stdlib']['help']['gds'] = "GDS file <libname filename>"
    cfg['sc_stdlib']['switch']['gds'] = "-stdlib_gds"

    cfg['sc_stdlib']['help']['cdl'] = "CDL file <libname filename>"
    cfg['sc_stdlib']['switch']['cdl'] = "-stdlib_cdl"

    cfg['sc_stdlib']['help']['setup'] = "Library setup file <libname filename>"
    cfg['sc_stdlib']['switch']['setup'] = "-stdlib_setup"

    cfg['sc_stdlib']['help']['driver'] = "Default driver cell <libname cell>"
    cfg['sc_stdlib']['switch']['driver'] = "-stdlib_driver"

    cfg['sc_stdlib']['help']['site'] = "Placement site name <libname site>"
    cfg['sc_stdlib']['switch']['site'] = "-stdlib_site"

    # Defaults

    libname = 'NangateOpenCellLibrary'
    corner = 'tt_0.9_25'    
    cfg['sc_cell_list'] = {
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
        
    cfg['sc_stdlib'][libname] = {}   

    #Liberty specified on a per corner basis (so one more level of nesting)
    cfg['sc_stdlib'][libname]['liberty'] = {}
    cfg['sc_stdlib'][libname]['liberty']['type'] = "nested"
    cfg['sc_stdlib'][libname]['liberty'][corner] = {
        'type' : "file",
        'default' : [iplib + "lib/NangateOpenCellLibrary_typical.lib"],
        'value' : [],
        'hash' : []
    }

    #Cell lists are many and dynamic (so one more level of nesting)
    cfg['sc_stdlib'][libname]['cells'] = {}
    cfg['sc_stdlib'][libname]['cells']['type'] = "nested"
    for val in cfg['sc_cell_list']['default']:
        cfg['sc_stdlib'][libname]['cells'][val] = {
            'type' : "list",
            'default' : [],
            'value' : [],
        }
    
    cfg['sc_stdlib'][libname]['lef'] = {
        'type' : "file",
        'default' : [iplib + "lef/NangateOpenCellLibrary.macro.lef"],
        'value' : [],
        'hash'   : []
    }

    cfg['sc_stdlib'][libname]['gds'] = {
        'type' : "file",
        'default' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'value' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib'][libname]['cdl'] = {
        'type' : "file",
        'default' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'value' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib'][libname]['setup'] = {
        'type' : "file",
        'default' : [],
        'value' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib'][libname]['driver'] = {
        'type' : "string",
        'default' : ["BUF_X1"],
        'value' : []
    } 

    cfg['sc_stdlib'][libname]['site'] = {
        'type' : "list",
        'default' : ["FreePDK45_38x28_10R_NP_162NW_34O"],
        'value' : []
    } 

    ############################################
    # Macro Configuration (per macro)
    #############################################

    #structure is the same as for standard cell libraries
    
    cfg['sc_macro'] = {}
    cfg['sc_macro']['type'] = "nested"
    cfg['sc_macro']['help'] = {}
    cfg['sc_macro']['switch'] = {}

    # Command line support
    cfg['sc_macro']['help']['liberty'] = "Liberty file <libname pvt filename>"
    cfg['sc_macro']['switch']['liberty'] = "-macro_liberty"

    cfg['sc_macro']['help']['lef'] = "LEF file <libname filename>"
    cfg['sc_macro']['switch']['lef'] = "-macro_lef"

    cfg['sc_macro']['help']['gds'] = "GDS file <libname filename>"
    cfg['sc_macro']['switch']['gds'] = "-macro_gds"

    cfg['sc_macro']['help']['cdl'] = "CDL file <libname filename>"
    cfg['sc_macro']['switch']['cdl'] = "-macro_cdl"

    cfg['sc_macro']['help']['setup'] = "Library setup file <libname filename>"
    cfg['sc_macro']['switch']['setup'] = "-macro_setup"

    ############################################
    # Execute Options
    #############################################

    cfg['sc_debug'] = {
        'help' : "Debug level (INFO/DEBUG/WARNING/ERROR/CRITICAL)",
        'type' : "string",
        'switch' : "-debug",
        'default' : "INFO"
    }

    cfg['sc_build'] = {
        'help' : "Name of build directory",
        'type' : "string",
        'switch' : "-build",
        'default' : "build"
    }
    
    cfg['sc_effort'] = {
        'help' : "Compilation effort (low,medium,high)",
        'type' : "string",
        'switch' : "-effort",
        'default' : "high"
    }

    cfg['sc_priority'] = {
        'help' : "Optimization priority (performance, power, area)",
        'type' : "string",
        'switch' : "-priority",
        'default' : "performance"
    }

    cfg['sc_cont'] = {
        'help' : "Continues from last completed stage",
        'type' : "bool",
        'switch' : "-cont",
        'default' : False
    }
        
    cfg['sc_gui'] = {
        'help' : "Launches GUI at every stage",
        'type' : "bool",
        'switch' : "-gui",
        'default' : False
    }

    cfg['sc_lock'] = {
        'help' : "Switch to lock configuration from further modification",
        'type' : "bool",
        'switch' : "-lock",
        'default' : False
    }
    
    cfg['sc_start'] = {
        'help' : "Compilation starting stage",
        'type' : "string",
        'switch' : "-start",
        'default' : "import"
    }

    cfg['sc_stop'] = {
        'help' : "Compilation ending stage",
        'type' : "string",
        'switch' : "-stop",
        'default' : "export"
    }
    
    cfg['sc_message_event'] = {
        'help' : "List of stages that triggermessages",
        'type' : "list",
        'switch' : "-message_event",
        'default' : ["export"]
    }

    cfg['sc_message_address'] = {
        'help' : "Message address (phone #/email addr)",
        'type' : "string",
        'switch' : "-message_address",
        'default' : ""
    }

    ############################################
    # Design Specific Source Code Parameters
    #############################################

    cfg['sc_source'] = {
        'help' : "Source files (.v/.vh/.sv/.vhd)",
        'type' : "file",
        'switch' : "None",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_design'] = {
        'help' : "Design top module name",
        'type' : "string",
        'switch' : "-design",
        'default' : ""
    }

    cfg['sc_nickname'] = {
        'help' : "Design nickname",
        'type' : "string",
        'switch' : "-nickname",
        'default' : ""
    }

    cfg['sc_clk'] = {
        'help' : "Clock defintion tuple (<clkname> <period(ns)>)",
        'type' : "list",
        'switch' : "-clk",
        'default' : []
    }


    cfg['sc_define'] = {
        'help' : "Define variables for Verilog preprocessor",
        'type' : "list",
        'switch' : "-D",
        'default' : []
    }
    
    cfg['sc_ydir'] = {
        'help' : "Directory to search for modules",
        'type' : "file",
        'switch' : "-y",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_idir'] = {
        'help' : "Directory to search for inclodes",
        'type' : "file",
        'switch' : "-I",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_vlib'] = {
        'help' : "Library file",
        'type' : "file",
        'switch' : "-v",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_libext'] = {
        'help' : "Extension for finding modules",
        'type' : "list",
        'switch' : "+libext",
        'default' : [".v", ".vh", ".sv", ".vhd"]
    }

    cfg['sc_cmdfile'] = {
        'help' : "Parse source options from command file",
        'type' : "file",
        'switch' : "-f",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_wall'] = {
        'help' : "Enable all lint style warnings",
        'type' : "string",
        'switch' : "-Wall",
        'default' : ""
    }

    cfg['sc_wno'] = {
        'help' : "Disables a warning -Woo-<message>",
        'type' : "list",
        'switch' : "-Wno",
        'default' : []
    }

    ############################################
    # Design specific PD Parameters
    #############################################

    cfg['sc_minlayer'] = {
        'help' : "Minimum routing layer (integer)",
        'type' : "int",
        'switch' : "-minlayer",
        'default' : 2
    }

    cfg['sc_maxlayer'] = {
        'help' : "Maximum routing layer (integer)",
        'type' : "int",
        'switch' : "-maxlayer",
        'default' : 5
    }
    
    cfg['sc_maxfanout'] = {
        'help' : "Maximum fanout",
        'type' : "int",
        'switch' : "-maxfanout",
        'default' : 64
    }

    cfg['sc_density'] = {
        'help' : "Target density for automated floor-planning (percent)",
        'type' : "int",
        'switch' : "-density",
        'default' : 30
    }

    cfg['sc_aspectratio'] = {
        'help' : "Aspect ratio for density driven floor-planning",
        'type' : "float",
        'switch' : "-aspectratio",
        'default' : 1
    }

    cfg['sc_coremargin'] = {
        'help' : "Margin around core for density driven floor-planning (um)",
        'type' : "float",
        'switch' : "-coremargin",
        'default' : 2
    }

    cfg['sc_diesize'] = {
        'help' : "Die size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-diesize",
        'default' : ""
    }

    cfg['sc_coresize'] = {
        'help' : "Core size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-coresize",
        'default' : ""
    }

    cfg['sc_floorplan'] = {
        'help' : "User supplied python based floorplaning script",
        'type' : "file",
        'switch' : "-floorplan",
        'default' : [],
        'hash'   : []
    }
    
    cfg['sc_def'] = {
        'help' : "User supplied hard-coded floorplan (DEF)",
        'type' : "file",
        'switch' : "-def",
        'default' : [],
        'hash'   : []
    }
    
    cfg['sc_constraints'] = {
        'help' : "Constraints file (SDC)",
        'type' : "file",
        'switch' : "-constraints",
        'default' : [],
        'hash'   : []
    }
    
    cfg['sc_ndr'] = {
        'help' : "Non-default net routing file",
        'type' : "file",
        'switch' : "-ndr",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_upf'] = {
        'help' : "Power intent file",
        'type' : "file",
        'switch' : "-upf",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_vcd'] = {
        'help' : "Value Change Dump (VCD) file for power analysis",
        'type' : "file",
        'switch' : "-vcd",
        'default' : [],
        'hash'   : []
    }

    ############################################
    # Tool Configuration (per stage)
    #############################################
    
    cfg['sc_tool'] = {}
    cfg['sc_tool']['type'] = "nested"
    cfg['sc_tool']['help'] = {}
    cfg['sc_tool']['switch'] = {}

    # Binary     
    cfg['sc_tool']['help']['exe'] = "Executable <stage, exe>"
    cfg['sc_tool']['switch']['exe'] = "-tool_exe"
    # Options
    cfg['sc_tool']['help']['opt'] = "Options <stage, options>"    
    cfg['sc_tool']['switch']['opt'] = "-tool_opt"
    # Script
    cfg['sc_tool']['help']['script'] = "Run script <stage, script>"
    cfg['sc_tool']['switch']['script'] = "-tool_script"
    # Jobid
    cfg['sc_tool']['help']['jobid'] = "Job index <stage, jobid>"
    cfg['sc_tool']['switch']['jobid'] = "-tool_jobid"
    # Parallelism
    cfg['sc_tool']['help']['np'] = "Parallelism <stage, threads>"
    cfg['sc_tool']['switch']['np'] = "-tool_np"

    # Defaults and config for all stages
    for stage in cfg['sc_stages']['default']:        
        cfg['sc_tool'][stage] = {}
        cfg['sc_tool'][stage]['type'] = "nested"
        for opt in ("exe", "opt", "script", "jobid", "np"):
            cfg['sc_tool'][stage][opt] = {}

        # Types
        cfg['sc_tool'][stage]['exe']['type'] = "string"
        cfg['sc_tool'][stage]['opt']['type'] = "string"
        cfg['sc_tool'][stage]['script']['type'] = "file"
        cfg['sc_tool'][stage]['jobid']['type'] = "int"
        cfg['sc_tool'][stage]['np']['type'] = "int"

        # No init hash
        cfg['sc_tool'][stage]['script']['hash'] = []

        #Creating defaults on a per tool basis
        cfg['sc_tool'][stage]['jobid']['default'] = 0
        cfg['sc_tool'][stage]['np']['default'] = 4

        script = scripts_dir+cfg['sc_mode']['default']+"/sc_"+stage+".tcl"

        if stage == "import":
            cfg['sc_tool'][stage]['exe']['default'] = "verilator"
            cfg['sc_tool'][stage]['opt']['default'] = ["--lint-only", "--debug"]
            cfg['sc_tool'][stage]['script']['default'] = []
        elif stage == "syn":
            cfg['sc_tool'][stage]['exe']['default'] = "yosys"
            cfg['sc_tool'][stage]['opt']['default'] = ["-c"]
            cfg['sc_tool'][stage]['script']['default'] = [script]
        elif stage in ("floorplan", "place", "cts", "route", "signoff"):
            cfg['sc_tool'][stage]['exe']['default'] = "openroad"
            cfg['sc_tool'][stage]['opt']['default'] = ["-no_init", "-exit"]
            cfg['sc_tool'][stage]['script']['default'] = [script]
        else:
            cfg['sc_tool'][stage]['exe']['default'] = ""
            cfg['sc_tool'][stage]['opt']['default'] = []
            cfg['sc_tool'][stage]['script']['default'] = []
            
    return cfg

