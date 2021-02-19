# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

###########################

def schema():
    '''Method for defining Chip configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    cfg = {}

    #FPGA Group
    cfg = schema_fpga(cfg)

    #PDK Group
    cfg = schema_pdk(cfg)

    #LIBS Group
    cfg = schema_libs(cfg, 'stdcells')

    cfg = schema_libs(cfg, 'macros')

    #EDA Group
    cfg = schema_eda(cfg)

    #Design Group
    cfg = schema_options(cfg)

    cfg = schema_rtl(cfg)

    cfg = schema_constraints(cfg)

    cfg = schema_floorplan(cfg)

    cfg = schema_apr(cfg)

    #Network Group
    cfg = schema_net(cfg)

    return cfg

###############################################################################
# FPGA
###############################################################################

def schema_fpga(cfg):
    ''' FPGA Setup
    '''
    cfg['fpga_xml'] = {
        'switch' : '-fpga_xml',
        'switch_args' : '<>',
        'requirement' : 'fpga',
        'type' : ['string', 'file'],
        'defvalue' : [],
        'short_help' : 'FPGA Architecture Description',
        'help' : ["Provides XML-based architecture description for the      ",
                  "target FPGA architecture to be used in VTR, allowing a   ",
                  "user to describe a large number of hypothetical and      ",
                  "commercial architectures.                                ",
                  "[More information...](https://verilogtorouting.org)      ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -fpga_xml myfpga.xml                                ",
                  "api:  chip.set('fpga_xml', 'myfpga.xml')                 "]
    }

    return cfg


###############################################################################
# PDK
###############################################################################

def schema_pdk(cfg):
    ''' Process Design Kit Setup
    '''

    cfg['pdk_foundry'] = {
        'switch' : '-pdk_foundry',
        'switch_args' : '<str>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Foundry Name',
        'help' : ["The name of the foundry. For example: intel, gf, tsmc,   ",
                  "samsung, skywater, virtual. The \'virtual\' keyword is   ",
                  "reserved for simulated non-manufacturable processes like ",
                  "freepdk45 and asap7.                                     ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_foundry virtual                                ",
                  "api:  chip.set('pdk_foundry', 'virtual')                 "]
    }

    cfg['pdk_process'] = {
        'switch' : '-pdk_process',
        'switch_args' : '<str>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Process Name',
        'help' : ["The official public name of the foundry process. The     ",
                  "name is case insensitive, but should otherwise match the ",
                  "complete public process name from the foundry. Example   ",
                  "process names include 22FFL from Intel, 12LPPLUS from    ",
                  "Globalfoundries, and 16FFC from TSMC.                    ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_process asap7                                  ",
                  "api:  chip.set('pdk_process', 'asap7')                   "]
    }

    cfg['pdk_node'] = {
        'switch' : '-pdk_node',
        'switch_args' : '<num>',
        'requirement' : 'asic',
        'type' : ['int'],
        'defvalue' : [],
        'short_help' : 'Process Node',
        'help' : ["An approximate relative minimum dimension of the process",
                  "node. A required parameter in some reference flows that ",
                  "leverage the value to drive technology dependent        ",
                  "synthesis and APR optimization. Node examples include   ",
                  "180nm, 130nm, 90nm, 65nm, 45nm, 32nm, 22nm, 14nm, 10nm, ",
                  "7nm, 5nm, 3nm. The value entered implies nanometers.    ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -pdk_node 130                                      ",
                  "api:  chip.set('pdk_node', '130')                       "]
    }

    cfg['pdk_rev'] = {
        'switch' : '-pdk_rev',
        'switch_args' : '<str>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Process Release Revision',
        'help' : ["An alphanumeric string specifying the revision  of the   ",
                  "current PDK. Verification of correct PDK and IP revisions",
                  "revisions is an ASIC tapeout requirement in all          ",
                  "commercial foundries.                                    ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_rev 1.0                                        ",
                  "api:  chip.set('pdk_rev', '1.0')                         "]
    }

    cfg['pdk_drm'] = {
        'switch' : '-pdk_drm',
        'switch_args' : '<file>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Process Design Rule Manual',
        'help' : ["A PDK document that includes complete information about ",
                  "all physical and electrical design rules to comply with ",
                  "in the design and layout of the chip. In cases where the",
                  "user guides and design rules are combined into a single ",
                  "document, the pdk_doc parameter can be left blank.      ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -pdk_drm asap7_drm.pdf                             ",
                  "api:  chip.set('pdk_drm', 'asap7_drm.pdf')              "]
    }

    cfg['pdk_doc'] = {
        'switch' : '-pdk_doc',
        'switch_args' : '<file>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Process Documents',
        'help' : ["A list of critical PDK designer documents provided by   ",
                  "the foundry entered in order of priority. The first item",
                  "in the list should be the primary PDK user guide. The   ",
                  "purpose of the list is to serve as a central record for ",
                  "all must-read PDK documents.                            ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -pdk_doc asap7_userguide.pdf                       ",
                  "api:  chip.set('pdk_doc', 'asap7_userguide.pdf')        "]
    }

    cfg['pdk_stackup'] = {
        'switch' : '-pdk_stackup',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Process Metal Stackups',
        'help' : ["A list of all metal stackups offered in the process node ",
                  "Older process nodes may only offer a single metal        ",
                  "stackup, while advanced nodes offer a large but finite   ",
                  "list of metal stacks with varying combinations of metal  ",
                  "line pitches and thicknesses. Stackup naming is unqiue   ",
                  "to a foundry, but is generally a long string or code. For",
                  "example, a 10 metal stackup two 1x wide, four 2x wide,   ",
                  "and 4x wide metals, might be identified as 2MA4MB2MC.    ",
                  "Each stackup will come with its own set of routing       ",
                  "technology files and parasitic models specified in the   ",
                  "pdk_pexmodel and pdk_aprtech parameters.                 ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_stackup 2MA4MB2MC                              ",
                  "api:  chip.set('pdk_stackup', '2MA4MB2MC')               "]
    }

    cfg['pdk_devmodel'] = {}
    cfg['pdk_devmodel']['default'] = {}
    cfg['pdk_devmodel']['default']['default'] = {}
    cfg['pdk_devmodel']['default']['default']['default'] = {
        'switch' : '-pdk_devmodel',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Device Models',
        'help' : ["A dynamic dictionary of filepaths for all PDK device     ",
                  "models. The structure serves as a central access registry",
                  "for models for different purpose and tools. The format   ",
                  "for the dictionary is [stackup][type][tool]. Examples of ",
                  "device model types include spice, aging, electromigration",
                  ",radiation. An example of a spice tool is xyce.          ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_devmodel '2MA4MB2MC spice xyce asap7.sp'       ",
                  "api: chip.set('pdk_devmodel','2MA4MB2MC','spice','xyce', ",
                  "              'asap7.sp')                                "]
    }

    cfg['pdk_pexmodel'] = {}
    cfg['pdk_pexmodel']['default'] = {}
    cfg['pdk_pexmodel']['default']['default']= {}
    cfg['pdk_pexmodel']['default']['default']['default'] = {
        'switch' : '-pdk_pexmodel',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Parasitic Extraction TCAD Models',
        'help' : ["A dynamic dictionary of filepaths for all PDK wire TCAD  ",
                  "models. The structure serves as a central access registry",
                  "for models for different purpose and tools. The format   ",
                  "for the dictionary is [stackup][corner][tool]. Examples  ",
                  "of RC extraction corners include: min, max, nominal. An  ",
                  "example of an extraction tool is FastCap.                ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_pexmodel '2MA4MB2MC max fastcap wire.mod'      ",
                  "api: chip.set('pdk_pexmodel','2MA4MB2MC','max','fastcap',",
                  "              'wire.mod')                                "]
    }

    cfg['pdk_layermap'] = {}
    cfg['pdk_layermap']['default'] = {}
    cfg['pdk_layermap']['default']['default'] = {}
    cfg['pdk_layermap']['default']['default']['default'] = {
        'switch' : '-pdk_layermap',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : [],
        'short_help' : 'Mask Layer Maps',
        'help' : ["A dynamic dictionary of filepaths describing input/output",
                  "mapping for streaming layout data from one format to     ",
                  "another. A foundry PDK will include an official layer    ",
                  "list for all user entered and generated layers supported ",
                  "in the GDS accepted by the foundry for processing, but   ",
                  "there is no standardized layer definition format that can",
                  "be read and written by all EDA tools. To ensure mask     ",
                  "layer matching, key/value type mapping files are needed  ",
                  "to convert EDA databases to/from GDS and to convert      ",
                  "between different types of EDA databases. The format for ",
                  "the dictionary is [stackup][src][dst].                   ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_layermap '2MA4MB2MC libtool gds asap7.map'     ",
                  "api: chip.set('pdk_layermap','2MA4MB2MC','libtool','gds',",
                  "              'asap7.map')                               "]
    }

    cfg['pdk_display'] = {}
    cfg['pdk_display']['default'] = {}
    cfg['pdk_display']['default']['default'] = {
        'switch' : '-pdk_display',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : [],
        'short_help' : 'Display Configurations',
        'help' : ["A dynamic dictionary of display configuration files      ",
                  "describing colors and pattern schemes for all layers in  ",
                  "the PDK. The display configuration file is entered on a  ",
                  "stackup and per tool basis, with the dictionary format   ",
                  "being [stackup][tool].                                   ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_display '2MA4MB2MC klayout display.cfg'        ",
                  "api: chip.set('pdk_display','2MA4MB2MC','klayout',       ",
                  "              'display.cfg')                             "]
    }

    cfg['pdk_lib'] = {}
    cfg['pdk_lib']['default'] = {}
    cfg['pdk_lib']['default']['default'] = {
        'switch' : '-pdk_clib',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : [],
        'short_help' : 'Custom Design Libraries',
        'help' : ["A dynamic dictionary of filepaths to all primitive cell  ",
                  "libraries supported by the PDK. The filepaths are entered",
                  "on a per stackup basis with the format: [stackup][tool]. ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_lib '2MA4MB2MC oa /disk/asap7/oa/devlib'       ",
                  "api: chip.set('pdk_lib','2MA4MB2MC','oa',                ",
                  "              '/disk/asap7/oa/devlib')                   "]
    }

    cfg['pdk_aprtech'] = {}
    cfg['pdk_aprtech']['default'] = {}
    cfg['pdk_aprtech']['default']['default'] = {}
    cfg['pdk_aprtech']['default']['default']['default'] = {
        'switch' : '-pdk_aprtech',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Place and Route Technology Files',
        'help' : ["A dynamic dictionary of paths to technology files       ",
                  "containing the design rule and setup information needed ",
                  "to enable DRC clean automated placement a routing. The  ",
                  "nested dictionary format is [stackup][libtype][format], ",
                  "where libtype generally indicates the height of the     ",
                  "standard cell library supported by the PDK. For example ",
                  "with support for 9 and 12 track libraries might have    ",
                  "libtypes called 9t and 12t.                             ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -pdk_aprtech '2MA4MB2MC 12t openroad asap_tech.lef'",
                  "api: chip.set('pdk_aprtech','2MA4MB2MC','12t','lef',    ",
                  "              'asap_tech.lef')                          "]
    }


    cfg['pdk_aprlayer'] = {}
    cfg['pdk_aprlayer']['default'] = {
        'switch' : '-pdk_aprlayer',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string', 'string', 'float', 'float'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Place and Route Layer Definitions',
        'help' : ["A optional list of metal layer definitions. Generally,   ",
                  "all APR setup rules would be read from the pdk_aprtec    ",
                  "file but there are cases when these rules should be      ",
                  "overriden with non-minimal design rules. The list enables",
                  "per layer routing rule definitions, entered as a tuple of",
                  "with format 'metalname preferred-dir width pitch'. The   ",
                  "values are entered on a per stackup basis with X denoting",
                  "horizontal direction, Y denoting vertical direction, and ",
                  "the width and pitch entered in micrometers.              ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_aprlayer 'm1 X 0.5 1.0'                        ",
                  "api: chip.set('pdk_aprlayer','m1 X 0.5 1.0')             "]
    }

    cfg['pdk_tapmax'] = {
        'switch' : '-pdk_tapmax',
        'switch_args' : '<num>',
        'requirement' : 'apr',
        'type' : ['float'],
        'defvalue' : [],
        'hash' : [],
        'short_help' : 'Tap Cell Max Distance Rule',
        'help' : ["Specifies the maximum distance allowed between tap cells ",
                  "in the PDK. The value is required for automated place and",
                  "route and is entered in micrometers.                     ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_tapmax 100                                     ",
                  "api: chip.set('pdk_tapmax','100')                        "]
    }

    cfg['pdk_tapoffset'] = {
        'switch' : '-pdk_tapoffset',
        'switch_args' : '<num>',
        'requirement' : 'apr',
        'type' : ['float'],
        'defvalue' : [],
        'hash' : [],
        'short_help' : 'Tap Cell Offset Rule',
        'help' : ["Specifies the offset from the edge of the block to the   ",
                  "tap cell grid. The value is required for automated place ",
                  "and route and is entered in micrometers.                 ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -pdk_tapoffset 0                                    ",
                  "api: chip.set('pdk_tapoffset','0')                       "]
    }

    return cfg

###############################################################################
# Library Configuration
###############################################################################

def schema_libs(cfg, group):

    cfg[group] = {}

    cfg[group]['default'] = {}

    cfg[group]['default']['rev'] = {
        'switch' : '-'+group+'_rev',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Library Release Revision',
        'help' : ["A dynamic dictionary specifying an alphanumeric revision ",
                  "string on a per library basis. Verification of correct   ",
                  "PDK and IP revisions is an ASIC tapeout requirement in   ",
                  "all commercial foundries.                                ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_rev 'mylib 1.0'                          ",
                  "api: chip.set('"+group+"','mylib','rev','1.0')           "]
    }

    cfg[group]['default']['doc'] = {
        'switch' : '-'+group+'_doc',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library Documentation',
        'help' : ["A list of critical library documents entered in order of ",
                  "importance. The first item in thelist should be the      ",
                  "primary library user guide. The purpose of the list is to",
                  "serve as a central record for all must-read PDK documents",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_doc 'mylib mylib_guide.pdf'              ",
                  "api: chip.set('"+group+"','mylib','doc',                 ",
                  "              'mylib_guide.pdf')                         "]
    }

    cfg[group]['default']['ds'] = {
        'switch' : '-'+group+'_ds',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library Datasheets',
        'help' : ["A complete collection of datasheets for the library. The ",
                  "documentation can be provied as a PDF or as a filepath to",
                  "a directory with one HTMl file per cell. This parameter  ",
                  "is optional for libraries where the datsheet is merged   ",
                  "within the library integration document.                 ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_ds 'mylib mylib_ds.pdf'                  ",
                  "api: chip.set('"+group+"','mylib','ds','mylib_ds.pdf')   "]
    }

    cfg[group]['default']['libtype'] = {
        'switch' : '-'+group+'_libtype',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Library Type',
        'help' : ["Libtype is a a unique string that identifies the row     ",
                  "height or performance class of the library for APR. The  ",
                  "libtype must match up with the name used in the          ",
                  "pdk_aprtech dictionary. Mixing of libtypes in a flat     ",
                  "place and route block is not allowed.                    ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_libtype 'mylib 12t'                      ",
                  "api: chip.set('"+group+"','mylib','libtype','12t')       "]
    }

    cfg[group]['default']['size'] = {
        'switch' : '-'+group+'_size',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['float', 'float'],
        'defvalue' : [],
        'short_help' : 'Library Height',
        'help' : ["Specifies the height and width of a unit cell. Values are",
                  "entered as width heigh tuplest. The value can usually be ",
                  "extracted automatically from the layout library but is   ",
                  "included in the schema to simplify the process of        ",
                  "creating parametrized floorplans. The parameter can be   ",
                  "omitted for macro libraries that lack the concept of a   ",
                  "unit cell.                                               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_size 'mylib 0.1 0.5'                     ",
                  "api: chip.set('"+group+"','mylib','size','0.1 0.5')      "]
    }


    cfg[group]['default']['nldm'] = {}
    cfg[group]['default']['nldm']['default'] = {}
    cfg[group]['default']['nldm']['default']['default'] = {
        'switch' : '-'+group+'_nldm',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : [],
        'short_help' : 'Library Non-Linear Delay Model',
        'help' : ["A dynamic dictionary of paths to non-linear delay model  ",
                  "files specified in the liberty format. The NLDM files are",
                  "specified on a per lib, per corner, and per format       ",
                  "basis with dictionary structure being:                   ",
                  "['libname']['nldm']['cornername']['format']              ",
                  "The format is driven by EDA tool requirements. Examples  ",
                  "of legal formats includ: lib, lib.gz, lib.bz2, and ldb.  ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_nldm 'mylib ttt lib mylib.lib'           ",
                  "api: chip.set('"+group+"','mylib','nldm','ttt','lib',    ",
                  "              'mylib.lib')                               "]
    }


    cfg[group]['default']['ccs'] = {}
    cfg[group]['default']['ccs']['default'] = {}
    cfg[group]['default']['ccs']['default']['default']= {
        'switch' : '-'+group+'_ccs',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash' : [],
        'short_help' : 'Library Composite Current Source Model File',
        'help' : ["A dynamic dictionary of paths to composite current source",
                  "models. CCS models are more acccurate than NLDM models   ",
                  "and are required for signoff at advanced nodes, but are  ",
                  "significantly larger and slower. The CCS files are       ",
                  "specified on a per lib, per corner, and per format basis ",
                  "with dictionary structure being:                         ",
                  "['libname']['ccs']['cornername']['format']               ",
                  "The format is driven by EDA tool requirements. Examples  ",
                  "of legal formats includ: lib, lib.gz, lib.bz2, and ldb.  ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_ccs 'mylib ttt lib mylib_ccs.lib'        ",
                  "api: chip.set('"+group+"','mylib','ccs','ttt','lib',     ",
                  "              'mylib_ccs.lib')                           "]
    }

    cfg[group]['default']['lef'] = {
        'switch' : '-'+group+'_lef',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library LEF Files',
        'help' : ["An abstracted view of library cells that gives complete  ",
                  "information about the cell place and route boundary, pin ",
                  "positions, pin metals, and metal routing blockages.      ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_lef 'mylib mylib.lef'                    ",
                  "api: chip.set('"+group+"','mylib','lef','mylib.lef'      "]
    }

    cfg[group]['default']['gds'] = {
        'switch' : '-'+group+'_gds',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library GDS Files',
        'help' : ["The complete mask layout of the library cells ready to be",
                  "merged with the rest of the design for tapeout. In some  ",
                  "cases, the GDS merge happens at the foundry, so inclusion",
                  "of a GDS file is optional. In all cases, where the GDS   ",
                  "files are available, they should specified here to enable",
                  "gds stream out/merge during the automated place and route",
                  "and chip assembly process.                               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_gds 'mylib mylib.gds'                    ",
                  "api: chip.set('"+group+"','mylib','gds','mylib.gds'      "]
    }

    cfg[group]['default']['cdl'] = {
        'switch' : '-'+group+'_cdl',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
         'short_help' : 'Library CDL Netlist Filesx',
        'help' : ["Files containing the netlists used for layout versus     ",
                  "schematic (LVS) checks. In some cases, the GDS merge     ",
                  "happens at the foundry, so inclusion of a CDL file is    ",
                  "optional. In all cases, where the CDL files are          ",
                  "available they should specified here to enable LVS checks",
                  "pre tapout                                               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_cdl 'mylib mylib.cdl'                    ",
                  "api: chip.set('"+group+"','mylib','cdl','mylib.cdl'      "]
    }

    cfg[group]['default']['spice'] = {
        'switch' : '-'+group+'_spice',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library Spice Netlist Files',
        'help' : ["Files containing the library spice netlists used for     ",
                  "circuit simulation.                                      ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_spice 'mylib mylib.sp'                   ",
                  "api: chip.set('"+group+"','mylib','spice','mylib.sp'     "]
    }

    cfg[group]['default']['hdl'] = {
        'switch' : '-'+group+'_hdl',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library HDL Model Files',
        'help' : ["Digital HDL models of the library cells, modeled in VHDL ",
                  "or verilog for use in funcational simulations.           ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_hdl 'mylib mylib.v'                      ",
                  "api: chip.set('"+group+"','mylib','hdl','mylib.v'        "]
    }

    cfg[group]['default']['atpg'] = {
        'switch' : '-'+group+'_atpg',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library ATPG Files',
        'help' : ["Library models used for ATPG based automated faultd based",
                  "post manufacturing testing.                              ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_atpg 'mylib mylib.atpg'                  ",
                  "api: chip.set('"+group+"','mylib','atpg','mylib.atpg')   "]
    }

    cfg[group]['default']['rails'] = {
        'switch' : '-'+group+'_rails',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Library Power/Ground Rails Metal Layer',
        'help' : ["Specifies the top metal layer used for power and ground  ",
                  "routing within the library. The parameter can be used to ",
                  "guide cell power grid hookup by APR tools.               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_rails 'mylib m1'                         ",
                  "api: chip.set('"+group+"','mylib','rails','m1')          "]
    }

    cfg[group]['default']['vt'] = {
        'switch' : '-'+group+'_vt',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['string'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library Transistor Threshold',
        'help' : ["The variable specifies the voltage threshold type of the ",
                  "library. The value is extracted automatically if found in",
                  "the default_threshold_voltage_group within the nldm/ccs  ",
                  "model. For older technologies with only one vt group, it ",
                  "the value can be set to an arbitrary string (eg: svt)    ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_vt 'mylib lvt'                           ",
                  "api: chip.set('"+group+"','mylib','vt','lvt')            "]
    }

    cfg[group]['default']['tag'] = {
        'switch' : '-'+group+'_tag',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Library Identifier Tags',
        'help' : ["Marks a library with a set of tags that can be used by   ",
                  "the designer and EDA tools for optimization purposes. The",
                  "tags are meant to cover features not currently supported ",
                  "by built in EDA optimization flows, but which can be     ",
                  "queried through EDA tool TCL commands and lists. The     ",
                  "example below demonstrates tagging the whole library as  ",
                  "virtual.                                                 ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_tag 'mylib virtual'                      ",
                  "api: chip.set('"+group+"','mylib','tag','virtual')       "]
    }

    cfg[group]['default']['driver'] = {
        'switch' : '-'+group+'_driver',
        'switch_args' : '<>',
        'requirement' : 'apr',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Library Default Driver Cell',
        'help' : ["The name of a library cell to be used as the default     ",
                  "driver for block timing constraints. The cell should be  ",
                  "strong enough to drive a block input from another block  ",
                  "including wire capacitance. In cases, where the actual   ",
                  "drive is known, the actual driver cell should be used.   ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_driver 'mylib BUFX1'                     ",
                  "api: chip.set('"+group+"','mylib','driver','BUFX1')      "]
    }

    cfg[group]['default']['site'] = {
        'switch' : '-'+group+'_site',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Library Site/Tile Name',
        'help' : ["Provides the primary site name within the library to use ",
                  "for placement. Value can generally be automatically      ",
                  "inferred from the provided library lef file.             ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_site 'mylib mylibsc7p5'                  ",
                  "api: chip.set('"+group+"','mylib','site','mylibsc7p5')   "]
    }

    cfg[group]['default']['cells'] = {}
    cfg[group]['default']['cells']['default'] = {
        'switch' : '-'+group+'_cells',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Library Cell Lists',
        'help' : ["A named list of cells grouped by a property that can be  ",
                  "accessed directly by the designer and EDA tools. The     ",
                  "example below shows how all cells containing the string  ",
                  "'eco' could be marked as dont use for the tool.          ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_cells 'mylib dontuse *eco*'              ",
                  "api: chip.set('"+group+"','mylib','cells','dontuse',     ",
                  "              '*eco*')                                   "]
    }

    cfg[group]['default']['setup'] = {}
    cfg[group]['default']['setup']['default'] = {
        'switch' : '-'+group+'_setup',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Library Setup Files',
        'help' : ["A list of setup files for use by specific EDA tools. The ",
                  "files are specified on a per EDA tool basis.             ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_setup 'mylib openroad mylib.tcl'         ",
                  "api: chip.set('"+group+"','mylib','setup','openroad',    ",
                  "              'mylib.tcl')                               "]
    }

    cfg[group]['default']['laydb'] = {}
    cfg[group]['default']['laydb']['default'] = {
        'switch' : '-'+group+'_laydb',
        'switch_args' : '<>',
        'requirement' : 'optional',
        'type' : ['file'],
        'defvalue' : [],
        'hash'   : [],
         'short_help' : 'Library Layout Database',
        'help' : ["A dynamic dictionary with filepaths to compiled library  ",
                  "layout database specified on a per format basis. Example ",
                  "formats include oa, mw, ndm.                             ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -"+group+"_laydb 'mylib oa /disk/myliblib'          ",
                  "api: chip.set('"+group+"','mylib','laydb','oa',          ",
                  "              '/disk/myliblib')                          "]
    }

    return cfg

###############################################################################
# EDA Tool Configuration
###############################################################################

def schema_eda(cfg):

    cfg['compile_stages'] = {
        'switch' : '-compile_stages',
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
                      'export'],
        'short_help' : 'List of Compilation Stages',
        'help' : ["A complete list of all stages included in fully automated",
                  "RTL to GDSII compilation. Compilation flow is controlled ",
                  "with the -start, -stop, -cont switches and by adding     ",
                  "values to the list. The list must be ordered to enable   ",
                  "default automated compilation from the first entry to the",
                  "last entry in the list. Inserting stages in the middle of",
                  "the list is only possible by overwriting the whole list. ",
                  "The example below demonstrates adding a tapeout stage    ",
                  "at the end of the compile_stages list.                   ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -compile_stages 'tapeout'                           ",
                  "api:  chip.add('compile_stages', 'tapeout')              "]
    }

    cfg['dv_stages'] = {
        'switch' : '-dv_stages',
        'switch_args' : '<str>',
        'requirement' : 'all',
        'type' : ['string'],
        'defvalue' : ['lec',
                      'pex',
                      'sta',
                      'pi',
                      'si',
                      'drc',
                      'erc',
                      'lvs'],
        'short_help' : 'List of Verification Stages',
        'help' : ["A complete list of all verification stages. Verification ",
                  "flow is controlled with the -start, -stop, -cont switches",
                  "and by expanding the list. The list must be ordered to   ",
                  "enable default automated verification from the first     ",
                  "entry to the last entry in the list. Inserting stages in ",
                  "the middle of the list is only possible by overwriting   ",
                  "the whole list. The example below demonstrates adding an ",
                  "archive stage at the end of the dv_stages list           ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -dv_stages 'archive'                                ",
                  "api:  chip.add('dv_stages', 'archive')                   "]
    }

    cfg['view_stages'] = {
        'switch' : '-view_stages',
        'switch_args' : '<str>',
        'requirement' : 'all',
        'type' : ['string'],
        'defvalue' : ['dashboard',
                      'defview',
                      'gdsview'],
        'short_help' : 'List of Interactive Viewer Stages',
        'help' : ["A complete list of all interactive viewer stages. The    ",
                  "viewer stages are not meant to be executed as a pipeline,",
                  "but serves as a central record for documenting tools and ",
                  "options for display tools.                               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -view_stages 'scopeview'                            ",
                  "api:  chip.add('view_stages', 'scopeview')               "]
    }

    #Concatenated list
    all_stages = (cfg['compile_stages']['defvalue'] +
                  cfg['dv_stages']['defvalue'] +
                  cfg['view_stages']['defvalue'])

    cfg['tool'] = {}

    # Defaults and config for all stages
    for stage in all_stages:
        cfg['tool'][stage] = {}

        # Exe
        cfg['tool'][stage]['exe'] = {}
        cfg['tool'][stage]['exe']['switch'] = '-tool_exe'
        cfg['tool'][stage]['exe']['switch_args'] = '<>'
        cfg['tool'][stage]['exe']['type'] = ['string']
        cfg['tool'][stage]['exe']['requirement'] = ['all']
        cfg['tool'][stage]['exe']['defvalue'] = []
        cfg['tool'][stage]['exe']['short_help'] = 'Executable Name'
        cfg['tool'][stage]['exe']['help'] = [
            "The name of the exuctable tool or the full path to the   ",
            "executable specified on a per stage basis.               ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_exe 'place openroad'                          ",
            "api:  chip.set('tool','place','exe','openroad')          "]

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
            "as a one list entry, specified on a per stage basis.     ",
            "Command line values must be enclosed in quotes.          ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_opt 'place -no_init'                          ",
            "api:  chip.set('tool','place','opt','-no_init')          "]

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
            "A path to a directory containing compilation scripts     ",
            "used by the executable specified on a per stage basis.   ",
            "                                                         ",
            "Examples:                                                ",
                  "cli: -tool_refdir 'place ./myrefdir'               ",
                  "api: chip.set('tool','place','refdir','./myrefdir')"]

        #script
        cfg['tool'][stage]['script'] = {}
        cfg['tool'][stage]['script']['switch'] = '-tool_script'
        cfg['tool'][stage]['script']['switch_args'] = '<>'
        cfg['tool'][stage]['script']['type'] = ['file']
        cfg['tool'][stage]['script']['requirement'] = 'optional'
        cfg['tool'][stage]['script']['hash'] = []
        cfg['tool'][stage]['script']['defvalue'] = []
        cfg['tool'][stage]['script']['short_help'] = 'Entry point Script'
        cfg['tool'][stage]['script']['help'] = [
            "Path to the entry point compilation script called by the ",
            "executable specified on a per stage basis.               ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_script 'place ./myrefdir/place.tcl'           ",
            "api: chip.set('tool','place','refdir',                   ",
            "              './myrefdir/place.tcl')                    "]

        #copy
        cfg['tool'][stage]['copy'] = {}
        cfg['tool'][stage]['copy']['switch'] = '-tool_copy'
        cfg['tool'][stage]['copy']['switch_args'] = '<>'
        cfg['tool'][stage]['copy']['type'] = ['string']
        cfg['tool'][stage]['copy']['requirement'] = 'optional'
        cfg['tool'][stage]['copy']['defvalue'] = []
        cfg['tool'][stage]['copy']['short_help'] = 'Copy Local Option'
        cfg['tool'][stage]['copy']['help'] = [
            "Specifies that the reference script directory should be  ",
            "copied and run from the local run directory. The option  ",
            "specified on a per stage basis.                          ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_copy 'place True'                             ",
            "api: chip.set('tool','place','copy','True')              "]

        #format
        cfg['tool'][stage]['format'] = {}
        cfg['tool'][stage]['format']['switch'] = '-tool_format'
        cfg['tool'][stage]['format']['switch_args'] = '<>'
        cfg['tool'][stage]['format']['type'] = ['string']
        cfg['tool'][stage]['format']['requirement'] = ['all']
        cfg['tool'][stage]['format']['defvalue'] = []
        cfg['tool'][stage]['format']['short_help'] = 'Script Format'
        cfg['tool'][stage]['format']['help'] = [
            "Specifies that format of the configuration file for the  ",
            "stage. Valid formats are tcl, yaml, and json. The format ",
            "used is dictated by the executable for the stage and     ",
            "specified on a per stage basis.                          ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_format 'place tcl'                            ",
            "api: chip.set('tool','place','format','tcl')             "]

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
            "forward to the next stage of the implementation pipeline ",
            "in cases where multiple jobs are run for one stage and a ",
            "programmatic selection if made to choose the best result ",
            "the variable can be used to point to a job which may not ",
            "be the last job launched. Job IDs are tracked on a per   ",
            "stage basis.                                             ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_jobid 'place 5'                               ",
            "api: chip.set('tool','place','jobid','5')                "]

        #parallelism
        cfg['tool'][stage]['np'] = {}
        cfg['tool'][stage]['np']['switch'] = '-tool_np'
        cfg['tool'][stage]['np']['switch_args'] = '<>'
        cfg['tool'][stage]['np']['type'] = ['int']
        cfg['tool'][stage]['np']['requirement'] = ['all']
        cfg['tool'][stage]['np']['defvalue'] = []
        cfg['tool'][stage]['np']['short_help'] = 'Thread Parallelism'
        cfg['tool'][stage]['np']['help'] = [
            "Specifies the level of CPU thread parallelism to enable  ",
            "on a per stage basis. This information is intended for   ",
            "the EDA tools to use to parallelize workloads on a       ",
            "multi-core single node CPU. Job parallelization across   ",
            "multiple machines can be explicitly specified using      ",
            "custom compilation scripts.                              ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_np 'drc 64'                                   ",
            "api: chip.set('tool','drc','np','64')                    "]


        #keymap
        cfg['tool'][stage]['keymap'] = {}
        cfg['tool'][stage]['keymap']['switch'] = '-tool_keymap'
        cfg['tool'][stage]['keymap']['switch_args'] = '<>'
        cfg['tool'][stage]['keymap']['type'] = ['string', 'string']
        cfg['tool'][stage]['keymap']['requirement'] = 'optional'
        cfg['tool'][stage]['keymap']['defvalue'] = []
        cfg['tool'][stage]['keymap']['short_help'] = 'Script Keymap'
        cfg['tool'][stage]['keymap']['help'] = [
            "The keymap is used to translate the schema keys when     ",
            "writing out the configuration to a TCL, JSON, or YAML    ",
            "file to be loaded by an EDA tool. Keymaps are specific to",
            "each EDA tool and specified on a per stage basis.        ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_keymap 'place design design_name'             ",
            "api: chip.set('tool','place','design', 'design_name')    "]

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
            "technology setup variables from the PDK and libraries    ",
            "which generally support multiple vendors for each        ",
            "implementation stage                                     ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -tool_vendor 'place vendor openroad'                ",
            "api: chip.set('tool','place','vendor', 'openroad')       "]

    return cfg

############################################
# Run-time Options
#############################################

def schema_options(cfg):
    ''' Run-time options
    '''
    cfg['cfgfile'] = {
        'switch' : '-cfgfile',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Compiler Configuration File',
        'help' : ["All parameters can be set at the command line, but with  ",
                  "over 100 configuration parameters available, the         ",
                  "preferred method for non trivial use cases is to create  ",
                  "a cfg file using the API. The cfg file can then be passed",
                  "in through he -cfgfile switch at the command line. There ",
                  "is no restriction on the number of cfgfiles that can be  ",
                  "be passed in. but it should be noted that the cfgfile are",
                  "appended to the existing list and configuration list.    ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -cfgfile 'mypdk.json'                               ",
                  "api: chip.set('cfgfile','mypdk.json)                     "]
    }

    cfg['env'] = {
        'switch' : '-env',
        'switch_args' : '<>',
        'type' : ['string', 'string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Environment Variables',
        'help' : ["Certain EDA tools and reference flows require environment",
                  "variables to be set. These variables can be managed      ",
                  "externally or specified through the env variable.        ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -env '$PDK_HOME /disk/mypdk'                        ",
                  "api: chip.set('env','$PDK_HOME /disk/mypdk')             "]
    }


    cfg['lock'] = {
        'switch' : '-lock',
        'switch_args' : '',
        'type' : ['bool'],
        'requirement' : 'optional',
        'defvalue' : ['False'],
        'short_help' : 'Configuration File Lock',
        'help' : ["The boolean lock switch can be used to prevent unintended",
                  "updates to the chip configuration. For example, a team   ",
                  "might converge on a golden reference methodology and will",
                  "have a company policy to not allow designers to deviate  ",
                  "from that golden reference. After the lock switch has    ",
                  "been set, the current configuration is in read only mode ",
                  "until the end of the compilation                         ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -lock                                               ",
                  "api: chip.set('lock','True')                             "]
    }

    cfg['quiet'] = {
        'short_help' : 'Quiet Execution Option',
        'switch' : '-quiet',
        'switch_args' : '',
        'type' : ['bool'],
        'requirement' : 'optional',
        'defvalue' : ['False'],
        'short_help' : 'Suppress informational printing',
        'help' : ["Modern EDA tools print significant content to the screen.",
                  "The -quiet option forces all stage prints into a per job ",
                  "log file.                                                ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -quiet                                              ",
                  "api: chip.set('quiet','True')                            "]
    }

    cfg['debug'] = {
        'switch' : '-debug',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : ['WARNING'],
        'short_help' : 'Debug Level',
        'help' : ["The debug param provides explicit control over the level ",
                  "of debug logging printed. Valid entries include INFO,    ",
                  "DEBUG, WARNING, ERROR. The default value is WARNING.     ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -debug INFO                                         ",
                  "api: chip.set('debug','INFO')                            "]
    }

    cfg['build'] = {
        'switch' : '-build',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : ['build'],
        'short_help' : 'Build Directory Name',
        'help' : ["By default, compilation is done in the local './build'   ",
                  "directory. The build parameter enables setting an        ",
                  "alternate compilation directory path.                    ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -build './build_the_future'                         ",
                  "api: chip.set('build','./build_the_future')              "]
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
                  "be continued from that point by specifying -start place  ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -start 'place'                                      ",
                  "api: chip.set('start','place')                           "]
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
                  "been completed.                                          ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -stop 'route'                                       ",
                  "api: chip.set('stop','route')                            "]

    }

    cfg['skip'] = {
        'switch' : '-skip',
        'switch_args' : '<stage>',
        'type' : ['string'],
        'defvalue' : [],
        'requirement' : 'optional',
        'short_help' : 'Compilation Skip Stages',
        'help' : ["In some older technologies it may be possible to skip    ",
                  "some of the stages in the standard flow defined by the   ",
                  "'compile_stages' and 'dv_stages' lists. The skip variable",
                  "lists the stages to be skipped during execution.         ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -skip 'import'                                      ",
                  "api: chip.set('skip','import')                           "]
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
                  "the syn, place, and cts stages.                          ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -msg_trigger 'export'                               ",
                  "api: chip.set('msg_trigger','export')                    "]
    }

    cfg['msg_contact'] = {
        'switch' : '-msg_contact',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Message Contact Information',
        'help' : ["A list of phone numbers or email addresses to message on ",
                  "a trigger event within the msg_trigger param.            ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -msg_contact 'wile.e.coyote@acme.com'               ",
                  "api: chip.set('msg_contact','wile.e.coyote@acme.com')    "]
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
        'short_help' : 'Source File List',
        'help' : ["A list of source files to read in for elaboration. The   ",
                  "files are read in order from first to last entered. File ",
                  "type is inferred from the file suffix:                   ",
                  "                                                         ",
                  "(*.v, *.vh) = Verilog                                    ",
                  "(*.sv)      = SystemVerilog                              ",
                  "(*.vhd)     = Vhdl                                       ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: 'hello_world.v'                                     ",
                  "api: chip.add('source','hello_world.v')                  "]
    }

    cfg['design'] = {
        'switch' : '-design',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Top Module Name',
        'help' : ["The name of the top level design to compile. Required in ",
                  "all non-single-module designs.                           ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -design 'hello_world'                               ",
                  "api: chip.set('design','hello_world')                    "]
    }

    cfg['nickname'] = {
        'switch' : '-nickname',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Nickname',
        'help' : ["An alias for the top level design name. Can be useful    ",
                  "when top level designs have long and confusing names. The",
                  "nickname is used in all output file prefixes.            ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -nickname 'top'                                     ",
                  "api: chip.set('nickname','top')                          "]
        }


    cfg['clock'] = {
        'switch' : '-clock',
        'switch_args' : '<>',
        'type' : ['string', "string", 'float', 'float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Clock Definitions',
        'help' : ["A complete clock definition specifying the name of the   ",
                  "clock, the name of the clock port, or the full hierarchy ",
                  "path to the generated internal clock, the clock frequency",
                  "and the clock uncertainty (jitter). The definition can be",
                  "used to drive constraints for implementation and signoff.",
                  "Clock period and clock jitter are specified in           ",
                  "nanoseconds.                                             ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -clock 'clk top.pll.clkout 10.0 0.1'                ",
                  "api: chip.add('clock','clk top.pll.clkout 10.0 0.1')     "]
    }

    cfg['supply'] = {
        'switch' : '-supply',
        'switch_args' : '<>',
        'type' : ['string', 'string', 'float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Power Supplies',
        'help' : ["A complete power supply definition specifying the supply ",
                  "name, the net name, and the voltage.The definition can   ",
                  "be used to drive constraints for implementation and      ",
                  "signoff. Supply values specified in Volts.               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -supply 'vdd vdd 0.9'                               ",
                  "api: chip.add('supply','vdd vdd 0.9')                    "]
    }

    cfg['define'] = {
        'switch' : '-D',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Verilog Preprocessor Define Symbols',
        'help' : ["Sets a preprocessor symbol for verilog source imports.   ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -D'CFG_ASIC=1'                                      ",
                  "api: chip.add('define','CFG_ASIC=1')                     "]
    }

    cfg['ydir'] = {
        'switch' : '-y',
        'switch_args' : '<dir>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Verilog Module Search Directories',
        'help' : ["Provides a search paths to look for modules found in the ",
                  "the source list. The import engine will look for modules ",
                  "inside files with the specified +libext+ param suffix    ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -y './mylib'                                        ",
                  "api: chip.add('ydir','./mylib')                          "]
    }

    cfg['idir'] = {
        'switch' : '-I',
        'switch_args' : '<dir>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Verilog Include File Search Directories',
        'help' : ["Provides a search paths to look for files included in    ",
                  "the design using the `include statement.                 ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -I'./mylib'                                         ",
                  "api: chip.add('idir','./mylib')                          "]
    }

    cfg['vlib'] = {
        'switch' : '-v',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Verilog Library Files',
        'help' : ["Declares source files to be read in, for which modules   ",
                  "are not to be interpreted as root modules.               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -v'./mylib.v'                                       ",
                  "api: chip.add('vlib','./mylib.v')                        "]
    }

    cfg['libext'] = {
        'switch' : '+libext',
        'switch_args' : '<ext>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Verilog Module Search File Extensions',
        'help' : ["Specifes the file extensions that should be used for     ",
                  "finding modules. For example, if -y is specified as ./lib",
                  "and '.v' is specified as libext then the files ./lib/*.v ",
                  "will be searched for module matches.                     ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: +libext+sv                                          ",
                  "api: chip.add('vlib','sv')                               "]
    }

    cfg['cmdfile'] = {
        'switch' : '-f',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Verilog Command Line Options File',
        'help' : ["Read the specified file, and act as if all text inside   ",
                  "it was specified as command line parameters. Supported   ",
                  "by most verilog simulators including Icarus and Verilator",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -f readscript.cmd                                   ",
                  "api: chip.set('cmdfile','readscript.cmd')                "]
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
        'help' : ["Specifies the target stackup to use in the design. The   ",
                  "name must match a value defined in the pdk_stackup list. ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -stackup '2MA4MB2MC'                                ",
                  "api: chip.set('stackup', '2MA4MB2MC')                    "]
    }

    # 1. Automatic floorplanning
    cfg['density'] = {
        'switch' : '-density',
        'switch_args' : '<num>',
        'type' : ['int'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Target Core Density',
        'help' : ["Provides a target density based on the total design cell ",
                  "area reported after synthesis. This number is used when  ",
                  "no die size or floorplan is supplied. Any number between ",
                  "1 and 100 is legal, but values above 50 may fail due to  ",
                  "area/congestion issues during apr.                       ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -density 30                                         ",
                  "api: chip.set('density', '30')                           "]
    }

    cfg['coremargin'] = {
        'switch' : '-coremargin',
        'switch_args' : '<num>',
        'type' : ['float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Place and Route Core Margin',
        'help' : ["Sets the halo/margin between the apr core cell area to   ",
                  "use for automated floorplanning setup. The value is      ",
                  "specified in microns and is only used when no diesize or ",
                  "floorplan is supplied.                                   ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -coremargin 1                                       ",
                  "api: chip.set('coremargin', '1')                         "]
    }

    cfg['aspectratio'] = {
        'switch' : '-aspectratio',
        'switch_args' : '<num>',
        'type' : ['float'],
        'requirement' : 'optional',
        'defvalue' : ['1'],
        'short_help' : 'Design Layout Aspect Ratio',
        'help' : ["Specifies the height to width ratio of the block for     ",
                  "automated floor-planning. Values below 0.1 and above 10  ",
                  "should be avoided as they will likely fail to converge   ",
                  "during placement and routing. The ideal aspect ratiio for",
                  "most designs is 1.                                       ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -aspectratio 2.0                                    ",
                  "api:  chip.set('aspectratio', '2.0')                     "]
    }

    # 2. Spec driven floorplanning
    cfg['diesize'] = {
        'switch' : '-diesize',
        'switch_args' : '<>',
        'type' : ['float', 'float', 'float', 'float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Target Die Size',
        'help' : ["Provides the outer boundary of the physical design. The  ",
                  "number is provided as a tuple (x0 y0 x1 y1), where x0, y0",
                  "species the lower left corner of the block and x1, y1    ",
                  "specifies the upper right corner. Only rectangular       ",
                  "blocks are supported with the diesize parameter. All     ",
                  "values are specified in microns.                         ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -diesize '0 0 100 100'                              ",
                  "api:  chip.set('diesize', '0 0 100 100')                 "]
    }

    cfg['coresize'] = {
        'switch' : '-coresize',
        'switch_args' : '<>',
        'type' : ['float', 'float', 'float', 'float'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Target Core Size',
        'help' : ["Provides the core cell boundary for place and route.The  ",
                  "number is provided as a tuple (x0 y0 x1 y1), where x0,y0 ",
                  "species the lower left corner of the block and x1,y1     ",
                  "specifies the upper right corner of. Only rectangular    ",
                  "blocks are supported with the diesize parameter. All     ",
                  "values are specified in microns.                         ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -coresize '0 0 90 90'                               ",
                  "api:  chip.set('coresize', '0 0 90 90')                  "]
    }

    # 3. Parameterized floorplanning
    cfg['floorplan'] = {
        'switch' : '-floorplan',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Floorplanning Script',
        'help' : ["Provides a parameterized floorplan to be used during the ",
                  "floorplan stage of compilation to generate a fixed DEF   ",
                  "ready for use by the place stage.                        ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -floorplan 'myplan.py'                              ",
                  "api:  chip.add('floorplan', 'myplan.py')                 "]
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
        'help' : ["Provides a hard coded DEF file to be used during the     ",
                  "place stage. The DEF file should be complete and have all",
                  "the features needed to enable cell placement             ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -def 'myplan.def'                                   ",
                  "api:  chip.add('def', 'myplan.def')                      "]
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
        'help' : ["Provides a string name for choosing a physical mapping   ",
                  "target for the design. Like in compilers like gcc, only  ",
                  "targets that are pre-baked into the compiler supported.  ",
                  "Custom targets can be configured through a combination   ",
                  "of command line switches and config files. The target    ",
                  "parameter is included for convenience, enabling cool     ",
                  "single line commands like sc -target asap hello_world.v  ",
                  "Specifying the target parameter causes a number of PDK   ",
                  "PDK and library variables to be set automatically set    ",
                  "based on he specific target specified. Currently, the    ",
                  "following native targets are supported:                  ",
                  "                                                         ",
                  "asap7: Virtual 7nm PDK with multiple VT libraries        ",
                  "freepdk45: Virtual 45nm PDK with a single VT library     ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -target 'freepdk45'                                 ",
                  "api:  chip.set('target', 'freepdk45')                    "]
    }

    cfg['target_lib'] = {
        'switch' : '-target_lib',
        'switch_args' : '<str>',
        'type' : ['string'],
        'defvalue' : [],
        'requirement' : 'apr',
        'short_help' : 'Target Libraries',
        'help' : ["Provides a list of library names to use for synthesis    ",
                  "and automated place and route.                           ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -target_lib 'asap7sc7p5t_lvt'                       ",
                  "api:  chip.add('target_lib', 'asap7sc7p5t_lvt')          "]
    }

    cfg['delaymodel'] = {
        'switch' : '-delaymodel',
        'switch_args' : '<str>',
        'type' : ['string'],
        'defvalue' : [],
        'requirement' : 'apr',
        'short_help' : 'Target Library Delay Model',
        'help' : ["Specifies the delay model to use for the target libs.    ",
                  "Supported values are nldm and ccs.                       ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -delaymodel 'nldm'                                  ",
                  "api:  chip.set('delaymodel', 'nldm')                     "]
    }

    # custom pass through variables
    cfg['custom'] = {
        'switch' : '-custom',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Custom Pass Through Parameters',
        'help' : ["Specifies a custom variable to pass through directly to  ",
                  "the EDA run scripts. The value is a space separated      ",
                  "string with the first value indicating the variable and  ",
                  "the remaining strings assigned as a list.                ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -custom 'SYNMODE lowpower'                          ",
                  "api:  chip.add('custom', 'SYNMODE lowpower')             "]
    }

    #optimization priority
    cfg['effort'] = {
        'switch' : '-effort',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : ['high'],
        'short_help' : 'Compilation Effort',
        'help' : ["Specifies the effort for the synthesis and place and     ",
                  "route efforts. Supported values are low, medium , high.  ",
                  "The default effort is set to high,                       ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -effort 'high'                                      ",
                  "api:  chip.set('effort', 'high')                         "]
    }

    cfg['priority'] = {
        'switch' : '-priority',
        'switch_args' : '<str>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : ['timing'],
        'short_help' : 'Optimization Priority',
        'help' : ["An optional parameter for tools that support tiered      ",
                  "optimization functions. For example, congestion might    ",
                  "be assigned higher priority than timing in some stages.  ",
                  "The optimization priority string must match the EDA tool ",
                  "value exactly.                                           ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -priority 'timing'                                  ",
                  "api:  chip.set('priority', 'timing')                     "]
    }

    cfg['ndr'] = {
        'switch' : '-ndr',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Non-default Net Routing File',
        'help' : ["A file containing a list of nets with non-default width  ",
                  "and spacing, with one net per line and no wildcards      ",
                  "The format is <netname width space>                      ",
                  "The netname should include the full hierarchy from the   ",
                  "root module while width space should be specified in the ",
                  "resolution specified in the technology file.             ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -priority 'myndr.txt'                               ",
                  "api:  chip.add('ndr', 'myndr.txt')                       "]
    }

    cfg['minlayer'] = {
        'switch' : '-minlayer',
        'switch_args' : '<num>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Minimum routing layer',
        'help' : ["The minimum layer to be used for automated place and    ",
                  "route. The layer can be supplied as an integer with 1   ",
                  "specifying the first routing layer in the apr_techfile. ",
                  "Alternatively the layer can be a string that matches    ",
                  "a layer hardcoded in the pdk_aprtech file. Designers    ",
                  "wishing to use the same setup across multiple process   ",
                  "nodes should use the integer approach. For processes    ",
                  "with ambigous starting routing layers, exact strings    ",
                  "should be used.                                         ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -minlayer '2'                                      ",
                  "api:  chip.add('minlayer', '2')                         "]
    }

    cfg['maxlayer'] = {
        'switch' : '-maxlayer',
        'switch_args' : '<num>',
        'type' : ['string'],
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Maximum Routing Layer',
        'help' : ["The maximum layer to be used for automated place and    ",
                  "route. The layer can be supplied as an integer with 1   ",
                  "specifying the first routing layer in the apr_techfile. ",
                  "Alternatively the layer can be a string that matches    ",
                  "a layer hardcoded in the pdk_aprtech file. Designers    ",
                  "wishing to use the same setup across multiple process   ",
                  "nodes should use the integer approach. For processes    ",
                  "with ambigous starting routing layers, exact strings    ",
                  "should be used.                                         ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -maxlayer 6                                        ",
                  "api:  chip.add('maxlayer', '6')                         "]
    }

    cfg['maxfanout'] = {
        'switch' : '-maxfanout',
        'switch_args' : '<num>',
        'type' : ['int'],
        'requirement' : 'apr',
        'defvalue' : ['64'],
        'short_help' : 'Maximum fanout',
        'help' : ["A max fanout rule to be applied during synthesis and    ",
                  "apr. The value has a default of 64.                     ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -maxfanout 32                                      ",
                  "api:  chip.add('maxfanout', '32')                       "]
    }

    cfg['vcd'] = {
        'switch' : '-vcd',
        'switch_args' : '<file>',
        'type' : ['file'],
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'short_help' : 'Value Change Dump File',
        'help' : ["A digital simulation trace that can be used to model    ",
                  "the peak and average power consumption of a design.     ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -vcd mytrace.vcd                                   ",
                  "api:  chip.add('vcd', 'mytrace.vcd')                    "]
    }

    return cfg

############################################
# Constraints
#############################################

def schema_constraints(cfg):

    cfg['mcmm'] = {}

    cfg['mcmm']['default'] = {}

    cfg['mcmm']['default']['libcorner'] = {
        'switch' : '-mcmm_libcorner',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM Library Corner Name',
        'help' : ["A dynamic dictionary that connects the scenario name with",
                  "a library corner name that can be used to access the     ",
                  "'stdcells' library timing models of the 'target_libs'    ",
                  "The 'libcorner' value must match the corner specified in ",
                  "the 'stdcells' dictionary exactly. The format for the    ",
                  "dictionary ia [scenarioname]['libcorner'].               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -mcmm_libcorner 'worst ttt'                         ",
                  "api: chip.set('mcmm','worst', 'ttt)                      "]
    }

    cfg['mcmm']['default']['pexcorner'] = {
        'switch' : '-mcmm_pexcorner',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM PEX Corner Name',
        'help' : ["A dynamic dictionary that connects the scenario name with",
                  "a RC extraction corner name that can be used to access   ",
                  "the 'pdd_pexmodel' models. The 'pexcorner' value must    ",
                  "match the value 'stdcells' dictionary exactly. The format",
                  "for the dictionary ia [scenarioname]['pexcorner'].       ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -mcmm_pexcorner ' worst max'                        ",
                  "api: chip.set('mcmm','worst','pexcorner, 'max')          "]
    }

    cfg['mcmm']['default']['mode'] = {
        'switch' : '-mcmm_mode',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM Mode Name',
        'help' : ["A dynamic dictionary that connects the scenario name with",
                  "a named mode that can be used to drive analys.           ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -mcmm_mode 'worst test'                             ",
                  "api: chip.set('mcmm','worst','mode', 'test')             "]
    }

    cfg['mcmm']['default']['constraint'] = {
        'switch' : '-mcmm_constraint',
        'switch_args' : '<>',
        'type' : ['file'],
        'requirement' : 'optional',
        'hash' : [],
        'defvalue' : [],
        'short_help' : 'MCMM Timing Constraints Files',
        'help' : ["Provides scenario specific constraints. If none are     ",
                  "supplied default constraints are generated based on     ",
                  "the clk parameter. The constraints can be applied on    ",
                  "per stage basis to allow for tightening margins as      ",
                  "the design gets more refined through he apr flow        ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -mcmm_constraints 'worst hello_world.sdc'          ",
                  "api: chip.add('mcmm','worst', 'constraint',             ",
                  "              'hello_world.sdc')                        "]
    }

    cfg['mcmm']['default']['goal'] = {
        'switch' : '-mcmm_goal',
        'switch_args' : '<>',
        'type' : ['string'],
        'requirement' : 'apr',
        'defvalue' : [],
        'short_help' : 'MCMM Goals',
        'help' : ["Provides target goals for a scenario aligned with the  ",
                  "optimization capabilities of the synthesis and apr     ",
                  "tool. Goals generally include objectives like meeting  ",
                  "setup and hold goals and minimize power.               ",
                  "                                                       ",
                  "Examples:                                              ",
                  "cli: -mcmm_goal 'worst goal setup'                     ",
                  "api: chip.add('mcmm','worst', 'goal', 'setup'          "]
    }

    return cfg

###############################################
# Network Configuration for Remote Compute Jobs
###############################################

def schema_net(cfg):

    # Remote IP address/host name running sc-server app
    cfg['remote'] = {
        'switch': '-remote',
        'switch_args' : '<str>',
        'type' : ['string'],
        'defvalue' : [],
        'short_help' : 'Remote server (https://acme.com:8080)',
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
        'short_help': 'Hostname or IP address for shared storage.',
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
