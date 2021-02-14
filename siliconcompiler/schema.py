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

    cfg = schema_libs(cfg, 'macros')

    cfg = schema_eda(cfg)

    cfg = schema_options(cfg)
    
    cfg = schema_rtl(cfg)

    cfg = schema_constraints(cfg)

    cfg = schema_floorplan(cfg)
    
    cfg = schema_apr(cfg)

    cfg = schema_net(cfg)

    return cfg

###############################################################################
# FPGA
###############################################################################

def schema_fpga(cfg):
    ''' FPGA Setup
    '''
    cfg['fpga_xml'] = {
        'short_help' : 'FPGA Architecture Description',
        'help' : ["The file provides XML-based architecture description for ",
                  "the target FPGA architecture to be used in VTR allowing  ",
                  "the user to describe a large number of hypothetical and  ",
                  "commercial architectures.                                ",
                  "[More information...](https://verilogtorouting.org)      "],
        'switch' : '-fpga_xml',
        'switch_args' : '<>',
        'requirement' : 'fpga',
        'type' : ['string', 'file'],
        'defvalue' : []
    }

    return cfg


###############################################################################
# PDK
###############################################################################

def schema_pdk(cfg):
    ''' Process Design Kit Setup
    '''
         
    cfg['pdk_foundry'] = {
        'short_help' : 'Foundry Name',
        'help' : ["The name of the foundry. Example values include: tsmc,  ",
                  "gf, samsung, intel, skywater, virtual. The virtual      ",
                  "keyword is reserved for simulated processes that can't  ",
                  "like nangate45 and asap7.                               "],
        'switch' : '-pdk_foundry',
        'switch_args' : '<str>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['pdk_process'] = {
        'short_help' : 'Process Name',
        'help' : ["The official name of the process within a foundry. The   ",
                  "name is case insensitive, but should otherwise match the ",
                  "complete public process name from the foundry. Examples  ",
                  "process names include 22FFL from Intel, 12LPPLUS from    ",
                  "Globalfoundries, and 16FFC from TSMC.                    "],
        'switch' : '-pdk_process',
        'switch_args' : '<str>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['pdk_node'] = {
        'short_help' : 'Process Node',
        'help' : ["An approximation of the relative minimum dimension       ",
                  "of the process node. Not a required parameter but may be ",
                  "used to select technology dependant synthesis and place  ",
                  "and route optimization algorithms and recipes. Examples  ",
                  "of nodes include 180nm, 130nm, 90nm, 65nm, 45m,32nm, 22nm",
                  "15nm, 10nm, 7nm, 5nm                                     "],
        'switch' : '-pdk_node',
        'switch_args' : '<num>',
        'requirement' : 'asic',
        'type' : ['int'],
        'defvalue' : []
    }

    cfg['pdk_rev'] = {
        'short_help' : 'Process Node Rev',
        'help' : ["The PDK rev is an alphanumeric string provided by to ",
                  "track changes in critical process design kit data shipped",
                  "to foundry customers. Designers should manually or       ",
                  "automatically verify that the PDK rev is approved    ",
                  "for new tapeouts.                                        "],
        'switch' : '-pdk_rev',
        'switch_args' : '<str>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }
        
    cfg['pdk_guide'] = {
        'short_help' : 'Process Guide',
        'help' : ["All PDKs ship with extensive documeation, generally      ",
                  "provided as PDFs. This first item in this parameter list ",
                  "should be the the primary PDK usage guide, while the rest",
                  "of the list would contain other important documents. The ",
                  "variable's purpose to serve as a central record for the  ",
                  "documents that can at times be hard to locate quickly in ",
                  "in complex advanced node PDKs. Example use cases include ",
                  "automatic PDF viewer launch of the document or static    ",
                  "static HTML page construction with links to all docsl    "],
        'switch' : '-pdk_guide',
        'switch_args' : '<file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_drm'] = {
        'short_help' : 'Process Design Rule Manual',
        'help' : ["A PDK document that includes detailed information about  ",
                  "all design rules to comply with in the design and        ",
                  "layout of a chip.                                        "],
        'switch' : '-pdk_drm',
        'switch_args' : '<file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_stackup'] = {
        'short_help' : 'Process Metal Stackup',
        'help' : ["A list of all metal stackups offered in the process node ",
                  "Older process nodes may only offer a single metal        ",
                  "stackup, while advanced nodes offer a large but finite   ",
                  "list of metal stacks with varying combinations of        ",
                  "metal line widths and thicknesses. Stackup naming is     ",
                  "unique to the foundry, but is generally a long string,   ",
                  "or code. For example, a 10 metal stackup two 1x wide,    ",
                  "four 2x wide, and 2 4x wide metals, might be identified  ",
                  "as 2MA_4MB_2MC. Each stackup will come with its own set  ",
                  "routing technology files and parasitic models specified  ",
                  "in the pdk_pexmodel and pdk_aprtech variables.           "],
        'switch' : '-pdk_stackup',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['pdk_model'] = {}
    cfg['pdk_model']['default'] = {}
    cfg['pdk_model']['default']['default'] = {}
    cfg['pdk_model']['default']['default']['default'] = {
        'short_help' : 'Device Model',
        'help' : ["A dynamic structure of paths to various device models.   ",
                  "The structure serves as a central access registry for    ",
                  "models for different purpose and vendors. The nested     ",
                  "dictionary order is [stackup][type][vendor]. For models  ",
                  "that span all metal stackups, the model directory        ",
                  "pointer can be trivially duplicated using a python for   ",
                  "loop in the PDK setup file. Examples of model types      ",
                  "include spice, aging, electromigration, radiation        "],
        'switch' : '-pdk_model',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_pexmodel'] = {}
    cfg['pdk_pexmodel']['default'] = {}
    cfg['pdk_pexmodel']['default']['default']= {}
    cfg['pdk_pexmodel']['default']['default']['default'] = {
        'short_help' : 'Parastic Extraction TCAD Model',
        'help' : ["A dynamic structure of paths to PDK parasitic models.    ",
                  "Modern PDKs include encrypted parasitic models for each  ",
                  "stackup offered, often with characterization across      ",
                  "multiple statitical process corners. The nested          ",
                  "dictionary order is [stackup][corner][vendor].           ",
                  "The methodology for applying these models is described   ",
                  "in the PDK docs. Within the digital place and route      ",
                  "flows the pex models must be accessed through the        ",
                  "pdk_pexmodel structure.                                  "],
        'switch' : '-pdk_pexmodel',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_layermap'] = {}
    cfg['pdk_layermap']['default'] = {}
    cfg['pdk_layermap']['default']['default'] = {}
    cfg['pdk_layermap']['default']['default']['streamout'] = {
        'short_help' : 'Layout Streamout Layermap',
        'help' : ["This structure contains pointers to the various layer    ",
                  "mapping files needed to stream data out from binary      ",
                  "databases to tapeout read GDSII datbases. The layer map  ",
                  "supplied in the PDK on a per stackup basis and the       ",
                  "nested dictionary order is [stackup][tool][streamout].   "],
        'switch' : '-pdk_streamout',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['pdk_layermap']['default']['default']['streamin'] = {
        'short_help' : 'Layout Streamin Layermap',
        'help' : ["This structure contains pointers to the various layer    ",
                  "mapping files needed to stream data into binary          ",
                  "databases. The layer map supplied in the PDK on a per    ",
                  "stackup basis and the nested dictionary order is         ",
                  "[stackup][tool][streamout].                              "],
        'switch' : '-pdk_streamin',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    
    cfg['pdk_display'] = {}
    cfg['pdk_display']['default'] = {}
    cfg['pdk_display']['default']['default'] = {
        'short_help' : 'Custom Design Display Configuration',
        'help' : ["This structure contains a display configuration file     ",
                  "for colors and pattern schemes for all layers in the     ",
                  "PDK. The layer map supplied in the PDK on a per          ",
                  "stackup basis and the nested dictionary order is         ",
                  "[stackup][tool].                                         "],
        'switch' : '-pdk_display',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['pdk_clib'] = {}
    cfg['pdk_clib']['default'] = {}
    cfg['pdk_clib']['default']['default'] = {
        'short_help' : 'Custom Design Library',
        'help' : ["A file containing pointers to all custom cell libs.      ",
                  "Examples include pcell libraries and pycell libs         ",
                  "The file is supplied in the PDK on a per stackup basis   ",
                  "and the nested dictionary order is [stackup][tool].      "],
        'switch' : '-pdk_clib',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    
    # Place and Route
    cfg['pdk_aprtech'] = {}
    cfg['pdk_aprtech']['default'] = {}
    cfg['pdk_aprtech']['default']['default'] = {}
    cfg['pdk_aprtech']['default']['default']['default'] = {
        'short_help' : 'Place and Route Tehnology File',
        'help' : ["Technology file for place and route tools. The file      ",
                  "contains the necessary information needed to create DRC  ",
                  "compliant automatically routed designs. The file is      ",
                  "vendor specific with the most commonf format being LEF.  ",
                  "The nested dictionary order is [stackup][arch][tool], ",
                  "where arch stands for the library type, generally the ",
                  "library height. For example a node might support 6 track,",
                  "7.5 track and 9 track high libraries with arch names  ",
                  "of 6T, 7.5T, 9T                                          "],
        'switch' : '-pdk_aprtech',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_aprdir'] = {}
    cfg['pdk_aprdir']['default'] = {}
    cfg['pdk_aprdir']['default']['default'] = {}
    cfg['pdk_aprdir']['default']['default']['default'] = {
        'short_help' : 'Place and Route Setup Directory ',
        'help' : ["Directory containing various setup files for place and   ",
                  "route tools. These files are avaialble in the PDK  on a  ",
                  "per tool and per stackup basis. The directory pointer    ",
                  "is not required by all tools. when provided, the nested  ",
                  "dictionary order is [stackup][arch][tool], where      ",
                  "arch stands for the library type, generally the       ",
                  "library height. For example a node might support 6       ",
                  "track, 7.5 track and 9 track high libraries with         ",
                  "arch names of 6T, 7.5T, 9T                            "],
        'switch' : '-pdk_aprdir',
        'switch_args' : '<>', 
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    
    cfg['pdk_aprlayer'] = {}
    cfg['pdk_aprlayer']['default'] = {
        'short_help' : 'Place and Route Layer Definitions',
        'help' : ["In experimental settings and for immature PDKs there may ",
                  "be a need to override the design rules defined int he    ",
                  "pdk_aprtech file. This should be done using using        ",
                  "pdk_aprlayer.The layer definition is given as a tuple on ",
                  "a per stackup basis. An hypothetical example of a valid  ",
                  "layer definition would be metal1 X 0.5 1.0 for defining  ",
                  "metal1 as a horizontal routing layer with a 0.5um width  ",
                  "and 1.0um pitch grid.                                    "],
        'switch' : '-pdk_aprlayer',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string', 'string', 'float', 'float'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_tapmax'] = {
        'short_help' : 'Tap Cell Max Distance Rule',
        'help' : ["Sets the maximum distance between tap cells for the place",
                  "and route tool. This value is derived from the design    ",
                  "rule manual and the methodology guides within the PDK.   "],
        'switch' : '-pdk_tapmax',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['float'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['pdk_tapoffset'] = {
        'short_help' : 'Tap Cell Offset Rule',
        'help' : ["Sets the offset from the edge of the block to place a tap",
                  "cell for the place route tool. This value is derived from",
                  "the design rule manual and the methodology guides within ",
                  "the PDK.                                                 "],
        'switch' : '-pdk_tapoffset',
        'switch_args' : '<num>',
        'requirement' : 'apr',
        'type' : ['float'],
        'defvalue' : [],
        'hash' : []
    }

    return cfg

###############################################################################
# Library Configuration
###############################################################################

def schema_libs(cfg, group):

    cfg[group] = {}  

    cfg[group]['default'] = {}
    
    # Rev #
    cfg[group]['default']['rev'] = {
        'short_help' : 'Library Release Rev',
        'help' : ["The library rev is an alphanumeric string provided by",
                  "the vendor to track changes in critical library data     ",
                  "shipped to the library customer. Designers should        ",
                  "manually or automatically verify that the library rev",
                  "is approved for tapeout                                  "],
        'switch' : '-'+group+'_rev',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }

    # user guide
    cfg[group]['default']['guide'] = {
        'short_help' : 'Library User Guide',
        'help' : ["The main documentation guide outlining how to use the IP ",
                  "successfully in ASIC design. If more than one document is",
                  "provided, the list should be ordered from most to least  ",
                  "important.                                               "],
        'switch' : '-'+group+'_guide',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    # Datasheets
    cfg[group]['default']['ds'] = {
        'short_help' : 'Library Datasheets',
        'help' : ["A complete collection of datasheets for the library. The ",
                  "documentation can be provided as a single collated PDF or",
                  "as one HTML file per cell                                "],
        'switch' : '-'+group+'_ds',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg[group]['default']['arch'] = {
        'short_help' : 'Library Architecture',
        'help' : ["A name/tag used to identify the library type for place   ",
                  "and route technology setup. Arch must match up with   ",
                  "the name used in the pdk_aprtech structure. The arch  ",
                  "is a unique a string that identifies the library height  ",
                  "or performance class of the library. Mixing of archs  ",
                  "in a flat place and route block is not allowed.          "],
        'switch' : '-'+group+'_arch',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg[group]['default']['height'] = {
        'short_help' : 'Library Height',
        'help' : ["The height of the library cells in (um). The value is    ",
                  "automatically extracted from the technology file from the",
                  "pdk_aprtech structure.                                   "], 
        'switch' : '-'+group+'_height',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['float'],
        'defvalue' : []
    }
    
    cfg[group]['default']['nldm'] = {}
    cfg[group]['default']['nldm']['default'] = {
        'short_help' : 'Library Non-Linear Delay Model File',
        'help' : ["A non-linear delay model in the liberty format. The file ",
                  "specifies timinga and logic functions to mapt the design ",
                  "to. The structure order is [library]['nldm'][corner]. The",
                  "corner is used to define scenarios and must be the       ",
                  "same as those used int he mcmm_scenario structure.       "],
        'switch' : '-'+group+'_nldm',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg[group]['default']['ccs'] = {}
    cfg[group]['default']['ccs']['default'] = {
        'short_help' : 'Library Composite Current Source Model File',
        'help' : ["A composite current source model for the library. It is  ",
                  "is more accurate than the NLDM model and recommended at  ",
                  "advanced nodes, but is significantly larger than the nldm",
                  "model and should only be used when accuracy is an        ",
                  "absolute requirement. When available, ccs models should  ",
                  "always be used for signoff timing checks.                "],
        'switch' : '-'+group+'_ccs',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg[group]['default']['lef'] = {
        'short_help' : 'Library LEF File',
        'help' : ["An abstracted view of library cells that gives complete  ",
                  "information about the cell place and route boundary, pin ",
                  "positions, pin metals, and metal routing blockages.      "],
        'switch' : '-'+group+'_lef',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
  
    cfg[group]['default']['gds'] = {
        'short_help' : 'Library GDS File',
        'help' : ["The complete mask layout of the library cells ready to be",
                  "merged with the rest of the design for tapeout. In some  ",
                  "cases, the GDS merge happens at the foundry, so inclusion",
                  "of a GDS file is optional. In all cases, where the GDS   ",
                  "files are available, they should specified here to enable",
                  "gds stream out/merge during the automated place and route",
                  "and chip assembly process.                               "],
        'switch' : '-'+group+'_gds',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg[group]['default']['cdl'] = {
        'short_help' : 'Library CDL Netlist File',
        'help' : ["The CDL file contains the netlists use for layout versus ",
                  "schematic (LVS) checks. In some cases, the GDS merge     ",
                  "happens at the foundry, so inclusion of a CDL file is    ",
                  "optional. In all cases, where the CDL files are          ",
                  "available they should specified here to enable LVS checks",
                  "pre tapout                                               "],
        'switch' : '-'+group+'_cdl',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg[group]['default']['spice'] = {
        'short_help' : 'Library Spice Netlist File',
        'help' : ["The spice file contains the netlists use for circuit     ",
                  "simulation.                                              "],
        'switch' : '-'+group+'_spice',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg[group]['default']['hdl'] = {
        'short_help' : 'Library HDL Model File',
        'help' : ["A bit exact or high level verilog model for all cells in ",
                  "the library. The file can be VHDL (.vhd) or Verilog (.v) "],
        'switch' : '-'+group+'_hdl',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg[group]['default']['atpg'] = {
        'short_help' : 'Library ATPG File',
        'help' : ["Logical model used for ATPG based chip test methods.     "],
        'switch' : '-'+group+'_atpg',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg[group]['default']['rails'] = {
        'short_help' : 'Library Power Rail Metal Layer',
        'help' : ["The variable specifies the top metal layer used for power",
                  "and ground routing. The parameter can be used to guide   ",
                  "standard cell power grid hookup within automated place   ",
                  "and route tools                                          "],
        'switch' : '-'+group+'_rails',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg[group]['default']['vt'] = {
        'short_help' : 'Library Transistor Threshold',
        'help' : ["The variable specifies the voltage threshold type of the ",
                  "library. The value is extracted automatically if found in",
                  "the default_threshold_voltage_group within the nldm      ",
                  "timing model. For older technologies with only one vt    ",
                  "group, it is recommended to set the value to rvt or svt  "],
        'switch' : '-'+group+'_vt',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['string'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg[group]['default']['tag'] = {
        'short_help' : 'Library Indentifier Tags',
        'help' : ["An arbitraty set of tags that can be used by the designer",
                  "or EDA tools for optimization purposes. The tags are     ",
                  "meant to cover features not currently supported by built ",
                  "in EDA optimization flows. Multiple tags per library is  ",
                  "supported.                                               "],
        'switch' : '-'+group+'_tag',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg[group]['default']['driver'] = {
        'short_help' : 'Library Default Driver Cell',
        'help' : ["The name of a library cell to be used as the default     ",
                  "driver for block timing constraints. The cell should be  ",
                  "strong enough to drive a block input from another block  ",
                  "including wire capacitance. In cases, where the actual   ",
                  "drive is known, the actual driver cell should be used.   "],
        'switch' : '-'+group+'_driver',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg[group]['default']['site'] = {
        'short_help' : 'Library Place and Route Site/Tile',
        'help' : ["Provides the primary site name within the library to use ",
                  "for placement. Value can generally be automatically      ",
                  "inferred from the lef file if only one site is specified "],
        'switch' : '-'+group+'_site',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }
    
    #Dont use cell lists
    cfg[group]['default']['exclude'] = {}
    cfg[group]['default']['exclude']['default'] = {
        'short_help' : 'Library Cell Exclude Lists',
        'help' : ["Lists of cells to exclude for specific stages within the ",
                  "an implementation flow. The structure of the dictionary  ",
                  "is ['exclude'][stage] = <list>.                          "],
        'switch' : '-'+group+'_exclude',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }
    cfg[group]['default']['include'] = {}
    cfg[group]['default']['include']['default'] = {
        'short_help' : 'Library Cell Include Lists',
        'help' : ["Lists of cells to include for specific stages within the ",
                  "an implementation flow. The structure of the dictionary  ",
                  "is ['include'][stage] = <list>.                          "],
        'switch' : '-'+group+'_include',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }

    #Vendor specific config
    cfg[group]['default']['config'] = {}
    cfg[group]['default']['config']['default'] = {
        'short_help' : 'Library EDA Setup File',
        'help' : ["A list of configuration files used to set up automated   ",
                  "place and route flows for specific EDA tools. The format ",
                  "of the variable is ['config']['tool'] = <filename>       "],
        'switch' : '-'+group+'_setup',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 
    
    #Vendor compiled databases
    cfg[group]['default']['nldmdb'] = {}
    cfg[group]['default']['nldmdb']['default'] = {}
    cfg[group]['default']['nldmdb']['default']['default'] = {
        'short_help' : 'Library NLDM Compiled Database',
        'help' : ["A binary compiled ndlm file for a specific EDA tool.     "],
        'switch' : '-'+group+'_nldmdb',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg[group]['default']['ccsdb'] = {}
    cfg[group]['default']['ccsdb']['default'] = {}
    cfg[group]['default']['ccsdb']['default']['default'] = {
        'short_help' : 'Library CCS Compiled Databse',
        'help' : ["A binary compiled ccs file for a specific EDA tool. The  ",
                  "dictionary format is ['ccsdb']['corner']['tool'] = <file>"],
        'switch' : '-'+group+'_ccsdb',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    cfg[group]['default']['laydb'] = {}
    cfg[group]['default']['laydb']['default'] = {
        'short_help' : 'Library Layout Compiled Database',
        'help' : ["A binary compiled library layout database for a specific ", 
                  "EDA tool. The dictionary format is:                      ",
                  "['laydb']['tool'] = <file>                               "],
        'switch' : '-'+group+'_laydb',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
    
    return cfg

###############################################################################
# EDA Tool Configuration
###############################################################################

def schema_eda(cfg):

    cfg['stages'] = {
        'short_help' : 'List of All Compilation Stages',
        'help' : ["A complete list of all stages included in fully automated",
                  "RTL to GDSII tapeout implementationa and verificatio flow",
                  "Stages can be added and skipped during flows, but not    ", 
                  "removed from the list as it would break the compiler.    "],
        'switch' : '-stages',
        'switch_args' : '<str>',
        'requirement' : 'all',
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
                      'gdsview',
                      'tapeout']
    }

    cfg['tool'] = {}
   
    # Defaults and config for all stages
    for stage in cfg['stages']['defvalue']:        
        cfg['tool'][stage] = {}
        # Exe
        cfg['tool'][stage]['exe'] = {}
        cfg['tool'][stage]['exe']['switch'] = '-tool_exe'
        cfg['tool'][stage]['exe']['switch_args'] = '<>'
        cfg['tool'][stage]['exe']['type'] = ['string']
        cfg['tool'][stage]['exe']['requirement'] = ['all']
        cfg['tool'][stage]['exe']['defvalue'] = []
        cfg['tool'][stage]['exe']['short_help'] = 'Executable'
        cfg['tool'][stage]['exe']['help'] = [
            "The name of the executable. Can be the full env path to  ",
            "the excutable or the simple name if the search path has  ",
            "already been set up in the working environment.          "]

        #opt  
        cfg['tool'][stage]['opt'] = {}
        cfg['tool'][stage]['opt']['switch'] = '-tool_opt'
        cfg['tool'][stage]['opt']['switch_args'] = '<>'
        cfg['tool'][stage]['opt']['type'] = ['string']
        cfg['tool'][stage]['opt']['requirement'] = 'optional'
        cfg['tool'][stage]['opt']['defvalue'] = []
        cfg['tool'][stage]['opt']['short_help'] = 'Executable Options'
        cfg['tool'][stage]['opt']['help'] = [
            "A list of command line options for the executable. For   ",
            "multiple argument options, enter each argument and value ",
            "as one list entry. Foe example, the argument pair        ",
            "-c 5 would be entered as one string \'-c 5\'             "]

        #refdir
        cfg['tool'][stage]['refdir'] = {}        
        cfg['tool'][stage]['refdir']['switch'] = '-tool_refdir'
        cfg['tool'][stage]['refdir']['switch_args'] = '<>'
        cfg['tool'][stage]['refdir']['type'] = ['file']
        cfg['tool'][stage]['refdir']['requirement'] = 'optional'
        cfg['tool'][stage]['refdir']['hash'] = []
        cfg['tool'][stage]['refdir']['defvalue'] = []
        cfg['tool'][stage]['refdir']['short_help'] = 'Reference Directory'
        cfg['tool'][stage]['refdir']['help'] = [
            "The directory containing the reference scripts used in   ",
            "by the stage executable.                                 "]

        #script
        cfg['tool'][stage]['script'] = {}        
        cfg['tool'][stage]['script']['switch'] = '-tool_script'
        cfg['tool'][stage]['script']['switch_args'] = '<>'
        cfg['tool'][stage]['script']['type'] = ['file']
        cfg['tool'][stage]['script']['requirement'] = 'optional'
        cfg['tool'][stage]['script']['hash'] = []
        cfg['tool'][stage]['script']['defvalue'] = []
        cfg['tool'][stage]['script']['short_help'] = 'Root Reference Script'
        cfg['tool'][stage]['script']['help'] = [
            "The top level reference script to called by the stage    ",
            "executable                                               "]

        #copy
        cfg['tool'][stage]['copy'] = {}
        cfg['tool'][stage]['copy']['switch'] = '-tool_copy'
        cfg['tool'][stage]['copy']['switch_args'] = '<>'
        cfg['tool'][stage]['copy']['type'] = ['bool']
        cfg['tool'][stage]['copy']['requirement'] = 'optional'
        cfg['tool'][stage]['copy']['defvalue'] = []
        cfg['tool'][stage]['copy']['short_help'] = 'Copy Local Option'
        cfg['tool'][stage]['copy']['help'] = [
            "Specifes that the reference script directory should be   ",
            "copied and run from the local run directory. This option ",
            "is set automatically set when the -remote option is set  "]

        #format
        cfg['tool'][stage]['format'] = {}
        cfg['tool'][stage]['format']['switch'] = '-tool_format'
        cfg['tool'][stage]['format']['switch_args'] = '<>'
        cfg['tool'][stage]['format']['type'] = ['string']
        cfg['tool'][stage]['format']['requirement'] = ['all']
        cfg['tool'][stage]['format']['defvalue'] = []
        cfg['tool'][stage]['format']['short_help'] = 'Script Format'
        cfg['tool'][stage]['format']['help'] = [
            "Specifes that format of the configuration file for the   ",
            "stage. Valid formats are tcl, yaml, and json. The format ",
            "used is dictated by the executable for the stage.        "]
        
        #jobid
        cfg['tool'][stage]['jobid'] = {}
        cfg['tool'][stage]['jobid']['switch'] = '-tool_jobid'
        cfg['tool'][stage]['jobid']['switch_args'] = '<>'
        cfg['tool'][stage]['jobid']['type'] = ['int']
        cfg['tool'][stage]['jobid']['requirement'] = ['all']
        cfg['tool'][stage]['jobid']['defvalue'] = ['0']
        cfg['tool'][stage]['jobid']['short_help'] = 'Job Index'
        cfg['tool'][stage]['jobid']['help'] = [
            "A dynamic variable that keeeps track of results to pass  ",
            "foward to the next stage of the implementation pipeline  ",
            "in cases where multiple jobs are run for one stage and a ",
            "progrematic selection if made to choose the best result, ",
            "the variable is use to point to a job which may or may   ",
            "not be the last job launched"]
        
        #np
        cfg['tool'][stage]['np'] = {}
        cfg['tool'][stage]['np']['switch'] = '-tool_np'
        cfg['tool'][stage]['np']['switch_args'] = '<>'
        cfg['tool'][stage]['np']['type'] = ['int']
        cfg['tool'][stage]['np']['requirement'] = ['all']
        cfg['tool'][stage]['np']['defvalue'] = []
        cfg['tool'][stage]['np']['short_help'] = 'Thread Parallelism'
        cfg['tool'][stage]['np']['help'] = [
            "The thread parallelism to use on a per stage basis.      ",
            "This information is intended for the EDA tools to use to ",
            "parallelize workloads on a multi-core single node CPU.   ",
            "Job parallelization across multiple machines need to be  ",
            "explicitly specified at the program level.               "]
        
        #keymap
        cfg['tool'][stage]['keymap'] = {}
        cfg['tool'][stage]['keymap']['switch'] = '-tool_keymap'
        cfg['tool'][stage]['keymap']['switch_args'] = '<>'
        cfg['tool'][stage]['keymap']['type'] = ['string', 'string']
        cfg['tool'][stage]['keymap']['requirmenet'] = 'optional'
        cfg['tool'][stage]['keymap']['defvalue'] = []
        cfg['tool'][stage]['keymap']['short_help'] = 'Script Keymap'
        cfg['tool'][stage]['keymap']['help'] = [
            "The keymap is used to performs a key to key translation  ",
            "within the writcfg step before a configuration is written",
            "out to a json, tcl, or yaml file to be used to drive the ",
            "stage execution flow. In cases where there is a one to   ",
            "one correlation between the features of the sc_cfg and   ",
            "the tool configuration, this keymap can be used to avoid ",
            "the need for stub scripts that translate the sc_cfg to   ",
            "the native eda tool reference flow scripts               "]
        
        #vendor
        cfg['tool'][stage]['vendor'] = {}
        cfg['tool'][stage]['vendor']['switch'] = '-tool_vendor'
        cfg['tool'][stage]['vendor']['switch_args'] = '<>'   
        cfg['tool'][stage]['vendor']['type'] = ['string']
        cfg['tool'][stage]['vendor']['requirement'] = ['all']
        cfg['tool'][stage]['vendor']['defvalue'] = []
        cfg['tool'][stage]['vendor']['short_help'] = 'Tool Vendor'
        cfg['tool'][stage]['vendor']['help'] = [
            "The vendor argument is used for selecting eda specific   ",
            "technology setup varaibales from the PDK and libraries   ",
            "which generallly support multiple vendors for each       ",
            "implementation stage                                     "]
        
    return cfg

############################################
# Run-time Options
#############################################

def schema_options(cfg):
    ''' Run-time options
    '''

    cfg['env'] = {
        'switch' : '-env',
        'switch_args' : '<>',
        'type' : ['string', 'string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Vendor Environment Variables',
        'help' : ["EDA tools and reference flows often require environment  ",
                  "variables to be set. These variables can be manageed     ",
                  "externally or passed in through this variable.           "],
    }

    cfg['cfgfile'] = {        
        'switch' : '-cfgfile',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Compiler Configuration File',
        'help' : ["All parameters can be set at the command line, but with  ",
                  "over 100 comfiguration parameters available in SC, the   ",
                  "preferred method for non trivial use cases is to create  ",
                  "a cfg file using the SC python API. The cfg file can be  ",
                  "passed in throught he -cfgfile switch at the commmand    ",
                  "There is no restruction on the number of cfgfiles that   ",
                  "can be passed in. Parameters in the cfgfile are appended ",
                  "to the existing list. In cases where a single entry is   ",
                  "expected such as in the case of <design> the last entered",
                  "value is used                                            "]
    }

    cfg['lock'] = {
        'switch' : '-lock',
        'switch_args' : '',
        'type' : ['bool'],
        'requirement' : 'optional',
        'defvalue' : ['False'],
        'short_help' : 'Configuration File Lock',
        'help' : ["The lock switch can be used to prevent unintented        ",
                  "updates to the chip configuration. For example, a team   ",
                  "might converge on a golden reference methodology and will",
                  "have a company policy to not allow designers to deviate  ",
                  "from that golden reference. After the lock switch has    ",
                  "been set, the configuration is in read only mode until   ",
                  "the end of the program"]
    }

    cfg['quiet'] = {
        'short_help' : 'Quiet Execution Option',
        'switch' : '-quiet',
        'switch_args' : '',
        'type' : ['bool'],
        'requirement' : 'optional',
        'defvalue' : ['False'],
        'short_help' : 'Supresses informational printing',
        'help' : ["By default, the sc will log extensive info to the display",
                  "This can be turned off using the -quiet param. Warnings  ",
                  "and errors are always logged."]
    }
    
    cfg['debug'] = {
        'switch' : '-debug',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : ['INFO'],
        'short_help' : 'Debug Level',
        'help' : ["The debug param provides explicit control over the level ",
                  "of debug information printed. Valid entries include      ",
                  "INFO, DEBUG, WARNING, ERROR                              "]
    }

    cfg['build'] = {
        'switch' : '-build',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : ['build'],
        'short_help' : 'Build Directory Name',
        'help' : ["By default, the flow is completed in the local directory ",
                  "named \'build\'. To change the name of the build dir     ",
                  "the user can specify an alternate directory path.        "]
    }

    cfg['start'] = {
        'switch' : '-start',
        'switch_args' : '<stage>',
        'type' : 'string',
        'requirement' : ['all'],
        'defvalue' : ['import'],
        'short_help' : 'Compilation Start Stage',
        'help' : ["The start parameter specifies the starting stage of the  ",
                  "flow. This would generally be the import stage but could ",
                  "be any one of the stages within the stages parameter. For",
                  "example, if a previous job was stopped at syn a job can  ",
                  "be continued from that point by specifying -start place  "]
    }

    cfg['stop'] = {
        'switch' : '-stop',
        'switch_args' : '<stage>',
        'type' : ['string'],
        'defvalue' : ['export'],
        'requirement' : ['all'],
        'short_help' : 'Compilation Stop Stage',
        'help' : ["The stop parameter specifies the stopping stage of the   ",
                  "flow. The value entered is inclusive, so if for example  ",
                  "the -stop syn is entered, the flow stops after syn has   ",
                  "been completed.                                          "]
    }

    cfg['skip'] = {
        'switch' : '-skip',
        'switch_args' : '<stage>',
        'type' : ['string'],
        'defvalue' : [],
        'requirement' : 'optional',
        'short_help' : 'Compilation Skip Stages',
        'help' : ["In some older technologies it may be possible to skip    ",
                  "some of the stages in the flow. The skip variable lists  ",
                  "the stages to be skipped during execution                "]
    }

    cfg['msg_trigger'] = {
        'switch' : '-msg_trigger',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Message Trigger',
        'help' : ["A list of stages after which to messages a recipient.    ",
                  "For example if values of syn, place, cts are entered     ",
                  "separate messages would be sent after the completion of  ",
                  "the syn, place, and cts stages.                          "]
    }

    cfg['msg_contact'] = {
        'switch' : '-msg_contact',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Message Contact Information',
        'help' : ["A list of phone numbers or email addreses to message on  ",
                  "a trigger event within the msg_trigger param.            "]
    }

    return cfg

############################################
# RTL Import Setup
#############################################

def schema_rtl(cfg):
    ''' Design setup
    '''

    cfg['source'] = {
        'switch' : 'None',
        'type' : ['file'],
        'requirement' : ['all'],
        'defvalue' : [],        
        'hash'   : [],
        'short_help' : 'Source files',
        'help' : ["A list of souroce files to read in for ellaboration. The ",
                  "files are read in order from first to last entered. File ",
                  "type is inferred from the file suffix:                   ",
                  "(*.v, *.vh) = verilog                                    ",
                  "(*.sv) = systemverilog                                   ",
                  "(*.vhd) = vhdl                                           "]
    }
        
    cfg['design'] = {
        'switch' : '-design',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Top Module name',
        'help' : ["The top level design name to synthesize. Required in all ",
                  "non-trivial designs with more than one source module     ",
                  "specified.                                               "]
    }

    cfg['nickname'] = {
        'switch' : '-nickname',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Nickname',
        'help' : ["An alias for the top level design name. Can be useful in ",
                  "for top level designs with long and confusing names. The ",
                  "nickname is used in all file prefixes.                   "]
        }
    
    
    cfg['clk'] = {
        'switch' : '-clk',
        'switch_args' : '<>',
        'type' : ['string', "string", 'float', 'float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Clock Defintion',
        'help' : ["A complete clock definition specifying the name of the   ",
                  "clock, the name of the clock port, or the full hierachy  ",
                  "path to the generated internal clock, the clock frequency",
                  "and the clock uncertainty (jitter). The definition can be",
                  "used to drive constraints for implementation and signoff."]
    }

    cfg['supply'] = {
        'switch' : '-supply',
        'switch_args' : '<>',
        'type' : ['string', 'string', 'float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Power Supply',
        'help' : ["A complete power supply definition specifying the supply ",
                  "name, t he power name, and the voltage.The definition can",
                  "be used to drive constraints for implementation and      ",
                  "signoff.                                                 "]
    }
    
    cfg['define'] = {
        'switch' : '-D',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Verilog Preprocessor Define Symbols',
        'help' : ["Sets a preprocessor symbol for verilog source imports.   "]
    }
    
    cfg['ydir'] = {
        'switch' : '-y',
        'switch_args' : '<dir>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Verilog Module Search Directory',
        'help' : ["Provides a search paths to look for modules found in the",
                  "the source list. The import engine will look for modules",
                  "inside files with the specified +libext+ param suffix   "]
    }

    cfg['idir'] = {
        'switch' : '-I',
        'switch_args' : '<dir>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Verilog Include File Search Directory',
        'help' : ["Provides a search paths to look for files included in   ",
                  "the design using the `include statement.                "]

    }

    cfg['vlib'] = {
        'switch' : '-v',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Verilog Library file',
        'help' : ["Declares a source code file where modules are not       ",
                  "interpreted as root modules                             "]
    }

    cfg['libext'] = {
        'switch' : '+libext',
        'switch_args' : '<ext>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Verilog Module Search File Extension',
        'help' : ["Specify the file extensions that should be used for     ",
                  "finding modules. For example, if -y is specified as     ",
                  "/home/$USER/mylib and '.v' is specified as libext       ",
                  "then all the files /home/$USER/mylib/*.v will be added  ",
                  "to the module search                                    "]
    }

    cfg['cmdfile'] = {
        'switch' : '-f',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Verilog Command Line Options File',
        'help' : ["Read the specified file, and act as if all text inside  ",
                  "it was specified as command line parameters. Supported  ",
                  "by most simulators including Icarus and Verilator       "]
    }

    return cfg

###########################
# Floorplan Setup
###########################

def schema_floorplan(cfg):

    cfg['stackup'] = {
        'switch' : '-stackup',
        'switch_args' : '<>',        
        'type' : ['string'],
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'Design Metal Stackup',
        'help' : ["Specifies the target stackup to use in the design. The  ",
                  "name must match a value defined in the pdk_stackup      ",
                  "exactly.                                                "]
    }
    
    # 1. Automatic floorplanning
    cfg['density'] = {
        'switch' : '-density',
        'switch_args' : '<num>',
        'type' : ['int'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Target Core Density',
        'help' : ["Provides a target density based on the total design cell",
                  "area reported after synthesis. This number is used when ",
                  "no diesize or floorplan is supplied. Any number between ",
                  "1 and 100 is legal, but values above 50 may fail due to ",
                  "area/congestion issues during apr.                      "]
    }

    cfg['coremargin'] = {
        'switch' : '-coremargin',
        'switch_args' : '<num>',
        'type' : ['float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Place and Route Core Margin',        
        'help' : ["Sets the halo/margin between the apr core cell area to  ",
                  "use for automated floorplaning setup. The value is      ",
                  "specified in microns and is only used when no diesize or",
                  "floorplan is supplied                                   "]
    }

    cfg['aspectratio'] = {
        'switch' : '-aspecratio',
        'switch_args' : '<num>',
        'type' : ['float'],
        'requirement' : 'optional',
        'defvalue' : ['1'],
        'short_help' : 'Design Layout Aspect Ratio',
        'help' : ["The aspect ratio to use for automated floor-planning and",
                  "specifes the height to width ratio of the block. Values ",
                  "below 0.1 and above 10 shuld be avoided as they will    ",
                  "likekly fail to converd during apr. The ideal aspect    ",
                  "ratio for the vast majhority of designs is 1.           "]
    }

    # 2. Spec driven floorplanning    
    cfg['diesize'] = {
        'switch' : '-diesize',
        'switch_args' : '<>',
        'type' : ['float', 'float', 'float', 'float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Target Die Size',
        'help' : ["Provides the outer boundary of the physical design. The ",
                  "number is provded as a tuple (x0 y0 x1 y1), where x0,y0 ",
                  "species the lower left corner of the block and x1,y1    ",
                  "specifies the upper right corner of. Only rectangular   ",
                  "blocks are supported with the diesize parameter. All    ",
                  "values are specified in microns.                        "]
    }

    cfg['coresize'] = {
        'switch' : '-coresize',
        'switch_args' : '<>',
        'type' : ['float', 'float', 'float', 'float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Target Core Size',
        'help' : ["Provides the core cell boundary for place and route.The ",
                  "number is provded as a tuple (x0 y0 x1 y1), where x0,y0 ",
                  "species the lower left corner of the block and x1,y1    ",
                  "specifies the upper right corner of. Only rectangular   ",
                  "blocks are supported with the diesize parameter. All    ",
                  "values are specified in microns.                        "]
    }
    
    # 3. Parametrized floorplanning
    cfg['floorplan'] = {
        'switch' : '-floorplan',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Floorplaning Script',
        'help' : ["Provides a parametrized floorplan to be used during the ",
                  "floorplan to create a fixed DEF file for placement.     ",
                  "Files with a .py suffix are processed by the sc, while  ",
                  "all other fils are passed through to the floorplanning  ",
                  "tool as is.                                             "]
    }
    
    # #4. Hard coded DEF
    cfg['def'] = {
        'switch' : '-def',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'DEF Floorplan',
        'help' : ["Provides a hard coded DEF file that takes the place of  ",
                  "the floorplanning stage. The DEF file should be complete",
                  "and have all the features needed to enable cell         ",
                  "placement"]
    }
    
    return cfg

###########################
# APR Setup
###########################
def schema_apr(cfg):
    ''' Physical design parameters
    '''
    
    cfg['target'] = {
        'switch' : '-target',
        'switch_args' : '<str>',        
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Target compilation platform',
        'help' : ["Provides a string name for choosing a physical mapping  ",
                  "target for the design. Like in compilers like gcc, only ",
                  "targets that are pre-baked into the compiler suppored.  ",
                  "Custom targets can be configured through a combination  ",
                  "of command line switches and config files. The target   ",                  
                  "parameter is included for conveneince, enabling cool    ",
                  "single line commands like sc -target asap hello_world.v ",
                  "Specifying the target parameter causes a number of PDK  ",
                  "PDK and library variables to be set automatically set   ",
                  "based ont he specific target specified.                 ",                 
                  "The targets currently supported are:                    ",
                  "asap7: A virtual PDK for 7nm with apr support           ",
                  "[More...](//http://asap.asu.edu/asap/                   ",
                  "freepdk45: A virtual PDK for 45nm with apr support      ",
                  "[More...](https://github.com/cornell-brg/freepdk-45nm   "]
    }
    
    cfg['target_lib'] = {
        'switch' : '-target_lib',
        'switch_args' : '<str>',        
        'type' : ['string'],
        'defvalue' : [],
        'requirement' : 'apr',
        'short_help' : 'Target Library',
        'help' : ["Provides a list of library names to use for synthesis   ",
                  "and automated place and route.                          "]
    }

    cfg['libarch'] = {
        'switch' : '-libarch',
        'switch_args' : '<str>',        
        'type' : ['string'],
        'defvalue' : [],
        'requirement' : 'apr',
        'short_help' : 'Target Library Architecture',
        'help' : ["Specifies the target library architecture to use. The   ",
                  "name is used to identify the technology file for must   ",
                  "match the pdk name and library name exactly.            "]
    }

    cfg['delaymodel'] = {
        'switch' : '-delaymodel',
        'switch_args' : '<str>',        
        'type' : ['string'],
        'defvalue' : [],
        'requirement' : 'apr',
        'short_help' : 'Target Library Delay Model',
        'help' : ["Specifies the delay model to use for the target libs.   ",
                  "Supported values are nldm and ccs.                      "]
    }

    # custom pass through variables
    cfg['custom'] = {
        'switch' : '-custom',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Custom EDA Pass-through Parameters',
        'help' : ["Specifies a custom variable to pass through directly to ",
                  "the EDA run scripts. The value is a space separated     ",
                  "string with the first value indicating the varibale.    ",
                  "For example -custom MYMODE 2 would result in tcl code   ",
                  "being generated as \'set MYMODE 2\'                     "]
    }

    #optimization priority
    cfg['effort'] = {
        'switch' : '-effort',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : ['high'],
        'short_help' : 'Compilation Effort',
        'help' : ["Specifies the effort for the synthesis and place and    ",
                  "route efforts. Supported values are low, medium , high. "]
    }

    cfg['priority'] = {
        'switch' : '-priority',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : ['timing'],
        'short_help' : 'Optimization Priority',
        'help' : ["An optional parameter for tools that support tiered     ",
                  "optimization functions. For example, congestion might   ",
                  "be assigned higher priority than timing in some stages. ",
                  "The optimization priority string must matcht the EDA    ",
                  "value exactly.                                          "]
    }
    #routing options
    cfg['ndr'] = {
        'switch' : '-ndr',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Non-default Net Routing File',
        'help' : ["A file containing a list of nets with non-default width ",
                  "and spacing, with one net per line and no wildcards     ",
                  "The formaat is <netname width space>                    ",
                  "The netname should include the full herarhcy from the   ",
                  "root module while width space should be specified in the",
                  "resolution specified in the technology file.            "]
    }
 
    cfg['minlayer'] = {
        'switch' : '-minlayer',
        'switch_args' : '<num>',
        'type' : ['int'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Minimum routing layer',
        'help' :  ["The minimum layer to be used for automated place and   ",
                  "route. The layer can be supplied as an integer with 1   ",
                  "specifying the first routing layer in apr_techfile.     "]
    }

    cfg['maxlayer'] = {
        'switch' : '-maxlayer',
        'switch_args' : '<num>',
        'type' : ['int'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Maximum Routing Layer',
        'help' : ["The maximum layer to be used for automated place and    ",
                  "route. The layer can be supplied as an integer with 1   ",
                  "specifying the first routing layer in apr_techfile.     "]
    }
    
    cfg['maxfanout'] = {
        'switch' : '-maxfanout',
        'switch_args' : '<num>',
        'type' : ['int'],
        'requirement' : 'apr',
        'defvalue' : ['64'],
        'short_help' : 'Maximum fanout',
        'help' : ["A max fanout rule to be applied during synthesis and apr",
                  "The value has a default of 64.                          "]
    }
   


    #power
    cfg['vcd'] = {
        'switch' : '-vcd',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Value Change Dump File',
        'help' : ["A digital simulation trace that can be used to model   ",
                  "the peak and average power consumption of a design.    "]
    }

    cfg['saif'] = {
        'switch' : '-saif',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Switching activity File',
        'help' : ["A simulat trace containing the toggle counts that can  ",
                  "be used for coarse statisttical power estimation.      "]
    }
    
    return cfg
    
############################################
# Constraints
#############################################   

def schema_constraints(cfg):

    cfg['mcmm_cornerlist'] = {
        'switch' : '-mcmm_cornerlist',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM Library Corner List',
        'help' : ["A complete list of the corners supported by the library",
                  "The list would include all combinations of process,    ",
                  "voltage, and temperature which have nldm views         "]
    }

    cfg['mcmm_pexlist'] = {
        'switch' : '-mcmm_pexlist',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM PEX Corner List',
        'help' : ["A complete list of the pex corners supported by the PDK"]
        
    }

    cfg['mcmm_scenario'] = {}
    cfg['mcmm_scenario']['default'] = {}
    
    cfg['mcmm_scenario']['default']['libcorner'] = {
        'switch' : '-mcmm_libcorner',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM Library Corner Name',
        'help' : ["Provides the exact libcorner name for accessing the  ",
                  "target timing views needed for mcmm                  "]
    }

    cfg['mcmm_scenario']['default']['pexcorner'] = {
        'switch' : '-mcmm_pexcorner',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM PEX Corner Name',
        'help' : ["Provides the exact pexcorner name for the accessing  ",
                  "the pdk_pexmodel                                     "]
    }
    
    cfg['mcmm_scenario']['default']['mode'] = {
        'switch' : '-mcmm_mode',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM Mode Name',
        'help' : ["Provides the exact pexcorner name for the accessing  ",
                  "the pdk_pexmodel                                     "]
    }
    cfg['mcmm_constr'] = {}
    cfg['mcmm_constr']['default'] = {}
    cfg['mcmm_constr']['default']['default'] = {
        'switch' : '-mcmm_constr',
        'switch_args' : '<>',
        'type' : ['file'],
        'requirement' : 'optional',
        'hash' : [],
        'defvalue' : [],
        'short_help' : 'MCMM Constraints File',        
        'help' : ["Provides scenario specific constraints. If none are  ",
                  "supplied default constraints are generated based on  ",
                  "the clk parameter. The constraints can be applied on ",
                  "per stage basis to allow for tighetening margins as  ",
                  "the design getes more refined throught he apr flow   "]
        }

    cfg['mcmm_goals'] = {}
    cfg['mcmm_goals']['default'] = {}
    cfg['mcmm_goals']['default']['default'] = {
        'switch' : '-mcmm_goals',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM Goals',
        'help' : ["Provides taget goals for a scenario on a per stage   ",
                  "basis. Valid goals must align with the syn and apr   ",
                  "apr tools, but generally include setup, hold, power. ",
                  "Per stage goals is supported to emable skipping of   ",
                  "certain goals like until the deisgn has the necessary",
                  "steps done, for example deferring the hold fix       ",
                  "objective until after cts.                           "]
    }

    return cfg

###############################################
# Network Configuration for Remote Compute Jobs
###############################################

def schema_net(cfg):

    # Remote IP address/hostname running sc-server app
    cfg['remote'] = {
        'short_help' : 'Remote server (https://acme.com:8080)',
        'switch': '-remote',
        'switch_args' : '<str>',
        'type' : ['string'],
        'defvalue' : [],
        'help' : ["TBD"]
    }

    # Port number that the remote host is running 'sc-server' on.
    cfg['remoteport'] = {
        'short_help': 'Port number used by sc-server.',
        'switch': '-remote_port',
        'switch_args' : '<num>',
        'type' : ['int'],
        'defvalue' : ['8080'],
        'help' : ["TBD"]
    }

    # NFS config: Username to use when copying file to remote compute storage.
    cfg['nfsuser'] = {
        'short_help': 'Remote server user name.',
        'switch': '-nfs_user',
        'switch_args' : '<str>',
        'type' : ['string'],
        'defvalue' : ['ubuntu'],
        'help' : ["TBD"]
    }

    # NFS config: Hostname to use for accessing shared remote compute storage.
    cfg['nfshost'] = {
        'short_help': 'Hostname or IP address for shared storate.',
        'switch': '-nfs_host',
        'switch_args' : '<str>',
        'type' : ['string'],
        'defvalue' : [],
        'help' : ["TBD"]
    }

    # NFS config: root filepath for shared NFS storage on the remote NFS host.
    cfg['nfsmount'] = {
        'short_help': 'Directory of mounted shared NFS storage.',
        'switch': '-nfs_mount',
        'switch_args' : '<str>',
        'type' : ['string'],
        'defvalue' : ['/nfs/sc_compute'],
        'help' : ["TBD"]
    }

    # NFS config: path to the SSH key file which will be used to access
    # the remote storage host.
    cfg['nfskey'] = {
        'short_help': 'Key-file used for remote connection.',
        'switch': '-nfs_key',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'help' : ["TBD"]
    }

    return cfg

###############################################
# Configuration schema for `sc-server`
###############################################

def server_schema():
    '''Method for defining Server configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    cfg = {}

    cfg['port'] = {
        'short_help': 'Port number to run the server on.',
        'switch': '-port',
        'switch_args': '<num>',
        'type': ['int'],
        'defvalue': ['8080'],
        'help' : ["TBD"]
    }

    cfg['nfsuser'] = {
        'short_help': 'Username on remote storage host.',
        'switch': '-nfs_user',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue': ['ubuntu'],
        'help' : ["TBD"]
    }

    cfg['nfshost'] = {
        'short_help': 'Hostname or IP address for shared storage.',
        'switch': '-nfs_host',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue' : [],
        'help' : ["TBD"]
    }

    cfg['nfsmount'] = {
        'short_help': 'Directory of mounted shared NFS storage.',
        'switch': '-nfs_mount',
        'switch_args': '<str>',
        'type': ['string'],
        'defvalue' : ['/nfs/sc_compute'],
        'help' : ["TBD"]
    }

    cfg['nfskey'] = {
        'short_help': 'Key-file used for remote connection.',
        'switch': '-nfs_key',
        'switch_args': '<file>',
        'type': ['file'],
        'defvalue' : [],
        'help' : ["TBD"]
    }

    return cfg
