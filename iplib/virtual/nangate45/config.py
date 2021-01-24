# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import re
import argparse

###########################
def defaults():
    '''Method for setting the default values for the Chip dictionary. 
    All the keys defined in this dictionary are reserved words. 
    '''
    
    ############################################
    # Paths
    #############################################

    # TODO!! Move defaults out of this file into the main compiler
    # THIs file should be pristine, "spec"
    # They can be set by loading a config file from a root directory 
    # That would emulate a real PDK show a setup file!
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
        'type' : "string",
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
        'defvalue' : ["asic"]
    }

    ############################################
    # Framework Adoption/Translation
    #############################################
    
    
    cfg['sc_custom'] = {
        'help' : "Custom EDA pass through variables",
        'type' : "string",
        'switch' : "-custom",
        'defvalue' : []
    }

    cfg['sc_keymap'] = {
        'help' : "Framwork keyword translation table",
        'type' : "string",
        'switch' : "-keymap",
        'defvalue' : ["default default"]
    }
      
    ############################################
    # Remote exeuction settings
    #############################################

    cfg['sc_remote'] = {
        'help' : "Name of remote server address (https://acme.com:8080)",
        'type' : "string",
        'switch' : "-remote",
        'defvalue' : []
    }

    ############################################
    # Environment Variables
    #############################################
      
    cfg['sc_ref'] = {
        'help' : "Reference methodology name",
        'type' : "string",
        'switch' : "-ref",
        'defvalue' : ["nangate45"]
    }

    cfg['sc_pdkdir'] = {
        'help' : "PDK root directory",
        'type' : "string",
        'switch' : "-pdkdir",
        'defvalue' : []
    }
    cfg['sc_edadir'] = {
        'help' : "EDA root directory",
        'type' : "string",
        'switch' : "-edadir",
        'defvalue' : []
    }

    cfg['sc_ipdir'] = {
        'help' : "IP root directory",
        'type' : "string",
        'switch' : "-ipdir",
        'defvalue' : []
    }

    ############################################
    # Technology setup
    #############################################
      
    cfg['sc_foundry'] = {
        'help' : "Foundry name (eg: virtual, tsmc, gf, samsung)",
        'type' : "string",
        'switch' : "-foundry",
        'defvalue' : ["virtual"]
    }
    
    cfg['sc_process'] = {
        'help' : "Process name",
        'type' : "string",
        'switch' : "-process",
        'defvalue' : ["nangate45"]
    }

    cfg['sc_node'] = {
        'help' : "Effective process node in nm (180, 90, 22, 12, 7 etc)",
        'type' : "string",
        'switch' : "-node",
        'defvalue' : ["45"]
    }
    
    cfg['sc_metalstack'] = {
        'help' : "Metal stack as named in the PDK",
        'type' : "string",
        'switch' : "-metalstack",
        'defvalue' : [""]
    }
    
    cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file",
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
    #TODO, make it a list
    cfg['sc_layer'] = {
        'help' : "Routing layer definitions",
        'type' : "string",
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
    #TODO: make it a list
    cfg['sc_scenario'] = {
        'help' : "Process,voltage,temp scenario (eg: tt 0.7 25 setup)",
        'type' : "string",
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
    
    # Setting up dicts
    #NOTE! 'defvalue' is a reserved keyword for libname
    cfg['sc_stdlib'] = {}  
    cfg['sc_stdlib']['default'] = {}

    #Liberty specified on a per corner basis (so one more level of nesting)
    cfg['sc_stdlib']['default']['timing'] = {}
    cfg['sc_stdlib']['default']['timing']['default'] = {
        'help' : "Library timing file",
        'switch' : "-stdlib_timing",
        'type' : "string",
        'defvalue' : [iplib + "lib/NangateOpenCellLibrary_typical.lib"],
        'hash' : []
    }

    #Power format
    cfg['sc_stdlib']['default']['power'] = {}
    cfg['sc_stdlib']['default']['power']['default'] = {
        'help' : "Library power file",
        'switch' : "-stdlib_power",        
        'type' : "file",
        'defvalue' : [],
        'hash' : []
    }

    #Cell lists are many and dynamic (so one more level of nesting)
    cfg['sc_stdlib']['default']['cells'] = {}
    cfg['sc_stdlib']['default']['cells']['default'] = {
            'help' : "Library cell type list",
            'switch' : "-stdlib_cells",
            'type' : "string",
            'defvalue' : []
        }
    
    cfg['sc_stdlib']['default']['lef'] = {
        'help' : "Library LEF file",
        'switch' : "-stdlib_lef",      
        'type' : "file",
        'defvalue' : [iplib + "lef/NangateOpenCellLibrary.macro.lef"],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['gds'] = {
        'help' : "Library GDS file",
        'switch' : "-stdlib_gds",        
        'type' : "file",
        'defvalue' : [iplib + "gds/NangateOpenCellLibrary.gds"],
        'hash'   : []
    } 

    cfg['sc_stdlib']['default']['cdl'] = {
        'help' : "Library CDL file",
        'switch' : "-stdlib_cdl",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib']['default']['setup'] = {
        'help' : "Library Setup file",
        'switch' : "-stdlib_setup",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_stdlib']['default']['dft'] = {
        'help' : "Library DFT file",
        'switch' : "-stdlib_dft",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['verilog'] = {
        'help' : "Library Verilog file",
        'switch' : "-stdlib_verilog",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_stdlib']['default']['doc'] = {
        'help' : "Library documentation",
        'switch' : "-stdlib_doc",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['pnrdb'] = {
        'help' : "Library PNR database",
        'switch' : "-stdlib_pnrdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['customdb'] = {
        'help' : "Library custom database",
        'switch' : "-stdlib_customdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_stdlib']['default']['driver'] = {
        'help' : "Library default driver",
        'switch' : "-stdlib_driver",     
        'type' : "string",
        'defvalue' : ["BUF_X1"]
    }
    
    cfg['sc_stdlib']['default']['site'] = {
        'help' : "Library placement site",
        'switch' : "-stdlib_site",     
        'type' : "string",
        'defvalue' : ["FreePDK45_38x28_10R_NP_162NW_34O"]
    }
    
    
    ############################################
    # Macro Configuration (per macro)
    #############################################

    #NOTE! 'defvalue' is a reserved keyword for maconame
     
    cfg['sc_macro'] = {}
    cfg['sc_macro']['default'] = {}

    #Timing specified on a per corner basis
    cfg['sc_macro']['default']['timing'] = {}
    cfg['sc_macro']['default']['timing']['default'] = {
        'help' : "Macro timing file",
        'switch' : "-macro_timing",
        'type' : "file",
        'defvalue' : [],
        'hash' : []
    }

    #Power specified on a per corner basis
    cfg['sc_macro']['default']['power'] = {}
    cfg['sc_macro']['default']['power']['default'] = {
        'help' : "Macro power file",
        'switch' : "-macro_power",        
        'type' : "file",
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_macro']['default']['lef'] = {
        'help' : "Macro LEF file",
        'switch' : "-macro_lef",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_macro']['default']['gds'] = {
        'help' : "Macro GDS file",
        'switch' : "-macro_gds",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['default']['cdl'] = {
        'help' : "Macro CDL file",
        'switch' : "-macro_cdl",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['default']['setup'] = {
        'help' : "Macro Setup file",
        'switch' : "-macro_setup",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_macro']['default']['dft'] = {
        'help' : "Macro DFT file",
        'switch' : "-macro_dft",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_macro']['default']['verilog'] = {
        'help' : "Macro Verilog file",
        'switch' : "-macro_verilog",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_macro']['default']['doc'] = {
        'help' : "Macro documentation",
        'switch' : "-macro_doc",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_macro']['default']['pnrdb'] = {
        'help' : "Macro PNR database",
        'switch' : "-macro_pnrdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_macro']['default']['customdb'] = {
        'help' : "Macro Custom database",
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
        'defvalue' : ["INFO"]
    }

    cfg['sc_build'] = {
        'help' : "Name of build directory",
        'type' : "string",
        'switch' : "-build",
        'defvalue' : ["build"]
    }
    
    cfg['sc_effort'] = {
        'help' : "Compilation effort (low,medium,high)",
        'type' : "string",
        'switch' : "-effort",
        'defvalue' : ["high"]
    }

    cfg['sc_priority'] = {
        'help' : "Optimization priority (performance, power, area)",
        'type' : "string",
        'switch' : "-priority",
        'defvalue' : ["performance"]
    }

    cfg['sc_cont'] = {
        'help' : "Continues from last completed stage",
        'type' : "bool",
        'switch' : "-cont",
        'defvalue' : ["False"]
    }
        
    cfg['sc_gui'] = {
        'help' : "Launches GUI at every stage",
        'type' : "bool",
        'switch' : "-gui",
        'defvalue' : ["False"]
    }
    
    cfg['sc_lock'] = {
        'help' : "Switch to lock configuration from further modification",
        'type' : "bool",
        'switch' : "-lock",
        'defvalue' : ["False"]
    }
    
    cfg['sc_start'] = {
        'help' : "Compilation starting stage",
        'type' : "string",
        'switch' : "-start",
        'defvalue' : ["import"]
    }

    cfg['sc_stop'] = {
        'help' : "Compilation ending stage",
        'type' : "string",
        'switch' : "-stop",
        'defvalue' : ["export"]
    }
    
    cfg['sc_trigger'] = {
        'help' : "Event that triggers message to <sc_contact>",
        'type' : "string",
        'switch' : "-trigger",
        'defvalue' : ["export"]
    }

    cfg['sc_contact'] = {
        'help' : "Who to contact on trigge event (phone#/email)",
        'type' : "string",
        'switch' : "-contact",
        'defvalue' : []
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
        'defvalue' : []
    }

    cfg['sc_nickname'] = {
        'help' : "Design nickname",
        'type' : "string",
        'switch' : "-nickname",
        'defvalue' : []
    }

    #TODO: Enhance, no tuples!
    cfg['sc_clk'] = {
        'help' : "Clock defintion tuple (<clkname> <period(ns)>)",
        'type' : "string",
        'switch' : "-clk",
        'defvalue' : []
    }


    cfg['sc_define'] = {
        'help' : "Define variables for Verilog preprocessor",
        'type' : "string",
        'switch' : "-D",
        'defvalue' : []
    }
    
    cfg['sc_ydir'] = {
        'help' : "Directory to search for modules",
        'type' : "string",
        'switch' : "-y",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_idir'] = {
        'help' : "Directory to search for inclodes",
        'type' : "string",
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
        'type' : "string",
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
        'defvalue' : []
    }

    cfg['sc_wno'] = {
        'help' : "Disables a warning -Woo-<message>",
        'type' : "string",
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
        'defvalue' : ["2"]
    }

    cfg['sc_maxlayer'] = {
        'help' : "Maximum routing layer (integer)",
        'type' : "int",
        'switch' : "-maxlayer",
        'defvalue' : ["5"]
    }
    
    cfg['sc_maxfanout'] = {
        'help' : "Maximum fanout",
        'type' : "int",
        'switch' : "-maxfanout",
        'defvalue' : ["64"]
    }

    cfg['sc_density'] = {
        'help' : "Target density for automated floor-planning (percent)",
        'type' : "int",
        'switch' : "-density",
        'defvalue' : ["30"]
    }

    cfg['sc_aspectratio'] = {
        'help' : "Aspect ratio for density driven floor-planning",
        'type' : "float",
        'switch' : "-aspectratio",
        'defvalue' : ["1"]
    }

    cfg['sc_coremargin'] = {
        'help' : "Margin around core for density driven floor-planning (um)",
        'type' : "float",
        'switch' : "-coremargin",
        'defvalue' : ["2"]
    }

    cfg['sc_diesize'] = {
        'help' : "Die size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-diesize",
        'defvalue' : []
    }

    cfg['sc_coresize'] = {
        'help' : "Core size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "string",
        'switch' : "-coresize",
        'defvalue' : [""]
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
        cfg['sc_tool'][stage]['exe']['help'] = "Stage Tool Executable"
        cfg['sc_tool'][stage]['opt']['help'] = "Stage Tool Options"
        cfg['sc_tool'][stage]['script']['help'] = "Stage Tool Run script"
        cfg['sc_tool'][stage]['jobid']['help'] = "Stage Tool Job index"
        cfg['sc_tool'][stage]['np']['help'] = "Stage Tool Parallelism"
        
        # Types
        cfg['sc_tool'][stage]['exe']['type'] = "string"
        cfg['sc_tool'][stage]['opt']['type'] = "string"
        cfg['sc_tool'][stage]['script']['type'] = "file"
        cfg['sc_tool'][stage]['jobid']['type'] = "int"
        cfg['sc_tool'][stage]['np']['type'] = "int"

        # No init hash
        cfg['sc_tool'][stage]['script']['hash'] = []

        #Creating defaults on a per tool basis
        cfg['sc_tool'][stage]['jobid']['defvalue'] = ["0"]
        cfg['sc_tool'][stage]['np']['defvalue'] = ["4"]

        script = scripts_dir+cfg['sc_mode']['defvalue']+"/sc_"+stage+".tcl"

        if stage == "import":
            cfg['sc_tool'][stage]['exe']['defvalue'] = ["verilator"]
            cfg['sc_tool'][stage]['opt']['defvalue'] = ["--lint-only", "--debug"]
            cfg['sc_tool'][stage]['script']['defvalue'] = []
        elif stage == "syn":
            cfg['sc_tool'][stage]['exe']['defvalue'] = ["yosys"]
            cfg['sc_tool'][stage]['opt']['defvalue'] = ["-c"]
            cfg['sc_tool'][stage]['script']['defvalue'] = [script]
        elif stage in ("floorplan", "place", "cts", "route", "signoff"):
            cfg['sc_tool'][stage]['exe']['defvalue'] = ["openroad"]
            cfg['sc_tool'][stage]['opt']['defvalue'] = ["-no_init", "-exit"]
            cfg['sc_tool'][stage]['script']['defvalue'] = [script]
        else:
            cfg['sc_tool'][stage]['exe']['defvalue'] = [""]
            cfg['sc_tool'][stage]['opt']['defvalue'] = []
            cfg['sc_tool'][stage]['script']['defvalue'] = []
            
    return cfg

