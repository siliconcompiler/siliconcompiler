# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import re
import os
import textwrap
import sys

###############################################################################
# CHIP CONFIGURATION
###############################################################################
def schema_cfg():
    '''Method for defining Chip configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    cfg = {}

    # Flow Setup (from schema_options)
    cfg = schema_flow(cfg, 'default')

    # Metric Tracking
    cfg = schema_metrics(cfg, 'goal', 'default')
    cfg = schema_metrics(cfg, 'real', 'default')    
 
    # FPGA Parameters
    cfg = schema_fpga(cfg)

    # ASIC Parameters
    cfg = schema_pdk(cfg)
    cfg = schema_asic(cfg) 
    cfg = schema_libs(cfg, 'stdcell')
    cfg = schema_libs(cfg, 'macro')

    # Designer's Choice
    cfg = schema_design(cfg)
    cfg = schema_mcmm(cfg)
    
    # Designer Run options
    cfg = schema_options(cfg)

    # Run status
    cfg = schema_status(cfg)

    return cfg

###############################################################################
# CHIP LAYOUT
###############################################################################
def schema_layout():
    
    layout = {}

    layout = schema_lef(layout)

    layout = schema_def(layout)

    return layout

###############################################################################
# UTILITY FUNCTIONS TIED TO SC SPECIFICATIONS
###############################################################################

def schema_path(filename):
    ''' Resolves file paths using SCPATH and resolve environment variables
    starting with $
    '''

    #Resolve absolute path usign SCPATH
    #list is read left to right    
    scpaths = str(os.environ['SCPATH']).split(':')
    for searchdir in scpaths:        
        abspath = searchdir + "/" + filename
        if os.path.exists(abspath):
            filename = abspath
            break
    #Replace $ Variables
    varmatch = re.match('^\$(\w+)(.*)', filename)
    if varmatch:
        var = varmatch.group(1)
        varpath = os.getenv(var)
        if varpath is None:
            print("FATAL ERROR: Missing environment variable:", var)
            sys.exit()
        relpath = varmatch.group(2)
        filename = varpath + relpath

    #Check Path Validity
    if not os.path.exists(filename):
        print("FATAL ERROR: File/Dir not found:", filename)
        sys.exit()
        
    return filename
            
def schema_istrue(value):
    ''' Checks schema boolean string and returns Python True/False
    '''
    boolean = value[-1].lower()
    if boolean == "true":
        return True
    else:
        return False

    
###############################################################################
# FPGA
###############################################################################

def schema_fpga(cfg):
    ''' FPGA Setup
    '''
    cfg['fpga'] = {}

    cfg['fpga']['xml'] = {
        'switch' : '-fpga_xml',
        'requirement' : 'fpga',
        'type' : ['file'],
        'defvalue' : [],
        'short_help' : 'FPGA Architecture File',
        'param_help' : "'fpga' 'xml' <file>",
        'help' : """
        Provides an XML-based architecture description for the target FPGA
        architecture to be used in VTR, allowing targeting a large number of 
        virtual and commercial architectures.
        [More information...](https://verilogtorouting.org)
        
        Examples:
        cli: -fpga_xml myfpga.xml
        api:  chip.set('fpga', 'xml', 'myfpga.xml')
        """
    }

    cfg['fpga']['vendor'] = {
        'switch' : '-fpga_vendor',
        'requirement' : '!fpga_xml',
        'type' : ['str'],
        'defvalue' : [],
        'short_help' : 'FPGA Vendor Name',
        'param_help' : "'fpga' 'vendor' <str>",
        'help' : """
        Name of the FPGA vendor for non-VTR based compilation
        
        Examples:
        cli: -fpga_vendor acme
        api:  chip.set('fpga', 'vendor', 'acme')
        """
    }

    cfg['fpga']['device'] = {
        'switch' : '-fpga_device',
        'requirement' : '!fpga_xml',
        'type' : ['str'],
        'defvalue' : [],
        'short_help' : 'FPGA Device Name',
        'param_help' : "'fpga' 'device' <str>",
        'help' : """
        Name of the FPGA device for non-VTR based compilation
                                                                        
        Examples:
        cli: -fpga_device fpga64k
        api:  chip.set('fpga', 'device', 'fpga64k')
        """        
    }

    return cfg

###############################################################################
# PDK
###############################################################################

def schema_pdk(cfg):
    ''' Process Design Kit Setup
    '''
    cfg['pdk'] = {}
    cfg['pdk']['foundry'] = {
        'switch' : '-pdk_foundry',
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'Foundry Name',
        'param_help' : "'pdk' 'foundry' <str>",
        'help' : """
        The name of the foundry. For example: intel, gf, tsmc, "samsung, 
        skywater, virtual. The \'virtual\' keyword is reserved for simulated 
        non-manufacturable processes such as freepdk45 and asap7.              
        
        Examples:                                                
        cli: -pdk_foundry virtual
        api:  chip.set('pdk', 'foundry', 'virtual')
        """
    }

    cfg['pdk']['process'] = {
        'switch' : '-pdk_process',
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'Process Name',
        'param_help' : "'pdk' 'process' <str>",
        'help' : """
        The official public name of the foundry process. The name is case 
        insensitive, but should otherwise match the complete public process 
        name from the foundry. Example process names include 22ffl from Intel,
        12lpplus from Globalfoundries, and 16ffc from TSMC.        

        Examples:
        cli: -pdk_process asap7
        api:  chip.set('pdk', 'process', 'asap7')
        """
    }

    cfg['pdk']['node'] = {
        'switch' : '-pdk_node',
        'requirement' : 'asic',
        'type' : ['num'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'Process Node',
        'param_help' : "'pdk' 'node' <num>",
        'help' : """
        An approximate relative minimum dimension of the process node. A 
        required parameter in some reference flows that leverage the value to 
        drive technology dependent synthesis and APR optimization. Node 
        examples include 180nm, 130nm, 90nm, 65nm, 45nm, 32nm, 22nm, 14nm, 
        10nm, 7nm, 5nm, 3nm. The value entered implies nanometers.

        Examples:
        cli: -pdk_node 130
        api:  chip.set('pdk', 'node', '130')
        """
    }

    cfg['pdk']['rev'] = {
        'switch' : '-pdk_rev',
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'Process Revision',
        'param_help' : "'pdk' 'rev' <str>",
        'help' : """
        An alphanumeric string specifying the revision  of the current PDK. 
        Verification of correct PDK and IP revisions revisions is an ASIC 
        tapeout requirement in all commercial foundries.

        Examples:
        cli: -pdk_rev 1.0
        api:  chip.set('pdk', 'rev', '1.0')
        """
    }
    
    cfg['pdk']['drm'] = {
        'switch' : '-pdk_drm',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],        
        'short_help' : 'PDK Design Rule Manual',
        'param_help' : "'pdk' 'drm' <file>",
        'help' : """
        A PDK document that includes complete information about physical and 
        electrical design rules to comply with in the design and layout of the 
        chip. In cases where the user guides and design rules are combined into
        a single document, the pdk_doc parameter can be left blank.

        Examples:
        cli: -pdk_drm asap7_drm.pdf
        api:  chip.set('pdk_drm', 'asap7_drm.pdf')
        """
    }

    cfg['pdk']['doc'] = {
        'switch' : '-pdk_doc',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'PDK Documents',
        'param_help' : "'pdk' 'doc' <file>",
        'help' : """
        A list of critical PDK designer documents provided by the foundry 
        entered in order of priority. The first item in the list should be the
        primary PDK user guide. The purpose of the list is to serve as a 
        central record for all must-read PDK documents.
        
        Examples:
        cli: -pdk_doc asap7_userguide.pdf
        api:  chip.add('pdk_doc', 'asap7_userguide.pdf')
        """
    }
        
    cfg['pdk']['stackup'] = {
        'switch' : '-pdk_stackup',
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'Process Metal Stackups',
        'param_help' : "'pdk' 'stackup' <str>",
        'help' : """
        A list of all metal stackups offered in the process node. Older process
        nodes may only offer a single metal stackup, while advanced nodes 
        offer a large but finite list of metal stacks with varying combinations
        of metal line pitches and thicknesses. Stackup naming is unqiue to a 
        foundry, but is generally a long string or code. For example, a 10 
        metal stackup two 1x wide, four 2x wide, and 4x wide metals, might be
        identified as 2MA4MB2MC. Each stackup will come with its own set of 
        routing technology files and parasitic models specified in the 
        pdk_pexmodel and pdk_aprtech parameters.
        
        Examples:
        cli: -pdk_stackup 2MA4MB2MC
        api:  chip.add('pdk_stackup', '2MA4MB2MC')
        """        
    }

    cfg['pdk']['devicemodel'] = {}
    cfg['pdk']['devicemodel']['default'] = {}
    cfg['pdk']['devicemodel']['default']['default'] = {}
    cfg['pdk']['devicemodel']['default']['default']['default'] = {
        'switch' : '-pdk_devicemodel',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Device Models',
        'param_help' : "'pdk' 'devicemodel' stackup type tool <file>",
        'help' : """
        Filepaths for all PDK device models. The structure serves as a central 
        access registry for models for different purpose and tools. Examples of
        device model types include spice, aging, electromigration, radiation. 
        An example of a spice tool is xyce.

        Examples:                                                
        cli: -pdk_devmodel '2MA4MB2MC spice xyce asap7.sp'
        api: chip.add('pdk_devmodel','2MA4MB2MC','spice','xyce','asap7.sp')
        """
    }

    cfg['pdk']['pexmodel'] = {}
    cfg['pdk']['pexmodel']['default'] = {}
    cfg['pdk']['pexmodel']['default']['default']= {}
    cfg['pdk']['pexmodel']['default']['default']['default'] = {
        'switch' : '-pdk_pexmodel',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Parasitic TCAD Models',
        'param_help' : "'pdk' 'pexmodel' stackup corner tool <file>",
        'help' : """
        Filepaths for all PDK wire TCAD models. The structure serves as a 
        central access registry for models for different purpose and tools. 
        Examples of RC extraction corners include: min, max, nominal. An 
        example of an extraction tool is FastCap.
        
        Examples:
        cli: -pdk_pexmodel '2MA4MB2MC max fastcap wire.mod'
        api: chip.add('pdk_pexmodel','2MA4MB2MC','max','fastcap', 'wire.mod')
        """
    }

    cfg['pdk']['layermap'] = {}
    cfg['pdk']['layermap']['default'] = {}
    cfg['pdk']['layermap']['default']['default'] = {}
    cfg['pdk']['layermap']['default']['default']['default'] = {
        'switch' : '-pdk_layermap',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Mask Layer Maps',
        'param_help' : "'pdk' 'layermap' stackup src dst <file>",
        'help' : """
        Files describing input/output mapping for streaming layout data from 
        one format to another. A foundry PDK will include an official layer 
        list for all user entered and generated layers supported in the GDS 
        accepted by the foundry for processing, but there is no standardized 
        layer definition format that can be read and written by all EDA tools.
        To ensure mask layer matching, key/value type mapping files are needed
        to convert EDA databases to/from GDS and to convert between different
        types of EDA databases.
        
        Examples:                                                
        cli: -pdk_layermap '2MA4MB2MC klayout gds asap7.map'
        api: chip.add('pdk','layermap','2MA4MB2MC','klayout','gds','asap7.map')
        """
    }

    cfg['pdk']['display'] = {}
    cfg['pdk']['display']['default'] = {}
    cfg['pdk']['display']['default']['default'] = {
        'switch' : '-pdk_display',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Display Configurations',
        'param_help' : "'pdk' 'display' stackup tool <file>",
        'help' : """
        Display configuration files describing colors and pattern schemes for
        all layers in the PDK. The display configuration file is entered on a 
        stackup and per tool basis.

        Examples:
        cli: -pdk_display '2MA4MB2MC klayout display.cfg'
        api: chip.add('pdk', display','2MA4MB2MC','klayout', display.cfg')
        """
    }

    cfg['pdk']['plib'] = {}
    cfg['pdk']['plib']['default'] = {}
    cfg['pdk']['plib']['default']['default'] = {
        'switch' : '-pdk_plib',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Primitive Libraries',
        'param_help' : "'pdk' 'plib' stackup format <file>",
        'help' : """
        Filepaths to all primitive cell libraries supported by the PDK. The 
        filepaths are entered on a per stackup and per format basis.
        
        Examples:
        cli: -pdk_plib '2MA4MB2MC oa /disk/asap7/oa/devlib'
        api: chip.add('pdk','plib','2MA4MB2MC','oa', '/disk/asap7/oa/devlib')
        """
    }

    cfg['pdk']['aprtech'] = {}
    cfg['pdk']['aprtech']['default'] = {}
    cfg['pdk']['aprtech']['default']['default'] = {}
    cfg['pdk']['aprtech']['default']['default']['default'] = {
        'switch' : '-pdk_aprtech',
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'APR Technology File',
        'param_help' : "'pdk' 'aprtech' stackup libtype vendor <file>",        
        'help' : """
        Technology file containing the design rule and setup information needed
        to enable DRC clean automated placement a routing. The file is 
        specified on a per stackup, libtype, and format basis, where libtype 
        generates the library architecture (e.g. library height). For example a
        PDK with support for 9 and 12 track libraries might have libtypes 
        called 9t and 12t.
        
        Examples:                                               
        cli: -pdk_aprtech '2MA4MB2MC 12t openroad tech.lef'
        api: chip.add('pdk','aprtech','2MA4MB2MC','12t','openroad','tech.lef')
        """
    }

    cfg['pdk']['aprlayer'] = {}
    cfg['pdk']['aprlayer']['default'] = {}
    cfg['pdk']['aprlayer']['default']['default'] = {}    
     
    cfg['pdk']['aprlayer'] = {}
    cfg['pdk']['aprlayer']['default'] = {}
    cfg['pdk']['aprlayer']['default']['default'] = {}

    cfg['pdk']['aprlayer']['default']['default']['name'] = {
        'switch' : '-pdk_aprlayer_name',
        'requirement' : 'optional',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'APR Layer Preferred Direction',
        'param_help' : "'pdk' 'aprlayer' stackup metal 'xpitch'",
        'help' : """
        Defines the hardcoded PDK metal name ona on a per stackup and 
        per metal basis. Metal layers are specifed from m1 to mN.
        
        Examples:
        cli: -pdk_aprlayer_xpitch '2MA4MB2MC m1 0.5'
        api: chip.add('pdk', 'aprlayer', '2MA4MB2MC', 'm1', 'xpitch', '0.5')
        """
    }
    
    cfg['pdk']['aprlayer']['default']['default']['xpitch'] = {
        'switch' : '-pdk_aprlayer_xpitch',
        'requirement' : 'optional',
        'type' : ['num'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'APR Layer Preferred Direction',
        'param_help' : "'pdk' 'aprlayer' stackup metal 'xpitch'",
        'help' : """
        Defines the horizontal minimum pitch of a metal layer specified 
        on a per stackup and per metal basis. Values are specified in um.
        Metal layers are specifed from m1 to mN.
        
        Examples:
        cli: -pdk_aprlayer_xpitch '2MA4MB2MC m1 0.5'
        api: chip.add('pdk', 'aprlayer', '2MA4MB2MC', 'm1', 'xpitch', '0.5')
        """
    }

    cfg['pdk']['aprlayer']['default']['default']['ypitch'] = {
        'switch' : '-pdk_aprlayer_ypitch',
        'requirement' : 'optional',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'APR Layer Preferred Direction',
        'param_help' : "'pdk' 'aprlayer' stackup metal 'ypitch'",
        'help' : """
        Defines the vertical minimum pitch of a metal layer specified 
        on a per stackup and per metal basis. Values are specified in um.
        Metal layers are specifed from m1 to mN.

        Examples:
        cli: -pdk_aprlayer_ypitch '2MA4MB2MC m1 0.5'
        api: chip.add('pdk', 'aprlayer', '2MA4MB2MC', 'm1', 'ypitch', '0.5')
        """
    }

    cfg['pdk']['aprlayer']['default']['default']['xoffset'] = {
        'switch' : '-pdk_aprlayer_xoffset',
        'requirement' : 'optional',
        'type' : ['num'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'APR Layer Preferred Direction',
        'param_help' : "'pdk' 'aprlayer' stackup metal 'xoffset'",
        'help' : """
        Defines the horizontal wire track offset of a metal layer specified 
        on a per stackup and per metal basis. Values are specified in um.
        
        Examples:
        cli: -pdk_aprlayer_xoffset '2MA4MB2MC m1 0.5'
        api: chip.add('pdk', 'aprlayer', '2MA4MB2MC', 'm1', 'xoffset', '0.5')
        """
    }

    cfg['pdk']['aprlayer']['default']['default']['yoffset'] = {
        'switch' : '-pdk_aprlayer_yoffset',
        'requirement' : 'optional',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'APR Layer Preferred Direction',
        'param_help' : "'pdk' 'aprlayer' stackup metal 'yoffset'",
        'help' : """
        Defines the vertical wire track offset of a metal layer specified 
        on a per stackup and per metal basis. Values are specified in um.

        Examples:
        cli: -pdk_aprlayer_yoffset '2MA4MB2MC m1 0.5'
        api: chip.add('pdk', 'aprlayer', '2MA4MB2MC', 'm1', 'yoffset', '0.5')
        """
    }
    
    cfg['pdk']['tapmax'] = {
        'switch' : '-pdk_tapmax',
        'requirement' : 'apr',
        'type' : ['num'],
        'lock' : 'false',
        'defvalue' : [], 
        'short_help' : 'Tap Cell Max Distance Rule',
        'param_help' : "'pdk' 'tapmax' <num>",
        'help' : """
        Maximum distance allowed between tap cells in the PDK. The value is 
        required for automated place and route and is entered in micrometers.
        
        Examples:
        cli: -pdk_tapmax 100
        api: chip.set('pdk_tapmax','100')
        """
    }

    cfg['pdk']['tapoffset'] = {
        'switch' : '-pdk_tapoffset',
        'requirement' : 'apr',
        'type' : ['num'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'Tap Cell Offset Rule',
        'param_help' : "'pdk' 'tapoffset' <num>",
        'help' : """
        Offset from the edge of the block to the tap cell grid. The value is 
        required for automated place and route and is entered in micrometers.

        Examples:      
        cli: -pdk_tapoffset 0
        api: chip.set('pdk','tapoffset','0')
        """
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
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' :  group.capitalize() + ' Release Revision',
        'param_help' : "'"+group+"' libname 'rev' <str>",
        'help' :
        "String specifying revision on a per library basis.Verification of   "\
        "correct PDK and IP revisions is an ASIC tapeout requirement in all  "\
        "commercial foundries.                                               "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_rev 'mylib 1.0'                                     "\
        "api: chip.set('"+group+"','mylib','rev','1.0')                      "
    }

    cfg[group]['default']['origin'] = {
        'switch' : '-'+group+'_origin',
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' :  group.capitalize() + ' Origin',
        'param_help' : "'"+group+"' libname 'origin' <str>",
        'help' :
        "String specifying library origin.                                   "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_origin 'mylib US'                                   "\
        "api: chip.set('"+group+"','mylib','origin','US')                    "
    }

    cfg[group]['default']['license'] = {
        'switch' : '-'+group+'_license',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' :  group.capitalize() + ' License File',
        'param_help' : "'"+group+"' libname 'license' <file>",
        'help' :
        "Filepath to library license                                         "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_license 'mylib ./LICENSE'                           "\
        "api: chip.add('"+group+"', 'mylib','license','./LICENSE')           "
    }
    
    cfg[group]['default']['doc'] = {
        'switch' : '-'+group+'_doc',
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' :  group.capitalize() + ' Documentation',
        'param_help' : "'"+group+"' libname 'doc' <file>",
        'help' :
        "A list of critical library documents entered in order of importance."\
        "The first item in thelist should be the primary library user guide. "\
        "The purpose of the list is to serve as a central record for all     "\
        "must-read PDK documents                                             "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_doc 'mylib mylib_guide.pdf'                         "\
        "api: chip.add('"+group+"','mylib','doc', 'mylib_guide.pdf'          "
    }

    cfg[group]['default']['datasheet'] = {
        'switch' : '-'+group+"_datasheet",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' Datasheets',
        'param_help' : "'"+group+"' libname 'datasheet' <file>",
        'help' :
        "A complete collection of library datasheets. The documentation can  "\
        "be provied as a PDF or as a filepath to a directory with one HTMl   "\
        "file per cell. This parameter is optional for libraries where the   "\
        "datsheet is merged within the library integration document.         "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_datasheet 'mylib mylib_ds.pdf'                      "\
        "api: chip.add('"+group+"','mylib','datasheet','mylib_ds.pdf')       "
    }

    cfg[group]['default']['libtype'] = {
        'switch' : '-'+group+'_libtype',
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Type',
        'param_help' : "'"+group+"' libname 'libtype' <str>",
        'help' :
        "Libtype is a a unique string that identifies the row height or      "\
        "performance class of the library for APR. The libtype must match up "\
        "with the name used in the pdk_aprtech dictionary. Mixing of libtypes"\
        "in a flat place and route block is not allowed.                     "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_libtype 'mylib 12t'                                 "\
        "api: chip.set('"+group+"','mylib','libtype','12t')                  "
    }

    cfg[group]['default']['width'] = {
        'switch' : '-'+group+'_width',
        'requirement' : 'apr',
        'type' : ['num'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Width',
        'param_help' : "'"+group+"' libname 'width' <num>",
        'help' :
        "Specifies the width of a unit cell. The value can usually be         "\
        "extracted automatically from the layout library but is included in   "\
        "the schema to simplify the process of creating parametrized          "\
        "floorplans.                                                          "\
        "                                                                     "\
        "Examples:                                                            "\
        "cli: -"+group+"_width 'mylib 0.1'                                    "\
        "api: chip.set('"+group+"','mylib','width','0.1')                     "
    }

    cfg[group]['default']['height'] = {
        'switch' : '-'+group+'_height',
        'requirement' : 'apr',
        'type' : ['num'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Height',
        'param_help' : "'"+group+"' libname 'height' <num>",
        'help' :
        "Specifies the height of a library unit cell or macro. The value can  "\
        "usually be extracted automatically from the layout library but is    "\
        "included in the schema to simplify the process of creating           "\
        "parametrized floorplans.                                             "\
        "                                                                     "\
        "Examples:                                                            "\
        "cli: -"+group+"_height 'mylib 0.1'                                   "\
        "api: chip.set('"+group+"','mylib','height','0.1')                    "
    }
    
    ###############################
    #Models (Timing, Power, Noise)
    ###############################

    cfg[group]['default']['model'] = {}
    cfg[group]['default']['model']['default'] = {}

    #Operating Conditions (per corner)
    cfg[group]['default']['model']['default']['opcond'] = {
        'switch' : '-'+group+"_opcond",
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Operating Condition',
        'param_help' : "'"+group+"' libname 'model' corner 'opcond' <str>",
        'help' :
        "The default operating condition to use for mcmm optimization and    "\
        "signoff on a per corner basis.                                      "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_opcond 'mylib model ss_1.0v_125c WORST'             "\
        "api: chip.add('"+group+"','mylib', 'model', 'ss_1.0v_125c',         "\
        "               'opcond', 'WORST')                                   "
    }
        
    #Checks To Do (per corner)
    cfg[group]['default']['model']['default']['check'] = {
        'switch' : '-'+group+"_check",
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Corner Checks',
        'param_help' : "'"+group+"' libname 'model' corner 'check' <str>",
        'help' :
        "Per corner checks to perform during optimization and STA signoff.   "\
        "Names used in the 'mcmm' scenarios must align with the 'check' names"\
        "used in this dictionary. The purpose of the dictionary is to serve  "\
        "as a serve as a central record for the PDK/Library recommended      "\
        "corner methodology and all PVT timing corners supported. Standard   "\
        'check' "values include setup, hold, power, noise, reliability but   "\
        "can be extended based on eda support and methodology.               "\
        "                                                                    "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_check 'mylib model ss_1.0v_125c setup'              "\
        "api: chip.add('"+group+"','mylib','model', 'ss_1.0v_125c','check',  "\
        "               'setup')                                             "
    }
        
    #NLDM
    cfg[group]['default']['model']['default']['nldm'] = {}
    cfg[group]['default']['model']['default']['nldm']['default'] = {        
        'switch' : '-'+group+"_nldm",
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' NLDM Timing Model',
        'param_help' : "'"+group+"' libname 'model' corner 'nldm' type <file>",
        'help' :
        "Filepaths to NLDM models. Timing files are specified on a per lib,  "\
        "per corner, and per format basis. The format is driven by EDA tool  "\
        "requirements. Examples of legal formats includ: lib, lib.gz,        "\
        "lib.bz2, and ldb.                                                   "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_nldm 'mylib model tt lib mylib_tt.lib'              "\
        "api: chip.add('"+group+"','mylib', 'model', 'tt','nldm','lib',      "\
        "              'mylib_tt.lib')                                       "
    }

    #CCS
    cfg[group]['default']['model']['default']['ccs'] = {}
    cfg[group]['default']['model']['default']['ccs']['default'] = {        
        'switch' : '-'+group+"_ccs",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' CCS Timing Model',
        'param_help' : "'"+group+"' libname 'model' corner 'ccs' type <file>",
        'help' :
        "Filepaths to CCS models. Timing files are specified on a per lib,   "\
        "per corner, and per format basis. The format is driven by EDA tool  "\
        "requirements. Examples of legal formats includ: lib,lib.gz,lib.bz2, "\
        "and ldb.                                                            "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_ccs 'mylib model tt lib mylib_tt.lib'               "\
        "api: chip.add('"+group+"','mylib', 'model', 'tt','ccs','lib',       "\
        "              'mylib_tt.lib')                                       "
    }

    #SCM
    cfg[group]['default']['model']['default']['scm'] = {}
    cfg[group]['default']['model']['default']['scm']['default'] = {        
        'switch' : '-'+group+"_scm",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' SCM Timing Model',
        'param_help' : "'"+group+"' libname 'model' corner 'scm' type <file>",
        'help' :
        "Filepaths to SCM timing models. Timing files are specified on a per "\
        "lib, per corner, and per format basis. The format is driven by EDA  "\
        "requirements. Examples of legal formats includ: lib,lib.gz,lib.bz2, "\
        "and ldb.                                                            "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_scm 'mylib model tt lib mylib_tt.lib'               "\
        "api: chip.add('"+group+"','mylib', 'model', 'tt','scm','lib',       "\
        "              'mylib_tt.lib')                                       "
    }
    
    #AOCV
    cfg[group]['default']['model']['default']['aocv'] = {        
        'switch' : '-'+group+"_aocv",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' AOCV Timing Model',
        'param_help' : "'"+group+"' libname 'model' corner 'aocv' <file>",
        'help' :
        "Filepaths to AOCV models. Timing files are specified on a per lib   "\
        "and per corner basis.                                               "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_aocv 'mylib model tt mylib_tt.aocv'                 "\
        "api: chip.add('"+group+"','mylib','model', 'tt','aocv',             "\
        "              mylib_tt.aocv')                                       "
    }

    #APL
    cfg[group]['default']['model']['default']['apl'] = {}
    cfg[group]['default']['model']['default']['apl']['default'] = {        
        'switch' : '-'+group+"_apl",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' APL Power Model',
        'param_help' : "'"+group+"' libname 'model' corner 'apl' type <file>",
        'help' :
        "Filepaths to APL power models. Power files are specified on a per   "\
        "lib, per corner, and per format basis                               "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_apl 'mylib model tt mylib_tt.cdev'                  "\
        "api: chip.add('"+group+"','mylib', 'model', 'tt','apl','cdev',      "\
        "               mylib_tt.cdev')                                      " 
    }

    #LEF
    cfg[group]['default']['lef'] = {
        'switch' : '-'+group+"_lef",
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' LEF',
        'param_help' : "'"+group+"' libname 'lef' <file>",
        'help' :
        "An abstracted view of library cells that gives a complete           "\
        "description of the cell's place and route boundary, pin positions,  "\
        "pin metals, and                                                     "\
        "metal routing blockages.                                            "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_lef 'mylib mylib.lef'                               "\
        "api: chip.add('"+group+"','mylib','lef','mylib.lef')                "
    }

    #GDS
    cfg[group]['default']['gds'] = {
        'switch' : '-'+group+"_gds",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' GDS',
        'param_help' : "'"+group+"' libname 'gds' <file>",
        'help' :
        "The complete mask layout of the library cells ready to be merged    "\
        "with the rest of the design for tapeout. In some cases, the GDS     "\
        "merge happens at the foundry, so inclusion of CDL files is optional."\
        "In all cases, where the CDL are available they should specified here"\
        "to enable LVS checks pre tapout                                     "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_gds 'mylib mylib.gds'                               "\
        "api: chip.add('"+group+"','mylib','gds','mylib.gds'                 "
    }

    cfg[group]['default']['cdl'] = {
        'switch' : '-'+group+"_cdl",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' CDL Netlist',
        'param_help' : "'"+group+"' libname 'cdl' <file>",
        'help' :
        "Files containing the netlists used for layout versus schematic (LVS)"\
        "checks. In some cases, the GDS merge happens at the foundry, so     "\
        "inclusion of a CDL file is optional. In all cases, where the CDL    "\
        "files are available they should specified here to enable LVS checks "\
        "pre tapout                                                          "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_cdl 'mylib mylib.cdl'                               "\
        "api: chip.add('"+group+"','mylib','cdl','mylib.cdl'                 "
    }

    cfg[group]['default']['spice'] = {
        'switch' : '-'+group+"_spice",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' Spice Netlist',
        'param_help' : "'"+group+"' libname 'spice' <file>",
        'help' :
        "Files containing the library spice netlists used for circuit        "\
        "simulation.                                                         "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_spice 'mylib mylib.sp'                              "\
        "api: chip.add('"+group+"','mylib','spice','mylib.sp'                "
    }

    cfg[group]['default']['hdl'] = {
        'switch' : '-'+group+"_hdl",
        'requirement' : 'asic',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' HDL Model',
        'param_help' : "'"+group+"' libname 'hdl' <file>",
        'help' :
        "Digital HDL models of the library cells, modeled in VHDL or verilog "\
        "for use in funcational simulations.                                 "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_hdl 'mylib mylib.v'                                 "\
        "api: chip.add('"+group+"','mylib','hdl','mylib.v'                   "
    }
    
    cfg[group]['default']['atpg'] = {
        'switch' : '-'+group+"_atpg",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' ATPG Model',
        'param_help' : "'"+group+"' libname 'atpg' <file>",
        'help' :
        "Library models used for ATPG based automated faultd based post      "\
        "manufacturing testing.                                              "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_atpg 'mylib mylib.atpg'                             "\
        "api: chip.add('"+group+"','mylib','atpg','mylib.atpg')              "
    }

    cfg[group]['default']['pgmetal'] = {
        'switch' : '-'+group+"_pgmetal",
        'requirement' : 'optional',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Power/Ground Layer',
        'param_help' : "'"+group+"' libname 'pgmetal' <str>",
        'help' :
        "Specifies the top metal layer used for power and ground routing     "\
        "within the library. The parameter can be used to guide cell power   "\
        "grid hookup by APR tools.                                           "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_pgmetal 'mylib m1'                                  "\
        "api: chip.add('"+group+"','mylib','pgmetal','m1')                   "
    }

    cfg[group]['default']['tag'] = {
        'switch' : '-'+group+"_tag",
        'requirement' : 'optional',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Identifier Tags',
        'param_help' : "'"+group+"' libname 'tag' <str>",
        'help' :
        "Marks a library with a set of tags that can be used by the designer "\
        "and EDA tools for optimization purposes. The tags are meant to cover"\
        "features not currently supported by built in EDA optimization flows,"\
        "but which can be queried through EDA tool TCL commands and lists.   "\
        "The example below demonstrates tagging the whole library as virtual."\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_tag 'mylib virtual'                                 "\
        "api: chip.add('"+group+"','mylib','tag','virtual')                  "
    }

    cfg[group]['default']['driver'] = {
        'switch' : '-'+group+"_driver",
        'switch_args' : '<>',
        'requirement' : 'asic',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Default Driver Cell',
        'param_help' : "'"+group+"' libname 'driver' <str>",
        'help' :
        "The name of a library cell to be used as the default driver for     "\
        "block timing constraints. The cell should be strong enough to drive "\
        "a block input from another block including wire capacitance.        "\
        "In cases where the actual driver is known, the actual driver cell   "\
        "should be used.                                                     "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_driver 'mylib BUFX1'                                "\
        "api: chip.add('"+group+"','mylib','driver','BUFX1')                 "
    }

    cfg[group]['default']['site'] = {
        'switch' : '-'+group+"_site",
        'requirement' : 'optional',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Site/Tile Name',
        'param_help' : "'"+group+"' libname 'site' <str>",
        'help' :
        "Provides the primary site name to use for placement.                "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_site 'mylib mylibsc7p5'                             "\
        "api: chip.add('"+group+"','mylib','site','mylibsc7p5')              "
    }

    cfg[group]['default']['cells'] = {}
    cfg[group]['default']['cells']['default'] = {
        'switch' : '-'+group+"_cells",
        'requirement' : 'optional',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : group.capitalize() + ' Cell Lists',
        'param_help' : "'"+group+"' libname 'cells' celltype <str>",
        'help' :
        "A named list of cells grouped by a property that can be accessed    "\
        "directly by the designer and EDA tools. The example below shows how "\
        "all cells containing the string 'eco' could be marked as dont use   "\
        "for the tool.                                                       "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_cells 'mylib dontuse *eco*'                         "\
        "api: chip.add('"+group+"','mylib','cells','dontuse','*eco*')        "\
    }

    cfg[group]['default']['layoutdb'] = {}
    cfg[group]['default']['layoutdb']['default'] = {}
    cfg[group]['default']['layoutdb']['default']['default'] = {
        'switch' : '-'+group+"_layoutdb",
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : group.capitalize() + ' Layout Database',
        'param_help' : "'"+group+"' libname 'layoutdb' stackup type <file>",
        'help' :
        "Filepaths to compiled library layout database specified on a per    "\
        "format basis. Example formats include oa, mw, ndm.                  "\
        "                                                                    "\
        "Examples:                                                           "\
        "cli: -"+group+"_layoutdb 'mylib 2MA4MB2MC oa /disk/myliblibdb'      "\
        "api: chip.add('"+group+"','mylib','layoutdb','2MA4MB2MC','oa', '/disk/mylibdb')    "
    }

    return cfg

###############################################################################
# Flow Configuration
###############################################################################

def schema_flow(cfg, step):

    if not 'flow' in cfg:
        cfg['flow'] = {}    
    cfg['flow'][step] = {}

    
    # Used to define flow sequence
    cfg['flow'][step]['input'] = {
        'switch' : '-flow_input',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Excution Dependency',
        'param_help' : "'flow' step 'input' <str>",
        'help' : """
        Specifies the a list of inputs that gate the execution start for
        'step'.

        Examples:
        cli: -flow_input 'cts place'
        "api: chip.set('flow', 'cts', 'input', 'place')
        """
    }

    # exe
    cfg['flow'][step]['exe'] = {
        'switch' : '-flow_exe',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Executable Name',
        'param_help' : "'flow' step 'exe' <str>",
        'help' : """
        The name of the exuctable step or the full path to the executable 
        specified on a per step basis.

        Examples:
        cli: -flow_exe 'place openroad'
        "api:  chip.set('flow', 'place', 'exe', 'openroad')
        """
    }
    
    # exe version    
    cfg['flow'][step]['version'] = {
        'switch' : '-flow_version',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Executable Version',
        'param_help' : "'flow' step 'version' <str>",
        'help' : """
        The version of the exuctable step to use in compilation.Mismatch 
        between the step specifed and the step avalable results in an error.

        Examples:
        cli: -flow_version 'place 1.0'
        api:  chip.set('flow', 'place', 'version', '1.0')
        """
    }
    
    #opt
    cfg['flow'][step]['option'] = {
        'switch' : '-flow_opt',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Executable Options',
        'param_help' : "'flow' step 'option' <str>",
        'help' : """
        A list of command line options for the executable. For multiple 
        argument options, enter each argument and value as a one list entry, 
        specified on a per step basis. Command line values must be enclosed in 
        quotes.
        
        Examples:
        cli: -flow_option 'place -no_init'
        api:  chip.add('flow', 'place', 'option', '-no_init')
        """
    }
    
    #refdir
    cfg['flow'][step]['refdir'] = {
        'switch' : '-flow_refdir',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Reference Directory',
        'param_help' : "'flow' step 'refdir' <file>",
        'help' : """
        A path to a directory containing compilation scripts used by the 
        executable specified on a per step basis.

        Examples:
        cli: -flow_refdir 'place ./myrefdir'
        api: chip.set('flow', 'place', 'refdir', './myrefdir')
        """
    }
    
    #entry point script
    cfg['flow'][step]['script'] = {
        'switch' : '-flow_script',
        'requirement' : 'optional',
        'type' : ['file'],
        'lock' : 'false',
        'defvalue' : [],
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],   
        'short_help' : 'Entry Point script',
        'param_help' : "'flow' step 'script' <file>",
        'help' : """
        Path to the entry point compilation script called by the executable 
        specified on a per step basis.

        Examples:
        cli: -step_script 'place ./myrefdir/place.tcl'
        api: chip.set(group,'place','refdir', './myrefdir/place.tcl')
        """
    }

    #copy
    cfg['flow'][step]['copy'] = {
        'switch' : '-flow_copy',
        'type' : ['bool'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Copy Local Option',
        'param_help' : "'flow' step 'copy' <bool>",
        'help' : """
        Specifies that the reference script directory should be copied and run 
        from the local run directory. The option specified on a per step basis.

        Examples:
        cli: -flow_copy 'place true'
        api: chip.set('flow','place','copy','true')
        """
    }
    
    #script format
    cfg['flow'][step]['format'] = {
        'switch' : '-flow_format',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Script Format',
        'param_help' : "'flow' step 'format' <str>",
        'help' : """
        Specifies that format of the configuration file for the step. Valid 
        formats are tcl, yaml, json, cmdline. The format used is dictated by 
        the executable for the step and specified on a per step basis.

        Examples:
        cli: -flow_format 'place tcl'
        api: chip.set('flow','place','format','tcl')
        """
    }
    
    #parallelism
    cfg['flow'][step]['threads'] = {
        'switch' : '-flow_threads',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Job Parallelism',
        'param_help' : "'flow' step 'threads' <num>",
        'help' : """
        Specifies the level of CPU thread parallelism to enable on a per step
        basis.

        Examples:
        cli: -flow_threads 'drc 64'
        api: chip.set('flow', 'drc', 'threads', '64')
        """
    }
    
    #cache
    cfg['flow'][step]['cache'] = {
        'switch' : '-flow_cache',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],  
        'short_help' : 'Cache Directory Name',
        'param_help' : "'flow' step 'cache' <file>",
        'help' : """
        "Specifies a writeable shared cache directory to be used for storage of 
        processed design and library data. The purpose of caching is to save 
        runtime and disk space in future runs.

        Examples:
        cli: -step_cache 'syn ./disk1/edacache'
        api: chip.set(group,'syn','cache','./disk1/edacache')
        """
    }
    
    #warnings
    cfg['flow'][step]['warningoff'] = {
        'switch' : '-flow_warningoff',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Warning Filter',
        'param_help' : "'flow' step 'warningoff' <file>",
        'help' : """
        Specifies a list of EDA warnings for which printing should be supressed.
        Generally this is done on a per design/node bases after review has 
        determined that warning can be safely ignored

        Examples:
        cli: -flow_warnoff 'import COMBDLY'
        api: chip.add('flow', 'import', 'warnoff', 'COMBDLY')
        """
    }
    
    #vendor
    cfg['flow'][step]['vendor'] = {
        'switch' : '-flow_vendor',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Step Vendor',
        'param_help' : "'flow' step 'vendor' <str>",
        'help' : """
        The vendor argument is used for selecting eda specific technology setup
        variables from the PDK and libraries which generally support multiple
        vendors for each implementation step

        Examples:
        cli: -flow_vendor 'place vendor openroad'
        api: chip.set('flow','place','vendor','openroad')
        """
    }

    #signature
    cfg['flow'][step]['signature'] = {
        'switch' : '-flow_signature',
        'requirement' : 'optional',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'Step Signature',
        'param_help' : "'flow' step 'signature' <str>",
        'help' : [
            "A hashed approval signature on a per step basis.        ",
            "                                                         ",
            "Examples:                                                ",
            "cli: -flow_signature 'signoff <str>'                     ",
            "api: chip.set('flow','signoff, 'signature', <str>)       "]
    }        
    
    #date
    cfg['flow'][step]['date'] = {
        'switch' : '-flow_date',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Step Date',
        'param_help' : "'flow' step 'date' <str>",
        'help' : """
        A date stamp on a per step basis updated at runtime in coordination 
        with jobid.

        Examples:
        cli: -flow_date 'date Mon Mar 1 16:12:14 2021'
        api: chip.set('flow','date', 'date','Mon Mar 1 16:12:14 2021')
        """
    }
    
    #author
    cfg['flow'][step]['author'] = {
        'switch' : '-flow_author',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Step Author',
        'param_help' : "'flow' step 'author' <str>",
        'help' : """
        A author record on a per step basis.

        Examples:
        cli: -flow_author 'syn author, wilecoyote@acme.com'
        api: chip.set('flow','syn, 'author', 'wilecoyote@acme.com'
        """
    }

    return cfg

###########################################################################
# Metrics to Track 
###########################################################################

def schema_metrics(cfg, group, step):

    if not group in cfg:
        cfg[group] = {}    

    cfg[group][step] = {}      # per step

    cfg[group][step]['instances'] = {
        'switch' : '-'+group+'_instances',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Total Cell Instances ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'instances' <num>",
        'help' : 
        "Metric tracking the total number of cell instances on a per step"\
        " basis. In the case of FPGAs, the it represents    "\
        "the number of LUTs.                                             "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_instances 'place 1 100'                         "\
        "api: chip.set('"+group+"','place', '1', 'instances', '100')     "
    }    
    
    cfg[group][step]['area'] = {
        'switch' : '-'+group+'_area',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Cell Area ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'area' <num>",
        'help' : 
        "Metric tracking the total cell area on a per step basis"\
        "specified in um^2.                                        "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_area 'place 1 10000'                            "\
        "api: chip.set('"+group+"','place', '1', 'area', '10000')        "
    }

    cfg[group][step]['density'] = {
        'switch' : '-'+group+'_density',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Cell Density ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'density' <num>",
        'help' : 
        "Metric tracking the density calculated as the ratio of cell area"\
        "devided by the total core area available for placement. Value   "\
        "specied as a percentage (%)                                     "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_density 'place 1 50'                            "\
        "api: chip.set('"+group+"','place', '1', 'density', '50')        "
    } 
    
    cfg[group][step]['power'] = {
        'switch' : '-'+group+'_power',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Active Power ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'power' <num>",
        'help' : 
        "Metric tracking the dynamic power of the design on a per step   "\
        "and per jobid basis calculated based on setup config and VCD    "\
        "stimulus. Metric unit is Watts.                                 "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_power 'place 1 0.001'                           "\
        "api: chip.set('"+group+"','place', '1', 'power', '0.001')       "
    }    

    cfg[group][step]['leakage'] = {
        'switch' : '-'+group+'_leakage',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Leakage ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'leakage' <num>",
        'help' : 
        "Metric tracking the leakage of the design on a per step and per "\
        "jobid basis. Calculated based on MCMM setup. Metric unit is     "\
        "Watts.                                                          "\
        "Examples:                                                       "\
        "cli: -"+group+"_power 'place 1 1e-6'                            "\
        "api: chip.set('"+group+"','place', '1','leakage', '1e-6')       "
    }    

    
    cfg[group][step]['hold_tns'] = {
        'switch' : '-'+group+'_hold_tns',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Hold TNS ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'hold_tns' <num>",
        'help' : 
        "Metric tracking the total negative hold slack (TNS) on a per    "\
        "step and per jobid basis. Metric unit is nanoseconds.           "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_hold_tns 'place 1 0'                            "\
        "api: chip.set('"+group+"','place', '1','hold_tns', '0')         "
    }    

    cfg[group][step]['hold_wns'] = {
        'switch' : '-'+group+'_hold_wns',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Hold WNS ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'hold_wns' <num>",
        'help' : 
        "Metric tracking the worst negative hold slack (TNS) on a per    "\
        "step and per jobid basis. Metric unit is nanoseconds.           "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_hold_wns 'place 1 0'                            "\
        "api: chip.set('"+group+"','place','1','hold_wns', '0')          "
    }    

    cfg[group][step]['setup_tns'] = {
        'switch' : '-'+group+'_setup_tns',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Setup TNS ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'setup_tns' <num>",
        'help' : 
        "Metric tracking the total negative setup slack (TNS) on a per   "\
        "step and per jobid basis. Metric unit is nanoseconds.           "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_setup_tns 'place 1 0'                           "\
        "api: chip.set('"+group+"','place','1','setup_tns', '0')         "
    }    

    cfg[group][step]['setup_wns'] = {
        'switch' : '-'+group+'_setup_wns',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Setup WNS ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'setup_wns' <num>",
        'help' : 
        "Metric tracking the worst negative setup slack (TNS) on a per   "\
        "step and per jobid basis. Metric unit is nanoseconds.           "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_setup_wns 'place 1 0'                           "\
        "api: chip.set('"+group+"','place','1','setup_wns','0')          "
    }    

    cfg[group][step]['drv'] = {
        'switch' : '-'+group+'_drv',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Rule Violations ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'drv' <num>",
        'help' : 
        "Metric tracking the total number of design rule violations on a "\
        "per step and per jobid basis.                                   "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_drv 'place 1 0'                                 "\
        "api: chip.set('"+group+"','place','1','drv', '0')               "
    }    

    cfg[group][step]['warnings'] = {
        'switch' : '-'+group+'_warnings',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Total Warnings ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'warnings' <num>",
        'help' : 
        "Metric tracking the total number of warnings on a per and per    "\
        "jobid basis.                                                     "\
        "Examples:                                                        "\
        "cli: -"+group+"_warnings 'place 1 0'                             "\
        "api: chip.set('"+group+"','place','1','warnings', '0')           "
    }
    
    cfg[group][step]['errors'] = {
        'switch' : '-'+group+'_errors',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Total Errors ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'errors' <num>",
        'help' : 
        "Metric tracking the total number of errors on a per step and    "\
        "per jobid basis.                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_errors 'place 1 0'                              "\
        "api: chip.set('"+group+"','place','1','errors', '0')            "
    }

    cfg[group][step]['runtime'] = {
        'switch' : '-'+group+'_runtime',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Total Runtime ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'runtime' <num>",
        'help' : 
        "Metric tracking the total runtime on a per step basis. Time     "\
        "recorded as wall clock time in seconds, with value displayed as "\
        "hr:min:sec                                                      "\
        "                                                                "\
        "Examples:                                                       "\
        "cli: -"+group+"_runtime 'place 1 0'                             "\
        "api: chip.set('"+group+"','place','1','runtime', '0')           "
    }
    
    cfg[group][step]['memory'] = {
        'switch' : '-'+group+'_memory',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Total Memory ' + group.capitalize(),
        'param_help' : "'"+group+"' step 'jobid' 'memory' <num>",
        'help' : 
        "Metric tracking the total memory on a per step and per jobid   "\
        "Value record as bytes, displayed with standard units:          "\
        "K,M,G,T,P,E for Kilo, Mega, Giga, Tera, Peta, Exa              "\
        "basis.                                                         "\
        "Examples:                                                      "\
        "cli: -"+group+"_memory 'place 1 0'                             "\
        "api: chip.set('"+group+"','place','1','memory', '0')           "
    }
    
    return cfg

###########################################################################
# Run Options
###########################################################################

def schema_options(cfg):
    ''' Run-time options
    '''
    
    cfg['mode'] = {
        'switch' : '-mode',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : ['asic'],
        'short_help' : 'Compilation Mode',
        'param_help' : "'mode' <str>",
        'help' : """
        Sets the compilation flow to 'fpga' or 'asic. The default is 'asic'
        
        Examples:
        cli: -mode 'fpga'
        api: chip.set('mode,'fpga')
        """
    }

    cfg['target'] = {
        'switch' : '-target',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['custom'],
        'short_help' : 'Target Platform',
        'param_help' : "'target' <str>",
        'help' : """
        Provides a string name for choosing a physical mapping target for the
        design. The target should be one of the following formats.

        1.) A single word target found in the targetmap list (freepdk45, asap7)
        2.) For ASICs, a quad of format "process_lib_dataflow"
        3.) For FPGAs, a quad of format "device_edaflow"

        Examples:
        cli: -target 'freepdk45'
        api:  chip.set('target', 'freepdk45')
        """
    }

    cfg['steplist'] = {
        'switch' : '-steplist',
        'requirement' : 'all',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'short_help' : 'Compilation Steps List',
        'param_help' : "'steplist' <str>",
        'help' : """
        A complete list of all steps included in the compilation process.
        Compilation flow is controlled with the -start, -stop, -cont switches 
        and by adding values to the list. The list must be ordered to enable 
        default automated compilation from the first entry to the last entry 
        in the list. 

        Examples:
        cli: -steplist 'export'
        api:  chip.add('steplist', 'export')
        """
    }

    cfg['cfg'] = {
        'switch' : '-cfg',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Configuration File',
        'param_help' : "'cfg' <file>",
        'help' : """
        All parameters can be set at the command line, but with over 500 
        configuration parameters possible, the preferred method for non trivial
        use cases is to create a cfg file using the python API. The cfg file 
        can then be passed in through he -cfgfile switch at the command line.
        There  is no restriction on the number of cfg files that can be be 
        passed in. but it should be noted that the cfgfile are appended to the 
        existing list and configuration list.

        Examples:
        cli: -cfg 'mypdk.json'
        api: chip.set('cfg','mypdk.json)
        """
        }

    cfg['env'] = {}
    cfg['env']['default'] = {
        'switch' : '-env',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Environment Variables',
        'param_help' : "'env' varname <str>",
        'help' : """
        Certain EDA tools and reference flows require environment variables to
        be set. These variables can be managed externally or specified through
        the env variable.

        Examples:
        cli: -env 'PDK_HOME /disk/mypdk'
        api: chip.set('env', 'PDK_HOME', /disk/mypdk')
        """
    }

    cfg['scpath'] = {
        'switch' : '-scpath',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Search path',
        'param_help' : "'scpath' <str>",
        'help' : """
        Specifies python modules paths for target import.

        Examples:
        cli: -scpath '/home/$USER/sclib'          
        api: chip.add('scpath,'/home/$USER/sclib')
        """
    }

    cfg['hash'] = {
        'switch' : '-hash',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['NONE'],
        'short_help' : 'Hash Files',
        'param_help' : "'hash' <str>",
        'help' : """
        The switch controls how/if setup files and source files are hashed
        during compilation. Valid entries include NONE, ALL, USED.

        Examples:
        cli: -hash ALL
        api: chip.set('hash','ALL')
        """
    }
    
    cfg['lock'] = {
        'switch' : '-lock',
        'type' : ['bool'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['false'],
        'short_help' : 'Configuration File Lock',
        'param_help' : "'lock' <bool>",
        'help' : """
        The boolean lock switch can be used to prevent unintended updates to the
        chip configuration. For example, a team  might converge on a golden 
        reference methodology and will have a company policy to not allow 
        designers to deviate from that golden reference. After the lock switch 
        has been set, the current configuration is in read only mode until the 
        end of the compilation

        Examples:
        cli: -lock
        api: chip.set('lock','true')
        """
    }

    cfg['quiet'] = {
        'short_help' : 'Quiet Execution Option',
        'switch' : '-quiet',
        'type' : ['bool'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['false'],
        'short_help' : 'Quiet execution',
        'param_help' : "'quiet' <bool>",
        'help' : """
        Modern EDA tools print significant content to the screen. The -quiet 
        option forces all steps to print to a log file. The quiet
        option is ignored when the -noexit is set to true.

        Examples:
        cli: -quiet                                              ",
        api: chip.set('quiet','true')
        """
    }

    cfg['loglevel'] = {
        'switch' : '-loglevel',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['WARNING'],
        'short_help' : 'Logging Level',
        'param_help' : "'loglevel' <str>",
        'help' : """
        The debug param provides explicit control over the level of debug 
        logging printed. Valid entries include INFO, DEBUG, WARNING, ERROR. The
        default value is WARNING.

        Examples:
        cli: -loglevel INFO
        api: chip.set('loglevel','INFO')
        """
    }

    cfg['dir'] = {
        'switch' : '-dir',
        'type' : ['dir'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['build'],
        'short_help' : 'Build Directory',
        'param_help' : "'dir' <dir>",
        'help' : """
        By default, compilation is done in the local './build' directory. The 
        build parameter enables setting an alternate compilation directory path.
        
        Examples:
        cli: -dir './build_the_future'
        api: chip.set('dir','./build_the_future')
        """
    }

    cfg['jobname'] = {
        'switch' : '-jobname',
        'type' : ['dir'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Job Name',
        'param_help' : "'jobname' <dir>",
        'help' : """
        By default, job directories are created inside the 'build' directory in a 
        sequential fashion as follows: job0, job1, job2,...
        The 'jobname' parameters allows user to manually specify a jobname.
        
        Examples:
        cli: -jobname 'may1'
        api: chip.set('jobname', 'may1')
        """
    }

    cfg['start'] = {
        'switch' : '-start',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Compilation Start Step',
        'param_help' : "'start' <str>",
        'help' : """
        The start parameter specifies the starting step of the flow. This would
        generally be the import step but could be any one of the steps within
        the steps parameter. For example, if a previous job was stopped at syn a
        job can be continued from that point by specifying -start place
        
        Examples:
        cli: -start 'place'
        api: chip.set('start','place')
        """
    }

    cfg['stop'] = {
        'switch' : '-stop',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'requirement' : 'optional',
        'short_help' : 'Compilation Stop Step',
        'param_help' : "'stop' <str>",
        'help' : """
        The stop parameter specifies the stopping step of the flow. The value
        entered is inclusive, so if for example the -stop syn is entered, the 
        flow stops after syn has been completed.

        Examples:
        cli: -stop 'route'
        api: chip.set('stop','route')
        """
    }

    cfg['skip'] = {
        'switch' : '-skip',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'requirement' : 'optional',
        'short_help' : 'Compilation Skip Steps',
        'param_help' : "'skip' <str>",
        'help' : """
        In some older technologies it may be possible to skip some of the steps 
        in the standard flow defined. The skip parameter lists the steps to be 
        skipped during execution.

        Examples:
        cli: -skip 'dfm'
        api: chip.set('skip','dfm')
        """
    }

    cfg['skipall'] = {
        'switch' : '-skipall',
        'type' : ['bool'],
        'lock' : 'false',
        'defvalue' : ['false'],
        'requirement' : 'optional',
        'short_help' : 'Skip All Steps',
        'param_help' : "'skipall' <bool>",
        'help' : """
        Skip all steps. Useful for initial bringup.

        Examples:
        cli: -skipall
        api: chip.set('skipall','true')
        """
    }
    
    
    cfg['msgevent'] = {
        'switch' : '-msgevent',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Message Event',
        'param_help' : "'msgevent' <str>",
        'help' : """
        A list of steps after which to notify a recipient. For example if 
        values of syn, place, cts are entered separate messages would be sent 
        after the completion of the syn, place, and cts steps.

        Examples:
        cli: -msgevent 'export'
        api: chip.set('msgevent','export')
        """
    }

    cfg['msgcontact'] = {
        'switch' : '-msgcontact',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Message Contact',
        'param_help' : "'msgcontact' <str>",
        'help' : """
        A list of phone numbers or email addresses to message on a event event
        within the msg_event param.
        
        Examples:
        cli: -msgcontact 'wile.e.coyote@acme.com'
        api: chip.set('msgcontact','wile.e.coyote@acme.com')
        """
    }

    cfg['optmode'] = {
        'switch' : '-O',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['O0'],
        'short_help' : 'Optimization Mode',
        'param_help' : "'optmode' <str>",
        'help' : """
        The compiler has modes to prioritize run time and ppa. Modes include:
        
        (0) = Exploration mode for debugging setup           
        (1) = Higher effort and better PPA than O0           
        (2) = Higher effort and better PPA than O1           
        (3) = Signoff qualtiy. Better PPA and higher run times than O2
        (4) = Experimental highest effort, may be unstable.   
                                                              
        Examples:                                             
        cli: -O3                                              
        api: chip.set('optmode','3')                          
        """
    }
    
    cfg['relax'] = {
        'switch' : '-relax',
        'type' : ['bool'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['false'],
        'short_help' : 'Relaxed RTL Linting',
        'param_help' : "'relax' <bool>",
        'help' : """
        Specifies that tools should be lenient and supress some warnigns that 
        may or may not indicate design issues. The default is to enforce strict
        checks for all steps.
        
        Examples:
        cli: -relax
        api: chip.set('relax','true')
        """
    }

    cfg['clean'] = {
        'switch' : '-clean',
        'type' : ['bool'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['false'],
        'short_help' : 'Keep essential files only',
        'param_help' : "'clean' <bool>",
        'help' : """
        Deletes all non-essential files at the end of each step and creates a 
        'zip' archive of the job folder.
        Examples:
        cli: -clean
        api: chip.set('clean','true')
        """
    }
    
    cfg['noexit'] = {
        'switch' : '-noexit',
        'type' : ['bool'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : ['false'],
        'short_help' : "Disable end of step tool exit",
        'param_help' : "'noexit' <bool>",
        'help' : """
        Disables automatic exit from tool at the end of a step for tools that
        support interactive shells such as synthesis and APR tools.
        Once inside the shell,  the native EDA tool commands are accessible 
        in full.
        Examples:
        cli: -noexit
        api: chip.set('noexit','true')
        """
    }

    # Remote IP address/host name running sc-server app
    cfg['remote'] = {
        'switch': '-remote',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Remote Server Address',
        'param_help' : "'remote' <str>",
        'help' : """
        Dicates that all steps after the compilation step should be executed
        on the remote server specified by the IP address. 

        Examples:
        cli: -remote '192.168.1.100'
        api:  chip.set('remote', '192.168.1.100')
        """
    }
    
    # Port number that the remote host is running 'sc-server' on.
    cfg['remoteport'] = {
        'switch': '-remoteport',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'remote',
        'defvalue' : ['8080'],
        'short_help': 'Remove Server Port',
        'param_help' : "'remoteport' <str>",
        'help' : """
        Sets the server port to be used in communicating with the remote host.

        Examples:
        cli: -remoteport '8080'
        api:  chip.set('rempoteport', '8080')
        """
    }

    # Path to a config file defining multiple remote jobs to run.
    cfg['permutations'] = {
        'switch' : '-permutations',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : "Python file containing configuration generator for parallel runs.",
        'param_help' : "'permutations' <str>",
        'help' : """
        Sets the path to a Python file containing a generator which yields
        multiple configurations of a job to run in parallel. This lets you
        'sweep' various configurations such as die size or clock speed.
        """
    }

    return cfg


############################################
# Runtime status
#############################################

def schema_status(cfg):

    cfg['status'] ={}
    cfg['status']['step'] = {
        'switch' : '-status_step',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Current Compilation Step',
        'param_help' : "'step' <str>",
        'help' : """
        A dynamic variable that keeps track of the current
        name being executed. The variable is managed by the run 
        function and not writable by the user.

        """
    }

    cfg['status']['default'] = { }

      
    cfg['status']['default']['active'] = {
        'switch' : '-status_active',
        'type' : ['bool'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Step Active Indicator',
        'param_help' : "'status' step 'active' <bool>",
        'help' : """
        Status field with boolean indicating step activity.
        true=active/processing, false=inactive/done
        """
        }
        
    return cfg


############################################
# Design Setup
#############################################

def schema_design(cfg):
    ''' Design Sources
    '''

    cfg['source'] = {
        'switch' : 'None',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Design Source Files',
        'param_help' : "'source' <file>",
        'help' : """
        A list of source files to read in for elaboration. The files are read 
        in order from first to last entered. File type is inferred from the 
        file suffix:

        (*.v, *.vh) = Verilog
        (*.sv)      = SystemVerilog
        (*.vhd)     = VHDL

        Examples:
        cli: 'hello_world.v'
        api: chip.add('source','hello_world.v')
        """
    }

    cfg['doc'] = {
        'switch' : '-doc',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Design Documentation',
        'param_help' : "'doc' <file>",
        'help' : """
        A list of design documents. Files are read in order from first to last.

        Examples:
        cli: -doc 'design_spec.pdf'
        api: chip.add('doc','design_spec.pdf')
        """
    }

    cfg['rev'] = {
        'switch' : '-rev',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Design Revision',
        'param_help' : "'rev' <str>",
        'help' : """
        Specifies the revision of the current design.
        Examples:
        cli: -rev '1.0'
        api: chip.add('rev','1.0')
        """
    }

    cfg['license'] = {
        'switch' : '-license',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'all',
        'defvalue' : [],
        'short_help' : 'Design License File',
        'param_help' : "'license' <file>",
        'help' : """
        Filepath to the technology license for currrent design.
        
        Examples:
        cli: -license './LICENSE'
        api: chip.add('license','./LICENSE')
        """
    }
  
    cfg['design'] = {
        'switch' : '-design',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Top Module Name',
        'param_help' : "'design' <str>",
        'help' : """
        Name of the top level design to compile. Required for all designs with
        more than one module.

        Examples:
        cli: -design 'hello_world'
        api: chip.set('design','hello_world')
        """
    }

    cfg['nickname'] = {
        'switch' : '-nickname',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Nickname',
        'param_help' : "'nickname' <str>",
        'help' : """
        An alias for the top level design name. Can be useful when top level 
        designs have long and confusing names. The nickname is used in all 
        output file prefixes.

        Examples:
        cli: -nickname 'top'
        api: chip.set('nickname','top')
        """
    }

    cfg['origin'] = {
        'switch' : '-origin',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Origin',
        'param_help' : "'origin' <str>",
        'help' : """
        Record of design source origin.

        Examples:
        cli: -origin unknown
        api: chip.set('origin','unknown')
        """
    }

    cfg['clock'] = {}
    cfg['clock']['default'] = {}
    
    cfg['clock']['default']['name'] = {
        'switch' : '-clock_name',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Clock Name',
        'param_help' : "'clock' clkpath 'name' <str>",
        'help' : """
        Defines a clock name alias to assign to a clock source.

        Examples:
        cli: -clock_name 'top.pll.clkout clk'
        api: chip.add('clock', 'top.pll.clkout', 'name', 'clk')
        """
    }
    
    cfg['clock'] = {}
    cfg['clock']['default'] = {}
    cfg['clock']['default']['period'] = {
        'switch' : '-clock_period',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Clocks',
        'param_help' : "'clock' clkpath period <num>",
        'help' : """
        Specifies the period for a clock source in nanoseconds

        Examples:
        cli: -clock_period 'clk top.pll.clkout 10.0'
        api: chip.add('clock', 'top.pll.clkout', 'period', '10.0')
        """
    }
    
    cfg['clock']['default']['jitter'] = {
        'switch' : '-clock_jitter',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Clock Jitter',
        'param_help' : "'clock' clkpath 'jitter' <num>",
        'help' : """
        Specifies the jitter for a clock source in nanoseconds.

        Examples:
        cli: -clock_jitter 'top.pll.clkout 0.1'
        api: chip.add('clock','top.pll.clkout', 'jitter', '0.01')
        """
    }

    cfg['supply'] = {}
    cfg['supply']['default'] = {}
            
    cfg['supply']['default']['name'] = {
        'switch' : '-supply_name',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Power Supply Name',
        'param_help' : "'supply' supplypath 'name' <str>",
        'help' : """
        Defines a supply name alias to assign to a power source.
        A power supply source can be a list of block pins or a regulator
        output pin.

        Examples:
        cli: -supply_name 'vdd_0 vdd'
        api: chip.add('supply','vdd_0', 'name', 'vdd')
        """
    }

    cfg['supply']['default']['level'] = {
        'switch' : '-supply_level',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Power Supply Level',
        'param_help' : "'ground' supplypath 'level' <num>",
        'help' : """
        Specifies level in Volts for a power source.

        Examples:
        cli: -supply_level 'vss 0.0'
        api: chip.add('supply','vss', 'level', '0.0')
        """
    }

    cfg['supply']['default']['noise'] = {
        'switch' : '-supply_noise',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Design Power Supply Noise',
        'param_help' : "'ground' supplypath 'noise' <num>",
        'help' : """
        Specifies the noise in Volts for a power source.

        Examples:
        cli: -supply_level 'vss 0.05'
        api: chip.add('supply','vss', 'level', '0.05')
        """
    }
  
    cfg['define'] = {
        'switch' : '-D',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Verilog Preprocessor Symbols',
        'param_help' : "'define' <str>",
        'help' : """
        Sets a preprocessor symbol for verilog source imports.

        Examples:
        cli: -D'CFG_ASIC=1'
        api: chip.add('define','CFG_ASIC=1')
        """
    }

    cfg['ydir'] = {
        'switch' : '-y',
        'type' : ['dir'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Verilog Module Search Paths',
        'param_help' : "'ydir' <dir>",
        'help' : """
        Provides a search paths to look for modules found in the the source 
        list. The import engine will look for modules inside files with the 
        specified +libext+ param suffix

        Examples:
        cli: -y './mylib'
        api: chip.add('ydir','./mylib')
        """
    }

    cfg['idir'] = {
        'switch' : '-I',
        'type' : ['dir'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Verilog Include Search Paths',
        'param_help' : "'idir' <dir>",
        'help' : """
        Provides a search paths to look for files included in the design using
        the `include statement.

        Examples:
        cli: -I'./mylib'
        api: chip.add('idir','./mylib')
        """
    }

    cfg['vlib'] = {
        'switch' : '-v',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Verilog Library',
        'param_help' : "'vlib' <file>",
        'help' : """
        Declares source files to be read in, for which modules are not to be 
        interpreted as root modules.

        Examples:
        cli: -v'./mylib.v'
        api: chip.add('vlib','./mylib.v')
        """
    }

    cfg['libext'] = {
        'switch' : '+libext',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'short_help' : 'Verilog File Extensions',
        'param_help' : "'libext' <str>",
        'help' : """
        Specifes the file extensions that should be used for finding modules. 
        For example, if -y is specified as ./lib", and '.v' is specified as 
        libext then the files ./lib/*.v ", will be searched for module matches.
        
        Examples:
        cli: +libext+sv
        api: chip.add('vlib','sv')
        """
    }

    cfg['cmdfile'] = {
        'switch' : '-f',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Verilog Options File',
        'param_help' : "'cmdfile' <file>",
        'help' : """
        Read the specified file, and act as if all text inside it was specified
        as command line parameters. Supported by most verilog simulators 
        including Icarus and Verilator.

        Examples:
        cli: -f design.f
        api: chip.set('cmdfile','design.f')
        """
    }

    cfg['constraint'] = {
        'switch' : '-constraint',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Design Constraint Files',
        'param_help' : "'constraint' <file>",
        'help' : """
        List of default constraints for the design to use during compilation. 
        Types of constraints include timing (SDC) and pin mappings for FPGAs.
        More than one file can be supplied. Timing constraints are global and 
        sourced in all MCMM scenarios.

        Examples:
        cli: -constaint 'top.sdc'
        api: chip.add('constraint','top.sdc')
        """
    }

    cfg['vcd'] = {
        'switch' : '-vcd',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Value Change Dump File',
        'param_help' : "'vcd' <file>",
        'help' : """
        A digital simulation trace that can be used to model the peak and 
        average power consumption of a design.
        
        Examples:
        cli: -vcd mytrace.vcd
        api:  chip.add('vcd', 'mytrace.vcd')
        """
    }

    cfg['spef'] = {
        'switch' : '-spef',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'SPEF File',
        'param_help' : "'spef' <file>",
        'help' : """
        File containing parastics specified in the Standard Parasitic Exchange
        format. The file is used in signoff static timing analysis and power
        analysis and should be generated by an accurate parasitic extraction
        engine.
        
        Examples:
        cli: -spef mydesign.spef
        api:  chip.add('spef', 'mydesign.spef')
        """
    }

    cfg['sdf'] = {
        'switch' : '-sdf',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'SDF File',
        'param_help' : "'sdf' <file>",
        'help' : """
        File containing timing data in Standard Delay Format (SDF).
        
        Examples:
        cli: -sdf mydesign.sdf
        api:  chip.add('sdf', 'mydesign.sdf')
        """
    }
    
    return cfg

###########################
# ASIC Setup
###########################

def schema_asic(cfg):
    ''' ASIC Automated Place and Route Parameters
    '''

    cfg['asic'] = {}
    
    cfg['asic']['targetlib'] = {
        'switch' : '-asic_targetlib',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'requirement' : 'asic',
        'short_help' : 'Target Libraries',
        'param_help' : "'asic' 'targetlib' <str>",
        'help' : """
        A list of library names to use for synthesis and automated place and 
        route. Names must match up exactly with the library name handle in the 
        'stdcells' dictionary.
        
        Examples:
        cli: -asic_targetlib 'asap7sc7p5t_lvt'
        api:  chip.add('asic, 'targetlib', 'asap7sc7p5t_lvt')
        """
    }

    cfg['asic']['macrolib'] = {
        'switch' : '-asic_macrolib',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'requirement' : 'optional',
        'short_help' : 'Macro Libraries',
        'param_help' : "'asic' 'macrolib' <str>",
        'help' : """
        A list of macro libraries to be linked in during synthesis and place
        and route. Macro libraries are used for resolving instances but are 
        not used as target for automated synthesis.
        
        Examples:
        cli: -asic_macrolib 'sram64x1024'
        api:  chip.add('asic', 'macrolib', 'sram64x1024')
        """
    }
        
    cfg['asic']['delaymodel'] = {
        'switch' : '-asic_delaymodel',
        'type' : ['str'],
        'lock' : 'false',
        'defvalue' : [],
        'requirement' : 'asic',
        'short_help' : 'Library Delay Model',
        'param_help' : "'asic' 'delaymodel' <str>",
        'help' : """
        Specifies the delay model to use for the target libs. Supported values
        are nldm and ccs.

        Examples:
        cli: -asic_delaymodel 'nldm'
        api:  chip.set('asic','delaymodel', 'nldm')
        """
    }
    
    cfg['asic']['ndr'] = {
        'switch' : '-asic_ndr',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : '',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Non-default Routing',
        'param_help' : "'asic' 'ndr' <str>",
        'help' : """
        A file containing a list of nets with non-default width and spacing,
        with one net per line and no wildcards. 
        The file format is: <netname width space>. The netname should include 
        the full hierarchy from the root module while width space should be 
        specified in the resolution specified in the technology file.
        Examples:
        cli: -asic_ndr 'myndr.txt'
        api:  chip.add('asic', 'ndr', 'myndr.txt')
        """
    }

    cfg['asic']['minlayer'] = {
        'switch' : '-asic_minlayer',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'Minimum routing layer',
        'param_help' : "'asic' 'minlayer' <str>",
        'help' : """
        The minimum layer to be used for automated place and route. The layer 
        can be supplied as an integer with 1 specifying the first routing layer
        in the apr_techfile. Alternatively the layer can be a string that 
        matches a layer hardcoded in the pdk_aprtech file. Designers wishing to
        use the same setup across multiple process nodes should use the integer
        approach. For processes with ambigous starting routing layers, exact 
        strings should be used.

        Examples:
        cli: -asic_minlayer '2'
        api:  chip.add('asic', 'minlayer', '2')
        """
    }

    cfg['asic']['maxlayer'] = {
        'switch' : '-maxlayer',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'Maximum Routing Layer',
        'param_help' : "'asic' 'maxlayer' <str>",
        'help' : """
        The maximum layer to be used for automated place and route. The layer 
        can be supplied as an integer with 1 specifying the first routing layer
        in the apr_techfile. Alternatively the layer can be a string that 
        matches a layer hardcoded in the pdk_aprtech file. Designers wishing to
        use the same setup across multiple process nodes should use the integer
        approach. For processes with ambigous starting routing layers, exact 
        strings should be used.

        Examples: 
        cli: -asic_maxlayer 6
        api:  chip.add('asic', 'maxlayer', '6')
        """
    }

    cfg['asic']['maxfanout'] = {
        'switch' : '-asic_maxfanout',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'Maximum Fanout',
        'param_help' : "'asic' 'maxfanout' <str>",
        'help' : """
        A max fanout rule to be applied during synthesis and apr.
        
        Examples:
        cli: -asic_maxfanout 32
        api:  chip.add('asic', 'maxfanout', '32')
        """
    }

    cfg['asic']['stackup'] = {
        'switch' : '-asic_stackup',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'Metal Stackup',
        'param_help' : "'asic' 'stackup' <str>",
        'help' : """
        Specifies the target stackup to use in the design. The stackup name 
        must match a value defined in the pdk_stackup list.

        Examples:
        cli: -asic_stackup '2MA4MB2MC'
        api: chip.set('asic', 'stackup', '2MA4MB2MC')
        """
    }
    
    # For density driven floorplanning
    cfg['asic']['density'] = {
        'switch' : '-asic_density',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : '!diesize',
        'defvalue' : [],
        'short_help' : 'Target Core Density',
        'param_help' : "'asic' 'density' <num>",
        'help' : """"
        Provides a target density based on the total design cell area reported
        after synthesis. This number is used when no die size or floorplan is 
        supplied. Any number between 1 and 100 is legal, but values above 50 
        may fail due to area/congestion issues during apr.

        Examples:
        cli: -asic_density 30
        api: chip.set('asic', 'density', '30')
        """
    }

    cfg['asic']['coremargin'] = {
        'switch' : '-asic_coremargin',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'density',
        'defvalue' : [],
        'short_help' : 'Block Core Margin',
        'param_help' : "'asic' 'coremargin' <num>",
        'help' : """
        Sets the halo/margin between the core area to use for automated 
        floorplanning and the outer core boundary. The value is specified in 
        microns and is only used when no diesize or floorplan is supplied.
        
        Examples:
        cli: -asic_coremargin 1
        api: chip.set('asic', 'coremargin', '1')
        """
    }

    cfg['asic']['aspectratio'] = {
        'switch' : '-asic_aspectratio',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'density',
        'defvalue' : ['1'],
        'short_help' : 'APR Block Aspect Ratio',
        'param_help' : "'asic' 'aspectratio' <num>",
        'help' : """
        Specifies the height to width ratio of the block for  automated 
        floor-planning. Values below 0.1 and above 10 should be avoided as 
        they will likely fail to converge during placement and routing. The 
        ideal aspect ratio for most designs is 1.
        
        Examples:
        cli: -asic_aspectratio 2.0
        api:  chip.set('asic', 'aspectratio', '2.0')
        """
        }

    # For spec driven floorplanning
    cfg['asic']['diesize'] = {
        'switch' : '-asic_diesize',
        'type' : ['num', 'num', 'num', 'num'],
        'lock' : 'false',
        'requirement' : '!density',
        'defvalue' : [],
        'short_help' : 'Target Die Size',
        'param_help' : "'asic' 'diesize' <num num num num>",
        'help' : """
        Provides the outer boundary of the physical design. The number is 
        provided as a tuple (x0 y0 x1 y1), where (x0, y0), specifes the lower 
        left corner of the block and (x1, y1) specifies the upper right corner.
        Only rectangular blocks are supported with the diesize parameter. All
        values are specified in microns.

        Examples:
        cli: -asic_diesize '0 0 100 100'
        api:  chip.set('asic', 'diesize', '0 0 100 100')
        """
    }
    
    cfg['asic']['coresize'] = {
        'switch' : '-asic_coresize',
        'type' : ['num', 'num', 'num', 'num'],
        'lock' : 'false',
        'requirement' : 'diesize',
        'defvalue' : [],
        'short_help' : 'Target Core Size',
        'param_help' : "'asic' 'coresize' <num num num num>",
        'help' : """
        Provides the core cell area of the physical design. The number is 
        provided as a tuple (x0 y0 x1 y1), where (x0, y0), specifes the lower 
        left corner of the block and (x1, y1) specifies the upper right corner.
        Only rectangular blocks are supported with the diesize parameter. For
        advanced geometries and blockages, a floor-plan file should is better.
        All values are specified in microns.

        Examples:
        cli: -asic_coresize '0 0 90 90'
        api:  chip.set('asic', 'coresize', '0 0 90 90')
        """
    }

    # Parameterized floorplanning
    cfg['asic']['floorplan'] = {
        'switch' : '-asic_floorplan',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Floorplanning Script',
        'param_help' : "'asic' 'floorplan' <file>",
        'help' : """
        Provides a parameterized floorplan to be used during the floorplan step
        of compilation to generate a fixed DEF ready for use by the APR tool.
        Supported formats are tcl, py, and def.

        Examples:
        cli: -asic_floorplan 'hello.py'
        api:  chip.add('asic', 'floorplan', 'hello.py')
        """
    }

    # Def file
    cfg['asic']['def'] = {
        'switch' : '-asic_def',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'optional',
        'defvalue' : [],
        'hash'   : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'short_help' : 'Harc coded DEF floorplan',
        'param_help' : "'asic' 'def' <file>",
        'help' : """
        Provides a fixed DEF floorplan to be used during the floorplan step
        and/or initial placement step.

        Examples:
        cli: -asic_def 'hello.def'
        api:  chip.add('asic', 'def', 'hello.def')
        """
    }
    
    

    return cfg

############################################
# Constraints
############################################

def schema_mcmm(cfg):

    cfg['mcmm'] = {}
    cfg['mcmm']['default'] = {}

    cfg['mcmm']['default']['voltage'] = {
        'switch' : '-mcmm_voltage',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'MCMM Voltage',
        'param_help' : "'mcmm' scenario 'voltage' <num>",
        'help' : ["Specifies the on chip primary core operating voltage.    ",
                  "Value specified in Volts.                                ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -mcmm_voltage 'worst 0.9'                           ",
                  "api: chip.set('mcmm','worst','voltage', '0.9')           "]
    }

    cfg['mcmm']['default']['temperature'] = {
        'switch' : '-mcmm_temperature',
        'type' : ['num'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'MCMM Temperature',
        'param_help' : "'mcmm' scenario 'temperature' <num>                 ",
        'help' : ["Specifies the on chip temperature.                       ",
                  "Value specified in degrees Celsius.                      ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -mcmm_temperature 'worst 125'                       ",
                  "api: chip.set('mcmm','worst','temperature', '125')       "]
    }
    
    cfg['mcmm']['default']['libcorner'] = {
        'switch' : '-mcmm_libcorner',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'MCMM Library Corner Name',
        'param_help' : "'mcmm' scenario 'libcorner' <str>",
        'help' : ["A dynamic dictionary that connects the scenario name with",
                  "a library corner name that can be used to access the     ",
                  "'stdcells' library timing models of the 'target_libs'    ",
                  "The 'libcorner' value must match the corner specified in ",
                  "the 'stdcells' dictionary exactly. The format for the    ",
                  "dictionary ia [scenarioname]['libcorner'].               ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -mcmm_libcorner 'worst ttt'                         ",
                  "api: chip.set('mcmm','worst','libcorner', 'ttt)          "]
    }

    cfg['mcmm']['default']['opcond'] = {
        'switch' : '-mcmm_opcond',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'MCMM Operating Condition',
        'param_help' : "'mcmm' scenario 'opcond' <str>",
        'help' : ["A dynamic dictionary that connects the scenario name with",
                  "a operating condition within the 'stdcells' found in the ",
                  "library timing models of the 'target_libs'. The 'opcond' ",
                  "value must match the corner specified in the timing model",
                  "The dictionary format is [scenarioname]['opcond'].       ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -mcmm_opcond 'worst typical_1.0'                    ",
                  "api: chip.set('mcmm', 'worst', 'opcond','typical_1.0')   "]
    }

    
    cfg['mcmm']['default']['pexcorner'] = {
        'switch' : '-mcmm_pexcorner',
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'MCMM PEX Corner Name',
        'param_help' : "'mcmm' scenario 'pexcorner' <str>",
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
        'type' : ['str'],
        'lock' : 'false',
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'MCMM Mode Name',
        'param_help' : "'mcmm' scenario 'mode' <str>",
        'help' : ["A dynamic dictionary that connects the scenario name with",
                  "a named mode that can be used to drive analys.           ",
                  "                                                         ",
                  "Examples:                                                ",
                  "cli: -mcmm_mode 'worst test'                             ",
                  "api: chip.set('mcmm','worst','mode', 'test')             "]
    }

    cfg['mcmm']['default']['constraint'] = {
        'switch' : '-mcmm_constraint',
        'type' : ['file'],
        'lock' : 'false',
        'requirement' : 'asic',
        'hash' : [],
        'date'   : [],
        'author' : [],
        'signature' : [],
        'defvalue' : [],
        'short_help' : 'MCMM Timing Constraints',
        'param_help' : "'mcmm' scenario 'constraint' <str>",
        'help' : ["Provides scenario specific constraints. If none are     ",
                  "supplied default constraints are generated based on     ",
                  "the clk parameter. The constraints can be applied on    ",
                  "per step basis to allow for tightening margins as      ",
                  "the design gets more refined through he apr flow        ",
                  "                                                        ",
                  "Examples:                                               ",
                  "cli: -mcmm_constraints 'worst hello_world.sdc'          ",
                  "api: chip.add('mcmm','worst', 'constraint',             ",
                  "              'hello_world.sdc')                        "]
    }

    cfg['mcmm']['default']['check'] = {
        'switch' : '-mcmm_check',
        'type' : ['str'],
        'lock' : 'false',        
        'requirement' : 'asic',
        'defvalue' : [],
        'short_help' : 'MCMM Checks',
        'param_help' : "'mcmm' scenario 'check' <str>",
        'help' : ["Provides a list of checks for a scenario aligned with  ",
                  "the optimization capabilities of the synthesis and apr ",
                  "tool. Checks generally include objectives like meeting ",
                  "setup and hold goals and minimize power. Standard check",
                  "names include setup, hold, power, noise, reliability   ",
                  "                                                       ",
                  "Examples:                                              ",
                  "cli: -mcmm_check 'worst check setup'                   ",
                  "api: chip.add('mcmm','worst', 'check', 'setup'         "]
    }

    return cfg

###############################################
# LEF/DEF
###############################################

def schema_lef(layout):

    #GLOBAL VARIABLES
    layout["version"] = ""
    layout["busbitchars"] = "[]"
    layout["dividerchar"] = "/"
    layout["units"] = ""
    layout["manufacturinggrid"] = ""

    #SITE
    layout["site"] = {}
    layout["site"]['default'] = {
        'symmetry' : "",
        'class' : "",
        'width' : "",
        'height' : ""
    }
    
    #ROUTING LAYERS
    layout["layer"] = {}
    layout["layer"]['default'] = {
        'number' : "",
        'direction' : "",
        'type' : "",
        'width' : "",
        'pitch' : "",
        'spacing' : "",
        'minwidth' : "",
        'maxwidth' : "",
        'antennaarearatio' : "",
        'antennadiffarearatio'  : ""
    }

    #MACROS
    layout["macro"] = {}
    layout["macro"]['default'] = {
        'class' : "",
        'site' : "",
        'width' : "",
        'height' : "",
        'origin' : "",
        'symmetry' : ""
    }
    layout["macro"]['default']['pin'] = {}
    layout["macro"]['default']['pin']['default'] = {
        'direction' : '',
        'use' : '',
        'shape' : '',
        'port' : []
    }


    return layout

def schema_def(layout):

    #DESIGN
    layout["design"] = []
    
    #DIEAREA
    #Arrray of points, kept as tuple arrray b/c order
    #is critical    
    layout["diearea"] = []
    
    #ROWS
    layout["row"] = {}    
    layout["row"]['default'] = {
        'site' : "",
        'x' : "",
        'y' : "",
        'orientation' : "",
        'numx' : "",
        'numy' : "",
        'stepx' : "",
        'stepy' : ""
    }

    #TRACKS (hidden name)
    layout["track"] = {}
    layout["track"]['default'] = {
        'layer' : "",
        'direction' : "",
        'start' : "",
        'step' : "",
        'total' : ""
    }

    #COMPONENTS (instance name driven)
    layout["component"] ={}
    layout["component"]['default'] = {
        'cell' : "",
        'x' : "",
        'y' : "",
        'status' : "",
        'orientation' : "",
        'halo' : ""
    }

    #VIA
    layout["via"] = {}
    layout["via"]['default'] = {
        'net' : "",
        'special' : "",
        'placement' : "",
        'direction' : "",
        'port' : []
    }

    
    #PINS
    layout["pin"] = {}
    layout["pin"]['default'] = {
        'net' : "",
        'direction' : "",
        'use' : "",
    }
    layout["pin"]['default']['port'] = {}
    layout["pin"]['default']['port']['default'] = {
        'layer' : "",
        'box' : [],
        'status' : "",
        'point' : "",
        'orientation' : "",
     }
    

    #SPECIALNETS
    layout["specialnet"] = {}
    layout["specialnet"]['default'] = {
        'connections' : [],
        'shield' : [],
        'use' : "",
        'fixed' : [],
        'routed' : []
    }

    #NETS
    layout["net"] = {}
    layout["net"]['default'] = {
        'shield' : [],
        'use' : "",
        'fixed' : [],
        'routed' : []
    }
   
    return layout
