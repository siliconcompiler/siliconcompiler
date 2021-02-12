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
        'short_help' : 'FPGA architecture description file (xml)',
        'help' : ["The file provides XML-based architecture description for ",
                  "the target FPGA architecture to be used in VTR allowing  ",
                  "the user to describe a large number of hypothetical and  ",
                  "commercial architectures.                                ",
                  "[More information...](https://verilogtorouting.org)      "],
        'switch' : '-fpga_xml',
        'switch_args' : '<target file>',
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
        'short_help' : 'Foundry name',
        'help' : ["The name of the foundry. Example values include: tsmc,  ",
                  "gf, samsung, intel, skywater, virtual. The virtual      ",
                  "keyword is reserved for simulated processes that can't  ",
                  "like nangate45 and asap7.                               "],
        'switch' : '-pdk_foundry',
        'switch_args' : '<string>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['pdk_process'] = {
        'short_help' : 'Process name',
        'help' : ["The official name of the process within a foundry. The   ",
                  "name is case insensitive, but should otherwise match the ",
                  "complete public process name from the foundry. Examples  ",
                  "process names include 22FFL from Intel, 12LPPLUS from    ",
                  "Globalfoundries, and 16FFC from TSMC.                    "],
        'switch' : '-pdk_process',
        'switch_args' : '<string>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['pdk_node'] = {
        'short_help' : 'Process node (in nm)',
        'help' : ["An approximation of the relative minimum dimension       ",
                  "of the process node. Not a required parameter but may be ",
                  "used to select technology dependant synthesis and place  ",
                  "and route optimization algorithms and recipes. Examples  ",
                  "of nodes include 180nm, 130nm, 90nm, 65nm, 45m,32nm, 22nm",
                  "15nm, 10nm, 7nm, 5nm                                     "],
        'switch' : '-pdk_node',
        'switch_args' : '<int>',
        'requirement' : 'asic',
        'type' : ['int'],
        'defvalue' : []
    }

    cfg['pdk_version'] = {
        'short_help' : 'Process node version',
        'help' : ["The PDK version is an alphanumeric string provided by to ",
                  "track changes in critical process design kit data shipped",
                  "to foundry customers. Designers should manually or       ",
                  "automatically verify that the PDK version is approved    ",
                  "for new tapeouts.                                        "],
        'switch' : '-pdk_version',
        'switch_args' : '<string>',
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
                  "in the pdk_pexmodel and pdk_pnrtech variables.           "],
        'switch' : '-pdk_stackup',
        'switch_args' : '<name>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['pdk_devicemodel'] = {}
    cfg['pdk_devicemodel']['default'] = {}
    cfg['pdk_devicemodel']['default']['default'] = {}
    cfg['pdk_devicemodel']['default']['default']['default'] = {
        'short_help' : 'Device model directory',
        'help' : ["A dynamic structure of paths to various device models.   ",
                  "The structure serves as a central access registry for    ",
                  "models for different purpose and vendors. The nested     ",
                  "dictionary order is [stackup][type][vendor]. For models  ",
                  "that span all metal stackups, the model directory        ",
                  "pointer can be trivially duplicated using a python for   ",
                  "loop in the PDK setup file. Examples of model types      ",
                  "include spice, aging, electromigration, radiation        "],
        'switch' : '-pdk_devicemodel',
        'switch_args' : '<stackup type vendor file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_pexmodel'] = {}
    cfg['pdk_pexmodel']['default'] = {}
    cfg['pdk_pexmodel']['default']['default']= {}
    cfg['pdk_pexmodel']['default']['default']['default'] = {
        'short_help' : 'Back end PEX TCAD model',
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
        'switch_args' : '<stackup corner vendor file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_layermap'] = {}
    cfg['pdk_layermap']['default'] = {}
    cfg['pdk_layermap']['default']['default'] = {}
    cfg['pdk_layermap']['default']['default']['streamout'] = {
        'short_help' : 'Layout streamout layermap',
        'help' : ["This structure contains pointers to the various layer    ",
                  "mapping files needed to stream data out from binary      ",
                  "databases to tapeout read GDSII datbases. The layer map  ",
                  "supplied in the PDK on a per stackup basis and the       ",
                  "nested dictionary order is [stackup][tool][streamout].   "],
        'switch' : '-pdk_layermap_streamout',
        'switch_args' : '<stackup tool file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['pdk_layermap']['default']['default']['streamin'] = {
        'short_help' : 'Layout streamin layermap',
        'help' : ["This structure contains pointers to the various layer    ",
                  "mapping files needed to stream data into binary          ",
                  "databases. The layer map supplied in the PDK on a per    ",
                  "stackup basis and the nested dictionary order is         ",
                  "[stackup][tool][streamout].                              "],
        'switch' : '-pdk_layermap_streamin',
        'switch_args' : '<stackup tool file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    
    cfg['pdk_display'] = {}
    cfg['pdk_display']['default'] = {}
    cfg['pdk_display']['default']['default'] = {
        'short_help' : 'Custom design display configuration',
        'help' : ["This structure contains a display configuration file     ",
                  "for colors and pattern schemes for all layers in the     ",
                  "PDK. The layer map supplied in the PDK on a per          ",
                  "stackup basis and the nested dictionary order is         ",
                  "[stackup][tool].                                         "],
        'switch' : '-pdk_display',
        'switch_args' : '<stackup tool file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['pdk_clib'] = {}
    cfg['pdk_clib']['default'] = {}
    cfg['pdk_clib']['default']['default'] = {
        'short_help' : 'Custom design library',
        'help' : ["A file containing pointers to all custom cell libs.      ",
                  "Examples include pcell libraries and pycell libs         ",
                  "The file is supplied in the PDK on a per stackup basis   ",
                  "and the nested dictionary order is [stackup][tool].      "],
        'switch' : '-pdk_clib',
        'switch_args' : '<stackup vendor file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    
    # Place and Route
    cfg['pdk_pnrtech'] = {}
    cfg['pdk_pnrtech']['default'] = {}
    cfg['pdk_pnrtech']['default']['default'] = {}
    cfg['pdk_pnrtech']['default']['default']['default'] = {
        'short_help' : 'Place and route tehnology file',
        'help' : ["Technology file for place and route tools. The file      ",
                  "contains the necessary information needed to create DRC  ",
                  "compliant automatically routed designs. The file is      ",
                  "vendor specific with the most commonf format being LEF.  ",
                  "The nested dictionary order is [stackup][libarch][tool], ",
                  "where libarch stands for the library type, generally the ",
                  "library height. For example a node might support 6 track,",
                  "7.5 track and 9 track high libraries with libarch names  ",
                  "of 6T, 7.5T, 9T                                          "],
        'switch' : '-pdk_pnrtech',
        'switch_args' : '<stackup lib vendor file>',
        'requirement' : 'apr',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_pnrdir'] = {}
    cfg['pdk_pnrdir']['default'] = {}
    cfg['pdk_pnrdir']['default']['default'] = {}
    cfg['pdk_pnrdir']['default']['default']['default'] = {
        'short_help' : 'Place and route tool setup directory ',
        'help' : ["Directory containing various setup files for place and   ",
                  "route tools. These files are avaialble in the PDK  on a  ",
                  "per tool and per stackup basis. The directory pointer    ",
                  "is not required by all tools. when provided, the nested  ",
                  "dictionary order is [stackup][libarch][tool], where      ",
                  "libarch stands for the library type, generally the       ",
                  "library height. For example a node might support 6       ",
                  "track, 7.5 track and 9 track high libraries with         ",
                  "libarch names of 6T, 7.5T, 9T                            "],
        'switch' : '-pdk_pnrdir',
        'switch_args' : '<stackup libarch tool file>', 
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    
    cfg['pdk_pnrlayer'] = {}
    cfg['pdk_pnrlayer']['default'] = {
        'short_help' : 'Place and route routing layer definitions',
        'help' : ["In experimental settings and for immature PDKs there may ",
                  "be a need to override the design rules defined int he    ",
                  "pdk_pnrtech file. This should be done using using        ",
                  "pdk_pnrlayer.The layer definition is given as a tuple on ",
                  "a per stackup basis. An hypothetical example of a valid  ",
                  "layer definition would be metal1 X 0.5 1.0 for defining  ",
                  "metal1 as a horizontal routing layer with a 0.5um width  ",
                  "and 1.0um pitch grid.                                    "],
        'switch' : '-pdk_pnrlayer',
        'switch_args' : '<stackup layername X|Y width pitch>',
        'requirement' : 'optional',
        'type' : ['string', 'string', 'float', 'float'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['pdk_tapmax'] = {
        'short_help' : 'Tap cell max distance rule',
        'help' : ["Sets the maximum distance between tap cells for the place",
                  "and route tool. This value is derived from the design    ",
                  "rule manual and the methodology guides within the PDK.   "],
        'switch' : '-pdk_tapmax',
        'switch_args' : '<float>',
        'requirement' : 'apr',
        'type' : ['float'],
        'defvalue' : [],
        'hash' : []
    }

    cfg['pdk_tapoffset'] = {
        'short_help' : 'Tap cell offset rule',
        'help' : ["Sets the offset from the edge of the block to place a tap",
                  "cell for the place route tool. This value is derived from",
                  "the design rule manual and the methodology guides within ",
                  "the PDK.                                                 "],
        'switch' : '-pdk_tapoffset',
        'switch_args' : '<float>',
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

    cfg[''+group] = {}  

    cfg[''+group]['default'] = {}
    
    # Version #
    cfg[''+group]['default']['version'] = {
        'short_help' : 'Library release version',
        'help' : ["The library version is an alphanumeric string provided by",
                  "the vendor to track changes in critical library data     ",
                  "shipped to the library customer. Designers should        ",
                  "manually or automatically verify that the library version",
                  "is approved for tapeout                                  "],
        'switch' : '-'+group+'_version',
        'switch_args' : '<lib version>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : []
    }

    # Userguide
    cfg[''+group]['default']['userguide'] = {
        'short_help' : 'Library userguide',
        'help' : ["The main documentation guide outlining how to use the IP ",
                  "successfully in ASIC design. If more than one document is",
                  "provided, the list should be ordered from most to least  ",
                  "important.                                               "],
        'switch' : '-'+group+'_userguide',
        'switch_args' : '<lib file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    # Datasheets
    cfg[''+group]['default']['datasheet'] = {
        'short_help' : 'Library datasheets',
        'help' : ["A complete collection of datasheets for the library. The ",
                  "documentation can be provided as a single collated PDF or",
                  "as one HTML file per cell                                "],
        'switch' : '-'+group+'_datasheet',
        'switch_args' : '<lib path>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg[''+group]['default']['libarch'] = {
        'short_help' : 'Library architecture',
        'help' : ["A name/tag used to identify the library type for place   ",
                  "and route technology setup. Libarch must match up with   ",
                  "the name used in the pdk_pnrtech structure. The libarch  ",
                  "is a unique a string that identifies the library height  ",
                  "or performance class of the library. Mixing of libarchs  ",
                  "in a flat place and route block is not allowed.          "],
        'switch' : '-'+group+'_libarch',
        'switch_args' : '<lib libarch>',
        'requirement' : 'apr',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg[''+group]['default']['libheight'] = {
        'short_help' : 'Library height',
        'help' : ["The height of the library cells in (um). The value is    ",
                  "automatically extracted from the technology file from the",
                  "pdk_pnrtech structure.                                   "], 
        'switch' : '-'+group+'_libheight',
        'switch_args' : '<lib libheight>',
        'requirement' : 'apr',
        'type' : ['float'],
        'defvalue' : []
    }
    
    cfg[''+group]['default']['nldm'] = {}
    cfg[''+group]['default']['nldm']['default'] = {
        'short_help' : 'Library non-linear delay timing model',
        'help' : ["A non-linear delay model in the liberty format. The file ",
                  "specifies timinga and logic functions to mapt the design ",
                  "to. The structure order is [library]['nldm'][corner]. The",
                  "corner is used to define scenarios and must be the       ",
                  "same as those used int he mcmm_scenario structure.       "],
        'switch' : '-'+group+'_nldm',
        'switch_args' : '<lib corner file>',
        'requirement' : 'apr',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg[''+group]['default']['ccs'] = {}
    cfg[''+group]['default']['ccs']['default'] = {
        'short_help' : 'Library composite current source model',
        'help' : ["A composite current source model for the library. It is  ",
                  "is more accurate than the NLDM model and recommended at  ",
                  "advanced nodes, but is significantly larger than the nldm",
                  "model and should only be used when accuracy is an        ",
                  "absolute requirement. When available, ccs models should  ",
                  "always be used for signoff timing checks.                "],
        'switch' : '-'+group+'_ccs',
        'switch_args' : '<lib corner file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg[''+group]['default']['lef'] = {
        'short_help' : 'Library layout exchange file (LEF)',
        'help' : ["An abstracted view of library cells that gives complete  ",
                  "information about the cell place and route boundary, pin ",
                  "positions, pin metals, and metal routing blockages.      "],
        'switch' : '-'+group+'_lef',
        'switch_args' : '<lib file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
  
    cfg[''+group]['default']['gds'] = {
        'short_help' : 'Library GDS file',
        'help' : ["The complete mask layout of the library cells ready to be"
                  "merged with the rest of the design for tapeout. In some  "
                  "cases, the GDS merge happens at the foundry, so inclusion"
                  "of a GDS file is optional. In all cases, where the GDS   "
                  "files are available, they should specified here to enable"
                  "gds stream out/merge during the automated place and route"
                  "and chip assembly process.                               "],
        'switch' : '-'+group+'_gds',
        'switch_args' : '<lib file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg[''+group]['default']['cdl'] = {
        'short_help' : 'Library CDL netlist file',
        'help' : ["The CDL file contains the netlists use for layout versus ",
                  "schematic (LVS) checks. In some cases, the GDS merge     ",
                  "happens at the foundry, so inclusion of a CDL file is    ",
                  "optional. In all cases, where the CDL files are          ",
                  "available they should specified here to enable LVS checks",
                  "pre tapout                                               "],
        'switch' : '-'+group+'_cdl',
        'switch_args' : '<lib file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg[''+group]['default']['spice'] = {
        'short_help' : 'Library spice file',
        'help' : ["The spice file contains the netlists use for circuit     ",
                  "simulation.                                              "],
        'switch' : '-'+group+'_spice',
        'switch_args' : '<lib file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg[''+group]['default']['hdl'] = {
        'short_help' : 'Library high level description language file',
        'help' : ["A bit exact or high level verilog model for all cells in ",
                  "the library. The file can be VHDL (.vhd) or Verilog (.v) "],
        'switch' : '-'+group+'_hdl',
        'switch_args' : '<lib file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg[''+group]['default']['atpg'] = {
        'short_help' : 'Library ATPG file',
        'help' : ["Logical model used for ATPG based chip test methods.     "],
        'switch' : '-'+group+'_atpg',
        'switch_args' : '<lib file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg[''+group]['default']['pgmetal'] = {
        'short_help' : 'Library power rail metal layer',
        'help' : ["The variable specifies the top metal layer used for power",
                  "and ground routing. The parameter can be used to guide   ",
                  "standard cell power grid hookup within automated place   ",
                  "and route tools                                          "],
        'switch' : '-'+group+'_pgmetal',
        'switch_args' : '<lib metal-layer>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg[''+group]['default']['vt'] = {
        'short_help' : 'Library transistor threshold',
        'help' : ["The variable specifies the voltage threshold type of the ",
                  "library. The value is extracted automatically if found in",
                  "the default_threshold_voltage_group within the nldm      ",
                  "timing model. For older technologies with only one vt    ",
                  "group, it is recommended to set the value to rvt or svt  "],
        'switch' : '-'+group+'_vt',
        'switch_args' : '<lib vt-type>',
        'requirement' : 'apr',
        'type' : ['string'],
        'defvalue' : [],
        'hash'   : []
    } 

    cfg[''+group]['default']['tag'] = {
        'short_help' : 'Library indentifier tags',
        'help' : ["An arbitraty set of tags that can be used by the designer",
                  "or EDA tools for optimization purposes. The tags are     ",
                  "meant to cover features not currently supported by built ",
                  "in EDA optimization flows. Multiple tags per library is  ",
                  "supported.                                               "],
        'switch' : '-'+group+'_tag',
        'switch_args' : '<lib tag>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg[''+group]['default']['driver'] = {
        'short_help' : 'Library default driver cell',
        'help' : ["The name of a library cell to be used as the default     ",
                  "driver for block timing constraints. The cell should be  ",
                  "strong enough to drive a block input from another block  ",
                  "including wire capacitance. In cases, where the actual   ",
                  "drive is known, the actual driver cell should be used.   "],
        'switch' : '-'+group+'_driver',
        'switch_args' : '<lib name>',
        'requirement' : 'apr',
        'type' : ['string'],
        'defvalue' : []
    }

    #Dont use cell lists
    cfg[''+group]['default']['exclude'] = {}
    cfg[''+group]['default']['exclude']['default'] = {
        'short_help' : 'Library cell exclude lists',
        'help' : ["Lists of cells to exclude for specific stages within the ",
                  "an implementation flow. The structure of the dictionary  ",
                  "is ['exclude'][stage] = <list>.                          "],
        'switch' : '-'+group+'_exclude',
        'switch_args' : '<lib type stage>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }
    cfg[''+group]['default']['include'] = {}
    cfg[''+group]['default']['include']['default'] = {
        'short_help' : 'Library cell include lists',
        'help' : ["Lists of cells to include for specific stages within the ",
                  "an implementation flow. The structure of the dictionary  ",
                  "is ['include'][stage] = <list>.                          "],
        'switch' : '-'+group+'_include',
        'switch_args' : '<lib type stage>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : []
    }

    #Vendor specific config
    cfg[''+group]['default']['config'] = {}
    cfg[''+group]['default']['config']['default'] = {
        'short_help' : 'Library EDA setup file',
        'help' : ["A list of configuration files used to set up automated   ",
                  "place and route flows for specific EDA tools. The format ",
                  "of the variable is ['config']['tool'] = <filename>       "],
        'switch' : '-'+group+'_setup',
        'switch_args' : '<lib file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    } 
    
    #Vendor compiled databases
    cfg[''+group]['default']['nldmdb'] = {}
    cfg[''+group]['default']['nldmdb']['default'] = {}
    cfg[''+group]['default']['nldmdb']['default']['default'] = {
        'short_help' : 'Library NLDM compiled database',
        'help' : ["A binary compiled ndlm file for a specific EDA tool.     "],
        'switch' : '-'+group+'_nldmdb',
        'switch_args' : '<lib corner vendor file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }

    cfg[''+group]['default']['ccsdb'] = {}
    cfg[''+group]['default']['ccsdb']['default'] = {}
    cfg[''+group]['default']['ccsdb']['default']['default'] = {
        'short_help' : 'Library CCS compiled databse',
        'help' : ["A binary compiled ccs file for a specific EDA tool. The  ",
                  "dictionary format is ['ccsdb']['corner']['tool'] = <file>"],
        'switch' : '-'+group+'_ccsdb',
        'switch_args' : '<lib corner vendor file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : []
    }
    cfg[''+group]['default']['libdb'] = {}
    cfg[''+group]['default']['libdb']['default'] = {
        'short_help' : 'Library layout compiled database',
        'help' : ["A binary compiled library layout database for a specific ", 
                  "EDA tool. The dictionary format is:                      ",
                  "['libdb']['tool'] = <file>                               "],
        'switch' : '-'+group+'_libdb',
        'switch_args' : '<lib vendor file>',
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
        'short_help' : 'List of all compilation stages',
        'help' : ["A complete list of all stages included in fully automated",
                  "RTL to GDSII tapeout implementationa and verificatio flow",
                  "Stages can be added and skipped during flows, but not    ", 
                  "removed from the list as it would break the compiler.    "],
        'switch' : '-stages',
        'switch_args' : '<string>',
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
                      'gdsview',
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

    cfg['tool'] = {}
   
    # Defaults and config for all stages
    for stage in cfg['stages']['defvalue']:        
        cfg['tool'][stage] = {}
        for key in ('exe', 'opt', 'refdir', 'script', 'copy',
                    'format', 'jobid', 'np', 'keymap','vendor'):
            cfg['tool'][stage][key] = {}
            cfg['tool'][stage][key]['switch'] = '-tool_'+key
            
        # Short Help
        cfg['tool'][stage]['exe']['short_help'] = 'Stage executable'
        cfg['tool'][stage]['opt']['short_help'] = 'Stage executable options'
        cfg['tool'][stage]['refdir']['short_help'] = 'Stage reference flow dir'
        cfg['tool'][stage]['script']['short_help'] = 'Stage entry point script'
        cfg['tool'][stage]['copy']['short_help'] = 'Stage copy-to-local option'
        cfg['tool'][stage]['format']['short_help'] = 'Stage config format'
        cfg['tool'][stage]['jobid']['short_help'] = 'Stage job index'
        cfg['tool'][stage]['np']['short_help'] = 'Stage thread parallelism'
        cfg['tool'][stage]['keymap']['short_help'] = 'Stage keyword translation'
        cfg['tool'][stage]['vendor']['short_help'] = 'Stage tool vendor'

        # Long Help
        cfg['tool'][stage]['exe']['help'] = [
            "The name of the executable. Can be the full env path to  ",
            "the excutable or the simple name if the search path has  ",
            "already been set up in the working environment.          "]

        cfg['tool'][stage]['opt']['help'] = [
            "A list of command line options for the executable. For   ",
            "multiple argument options, enter each argument and value ",
            "as one list entry. Foe example, the argument pair        ",
            "-c 5 would be entered as one string \'-c 5\'             "]

        cfg['tool'][stage]['refdir']['help'] = [
            "The directory containing the reference scripts used in   ",
            "by the stage executable.                                 "]

        cfg['tool'][stage]['script']['help'] = [
            "The top level reference script to called by the stage    ",
            "executable                                               "]

        cfg['tool'][stage]['copy']['help'] = [
            "Specifes that the reference script directory shoulld be  ",
            "copied and run from the local run directory. This option ",
            "is set automatically set when the -remote option is set  "]
        
        cfg['tool'][stage]['format']['help'] = [
            "Specifes that format of the configuration file for the   ",
            "stage. Valid formats are tcl, yaml, and json. The format ",
            "used is dictated by the executable for the stage.        "]

        cfg['tool'][stage]['jobid']['help'] = [
            "A dynamic variable that keeeps track of results to pass  ",
            "foward to the next stage of the implementation pipeline  ",
            "in cases where multiple jobs are run for one stage and a ",
            "progrematic selection if made to choose the best result, ",
            "the variable is use to point to a job which may or may   ",
            "not be the last job launched"]
        
        cfg['tool'][stage]['keymap']['help'] = [
            "The keymap is used to performs a key to key translation  ",
            "within the writcfg step before a configuration is written",
            "out to a json, tcl, or yaml file to be used to drive the ",
            "stage execution flow. In cases where there is a one to   ",
            "one correlation between the features of the sc_cfg and   ",
            "the tool configuration, this keymap can be used to avoid ",
            "the need for stub scripts that translate the sc_cfg to   ",
            "the native eda tool reference flow scripts               "]

        cfg['tool'][stage]['vendor']['help'] = [
            "The vendor argument is used for selecting eda specific   ",
            "technology setup varaibales from the PDK and libraries   ",
            "which generallly support multiple vendors for each       ",
            "implementation stage                                     "]

        
        
        # Switch Args
        cfg['tool'][stage]['exe']['switch_args'] = '<stage string>'
        cfg['tool'][stage]['opt']['switch_args'] = '<stage string>'
        cfg['tool'][stage]['refdir']['switch_args'] = '<stage dir>'
        cfg['tool'][stage]['script']['switch_args'] = '<stage file>'
        cfg['tool'][stage]['copy']['switch_args'] = '<stage string>'
        cfg['tool'][stage]['format']['switch_args'] = '<stage string>'
        cfg['tool'][stage]['jobid']['switch_args'] = '<stage int>'
        cfg['tool'][stage]['np']['switch_args'] = '<stage int>'
        cfg['tool'][stage]['keymap']['switch_args'] = '<stage string string>'
        cfg['tool'][stage]['vendor']['switch_args'] = '<stage string>'        

        # Types
        cfg['tool'][stage]['exe']['type'] = ['string']
        cfg['tool'][stage]['opt']['type'] = ['string']
        cfg['tool'][stage]['refdir']['type'] = ['file']
        cfg['tool'][stage]['script']['type'] = ['file']
        cfg['tool'][stage]['copy']['type'] = ['string']
        cfg['tool'][stage]['format']['type'] = ['string']
        cfg['tool'][stage]['jobid']['type'] = ['int']
        cfg['tool'][stage]['np']['type'] = ['int']
        cfg['tool'][stage]['keymap']['type'] = ['string', 'string']
        cfg['tool'][stage]['vendor']['type'] = ['string']

        # Requirement
        cfg['tool'][stage]['exe']['requirement'] = ['all']
        cfg['tool'][stage]['opt']['requirement'] = ['optional']
        cfg['tool'][stage]['refdir']['requirement'] = ['optional']
        cfg['tool'][stage]['script']['requirement'] = ['optional']
        cfg['tool'][stage]['copy']['requirement'] = ['optional']
        cfg['tool'][stage]['format']['requirement'] = ['optional']
        cfg['tool'][stage]['jobid']['requirement'] = ['all']
        cfg['tool'][stage]['np']['requirement'] = ['all']
        cfg['tool'][stage]['keymap']['requirmenet'] = ['optional']
        cfg['tool'][stage]['vendor']['requirement'] = ['all']

        
        # Hash
        cfg['tool'][stage]['refdir']['hash'] = []
        cfg['tool'][stage]['script']['hash'] = []

        # Default value
        cfg['tool'][stage]['exe']['defvalue'] = []
        cfg['tool'][stage]['opt']['defvalue'] = []
        cfg['tool'][stage]['refdir']['defvalue'] = []
        cfg['tool'][stage]['script']['defvalue'] = []
        cfg['tool'][stage]['copy']['defvalue'] = []
        cfg['tool'][stage]['format']['defvalue'] = []
        cfg['tool'][stage]['np']['defvalue'] = []
        cfg['tool'][stage]['keymap']['defvalue'] = []
        cfg['tool'][stage]['vendor']['defvalue'] = []
        cfg['tool'][stage]['jobid']['defvalue'] = ['0']

    return cfg

############################################
# Run-time Options
#############################################

def schema_options(cfg):
    ''' Run-time options
    '''

    cfg['env'] = {
        'short_help' : 'Vendor specific environment variables to set',
        'switch' : '-env',
        'switch_args' : '<varname value>',
        'type' : ['string', 'string'],
        'defvalue' : []
    }

    cfg['cfgfile'] = {
        'short_help' : 'Loads configurations from a json file',
        'switch' : '-cfgfile',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['lock'] = {
        'short_help' : 'Locks the configuration dict from edit',
        'switch' : '-lock',
        'switch_args' : '',
        'type' : ['bool'],
        'defvalue' : ['False'],
    }

    cfg['quiet'] = {
        'short_help' : 'Supresses informational printing',
        'switch' : '-quiet',
        'switch_args' : '',
        'type' : ['bool'],
        'defvalue' : ['False'],
    }
    
    cfg['debug'] = {
        'short_help' : 'Debug level (INFO/DEBUG/WARNING/ERROR)',
        'switch' : '-debug',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['INFO']
    }

    cfg['build'] = {
        'short_help' : 'Name of build directory',
        'switch' : '-build',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['build']
    }

    cfg['start'] = {
        'short_help' : 'Compilation starting stage',
        'type' : 'string',
        'switch' : '-start',
        'switch_args' : '<stage>',
        'defvalue' : ['import']
    }

    cfg['stop'] = {
        'short_help' : 'Compilation ending stage',
        'switch' : '-stop',
        'switch_args' : '<stage>',
        'type' : ['string'],
        'defvalue' : ['export']
    }
    
    cfg['msg_trigger'] = {
        'short_help' : 'Trigger for messaging to <msg_contact>',
        'switch' : '-msg_trigger',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['msg_contact'] = {
        'short_help' : 'Trigger event contact (phone#/email)',
        'switch' : '-msg_contact',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    return cfg

############################################
# RTL Import Setup
#############################################

def schema_rtl(cfg):
    ''' Design setup
    '''

    cfg['source'] = {
        'short_help' : 'Source files (.v/.vh/.sv/.vhd)',
        'switch' : 'None',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
        
    cfg['design'] = {
        'short_help' : 'Design top module name',
        'switch' : '-design',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['nickname'] = {
        'short_help' : 'Design nickname',
        'switch' : '-nickname',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }
    
    cfg['clk'] = {
        'short_help' : 'Clock defintion',
        'switch' : '-clk',
        'switch_args' : '<name period uncertainty>',
        'type' : ['string', 'float', 'float'],
        'defvalue' : []
    }

    cfg['supply'] = {
        'short_help' : 'Power supply',
        'switch' : '-supply',
        'switch_args' : '<name pin voltage>',
        'type' : ['string', 'string', 'float'],
        'defvalue' : []
    }
    
    cfg['define'] = {
        'short_help' : 'Define variables for Verilog preprocessor',
        'switch' : '-D',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }
    
    cfg['ydir'] = {
        'short_help' : 'Directory to search for modules',
        'switch' : '-y',
        'switch_args' : '<dir>',
        'type' : ['string'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['idir'] = {
        'short_help' : 'Directory to search for includes',
        'switch' : '-I',
        'switch_args' : '<dir>',
        'type' : ['string'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['vlib'] = {
        'short_help' : 'Library file',
        'switch' : '-v',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['libext'] = {
        'short_help' : 'Extension for finding modules',
        'switch' : '+libext',
        'switch_args' : '<ext>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['readscript'] = {
        'short_help' : 'Source file read script',
        'switch' : '-f',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    return cfg


###########################
# Floorplan Setup
###########################

def schema_floorplan(cfg):


    # 1. Automatic floorplanning
    cfg['density'] = {
        'short_help' : 'Target core density (percent)',
        'switch' : '-density',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }

    cfg['coremargin'] = {
        'short_help' : 'Core place and route halo margin (um)',
        'switch' : '-coremargin',
        'switch_args' : '<float>',
        'type' : ['float'],
        'defvalue' : []
    }

    cfg['aspectratio'] = {
        'short_help' : 'Target aspect ratio',
        'switch' : '-aspectratio',
        'switch_args' : '<float>',
        'type' : ['float'],
        'defvalue' : []
    }

    # 2. Spec driven floorplanning    
    cfg['diesize'] = {
        'short_help' : 'Target die size (x0 y0 x1 y1) (um)',
        'switch' : '-diesize',
        'switch_args' : '<float float float float>',
        'type' : ['float', 'float', 'float', 'float'],
        'defvalue' : []
    }

    cfg['coresize'] = {
        'short_help' : 'Target core size (x0 y0 x1 y1) (um)',
        'switch' : '-coresize',
        'switch_args' : '<float float float float>',
        'type' : ['float', 'float', 'float', 'float'],
        'defvalue' : []
    }
    
    # 3. Parametrized floorplanning
    cfg['floorplan'] = {
        'short_help' : 'Floorplaning script/program',
        'switch' : '-floorplan',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
    
    # #4. Hard coded DEF
    cfg['def'] = {
        'short_help' : 'Firm floorplan file (DEF)',
        'switch' : '-def',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
    
    return cfg

###########################
# PNR Setup
###########################
def schema_apr(cfg):
    ''' Physical design parameters
    '''
    
    cfg['target'] = {
        'short_help' : 'Target platform',
        'switch' : '-target',
        'switch_args' : '<string>',        
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['target_stackup'] = {
        'short_help' : 'Target metal stackup',
        'switch' : '-target_stackup',
        'switch_args' : '<string>',        
        'type' : ['string'],
        'defvalue' : []
    }
    
    cfg['target_lib'] = {
        'short_help' : 'Target library/device',
        'switch' : '-target_lib',
        'switch_args' : '<string>',        
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['target_libarch'] = {
        'short_help' : 'Target library architecture',
        'switch' : '-target_libarch',
        'switch_args' : '<string>',        
        'type' : ['string'],
        'defvalue' : []
    }

    # custom pass through variables
    cfg['custom'] = {
        'short_help' : 'Custom EDA pass through variables',
        'switch' : '-custom',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    #optimization priority
    cfg['effort'] = {
        'short_help' : 'Compilation effort',
        'switch' : '-effort',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['high']
    }

    cfg['priority'] = {
        'short_help' : 'Optimization priority',
        'switch' : '-priority',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['timing']
    }

    #routing options
    cfg['ndr'] = {
        'short_help' : 'Non-default net routing file',
        'switch' : '-ndr',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
 
    cfg['minlayer'] = {
        'short_help' : 'Minimum routing layer (integer)',
        'switch' : '-minlayer',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }

    cfg['maxlayer'] = {
        'short_help' : 'Maximum routing layer (integer)',
        'switch' : '-maxlayer',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }
    
    cfg['maxfanout'] = {
        'short_help' : 'Maximum fanout',
        'switch' : '-maxfanout',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : []
    }
   
    #power
    cfg['vcd'] = {
        'short_help' : 'Value Change Dump (VCD) file',
        'switch' : '-vcd',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }

    cfg['saif'] = {
        'short_help' : 'Switching activity (SAIF) file',
        'switch' : '-saif',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : []
    }
    
    return cfg
    
############################################
# Constraints
#############################################   

def schema_constraints(cfg):

    cfg['mcmm_libcorner'] = {
        'short_help' : 'MMCM Lib Corner List (p_v_t)',
        'switch' : '-mcmm_libcorner',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['mcmm_pexcorner'] = {
        'short_help' : 'MMCM PEX Corner List',
        'switch' : '-mcmm_pexcorner',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['mcmm_scenario'] = {}
    cfg['mcmm_scenario']['default'] = {}
    
    cfg['mcmm_scenario']['default']['libcorner'] = {
        'short_help' : 'MMCM scenario libcorner',
        'switch' : '-mcmm_scenario_libcorner',
        'switch_args' : '<scenario libcorner>',
        'type' : ['string'],
        'defvalue' : []
    }

    cfg['mcmm_scenario']['default']['pexcorner'] = {
        'short_help' : 'MMCM scenario pexcorner',
        'switch' : '-mcmm_scenario_pexcorner',
        'switch_args' : '<scenario pexcorner>',
        'type' : ['string'],
        'defvalue' : []
    }
      
    cfg['mcmm_scenario']['default']['opcond'] = {
        'short_help' : 'MMCM scenario operating condition and library',
        'switch' : '-mcmm_scenario_opcond',
        'switch_args' : '<scenario (opcond library)>',
        'type' : ['string', 'string'],
        'defvalue' : []
    }
        
    cfg['mcmm_scenario']['default']['constraints'] = {
        'short_help' : 'MMCM scenario constraints',
        'switch' : '-mcmm_scenario_constraints',
        'switch_args' : '<scenario stage file>',
        'type' : ['file'],
        'hash' : [],
        'defvalue' : []
    }

    cfg['mcmm_scenario']['default']['objectives'] = {
        'short_help' : 'MMCM Objectives (setup, hold, power,...)',
        'switch' : '-mcmm_scenario_objectives',
        'switch_args' : '<scenario stage objective>',
        'type' : ['string'],
        'defvalue' : []
    }

    return cfg

###############################################
# Network Configuration for Remote Compute Jobs
###############################################

def schema_net(cfg):

    # Remote IP address or hostname of a server which is running 'sc-server'
    cfg['remote'] = {
        'short_help' : 'Remote server (https://acme.com:8080)',
        'switch': '-remote',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    # Port number that the remote host is running 'sc-server' on.
    cfg['remoteport'] = {
        'short_help': 'Port number which the remote \'sc-server\' instance is running on.',
        'switch': '-remote_port',
        'switch_args' : '<int>',
        'type' : ['int'],
        'defvalue' : ['8080']
    }

    # NFS config: Username to use when copying file to remote compute storage.
    cfg['nfsuser'] = {
        'short_help': 'Username to use when copying files to the remote compute storage host.',
        'switch': '-nfs_user',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['ubuntu']
    }

    # NFS config: Hostname to use for accessing shared remote compute storage.
    cfg['nfshost'] = {
        'short_help': 'Hostname or IP address where shared compute cluster storage can be accessed.',
        'switch': '-nfs_host',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : []
    }

    # NFS config: root filepath for shared NFS storage on the remote NFS host.
    cfg['nfsmount'] = {
        'short_help': 'Directory where shared NFS storage is mounted on the remote storage host.',
        'switch': '-nfs_mount',
        'switch_args' : '<string>',
        'type' : ['string'],
        'defvalue' : ['/nfs/sc_compute']
    }

    # NFS config: path to the SSH key file which will be used to access
    # the remote storage host.
    cfg['nfskey'] = {
        'short_help': 'Key file used to send files to remote compute storage.',
        'switch': '-nfs_key',
        'switch_args' : '<file>',
        'type' : ['file'],
        'defvalue' : []
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
        'switch_args': '<int>',
        'type': ['int'],
        'defvalue': ['8080']
    }

    cfg['nfsuser'] = {
        'short_help': 'Username to login to the remote storage host with.',
        'switch': '-nfs_user',
        'switch_args': '<string>',
        'type': ['string'],
        'defvalue': ['ubuntu']
    }

    cfg['nfshost'] = {
        'short_help': 'Hostname or IP address where shared compute cluster storage can be accesed.',
        'switch': '-nfs_host',
        'switch_args': '<string>',
        'type': ['string'],
        'defvalue' : []
    }

    cfg['nfsmount'] = {
        'short_help': 'Directory where shared NFS storage is mounted on individual slurm nodes.',
        'switch': '-nfs_mount',
        'switch_args': '<string>',
        'type': ['string'],
        'defvalue' : ['/nfs/sc_compute']
    }

    cfg['nfskey'] = {
        'short_help': 'Key file used to send files to shared compute cluster storage. Accepts a file path.',
        'switch': '-nfs_key',
        'switch_args': '<file>',
        'type': ['file'],
        'defvalue' : []
    }

    return cfg
