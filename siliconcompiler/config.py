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
        'defvalue' : ["import",
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
                     "tapeout"]
    }

    ############################################
    # General Settings
    #############################################

    cfg['sc_cfgfile'] = {
        'help' : "Loads configurations from a json file",
        'type' : "file",
        'switch' : "-cfgfile",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_mode'] = {
        'help' : "Implementation mode (asic or fpga)",
        'type' : "string",
        'switch' : "-mode",
        'defvalue' : "asic"
    }

    ############################################
    # Framework Adoption/Translation
    #############################################
    
    
    cfg['sc_custom'] = {
        'help' : "Custom EDA pass through variables",
        'type' : "list",
        'switch' : "-custom",
        'defvalue' : []
    }

    cfg['sc_keymap'] = {
        'help' : "Framwork keyword translation table",
        'type' : "list",
        'switch' : "-keymap",
        'defvalue' : []
    }
      
    ############################################
    # Remote exeuction settings
    #############################################

    cfg['sc_remote'] = {
        'help' : "Name of remote server address (https://acme.com:8080)",
        'type' : "string",
        'switch' : "-remote",
        'defvalue' : ""
    }

    ############################################
    # Environment Variables
    #############################################
      
    cfg['sc_ref'] = {
        'help' : "Reference methodology name",
        'type' : "string",
        'switch' : "-ref",
        'defvalue' : "nangate45"
    }

    cfg['sc_pdkdir'] = {
        'help' : "PDK root directory",
        'type' : "string",
        'switch' : "-pdkdir",
        'defvalue' : ""
    }
    cfg['sc_edadir'] = {
        'help' : "EDA root directory",
        'type' : "string",
        'switch' : "-edadir",
        'defvalue' : ""
    }

    cfg['sc_ipdir'] = {
        'help' : "IP root directory",
        'type' : "string",
        'switch' : "-ipdir",
        'defvalue' : ""
    }

    ############################################
    # Technology setup
    #############################################
      
    cfg['sc_foundry'] = {
        'help' : "Foundry name (eg: virtual, tsmc, gf, samsung)",
        'type' : "string",
        'switch' : "-foundry",
        'defvalue' : "virtual"
    }
    
    cfg['sc_process'] = {
        'help' : "Process name",
        'type' : "string",
        'switch' : "-process",
        'defvalue' : "nangate45"
    }

    cfg['sc_node'] = {
        'help' : "Effective process node in nm (180, 90, 22, 12, 7 etc)",
        'type' : "string",
        'switch' : "-node",
        'defvalue' : "45"
    }
    
    cfg['sc_metalstack'] = {
        'help' : "Metal stack as named in the PDK",
        'type' : "string",
        'switch' : "-metalstack",
        'defvalue' : ""
    }
    
    cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file (lef or tf)",
        'type' : "file",
        'switch' : "-techfile",
        'defvalue' : [pdklib + "nangate45.tech.lef"],
        'hash'   : []
    }

    cfg['sc_rcfile'] = {
        'help' : "RC extraction file",
        'type' : "file",
        'switch' : "-rcfile",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_layer'] = {
        'help' : "Routing layer definitions (eg: metal1 X 0.095 0.19) ",
        'type' : "list",
        'switch' : "-layer",
        'defvalue' : ["metal1 X 0.095 0.19",
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
    #TODO: Fix, layer
    cfg['sc_scenario'] = {
        'help' : "Process,voltage,temp scenario (eg: tt 0.7 25 setup)",
        'type' : "list",
        'switch' : "-scenario",
               #     procr  #voltage  #temp #opt/signoff  #setup/hold/power     
        'defvalue' : ["tt      1.0       25    all           all",
                    "ff      1.1       -40   opt           hold",
                    "ff      1.1       125   opt           power",
                     "ss      0.9       125   signoff       setup"]
    }

    cfg['sc_layermap'] = {
        'help' : "GDS layer map",
        'type' : "file",
        'switch' : "-layermap",
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_model'] = {
        'help' : "Spice model file",
        'type' : "file",
        'switch' : "-model",
        'defvalue' : [],
        'hash'   : []
    }
           
    ############################################
    # Library Configuration (per library)
    #############################################
    
    cfg['sc_cell_list'] = {
        'help' : "List of cell lists needed for PNR setup",
        'type' : "list",
        'switch' : "-cell_list",
        'defvalue' : ["icg",
                     "dontuse",
                     "antenna",
                     "dcap",
                     "filler",
                     "tielo",
                     "tiehi"]
    }

    # Setting up dicts
    #NOTE! 'defvalue' is a reserved keyword for libname
    cfg['sc_stdlib'] = {}  
    cfg['sc_stdlib']['deflib'] = {}

    #Liberty specified on a per corner basis (so one more level of nesting)
    cfg['sc_stdlib']['deflib']['timing'] = {}
    cfg['sc_stdlib']['deflib']['timing']['defcorner'] = {
        'help' : "Library Timing file <lib pvt filename>",
        'switch' : "-stdlib_timing",
        'type' : "file",
        'defvalue' : [iplib + "lib/NangateOpenCellLibrary_typical.lib"],
        'hash' : []
    }

    #Power format
    cfg['sc_stdlib']['deflib']['power'] = {}
    cfg['sc_stdlib']['deflib']['power']['defcorner'] = {
        'help' : "Library Power file <lib pvt filename>",
        'switch' : "-stdlib_power",        
        'type' : "file",
        'defvalue' : [],
        'hash' : []
    }

    #Cell lists are many and dynamic (so one more level of nesting)
    cfg['sc_stdlib']['deflib']['cells'] = {}
    for val in cfg['sc_cell_list']['defvalue']:
        cfg['sc_stdlib']['deflib']['cells'][val] = {
            'help' : "Library "+val+" cells <lib list> ",
            'switch' : "-stdlib_"+val,
            'type' : "list",
            'defvalue' : []
        }
    
    cfg['sc_stdlib']['deflib']['lef'] = {
        'help' : "Library LEF file <lib filename>",
        'switch' : "-stdlib_lef",      
        'type' : "file",
        'defvalue' : [iplib + "lef/NangateOpenCellLibrary.macro.lef"],
        'hash'   : []
    }

    cfg['sc_stdlib']['deflib']['gds'] = {
        'help' : "Library GDS file <lib filename>",
        'switch' : "-stdlib_gds",        
        'type' : "file",
        'defvalue' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'hash'   : []
    } 

    cfg['sc_stdlib']['deflib']['cdl'] = {
        'help' : "Library CDL file <lib filename>",
        'switch' : "-stdlib_cdl",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib']['deflib']['setup'] = {
        'help' : "Library Setup file <lib filename>",
        'switch' : "-stdlib_setup",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib']['deflib']['dft'] = {
        'help' : "Library DFT file <lib filename>",
        'switch' : "-stdlib_dft",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['deflib']['verilog'] = {
        'help' : "Library Verilog file <lib filename>",
        'switch' : "-stdlib_verilog",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_stdlib']['deflib']['doc'] = {
        'help' : "Library documentation <lib path>",
        'switch' : "-stdlib_doc",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['deflib']['pnrdb'] = {
        'help' : "Library PNR database<lib path>",
        'switch' : "-stdlib_pnrdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['deflib']['customdb'] = {
        'help' : "Library custom database <lib path>",
        'switch' : "-stdlib_customdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['deflib']['driver'] = {
        'help' : "Library default driver <lib cell>",
        'switch' : "-stdlib_driver",     
        'type' : "list",
        'defvalue' : ["BUF_X1"]
    }
    
    cfg['sc_stdlib']['deflib']['site'] = {
        'help' : "Library placement site <lib site>",
        'switch' : "-stdlib_site",     
        'type' : "list",
        'defvalue' : ["FreePDK45_38x28_10R_NP_162NW_34O"]
    }
    
    
    ############################################
    # Macro Configuration (per macro)
    #############################################

    #NOTE! 'defvalue' is a reserved keyword for maconame
     
    cfg['sc_macro'] = {}
    cfg['sc_macro']['defmacro'] = {}

    #Timing specified on a per corner basis
    cfg['sc_macro']['defmacro']['timing'] = {}
    cfg['sc_macro']['defmacro']['timing']['defcorner'] = {
        'help' : "Macro timing file <lib pvt filename>",
        'switch' : "-macro_timing",
        'type' : "file",
        'defvalue' : [],
        'hash' : []
    }

    #Power specified on a per corner basis
    cfg['sc_macro']['defmacro']['power'] = {}
    cfg['sc_macro']['defmacro']['power']['defcorner'] = {
        'help' : "Macro power file <lib pvt filename>",
        'switch' : "-macro_power",        
        'type' : "file",
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_macro']['defmacro']['lef'] = {
        'help' : "Macro LEF file <lib filename>",
        'switch' : "-macro_lef",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_macro']['defmacro']['gds'] = {
        'help' : "Macro GDS file <lib filename>",
        'switch' : "-macro_gds",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['defmacro']['cdl'] = {
        'help' : "Macro CDL file <lib filename>",
        'switch' : "-macro_cdl",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['defmacro']['setup'] = {
        'help' : "Macro Setup file <lib filename>",
        'switch' : "-macro_setup",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['defmacro']['dft'] = {
        'help' : "Macro DFT file <lib filename>",
        'switch' : "-macro_dft",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_macro']['defmacro']['verilog'] = {
        'help' : "Macro Verilog file <lib filename>",
        'switch' : "-macro_verilog",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_macro']['defmacro']['doc'] = {
        'help' : "Macro documentation <lib path>",
        'switch' : "-macro_doc",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_macro']['defmacro']['pnrdb'] = {
        'help' : "Macro PNR database <lib path>",
        'switch' : "-macro_pnrdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_macro']['defmacro']['customdb'] = {
        'help' : "Macro Custom database <lib path>",
        'switch' : "-macro_customdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

  
    ############################################
    # Execute Options
    #############################################

    cfg['sc_debug'] = {
        'help' : "Debug level (INFO/DEBUG/WARNING/ERROR/CRITICAL)",
        'type' : "string",
        'switch' : "-debug",
        'defvalue' : "INFO"
    }

    cfg['sc_build'] = {
        'help' : "Name of build directory",
        'type' : "string",
        'switch' : "-build",
        'defvalue' : "build"
    }
    
    cfg['sc_effort'] = {
        'help' : "Compilation effort (low,medium,high)",
        'type' : "string",
        'switch' : "-effort",
        'defvalue' : "high"
    }

    cfg['sc_priority'] = {
        'help' : "Optimization priority (performance, power, area)",
        'type' : "string",
        'switch' : "-priority",
        'defvalue' : "performance"
    }

    cfg['sc_cont'] = {
        'help' : "Continues from last completed stage",
        'type' : "bool",
        'switch' : "-cont",
        'defvalue' : False
    }
        
    cfg['sc_gui'] = {
        'help' : "Launches GUI at every stage",
        'type' : "bool",
        'switch' : "-gui",
        'defvalue' : False
    }

    cfg['sc_lock'] = {
        'help' : "Switch to lock configuration from further modification",
        'type' : "bool",
        'switch' : "-lock",
        'defvalue' : False
    }
    
    cfg['sc_start'] = {
        'help' : "Compilation starting stage",
        'type' : "string",
        'switch' : "-start",
        'defvalue' : "import"
    }

    cfg['sc_stop'] = {
        'help' : "Compilation ending stage",
        'type' : "string",
        'switch' : "-stop",
        'defvalue' : "export"
    }
    
    cfg['sc_message_event'] = {
        'help' : "List of stages that triggermessages",
        'type' : "list",
        'switch' : "-message_event",
        'defvalue' : ["export"]
    }

    cfg['sc_message_address'] = {
        'help' : "Message address (phone #/email addr)",
        'type' : "string",
        'switch' : "-message_address",
        'defvalue' : ""
    }

    ############################################
    # Design Specific Source Code Parameters
    #############################################

    cfg['sc_source'] = {
        'help' : "Source files (.v/.vh/.sv/.vhd)",
        'type' : "file",
        'switch' : "None",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_design'] = {
        'help' : "Design top module name",
        'type' : "string",
        'switch' : "-design",
        'defvalue' : ""
    }

    cfg['sc_nickname'] = {
        'help' : "Design nickname",
        'type' : "string",
        'switch' : "-nickname",
        'defvalue' : ""
    }

    #TODO: Enhance, no tuples!
    cfg['sc_clk'] = {
        'help' : "Clock defintion tuple (<clkname> <period(ns)>)",
        'type' : "list",
        'switch' : "-clk",
        'defvalue' : []
    }


    cfg['sc_define'] = {
        'help' : "Define variables for Verilog preprocessor",
        'type' : "list",
        'switch' : "-D",
        'defvalue' : []
    }
    
    cfg['sc_ydir'] = {
        'help' : "Directory to search for modules",
        'type' : "file",
        'switch' : "-y",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_idir'] = {
        'help' : "Directory to search for inclodes",
        'type' : "file",
        'switch' : "-I",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_vlib'] = {
        'help' : "Library file",
        'type' : "file",
        'switch' : "-v",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_libext'] = {
        'help' : "Extension for finding modules",
        'type' : "list",
        'switch' : "+libext",
        'defvalue' : [".v", ".vh", ".sv", ".vhd"]
    }

    cfg['sc_cmdfile'] = {
        'help' : "Parse source options from command file",
        'type' : "file",
        'switch' : "-f",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_wall'] = {
        'help' : "Enable all lint style warnings",
        'type' : "string",
        'switch' : "-Wall",
        'defvalue' : ""
    }

    cfg['sc_wno'] = {
        'help' : "Disables a warning -Woo-<message>",
        'type' : "list",
        'switch' : "-Wno",
        'defvalue' : []
    }

    ############################################
    # Design specific PD Parameters
    #############################################

    cfg['sc_minlayer'] = {
        'help' : "Minimum routing layer (integer)",
        'type' : "int",
        'switch' : "-minlayer",
        'defvalue' : 2
    }

    cfg['sc_maxlayer'] = {
        'help' : "Maximum routing layer (integer)",
        'type' : "int",
        'switch' : "-maxlayer",
        'defvalue' : 5
    }
    
    cfg['sc_maxfanout'] = {
        'help' : "Maximum fanout",
        'type' : "int",
        'switch' : "-maxfanout",
        'defvalue' : 64
    }

    cfg['sc_density'] = {
        'help' : "Target density for automated floor-planning (percent)",
        'type' : "int",
        'switch' : "-density",
        'defvalue' : 30
    }

    cfg['sc_aspectratio'] = {
        'help' : "Aspect ratio for density driven floor-planning",
        'type' : "float",
        'switch' : "-aspectratio",
        'defvalue' : 1
    }

    cfg['sc_coremargin'] = {
        'help' : "Margin around core for density driven floor-planning (um)",
        'type' : "float",
        'switch' : "-coremargin",
        'defvalue' : 2
    }

    cfg['sc_diesize'] = {
        'help' : "Die size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-diesize",
        'defvalue' : ""
    }

    cfg['sc_coresize'] = {
        'help' : "Core size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-coresize",
        'defvalue' : ""
    }

    cfg['sc_floorplan'] = {
        'help' : "User supplied python based floorplaning script",
        'type' : "file",
        'switch' : "-floorplan",
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_def'] = {
        'help' : "User supplied hard-coded floorplan (DEF)",
        'type' : "file",
        'switch' : "-def",
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_constraints'] = {
        'help' : "Constraints file (SDC)",
        'type' : "file",
        'switch' : "-constraints",
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_ndr'] = {
        'help' : "Non-default net routing file",
        'type' : "file",
        'switch' : "-ndr",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_upf'] = {
        'help' : "Power intent file",
        'type' : "file",
        'switch' : "-upf",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_vcd'] = {
        'help' : "Value Change Dump (VCD) file for power analysis",
        'type' : "file",
        'switch' : "-vcd",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_saif'] = {
        'help' : "Switching activity (SAIF) file for power analysis",
        'type' : "file",
        'switch' : "-saif",
        'defvalue' : [],
        'hash'   : []
    }

    ############################################
    # Tool Configuration (per stage)
    #############################################

    cfg['sc_tool'] = {}

    # Defaults and config for all stages
    for stage in cfg['sc_stages']['defvalue']:        
        cfg['sc_tool'][stage] = {}
        for key in ("exe", "opt", "script", "jobid", "np"):
            cfg['sc_tool'][stage][key] = {}
            cfg['sc_tool'][stage][key]['switch'] = "-tool_"+key
            
        # Help
        cfg['sc_tool'][stage]['exe']['help'] = "Executable <stage, exe>"
        cfg['sc_tool'][stage]['opt']['help'] = "Options <stage, options>"
        cfg['sc_tool'][stage]['script']['help'] = "Run script <stage, script>"
        cfg['sc_tool'][stage]['jobid']['help'] = "Job index <stage, jobid>"
        cfg['sc_tool'][stage]['np']['help'] = "Parallelism <stage, threads>"
        
        # Types
        cfg['sc_tool'][stage]['exe']['type'] = "string"
        cfg['sc_tool'][stage]['opt']['type'] = "string"
        cfg['sc_tool'][stage]['script']['type'] = "file"
        cfg['sc_tool'][stage]['jobid']['type'] = "int"
        cfg['sc_tool'][stage]['np']['type'] = "int"

        # No init hash
        cfg['sc_tool'][stage]['script']['hash'] = []

        #Creating defaults on a per tool basis
        cfg['sc_tool'][stage]['jobid']['defvalue'] = 0
        cfg['sc_tool'][stage]['np']['defvalue'] = 4

        script = scripts_dir+cfg['sc_mode']['defvalue']+"/sc_"+stage+".tcl"

        if stage == "import":
            cfg['sc_tool'][stage]['exe']['defvalue'] = "verilator"
            cfg['sc_tool'][stage]['opt']['defvalue'] = ["--lint-only", "--debug"]
            cfg['sc_tool'][stage]['script']['defvalue'] = []
        elif stage == "syn":
            cfg['sc_tool'][stage]['exe']['defvalue'] = "yosys"
            cfg['sc_tool'][stage]['opt']['defvalue'] = ["-c"]
            cfg['sc_tool'][stage]['script']['defvalue'] = [script]
        elif stage in ("floorplan", "place", "cts", "route", "signoff"):
            cfg['sc_tool'][stage]['exe']['defvalue'] = "openroad"
            cfg['sc_tool'][stage]['opt']['defvalue'] = ["-no_init", "-exit"]
            cfg['sc_tool'][stage]['script']['defvalue'] = [script]
        else:
            cfg['sc_tool'][stage]['exe']['defvalue'] = ""
            cfg['sc_tool'][stage]['opt']['defvalue'] = []
            cfg['sc_tool'][stage]['script']['defvalue'] = []
            
    return cfg

