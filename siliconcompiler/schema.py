# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

###########################

def schema():
    '''Method for defining Chip configuration schema 
    All the keys defined in this dictionary are reserved words. 
    '''
    
    cfg = {}

    cfg = schema_fpga(cfg)
    
    cfg = schema_pdk(cfg)

    cfg = schema_libs(cfg, 'stdcells')

    cfg = schema_libs(cfg, 'macro')

    cfg = schema_eda(cfg)

    cfg = schema_design_rtl(cfg)
    
    cfg = schema_design_physical(cfg)

    cfg = schema_mcmm(cfg)

    cfg = schema_options(cfg)


    return cfg

############################################
# FPGA
#############################################

def schema_fpga(cfg):
    ''' FPGA Setup
    '''
    cfg['sc_fpga_xml'] = {
        'help' : 'FPGA architecture description file (xml)',
        'long_help' : [
            "line one.........................................................",
            "line two.........................................................",
            "line three......................................................."
        ],
        'switch' : '-fpga_xml',
        'switch_args' : '<target file>',
        'type' : ['string', 'file'],
        'defvalue' : []
    }

    return cfg


############################################
# PDK
#############################################

def schema_pdk(cfg):
    ''' Process Design Kit Setup
    '''
         
    cfg['sc_pdk_foundry'] = {
        'help' : 'Foundry name',
        'switch' : '-pdk_foundry',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_pdk_process'] = {
        'help' : 'Process name',
        'switch' : '-pdk_process',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_pdk_node'] = {
        'help' : 'Process node (in nm)',
        'switch' : '-pdk_node',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }

    cfg['sc_pdk_version'] = {
        'help' : 'Process node version',
        'switch' : '-pdk_version',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }
        
    cfg['sc_pdk_guide'] = {
        'help' : 'Process Manual',
        'switch' : '-pdk_guide',
        'switch_args' : '<file>',  
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_pdk_drm'] = {
        'help' : 'Process Design Rule Manual',
        'switch' : '-pdk_drm',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_pdk_stackup'] = {
        'help' : 'Process Metal Stackup',
        'switch' : '-pdk_stackup',
        'switch_args' : '<name>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_pdk_devicemodel'] = {}
    cfg['sc_pdk_devicemodel']['default'] = {}
    cfg['sc_pdk_devicemodel']['default']['default'] = {}
    cfg['sc_pdk_devicemodel']['default']['default']['default'] = {
        'help' : 'Device model directory',
        'switch' : '-pdk_devicemodel',
        'switch_args' : '<stackup type vendor file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_pdk_pexmodel'] = {}
    cfg['sc_pdk_pexmodel']['default'] = {}
    cfg['sc_pdk_pexmodel']['default']['default']= {}
    cfg['sc_pdk_pexmodel']['default']['default']['default'] = {
        'help' : 'Back end PEX TCAD model',
        'switch' : '-pdk_pexmodel',
        'switch_args' : '<stackup corner vendor file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_pdk_layermap'] = {}
    cfg['sc_pdk_layermap']['default'] = {}

    cfg['sc_pdk_layermap']['default']['streamout'] = {}
    cfg['sc_pdk_layermap']['default']['streamout']['default'] = {
        'help' : 'Layout streamout layermap',
        'switch' : '-pdk_layermap_streamout',
        'switch_args' : '<stackup tool file>', 
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_pdk_layermap']['default']['streamin'] = {}
    cfg['sc_pdk_layermap']['default']['streamin']['default'] = {
        'help' : 'Layout streamin layermap',
        'switch' : '-pdk_layermap_streamin',
        'switch_args' : '<stackup tool file>', 
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    
    cfg['sc_pdk_display'] = {}
    cfg['sc_pdk_display']['default'] = {}
    cfg['sc_pdk_display']['default']['default'] = {
        'help' : 'Custom design display configuration',
        'switch' : '-pdk_display',
        'switch_args' : '<stackup vendor file>', 
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_pdk_clib'] = {}
    cfg['sc_pdk_clib']['default'] = {}
    cfg['sc_pdk_clib']['default']['default'] = {
        'help' : 'Custom design library',
        'switch' : '-pdk_clib',
        'switch_args' : '<stackup vendor file>', 
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    
    cfg['sc_pdk_init'] = {}
    cfg['sc_pdk_init']['default'] = {}
    cfg['sc_pdk_init']['default']['default'] = {
        'help' : 'Custom design init file',
        'switch' : '-pdk_init',
        'switch_args' : '<stackup vendor file>', 
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_pdk_objmap'] = {}
    cfg['sc_pdk_objmap']['default'] = {}
    cfg['sc_pdk_objmap']['default']['default'] = {
        'help' : 'GDS object map',
        'switch' : '-pdk_objmap',
        'switch_args' : '<stackup vendor file>', 
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    ###################
    # Place and Route
    ###################
    
    cfg['sc_pdk_pnrdir'] = {}
    cfg['sc_pdk_pnrdir']['default'] = {}
    cfg['sc_pdk_pnrdir']['default']['default'] = {}
    cfg['sc_pdk_pnrdir']['default']['default']['default'] = {
        'help' : 'Place and route technology directory',
        'switch_args' : '<stackup lib vendor file>', 
        'switch' : '-pdk_pnrdir',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_pdk_pnrtech'] = {}
    cfg['sc_pdk_pnrtech']['default'] = {}
    cfg['sc_pdk_pnrtech']['default']['default'] = {}
    cfg['sc_pdk_pnrtech']['default']['default']['default'] = {
        'help' : 'Place and route tehnology file',
        'switch' : '-pdk_pnrtech',
        'switch_args' : '<stackup lib vendor file>', 
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_pdk_pnrmap'] = {}
    cfg['sc_pdk_pnrmap']['default'] = {}    
    cfg['sc_pdk_pnrmap']['default']['default'] = {
        'help' : 'Place and route layer gdsout mapping file',
        'switch' : '-pdk_pnrgdsmap',
        'switch_args' : '<stackup vendor file>', 
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_pdk_pnrlayer'] = {}
    cfg['sc_pdk_pnrlayer']['default'] = {}
    cfg['sc_pdk_pnrlayer']['default']['default'] = {
        'help' : 'Place and route routing layer definitions',
        'switch' : '-pdk_pnrlayer',
        'switch_args' : '<stackup layername X|Y width pitch>', 
        'type' : ['string', 'string', 'float', 'float'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_pdk_tapmax'] = {
        'help' : 'Tap cell max distance rule',
        'switch' : '-pdk_tapmax',
        'switch_args' : '<float>',     
        'type' : ['float'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_pdk_tapoffset'] = {
        'help' : 'Tap cell offset rule',
        'switch' : '-pdk_tapoffset',
        'switch_args' : '<float>',     
        'type' : ['float'],
        'defvalue' : [],
        'hash' : []
    }

    return cfg

############################################
# Library Configuration
#############################################   

def schema_libs(cfg, group):

    cfg['sc_'+group] = {}  

    cfg['sc_'+group]['default'] = {}
    
    # Version #
    cfg['sc_'+group]['default']['version'] = {
        'help' : 'Library release version',
        'switch' : '-'+group+'_version',
        'switch_args' : '<lib version>',     
        'type' : ['string'],
        'defvalue' : []
    }

    # Userguide
    cfg['sc_'+group]['default']['userguide'] = {
        'help' : 'Library userguide',
        'switch' : '-'+group+'_userguide',
        'switch_args' : '<lib file>',     
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    # Datasheets
    cfg['sc_'+group]['default']['datasheet'] = {
        'help' : 'Library datasheets',
        'switch' : '-'+group+'_datasheet',
        'switch_args' : '<lib path>',  
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    # Non linear delay models (timing only)
    cfg['sc_'+group]['default']['nldm'] = {}
    cfg['sc_'+group]['default']['nldm']['default'] = {
        'help' : 'Library non-linear delay timing model',
        'switch' : '-'+group+'_nldm',
        'switch_args' : '<lib corner file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_'+group]['default']['ccs'] = {}
    cfg['sc_'+group]['default']['ccs']['default'] = {
        'help' : 'Library composite current source model',
        'switch' : '-'+group+'_ccs',
        'switch_args' : '<lib corner file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_'+group]['default']['lef'] = {
        'help' : 'Library layout exchange file (LEF)',
        'switch' : '-'+group+'_lef',
        'switch_args' : '<lib file>',     
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
  
    cfg['sc_'+group]['default']['gds'] = {
        'help' : 'Library GDS file',
        'switch' : '-'+group+'_gds',
        'switch_args' : '<lib file>',        
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['cdl'] = {
        'help' : 'Library CDL file',
        'switch' : '-'+group+'_cdl',
        'switch_args' : '<lib file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['spice'] = {
        'help' : 'Library Spice file',
        'switch' : '-'+group+'_spice',
        'switch_args' : '<lib file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['verilog'] = {
        'help' : 'Library Verilog file',
        'switch' : '-'+group+'_verilog',
        'switch_args' : '<lib file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['atpg'] = {
        'help' : 'Library ATPG file',
        'switch' : '-'+group+'_atpg',
        'switch_args' : '<lib file>',    
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_'+group]['default']['setup'] = {
        'help' : 'Library TCL setup file',
        'switch' : '-'+group+'_setup',
        'switch_args' : '<lib file>',    
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 
           
    cfg['sc_'+group]['default']['site'] = {
        'help' : 'Library placement site',
        'switch' : '-'+group+'_site',
        'switch_args' : '<lib site width height>',     
        'type' : ['string', 'float', 'float'],
        'defvalue' : []
    }

    cfg['sc_'+group]['default']['pgmetal'] = {
        'help' : 'Library power rail metal layer',
        'switch' : '-'+group+'_pgmetal',
        'switch_args' : '<lib metal-layer>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_'+group]['default']['vt'] = {
        'help' : 'Library Transistor Threshold',
        'switch' : '-'+group+'_vt',
        'switch_args' : '<lib vt-type>',
        'type' : ['string'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg['sc_'+group]['default']['tag'] = {
        'help' : 'Library indentifier tags',
        'switch' : '-'+group+'_tag',
        'switch_args' : '<lib tag>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_'+group]['default']['driver'] = {
        'help' : 'Library default driver cell',
        'switch' : '-'+group+'_driver',
        'switch_args' : '<lib name>',
        'type' : ['string'],
        'defvalue' : []
    }

    #Dont use cell lists
    cfg['sc_'+group]['default']['exclude'] = {}
    cfg['sc_'+group]['default']['exclude']['default'] = {}
    cfg['sc_'+group]['default']['exclude']['default']['default'] = {
        'help' : 'Library cell exclude lists',
        'switch' : '-'+group+'_exclude',
        'switch_args' : '<lib type stage>',
        'type' : ['string'],
        'defvalue' : []
    }
    cfg['sc_'+group]['default']['include'] = {}
    cfg['sc_'+group]['default']['include']['default'] = {}
    cfg['sc_'+group]['default']['include']['default']['default'] = {
        'help' : 'Library cell include lists',
        'switch' : '-'+group+'_include',
        'switch_args' : '<lib type stage>',
        'type' : ['string'],
        'defvalue' : []
    }

    #Vendor compiled databases
    cfg['sc_'+group]['default']['nldmdb'] = {}
    cfg['sc_'+group]['default']['nldmdb']['default'] = {}
    cfg['sc_'+group]['default']['nldmdb']['default']['default'] = {
        'help' : 'Library NLDM compiled database',
        'switch' : '-'+group+'_nldmdb',
        'switch_args' : '<lib corner vendor file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['sc_'+group]['default']['ccsdb'] = {}
    cfg['sc_'+group]['default']['ccsdb']['default'] = {}
    cfg['sc_'+group]['default']['ccsdb']['default']['default'] = {
        'help' : 'Library CCS compiled databse',
        'switch' : '-'+group+'_ccsdb',
        'switch_args' : '<lib corner vendor file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    cfg['sc_'+group]['default']['pnrdb'] = {}
    cfg['sc_'+group]['default']['pnrdb']['default'] = {}
    cfg['sc_'+group]['default']['pnrdb']['default']['default'] = {
        'help' : 'Library layout compiled database',
        'switch' : '-'+group+'_pnrdb',
        'switch_args' : '<lib vendor file>',    
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
    
    return cfg

############################################
# EDA Configuration
#############################################

def schema_eda(cfg):

    cfg['sc_stages'] = {
        'help' : 'List of all compilation stages',
        'switch' : '-stages',
        'type' : ['string'],
        'defvalue' : ['import',
                      'syn',
                      'floorplan',
                      'place',
                      'cts',
                      'route',
                      'signoff',
                      'export',
                      'lec',
                      'pex',
                      'sta',
                      'pi',
                      'si',
                      'drc',
                      'erc',                    
                      'lvs',
                      'tapeout']
    }

    cfg['sc_tool'] = {}
   
    # Defaults and config for all stages
    for stage in cfg['sc_stages']['defvalue']:        
        cfg['sc_tool'][stage] = {}
        for key in ('exe', 'opt', 'refdir', 'script', 'copy', 'format', 'jobid', 'np', 'keymap','vendor'):
            cfg['sc_tool'][stage][key] = {}
            cfg['sc_tool'][stage][key]['switch'] = '-tool_'+key
            
        # Help
        cfg['sc_tool'][stage]['exe']['help'] = 'Stage executable'
        cfg['sc_tool'][stage]['opt']['help'] = 'Stage executable options'
        cfg['sc_tool'][stage]['refdir']['help'] = 'Stage reference Flow Directory'
        cfg['sc_tool'][stage]['script']['help'] = 'Stage entry point script'
        cfg['sc_tool'][stage]['copy']['help'] = 'Stage copy-to-local option'
        cfg['sc_tool'][stage]['format']['help'] = 'Stage configuration format'
        cfg['sc_tool'][stage]['jobid']['help'] = 'Stage job index'
        cfg['sc_tool'][stage]['np']['help'] = 'Stage thread parallelism'
        cfg['sc_tool'][stage]['keymap']['help'] = 'Stage keyword translation'
        cfg['sc_tool'][stage]['vendor']['help'] = 'Stage tool vendor'

        # Switch Args
        cfg['sc_tool'][stage]['exe']['switch_args'] = '<stage string>'
        cfg['sc_tool'][stage]['opt']['switch_args'] = '<stage string>'
        cfg['sc_tool'][stage]['refdir']['switch_args'] = '<stage dir>'
        cfg['sc_tool'][stage]['script']['switch_args'] = '<stage file>'
        cfg['sc_tool'][stage]['copy']['switch_args'] = '<stage string>'
        cfg['sc_tool'][stage]['format']['switch_args'] = '<stage string>'
        cfg['sc_tool'][stage]['jobid']['switch_args'] = '<stage int>'
        cfg['sc_tool'][stage]['np']['switch_args'] = '<stage int>'
        cfg['sc_tool'][stage]['keymap']['switch_args'] = '<stage string string>'
        cfg['sc_tool'][stage]['vendor']['switch_args'] = '<stage string>'        

        # Types
        cfg['sc_tool'][stage]['exe']['type'] = ['string']
        cfg['sc_tool'][stage]['opt']['type'] = ['string']
        cfg['sc_tool'][stage]['refdir']['type'] = ['file']
        cfg['sc_tool'][stage]['script']['type'] = ['file']
        cfg['sc_tool'][stage]['copy']['type'] = ['string']
        cfg['sc_tool'][stage]['format']['type'] = ['string']
        cfg['sc_tool'][stage]['jobid']['type'] = ['int']
        cfg['sc_tool'][stage]['np']['type'] = ['int']
        cfg['sc_tool'][stage]['keymap']['type'] = ['string', 'string']
        cfg['sc_tool'][stage]['vendor']['type'] = ['string']

        # Hash
        cfg['sc_tool'][stage]['refdir']['hash'] = []
        cfg['sc_tool'][stage]['script']['hash'] = []

        # Default value
        cfg['sc_tool'][stage]['exe']['defvalue'] = []
        cfg['sc_tool'][stage]['opt']['defvalue'] = []
        cfg['sc_tool'][stage]['refdir']['defvalue'] = []
        cfg['sc_tool'][stage]['script']['defvalue'] = []
        cfg['sc_tool'][stage]['copy']['defvalue'] = []
        cfg['sc_tool'][stage]['format']['defvalue'] = []
        cfg['sc_tool'][stage]['np']['defvalue'] = []
        cfg['sc_tool'][stage]['keymap']['defvalue'] = []
        cfg['sc_tool'][stage]['vendor']['defvalue'] = []
        cfg['sc_tool'][stage]['jobid']['defvalue'] = ['0']

    return cfg


############################################
# Design Specific Parameters
#############################################

def schema_design_rtl(cfg):
    ''' Design setup
    '''

    cfg['sc_source'] = {
        'help' : 'Source files (.v/.vh/.sv/.vhd)',
        'switch' : 'None',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
        
    cfg['sc_design'] = {
        'help' : 'Design top module name',
        'switch' : '-design',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_clk'] = {
        'help' : 'Clock defintion',
        'switch' : '-clk',
        'switch_args' : '<name period uncertainty>',
        'type' : ['string', 'float', 'float'],
        'defvalue' : []
    }

    cfg['sc_supply'] = {
        'help' : 'Power supply',
        'switch' : '-supply',
        'switch_args' : '<name pin voltage>',
        'type' : ['string', 'string', 'float'],
        'defvalue' : []
    }
    
    cfg['sc_define'] = {
        'help' : 'Define variables for Verilog preprocessor',
        'switch' : '-D',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }
    
    cfg['sc_ydir'] = {
        'help' : 'Directory to search for modules',
        'switch' : '-y',
        'switch_args' : '<dir>',
        'type' : ['string'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_idir'] = {
        'help' : 'Directory to search for includes',
        'switch' : '-I',
        'switch_args' : '<dir>',
        'type' : ['string'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_vlib'] = {
        'help' : 'Library file',
        'switch' : '-v',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_libext'] = {
        'help' : 'Extension for finding modules',
        'switch' : '+libext',
        'switch_args' : '<ext>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_readscript'] = {
        'help' : 'Source file read script',
        'switch' : '-f',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    return cfg

def schema_design_physical(cfg):
    ''' Physical design parameters
    '''
    
    cfg['sc_target'] = {
        'help' : 'Target platform',
        'switch' : '-target',
        'switch_args' : '<string>',        
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_target_stackup'] = {
        'help' : 'Target metal stackup',
        'switch' : '-target_stackup',
        'switch_args' : '<string>',        
        'type' : ['string'],
        'defvalue' : []
    }
    
    cfg['sc_target_lib'] = {
        'help' : 'Target library/device',
        'switch' : '-target_lib',
        'switch_args' : '<string>',        
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_target_libarch'] = {
        'help' : 'Target library architecture',
        'switch' : '-target_libarch',
        'switch_args' : '<string>',        
        'type' : ['string'],
        'defvalue' : []
    }

    # custom pass through variables
    cfg['sc_custom'] = {
        'help' : 'Custom EDA pass through variables',
        'switch' : '-custom',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    # floorplanning
    cfg['sc_def'] = {
        'help' : 'Firm floorplan file (DEF)',
        'switch' : '-def',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
     }

    cfg['sc_floorplan'] = {
        'help' : 'Floorplaning script/program',
        'switch' : '-floorplan',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    #automated floorplanning
    cfg['sc_coremargin'] = {
        'help' : 'Core place and route halo margin (um)',
        'switch' : '-coremargin',
        'switch_args' : '<float>',
        'type' : ['float'],
        'defvalue' : []
    }

    cfg['sc_aspectratio'] = {
        'help' : 'Target aspect ratio',
        'switch' : '-aspectratio',
        'switch_args' : '<float>',
        'type' : ['float'],
        'defvalue' : []
    }

    cfg['sc_density'] = {
        'help' : 'Target core density (percent)',
        'switch' : '-density',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }

    cfg['sc_diesize'] = {
        'help' : 'Target die size (x0 y0 x1 y1) (um)',
        'switch' : '-diesize',
        'switch_args' : '<float float float float>',
        'type' : ['float', 'float', 'float', 'float'],
        'defvalue' : []
    }

    cfg['sc_coresize'] = {
        'help' : 'Target core size (x0 y0 x1 y1) (um)',
        'switch' : '-coresize',
        'switch_args' : '<float float float float>',
        'type' : ['float', 'float', 'float', 'float'],
        'defvalue' : []
    }
    
    cfg['sc_ndr'] = {
        'help' : 'Non-default net routing file',
        'switch' : '-ndr',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
 
    #designer options
    cfg['sc_minlayer'] = {
        'help' : 'Minimum routing layer (integer)',
        'switch' : '-minlayer',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }

    cfg['sc_maxlayer'] = {
        'help' : 'Maximum routing layer (integer)',
        'switch' : '-maxlayer',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }
    
    cfg['sc_maxfanout'] = {
        'help' : 'Maximum fanout',
        'switch' : '-maxfanout',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }
   
    #power
    cfg['sc_vcd'] = {
        'help' : 'Value Change Dump (VCD) file',
        'switch' : '-vcd',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_saif'] = {
        'help' : 'Switching activity (SAIF) file',
        'switch' : '-saif',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
    
    return cfg
    
############################################
# MMCM Configuration
#############################################   

def schema_mcmm(cfg):

    cfg['sc_mcmm_libcorner'] = {
        'help' : 'MMCM Lib Corner List (p_v_t)',
        'switch' : '-mcmm_libcorner',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_mcmm_pexcorner'] = {
        'help' : 'MMCM PEX Corner List',
        'switch' : '-mcmm_pexcorner',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_mcmm_scenario'] = {}
    cfg['sc_mcmm_scenario']['default'] = {}
    
    cfg['sc_mcmm_scenario']['default']['libcorner'] = {
        'help' : 'MMCM scenario libcorner',
        'switch' : '-mcmm_scenario_libcorner',
        'switch_args' : '<scenario libcorner>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_mcmm_scenario']['default']['pexcorner'] = {
        'help' : 'MMCM scenario pexcorner',
        'switch' : '-mcmm_scenario_pexcorner',
        'switch_args' : '<scenario pexcorner>',
        'type' : ['string'],
        'defvalue' : []
    }
      
    cfg['sc_mcmm_scenario']['default']['opcond'] = {
        'help' : 'MMCM scenario operating condition and library',
        'switch' : '-mcmm_scenario_opcond',
        'switch_args' : '<scenario (opcond library)>',
        'type' : ['string', 'string'],
        'defvalue' : []
    }
        
    cfg['sc_mcmm_scenario']['default']['constraints'] = {
        'help' : 'MMCM scenario constraints',
        'switch' : '-mcmm_scenario_constraints',
        'switch_args' : '<scenario stage file>',
        'type' : ['file'],
        'hash' : [],
        'defvalue' : []
    }

    cfg['sc_mcmm_scenario']['default']['objectives'] = {
        'help' : 'MMCM Objectives (setup, hold, power,...)',
        'switch' : '-mcmm_scenario_objectives',
        'switch_args' : '<scenario stage objective>',
        'type' : ['string'],
        'defvalue' : []
    }

    return cfg


def schema_options(cfg):
    ''' Run-time options
    '''

    cfg['sc_env'] = {
        'help' : 'PDK imposed environment variables to set',
        'switch' : '-env',
        'switch_args' : '<varname value>',
        'type' : ['string', 'file'],
        'defvalue' : []
    }

    cfg['sc_cfgfile'] = {
        'help' : 'Loads configurations from a json file',
        'switch' : '-cfgfile',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['sc_lock'] = {
        'help' : 'Locks the configuration dict from edit',
        'switch' : '-lock',
        'switch_args' : '',
        'type' : ['bool'],
        'defvalue' : ['False'],
    }

    cfg['sc_quiet'] = {
        'help' : 'Supresses informational printing',
        'switch' : '-quiet',
        'switch_args' : '',
        'type' : ['bool'],
        'defvalue' : ['False'],
    }
    
    
    cfg['sc_remote'] = {
        'help' : 'Remote server (https://acme.com:8080)',
        'switch' : '-remote',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_debug'] = {
        'help' : 'Debug level (INFO/DEBUG/WARNING/ERROR)',
        'switch' : '-debug',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['INFO']
    }

    cfg['sc_build'] = {
        'help' : 'Name of build directory',
        'switch' : '-build',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['build']
    }

    cfg['sc_effort'] = {
        'help' : 'Compilation effort',
        'switch' : '-effort',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['high']
    }

    cfg['sc_priority'] = {
        'help' : 'Optimization priority',
        'switch' : '-priority',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['timing']
    }

    cfg['sc_start'] = {
        'help' : 'Compilation starting stage',
        'type' : 'string',
        'switch' : '-start',
        'switch_args' : '<stage>',
        'defvalue' : ['import']
    }

    cfg['sc_stop'] = {
        'help' : 'Compilation ending stage',
        'switch' : '-stop',
        'switch_args' : '<stage>',
        'type' : ['string'],
        'defvalue' : ['export']
    }
    
    cfg['sc_nickname'] = {
        'help' : 'Design nickname',
        'switch' : '-nickname',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_msg_trigger'] = {
        'help' : 'Trigger for messaging to <sc_msg_contact>',
        'switch' : '-msg_trigger',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['sc_msg_contact'] = {
        'help' : 'Trigger event contact (phone#/email)',
        'switch' : '-msg_contact',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    return cfg
