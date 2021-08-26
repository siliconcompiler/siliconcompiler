# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import re
import os
import sys

###############################################################################
# CHIP CONFIGURATION
###############################################################################

def schema_cfg():
    '''Method for defining Chip configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    cfg = {}

    # Flow graph Setup
    cfg = schema_flowgraph(cfg)

    # Design Hiearchy
    cfg = schema_hier(cfg)

    # EDA setup
    cfg = schema_eda(cfg)

    # Dyanamic Tool Arguments
    cfg = schema_arg(cfg)

    # Metric tracking
    cfg = schema_metric(cfg)

    # Recording design provenance
    cfg = schema_record(cfg)

    # FPGA parameters
    cfg = schema_fpga(cfg)

    # ASIC parameters
    cfg = schema_pdk(cfg)
    cfg = schema_asic(cfg)

    # Designer's choice
    cfg = schema_design(cfg)
    cfg = schema_mcmm(cfg)

    # Library/Component Definitions
    cfg = schema_libs(cfg)

    # Designer runtime options
    cfg = schema_options(cfg)

    # Remote options
    cfg = schema_remote(cfg)

    return cfg

###############################################################################
# UTILITY FUNCTIONS TIED TO SC SPECIFICATIONS
###############################################################################

def schema_path(filename):
    ''' Resolves file paths using SCPATH and resolve environment variables
    starting with $
    '''

    if filename==None:
        return None

    #Resolve absolute path usign SCPATH
    #list is read left to right
    scpaths = str(os.environ['SCPATH']).split(':')
    for searchdir in scpaths:
        abspath = searchdir + "/" + filename
        if os.path.exists(abspath):
            filename = abspath
            break
    #Replace $ Variables
    varmatch = re.match(r'^\$(\w+)(.*)', filename)
    if varmatch:
        var = varmatch.group(1)
        varpath = os.getenv(var)
        if varpath is None:
            print("ERROR: Missing environment variable:", var)
            sys.exit()
            relpath = varmatch.group(2)
            filename = varpath + relpath

    return filename

def schema_typecheck(chip, cfg, leafkey, value):
    ''' Schema type checking
    '''

    # Check that value is list when type is scalar
    ok = True
    valuetype = type(value)
    if (not re.match(r'\[',cfg['type'])) & (valuetype==list):
        errormsg = "Value must be scalar."
        ok = False
        # Iterate over list
    else:
        # Create list for iteration
        if valuetype == list:
            valuelist = value
        else:
            valuelist = [value]
            # Make type python compatible
        cfgtype = re.sub(r'[\[\]]', '', cfg['type'])
        for item in valuelist:
            valuetype =  type(item)
            if (cfgtype != valuetype.__name__):
                tupletype = re.match(r'\([\w\,]+\)',cfgtype)
                #TODO: check tuples!
                if tupletype:
                    pass
                elif cfgtype == 'bool':
                    if not item in ['true', 'false']:
                        errormsg = "Valid boolean values are True/False/'true'/'false'"
                        ok = False
                elif cfgtype == 'file':
                    pass
                elif cfgtype == 'dir':
                    pass
                elif (cfgtype == 'float'):
                    try:
                        float(item)
                    except:
                        errormsg = "Type mismatch. Cannot cast item to float."
                        ok = False
                elif (cfgtype == 'int'):
                    try:
                        int(item)
                    except:
                        errormsg = "Type mismatch. Cannot cast item to int."
                        ok = False
                else:
                    errormsg = "Type mismach."
                    ok = False
    # Logger message
    if not ok:
        if type(value) == list:
            printvalue = ','.join(map(str, value))
        else:
            printvalue = str(value)
        errormsg = (errormsg +
                    " Key=" + str(leafkey) +
                    ", Expected Type=" + cfg['type'] +
                    ", Entered Type=" + valuetype.__name__ +
                    ", Value=" + printvalue)
        chip.logger.error("%s", errormsg)

    return ok


def schema_reorder(param_help, item):
    ''' Returns a keylist used to access the dictionary based on the
    cmdline switch argument and the param_help field.
    '''
    #Split param help into keys and data based in <>
    m = re.search('(.*?)(<.*)', param_help)
    paramlist = m.group(1).split()
    datalist = m.group(2).split()
    itemlist = item.split()

    depth = len(paramlist)+1
    args = [None] * depth

    #Combine keys from param_help and cmdline field
    j = 0
    for i in range(depth-1):
        if paramlist[i].endswith('var'):
            args[i] = itemlist[j]
            j = j + 1
        else:
            args[i] = paramlist[i]

    #Insert data field as last entry (some are string tuples)
    #ugly, not planning a lot these, keep for now...
    if re.search('float float float float', param_help):
        args[-1] = ' '.join(map(str, itemlist))
    else:
        args[-1] = itemlist[-1]

    return args


###############################################################################
# FPGA
###############################################################################

def schema_fpga(cfg):
    ''' FPGA Setup
    '''
    cfg['fpga'] = {}

    cfg['fpga']['arch'] = {
        'switch': "-fpga_arch <file>",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'FPGA Architecture File',
        'example': ["cli: -fpga_arch myfpga.xml",
                    "api:  chip.set('fpga', 'arch', ['myfpga.xml'])"],
        'help': """
        Architecture definition file for the FPGA place and route tool. In the
        Verilog To Routing case, tjhe file is an XML based description,
        allowing targeting a large number of virtual and commercial
        architectures. `More information... <https://verilogtorouting.org>`_
        """
    }

    cfg['fpga']['vendor'] = {
        'switch': "-fpga_vendor <str>",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'FPGA Vendor Name',
        'example': ["cli: -fpga_vendor acme",
                    "api:  chip.set('fpga', 'vendor', 'acme')"],
        'help': """
        Name of the FPGA vendor. Use to check part name and to select
        the eda tool flow in case 'edaflow' is unspecified.
        """
    }

    cfg['fpga']['partname'] = {
        'switch': "-fpga_partname <str>",
        'requirement': 'fpga',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'FPGA Part Name',
        'example': ["cli: -fpga_partname fpga64k",
                    "api:  chip.set('fpga', 'partname', 'fpga64k')"],
        'help': """
        FPGA part name to target for bit stream generation. The string
        must match the value recognized by the edaflow tools.
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
        'switch': "-pdk_foundry <str>",
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Foundry Name',
        'example': ["cli: -pdk_foundry virtual",
                    "api:  chip.set('pdk', 'foundry', 'virtual')"],
        'help': """
        The official foundry company name. For example: intel, gf, tsmc,
        samsung, skywater, virtual. The \'virtual\' keyword is reserved for
        simulated non-manufacturable processes such as freepdk45 and asap7.
        """
    }

    cfg['pdk']['process'] = {
        'switch': "-pdk_process <str>",
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Name',
        'example': ["cli: -pdk_process asap7",
                    "api:  chip.set('pdk', 'process', 'asap7')"],
        'help': """
        The official public name of the foundry process. The name is case
        insensitive, but should otherwise match the complete public process
        name from the foundry. Example process names include 22ffl from Intel,
        12lpplus from Globalfoundries, and 16ffc from TSMC.
        """
    }

    cfg['pdk']['node'] = {
        'switch': "-pdk_node <float>",
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Node',
        'example': ["cli: -pdk_node 130",
                    "api:  chip.set('pdk', 'node', 130)"],
        'help': """
        Approximate relative minimum dimension of the process target. A
        required parameter in some reference flows that leverage the value to
        drive technology dependent synthesis and APR optimization. Node
        examples include 180nm, 130nm, 90nm, 65nm, 45nm, 32nm, 22nm, 14nm,
        10nm, 7nm, 5nm, 3nm. The value entered implies nanometers.
        """
    }

    cfg['pdk']['wafersize'] = {
        'switch': "-pdk_wafersize <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Wafer Size',
        'example': ["cli: -pdk_wafersize 300",
                    "api:  chip.set('pdk', 'wafersize', 300)"],
        'help': """
        Wafer diameter used in manufacturing specified in mm. The standard
        diameter for leading edge manufacturing is generally 300mm. For older
        process technologies and speciality fabs, smaller diameters such as
        200, 100, 125, 100 are more common. The value is used to calculate
        dies per wafer and full factory chip costs.
        """
    }

    cfg['pdk']['wafercost'] = {
        'switch': "-pdk_wafercost <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Wafer Cost',
        'example': ["cli: -pdk_wafercost 10000",
                    "api:  chip.set('pdk', 'wafercost', 10000)"],
        'help': """
        Raw cost per wafer purchased specified in USD, not accounting for
        yield loss. The values is used to calculate chip full factory costs.
        """
    }

    cfg['pdk']['d0'] = {
        'switch': "-pdk_d0 <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Defect Density',
        'example': ["cli: -pdk_d0 0.1",
                    "api:  chip.set('pdk', 'd0', 0.1)"],
        'help': """
        Process defect density (D0) expressed as random defects per cm^2. The
        value is used to calcuate yield losses as a function of area, which in
        turn affects the chip full factory costs. Two yield models are
        supported: poisson (default), and murphy. The poisson based yield is
        calculated as dy = exp(-area * d0/100). The murphy based yield is
        calculated as dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.
        """
    }

    cfg['pdk']['hscribe'] = {
        'switch': "-pdk_hscribe <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Horizontal Scribeline',
        'example': ["cli: -pdk_hscribe 0.1",
                    "api:  chip.set('pdk', 'hscribe', 0.1)"],
        'help': """
        Width of the horizonotal scribe line (in mm) used during die separation.
        The process is generally complted using a mecanical saw, but can be
        done through combinations of mechanical saws, lasers, wafer thinning,
        and chemical etching in more advanced technolgoies. The value is used
        to calculate effective dies per wafer and full factory cost.
        """
    }

    cfg['pdk']['vscribe'] = {
        'switch': "-pdk_vscribe <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Horizontal Scribeline',
        'example': ["cli: -pdk_vscribe 0.1",
                    "api:  chip.set('pdk', 'vscribe', 0.1)"],
        'help': """
        Width of the vertical scribe line (in mm) used during die separation.
        The process is generally complted using a mecanical saw, but can be
        done through combinations of mechanical saws, lasers, wafer thinning,
        and chemical etching in more advanced technolgoies. The value is used
        to calculate effective dies per wafer and full factory cost.
        """
    }

    cfg['pdk']['edgemargin'] = {
        'switch': "-pdk_edgemargin <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Wafer Edge Margin',
        'example': ["cli: -pdk_edgemargin 1",
                    "api:  chip.set('pdk', 'edgemargin', 1)"],
        'help': """
        Keepout distance/margin (in mm) from the wafer edge prone to chipping
        and poor yield. The value is used to calculate effective dies per
        wafer and full factory cost.
        """
    }

    cfg['pdk']['density'] = {
        'switch': "-pdk_density <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Transistor Density',
        'example': ["cli: -pdk_density 100e6",
                    "api:  chip.set('pdk', 'density', 10e6)"],
        'help': """
        An approximate logic density expressed as # transistors / mm^2
        calculated as:
        0.6 * (Nand2 Transistor Count) / (Nand2 Cell Area) +
        0.4 * (Register Transistor Count) / (Register Cell Area)
        The value is specified for a fixed standard cell library
        within a node and will differ depending on the library vendor,
        library track height and library type. The value is used to
        normalize the effective density reported for the design and to
        enable technology portable floor-plans.
        """
    }

    cfg['pdk']['sramsize'] = {
        'switch': "-pdk_sramsize <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process SRAM Bitcell Size',
        'example': ["cli: -pdk_sramsize 0.032",
                    "api:  chip.set('pdk', 'sramsize', '0.026')"],
        'help': """
        Area of an SRAM bitcell expressed in um^2. The value can be found
        in the PDK and  is used to normalize the effective density reported
        enable technology portable floor-plans.
        """
    }

    cfg['pdk']['version'] = {
        'switch': "-pdk_version <str>",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Version',
        'example': ["cli: -pdk_version 1.0",
                    "api:  chip.set('pdk', 'version', '1.0')"],
        'help': """
        Alphanumeric string specifying the version of the current PDK.
        Verification of correct PDK and IP versionss is an ASIC
        tapeout requirement in all commercial foundries. The value is used
        to for design manifest tracking and tapeout checklists.
        """
    }

    cfg['pdk']['drm'] = {
        'switch': "-pdk_drm <file>",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'PDK Design Rule Manual',
        'example': ["cli: -pdk_drm asap7_drm.pdf",
                    "api:  chip.set('pdk', 'drm', 'asap7_drm.pdf')"],
        'help': """
        PDK document that includes complete information about physical and
        electrical design rules to comply with in the design and layout of the
        chip. In advanced technologies, design rules may be split across
        multiple documents, in which case all files should be listed within
        the drm parameter.
        """
    }

    cfg['pdk']['doc'] = {
        'switch': "-pdk_doc <file>",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'PDK Documents',
        'example': ["cli: -pdk_doc asap7_userguide.pdf",
                    "api: chip.set('pdk', 'doc', 'asap7_userguide.pdf')"],
        'help': """
        A list of critical PDK designer documents provided by the foundry
        entered in order of priority. The first item in the list should be the
        primary PDK user guide. The purpose of the list is to serve as a
        central record for all must-read PDK documents.
        """
    }

    cfg['pdk']['stackup'] = {
        'switch': "-pdk_stackup <str>",
        'requirement': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Process Metal Stackups',
        'example': ["cli: -pdk_stackup 2MA4MB2MC",
                    "api: chip.set('pdk', 'stackup', '2MA4MB2MC')"],
        'help': """
        A list of all metal stackups offered in the process node. Older process
        nodes may only offer a single metal stackup, while advanced nodes
        offer a large but finite list of metal stacks with varying combinations
        of metal line pitches and thicknesses. Stackup naming is unqiue to a
        foundry, but is generally a long string or code. For example, a 10
        metal stackup two 1x wide, four 2x wide, and 4x wide metals, might be
        identified as 2MA4MB2MC. Each stackup will come with its own set of
        routing technology files and parasitic models specified in the
        pdk_pexmodel and pdk_aprtech parameters.
        """
    }

    cfg['pdk']['devicemodel'] = {}
    cfg['pdk']['devicemodel']['default'] = {}
    cfg['pdk']['devicemodel']['default']['default'] = {}
    cfg['pdk']['devicemodel']['default']['default']['default'] = {
        'switch': "-pdk_devicemodel 'stackup simtype tool <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Device Models',
        'example': [
            "cli: -pdk_devicemodel 'M10 spice xyce asap7.sp'",
            "api: chip.set('pdk','devicemodel','M10','spice','xyce','asap7.sp')"],
        'help': """
        Filepaths to PDK device models. The structure serves as a central
        access registry for models for different purpose and tools. Examples of
        device model types include spice, aging, electromigration, radiation.
        An example of a spice tool is xyce. Device models should be specified
        per metal stack basis. Device types and tools are dynamic entries
        that depend on the tool setup and device technology. Pseud-standardized
        device types include spice, em (electromigration), and aging.
        """
    }

    cfg['pdk']['pexmodel'] = {}
    cfg['pdk']['pexmodel']['default'] = {}
    cfg['pdk']['pexmodel']['default']['default'] = {}
    cfg['pdk']['pexmodel']['default']['default']['default'] = {
        'switch': "-pdk_pexmodel 'stackup corner tool <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Parasitic TCAD Models',
        'example': [
            "cli: -pdk_pexmodel 'M10 max fastcap wire.mod'",
            "api: chip.set('pdk','pexmodel','M10','max','fastcap','wire.mod')"],
        'help': """
        Filepaths to PDK wire TCAD models. The structure serves as a
        central access registry for models for different purpose and tools.
        Pexmodels are specified on a per metal stack basis. Corner values
        depend on the process being used, but typically include nomeclature
        such as min, max, nominal. For exact names, refer to the DRM. Pexmodels
        are generally not standardized and specified on a per tool basis.
        """
    }

    cfg['pdk']['layermap'] = {}
    cfg['pdk']['layermap']['default'] = {}
    cfg['pdk']['layermap']['default']['default'] = {}
    cfg['pdk']['layermap']['default']['default']['default'] = {
        'switch': "-pdk_layermap 'stackup src dst <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Mask Layer Maps',
        'example': [
            "cli: -pdk_layermap 'M10 klayout gds asap7.map'",
            "api: chip.set('pdk','layermap','M10','klayout','gds','asap7.map')"],
        'help': """
        Files describing input/output mapping for streaming layout data from
        one format to another. A foundry PDK will include an official layer
        list for all user entered and generated layers supported in the GDS
        accepted by the foundry for processing, but there is no standardized
        layer definition format that can be read and written by all EDA tools.
        To ensure mask layer matching, key/value type mapping files are needed
        to convert EDA databases to/from GDS and to convert between different
        types of EDA databases.
        """
    }

    cfg['pdk']['display'] = {}
    cfg['pdk']['display']['default'] = {}
    cfg['pdk']['display']['default']['default'] = {}
    cfg['pdk']['display']['default']['default']['default'] = {
        'switch': "-pdk_display 'stackup tool format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Display Configurations',
        'example': [
            "cli: -pdk_display 'M10 klayout python display.lyt'",
            "api: chip.set('pdk','display','M10','klayout','python','display.cfg')"],
        'help': """
        Display configuration files describing colors and pattern schemes for
        all layers in the PDK. The display configuration file is entered on a
        stackup, tool, and format basis.
        """
    }

    cfg['pdk']['plib'] = {}
    cfg['pdk']['plib']['default'] = {}
    cfg['pdk']['plib']['default']['default'] = {}
    cfg['pdk']['plib']['default']['default']['default'] = {
        'switch': "-pdk_plib 'stackup tool format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Primitive Libraries',
        'example': [
            "cli: -pdk_plib 'M10 klayout oa ~/devlib'",
            "api: chip.set('pdk','plib','M10','klayout','oa','~/devlib')"],
        'help': """
        Filepaths to all primitive cell libraries supported by the PDK. The
        filepaths are entered on a per stackup, tool,  and format basis.
        The plib cells is the first layer of abstraction encountered above
        the basic device models, and genearally include parametrized
        transistors, resistors, capacitors, inductors, etc.
        """
    }

    cfg['pdk']['aprtech'] = {}
    cfg['pdk']['aprtech']['default'] = {}
    cfg['pdk']['aprtech']['default']['default'] = {}
    cfg['pdk']['aprtech']['default']['default']['default'] = {
        'switch': "-pdk_aprtech 'stackup libarch filetype <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'APR Technology File',
        'example': [
            "cli: -pdk_aprtech 'M10 12t lef tech.lef'",
            "api: chip.set('pdk','aprtech','M10','12t','lef','tech.lef')"],
        'help': """
        Technology file containing the design rule and setup information needed
        to enable DRC clean automated placement a routing. The file is
        specified on a per stackup, libtype, and format basis, where libtype
        generates the library architecture (e.g. library height). For example a
        PDK with support for 9 and 12 track libraries might have libtypes
        called 9t and 12t. The standardized method of specifying place and
        route design rules for a process node is through a LEF format
        technology file.
        """
    }

    cfg['pdk']['grid'] = {}
    cfg['pdk']['grid']['default'] = {}
    cfg['pdk']['grid']['default']['default'] = {}

    #Name Map
    cfg['pdk']['grid']['default']['default']['name'] = {
        'switch': "-pdk_grid_name 'stackup layer <str>'",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Name Map',
        'example': [
            "cli: -pdk_grid_name 'M10 m1 metal1'""",
            "api: chip.set('pdk', 'grid', 'M10', 'm1', 'name', 'metal1')"],
        'help': """
        Map betwen the custom PDK metal names found in the tech,lef and the
        SC standardized metal naming schem that starts with m1 (lowest
        routing layer) and ends with mN (highest routing layer). The map is
        specified on a per metal stack basis.
        """
    }
    # Vertical Grid
    cfg['pdk']['grid']['default']['default']['xpitch'] = {
        'switch': "-pdk_grid_xpitch 'stackup layer <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Horizontal Grid',
        'example': [
            "cli: -pdk_grid_xpitch 'M10 m1 0.5'",
            "api: chip.set('pdk','grid','M10','m1','xpitch', '0.5')"],
        'help': """
        Defines the routing pitch for vertical wires on a per stackup and
        per metal basis. Values are specified in um. Metal layers are ordered
        from m1 to mn, where m1 is the lowest routing layer in the tech.lef.
        """
    }

    # Horizontal Grid
    cfg['pdk']['grid']['default']['default']['ypitch'] = {
        'switch': "-pdk_grid_ypitch 'stackup layer <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Vertical Grid',
        'example': [
            "cli: -pdk_grid_ypitch 'M10 m2 0.5'",
            "api: chip.set('pdk','grid','M10','m2','ypitch', '0.5')"],
        'help': """
        Defines the routing pitch for horizontal wires on a per stackup and
        per metal basis. Values are specified in um. Metal layers are ordered
        from m1 to mn, where m1 is the lowest routing layer in the tech.lef.
        """
    }

    # Vertical Grid Offset
    cfg['pdk']['grid']['default']['default']['xoffset'] = {
        'switch': "-pdk_grid_xoffset 'stackup layer <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Preferred Direction',
        'example': [
            "cli: -pdk_grid_xoffset 'M10 m2 0.5'",
            "api: chip.set('pdk','grid','M10','m2','xoffset','0.5')"],
        'help': """
        Defines the grid offset of a vertical metal layer specified on a per
        stackup and per metal basis. Values are specified in um.
        """
    }

    # Horizontal Grid Offset
    cfg['pdk']['grid']['default']['default']['yoffset'] = {
        'switch': "-pdk_grid_yoffset 'stackup layer <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Preferred Direction',
        'example': [
            "cli: -pdk_grid_yoffset 'M10 m2 0.5'",
            "api: chip.set('pdk','grid','M10','m2','yoffset', '0.5')"],
        'help': """
        Defines the grid offset of a horizontal metal layer specified on a per
        stackup and per metal basis. Values are specified in um.
        """
    }

    # Routing Layer Adjustment
    cfg['pdk']['grid']['default']['default']['adj'] = {
        'switch': "-pdk_grid_adj 'stackup layer <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Routing Adjustment',
        'example': [
            "cli: -pdk_grid_adj 'M10 m2 0.5'",
            "api: chip.set('pdk','grid','M10','m2','adj','0.5')"],
        'help': """
        Defines the routing resources adjustments for the design on a per layer
        basis. The value is expressed as a fraction from 0 to 1. A value of
        0.5 reduces the routing resources by 50%.
        """
    }

    # Routing Layer Capacitance
    cfg['pdk']['grid']['default']['default']['cap'] = {
        'switch': "-pdk_grid_cap 'stackup layer <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Routing Layer Capacitance',
        'example': [
            "cli: -pdk_grid_cap 'M10 m2 0.2'",
            "api: chip.set('pdk','grid','M10','m2','cap','0.2')"],
        'help': """
        Unit capacitance of a wire defined by the grid width and spacing values
        in the 'grid' structure. The value is specifed as ff/um on a per
        stackup and per metal basis. As a rough rule of thumb, this value
        tends to stay around 0.2ff/um. This number should only be used for
        realtiy confirmation. Accurate analysis should use the PEX models.
        """
    }

    # Routing Layer Resistance
    cfg['pdk']['grid']['default']['default']['res'] = {
        'switch': "-pdk_grid_res 'stackup layer <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Routing Layer Resistance',
        'example': [
            "cli: -pdk_grid_res 'M10 m2 0.2'",
            "api: chip.set('pdk','grid','M10','m2','res','0.2')"],
        'help': """
        Resistance of a wire defined by the grid width and spacing values
        in the 'grid' structure.  The value is specifed as ohms/um. The number
        is only meant to be used as a sanity check and for coarse design
        planning. Accurate analysis should use the PEX models.
        """
    }

    # Wire Temperature Coefficient
    cfg['pdk']['grid']['default']['default']['tcr'] = {
        'switch': "-pdk_grid_tcr 'stackup layer <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Temperature Coefficent',
        'example': [
            "cli: -pdk_grid_tcr 'M10 m2 0.1'",
            "api: chip.set('pdk','grid','M10','m2','tcr','0.1')"],
        'help': """
        Temperature coefficient of resistance of the wire defined by the grid
        width and spacing values in the 'grid' structure. The value is specifed
        in %/ deg C. The number is only meant to be used as a sanity check and
        for coarse design planning. Accurate analysis should use the PEX models.
        """
    }

    cfg['pdk']['tapmax'] = {
        'switch': '-pdk_tapmax',
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Tap Cell Max Distance Rule',
        'example': ["""cli: -pdk_tapmax 100""",
                    """api: chip.set('pdk', 'tapmax','100')"""],
        'help': """
        Maximum distance allowed between tap cells in the PDK. The value is
        required for automated place and route and is entered in micrometers.
        """
    }

    cfg['pdk']['tapoffset'] = {
        'switch': "-pdk_tapoffset <float>",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Tap Cell Offset Rule',
        'example': [
            "cli: -pdk_tapoffset 100",
            "api: chip.set('pdk, 'tapoffset','100')"],
        'help': """
        Offset from the edge of the block to the tap cell grid.
        The value is required for automated place and route and is entered in
        micrometers.
        """
    }

    return cfg

###############################################################################
# Library Configuration
###############################################################################

def schema_libs(cfg, lib='default'):

    cfg['library'] = {}
    cfg['library'][lib] = {}

    cfg['library'][lib]['type'] = {
        'switch': "-library_type 'lib <str>'",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Type',
        'example': ["cli: -library_type 'mylib stdcell'",
                    "api: chip.set('library', 'mylib', 'type', 'stdcell')"],
        'help': """
        String specifying the library type. A 'stdcell' type is reserved
        for fixed height stadnard cell libraries used for synthesis and
        place and route. A 'component' type is used for everything else.
        """
    }


    cfg['library'][lib]['testbench'] = {}
    cfg['library'][lib]['testbench']['default'] = {
        'switch': "-library_testbench 'lib simtype <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Testbench',
        'example': ["cli: -library_testbench 'mylib verilog ./mylib_tb.v'",
                    "api: chip.set('library', 'mylib', 'testbench', 'verilog, '/mylib_tb.v')"],
        'help': """
        Path to testbench specified based on a per library and per
        simluation type basis. Typical simulation types include verilog, spice.
        """
    }

    cfg['library'][lib]['version'] = {
        'switch': "-library_version 'lib <str>'",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Version',
        'example': ["cli: -library_version 'mylib 1.0'",
                    "api: chip.set('library','mylib','version','1.0')"],
        'help': """
        String specifying version on a per library basis. Verification of
        correct PDK and IP versions is an ASIC tapeout requirement in all
        commercial foundries.
        """
    }

    cfg['library'][lib]['origin'] = {
        'switch': "-library_origin 'lib <str>'",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Origin',
        'example': ["cli: -library_origin 'mylib US'",
                    "api: chip.set('library','mylib','origin','US')"],
        'help': """
        String specifying library country of origin.
        """
    }

    cfg['library'][lib]['license'] = {
        'switch': "-library_license 'lib <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library License File',
        'example': ["cli: -library_license 'mylib ./LICENSE'",
                    "api: chip.set('library','mylib','license','./LICENSE')"],
        'help': """
        Filepath to library license
        """
    }

    cfg['library'][lib]['doc'] = {
        'switch': "-library_doc 'lib <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Documentation',
        'example': ["cli: -library_doc 'lib lib_guide.pdf'",
                    "api: chip.set('library','lib','doc','lib_guide.pdf')"],
        'help': """
        A list of critical library documents entered in order of importance.
        The first item in thelist should be the primary library user guide.
        The  purpose of the list is to serve as a central record for all
        must-read PDK documents
        """
    }

    cfg['library'][lib]['datasheet'] = {
        'switch': "-library_datasheet 'lib <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Datasheets',
        'example': [
            "cli: -library_datasheet 'lib lib_ds.pdf'",
            "api: chip.set('library','lib','datasheet','lib_ds.pdf')"],
        'help': """
        A complete collection of library datasheets. The documentation can be
        provied as a PDF or as a filepath to a directory with one HTMl file
        per cell. This parameter is optional for libraries where the datsheet
        is merged within the library integration document.
        """
    }

    cfg['library'][lib]['arch'] = {
        'switch': "-library_arch 'lib <str>'",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Type',
        'example': [
            "cli: -library_arch 'mylib 12t'",
            "api: chip.set('library','mylib','arch', '12t')"],
        'help': """
        A unique string that identifies the row height or performance
        class of the library for APR. The arch must match up with the name
        used in the pdk_aprtech dictionary. Mixing of library archs in a flat
        place and route block is not allowed. Examples of library archs include
        6 track libraries, 9 track libraries, 10 track libraries, etc.
        """
    }

    cfg['library'][lib]['width'] = {
        'switch': "-library_width 'lib <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Width',
        'example': ["cli: -library_width 'mylib 0.1'",
                    "api: chip.set('library','mylib','width', '0.1')"],

        'help': """
        Specifies the width of a unit cell. The value can usually be
        extracted automatically from the layout library but is included in the
        schema to simplify the process of creating parametrized floorplans.
        """
    }

    cfg['library'][lib]['height'] = {
        'switch': "-library_height 'lib <float>'",
        'requirement': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Height',
        'example': [
            "cli: -library_height 'mylib 1.0'",
            "api: chip.set('library','mylib','height', '1.0')"],
        'help': """
        Specifies the height of a unit cell. The value can usually be
        extracted automatically from the layout library but is included in the
        schema to simplify the process of creating parametrized floorplans.
        """
    }

    ###############################
    #Models (Timing, Power, Noise)
    ###############################

    cfg['library'][lib]['model'] = {}
    cfg['library'][lib]['model']['default'] = {}

    #Operating Conditions (per corner)
    cfg['library'][lib]['model']['default']['opcond'] = {
        'switch': "-library_opcond 'lib model corner <str>'",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Operating Condition',
        'example': [
            "cli: -library_opcond 'lib model ss_1.0v_125c WORST'",
            "api: chip.set('library','lib','model','ss_1.0v_125c','opcond','WORST')"],
        'help': """
        The default operating condition to use for mcmm optimization and
        signoff on a per corner basis.
        """
    }

    #Checks To Do (per corner)
    cfg['library'][lib]['model']['default']['check'] = {
        'switch': "-library_check 'lib model corner <str>'",
        'requirement': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Library Corner Checks',
        'example': [
            "cli: -library_check 'lib model ss_1.0v_125c setup'",
            "api: chip.set('library','lib','model','ss_1.0v_125c','check','setup')"],
        'help': """
        Per corner checks to perform during optimization and STA signoff.
        Names used in the 'mcmm' scenarios must align with the 'check' names
        used in this dictionary. The purpose of the dictionary is to serve as
        a serve as a central record for the PDK/Library recommended corner
        methodology and all PVT timing corners supported. Standard 'check'
        values include setup, hold, power, noise, reliability but can be
        extended based on eda support and methodology.
        """
    }

    #NLDM
    cfg['library'][lib]['model']['default']['nldm'] = {}
    cfg['library'][lib]['model']['default']['nldm']['default'] = {
        'switch': "-library_nldm 'lib model corner format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library NLDM Timing Model',
        'example': [
            "cli: -library_nldm 'lib model ss gz ss.lib.gz'",
            "api: chip.set('library','lib','model','ss','nldm','gz','ss.lib.gz')"],
        'help': """
        Filepaths to NLDM models. Timing files are specified on a per lib,
        per corner, and per format basis. The format is driven by EDA tool
        requirements. Examples of legal formats includ: lib, gz, bz2,
        and ldb.
        """
    }

    #CCS
    cfg['library'][lib]['model']['default']['ccs'] = {}
    cfg['library'][lib]['model']['default']['ccs']['default'] = {
        'switch': "-library_ccs 'lib model corner format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library CCS Timing Model',
        'example': [
            "cli: -library_ccs 'lib model ss lib.gz ss.lib.gz'",
            "api: chip.set('library','lib','model','ss','ccs','gz','ss.lib.gz')"],
        'help': """
        Filepaths to CCS models. Timing files are specified on a per lib,
        per corner, and per format basis. The format is driven by EDA tool
        requirements. Examples of legal formats includ: lib, gz, bz2,
        and ldb.
        """
    }

    #SCM
    cfg['library'][lib]['model']['default']['scm'] = {}
    cfg['library'][lib]['model']['default']['scm']['default'] = {
        'switch': "-library_scm 'lib model corner format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library SCM Timing Model',
        'example': [
            "cli: -library_scm 'lib model ss lib.gz ss.lib.gz'",
            "api: chip.set('library','lib','model','ss', 'scm','gz','ss.lib.gz')"],
        'help': """
        Filepaths to SCM models. Timing files are specified on a per lib,
        per corner, and per format basis. The format is driven by EDA tool
        requirements. Examples of legal formats includ: lib, gz, bz2,
        and ldb.
        """
    }

    #AOCV
    cfg['library'][lib]['model']['default']['aocv'] = {
        'switch': "-library_aocv 'lib model corner <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library AOCV Timing Model',
        'example': [
            "cli: -library_aocv 'lib model ss lib.aocv'",
            "api: chip.set('library','lib','model','ss','aocv','lib_ss.aocv')"],
        'help': """
        Filepaths to AOCV models. Timing files are specified on a per lib,
        per corner basis.
        """
    }

    #APL
    cfg['library'][lib]['model']['default']['apl'] = {}
    cfg['library'][lib]['model']['default']['apl']['default'] = {
        'switch': "-library_apl 'lib model corner format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library APL Power Model',
        'example': [
            "cli: -library_apl 'lib model ss cdev lib_tt.cdev'",
            "api: chip.set('library','lib','model','ss','apl','cdev','lib_tt.cdev')"],
        'help': """
        Filepaths to APL power models. Power files are specified on a per
        lib, per corner, and per format basis.
        """
    }

    #LEF
    cfg['library'][lib]['lef'] = {
        'switch': "-library_lef 'lib <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library LEF',
        'example': ["cli: -library_lef 'mylib mylib.lef'",
                    "api: chip.set('library','mylib','lef','mylib.lef')"],
        'help': """
        An abstracted view of library cells that gives a complete description
        of the cell's place and route boundary, pin positions, pin metals, and
        metal routing blockages.
        """
    }

    #GDS
    cfg['library'][lib]['gds'] = {
        'switch': "-library_gds 'lib <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library GDS',
        'example': ["cli: -library_gds 'mylib mylib.gds'",
                    "api: chip.set('library','mylib','gds','mylib.gds')"],
        'help': """
        The complete mask layout of the library cells ready to be merged with
        the rest of the design for tapeout. In some cases, the GDS merge
        happens at the foundry, so inclusion of CDL files is optional. In all
        cases, where the CDL are available they should specified here to
        enable LVS checks pre tapout
        """
    }

    cfg['library'][lib]['netlist'] = {
        'switch': "-library_netlist 'lib <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Netlist',
        'example': ["cli: -library_netlist 'mylib mylib.cdl'",
                    "api: chip.set('library','mylib','netlist','mylib.cdl')"],
        'help': """
        Files containing the netlist used for layout versus schematic (LVS)
        checks. For transistor level libraries such as standard cell libraries
        and SRAM macros, this should be a CDL type netlist. For higher level
        modules like place and route blocks, it should be a verilog gate
        level netlist.
        """
    }
    cfg['library'][lib]['spice'] = {}
    cfg['library'][lib]['spice']['default'] = {
        'switch': "-library_spice 'lib format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Spice Netlist',
        'example': ["cli: -library_spice 'mylib pspice mylib.sp'",
                    "api: chip.set('library','mylib','spice', 'pspice',"
                    "'mylib.sp')"],
        'help': """
        Files containing library spice netlists used for circuit
        simulation, specified on a per format basis.
        """
    }
    cfg['library'][lib]['hdl'] = {}
    cfg['library'][lib]['hdl']['default'] = {
        'switch': "-library_hdl 'lib format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library HDL Model',
        'example': ["cli: -library_hdl 'mylib verilog mylib.v'",
                    "api: chip.set('library','mylib','hdl', 'verilog',"
                    "'mylib.v')"],
        'help': """
        Library HDL models, specifed on a per format basis. Examples
        of legal formats include Verilog,  VHDL.
        """
    }

    cfg['library'][lib]['atpg'] = {
        'switch': "-library_atpg 'lib <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library ATPG Model',
        'example': ["cli: -library_atpg 'mylib atpg mylib.atpg'",
                    "api: chip.set('library','mylib','atpg','mylib.atpg')"],
        'help': """
        Library models used for ATPG based automated faultd based post
        manufacturing testing.
        """
    }

    cfg['library'][lib]['pgmetal'] = {
        'switch': "-library_pgmetal 'lib <str>'",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Power/Ground Layer',
        'example': ["cli: -library_pgmetal 'mylib m1'",
                    "api: chip.set('library','mylib','pgmetal','m1')"],
        'help': """
        Specifies the top metal layer used for power and ground routing within
        the library. The parameter can be used to guide cell power grid hookup
        by APR tools.
        """
    }

    cfg['library'][lib]['tag'] = {
        'switch': "-library_tag 'lib <str>'",
        'requirement': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Library Identifier Tags',
        'example': ["cli: -library_tag 'mylib virtual'",
                    "api: chip.set('library','mylib','tag','virtual')"],
        'help': """
        Marks a library with a set of tags that can be used by the designer
        and EDA tools for optimization purposes. The tags are meant to cover
        features not currently supported by built in EDA optimization flows,
        but which can be queried through EDA tool TCL commands and lists.
        The example below demonstrates tagging the whole library as virtual.
        """
    }

    cfg['library'][lib]['driver'] = {
        'switch': "-library_driver 'lib <str>'",
        'requirement': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Library Default Driver Cell',
        'example': ["cli: -library_driver 'mylib BUFX1'",
                    "api: chip.set('library','mylib','driver','BUFX1')"],
        'help': """
        The name of a library cell to be used as the default driver for
        block timing constraints. The cell should be strong enough to drive
        a block input from another block including wire capacitance.
        In cases where the actual driver is known, the actual driver cell
        should be used.
        """
    }

    cfg['library'][lib]['site'] = {
        'switch': "-library_site 'lib <str>'",
        'requirement': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Site/Tile Name',
        'example': ["cli: -library_site 'mylib core'",
                    "api: chip.set('library','mylib','site','core')"],
        'help': """
        Provides the primary site name to use for placement.
        """
    }

    cfg['library'][lib]['cells'] = {}
    cfg['library'][lib]['cells']['default'] = {
        'switch': "-library_cells 'lib group <str>'",
        'requirement': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Library Cell Lists',
        'example': ["cli: -library_cells 'mylib dontuse *eco*'",
                    "api: chip.set('library','mylib','cells','dontuse',"
                    "'*eco*')"],
        'help': """
        A named list of cells grouped by a property that can be accessed
        directly by the designer and EDA tools. The example below shows how
        all cells containing the string 'eco' could be marked as dont use
        for the tool.
        """
    }

    cfg['library'][lib]['layoutdb'] = {}
    cfg['library'][lib]['layoutdb']['default'] = {}
    cfg['library'][lib]['layoutdb']['default']['default'] = {
        'switch': "-library_layoutdb 'lib stackup format <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Layout Database',
        'example': ["cli: -library_layoutdb 'mylib M10 oa /disk/mylibdb'",
                    "api: chip.set('library','mylib','layoutdb','M10',"
                    "'oa', '/disk/mylibdb')"],
        'help': """
        Filepaths to compiled library layout database specified on a per format
        basis. Example formats include oa, mw, ndm.
        """
    }

    return cfg

###############################################################################
# Flow Configuration
###############################################################################

def schema_flowgraph(cfg, step='default'):

    cfg['flowgraph'] = {}

    # Flow step parallelism
    cfg['flowgraph']['nproc'] =  {}
    cfg['flowgraph']['nproc'][step] = {
        'switch': "-flowgraph_nproc 'step <int>'",
        'type': 'int',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Flowgraph step parallelism',
        'example': ["cli: -flowgraph_nproc 'cts 10'",
                    "api:  chip.set('flowgraph','nproc,'cts','10')"],
        'help': """
        Integer specifying how many parallel processes to launch for step
        the step specified Each forked process operates on the same input
        data but on slightly different setup parameters as configured on
        a per fork basis.
        """
    }

    # Flow input dependancy
    cfg['flowgraph']['input'] =  {}
    cfg['flowgraph']['input'][step] = {
        'switch': "-flowgraph_input 'step <str>'",
        'type': '[str]',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': [],
        'short_help': 'Flowgraph Step Input',
        'example': ["cli: -flowgraph_input 'cts place'",
                    "api:  chip.set('flowgraph','input,'cts','place')"],
        'help': """
        List of input step dependancies for the current step. A step
        with no dependancies (like 'import') should set the value to
        'source'.
        """
    }



    # Flow input merging
    cfg['flowgraph']['mergeop'] = {}
    cfg['flowgraph']['mergeop'][step] = {
        'switch': "-flowgraph_mergeop 'step <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': [],
        'short_help': 'Flowgraph Merge Operation',
        'example': ["cli: -flowgraph_mergeop 'cts min'",
                    "api:  chip.set('flowgraph', 'mergeop', 'cts', 'min')"],
        'help': """
        Function to use when merging data from multiple inputs. Valid
        options are 'or' and 'min'.
        """
    }

    # Flow graph score weights
    cfg['flowgraph']['weight'] = {}
    cfg['flowgraph']['weight'][step] = {}
    cfg['flowgraph']['weight'][step]['default'] = {
        'switch': "-flowgraph_weight 'step metric <float>'",
        'type': 'float',
        'lock': 'false',
        'requirement': 'all,',
        'defvalue': [],
        'short_help': 'Flowgraph Metric Weights',
        'example': ["cli: -flowgraph_weight 'cts area_cells 1.0'",
                    "api:  chip.set('flowgraph','weight','cts', 'area_cells', 1.0)"],
        'help': """
        Weights specified on a per step and per metric basis used to give
        effective "goodnes" score for a step by calculating the sum all step
        real metrics results by the corresponding per step weights.
        """
    }

    # Step tool
    cfg['flowgraph']['tool'] = {}
    cfg['flowgraph']['tool'][step] = {
        'switch': "-flowgraph_tool 'step <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Flowgraph Tool Selection',
        'example': ["cli: -flowgraph_tool 'place openroad'",
                    "api: chip.set('flowgraph','tool','place','openroad')"],
        'help': """
        Name of the EDA tool to use for a specific step in the exeecution flow
        graph.
        """
    }

    # Step showtool
    cfg['flowgraph']['showtool'] = {}
    cfg['flowgraph']['showtool'][step] = {
        'switch': "-flowgraph_showtool 'step <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Flowgraph Show Tool Selection',
        'example': ["cli: -flowgraph_showtool 'place openroad'",
                    "api: chip.set('flowgraph','showtool','place','openroad')"],
        'help': """
        Name of the tool to use for showing the output file for a specific step in
        the exeecution flowgraph.
        """
    }

    return cfg

###########################################################################
# Design Hieararchy
###########################################################################

def schema_hier(cfg, parent='default', child='default'):


    cfg['hier'] = {}

    # Flow graph definition
    cfg['hier']['package'] = {}
    cfg['hier']['package'][parent] =  {}
    cfg['hier']['package'][parent][child] = {
        'switch': "-hier_package 'parent child <file>'",
        'type': '[file]',
        'lock': 'false',
        'requirement': None,
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Component package file',
        'example': ["cli: -hier_package 'top padring padring_package.json'",
                    "api:  chip.set('hier','package','top','padring','padring_package.json')"],
        'help': """
        Path to an instantiated child component package file. The file format is
        the standard JSON format exported by SC.
        """
    }

    # Hierarchical build indicator
    cfg['hier']['build'] = {}
    cfg['hier']['build'][parent] =  {}
    cfg['hier']['build'][parent][child] = {
        'switch': "-hier_build 'parent child <bool>'",
        'type': 'bool',
        'lock': 'false',
        'requirement': None,
        'defvalue': "false",
        'short_help': 'Child ',
        'example': ["cli: -hiear_build 'top padring true'",
                    "api:  chip.set('hier', 'build', 'top', 'padring', 'true')"],
        'help': """
        Path to an instantiated child cell package file.
        """
    }

    return cfg

###########################################################################
# EDA Tool Setup
###########################################################################

def schema_eda(cfg, tool='default', step='default', index='default'):

    cfg['eda'] = {}


    cfg['eda'][tool] = {}
    cfg['eda'][tool][step] = {}
    cfg['eda'][tool][step][index] = {}

    # exe
    cfg['eda']['exe'] = {}
    cfg['eda']['exe'][tool] = {}
    cfg['eda']['exe'][tool][step] = {}
    cfg['eda']['exe'][tool][step][index] = {
        'switch': "-eda_exe 'tool step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Executable Name',
        'example': [
            "cli: -eda_exe 'openroad cts 0 openroad'",
            "api:  chip.set('eda','exe','openroad,'cts','0','openroad')"],
        'help': """
        Name of the exuctable step or the full path to the executable
        specified on a per tool and step basis.
        """
    }

    # version-check
    cfg['eda']['vswitch'] = {}
    cfg['eda']['vswitch'][tool] = {}
    cfg['eda']['vswitch'][tool][step] = {}
    cfg['eda']['vswitch'][tool][step][index] = {
        'switch': "-eda_vswitch 'tool step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Executable version switch',
        'example': [
            "cli: -eda_vswitch 'openroad cts 0 -version'",
            "api:  chip.set('eda','vswitch,'openroad','cts','0','-version')"],
        'help': """
        Command line switch to use with executable used to print out
        the version number. Commmon switches include -v, -version,
        --version.
        """
    }

    # exe vendor
    cfg['eda']['vendor'] = {}
    cfg['eda']['vendor'][tool] = {}
    cfg['eda']['vendor'][tool][step] = {}
    cfg['eda']['vendor'][tool][step][index] = {
        'switch': "-eda_vendor 'tool step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Tool Vendor',
        'example': ["cli: -eda_vendor 'yosys syn 0 yosys'",
                    "api: chip.set('eda','vendor','yosys,'syn','0','yosys')"],
        'help': """
        Name of the tool vendor specified on a per tool and step basis.
        Parameter can be used to set vendor specific technology variables
        in the PDK and libraries. For open source projects, the project
        name should be used in place of vendor.
        """
    }

    # exe version
    cfg['eda']['version'] = {}
    cfg['eda']['version'][tool] = {}
    cfg['eda']['version'][tool][step] = {}
    cfg['eda']['version'][tool][step][index] = {
        'switch': "-eda_version 'tool step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Executable Version',
        'example': [
            "cli: -eda_version 'openroad cts 0 1.0'",
            "api:  chip.set('eda','version,'openroad','cts','0','1.0')"],
        'help': """
        Version of the tool executable specified on a per tool and per step
        basis. Mismatch between the step specifed and the step avalable results
        in an error.
        """
    }

    # options
    cfg['eda']['option'] = {}
    cfg['eda']['option'][tool] = {}
    cfg['eda']['option'][tool][step] = {}
    cfg['eda']['option'][tool][step][index] = {}
    cfg['eda']['option'][tool][step][index]['default'] = {
        'switch': "-eda_option 'tool step index name <str>'",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Executable Options',
        'example': [
            "cli: -eda_option 'openroad cts 0 cmdline -no_init'",
            "api:  chip.set('eda','option,'openroad,'cts','0','cmdline','-no_init')"],
        'help': """
        List of command line options for the tool executable, specified on
        a per tool and per step basis. For multiple argument options, enter
        each argument and value as a one list entry, specified on a per
        step basis. Options that include spaces must be enclosed in in double
        quotes. The options are entered as a dictionary assigned to a variable.
        For command line options, a variable should be 'cmdline'. For TCL
        variables fed into specific tools,  the variable name can be anything
        that is compatible with the tool, thus enabling the driving of an
        arbitray set of parameters within the tool.
        """
    }

    # input files
    cfg['eda']['input'] = {}
    cfg['eda']['input'][tool] = {}
    cfg['eda']['input'][tool][step] = {}
    cfg['eda']['input'][tool][step][index] = {
        'switch': "-eda_input 'tool step index <str>'",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'List of input files',
        'example': [
            "cli: -eda_input 'openroad place 0 oh_add.def'",
            "api: chip.set('eda','input','openroad,'place','0','oh_add.def')"],
        'help': """
        List of data files to be copied from previous flowgraph steps 'output'
        directory. The list of steps to copy files from is defined by the
        list defined by the dictionary key ['flowgraph', step, 'input'].
        'All files must be available for flow to continue. If a file
        is missing, the program exists on an error.
        """
    }

    # output files
    cfg['eda']['output'] = {}
    cfg['eda']['output'][tool] = {}
    cfg['eda']['output'][tool][step] = {}
    cfg['eda']['output'][tool][step][index] = {
        'switch': "-eda_output 'tool step index <str>'",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'List of outputd files ',
        'example': ["cli: -eda_output 'openroad place 0 oh_add.def'",
                    "api: chip.set('eda','output','openroad, 'place','0','oh_add.def')"],
        'help': """
        List of data files produced by the current step and placed in the
        'output' directory. During execuition, if a file is missing, the
        program exists on an error.
        """
    }

    # list of parameters used by tool
    cfg['eda']['param'] = {}
    cfg['eda']['param'][tool] = {}
    cfg['eda']['param'][tool][step] = {}
    cfg['eda']['param'][tool][step][index] = {
        'switch': "-eda_param 'tool step index <str>'",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'List of parameters used by tool',
        'example': [
            "cli: -eda_param 'openroad place 0 design'",
            "api: chip.set('eda','param','openroad, 'place','0','design')"],
        'help': """
        List of keypaths to SC parameters used by the tool. The list is used
        by check() to verify that all parameters have been set up before
        step execution begins.
        """
    }

    # refdir
    cfg['eda']['refdir'] = {}
    cfg['eda']['refdir'][tool] = {}
    cfg['eda']['refdir'][tool][step] = {}
    cfg['eda']['refdir'][tool][step][index] = {
        'switch': "-eda_refdir 'tool step index <dir>'",
        'type': 'dir',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Reference Directory',
        'example': [
            "cli: -eda_refdir 'yosys syn 0 ./myref'",
            "api:  chip.set('eda','refdir,'yosys','syn','0','./myref')"],
        'help': """
        Path to directories  containing compilation scripts, specified
        on a per step basis.
        """
    }

    # entry point scripts
    cfg['eda']['script'] = {}
    cfg['eda']['script'][tool] = {}
    cfg['eda']['script'][tool][step] = {}
    cfg['eda']['script'][tool][step][index] = {
        'switch': "-eda_script 'tool step index <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Entry Point script',
        'example': [
            "cli: -eda_script 'yosys syn 0 syn.tcl'",
            "api: chip.set('eda','script','yosys','syn','0','syn.tcl')"],
        'help': """
        Path to the entry point compilation script called by the executable,
        specified on a per tool and per step basis.
        """
    }

    # pre execution script
    cfg['eda']['prescript'] = {}
    cfg['eda']['prescript'][tool] = {}
    cfg['eda']['prescript'][tool][step] = {}
    cfg['eda']['prescript'][tool][step][index] = {
        'switch': "-eda_prescript 'tool step index <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Pre step script',
        'example': [
            "cli: -eda_prescript 'yosys syn 0 pre.tcl'",
            "api: chip.set('eda','prescript','yosys','syn','0','pre.tcl')"],
        'help': """
        Path to a user supplied script to execute after reading in the design
        but before the main execution stage of the step. Exact entry point
        depends on the step and main script being executed. An example
        of a prescript entry point would be immediately before global
        placement.
        """
    }

    # post execution script
    cfg['eda']['postscript'] = {}
    cfg['eda']['postscript'][tool] = {}
    cfg['eda']['postscript'][tool][step] = {}
    cfg['eda']['postscript'][tool][step][index] = {
        'switch': "-eda_postscript 'tool step index <file>'",
        'requirement': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Post step script',
        'example': ["cli: -eda_postscript 'yosys syn 0 post.tcl'",
                    "api: chip.set('eda','postscript,'yosys','syn','0','post.tcl')"],
        'help': """
        Path to a user supplied script to execute after reading in the design
        but before the main execution stage of the step. Exact entry point
        depends on the step and main script being executed. An example
        of a postscript entry point would be immediately after global
        placement.
        """
    }

    # copy
    cfg['eda']['copy'] = {}
    cfg['eda']['copy'][tool] = {}
    cfg['eda']['copy'][tool][step] = {}
    cfg['eda']['copy'][tool][step][index] = {
        'switch': "-eda_copy 'tool step index <bool>'",
        'type': 'bool',
        'lock': 'false',
        'requirement': None,
        'defvalue': "false",
        'short_help': 'Copy Local Option',
        'example': ["cli: -eda_copy 'openroad cts 0 true'",
                    "api: chip.set('eda','copy','openroad', 'cts','0', true)"],
        'help': """
        Specifies that the reference script directory should be copied and run
        from the local run directory. The option is specified on a per tool and
        per step basis.
        """
    }

    # exe type/format
    cfg['eda']['format'] = {}
    cfg['eda']['format'][tool] = {}
    cfg['eda']['format'][tool][step] = {}
    cfg['eda']['format'][tool][step][index] = {
        'switch': "-eda_format 'tool step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Script Format',
        'example': ["cli: -eda_format 'openroad cts 0 tcl'",
                    "api: chip.set('eda','format','openroad, 'cts','0','tcl')"],
        'help': """
        Format of the configuration file specified on a per tool and per
        step basis. Valid formats depend on the type of tool. Supported formats
        include tcl, yaml, json, command line.The keyword 'cmdline' is reserved
        for executables without TCL interfaces.
        """
    }

    # parallelism
    cfg['eda']['threads'] = {}
    cfg['eda']['threads'][tool] = {}
    cfg['eda']['threads'][tool][step] = {}
    cfg['eda']['threads'][tool][step][index] = {
        'switch': "-eda_threads 'tool step index <int>'",
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Job Parallelism',
        'example': ["cli: -eda_threads 'magic drc 0 64'",
                    "api: chip.set('eda','threads','magic','drc','0','64')"],
        'help': """
        Thread parallelism to use for execution specified on a per tool and per
        step basis. If not specified, SC queries the operating system and sets
        the threads based on the maximum thread count supported by the
        hardware.
        """
    }

    # turn off warning
    cfg['eda']['woff'] = {}
    cfg['eda']['woff'][tool] = {}
    cfg['eda']['woff'][tool][step] = {}
    cfg['eda']['woff'][tool][step][index] = {
        'switch': "-eda_woff 'tool step index name <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Warning Filter',
        'example': ["cli: -eda_woff 'verilator import 0 COMBDLY'",
                    "api: chip.set('eda','woff','verilator','import','0','COMBDLY')"],
        'help': """
        A list of EDA warnings for which printing should be supressed specified
        on a per tool and per step basis. Generally this is done on a per
        design basis after review has determined that warning can be safely
        ignored The code for turning off warnings can be found in the specific
        tool reference manual.
        """
    }

    # continue
    cfg['eda']['continue'] = {}
    cfg['eda']['continue'][tool] = {}
    cfg['eda']['continue'][tool][step] = {}
    cfg['eda']['continue'][tool][step][index] = {
        'switch': "-eda_continue 'tool step index <bool>'",
        'type': 'bool',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'false',
        'short_help': "Continue on error",
        'example': [
            "cli: -eda_continue 'verilator import 0 true'",
            "api: chip.set('eda','continue','verilator','import','0',true)"],
        'help': """
        Directs tool to not exit on error.
        """
    }

    return cfg

###########################################################################
# Local (not global!) parameters for controllings tools
###########################################################################
def schema_arg(cfg):


    cfg['arg'] = {}

    cfg['arg']['step'] = {
        'switch': "-arg_step <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Current Execution Step',
        'example': ["cli: -arg_step 'route'",
                    "api: chip.set('arg', 'step', 'route')"],
        'help': """
        Dynamic variable passed in by the sc runtime as an argument to
        an EDA tool. The variable allows the EDA configuration code
        (usually TCL) to use control flow that depend on the current
        executions step rather than having separate files called
        for each step.
        """
    }

    cfg['arg']['index'] = {
        'switch': "-arg_index <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Current Step Index',
        'example': ["cli: -arg_index 0",
                    "api: chip.set('arg','index','0')"],
        'help': """
        Dynamic variable passed in by the sc runtime as an argument to
        an EDA tool to indicate the index of the step being worked on.
        """
    }

    return cfg


###########################################################################
# Metrics to Track
###########################################################################

def schema_metric(cfg, group='default', step='default', index='default'):

    if not 'metric' in cfg:
        cfg['metric'] = {}

    cfg['metric']['registers'] = {}
    cfg['metric']['registers'][step] = {}
    cfg['metric']['registers'][step][index] = {}
    cfg['metric']['registers'][step][index][group] = {
        'switch': '-metric_registers step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Registers Metric',
        'example': [
            "cli: -metric_registers 'place 0 real 100'",
            "api: chip.set('metric','registers','place','0','goal','100')"],
        'help': """
        Metric tracking the total number of register cells on a per step basis.
        """
    }

    cfg['metric']['cells'] = {}
    cfg['metric']['cells'][step] = {}
    cfg['metric']['cells'][step][index] = {}
    cfg['metric']['cells'][step][index][group] = {
        'switch': '-metric_cells step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Cell Instances Metric',
        'example': [
            "cli: -metric_cells 'place 0 goal 100'",
            "api: chip.set('metric','cells','place','0','goal,'100')"],
        'help': """
        Metric tracking the total number of instances on a per step basis.
        Total cells includes registers. In the case of FPGAs, the it
        represents the number of LUTs.
        """
    }

    cfg['metric']['rambits'] = {}
    cfg['metric']['rambits'][step] = {}
    cfg['metric']['rambits'][step][index] = {}
    cfg['metric']['rambits'][step][index][group] = {
        'switch': '-metric_rambits step index rambits <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total RAM Macro Bits Metric',
        'example': [
            "cli: -metric_rambits 'place 0 goal 100'",
            "api: chip.set('metric','rambits','place','0','goal','100')"],
        'help': """
        Metric tracking the total number of RAM bits in the design
        on a per step basis. In the case of FPGAs, the it
        represents the number of bits mapped to block ram.
        """
    }
    cfg['metric']['xtors'] = {}
    cfg['metric']['xtors'][step] = {}
    cfg['metric']['xtors'][step][index] = {}
    cfg['metric']['xtors'][step][index][group] = {
        'switch': '-metric_cells step index xtors <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Transistors Metric',
        'example': [
            "cli: -metric_xtors 'place 0 goal 100'",
            "api: chip.set('metric','xtors','place','0','real','100')"],
        'help': """
        Metric tracking the total number of transistors in the design
        on a per step basis.
        """
    }

    cfg['metric']['nets'] = {}
    cfg['metric']['nets'][step] = {}
    cfg['metric']['nets'][step][index] = {}
    cfg['metric']['nets'][step][index][group] = {
        'switch': '-metric_nets step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Nets Metric',
        'example': [
            "cli: -metric_nets 'place 0 real 100'",
            "api: chip.set('metric','nets','place','0','real','100')"],
        'help': """
        Metric tracking the total number of net segments on a per step
        basis.
        """
    }

    cfg['metric']['pins'] = {}
    cfg['metric']['pins'][step] = {}
    cfg['metric']['pins'][step][index] = {}
    cfg['metric']['pins'][step][index][group] = {
        'switch': '-metric_pins step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Pins Metric',
        'example': [
            "cli: -metric_pins 'place 0 real 100'",
            "api: chip.set('metric','pins','place','0','real','100')"],
        'help': """
        Metric tracking the total number of I/O pins on a per step
        basis.
        """
    }

    cfg['metric']['vias'] = {}
    cfg['metric']['vias'][step] = {}
    cfg['metric']['vias'][step][index] = {}
    cfg['metric']['vias'][step][index][group] = {
        'switch': '-metric_vias step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Vias metric',
        'example': [
            "cli: -metric_vias 'route 0 real 100'",
            "api: chip.set('metric','vias','place','0','real','100')"],
        'help': """
        Metric tracking the total number of vias in the design.
        """
    }
    cfg['metric']['wirelength'] = {}
    cfg['metric']['wirelength'][step] = {}
    cfg['metric']['wirelength'][step][index] = {}
    cfg['metric']['wirelength'][step][index][group] = {
        'switch': '-metric_wirelength step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Wirelength Metric',
        'example': [
            "cli: -metric_wirelength 'route 0 real 100.00'",
            "api: chip.set('metric','wirelength','place','0','real','100.42')"],
        'help': """
        Metric tracking the total wirelength in the design in meters.
        """
    }
    cfg['metric']['overflow'] = {}
    cfg['metric']['overflow'][step] = {}
    cfg['metric']['overflow'][step][index] = {}
    cfg['metric']['overflow'][step][index][group] = {
        'switch': '-metric_overflow step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Routing Overflow Metric',
        'example': [
            "cli: -metric_overflow 'route 0 real 0'",
            "api: chip.set('metric','overflow','place','0','real','0')"],
        'help': """
        Metric tracking the total number of overflow tracks for the routing.
        Any non-zero number suggests an over congested design. To analyze
        where the congestion is occuring inspect the router log files for
        detailed per metal overflow reporting and open up the design to find
        routing hotspots.
        """
    }
    cfg['metric']['area_cells'] = {}
    cfg['metric']['area_cells'][step] = {}
    cfg['metric']['area_cells'][step][index] = {}
    cfg['metric']['area_cells'][step][index][group] = {
        'switch': '-metric_area_cells step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Cell Area Metric',
        'example': [
            "cli: -metric_area_cells 'place 0 goal 100.00'",
            "api: chip.set('metric','area_cells','place','0','real','100.00')"],
        'help': """
        Metric tracking the sum of all non-filler standard cells on a per and per
        index basis specified in um^2.
        """
    }
    cfg['metric']['area_density'] = {}
    cfg['metric']['area_density'][step] = {}
    cfg['metric']['area_density'][step][index] = {}
    cfg['metric']['area_density'][step][index][group] = {
        'switch': '-metric_area_density step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Area Density Metric',
        'example': [
            "cli: -metric_area_density 'place 0 goal 99.9'",
            "api: chip.set('metric','area_density','place','0','real','99.9')"],
        'help': """
        Metric tracking the effective area utilization/desnity calculated as the
        ratio of cell area divided by the total core area available for
        placement. Value is specified as a percentage (%) and does not include
        filler cells.
        """
    }

    cfg['metric']['power_total'] = {}
    cfg['metric']['power_total'][step] = {}
    cfg['metric']['power_total'][step][index] = {}
    cfg['metric']['power_total'][step][index][group] = {
        'switch': '-metric_power_total step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Power Metric',
        'example': [
            "cli: -metric_power_total 'place 0 real 0.001'",
            "api: chip.set('metric','power_total','place','0','real','0.001')"],
        'help': """
        Metric tracking the worst case total power of the design on a per
        step basis calculated based on setup config and VCD stimulus.
        stimulus. Metric unit is Watts.
        """
    }

    cfg['metric']['power_leakage'] = {}
    cfg['metric']['power_leakage'][step] = {}
    cfg['metric']['power_leakage'][step][index] = {}
    cfg['metric']['power_leakage'][step][index][group] = {
        'switch': '-metric_power_leakage step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Leakage Power Metric',
        'example': [
            "cli: -metric_power_leakage 'place 0 real 1e-6'",
            "api: chip.set('metric','power_leakage','place','0','real','1e-6')"],
        'help': """
        Metric tracking the leakage power of the design on a per step
        basis. Metric unit is Watts.
        """
    }

    cfg['metric']['hold_slack'] = {}
    cfg['metric']['hold_slack'][step] = {}
    cfg['metric']['hold_slack'][step][index] = {}
    cfg['metric']['hold_slack'][step][index][group] = {
        'switch': '-metric_hold_slack step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Hold Slack Metric',
        'example': [
            "cli: -metric_hold_slack 'place 0 real 0.42",
            "api: chip.set('metric','hold_slack','place','0','real,'0.43')"],
        'help': """
        Metric tracking the worst hold/min timing path slack in the design.
        Positive values means there is spare/slack, negative slack means the design
        is failing a hold timing constrainng. The metric unit is nanoseconds.
        """
    }

    cfg['metric']['hold_tns'] = {}
    cfg['metric']['hold_tns'][step] = {}
    cfg['metric']['hold_tns'][step][index] = {}
    cfg['metric']['hold_tns'][step][index][group] = {
        'switch': '-metric_hold_tns step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Hold TNS Metric',
        'example': [
            "cli: -metric_hold_tns 'place 0 real 0.0'",
            "api: chip.set('metric','hold_tns','place','0','real','0')"],
        'help': """
        Metric tracking of total negative hold slack (TNS) on a per step basis.
        Metric unit is nanoseconds.
        """
    }

    cfg['metric']['setup_slack'] = {}
    cfg['metric']['setup_slack'][step] = {}
    cfg['metric']['setup_slack'][step][index] = {}
    cfg['metric']['setup_slack'][step][index][group] = {
        'switch': '-metric_setup_slack step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Setup Slack Metric',
        'example': [
            "cli: -metric_setup_slack 'place 0 goal 0.0",
            "api: chip.set('metric','setup_slack','place','0','real','0.0')"],
        'help': """
        Metric tracking the worst setup/min timing path slack in the design.
        Positive values means there is spare/slack, negative slack means the design
        is failing a setup timing constrainng. The metric unit is nanoseconds.
        """
    }

    cfg['metric']['setup_tns'] = {}
    cfg['metric']['setup_tns'][step] = {}
    cfg['metric']['setup_tns'][step][index] = {}
    cfg['metric']['setup_tns'][step][index][group] = {
        'switch': '-metric_setup_tns step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Setup TNS Metric',
        'example': [
            "cli: -metric_setup_tns 'place 0 goal 0.0'",
            "api: chip.set('metric','setup_tns','place','0','real','0.0')"],
        'help': """
        Metric tracking of total negative setup slack (TNS) on a per step basis.
        Metric unit is nanoseconds.
        """
    }

    cfg['metric']['drv'] = {}
    cfg['metric']['drv'][step] = {}
    cfg['metric']['drv'][step][index] = {}
    cfg['metric']['drv'][step][index][group] = {
        'switch': '-metric_drv step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Rule Violations Metric',
        'example': [
            "cli: -metric_drv 'dfm 0 goal 0'",
            "api: chip.set('metric','drv','dfm','0','real','0')"],
        'help': """
        Metric tracking the total number of design rule violations on per step
        basis.
        """
    }
    cfg['metric']['warnings'] = {}
    cfg['metric']['warnings'][step] = {}
    cfg['metric']['warnings'][step][index] = {}
    cfg['metric']['warnings'][step][index][group] = {
        'switch': '-metric_warnings step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Warnings Metric',
        'example': [
            "cli: -metric_warnings 'dfm 0 goal 0'",
            "api: chip.set('metric','warnings','dfm','0','real','0')"],

        'help': """
        Metric tracking the total number of warnings on a per step basis.
        """
    }
    cfg['metric']['errors'] = {}
    cfg['metric']['errors'][step] = {}
    cfg['metric']['errors'][step][index] = {}
    cfg['metric']['errors'][step][index][group] = {
        'switch': '-metric_errors step index group <int>',
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Errors Metric',
        'example': [
            "cli: -metric_errors 'dfm 0 goal 0'",
            "api: chip.set('metric','errors','dfm','0','real','0')"],
        'help': """
        Metric tracking the total number of errors on a per step basis.
        """
    }

    cfg['metric']['runtime'] = {}
    cfg['metric']['runtime'][step] = {}
    cfg['metric']['runtime'][step][index] = {}
    cfg['metric']['runtime'][step][index][group] = {
        'switch': '-metric_runtime step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Runtime Metric',
        'example': [
            "cli: -metric_runtime 'dfm 0 goal 35.3'",
            "api: chip.set('metric','runtime','dfm','0','real','35.3')"],
        'help': """
        Metric tracking the total runtime on a per step basis. Time recorded
        as wall clock time specified in seconds.
        """
    }

    cfg['metric']['memory'] = {}
    cfg['metric']['memory'][step] = {}
    cfg['metric']['memory'][step][index] = {}
    cfg['metric']['memory'][step][index][group] = {
        'switch': '-metric_memory step index group <float>',
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Total Memory Metric',
        'example': [
            "cli: -metric_memory 'dfm 0 goal 10e9'",
            "api: chip.set('metric','memory','dfm','0','real,'10e6')"],
        'help': """
        Metric tracking the total memory on a per step basis, specified
        in bytes.
        """
    }

    return cfg

###########################################################################
# Design Tracking
###########################################################################

def schema_record(cfg, step='default', index='default'):

    cfg['record'] = {}

    cfg['record']['input'] = {}
    cfg['record']['input'][step] = {}
    cfg['record']['input'][step][index] = {
        'switch': "-record_input 'step index <file>'",
        'requirement': None,
        'type': '[file]',
        'copy': 'false',
        'lock': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Step Inputs',
        'example': ["cli: -record_input 'import 0 gcd.v'",
                    "api: chip.set('record','input','import','0','gcd.v')"],
        'help': """
        Metric tracking all input files on a per step basis. This list
        include files entered by the user and files automatically found
        by the flow like in the case of the "-y" auto-discovery path.
        """
    }

    cfg['record']['author'] = {}
    cfg['record']['author'][step] = {}
    cfg['record']['author'][step][index] = {
        'switch': "-record_author 'step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Step Author',
        'example': ["cli: -record_author 'dfm 0 coyote'",
                    "api: chip.set('record','author','dfm','0','wcoyote')"],
        'help': """
        Metric tracking the author on a per step basis.
        """
    }

    cfg['record']['userid'] = {}
    cfg['record']['userid'][step] = {}
    cfg['record']['userid'][step][index] = {
        'switch': "-record_userid 'step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Step User ID',
        'example': ["cli: -record_userid 'dfm 0 0982acea'",
                    "api: chip.set('record','userid','dfm','0','0982acea')"],
        'help': """
        Metric tracking the run userid on a per step basis.
        """
    }
    cfg['record']['signature'] = {}
    cfg['record']['signature'][step] = {}
    cfg['record']['signature'][step][index] = {
        'switch': "-record_signature 'step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Step Signature',
        'example': ["cli: -record_signature 'dfm 0 473c04b'",
                    "api: chip.set('record','signature','dfm','0','473c04b')"],
        'help': """
        Metric tracking the execution signature/hashid on a per step basis.
        """
    }

    cfg['record']['org'] = {}
    cfg['record']['org'][step] = {}
    cfg['record']['org'][step][index] = {
        'switch': "-record_org 'step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Step Organization',
        'example': ["cli: -record_org 'dfm 0 earth'",
                    "api: chip.set('record','org','dfm','0','earth')"],
        'help': """
        Metric tracking the user's organization on a per step basis.
        """
    }

    cfg['record']['location'] = {}
    cfg['record']['location'][step] = {}
    cfg['record']['location'][step][index] = {
        'switch': "-record_location 'step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Step Location',
        'example': ["cli: -record_location 'dfm 0 Boston'",
                    "api: chip.set('record','location,'dfm','0','Boston')"],
        'help': """
        Metric tracking the user's location/site on a per step basis.
        """
    }

    cfg['record']['date'] = {}
    cfg['record']['date'][step] = {}
    cfg['record']['date'][step][index] = {
        'switch': "-record_date 'step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Step Date Stamp',
        'example': ["cli: -record_date 'dfm 2021-05-01'",
                    "api: chip.set('record','date','dfm','0','2021-05-01')"],
        'help': """
        Metric tracking the run date stamp on a per step basis.
        The date format is the ISO 8601 format YYYY-MM-DD.
        """
    }

    cfg['record']['time'] = {}
    cfg['record']['time'][step] = {}
    cfg['record']['time'][step][index] = {
        'switch': "-record_time 'step index <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Step Time Stamp',
        'example': ["cli: -record_time 'dfm 0 11:35:40'",
                    "api: chip.set('record','time','dfm','0', '11:35:40')"],
        'help': """
        Metric tracking the local run start time on a per step basis.
        The time format is specified in 24h-hr format hr:min:sec
        """
    }

    return cfg

###########################################################################
# Run Options
###########################################################################

def schema_options(cfg):
    ''' Run-time options
    '''

    cfg['mode'] = {
        'switch': "-mode <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'asic',
        'short_help': 'Compilation Mode',
        'example': ["cli: -mode fpga",
                    "api: chip.set('mode','fpga')"],
        'help': """
        Sets the compilation flow to 'fpga' or 'asic. The default is 'asic'
        """
    }

    cfg['target'] = {
        'switch': "-target <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Compilation Target',
        'example': ["cli: -target 'freepdk45_asicflow'",
                    "api: chip.set('target','freepdk45_asicflow')"],
        'help': """
        Compilation target double string separated by a single underscore,
        specified as "<process>_<edaflow>" for ASIC compilation and
        "<partname>_<edaflow>" for FPGA compilation. The process, edaflow,
        partname fields must be alphanumeric and cannot contain underscores.
        """
    }

    cfg['cfg'] = {
        'switch': "-cfg <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Configuration File',
        'example': ["cli: -cfg mypdk.json",
                    "api: chip.set('cfg','mypdk.json')"],
        'help': """
        All parameters can be set at the command line, but with over 500
        configuration parameters possible, the preferred method for non trivial
        use cases is to create a cfg file using the python API. The cfg file
        can then be passed in through he -cfg switch at the command line.
        There  is no restriction on the number of cfg files that can be be
        passed in. but it should be noted that the cfg are appended to the
        existing list and configuration list.
        """
        }

    cfg['env'] = {}
    cfg['env']['default'] = {
        'switch': "-env 'var <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Environment Variables',
        'example': ["cli: -env 'PDK_HOME /disk/mypdk'",
                    "api: chip.set('env', 'PDK_HOME', '/disk/mypdk')"],
        'help': """
        Certain EDA tools and reference flows require environment variables to
        be set. These variables can be managed externally or specified through
        the env variable.
        """
    }

    cfg['scpath'] = {
        'switch': "-scpath <dir>",
        'type': '[dir]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Search path',
        'example': ["cli: -scpath '/home/$USER/sclib'",
                    "api: chip.set('scpath', '/home/$USER/sclib')"],
        'help': """
        Specifies python modules paths for target import.
        """
    }

    cfg['hashmode'] = {
        'switch': "-hashmode <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'OFF',
        'short_help': 'File Hash Mode',
        'example': ["cli: -hashmode 'ALL'",
                    "api: chip.set('hashmode', 'ALL')"],
        'help': """
        The switch controls how/if setup files and source files are hashed
        during compilation. Valid entries include OFF, ALL, ACTIVE.
        ACTIVE specifies to only hash files being used in the current cfg.
        """
    }

    cfg['quiet'] = {
        'switch': "-quiet <bool>",
        'type': 'bool',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'false',
        'short_help': 'Quiet execution',
        'example': ["cli: -quiet",
                    "api: chip.set('quiet', 'true')"],
        'help': """
        Modern EDA tools print significant content to the screen. The -quiet
        option forces all steps to print to a log file. The quiet
        option is ignored when the -noexit is set to true.
        """
    }

    cfg['loglevel'] = {
        'switch': "-loglevel <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'WARNING',
        'short_help': 'Logging Level',
        'example': ["cli: -loglevel INFO",
                    "api: chip.set('loglevel', 'INFO')"],
        'help': """
        The debug param provides explicit control over the level of debug
        logging printed. Valid entries include INFO, DEBUG, WARNING, ERROR. The
        default value is WARNING.
        """
    }

    cfg['build_dir'] = {
        'switch': "-build_dir <dir>",
        'type': 'dir',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'build',
        'short_help': 'Build Directory',
        'example': ["cli: -build_dir ./build_the_future",
                    "api: chip.set('build_dir','./build_the_future')"],
        'help': """
        The default build directoryis './build'. The 'dir' parameters can be
        used to set an alternate compilation directory path.
        """
    }

    cfg['jobname'] = {
        'switch': "-jobname <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'job',
        'short_help': 'Job Name Prefix',
        'example': ["cli: -jobname may1",
                    "api: chip.set('jobname','may1')"],
        'help': """
        The name of the directory to work in.
        The full directory structure is:
        'dir'/'design'/'jobname''jobid'
        """
    }

    cfg['jobid'] = {
        'switch': "-jobid <int>",
        'type': 'int',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': '0',
        'short_help': 'Job ID',
        'example': ["cli: -jobid 0",
                    "api: chip.set('jobid',0)"],
        'help': """
        The id of the specific job to be exeucted.
        The directory structure is:
        'dir'/'design'/'jobname''jobid'
        """
    }

    cfg['jobincr'] = {
        'switch': "-jobincr <bool>",
        'type': 'bool',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'true',
        'short_help': 'Job ID Autoincrement Mode ',
        'example': ["cli: -jobincr",
                    "api: chip.set('jobincr', true)"],
        'help': """
        Autoincrements the jobid value based on the latest
        executed job in the design build directory. If no jobs are found,
        the value in the 'jobid' parameter is used.
        """
    }

    cfg['steplist'] = {
        'switch': "-steplist <str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Compilation step list',
        'example': ["cli: -steplist 'import'",
                    "api: chip.set('steplist','import')"],
        'help': """
        List of steps to execute. The default is to execute all steps defined
        in the flow graph.
        """
    }

    cfg['msgevent'] = {
        'switch': "-msgevent <str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Message Event',
        'example': ["cli: -msgevent export",
                    "api: chip.set('msgevent','export')"],
        'help': """
        A list of steps after which to notify a recipient. For example if
        values of syn, place, cts are entered separate messages would be sent
        after the completion of the syn, place, and cts steps.
        """
    }

    cfg['msgcontact'] = {
        'switch': "-msgcontact <str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Message Contact',
        'example': ["cli: -msgcontact 'wile.e.coyote@acme.com'",
                    "api: chip.set('msgcontact','wile.e.coyote@acme.com')"],
        'help': """
        A list of phone numbers or email addresses to message on a event event
        within the msg_event param.
        """
    }

    cfg['optmode'] = {
        'switch': '-O <str>',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'O0',
        'short_help': 'Optimization Mode',
        'example': ["cli: -O3",
                    "api: chip.set('optmode','3')"],
        'help': """
        The compiler has modes to prioritize run time and ppa. Modes include:

        (0) = Exploration mode for debugging setup
        (1) = Higher effort and better PPA than O0
        (2) = Higher effort and better PPA than O1
        (3) = Signoff qualtiy. Better PPA and higher run times than O2
        (4) = Experimental highest effort, may be unstable.
        """
    }

    cfg['relax'] = {
        'switch': "-relax <bool>",
        'type': 'bool',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'false',
        'short_help': 'Relaxed RTL Linting',
        'example': ["cli: -relax",
                    "api: chip.set('relax', 'true')"],
        'help': """
        Specifies that tools should be lenient and supress some warnigns that
        may or may not indicate design issues. The default is to enforce strict
        checks for all steps.
        """
    }

    cfg['clean'] = {
        'switch': "-clean <bool>",
        'type': 'bool',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'false',
        'short_help': 'Keep essential files only',
        'example': ["cli: -clean",
                    "api: chip.set('clean', 'true')"],
        'help': """
        Deletes all non-essential files at the end of each step and creates a
        'zip' archive of the job folder.
        """
    }

    cfg['bkpt'] = {
        'switch': "-bkpt <str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': "A list of flow breakpoints",
        'example': ["cli: -bkpt place",
                    "api: chip.set('bkpt','place')"],
        'help': """
        Specifies a list of step stop (break) points. If the step is
        a TCL based tool, then the breakpoints stops the flow inside the EDA
        tool. If the step is a command line tool, then the flow drops into
        a Python interpreter.
        """
    }

    cfg['copyall'] = {
        'switch': "-copyall <bool>",
        'type': 'bool',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'false',
        'short_help': "Copy All Input Files to Jobdir",
        'example': ["cli: -copyall",
                    "api: chip.set('copyall', 'true')"],
        'help': """
        Specifies that all used files should be copied into the jobdir,
        overriding the per schema entry copy settings. The default
        is false.
        """
    }

    return cfg

############################################
# Remote Run Options
#############################################
def schema_remote(cfg):

    cfg['remote'] = {}

    # Remote IP address/host name running sc-server app
    cfg['remote']['addr'] = {
        'switch': "-remote_addr <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': None,
        'short_help': 'Remote Server Address',
        'example': ["cli: -remote_addr 192.168.1.100",
                    "api: chip.set('remote', 'addr', '192.168.1.100')"],
        'help': """
        Dicates that all steps after the compilation step should be executed
        on the remote server specified by the IP address or domain name.
        """
    }

    # Port number that the remote host is running 'sc-server' on.
    cfg['remote']['port'] = {
        'switch': "-remote_port <int>",
        'type': 'int',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': '443',
        'short_help': 'Remote Server Port',
        'example': ["cli: -remote_port 8080",
                    "api: chip.set('remote', 'port', '8080')"],
        'help': """
        Sets the server port to be used in communicating with the remote host.
        """
    }

    # Job hash. Used to resume or cancel remote jobs after they are started.
    cfg['remote']['jobhash'] = {
        'switch': "-remote_jobhash <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Job hash/UUID value',
        'example': ["cli: -remote_jobhash 0123456789abcdeffedcba9876543210",
                    "api: chip.set('remote', 'jobhash','0123456789abcdeffedcba9876543210')"],
        'help': """
        A unique ID associated with a job run. This field should be left blank
        when starting a new job, but it can be provided to resume an interrupted
        remote job, or to clean up after unexpected failures.
        """
    }

    # Remote execution steplist
    cfg['remote']['steplist'] = {
        'switch': "-remote_steplist <str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Remote steplist execution',
        'example': ["cli: -remote_steplist syn",
                    "api: chip.set('remote', 'steplist', 'syn')"],
        'help': """
        List of steps to execute remotely.
        """
    }

    # Remote username
    cfg['remote']['user'] = {
        'switch': "-remote_user <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': None,
        'short_help': 'Remote authentication username.',
        'example': ["cli: -remote_user testuser",
                    "api: chip.set('remote', 'user', 'testuser')"],
        'help': """
        Specifies a username for authenticating calls with a remote server.
        """
    }

    # Remote private key file.
    cfg['remote']['key'] = {
        'switch': '-remote_key <file>',
        'type': 'file',
        'lock': 'false',
        'copy': 'false',
        'requirement': 'remote',
        'defvalue': None,
        'short_help': 'Remote authentication private key file.',
        'example': ["cli: -remote_key ~/.ssh/decrypt_key",
                    "api: chip.set('remote', 'key', './decrypt_key')"],
        'help': """
        Specifies a private key file which will allow the server to
        authenticate the given user and decrypt data associated with them.
        """
    }

    # Number of temporary hosts to request for the job. (Default: 0)
    cfg['remote']['hosts'] = {
        'switch': "-remote_hosts <int>",
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': '0',
        'short_help': 'Number of temporary compute nodes to request.',
        'example': ["cli: -remote_hosts 2",
                    "api: chip.set('remote', 'hosts', '2')"],
        'help': """
        Sets the number of temporary hosts to request for parallel processing.
        Should be less than or equal to the number of permutations being run.
        No effect if the server is not configured for clustering.
        If no hosts are requested, the job will run in the standing pool
        of compute nodes, which is typically small and shared.
        Depending on server-side limits and capacity, the job may receive
        fewer temporary hosts than requested, down to and including 0.
        """
    }

    # GiB of RAM to request in a remote host.
    cfg['remote']['ram'] = {
        'switch': "-remote_ram <float>",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'GiB of RAM to request in temporary cloud hosts.',
        'example': ["cli: -remote_ram 16",
                    "api: chip.set('remote', 'ram', '16')"],
        'help': """
        Sets how much RAM each temporary host should have. If the given value
        is not a power of two, the script may request up to one power of two
        above the given amount. For example, requesting 10GiB of RAM may allocate
        hosts with up to 16GiB, but requesting 8GiB will not.
        An error may be returned if no hosts can meet the given specifications.
        """
    }

    # Number of 'virtual CPUs' to request in a remote host.
    cfg['remote']['threads'] = {
        'switch': "-remote_threads <int>",
        'type': 'int',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': None,
        'short_help': 'Number of harts to request in each remote host.',
        'example': ["cli: -remote_threads 4",
                    "api: chip.set('remote', 'threads', '4')"],
        'help': """
        Sets how many hardware threads each temporary host should have.
        Threads are the most common metric, but depending on the cloud hosting
        provider, this parameter may allocate physical CPU cores in some cases.
        If the given value is not a power of two, the script may request
        up to one power of two above the given amount. For example, requesting
        hosts with 6 vCPUs may allocate up to 8 vCPUS, but requesting 4 will not.
        An error may be returned if no hosts can meet the given specifications.
        """
    }

    return cfg

############################################
# Design Setup
#############################################

def schema_design(cfg):
    ''' Design Sources
    '''

    cfg['design'] = {
        'switch': "-design <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Top Module Name',
        'example': ["cli: -design hello_world",
                    "api: chip.set('design', 'hello_world')"],
        'help': """
        Name of the top level design to compile. Required for all designs with
        more than one module.
        """
    }

    cfg['source'] = {
        'switch': '<file>',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'all',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Source Files',
        'example': ["cli: hello_world.v",
                    "api: chip.set('source', 'hello_world.v')"],
        'help': """
        A list of source files to read in for elaboration. The files are read
        in order from first to last entered. File type is inferred from the
        file suffix:
        (\\*.v, \\*.vh) = Verilog
        (\\*.vhd)      = VHDL
        (\\*.sv)       = SystemVerilog
        (\\*.c)        = C
        (\\*.cpp, .cc) = C++
        (\\*.py)       = Python
        """
    }

    cfg['repo'] = {
        'switch': "-repo <str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Design Repository',
        'example': ["cli: -repo git@github.com:aolofsson/oh.git",
                    "api: chip.set('repo','git@github.com:aolofsson/oh.git')"],
        'help': """
        Optional address to the design repositories used in design.
        """
    }

    cfg['doc'] = {
        'switch': "-doc <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Documentation',
        'example': ["cli: -doc spec.pdf",
                    "api: chip.set('doc', 'spec.pdf')"],
        'help': """
        A list of design documents. Files are read in order from first to last.
        """
    }

    cfg['version'] = {
        'switch': "-version <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Version',
        'example': ["cli: -version 1.0",
                    "api: chip.set('version', '1.0')"],
        'help': """
        Specifies the version of the current design. Can be a branch, tag, or
        commit has or simple string.
        """
    }

    cfg['license'] = {
        'switch': "-license <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design License File',
        'example': ["cli: -license ./LICENSE",
                    "api: chip.set('license', './LICENSE')"],
        'help': """
        Filepath to the technology license for currrent design.
        """
    }

    cfg['name'] = {
        'switch': "-name <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Package Name',
        'example': ["cli: -name hello",
                    "api: chip.set('name', 'hello')"],
        'help': """
        An alias for the top level design name. Can be useful when top level
        designs have long and confusing names or when multiple configuration
        packages are created for the same design. The nickname is used in all
        output file prefixes. The top level design name is used if no
        'name' parameter is defined.
        """
    }

    cfg['origin'] = {
        'switch': "-origin <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Origin',
        'example': ["cli: -origin mars",
                    "api: chip.set('origin', 'mars')"],
        'help': """
        Record of design country of origin.
        """
    }

    cfg['clock'] = {}
    cfg['clock']['default'] = {}
    cfg['clock']['default']['pin'] = {
        'switch': "-clock_pin 'clkname <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Clock Driver',
        'example': ["cli: -clock_pin 'clk top.pll.clkout'",
                    "api: chip.set('clock', 'clk','pin','top.pll.clkout')"],
        'help': """
        Defines a clock name alias to assign to a clock source.
        """
    }

    cfg['clock']['default']['period'] = {
        'switch': "-clock_period 'clkname <float>'",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Clock Period',
        'example': ["cli: -clock_period 'clk 10'",
                    "api: chip.set('clock','clk','period','10')"],
        'help': """
        Specifies the period for a clock source in nanoseconds.
        """
    }

    cfg['clock']['default']['jitter'] = {
        'switch': "-clock_jitter 'clkname <float>'",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Clock Jitter',
        'example': ["cli: -clock_jitter 'clk 0.01'",
                    "api: chip.set('clock','clk','jitter','0.01')"],
        'help': """
        Specifies the jitter for a clock source in nanoseconds.
        """
    }

    cfg['supply'] = {}
    cfg['supply']['default'] = {}
    cfg['supply']['default']['pin'] = {
        'switch': "-supply_pin 'supplyname <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Power Supply Name',
        'example': ["cli: -supply_pin 'vdd vdd_0'",
                    "api: chip.set('supply','vdd','pin','vdd_0')"],
        'help': """
        Defines a supply name alias to assign to a power source.
        A power supply source can be a list of block pins or a regulator
        output pin.

        Examples:
        cli: -supply_name 'vdd_0 vdd'
        api: chip.set('supply','vdd_0', 'pin', 'vdd')
        """
    }

    cfg['supply']['default']['level'] = {
        'switch': "-supply_level 'supplyname <float>'",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Power Supply Level',
        'example': ["cli: -supply_level 'vdd 1.0'",
                    "api: chip.set('supply','vdd','level','1.0')"],
        'help': """
        Specifies level in Volts for a power source.
        """
    }

    cfg['supply']['default']['noise'] = {
        'switch': "-supply_noise 'supplyname <float>'",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Power Supply Noise',
        'example': ["cli: -supply_noise 'vdd 0.05'",
                    "api: chip.set('supply','vdd','noise','0.05')"],
        'help': """
        Specifies the noise in Volts for a power source.
        """
    }

    cfg['param'] = {}
    cfg['param']['default'] = {
        'switch': "-param 'name <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Parameter Override',
        'example': ["cli: -param 'N 64'",
                    "api: chip.set('param','N', '64')"],
        'help': """
        Overrides the given parameter of the top level module. The value
        is limited to basic data literals. The parameter override is
        passed into tools such as Verilator and Yosys. The parameters
        support Verilog integer literals (64'h4, 2'b0, 4) and strings.
        """
    }

    cfg['define'] = {
        'switch': "-D<str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Design Preprocessor Symbols',
        'example': ["cli: -D 'CFG_ASIC=1'",
                    "api: chip.set('define','CFG_ASIC=1')"],
        'help': """
        Sets a preprocessor symbol for verilog source imports.
        """
    }

    cfg['ydir'] = {
        'switch': "-y <dir>",
        'type': '[dir]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Module Search Paths',
        'example': ["cli: -y './mylib'",
                    "api: chip.set('ydir','./mylib')"],
        'help': """
        Provides a search paths to look for modules found in the the source
        list. The import engine will look for modules inside files with the
        specified +libext+ param suffix
        """
    }

    cfg['idir'] = {
        'switch': "+incdir+<dir>",
        'type': '[dir]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Include Search Paths',
        'example': ["cli: '+incdir+./mylib'",
                    "api: chip.set('idir','./mylib')"],
        'help': """
        Provides a search paths to look for files included in the design using
        the ```include`` statement.
        """
    }

    cfg['vlib'] = {
        'switch': "-v <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Verilog Library',
        'example': ["cli: -v './mylib.v'",
                    "api: chip.set('vlib','./mylib.v')"],
        'help': """
        Declares source files to be read in, for which modules are not to be
        interpreted as root modules.
        """
    }

    cfg['libext'] = {
        'switch': "+libext+<str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Verilog File Extensions',
        'example': ["cli: +libext+sv",
                    "api: chip.set('libext','sv')"],
        'help': """
        Specifes the file extensions that should be used for finding modules.
        For example, if -y is specified as ./lib", and '.v' is specified as
        libext then the files ./lib/\\*.v ", will be searched for module matches.
        """
    }

    cfg['cmdfile'] = {
        'switch': "-f <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Verilog Options File',
        'example': ["cli: -f design.f",
                    "api: chip.set('cmdfile','design.f')"],
        'help': """
        Read the specified file, and act as if all text inside it was specified
        as command line parameters. Supported by most verilog simulators
        including Icarus and Verilator.
        """
    }

    cfg['constraint'] = {
        'switch': "-constraint <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Constraint Files',
        'example': ["cli: -constraint top.sdc",
                    "api: chip.set('constraint','top.sdc')"],
        'help': """
        List of default constraints for the design to use during compilation.
        Types of constraints include timing (SDC) and pin mappings for FPGAs.
        More than one file can be supplied. Timing constraints are global and
        sourced in all MCMM scenarios.
        """
    }

    cfg['vcd'] = {
        'switch': "-vcd <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Value Change Dump File',
        'example': ["cli: -vcd mytrace.vcd",
                    "api: chip.set('vcd','mytrace.vcd')"],
        'help': """
        A digital simulation trace that can be used to model the peak and
        average power consumption of a design.
        """
    }

    cfg['spef'] = {
        'switch': "-spef <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'SPEF File',
        'example': ["cli: -spef mydesign.spef",
                    "api: chip.set('spef','mydesign.spef')"],
        'help': """
        File containing parastics specified in the Standard Parasitic Exchange
        format. The file is used in signoff static timing analysis and power
        analysis and should be generated by an accurate parasitic extraction
        engine.
        """
    }

    cfg['sdf'] = {
        'switch': "-sdf <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'SDF File',
        'example': ["cli: -sdf mydesign.sdf",
                    "api: chip.set('sdf','mydesign.sdf')"],
        'help': """
        File containing timing data in Standard Delay Format (SDF).
        """
    }

    cfg['exclude'] = {
        'switch': "-exclude <str>",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'List of cells to exclude',
        'example': ["cli: -exclude sram_macro",
                    "api: chip.set('exclude','sram_macro')"],
        'help': """
        List of physical cells to exclude during step execution. The process
        of exclusion is controlled by the flow step and tool setup. The list
        is commonly used by DRC tools and GDS export tools to direct the tool
        to exclude GDS information during GDS merge/export.
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

    cfg['asic']['stackup'] = {
        'switch': "-asic_stackup <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Metal Stackup',
        'example': ["cli: -asic_stackup 2MA4MB2MC",
                    "api: chip.set('asic','stackup','2MA4MB2MC')"],
        'help': """
        Specifies the target stackup to use in the design. The stackup name
        must match a value defined in the pdk_stackup list.
        """
    }

    cfg['asic']['targetlib'] = {
        'switch': "-asic_targetlib <str>",
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'requirement': None,
        'short_help': 'Target Libraries',
        'example': ["cli: -asic_targetlib asap7sc7p5t_lvt",
                    "api: chip.set('asic', 'targetlib', 'asap7sc7p5t_lvt')"],
        'help': """
        A list of library names to use for synthesis and automated place and
        route. Names must match up exactly with the library name handle in the
        'stdcells' dictionary.
        """
    }

    cfg['asic']['macrolib'] = {
        'switch': "-asic_macrolib <str>",
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'requirement': None,
        'short_help': 'Macro Libraries',
        'example': ["cli: -asic_macrolib sram64x1024",
                    "api: chip.set('asic', 'macrolib', 'sram64x1024')"],
        'help': """
        A list of macro libraries to be linked in during synthesis and place
        and route. Macro libraries are used for resolving instances but are
        not used as target for automated synthesis.
        """
    }

    cfg['asic']['delaymodel'] = {
        'switch': "-asic_delaymodel <str>",
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'requirement': None,
        'short_help': 'Library Delay Model',
        'example': ["cli: -asic_delaymodel ccs",
                    "api: chip.set('asic', 'delaymodel', 'ccs')"],
        'help': """
        Specifies the delay model to use for the target libs. Supported values
        are nldm and ccs.
        """
    }

    #TODO? Change to dictionary
    cfg['asic']['ndr'] = {}
    cfg['asic']['ndr']['default'] = {
        'switch': "-asic_ndr 'netname <(float,float)>",
        'type': '(float,float)',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Non-default net width',
        'example': ["cli: -asic_ndr_width 'clk (0.2,0.2)",
                    "api: chip.set('asic','ndr','clk', (0.2,0.2))"],
        'help': """
        Specifies a non-default routing rule for a net, specified
        as a (width,space) float tuple.
        """
    }

    cfg['asic']['minlayer'] = {
        'switch': "-asic_minlayer <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Design Minimum Routing Layer',
        'example': ["cli: -asic_minlayer m2",
                    "api: chip.set('asic', 'minlayer', 'm2')"],
        'help': """
        The minimum layer to be used for automated place and route. The layer
        can be supplied as an integer with 1 specifying the first routing layer
        in the apr_techfile. Alternatively the layer can be a string that
        matches a layer hardcoded in the pdk_aprtech file. Designers wishing to
        use the same setup across multiple process nodes should use the integer
        approach. For processes with ambigous starting routing layers, exact
        strings should be used.
        """
    }

    cfg['asic']['maxlayer'] = {
        'switch': "-asic_maxlayer <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Maximum Routing Layer',
        'example': ["cli: -asic_maxlayer m6",
                    "api: chip.set('asic', 'maxlayer', 'm6')"],
        'help': """
        The maximum layer to be used for automated place and route. The layer
        can be supplied as an integer with 1 specifying the first routing layer
        in the apr_techfile. Alternatively the layer can be a string that
        matches a layer hardcoded in the pdk_aprtech file. Designers wishing to
        use the same setup across multiple process nodes should use the integer
        approach. For processes with ambigous starting routing layers, exact
        strings should be used.
        """
    }

    cfg['asic']['maxfanout'] = {
        'switch': "-asic_maxfanout <int>",
        'type': 'int',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Maximum Fanout',
        'example': ["cli: -asic_maxfanout 64",
                    "api: chip.set('asic', 'maxfanout', '64')"],
        'help': """
        The maximum driver fanout allowed during automated place and route.
        The parameter directs the APR tool to break up any net with fanout
        larger than maxfanout into subnets and buffer.
        """
    }

    cfg['asic']['maxlength'] = {
        'switch': "-asic_maxlength <float>",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Maximum Wire Length',
        'example': ["cli: -asic_maxlength 1000",
                    "api: chip.set('asic', 'maxlength', '1000')"],
        'help': """
        The maximum total wire length allowed in design during APR. Any
        net that is longer than maxlength is broken up into segments by
        the tool.
        """
    }

    cfg['asic']['maxcap'] = {
        'switch': "-asic_maxcap <float>",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Maximum Net Capacitance',
        'example': ["cli: -asic_maxcap '0.25e-12'",
                    "api: chip.set('asic', 'maxcap', '0.25e-12')"],
        'help': """
        The maximum allowed capacitance per net. The number is specified
        in Farads.
        """
    }

    cfg['asic']['maxslew'] = {
        'switch': "-asic_maxslew <float>",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Maximum Net Slew',
        'example': ["cli: -asic_maxslew '01e-9'",
                    "api: chip.set('asic', 'maxslew', '1e-9')"],
        'help': """
        The maximum allowed capacitance per net. The number is specified
        in seconds.
        """
    }

    cfg['asic']['rclayer'] = {}
    cfg['asic']['rclayer']['default'] = {
        'switch': "-asic_rclayer 'name <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Parasitic Extraction Estimation Layer',
        'example': ["cli: -asic_rclayer 'clk m3",
                    "api: chip.set('asic', 'rclayer', 'clk', 'm3')"],
        'help': """
        The technology agnostic metal layer to be used for parasitic
        extraction estimation during APR for the wire type specified
        Current the supported wire types are: clk, data. The metal
        layers are specified as technology agnostic SC layers starting
        with m1. Actual technology metal layers are looked up through the
        'grid' dictionary.
        """
    }

    cfg['asic']['vpinlayer'] = {
        'switch': "-asic_vpinlayer <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Vertical Pin Layer',
        'example': ["cli: -asic_vpinlayer m3",
                    "api: chip.set('asic', 'vpinlayer', 'm3')"],
        'help': """
        Metal layer to use for automated vertical pin placement
        during APR.  The metal layers are specified as technology agnostic
        SC layers starting with m1. Actual technology metal layers are
        looked up through the 'grid' dictionary.
        """
    }

    cfg['asic']['hpinlayer'] = {
        'switch': "-asic_hpinlayer <str>",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'Design Horizontal Pin Layer',
        'example': ["cli: -asic_hpinlayer m2",
                    "api: chip.set('asic', 'hpinlayer', 'm2')"],
        'help': """
        Metal layer to use for automated horizontal pin placement
        during APR.  The metal layers are specified as technology agnostic
        SC layers starting with m1. Actual technology metal layers are
        looked up through the 'grid' dictionary.
        """
    }


    # For density driven floorplanning
    cfg['asic']['density'] = {
        'switch': "-asic_density <float>",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'APR Target Core Density',
        'example': ["cli: -asic_density 30",
                    "api: chip.set('asic', 'density', '30')"],
        'help': """"
        Provides a target density based on the total design cell area reported
        after synthesis. This number is used when no die size or floorplan is
        supplied. Any number between 1 and 100 is legal, but values above 50
        may fail due to area/congestion issues during apr.
        """
    }

    cfg['asic']['coremargin'] = {
        'switch': "-asic_coremargin <float>",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'APR Block Core Margin',
        'example': ["cli: -asic_coremargin 1",
                    "api: chip.set('asic', 'coremargin', '1')"],
        'help': """
        Sets the halo/margin between the core area to use for automated
        floorplanning and the outer core boundary. The value is specified in
        microns and is only used when no diesize or floorplan is supplied.
        """
    }

    cfg['asic']['aspectratio'] = {
        'switch': "-asic_aspectratio <float>",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'APR Block Aspect Ratio',
        'example': ["cli: -asic_aspectratio 2.0",
                    "api: chip.set('asic', 'aspectratio', '2.0')"],
        'help': """
        Specifies the height to width ratio of the block for automated
        floor-planning. Values below 0.1 and above 10 should be avoided as
        they will likely fail to converge during placement and routing. The
        ideal aspect ratio for most designs is 1. This value is only used when
        no diesize or floorplan is supplied.
        """
        }

    # For spec driven floorplanning
    cfg['asic']['diearea'] = {
        'switch': "-asic_diearea '<[(float,float)]'>",
        'type': '[(float,float)]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Target Die Size',
        'example': ["cli: -asic_diearea '(0,0)'",
                    "api: chip.set('asic', 'diearea', (0,0))"],
        'help': """
        Provides the outer boundary of the physical design. The number is
        provided as a tuple (x0,y0,x1,y1), where (x0, y0), specifes the lower
        left corner of the block and (x1, y1) specifies the upper right corner.
        Only rectangular blocks are supported with the diesize parameter. All
        values are specified in microns.
        """
    }

    cfg['asic']['corearea'] = {
        'switch': "-asic_corearea '<[(float,float)]'>",
        'type': '[(float,float)]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'Target Core Size',
        'example': ["cli: -asic_corearea '(0,0)'",
                    "api: chip.set('asic', 'corearea', (0,0))"],
        'help': """
        Provides the core cell area of the physical design. The number is
        provided as a tuple (x0 y0 x1 y1), where (x0, y0), specifes the lower
        left corner of the block and (x1, y1) specifies the upper right corner.
        Only rectangular blocks are supported with the diesize parameter. For
        advanced geometries and blockages, a floor-plan file should is better.
        All values are specified in microns.
        """
    }

    # Def file
    cfg['asic']['def'] = {
        'switch': "-asic_def <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Harc coded DEF floorplan',
        'example': ["cli: -asic_def 'hello.def'",
                    "api: chip.set('asic', 'def', 'hello.def')"],
        'help': """
        Provides a hard coded DEF floorplan to be used during the floorplan step
        and/or initial placement step.
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
        'switch': "-mcmm_voltage 'scenario <float>'",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'MCMM Voltage',
        'example': ["cli: -mcmm_voltage 'worst 0.9'",
                    "api: chip.set('mcmm', 'worst', 'voltage', '0.9')"],
        'help': """
        Specifies the on chip primary core operating voltage for the scenario.
        The value is specified in Volts.
        """
    }

    cfg['mcmm']['default']['temperature'] = {
        'switch': "-mcmm_temperature 'scenario <float>'",
        'type': 'float',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'MCMM Temperature',
        'example': ["cli: -mcmm_temperature 'worst 0.9'",
                    "api: chip.set('mcmm', 'worst', 'temperature', '125')"],
        'help': """
        Specifies the on chip temperature for the scenario. The value is specified in
        degrees Celsius.
        """
    }

    cfg['mcmm']['default']['libcorner'] = {
        'switch': "-mcmm_libcorner 'scenario <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'MCMM Library Corner Name',
        'example': ["cli: -mcmm_libcorner 'worst ttt'",
                    "api: chip.set('mcmm', 'worst', 'libcorner', 'ttt')"],
        'help': """
        Specifies the library corner for the scenario. The value is used to access the
        stdcells library timing model. The 'libcorner' value must match the corner
        in the 'stdcells' dictionary exactly.
        """
    }

    cfg['mcmm']['default']['opcond'] = {
        'switch': "-mcmm_libcorner 'scenario <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'MCMM Operating Condition',
        'example': ["cli: -mcmm_opcond 'worst typical_1.0'",
                    "api: chip.set('mcmm', 'worst', 'opcond', 'typical_1.0')"],
        'help': """
        Specifies the operating condition for the scenario. The value can be used
        to access specific conditions within the library timing models of the
        'target_libs'. The 'opcond' value must match the corner in the
        timing model.
        """
    }

    cfg['mcmm']['default']['pexcorner'] = {
        'switch': "-mcmm_pexcorner 'scenario <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'MCMM PEX Corner Name',
        'example': ["cli: -mcmm_pexcorner 'worst max'",
                    "api: chip.set('mcmm','worst','pexcorner','max')"],
        'help': """
        Specifies the parasitic corner for the scenario. The 'pexcorner' string must
        match the value 'pdk','pexmodel' dictionary exactly.
        """
    }

    cfg['mcmm']['default']['mode'] = {
        'switch': "-mcmm_mode 'scenario <str>'",
        'type': 'str',
        'lock': 'false',
        'requirement': None,
        'defvalue': None,
        'short_help': 'MCMM Mode Name',
        'example': ["cli: -mcmm_mode 'worst test'",
                    "api: chip.set('mcmm', 'worst', 'mode', 'test')"],
        'help': """
        Specifies the operating mode for the scenario. Operating mode strings can be
        values such as "test, functional, standby".
        """
    }

    cfg['mcmm']['default']['constraint'] = {
        'switch': "-mcmm_mode 'scenario <file>'",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': None,
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'defvalue': [],
        'short_help': 'MCMM Timing Constraints',
        'example': ["cli: -mcmm_constraint 'worst hello.sdc'",
                    "api: chip.set('mcmm','worst','constraint','hello.sdc')"],
        'help': """
        Specifies a list of timing contstraint files to use for the scenario.
        The values are combined with any constraints specified by the design
        'constraint' parameter. If no constraints are found, a default constraint
        file is used based on the clock definitions.
        """
    }

    cfg['mcmm']['default']['check'] = {
        'switch': "-mcmm_check 'scenario <str>'",
        'type': '[str]',
        'lock': 'false',
        'requirement': None,
        'defvalue': [],
        'short_help': 'MCMM Checks',
        'example': ["cli: -mcmm_check 'worst check setup'",
                    "api: chip.set('mcmm','worst','check','setup')"],
        'help': """
        Specifies a list of checks for to perform for the scenario aligned. The checks
        must align with the capabilities of the EDA tools. Checks generally include
        objectives like meeting setup and hold goals and minimize power.
        Standard check names include setup, hold, power, noise, reliability.
        """
    }

    return cfg
