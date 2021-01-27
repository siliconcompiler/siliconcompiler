# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

###########################

def schema():
    '''Method for defining Chip configuration schema 
    All the keys defined in this dictionary are reserved words. 
    '''
    
    cfg = {}

    cfg = schema_defaults(cfg)
    
    cfg = schema_setup(cfg)

    cfg = schema_process(cfg)

    cfg = schema_libs(cfg, "stdlib")

    cfg = schema_libs(cfg, "macro")

    cfg = schema_tools(cfg)

    cfg = schema_design(cfg)
       
    return cfg

############################################
# Parameters that deserve default values
#############################################

def schema_defaults(cfg):

    cfg['sc_mode'] = {
        'help' : "Implementation mode (asic or fpga)",
        'switch' : "-mode",
        'type' : ["string"],
        'defvalue' : ['asic']
    }
    
    cfg['sc_debug'] = {
        'help' : "Debug level (INFO/DEBUG/WARNING/ERROR/CRITICAL)",
        'switch' : "-debug",
        'type' : ["string"],
        'defvalue' : ['INFO']
    }

    cfg['sc_build'] = {
        'help' : "Name of build directory",
        'switch' : "-build",
        'type' : ["string"],
        'defvalue' : ['build']
    }

    cfg['sc_effort'] = {
        'help' : "Compilation effort (low,medium,high)",
        'switch' : "-effort",
        'type' : ["string"],
        'defvalue' : ['high']
    }

    cfg['sc_priority'] = {
        'help' : "Optimization priority (timing, power, area)",
        'switch' : "-priority",
        'type' : ["string"],
        'defvalue' : ['timing']
    }

    cfg['sc_start'] = {
        'help' : "Compilation starting stage",
        'type' : "string",
        'switch' : "-start",
        'defvalue' : ['import']
    }

    cfg['sc_stop'] = {
        'help' : "Compilation ending stage",
        'switch' : "-stop",
        'type' : ["string"],
        'defvalue' : ['export']
    }

    cfg['sc_cont'] = {
        'help' : "Continues from last completed stage",
        'switch' : "-cont",
        'type' : ["bool"],
        'defvalue' : ["False"]
    }
        
    cfg['sc_gui'] = {
        'help' : "Launches GUI at every stage",
        'switch' : "-gui",
        'type' : ["bool"],
        'defvalue' : ["False"]
    }

    cfg['sc_verbose'] = {
        'help' : "Enables verbose printing to screen by EDA tools",
        'switch' : "-verbose",
        'type' : ["bool"],
        'defvalue' : ["False"]
    }
    
    cfg['sc_lock'] = {
        'help' : "Switch to lock configuration from further modification",
        'switch' : "-lock",
        'type' : ["bool"],
        'defvalue' : ["False"]
    }

    return cfg

############################################
# General Setup
#############################################

def schema_setup(cfg):
    '''Compilation setup method
    '''
    cfg['sc_cfgfile'] = {
        'help' : "Loads configurations from a json file",
        'switch' : "-cfgfile",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_custom'] = {
        'help' : "Custom EDA pass through variables",
        'switch' : "-custom",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_keymap'] = {
        'help' : "Keyword translation table for readcfg/writecfg ",
        'switch' : "-keymap",
        'type' : ["string", "string"],
        'defvalue' : []
    }
  
    cfg['sc_remote'] = {
        'help' : "Name of remote server address (https://acme.com:8080)",
        'switch' : "-remote",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_ref'] = {
        'help' : "Reference methodology name",
        'switch' : "-ref",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_pdkdir'] = {
        'help' : "PDK root directory",
        'switch' : "-pdkdir",
        'type' : ["string"],
        'defvalue' : []
    }
    
    cfg['sc_ipdir'] = {
        'help' : "IP root directory",
        'switch' : "-ipdir",
        'type' : ["string"],
        'defvalue' : []
    }
    
    cfg['sc_trigger'] = {
        'help' : "Stage completion that triggers message to <sc_contact>",
        'switch' : "-trigger",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_contact'] = {
        'help' : "Trigger event contact (phone#/email)",
        'switch' : "-contact",
        'type' : ["string"],
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
        'switch' : "-foundry",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_process'] = {
        'help' : "Process name",
        'switch' : "-process",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_node'] = {
        'help' : "Process node in nm (180, 90, 22, 12, 7 etc)",
        'switch' : "-node",
        'type' : ["int"],
        'defvalue' : []
    }

    cfg['sc_grid'] = {
        'help' : "Grid unit (in um)",
        'switch' : "-grid",
        'type' : ["float"],
        'defvalue' : []
    }

    cfg['sc_time'] = {
        'help' : "Time unit (1 ps)",
        'switch' : "-time",
        'type' : ["int"],
        'defvalue' : []
    }

    cfg['sc_stackup'] = {
        'help' : "Metal stackup as named in the PDK",
        'switch' : "-stackup",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_layer'] = {
        'help' : "Metal stackup routing layer definitions",
        'switch' : "-layer",
        'type' : ["string", "string", "float", "float"],
        'defvalue' : []
    }
    
    cfg['sc_techfile'] = {
        'help' : "Place and route tehnology file",
        'switch' : "-techfile",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_model'] = {
        'help' : "Device model file",
        'switch' : "-model",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_rcfile'] = {
        'help' : "RC extraction file",
        'switch' : "-rcfile",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_scenario'] = {
        'help' : "Process, voltage, temp scenario ",
        'switch' : "-scenario",
        'type' : ["string", "float", "int", "string"],
        'defvalue' : []
    }

    cfg['sc_layermap'] = {
        'help' : "GDS layer map",
        'switch' : "-layermap",
        'type' : "string, string, int, int",
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_taprules'] = {
        'help' : "Tap cell rules <maxdistance offset>",
        'switch' : "-taprules",
        'type' : ["float","float"],
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_minlayer'] = {
        'help' : "Minimum routing layer (integer)",
        'switch' : "-minlayer",
        'type' : ["int"],
        'defvalue' : []
    }

    cfg['sc_maxlayer'] = {
        'help' : "Maximum routing layer (integer)",
        'switch' : "-maxlayer",
        'type' : ["int"],
        'defvalue' : []
    }
    
    cfg['sc_maxfanout'] = {
        'help' : "Maximum fanout",
        'switch' : "-maxfanout",
        'type' : ["int"],
        'defvalue' : []
    }

    cfg['sc_density'] = {
        'help' : "Target density for density driven floor-planning (percent)",
        'switch' : "-density",
        'type' : ["int"],
        'defvalue' : []
    }

    cfg['sc_coremargin'] = {
        'help' : "Margin around core for density driven floor-planning (um)",
        'switch' : "-coremargin",
        'type' : ["float"],
        'defvalue' : []
    }

    cfg['sc_aspectratio'] = {
        'help' : "Aspect ratio for density driven floor-planning",
        'switch' : "-aspectratio",
        'type' : ["float"],
        'defvalue' : []
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
        'switch' : "None",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_design'] = {
        'help' : "Design top module name",
        'switch' : "-design",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_nickname'] = {
        'help' : "Design nickname",
        'switch' : "-nickname",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_clk'] = {
        'help' : "Clock defintion (<name period uncertainty>)",
        'switch' : "-clk",
        'type' : ["string", "float", "float"],
        'defvalue' : []
    }

    cfg['sc_supplies'] = {
        'help' : "Supply voltages (<name pin voltage>)",
        'switch' : "-supply",
        'type' : ["string", "string", "float"],

        'defvalue' : []
    }
    
    cfg['sc_define'] = {
        'help' : "Define variables for Verilog preprocessor",
        'switch' : "-D",
        'type' : ["string"],
        'defvalue' : []
    }
    
    cfg['sc_ydir'] = {
        'help' : "Directory to search for modules",
        'switch' : "-y",
        'type' : ["string"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_idir'] = {
        'help' : "Directory to search for inclodes",
        'switch' : "-I",
        'type' : ["string"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_vlib'] = {
        'help' : "Library file",
        'switch' : "-v",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_libext'] = {
        'help' : "Extension for finding modules",
        'switch' : "+libext",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_readscript'] = {
        'help' : "Source file read script",
        'switch' : "-f",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }
    cfg['sc_wall'] = {
        'help' : "Enable all lint style warnings",
        'switch' : "-Wall",
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_wno'] = {
        'help' : "Disables a warning -Woo-<message>",
        'switch' : "-Wno",
        'type' : ["string"],
        'defvalue' : []
    }
 
    cfg['sc_diesize'] = {
        'help' : "Die size (x0 y0 x1 y1) for automated floor-planning (um)",
        'switch' : "-diesize",
        'type' : ["float", "float", "float", "float"],
        'defvalue' : []
    }

    cfg['sc_coresize'] = {
        'help' : "Core size (x0 y0 x1 y1) for automated floor-planning (um)",
        'switch' : "-coresize",
        'type' : ["float", "float", "float", "float"],
        'defvalue' : []
    }

    cfg['sc_floorplan'] = {
        'help' : "User supplied python based floorplaning script",
        'switch' : "-floorplan",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_def'] = {
        'help' : "User supplied hard-coded floorplan (DEF)",
        'switch' : "-def",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_constraints'] = {
        'help' : "Constraints file (SDC)",
        'switch' : "-constraints",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_ndr'] = {
        'help' : "Non-default net routing file",
        'switch' : "-ndr",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_vcd'] = {
        'help' : "Value Change Dump (VCD) file for power analysis",
        'switch' : "-vcd",
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_saif'] = {
        'help' : "Switching activity (SAIF) file for power analysis",
        'switch' : "-saif",
        'type' : ["file"],
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

    cfg['sc_'+group]['default']['views'] = {
        'help' : "List of all library views",
        'switch' : "-"+group+"_views",
        'type' : ["string"],
        'defvalue' : ["timing",
                      "power",
                      "cells",
                      "lef",
                      "gds",
                      "cdl",
                      "setup",
                      "dft",
                      "verilog",
                      "doc",
                      "pnrdb",
                      "customdb",
                      "driver",
                      "site",
                      "pgmetal",
                      "tag"]
    }
    
    #Liberty specified on a per corner basis (so one more level of nesting)
    cfg['sc_'+group]['default']['timing'] = {}
    cfg['sc_'+group]['default']['timing']['default'] = {
        'help' : "Library timing file",
        'switch' : "-"+group+"_timing",
        'type' : ["file"],
        'defvalue' : [],
        'hash' : []
    }

    #Power format
    cfg['sc_'+group]['default']['power'] = {}
    cfg['sc_'+group]['default']['power']['default'] = {
        'help' : "Library power file",
        'switch' : "-"+group+"_power",        
        'type' : ["file"],
        'defvalue' : [],
        'hash' : []
    }

    #Cell lists are many and dynamic (so one more level of nesting)
    cfg['sc_'+group]['default']['cells'] = {}
    cfg['sc_'+group]['default']['cells']['default'] = {
            'help' : "Library cell type list",
            'switch' : "-"+group+"_cells",
            'type' : ["string"],
            'defvalue' : []
        }
    
    cfg['sc_'+group]['default']['lef'] = {
        'help' : "Library LEF file",
        'switch' : "-"+group+"_lef",      
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['gds'] = {
        'help' : "Library GDS file",
        'switch' : "-"+group+"_gds",        
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['cdl'] = {
        'help' : "Library CDL file",
        'switch' : "-"+group+"_cdl",        
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['setup'] = {
        'help' : "Library Setup file",
        'switch' : "-"+group+"_setup",     
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['dft'] = {
        'help' : "Library DFT file",
        'switch' : "-"+group+"_dft",     
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['verilog'] = {
        'help' : "Library Verilog file",
        'switch' : "-"+group+"_verilog",     
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }
    
    cfg['sc_'+group]['default']['doc'] = {
        'help' : "Library documentation",
        'switch' : "-"+group+"_doc",     
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['pnrdb'] = {
        'help' : "Library PNR database",
        'switch' : "-"+group+"_pnrdb",     
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['customdb'] = {
        'help' : "Library custom database",
        'switch' : "-"+group+"_customdb",     
        'type' : ["file"],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['driver'] = {
        'help' : "Library default driver",
        'switch' : "-"+group+"_driver",     
        'type' : ["string"],
        'defvalue' : []
    }
    
    cfg['sc_'+group]['default']['site'] = {
        'help' : "Library placement site",
        'switch' : "-"+group+"_site",     
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_'+group]['default']['pgmetal'] = {
        'help' : "Metal layer used for power rails",
        'switch' : "-"+group+"_pgmetal",     
        'type' : ["string"],
        'defvalue' : []
    }

    cfg['sc_'+group]['default']['tag'] = {
        'help' : "Tags to identify library",
        'switch' : "-"+group+"_tag",     
        'type' : ["string"],
        'defvalue' : []
    }
    
    return cfg

############################################
# Tool Configuration
#############################################

def schema_tools(cfg):

    cfg['sc_stages'] = {
        'help' : "List of all compilation stages",
        'switch' : "-stages",
        'type' : ["string"],
        'defvalue' : ["import",
                      "syn",
                      "floorplan",
                      "place",
                      "cts",
                      "route",
                      "signoff",
                      "export",
                      "display",
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
        for key in ("exe", "opt", "refdir", "script", "format", "jobid", "np"):
            cfg['sc_tool'][stage][key] = {}
            cfg['sc_tool'][stage][key]['switch'] = "-tool_"+key
            
        # Help
        cfg['sc_tool'][stage]['exe']['help'] = "Stage Tool Executable"
        cfg['sc_tool'][stage]['opt']['help'] = "Stage Tool Options"
        cfg['sc_tool'][stage]['refdir']['help'] = "Stage Tool Reference Flow Directory"
        cfg['sc_tool'][stage]['script']['help'] = "Stage Tool Script"
        cfg['sc_tool'][stage]['format']['help'] = "Stage Tool Configuration Format"
        cfg['sc_tool'][stage]['jobid']['help'] = "Stage Tool Job index"
        cfg['sc_tool'][stage]['np']['help'] = "Stage Tool Parallelism"
        
        # Types
        cfg['sc_tool'][stage]['exe']['type'] = ["string"]
        cfg['sc_tool'][stage]['opt']['type'] = ["string"]
        cfg['sc_tool'][stage]['refdir']['type'] = ["file"]
        cfg['sc_tool'][stage]['script']['type'] = ["file"]
        cfg['sc_tool'][stage]['format']['type'] = ["string"]
        cfg['sc_tool'][stage]['jobid']['type'] = ["int"]
        cfg['sc_tool'][stage]['np']['type'] = ["int"]

        # Hash
        cfg['sc_tool'][stage]['refdir']['hash'] = []
        cfg['sc_tool'][stage]['script']['hash'] = []

        # Default value
        cfg['sc_tool'][stage]['exe']['defvalue'] = []
        cfg['sc_tool'][stage]['opt']['defvalue'] = []
        cfg['sc_tool'][stage]['refdir']['defvalue'] = []
        cfg['sc_tool'][stage]['script']['defvalue'] = []
        cfg['sc_tool'][stage]['format']['defvalue'] = []
        cfg['sc_tool'][stage]['np']['defvalue'] = []
        cfg['sc_tool'][stage]['jobid']['defvalue'] = ["0"]

    return cfg


