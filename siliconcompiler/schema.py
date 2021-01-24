# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import json

###########################

def schema():
    '''Method for defining Chip configuration schema 
    All the keys defined in this dictionary are reserved words. 
    '''
    
    cfg = {}
        
    cfg = schema_setup(cfg)

    cfg = schema_process(cfg)

    cfg = schema_libs(cfg, "stdlib")

    cfg = schema_libs(cfg, "macro")

    cfg = schema_tools(cfg)

    cfg = schema_design(cfg)
       
    return cfg
    
############################################
# General Setup
#############################################

def schema_setup(cfg):
    '''Compilation setup method
    '''
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
        'defvalue' : []
    }

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
  
    cfg['sc_remote'] = {
        'help' : "Name of remote server address (https://acme.com:8080)",
        'type' : "string",
        'switch' : "-remote",
        'defvalue' : []
    }

    cfg['sc_ref'] = {
        'help' : "Reference methodology name",
        'type' : "string",
        'switch' : "-ref",
        'defvalue' : []
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
        'help' : "Stage completion that triggers message to <sc_contact>",
        'type' : "string",
        'switch' : "-trigger",
        'defvalue' : ["export"]
    }

    cfg['sc_contact'] = {
        'help' : "Trigger event contact (phone#/email)",
        'type' : "string",
        'switch' : "-contact",
        'defvalue' : []
    }

    return cfg
    

############################################
# Technology setup
#############################################

def schema_process(cfg):
    ''' Process technology setup
    '''
      
    cfg['sc_foundry'] = {
        'help' : "Foundry name (eg: virtual, tsmc, gf, samsung)",
        'type' : "string",
        'switch' : "-foundry",
        'defvalue' : []
    }

    cfg['sc_process'] = {
        'help' : "Process name",
        'type' : "string",
        'switch' : "-process",
        'defvalue' : []
    }

    cfg['sc_node'] = {
        'help' : "Process node in nm (180, 90, 22, 12, 7 etc)",
        'type' : "int",
        'switch' : "-node",
        'defvalue' : []
    }

    cfg['sc_grid'] = {
        'help' : "Grid unit (in um)",
        'type' : "float",
        'switch' : "-grid",
        'defvalue' : []
    }

    cfg['sc_time'] = {
        'help' : "Time unit (1 ps)",
        'type' : "int",
        'switch' : "-time",
        'defvalue' : []
    }

    cfg['sc_stackup'] = {
        'help' : "Metal stackup as named in the PDK",
        'type' : "string",
        'switch' : "-stackup",
        'defvalue' : []
    }

    cfg['sc_layer'] = {
        'help' : "Metal stackup routing layer definitions",
        'type' : "tuple4",
        'switch' : "-layer",
        'defvalue' : []
    }
    
    cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file",
        'type' : "file",
        'switch' : "-techfile",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_model'] = {
        'help' : "Device model file",
        'type' : "file",
        'switch' : "-model",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_rcfile'] = {
        'help' : "RC extraction file",
        'type' : "file",
        'switch' : "-rcfile",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_scenario'] = {
        'help' : "Process, voltage, temp scenario",
        'type' : "tuple5",
        'switch' : "-scenario",
        'defvalue' : []
    }

    cfg['sc_layermap'] = {
        'help' : "GDS layer map",
        'type' : "tuple4",
        'switch' : "-layermap",
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_taprules'] = {
        'help' : "Tap cell rules <maxdistance offset>",
        'type' : "tuple2",
        'switch' : "-taprules",
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_minlayer'] = {
        'help' : "Minimum routing layer (integer)",
        'type' : "int",
        'switch' : "-minlayer",
        'defvalue' : []
    }

    cfg['sc_maxlayer'] = {
        'help' : "Maximum routing layer (integer)",
        'type' : "int",
        'switch' : "-maxlayer",
        'defvalue' : []
    }
    
    cfg['sc_maxfanout'] = {
        'help' : "Maximum fanout",
        'type' : "int",
        'switch' : "-maxfanout",
        'defvalue' : ["64"]
    }

    cfg['sc_density'] = {
        'help' : "Target density for density driven floor-planning (percent)",
        'type' : "int",
        'switch' : "-density",
        'defvalue' : ["30"]
    }

    cfg['sc_coremargin'] = {
        'help' : "Margin around core for density driven floor-planning (um)",
        'type' : "float",
        'switch' : "-coremargin",
        'defvalue' : ["2"]
    }

    cfg['sc_aspectratio'] = {
        'help' : "Aspect ratio for density driven floor-planning",
        'type' : "float",
        'switch' : "-aspectratio",
        'defvalue' : ["1"]
    }

    return cfg

############################################
# Design Specific Parameters
#############################################

def schema_design(cfg):
    ''' Design setup schema
    '''
    
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

    cfg['sc_clk'] = {
        'help' : "Clock defintion (<name period uncertainty>)",
        'type' : "tuple3",
        'switch' : "-clk",
        'defvalue' : []
    }

    cfg['sc_supplies'] = {
        'help' : "Supply voltages (<name pin voltage>)",
        'type' : "tuple3",
        'switch' : "-supply",
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
 
    cfg['sc_diesize'] = {
        'help' : "Die size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "tuple4",
        'switch' : "-diesize",
        'defvalue' : []
    }

    cfg['sc_coresize'] = {
        'help' : "Core size (x0 y0 x1 y1) for automated floor-planning (um)",
        'type' : "tuple4",
        'switch' : "-coresize",
        'defvalue' : []
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

    return cfg

############################################
# Library Configuration
#############################################   

def schema_libs(cfg, group):

    
    cfg['sc_'+group] = {}  
    cfg['sc_'+group]['default'] = {}

    #Liberty specified on a per corner basis (so one more level of nesting)
    cfg['sc_'+group]['default']['timing'] = {}
    cfg['sc_'+group]['default']['timing']['default'] = {
        'help' : "Library timing file",
        'switch' : "-"+group+"_timing",
        'type' : "file",
        'defvalue' : [],
        'hash' : []
    }

    #Power format
    cfg['sc_'+group]['default']['power'] = {}
    cfg['sc_'+group]['default']['power']['default'] = {
        'help' : "Library power file",
        'switch' : "-"+group+"_power",        
        'type' : "file",
        'defvalue' : [],
        'hash' : []
    }

    #Cell lists are many and dynamic (so one more level of nesting)
    cfg['sc_'+group]['default']['cells'] = {}
    cfg['sc_'+group]['default']['cells']['default'] = {
            'help' : "Library cell type list",
            'switch' : "-"+group+"_cells",
            'type' : "string",
            'defvalue' : []
        }
    
    cfg['sc_'+group]['default']['lef'] = {
        'help' : "Library LEF file",
        'switch' : "-"+group+"_lef",      
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['gds'] = {
        'help' : "Library GDS file",
        'switch' : "-"+group+"_gds",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['cdl'] = {
        'help' : "Library CDL file",
        'switch' : "-"+group+"_cdl",        
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['setup'] = {
        'help' : "Library Setup file",
        'switch' : "-"+group+"_setup",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['dft'] = {
        'help' : "Library DFT file",
        'switch' : "-"+group+"_dft",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['verilog'] = {
        'help' : "Library Verilog file",
        'switch' : "-"+group+"_verilog",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_'+group]['default']['doc'] = {
        'help' : "Library documentation",
        'switch' : "-"+group+"_doc",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['pnrdb'] = {
        'help' : "Library PNR database",
        'switch' : "-"+group+"_pnrdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['customdb'] = {
        'help' : "Library custom database",
        'switch' : "-"+group+"_customdb",     
        'type' : "file",
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['driver'] = {
        'help' : "Library default driver",
        'switch' : "-"+group+"_driver",     
        'type' : "string",
        'defvalue' : []
    }
    
    cfg['sc_'+group]['default']['site'] = {
        'help' : "Library placement site",
        'switch' : "-"+group+"_site",     
        'type' : "string",
        'defvalue' : []
    }

    cfg['sc_'+group]['default']['pgmetal'] = {
        'help' : "Metal layer used for power rails",
        'switch' : "-"+group+"_pgmetal",     
        'type' : "string",
        'defvalue' : []
    }

    cfg['sc_'+group]['default']['tag'] = {
        'help' : "Tags to identify library",
        'switch' : "-"+group+"_tag",     
        'type' : "string",
        'defvalue' : []
    }
    
    return cfg

############################################
# Tool Configuration
#############################################

def schema_tools(cfg):

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

        if stage == "import":
            cfg['sc_tool'][stage]['exe']['defvalue'] = []
            cfg['sc_tool'][stage]['opt']['defvalue'] = []
            cfg['sc_tool'][stage]['script']['defvalue'] = []
        elif stage == "syn":
            cfg['sc_tool'][stage]['exe']['defvalue'] = []
            cfg['sc_tool'][stage]['opt']['defvalue'] = []
            cfg['sc_tool'][stage]['script']['defvalue'] = []
        elif stage in ("floorplan", "place", "cts", "route", "signoff"):
            cfg['sc_tool'][stage]['exe']['defvalue'] = []
            cfg['sc_tool'][stage]['opt']['defvalue'] = []
            cfg['sc_tool'][stage]['script']['defvalue'] = []
        else:
            cfg['sc_tool'][stage]['exe']['defvalue'] = [""]
            cfg['sc_tool'][stage]['opt']['defvalue'] = []
            cfg['sc_tool'][stage]['script']['defvalue'] = []
            
    
    return cfg


