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
                     "tapeout"]
    }

    ############################################
    # General Settings
    #############################################

    cfg['sc_cfgfile'] = {
        'help' : "Loads configurations from a json file",
        'type' : "file",
        'switch' : "-cfgfile",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_mode'] = {
        'help' : "Implementation mode (asic or fpga)",
        'type' : "string",
        'switch' : "-mode",
        'default' : "asic"
    }

    ############################################
    # Framework Adoption/Translation
    #############################################
    
    
    cfg['sc_custom'] = {
        'help' : "Custom EDA pass through variables",
        'type' : "list",
        'switch' : "-custom",
        'default' : []
    }

    cfg['sc_keymap'] = {
        'help' : "Framwork keyword translation table",
        'type' : "list",
        'switch' : "-keymap",
        'default' : []
    }
      
    ############################################
    # Remote exeuction settings
    #############################################

    cfg['sc_remote'] = {
        'help' : "Name of remote server address (https://acme.com:8080)",
        'type' : "string",
        'switch' : "-remote",
        'default' : ""
    }
  
    cfg['sc_ref'] = {
        'help' : "Reference methodology name ",
        'type' : "string",
        'switch' : "-ref",
        'default' : "nangate45"
    }
    
    ############################################
    # Technology setup
    #############################################
      
    cfg['sc_foundry'] = {
        'help' : "Foundry name (eg: virtual, tsmc, gf, samsung)",
        'type' : "string",
        'switch' : "-foundry",
        'default' : "virtual"
    }
    
    cfg['sc_process'] = {
        'help' : "Process name",
        'type' : "string",
        'switch' : "-process",
        'default' : "nangate45"
    }

    cfg['sc_node'] = {
        'help' : "Effective process node in nm (180, 90, 22, 12, 7 etc)",
        'type' : "string",
        'switch' : "-node",
        'default' : "45"
    }
    
    cfg['sc_metalstack'] = {
        'help' : "Metal stack as named in the PDK",
        'type' : "string",
        'switch' : "-metalstack",
        'default' : ""
    }
    
    cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file (lef or tf)",
        'type' : "file",
        'switch' : "-techfile",
        'default' : [pdklib + "nangate45.tech.lef"],
        'hash'   : []
    }

    cfg['sc_rcfile'] = {
        'help' : "RC extraction file",
        'type' : "file",
        'switch' : "-rcfile",
        'default' : [],
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
                     "metal10 Y 0.07 1.6"]
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
                     "ss      0.9       125   signoff       setup"]
    }

    cfg['sc_layermap'] = {
        'help' : "GDS layer map",
        'type' : "file",
        'switch' : "-layermap",
        'default' : [],
        'hash' : []
    }

    cfg['sc_model'] = {
        'help' : "Spice model file",
        'type' : "file",
        'switch' : "-model",
        'default' : [],
        'hash'   : []
    }
           
    ############################################
    # Library Configuration (per library)
    #############################################
    
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
                     "tiehi"]
    }

    # Setting up dicts
    #NOTE! 'default' is a reserved keyword for libname
    cfg['sc_stdlib'] = {}  
    cfg['sc_stdlib']['default'] = {}

    #Liberty specified on a per corner basis (so one more level of nesting)
    cfg['sc_stdlib']['default']['timing'] = {}
    cfg['sc_stdlib']['default']['timing']['default'] = {
        'help' : "Library Timing file <lib pvt filename>",
        'switch' : "-stdlib_timing",
        'type' : "file",
        'default' : [iplib + "lib/NangateOpenCellLibrary_typical.lib"],
        'hash' : []
    }

    #Power format
    cfg['sc_stdlib']['default']['power'] = {}
    cfg['sc_stdlib']['default']['power']['default'] = {
        'help' : "Library Power file <lib pvt filename>",
        'switch' : "-stdlib_power",        
        'type' : "file",
        'default' : [],
        'hash' : []
    }

    #Cell lists are many and dynamic (so one more level of nesting)
    cfg['sc_stdlib']['default']['cells'] = {}
    for val in cfg['sc_cell_list']['default']:
        cfg['sc_stdlib']['default']['cells'][val] = {
            'help' : "Library "+val+" cells <lib list> ",
            'switch' : "-stdlib_"+val,
            'type' : "list",
            'default' : []
        }
    
    cfg['sc_stdlib']['default']['lef'] = {
        'help' : "Library LEF file <lib filename>",
        'switch' : "-stdlib_lef",      
        'type' : "file",
        'default' : [iplib + "lef/NangateOpenCellLibrary.macro.lef"],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['gds'] = {
        'help' : "Library GDS file <lib filename>",
        'switch' : "-stdlib_gds",        
        'type' : "file",
        'default' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'hash'   : []
    } 

    cfg['sc_stdlib']['default']['cdl'] = {
        'help' : "Library CDL file <lib filename>",
        'switch' : "-stdlib_cdl",        
        'type' : "file",
        'default' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib']['default']['setup'] = {
        'help' : "Library Setup file <lib filename>",
        'switch' : "-stdlib_setup",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib']['default']['dft'] = {
        'help' : "Library DFT file <lib filename>",
        'switch' : "-stdlib_dft",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['verilog'] = {
        'help' : "Library Verilog file <lib filename>",
        'switch' : "-stdlib_verilog",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }
    
    cfg['sc_stdlib']['default']['doc'] = {
        'help' : "Library documentation <lib path>",
        'switch' : "-stdlib_doc",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['pnrdb'] = {
        'help' : "Library PNR database<lib path>",
        'switch' : "-stdlib_pnrdb",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['customdb'] = {
        'help' : "Library custom database <lib path>",
        'switch' : "-stdlib_customdb",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['driver'] = {
        'help' : "Library default driver <lib cell>",
        'switch' : "-stdlib_driver",     
        'type' : "list",
        'default' : ["BUF_X1"]
    }
    
    cfg['sc_stdlib']['default']['site'] = {
        'help' : "Library placement site <lib site>",
        'switch' : "-stdlib_site",     
        'type' : "list",
        'default' : ["FreePDK45_38x28_10R_NP_162NW_34O"]
    }
    
    
    ############################################
    # Macro Configuration (per macro)
    #############################################

    #NOTE! 'default' is a reserved keyword for maconame
     
    cfg['sc_macro'] = {}
    cfg['sc_macro']['default'] = {}

    #Timing specified on a per corner basis
    cfg['sc_macro']['default']['timing'] = {}
    cfg['sc_macro']['default']['timing']['default'] = {
        'help' : "Macro timing file <lib pvt filename>",
        'switch' : "-macro_timing",
        'type' : "file",
        'default' : [],
        'hash' : []
    }

    #Power specified on a per corner basis
    cfg['sc_macro']['default']['power'] = {}
    cfg['sc_macro']['default']['power']['default'] = {
        'help' : "Macro power file <lib pvt filename>",
        'switch' : "-macro_power",        
        'type' : "file",
        'default' : [],
        'hash' : []
    }

    cfg['sc_macro']['default']['lef'] = {
        'help' : "Macro LEF file <lib filename>",
        'switch' : "-macro_lef",        
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_macro']['default']['gds'] = {
        'help' : "Macro GDS file <lib filename>",
        'switch' : "-macro_gds",        
        'type' : "file",
        'default' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['default']['cdl'] = {
        'help' : "Macro CDL file <lib filename>",
        'switch' : "-macro_cdl",        
        'type' : "file",
        'default' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['default']['setup'] = {
        'help' : "Macro Setup file <lib filename>",
        'switch' : "-macro_setup",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['default']['dft'] = {
        'help' : "Macro DFT file <lib filename>",
        'switch' : "-macro_dft",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_macro']['default']['verilog'] = {
        'help' : "Macro Verilog file <lib filename>",
        'switch' : "-macro_verilog",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }
    
    cfg['sc_macro']['default']['doc'] = {
        'help' : "Macro documentation <lib path>",
        'switch' : "-macro_doc",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_macro']['default']['pnrdb'] = {
        'help' : "Macro PNR database <lib path>",
        'switch' : "-macro_pnrdb",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

    cfg['sc_macro']['default']['customdb'] = {
        'help' : "Macro Custom database <lib path>",
        'switch' : "-macro_customdb",     
        'type' : "file",
        'default' : [],
        'hash'   : []
    }

  
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

    #TODO: Enhance, no tuples!
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

    # Defaults and config for all stages
    for stage in cfg['sc_stages']['default']:        
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

