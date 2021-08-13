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

    # Run status
    cfg = schema_status(cfg)

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
    valuetype =type(value)
    if (not re.match(r'\[',cfg['type'])) & (valuetype==list):
        errormsg = "Value should be a scalar."
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
                if cfgtype == 'float4':
                    if (len(valuelist) != 1):
                        errormsg = "Value should be entered as a single string."
                        ok = False
                    else:
                        float4list = valuelist[0].split()
                        if (len(float4list) != 4):
                            errormsg = "String should be string with 4 space separated values."
                            ok = False
                        else:
                            for num in float4list:
                                try:
                                    float(num)
                                except ValueError:
                                    errormsg = "Type mismatch. String cannot be cast to float."
                                    ok = False
                elif cfgtype == 'bool':
                    if not item in ['true', 'false']:
                        errormsg = "Valid boolean values are True/False/'true'/'false'"
                        ok = False
                elif cfgtype == 'file':
                    if not os.path.isfile(schema_path(item)):
                        errormsg = "Invalid path or missing file."
                        ok = False
                elif cfgtype == 'dir':
                    if not os.path.isdir(schema_path(item)):
                        errormsg = "Invalid path or missing directory."
                        ok = False
                elif (cfgtype == 'float'):
                    try:
                        float(item)
                    except:
                        errormsg = "Type mismatch. Cannot cast iteme to float."
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


def schema_reorder_keys(param_help, item):
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
        'switch': '-fpga_arch',
        'requirement': 'fpga',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'FPGA Architecture File',
        'param_help': "fpga arch <file>",
        'example': ["cli: -fpga_arch myfpga.xml",
                    "api:  chip.set('fpga', 'arch', 'myfpga.xml')"],
        'help': """
        Architecture definition file for the FPGA place and route tool. In the
        Verilog To Routing case, tjhe file is an XML based description,
        allowing targeting a large number of virtual and commercial
        architectures. `More information... <https://verilogtorouting.org>`_
        """
    }

    cfg['fpga']['vendor'] = {
        'switch': '-fpga_vendor',
        'requirement': '!fpga_xml',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'FPGA Vendor Name',
        'param_help': "fpga vendor <str>",
        'example': ["cli: -fpga_vendor acme",
                    "api:  chip.set('fpga', 'vendor', 'acme')"],
        'help': """
        Name of the FPGA vendor. Use to check part name and to select
        the eda tool flow in case 'edaflow' is unspecified.
        """
    }

    cfg['fpga']['partname'] = {
        'switch': '-fpga_partname',
        'requirement': '!fpga_xml',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'FPGA Part Name',
        'param_help': "fpga partname <str>",
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
        'switch': '-pdk_foundry',
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Foundry Name',
        'param_help': "pdk foundry <str>",
        'example': ["cli: -pdk_foundry virtual",
                    "api:  chip.set('pdk', 'foundry', 'virtual')"],
        'help': """
        The official foundry company name. For example: intel, gf, tsmc,
        samsung, skywater, virtual. The \'virtual\' keyword is reserved for
        simulated non-manufacturable processes such as freepdk45 and asap7.
        """
    }

    cfg['pdk']['process'] = {
        'switch': '-pdk_process',
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Name',
        'param_help': "pdk process <str>",
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
        'switch': '-pdk_node',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Node',
        'param_help': "pdk node <num>",
        'example': ["cli: -pdk_node 130",
                    "api:  chip.set('pdk', 'node', '130')"],
        'help': """
        Approximate relative minimum dimension of the process target. A
        required parameter in some reference flows that leverage the value to
        drive technology dependent synthesis and APR optimization. Node
        examples include 180nm, 130nm, 90nm, 65nm, 45nm, 32nm, 22nm, 14nm,
        10nm, 7nm, 5nm, 3nm. The value entered implies nanometers.
        """
    }

    cfg['pdk']['wafersize'] = {
        'switch': '-pdk_wafersize',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Wafer Size',
        'param_help': "pdk wafersize <num>",
        'example': ["cli: -pdk_wafersize 300",
                    "api:  chip.set('pdk', 'wafersize', '300')"],
        'help': """
        Wafer diameter used in manufacturing specified in mm. The standard
        diameter for leading edge manufacturing is generally 300mm. For older
        process technologies and speciality fabs, smaller diameters such as
        200, 100, 125, 100 are more common. The value is used to calculate
        dies per wafer and full factory chip costs.
        """
    }

    cfg['pdk']['wafercost'] = {
        'switch': '-pdk_wafercost',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Wafer Cost',
        'param_help': "pdk wafercost <num>",
        'example': ["cli: -pdk_wafercost 10000",
                    "api:  chip.set('pdk', 'wafercost', '10000')"],
        'help': """
        Raw cost per wafer purchased specified in USD, not accounting for
        yield loss. The values is used to calculate chip full factory costs.
        """
    }

    cfg['pdk']['d0'] = {
        'switch': '-pdk_d0',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Defect Density',
        'param_help': "pdk d0 <num>",
        'example': ["cli: -pdk_d0 0.1",
                    "api:  chip.set('pdk', 'd0', '0.1')"],
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
        'switch': '-pdk_hscribe',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Horizontal Scribeline',
        'param_help': "pdk hscribe <num>",
        'example': ["cli: -pdk_hscribe 0.1",
                    "api:  chip.set('pdk', 'hscribe', '0.1')"],
        'help': """
        Width of the horizonotal scribe line (in mm) used during die separation.
        The process is generally complted using a mecanical saw, but can be
        done through combinations of mechanical saws, lasers, wafer thinning,
        and chemical etching in more advanced technolgoies. The value is used
        to calculate effective dies per wafer and full factory cost.
        """
    }

    cfg['pdk']['vscribe'] = {
        'switch': '-pdk_vscribe',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Horizontal Scribeline',
        'param_help': "pdk vscribe <num>",
        'example': ["cli: -pdk_vscribe 0.1",
                    "api:  chip.set('pdk', 'vscribe', '0.1')"],
        'help': """
        Width of the vertical scribe line (in mm) used during die separation.
        The process is generally complted using a mecanical saw, but can be
        done through combinations of mechanical saws, lasers, wafer thinning,
        and chemical etching in more advanced technolgoies. The value is used
        to calculate effective dies per wafer and full factory cost.
        """
    }

    cfg['pdk']['edgemargin'] = {
        'switch': '-pdk_edgemargin',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Wafer Edge Margin',
        'param_help': "pdk edgemargin <num>",
        'example': ["cli: -pdk_edgemargin 1",
                    "api:  chip.set('pdk', 'edgemargin', '1')"],
        'help': """
        Keepout distance/margin (in mm) from the wafer edge prone to chipping
        and poor yield. The value is used to calculate effective dies per
        wafer and full factory cost.
        """
    }

    cfg['pdk']['density'] = {
        'switch': '-pdk_density',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Transistor Density',
        'param_help': "pdk density <num>",
        'example': ["cli: -pdk_density 100e6",
                    "api:  chip.set('pdk', 'density', '10e6')"],
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
        'switch': '-pdk_sramsize',
        'requirement': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process SRAM Bitcell Size',
        'param_help': "pdk sramsize <num>",
        'example': ["cli: -pdk_sramsize 0.032",
                    "api:  chip.set('pdk', 'sramcell', '0.026')"],
        'help': """
        Area of an SRAM bitcell expressed in um^2. The value can be found
        in the PDK and  is used to normalize the effective density reported
        enable technology portable floor-plans.
        """
    }

    cfg['pdk']['rev'] = {
        'switch': '-pdk_rev',
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Process Revision',
        'param_help': "pdk rev <str>",
        'example': ["cli: -pdk_rev 1.0",
                    "api:  chip.set('pdk', 'rev', '1.0')"],
        'help': """
        Alphanumeric string specifying the revision of the current PDK.
        Verification of correct PDK and IP revisions revisions is an ASIC
        tapeout requirement in all commercial foundries. The value is used
        to for design manifest tracking and tapeout checklists.
        """
    }

    cfg['pdk']['drm'] = {
        'switch': '-pdk_drm',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'PDK Design Rule Manual',
        'param_help': "pdk drm <file>",
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
        'switch': '-pdk_doc',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'PDK Documents',
        'param_help': "pdk doc <file>",
        'example': ["cli: -pdk_doc asap7_userguide.pdf",
                    "api: chip.add('pdk', 'doc', 'asap7_userguide.pdf')"],
        'help': """
        A list of critical PDK designer documents provided by the foundry
        entered in order of priority. The first item in the list should be the
        primary PDK user guide. The purpose of the list is to serve as a
        central record for all must-read PDK documents.
        """
    }

    cfg['pdk']['stackup'] = {
        'switch': '-pdk_stackup',
        'requirement': 'asic',
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Process Metal Stackups',
        'param_help': "pdk stackup <str>",
        'example': ["cli: -pdk_stackup 2MA4MB2MC",
                    "api: chip.add('pdk', 'stackup', '2MA4MB2MC')"],
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
        'switch': '-pdk_devicemodel',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Device Models',
        'param_help': "pdk devicemodel stackvar typevar toolvar <file>",
        'example': [
            "cli: -pdk_devicemodel 'M10 spice xyce asap7.sp'",
            "api: chip.add('pdk','devicemodel','M10','spice','xyce','asap7.sp')"],
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
        'switch': '-pdk_pexmodel',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Parasitic TCAD Models',
        'param_help': "pdk pexmodel stackvar cornervar toolvar <file>",
        'example': [
            "cli: -pdk_pexmodel 'M10 max fastcap wire.mod'",
            "api: chip.add('pdk','pexmodel','M10','max','fastcap','wire.mod')"],
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
        'switch': '-pdk_layermap',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Mask Layer Maps',
        'param_help': "pdk layermap stackvar srcvar dstvar <file>",
        'example': [
            "cli: -pdk_layermap 'M10 klayout gds asap7.map'",
            "api: chip.add('pdk','layermap','M10','klayout','gds','asap7.map')"],
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
        'switch': '-pdk_display',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Display Configurations',
        'param_help': "pdk display stackvar toolvar formatvar <file>",
        'example': [
            "cli: -pdk_display 'M10 klayout python display.lyt'",
            "api: chip.add('pdk','display','M10','klayout','python','display.cfg')"],
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
        'switch': '-pdk_plib',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Primitive Libraries',
        'param_help': "pdk plib stackvar toolvar formatvar <file>",
        'example': [
            "cli: -pdk_plib 'M10 klayout oa ~/devlib'",
            "api: chip.add('pdk','plib','M10','klayout','oa','~/devlib')"],
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
        'switch': '-pdk_aprtech',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'APR Technology File',
        'param_help': "pdk aprtech stackvar libtypevar filetypevar <file>",
        'example': [
            "cli: -pdk_aprtech 'M10 12t lef tech.lef'",
            "api: chip.add('pdk','aprtech','M10','12t','lef','tech.lef')"],
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
        'switch': '-pdk_grid_name',
        'requirement': 'optional',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Name Map',
        'param_help': "pdk grid stackvar layervar name <str>",
        'example': ["""cli: -pdk_grid_name 'M10 m1 metal1'""",
                    "api: chip.add('pdk', 'grid', 'M10', 'm1', 'name',"
                    "'metal1')"],
        'help': """
        Map betwen the custom PDK metal names found in the tech,lef and the
        SC standardized metal naming schem that starts with m1 (lowest
        routing layer) and ends with mN (highest routing layer). The map is
        specified on a per metal stack basis.
        """
    }
    # Vertical Grid
    cfg['pdk']['grid']['default']['default']['xpitch'] = {
        'switch': '-pdk_grid_xpitch',
        'requirement': 'optional',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Horizontal Grid',
        'param_help': "pdk grid stackvar layervar xpitch <num>",
        'example': ["""cli: -pdk_grid_xpitch 'M10 m1 0.5'""",
                    "api: chip.add('pdk','grid','M10','m1','xpitch',"
                    "'0.5')"],
        'help': """
        Defines the routing pitch for vertical wires on a per stackup and
        per metal basis. Values are specified in um. Metal layers are ordered
        from m1 to mn, where m1 is the lowest routing layer in the tech.lef.
        """
    }

    # Horizontal Grid
    cfg['pdk']['grid']['default']['default']['ypitch'] = {
        'switch': '-pdk_grid_ypitch',
        'requirement': 'optional',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Vertical Grid',
        'param_help': "pdk grid stackvar layervar ypitch <num>'",
        'example': ["""cli: -pdk_grid_ypitch 'M10 m2 0.5'""",
                    "api: chip.add('pdk','grid','M10','m2','ypitch',"
                    "'0.5')"],
        'help': """
        Defines the routing pitch for horizontal wires on a per stackup and
        per metal basis. Values are specified in um. Metal layers are ordered
        from m1 to mn, where m1 is the lowest routing layer in the tech.lef.
        """
    }

    # Vertical Grid Offset
    cfg['pdk']['grid']['default']['default']['xoffset'] = {
        'switch': '-pdk_grid_xoffset',
        'requirement': 'optional',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Preferred Direction',
        'param_help': "pdk grid stackvar layervar xoffset <num>",
        'example': ["""cli: -pdk_grid_xoffset 'M10 m2 0.5'""",
                    "api: chip.add('pdk','grid','M10','m2','xoffset',"
                    "'0.5')"],
        'help': """
        Defines the grid offset of a vertical metal layer specified on a per
        stackup and per metal basis. Values are specified in um.
        """
    }

    # Horizontal Grid Offset
    cfg['pdk']['grid']['default']['default']['yoffset'] = {
        'switch': '-pdk_grid_yoffset',
        'requirement': 'optional',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Preferred Direction',
        'param_help': "pdk grid stackvar layervar yoffset <num>",
        'example': ["""cli: -pdk_grid_yoffset 'M10 m2 0.5'""",
                    "api: chip.add('pdk','grid','M10','m2','yoffset',"
                    "'0.5')"],
        'help': """
        Defines the grid offset of a horizontal metal layer specified on a per
        stackup and per metal basis. Values are specified in um.
        """
    }

    # Routing Layer Adjustment
    cfg['pdk']['grid']['default']['default']['adj'] = {
        'switch': '-pdk_grid_adj',
        'requirement': 'optional',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Routing Adjustment',
        'param_help': "pdk grid stackvar layervar adj <num>",
        'example': ["""cli: -pdk_grid_adj 'M10 m2 0.5'""",
                    "api: chip.set('pdk','grid','M10','m2','adj',"
                    "'0.5')"],
        'help': """
        Defines the routing resources adjustments for the design on a per layer
        basis. The value is expressed as a fraction from 0 to 1. A value of
        0.5 reduces the routing resources by 50%.
        """
    }

    # Routing Layer Capacitance
    cfg['pdk']['grid']['default']['default']['cap'] = {
        'switch': '-pdk_grid_cap',
        'requirement': 'optional',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Routing Layer Capacitance',
        'param_help': "pdk grid stackvar layervar cap <num>",
        'example': ["""cli: -pdk_grid_cap 'M10 m2 0.2'""",
                    "api: chip.set('pdk','grid','M10','m2','cap',"
                    "0.2')"],
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
        'switch': '-pdk_grid_res',
        'requirement': 'optional',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Routing Layer Resistance',
        'param_help': "pdk grid stackvar layervar res <num>",
        'example': ["""cli: -pdk_grid_res 'M10 m2 0.2'""",
                    "api: chip.set('pdk','grid','M10','m2','res',"
                    "'0.2')"],
        'help': """
        Resistance of a wire defined by the grid width and spacing values
        in the 'grid' structure.  The value is specifed as ohms/um. The number
        is only meant to be used as a sanity check and for coarse design
        planning. Accurate analysis should use the PEX models.
        """
    }

    # Wire Temperature Coefficient
    cfg['pdk']['grid']['default']['default']['tcr'] = {
        'switch': '-pdk_grid_tcr',
        'requirement': 'optional',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Grid Layer Temperature Coefficent',
        'param_help': "pdk grid stackvar layervar tcr <num>",
        'example': ["""cli: -pdk_grid_tcr 'M10 m2 0.1'""",
                    "api: chip.set('pdk','grid','M10','m2','tcr',"
                    "'0.1')"],
        'help': """
        Temperature coefficient of resistance of the wire defined by the grid
        width and spacing values in the 'grid' structure. The value is specifed
        in %/ deg C. The number is only meant to be used as a sanity check and
        for coarse design planning. Accurate analysis should use the PEX models.
        """
    }

    cfg['pdk']['tapmax'] = {
        'switch': '-pdk_tapmax',
        'requirement': 'apr',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Tap Cell Max Distance Rule',
        'param_help': "pdk tapmax <num>",
        'example': ["""cli: -pdk_tapmax 100""",
                    """api: chip.set('pdk', 'tapmax','100')"""],
        'help': """
        Maximum distance allowed between tap cells in the PDK. The value is
        required for automated place and route and is entered in micrometers.
        """
    }

    cfg['pdk']['tapoffset'] = {
        'switch': '-pdk_tapoffset',
        'requirement': 'apr',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Tap Cell Offset Rule',
        'param_help': "pdk tapoffset <num>",
        'example': ["""cli: -pdk_tapoffset 100""",
                    """api: chip.set('pdk, 'tapoffset','100')"""],
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

def schema_libs(cfg):

    cfg['library'] = {}
    cfg['library']['default'] = {}

    cfg['library']['default']['type'] = {
        'switch': '-library_type',
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Type',
        'param_help': "library libvar type <str>",
        'example': ["cli: -library_type 'mylib stdcell'",
                    "api: chip.set('library', 'mylib', 'type', 'stdcell')"],
        'help': """
        String specifying the library type. A 'stdcell' type is reserved
        for fixed height stadnard cell libraries used for synthesis and
        place and route. A 'component' type is used for everything else.
        """
    }


    cfg['library']['default']['testbench'] = {}
    cfg['library']['default']['testbench']['default'] = {
        'switch': '-library_testbench',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Testbench',
        'param_help': "library libvar testbench simvar <file>",
        'example': ["cli: -library_testbench 'mylib verilog ./mylib_tb.v'",
                    "api: chip.set('library', 'mylib', 'testbench', 'verilog, '/mylib_tb.v')"],
        'help': """
        Path to testbench specified based on a per library and per
        simluation type basis. Typical simulation types include verilog, spice.
        """
    }


    cfg['library']['default']['rev'] = {
        'switch': '-library_rev',
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Release Revision',
        'param_help': "library libvar rev <str>",
        'example': ["cli: -library_rev 'mylib 1.0'",
                    "api: chip.set('library','mylib','rev','1.0')"],
        'help': """
        String specifying revision on a per library basis. Verification of
        correct PDK and IP revisions is an ASIC tapeout requirement in all
        commercial foundries.
        """
    }

    cfg['library']['default']['origin'] = {
        'switch': '-library_origin',
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Origin',
        'param_help': "library libvar origin <str>",
        'example': ["cli: -library_origin 'mylib US'",
                    "api: chip.set('library','mylib','origin','US')"],
        'help': """
        String specifying library country of origin.
        """
    }

    cfg['library']['default']['license'] = {
        'switch': '-library_license',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library License File',
        'param_help': "library libvar license <file>",
        'example': ["cli: -library_license 'mylib ./LICENSE'",
                    "api: chip.set('library','mylib','license','./LICENSE')"],
        'help': """
        Filepath to library license
        """
    }

    cfg['library']['default']['doc'] = {
        'switch': '-library_doc',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Documentation',
        'param_help': "library libvar doc <file>",
        'example': ["cli: -library_doc 'lib lib_guide.pdf'",
                    "api: chip.set('library','lib','doc','lib_guide.pdf')"],
        'help': """
        A list of critical library documents entered in order of importance.
        The first item in thelist should be the primary library user guide.
        The  purpose of the list is to serve as a central record for all
        must-read PDK documents
        """
    }

    cfg['library']['default']['datasheet'] = {
        'switch': '-'+"library_datasheet",
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Datasheets',
        'param_help': "library libvar datasheet <file>",
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

    cfg['library']['default']['arch'] = {
        'switch': '-library_arch',
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Type',
        'param_help': "library libvar arch <str>",
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

    cfg['library']['default']['width'] = {
        'switch': '-library_width',
        'requirement': 'apr',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Width',
        'param_help': "library libvar width <num>",
        'example': ["cli: -library_width 'mylib 0.1'",
                    "api: chip.set('library','mylib','width', '0.1')"],

        'help': """
        Specifies the width of a unit cell. The value can usually be
        extracted automatically from the layout library but is included in the
        schema to simplify the process of creating parametrized floorplans.
        """
    }

    cfg['library']['default']['height'] = {
        'switch': '-library_height',
        'requirement': 'apr',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Height',
        'param_help': "library libvar height <num>",
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

    cfg['library']['default']['model'] = {}
    cfg['library']['default']['model']['default'] = {}

    #Operating Conditions (per corner)
    cfg['library']['default']['model']['default']['opcond'] = {
        'switch': '-library_opcond',
        'requirement': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Operating Condition',
        'param_help': "library libvar model cornervar opcond <str>",
        'example': [
            "cli: -library_opcond 'lib model ss_1.0v_125c WORST'",
            "api: chip.add('library','lib','model','ss_1.0v_125c','opcond','WORST')"],
        'help': """
        The default operating condition to use for mcmm optimization and
        signoff on a per corner basis.
        """
    }

    #Checks To Do (per corner)
    cfg['library']['default']['model']['default']['check'] = {
        'switch': '-library_check',
        'requirement': 'asic',
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Library Corner Checks',
        'param_help': "library libvar model cornervar check <str>",
        'example': [
            "cli: -library_check 'lib model ss_1.0v_125c setup'",
            "api: chip.add('library','lib','model','ss_1.0v_125c','check','setup')"],
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
    cfg['library']['default']['model']['default']['nldm'] = {}
    cfg['library']['default']['model']['default']['nldm']['default'] = {
        'switch': '-library_nldm',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library NLDM Timing Model',
        'param_help': "library libvar model cornervar nldm typevar <file>",
        'example': [
            "cli: -library_nldm 'lib model ss gz ss.lib.gz'",
            "api: chip.add('library','lib','model','ss','nldm','gz','ss.lib.gz')"],
        'help': """
        Filepaths to NLDM models. Timing files are specified on a per lib,
        per corner, and per format basis. The format is driven by EDA tool
        requirements. Examples of legal formats includ: lib, gz, bz2,
        and ldb.
        """
    }

    #CCS
    cfg['library']['default']['model']['default']['ccs'] = {}
    cfg['library']['default']['model']['default']['ccs']['default'] = {
        'switch': '-library_ccs',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library CCS Timing Model',
        'param_help': "library libvar model cornervar ccs typevar <file>",
        'example': [
            "cli: -library_ccs 'lib model ss lib.gz ss.lib.gz'",
            "api: chip.add('library','lib','model','ss','ccs','gz','ss.lib.gz')"],
        'help': """
        Filepaths to CCS models. Timing files are specified on a per lib,
        per corner, and per format basis. The format is driven by EDA tool
        requirements. Examples of legal formats includ: lib, gz, bz2,
        and ldb.
        """
    }

    #SCM
    cfg['library']['default']['model']['default']['scm'] = {}
    cfg['library']['default']['model']['default']['scm']['default'] = {
        'switch': '-library_scm',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library SCM Timing Model',
        'param_help': "library libvar model cornervar scm typevar <file>",
        'example': [
            "cli: -library_scm 'lib model ss lib.gz ss.lib.gz'",
            "api: chip.add('library','lib','model','ss', 'scm','gz','ss.lib.gz')"],
        'help': """
        Filepaths to SCM models. Timing files are specified on a per lib,
        per corner, and per format basis. The format is driven by EDA tool
        requirements. Examples of legal formats includ: lib, gz, bz2,
        and ldb.
        """
    }

    #AOCV
    cfg['library']['default']['model']['default']['aocv'] = {
        'switch': '-library_aocv',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library AOCV Timing Model',
        'param_help': "library libvar model cornervar aocv <file>",
        'example': [
            "cli: -library_aocv 'lib model ss lib.aocv'",
            "api: chip.add('library','lib','model','ss','aocv','lib_ss.aocv')"],
        'help': """
        Filepaths to AOCV models. Timing files are specified on a per lib,
        per corner basis.
        """
    }

    #APL
    cfg['library']['default']['model']['default']['apl'] = {}
    cfg['library']['default']['model']['default']['apl']['default'] = {
        'switch': '-library_apl',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library APL Power Model',
        'param_help': "library libvar model cornervar apl typevar <file>",
        'example': [
            "cli: -library_apl 'lib model ss cdev lib_tt.cdev'",
            "api: chip.add('library','lib','model','ss','apl','cdev','lib_tt.cdev')"],
        'help': """
        Filepaths to APL power models. Power files are specified on a per
        lib, per corner, and per format basis.
        """
    }

    #LEF
    cfg['library']['default']['lef'] = {
        'switch': '-library_lef',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library LEF',
        'param_help': "library libvar lef <file>",
        'example': ["cli: -library_lef 'mylib mylib.lef'",
                    "api: chip.add('library','mylib','lef','mylib.lef')"],
        'help': """
        An abstracted view of library cells that gives a complete description
        of the cell's place and route boundary, pin positions, pin metals, and
        metal routing blockages.
        """
    }

    #GDS
    cfg['library']['default']['gds'] = {
        'switch': '-library_gds',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library GDS',
        'param_help': "library libvar gds <file>",
        'example': ["cli: -library_gds 'mylib mylib.gds'",
                    "api: chip.add('library','mylib','gds','mylib.gds')"],
        'help': """
        The complete mask layout of the library cells ready to be merged with
        the rest of the design for tapeout. In some cases, the GDS merge
        happens at the foundry, so inclusion of CDL files is optional. In all
        cases, where the CDL are available they should specified here to
        enable LVS checks pre tapout
        """
    }

    cfg['library']['default']['netlist'] = {
        'switch': '-library_netlist',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Netlist',
        'param_help': "library libvar netlist <file>",
        'example': ["cli: -library_netlist 'mylib mylib.cdl'",
                    "api: chip.add('library','mylib','netlist','mylib.cdl')"],
        'help': """
        Files containing the netlist used for layout versus schematic (LVS)
        checks. For transistor level libraries such as standard cell libraries
        and SRAM macros, this should be a CDL type netlist. For higher level
        modules like place and route blocks, it should be a verilog gate
        level netlist.
        """
    }
    cfg['library']['default']['spice'] = {}
    cfg['library']['default']['spice']['default'] = {
        'switch': '-library_spice',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Spice Netlist',
        'param_help': "library libvar spice format <file>",
        'example': ["cli: -library_spice 'mylib pspice mylib.sp'",
                    "api: chip.add('library','mylib','spice', 'pspice',"
                    "'mylib.sp')"],
        'help': """
        Files containing library spice netlists used for circuit
        simulation, specified on a per format basis.
        """
    }
    cfg['library']['default']['hdl'] = {}
    cfg['library']['default']['hdl']['default'] = {
        'switch': '-library_hdl',
        'requirement': 'asic',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library HDL Model',
        'param_help': "library libvar hdl formatvar <file>",
        'example': ["cli: -library_hdl 'mylib verilog mylib.v'",
                    "api: chip.add('library','mylib','hdl', 'verilog',"
                    "'mylib.v')"],
        'help': """
        Library HDL models, specifed on a per format basis. Examples
        of legal formats include Verilog,  VHDL.
        """
    }

    cfg['library']['default']['atpg'] = {
        'switch': '-library_atpg',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library ATPG Model',
        'param_help': "library libvar atpg <file>",
        'example': ["cli: -library_atpg 'mylib atpg mylib.atpg'",
                    "api: chip.add('library','mylib','atpg','mylib.atpg')"],
        'help': """
        Library models used for ATPG based automated faultd based post
        manufacturing testing.
        """
    }

    cfg['library']['default']['pgmetal'] = {
        'switch': '-library_pgmetal',
        'requirement': 'optional',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Power/Ground Layer',
        'param_help': "library libvar pgmetal <str>",
        'example': ["cli: -library_pgmetal 'mylib m1'",
                    "api: chip.add('library','mylib','pgmetal','m1')"],
        'help': """
        Specifies the top metal layer used for power and ground routing within
        the library. The parameter can be used to guide cell power grid hookup
        by APR tools.
        """
    }

    cfg['library']['default']['tag'] = {
        'switch': '-library_tag',
        'requirement': 'optional',
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Library Identifier Tags',
        'param_help': "library libvar tag <str>",
        'example': ["cli: -library_tag 'mylib virtual'",
                    "api: chip.add('library','mylib','tag','virtual')"],
        'help': """
        Marks a library with a set of tags that can be used by the designer
        and EDA tools for optimization purposes. The tags are meant to cover
        features not currently supported by built in EDA optimization flows,
        but which can be queried through EDA tool TCL commands and lists.
        The example below demonstrates tagging the whole library as virtual.
        """
    }

    cfg['library']['default']['driver'] = {
        'switch': '-library_driver',
        'requirement': 'asic',
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Library Default Driver Cell',
        'param_help': "library libvar driver <str>",
        'example': ["cli: -library_driver 'mylib BUFX1'",
                    "api: chip.add('library','mylib','driver','BUFX1')"],
        'help': """
        The name of a library cell to be used as the default driver for
        block timing constraints. The cell should be strong enough to drive
        a block input from another block including wire capacitance.
        In cases where the actual driver is known, the actual driver cell
        should be used.
        """
    }

    cfg['library']['default']['site'] = {
        'switch': '-library_site',
        'requirement': 'optional',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'short_help': 'Library Site/Tile Name',
        'param_help': "library libvar site <str>",
        'example': ["cli: -library_site 'mylib core'",
                    "api: chip.add('library','mylib','site','core')"],
        'help': """
        Provides the primary site name to use for placement.
        """
    }

    cfg['library']['default']['cells'] = {}
    cfg['library']['default']['cells']['default'] = {
        'switch': '-library_cells',
        'requirement': 'optional',
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'short_help': 'Library Cell Lists',
        'param_help': "library libvar cells groupvar <str>",
        'example': ["cli: -library_cells 'mylib dontuse *eco*'",
                    "api: chip.add('library','mylib','cells','dontuse',"
                    "'*eco*')"],
        'help': """
        A named list of cells grouped by a property that can be accessed
        directly by the designer and EDA tools. The example below shows how
        all cells containing the string 'eco' could be marked as dont use
        for the tool.
        """
    }

    cfg['library']['default']['layoutdb'] = {}
    cfg['library']['default']['layoutdb']['default'] = {}
    cfg['library']['default']['layoutdb']['default']['default'] = {
        'switch': '-library_layoutdb',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Library Layout Database',
        'param_help': "library libvar layoutdb stackvar formatvar <file>",
        'example': ["cli: -library_layoutdb 'mylib M10 oa /disk/mylibdb'",
                    "api: chip.add('library','mylib','layoutdb','M10',"
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

    if not 'flowgraph' in cfg:
        cfg['flowgraph'] = {}
    cfg['flowgraph'][step] = {}


    # Flow graph definition
    cfg['flowgraph'][step]['input'] = {
        'switch': '-flowgraph_input',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': [],
        'short_help': 'Flowgraph Step Input',
        'param_help': "flowgraph stepvar input <str>",
        'example': ["cli: -flowgraph_input 'cts place'",
                    "api:  chip.set('flowgraph', 'cts', 'input', 'place')"],
        'help': """
        List of input step dependancies for the current step.
        """
    }

    # Flow graph score weights
    cfg['flowgraph'][step]['weight'] = {}
    cfg['flowgraph'][step]['weight']['default'] = {
        'switch': '-flowgraph_weight',
        'type': '[float]',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': [],
        'short_help': 'Flowgraph Metric Weights',
        'param_help': "flowgraph stepvar input <str>",
        'example': ["cli: -flowgraph_weight 'cts area_cells 1.0'",
                    "api:  chip.set('flowgraph', 'cts', 'weight', 'are_cells', '1.0')"],
        'help': """
        Weights specified on a per step and per metric basis used to give
        effective "goodnes" score for a step by calculating the sum all step
        real metrics results by the corresponding per step weights.
        """
    }



    # Step tool
    cfg['flowgraph'][step]['tool'] = {
        'switch': '-flowgraph_tool',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Flowgraph Tool Selection',
        'param_help': "flowgraph stepvar tool <str>",
        'example': ["cli: -flowgraph_tool 'place openroad'",
                    "api: chip.set('flowgraph', 'place', 'tool', 'openroad')"],
        'help': """
        Name of the EDA tool to use for a specific step in the exeecution flow
        graph.
        """
    }

    # Step showtool
    cfg['flowgraph'][step]['showtool'] = {
        'switch': '-flowgraph_showtool',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Flowgraph Show Tool Selection',
        'param_help': "flowgraph stepvar showtool <str>",
        'example': ["cli: -flowgraph_showtool 'place openroad'",
                    "api: chip.set('flowgraph', 'place', 'showtool', 'openroad')"],
        'help': """
        Name of the tool to use for showing the output file for a specific step in
        the exeecution flowgraph.
        """
    }

    return cfg

###########################################################################
# EDA Tool Setup
###########################################################################

def schema_eda(cfg):


    tool = 'default'
    step = 'default'

    cfg['eda'] = {}
    cfg['eda'][tool] = {}
    cfg['eda'][tool][step] = {}

    # exe
    cfg['eda'][tool][step]['exe'] = {
        'switch': '-eda_exe',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Executable Name',
        'param_help': "eda toolvar stepvar exe <str>",
        'example': ["cli: -eda_exe 'cts openroad'",
                    "api:  chip.set('eda', 'cts', 'exe', 'openroad')"],
        'help': """
        Name of the exuctable step or the full path to the executable
        specified on a per tool and step basis.
        """
    }

    # exe vendor
    cfg['eda'][tool][step]['vendor'] = {
        'switch': '-eda_vendor',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Tool Vendor',
        'param_help': "eda toolvar stepvar vendor <str>",
        'example': ["cli: -eda_vendor 'yosys syn yosys'",
                    "api: chip.set('eda','yosys,'syn','vendor','yosys')"],
        'help': """
        Name of the tool vendor specified on a per tool and step basis.
        Parameter can be used to set vendor specific technology variables
        in the PDK and libraries. For open source projects, the project
        name should be used in place of vendor.
        """
    }

    # exe version
    cfg['eda'][tool][step]['version'] = {
        'switch': '-eda_version',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Executable Version',
        'param_help': "eda toolvar version <str>",
        'example': ["cli: -eda_version 'cts 1.0'",
                    "api:  chip.set('eda', 'cts', 'version', '1.0')"],
        'help': """
        Version of the tool executable specified on a per tool and per step
        basis. Mismatch between the step specifed and the step avalable results
        in an error.
        """
    }

    # options
    cfg['eda'][tool][step]['option'] = {}
    cfg['eda'][tool][step]['option']['default'] = {
        'switch': '-eda_option',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Executable Options',
        'param_help': "eda toolvar stepvar option optvar <str>",
        'example': ["cli: -eda_option 'cts cmdline -no_init'",
                    "api:  chip.set('eda', 'cts', 'option', 'cmdline', '-no_init')"],
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

    # refdir
    cfg['eda'][tool][step]['refdir'] = {
        'switch': '-eda_refdir',
        'type': 'dir',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Reference Directory',
        'param_help': "eda toolvar stepvar refdir <file>",
        'example': ["cli: -eda_refdir 'yosys syn ./myref'",
                    "api:  chip.set('eda', 'yosys', 'syn', './myref')"],
        'help': """
        Path to directories  containing compilation scripts, specified
        on a per step basis.
        """
    }

    # entry point scripts
    cfg['eda'][tool][step]['script'] = {
        'switch': '-eda_script',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Entry Point script',
        'param_help': "eda toolvar stepvar script <file>",
        'example': ["cli: -eda_script 'yosys syn syn.tcl'",
                    "api: chip.set('eda', 'yosys','syn','script','syn.tcl')"],
        'help': """
        Path to the entry point compilation script called by the executable,
        specified on a per tool and per step basis.
        """
    }

    # pre execution script
    cfg['eda'][tool][step]['prescript'] = {
        'switch': '-eda_prescript',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Pre step script',
        'param_help': "eda toolvar stepvar prescript <file>",
        'example': ["cli: -eda_prescript 'yosys syn pre.tcl'",
                    "api: chip.set('eda', 'yosys','syn','prescript','pre.tcl')"],
        'help': """
        Path to a user supplied script to execute after reading in the design
        but before the main execution stage of the step. Exact entry point
        depends on the step and main script being executed. An example
        of a prescript entry point would be immediately before global
        placement.
        """
    }

    # post execution script
    cfg['eda'][tool][step]['postcript'] = {
        'switch': '-eda_postscript',
        'requirement': 'optional',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Post step script',
        'param_help': "eda toolvar stepvar postscript <file>",
        'example': ["cli: -eda_postscript 'yosys syn post.tcl'",
                    "api: chip.set('eda', 'yosys','syn','postscript','post.tcl')"],
        'help': """
        Path to a user supplied script to execute after reading in the design
        but before the main execution stage of the step. Exact entry point
        depends on the step and main script being executed. An example
        of a postscript entry point would be immediately after global
        placement.
        """
    }

    # copy
    cfg['eda'][tool][step]['copy'] = {
        'switch': '-eda_copy',
        'type': 'bool',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': "false",
        'short_help': 'Copy Local Option',
        'param_help': "eda toolvar stepvar copy <bool>",
        'example': ["cli: -eda_copy 'openroad cts true'",
                    "api: chip.set('eda', 'openroad', 'cts','copy','true')"],
        'help': """
        Specifies that the reference script directory should be copied and run
        from the local run directory. The option is specified on a per tool and
        per step basis.
        """
    }

    # script format
    cfg['eda'][tool][step]['format'] = {
        'switch': '-eda_format',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Script Format',
        'param_help': "eda toolvar stepvar format <str>",
        'example': ["cli: -eda_format 'openroad cts tcl'",
                    "api: chip.set('eda','openroad, 'cts','format','tcl')"],
        'help': """
        Format of the configuration file specified on a per tool and per
        step basis. Valid formats depend on the type of tool. Supported formats
        include tcl, yaml, json, command line.
        """
    }

    # parallelism
    cfg['eda'][tool][step]['threads'] = {
        'switch': '-eda_threads',
        'type': 'int',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Job Parallelism',
        'param_help': "eda toolvar stepvar threads <num>",
        'example': ["cli: -eda_threads 'magic drc 64'",
                    "api: chip.set('eda','magic', 'drc','threads','64')"],
        'help': """
        Thread parallelism to use for execution specified on a per tool and per
        step basis. If not specified, SC queries the operating system and sets
        the threads based on the maximum thread count supported by the
        hardware.
        """
    }

    # warnings
    cfg['eda'][tool][step]['woff'] = {
        'switch': '-eda_woff',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Warning Filter',
        'param_help': "eda toolvar stepvar woff <file>",
        'example': ["cli: -eda_woff 'verilator import COMBDLY'",
                    "api: chip.set('eda','verilator', 'import','woff','COMBDLY')"],
        'help': """
        A list of EDA warnings for which printing should be supressed specified
        on a per tool and per step basis. Generally this is done on a per
        design basis after review has determined that warning can be safely
        ignored The code for turning off warnings can be found in the specific
        tool reference manual.
        """
    }

    return cfg

###########################################################################
# Local (not global!) parameters for controllings tools
###########################################################################
def schema_arg(cfg):


    cfg['arg'] = {}

    cfg['arg']['step'] = {
        'switch': '-arg_step',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Current Execution Step',
        'param_help': "arg_step <str>",
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



    return cfg


###########################################################################
# Metrics to Track
###########################################################################

def schema_metric(cfg, group='default', step='default'):

    if not 'metric' in cfg:
        cfg['metric'] = {}
        cfg['metric'][step] = {}

    cfg['metric'][step]['default'] = {}

    cfg['metric'][step][group]['registers'] = {
        'switch': '-metric_registers',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Registers Metric',
        'param_help': 'metric stepvar stagevar registers <num>',
        'example': ["cli: -metric_"+group+"_registers 'place 100'",
                    "api: chip.add(metric,'"+group+"','place','registers','100')"],
        'help': """
        Metric tracking the total number of register cells on a per step basis.
        """
    }

    cfg['metric'][step][group]['cells'] = {
        'switch': '-metric_cells',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Cell Instances Metric',
        'param_help': 'metric stepvar stagevar cells <num>',
        'example': ["cli: -"+group+"_cells 'place 100'",
                    "api: chip.add(metric,'"+group+"','place','cells','100')"],
        'help': """
        Metric tracking the total number of instances on a per step basis.
        Total cells includes registers. In the case of FPGAs, the it
        represents the number of LUTs.
        """
    }

    cfg['metric'][step][group]['rambits'] = {
        'switch': '-metric_rambits',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total RAM Macro Bits Metric',
        'param_help': 'metric stepvar stagevar rambits <num>',
        'example': ["cli: -"+group+"_rambits 'place 100'",
                    "api: chip.add(metric,'"+group+"','place','rambits','100')"],
        'help': """
        Metric tracking the total number of RAM bits in the design
        on a per step basis. In the case of FPGAs, the it
        represents the number of bits mapped to block ram.
        """
    }

    cfg['metric'][step][group]['xtors'] = {
        'switch': '-metric_xtors',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Transistors Metric',
        'param_help': 'metric stepvar stagevar xtors <num>',
        'example': ["cli: -"+group+"_xtors 'place 100'",
                    "api: chip.add(metric,'"+group+"','place','xtors','100')"],
        'help': """
        Metric tracking the total number of transistors in the design
        on a per step basis.
        """
    }

    cfg['metric'][step][group]['nets'] = {
        'switch': '-metric_nets',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Nets Metric',
        'param_help': 'metric stepvar stagevar nets <num>',
        'example': ["cli: -"+group+"_nets 'place 100'",
                    "api: chip.add(metric,'"+group+"','place','nets','100')"],
        'help': """
        Metric tracking the total number of net segments on a per step
        basis.
        """
    }

    cfg['metric'][step][group]['pins'] = {
        'switch': '-metric_pins',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Pins Metric',
        'param_help': 'metric stepvar '+group+" stepvar pins <num>",
        'example': ["cli: -"+group+"_pins 'place 100'",
                    "api: chip.add(metric,'"+group+"','place','pins','100')"],
        'help': """
        Metric tracking the total number of I/O pins on a per step
        basis.
        """
    }

    cfg['metric'][step][group]['vias'] = {
        'switch': '-metric_vias',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Vias metric',
        'param_help': 'metric stepvar stagevar vias <num>',
        'example': ["cli: -"+group+"_vias 'route 100.00'",
                    "api: chip.add(metric,'"+group+"','place','vias','100')"],
        'help': """
        Metric tracking the total number of vias in the design.
        """
    }

    cfg['metric'][step][group]['wirelength'] = {
        'switch': '-metric_wirelength',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Wirelength Metric',
        'param_help': 'metric stepvar stagevar wirelength <num>',
        'example': ["cli: -"+group+"_wirelength 'route 100.00'",
                    "api: chip.add(metric,'"+group+"','place','wirelength','100')"],
        'help': """
        Metric tracking the total wirelength in the design in meters.
        """
    }

    cfg['metric'][step][group]['overflow'] = {
        'switch': '-metric_overflow',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Routing Overflow Metric',
        'param_help': 'metric stepvar stagevar overflow <num>',
        'example': ["cli: -"+group+"_overflow 'route 0'",
                    "api: chip.add(metric,'"+group+"','place','overflow','0')"],
        'help': """
        Metric tracking the total number of overflow tracks for the routing.
        Any non-zero number suggests an over congested design. To analyze
        where the congestion is occuring inspect the router log files for
        detailed per metal overflow reporting and open up the design to find
        routing hotspots.
        """
    }

    cfg['metric'][step][group]['area_cells'] = {
        'switch': '-metric_area_cells',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Cell Area Metric',
        'param_help': 'metric stepvar stagevar area_cells <num>',
        'example': ["cli: -"+group+"_area_cells 'place 100.00'",
                    "api: chip.add(metric,'"+group+"','place','area_cells','100.00')"],
        'help': """
        Metric tracking the sum of all cell area on a per step basis specified
        in um^2.
        """
    }

    cfg['metric'][step][group]['area_total'] = {
        'switch': '-metric_area_total',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Area Metric',
        'param_help': 'metric stepvar stagevar area_total <num>',
        'example': ["cli: -"+group+"_area_total 'place 100.00'",
                    "api: chip.add(metric,'"+group+"','place','area_total','100.00')"],
        'help': """
        Metric tracking the total physical design area on a per step basis
        specified in um^2.
        """
    }

    cfg['metric'][step][group]['area_density'] = {
        'switch': '-metric_area_density',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Area Density Metric',
        'param_help': 'metric stepvar stagevar area_density <num>',
        'example': ["cli: -"+group+"_area_density 'place 99.9'",
                    "api: chip.add(metric,'"+group+"','place','area_density','99.9')"],
        'help': """
        Metric tracking the effective area utilization/desnity calculated as the
        ratio of cell area divided by the total core area available for
        placement. Value is specified as a percentage (%) and does not include
        filler cells.
        """
    }

    cfg['metric'][step][group]['power_total'] = {
        'switch': '-metric_power_total',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Power Metric',
        'param_help': 'metric stepvar stagevar power_total <num>',
        'example': ["cli: -"+group+"_power_total 'place 0.001'",
                    "api: chip.add(metric,'"+group+"','place','power_total','0.001')"],
        'help': """
        Metric tracking the worst case total power of the design on a per
        step basis calculated based on setup config and VCD stimulus.
        stimulus. Metric unit is Watts.
        """
    }

    cfg['metric'][step][group]['power_leakage'] = {
        'switch': '-metric_power_leakage',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Leakage Power Metric',
        'param_help': 'metric stepvar stagevar power_leakage <num>',
        'example': ["cli: -"+group+"_power_leakage 'place 1e-6'",
                    "api: chip.add(metric,'"+group+"','place','power_leakage','1e-6')"],
        'help': """
        Metric tracking the leakage power of the design on a per step
        basis. Metric unit is Watts.
        """
    }

    cfg['metric'][step][group]['hold_slack'] = {
        'switch': '-metric_hold_slack',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Hold Slack Metric',
        'param_help': 'metric stepvar stagevar hold_slack <num>',
        'example': ["cli: -metric_hold_slack 'place "+group+" 0",
                    "api: chip.add(metric,'place','"+group+"','hold_slack','0')"],
        'help': """
        Metric tracking the worst hold/min timing path slack in the design.
        Positive values means there is spare/slack, negative slack means the design
        is failing a hold timing constrainng. The metric unit is nanoseconds.
        """
    }

    cfg['metric'][step][group]['hold_tns'] = {
        'switch': '-metric_hold_tns',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Hold TNS Metric',
        'param_help': 'metric stepvar stagevar hold_tns <num>',
        'example': ["cli: -"+group+"_hold_tns 'place 0'",
                    "api: chip.add(metric,'"+group+"','place','hold_tns','0')"],
        'help': """
        Metric tracking of total negative hold slack (TNS) on a per step basis.
        Metric unit is nanoseconds.
        """
    }

    cfg['metric'][step][group]['setup_slack'] = {
        'switch': '-metric_setup_slack',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Setup Slack Metric',
        'param_help': 'metric stepvar stagevar setup_slack <num>',
        'example': ["cli: -metric_setup_slack 'place "+group+" 0",
                    "api: chip.add(metric,'place','"+group+"','setup_slack','0')"],
        'help': """
        Metric tracking the worst setup/min timing path slack in the design.
        Positive values means there is spare/slack, negative slack means the design
        is failing a setup timing constrainng. The metric unit is nanoseconds.
        """
    }


    cfg['metric'][step][group]['setup_tns'] = {
        'switch': '-metric_setup_tns',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Setup TNS Metric',
        'param_help': 'metric stepvar stagevar setup_tns <num>',
        'example': ["cli: -"+group+"_setup_tns 'place 0'",
                    "api: chip.add(metric,'"+group+"','place','setup_tns','0')"],
        'help': """
        Metric tracking of total negative setup slack (TNS) on a per step basis.
        Metric unit is nanoseconds.
        """
    }

    cfg['metric'][step][group]['drv'] = {
        'switch': '-metric_drv',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Rule Violations Metric',
        'param_help': 'metric stepvar stagevar drv <num>',
        'example': ["cli: -"+group+"_drv 'dfm 0'",
                    "api: chip.add(metric,'"+group+"','dfm','drv','0')"],
        'help': """
        Metric tracking the total number of design rule violations on per step
        basis.
        """
    }

    cfg['metric'][step][group]['warnings'] = {
        'switch': '-metric_warnings',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Warnings Metric',
        'param_help': 'metric stepvar stagevar warnings <num>',
        'example': ["cli: -"+group+"_warnings 'dfm 0'",
                    "api: chip.add(metric,'"+group+"','dfm','warnings','0')"],

        'help': """
        Metric tracking the total number of warnings on a per step basis.
        """
    }

    cfg['metric'][step][group]['errors'] = {
        'switch': '-metric_errors',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Errors Metric',
        'param_help': 'metric stepvar stagevar errors <num>',
        'example': ["cli: -"+group+"_errors 'dfm 0'",
                    "api: chip.add(metric,'"+group+"','dfm','errors','0')"],
        'help': """
        Metric tracking the total number of errors on a per step basis.
        """
    }

    cfg['metric'][step][group]['runtime'] = {
        'switch': '-metric_runtime',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Runtime Metric',
        'param_help': 'metric stepvar stagevar runtime <num>',
        'example': ["cli: -"+group+"_runtime 'dfm 35.3'",
                    "api: chip.add(metric,'"+group+"','dfm','runtime','35.3')"],
        'help': """
        Metric tracking the total runtime on a per step basis. Time recorded
        as wall clock time specified in seconds.
        """
    }

    cfg['metric'][step][group]['memory'] = {
        'switch': '-metric_memory',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Total Memory Metric',
        'param_help': 'metric stepvar stagevar memory <num>',
        'example': ["cli: -"+group+"_memory 'dfm 10e6'",
                    "api: chip.add(metric,'"+group+"','dfm','memory','10e6')"],
        'help': """
        Metric tracking the total memory on a per step basis, specified
        in bytes.
        """
    }

    return cfg

###########################################################################
# Design Tracking
###########################################################################

def schema_record(cfg, step='default'):

    cfg['record'] = {}

    cfg['record'][step] = {}      # per step

    cfg['record'][step]['input'] = {
        'switch': '-record_input',
        'requirement': 'optional',
        'type': '[file]',
        'copy': 'false',
        'lock': 'false',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Step Inputs',
        'param_help': "record stepvar input <str>",
        'example': ["cli: -record_input 'package gcd.v'",
                    "api: chip.add('record','package','input','gcd.v')"],
        'help': """
        Metric tracking all input files on a per step basis. This list
        include files entered by the user and files automatically found
        by the flow like in the case of the "-y" auto-discovery path.
        """
    }

    cfg['record'][step]['author'] = {
        'switch': '-record_author',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step Author',
        'param_help': "record stepvar author <str>",
        'example': ["cli: -record_author 'dfm coyote'",
                    "api: chip.add('record','dfm','author','wcoyote')"],
        'help': """
        Metric tracking the author on a per step basis.
        """
    }

    cfg['record'][step]['userid'] = {
        'switch': '-record_userid',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step User ID',
        'param_help': "record stepvar userid <str>",
        'example': ["cli: -record_userid 'dfm 0982acea'",
                    "api: chip.add('record','dfm','userid','0982acea')"],
        'help': """
        Metric tracking the run userid on a per step basis.
        """
    }

    cfg['record'][step]['signature'] = {
        'switch': '-record_signature',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step Signature',
        'param_help': "record stepvar signature <str>",
        'example': ["cli: -record_signature 'dfm 473c04b'",
                    "api: chip.add('record','dfm','signature','473c04b')"],
        'help': """
        Metric tracking the execution signature/hashid on a per step basis.
        """
    }

    cfg['record'][step]['org'] = {
        'switch': '-record_org',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step Organization',
        'param_help': "record stepvar org <str>",
        'example': ["cli: -record_org 'dfm earth'",
                    "api: chip.add('record','dfm','org','earth')"],
        'help': """
        Metric tracking the user's organization on a per step basis.
        """
    }

    cfg['record'][step]['location'] = {
        'switch': '-record_location',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step Location',
        'param_help': "record stepvar location <str>",
        'example': ["cli: -record_location 'dfm Boston'",
                    "api: chip.add('record','dfm','location','Boston')"],
        'help': """
        Metric tracking the user's location/site on a per step basis.
        """
    }

    cfg['record'][step]['date'] = {
        'switch': '-record_date',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step Date Stamp',
        'param_help': "record stepvar date <str>",
        'example': ["cli: -record_date 'dfm 2021-05-01'",
                    "api: chip.add('record','dfm','date','2021-05-01')"],
        'help': """
        Metric tracking the run date stamp on a per step basis.
        The date format is the ISO 8601 format YYYY-MM-DD.
        """
    }

    cfg['record'][step]['time'] = {
        'switch': '-record_time',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step Time Stamp',
        'param_help': "record stepvar time <str>",
        'example': ["cli: -record_time 'dfm 11:35:40'",
                    "api: chip.add('record','dfm','time','11:35:40')"],
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
        'switch': '-mode',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': 'asic',
        'short_help': 'Compilation Mode',
        'param_help': "mode <str>",
        'example': ["cli: -mode fpga",
                    "api: chip.set('mode','fpga')"],
        'help': """
        Sets the compilation flow to 'fpga' or 'asic. The default is 'asic'
        """
    }

    cfg['target'] = {
        'switch': '-target',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Compilation Target',
        'param_help': "target <str>",
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
        'switch': '-cfg',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Configuration File',
        'param_help': "cfg <file>",
        'example': ["cli: -cfg mypdk.json",
                    "api: chip.add('cfg','mypdk.json')"],
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
        'switch': '-env',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Environment Variables',
        'param_help': "env namevar <str>",
        'example': ["cli: -env 'PDK_HOME /disk/mypdk'",
                    "api: chip.add('env', 'PDK_HOME', '/disk/mypdk')"],
        'help': """
        Certain EDA tools and reference flows require environment variables to
        be set. These variables can be managed externally or specified through
        the env variable.
        """
    }

    cfg['scpath'] = {
        'switch': '-scpath',
        'type': '[dir]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Search path',
        'param_help': "scpath <dir>",
        'example': ["cli: -scpath '/home/$USER/sclib'",
                    "api: chip.add('scpath', '/home/$USER/sclib')"],
        'help': """
        Specifies python modules paths for target import.
        """
    }

    cfg['hashmode'] = {
        'switch': '-hashmode',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'OFF',
        'short_help': 'File Hash Mode',
        'param_help': "hashmode <str>",
        'example': ["cli: -hashmode 'ALL'",
                    "api: chip.add('hashmode', 'ALL')"],
        'help': """
        The switch controls how/if setup files and source files are hashed
        during compilation. Valid entries include OFF, ALL, ACTIVE.
        ACTIVE specifies to only hash files being used in the current cfg.
        """
    }

    cfg['quiet'] = {
        'switch': '-quiet',
        'type': 'bool',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'false',
        'short_help': 'Quiet execution',
        'param_help': "quiet <bool>",
        'example': ["cli: -quiet",
                    "api: chip.set('quiet', 'true')"],
        'help': """
        Modern EDA tools print significant content to the screen. The -quiet
        option forces all steps to print to a log file. The quiet
        option is ignored when the -noexit is set to true.
        """
    }

    cfg['loglevel'] = {
        'switch': '-loglevel',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'WARNING',
        'short_help': 'Logging Level',
        'param_help': "loglevel <str>",
        'example': ["cli: -loglevel INFO",
                    "api: chip.set('loglevel', 'INFO')"],
        'help': """
        The debug param provides explicit control over the level of debug
        logging printed. Valid entries include INFO, DEBUG, WARNING, ERROR. The
        default value is WARNING.
        """
    }

    cfg['build_dir'] = {
        'switch': '-build_dir',
        'type': 'dir',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'build',
        'short_help': 'Build Directory',
        'param_help': "build_dir <build_dir>",
        'example': ["cli: -build_dir ./build_the_future",
                    "api: chip.set('build_dir','./build_the_future')"],
        'help': """
        The default build directoryis './build'. The 'dir' parameters can be
        used to set an alternate compilation directory path.
        """
    }

    cfg['jobname'] = {
        'switch': '-jobname',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'job',
        'short_help': 'Job Name Prefix',
        'param_help': "jobname <dir>",
        'example': ["cli: -jobname may1",
                    "api: chip.set('jobname','may1')"],
        'help': """
        The name of the directory to work in.
        The full directory structure is:
        'dir'/'design'/'jobname''jobid'
        """
    }

    cfg['jobid'] = {
        'switch': '-jobid',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': '1',
        'short_help': 'Job ID',
        'param_help': "jobid <num>",
        'example': ["cli: -jobid 0",
                    "api: chip.set('jobid','0')"],
        'help': """
        The id of the specific job to be exeucted.
        The directory structure is:
        'dir'/'design'/'jobname''jobid'
        """
    }

    cfg['jobincr'] = {
        'switch': '-jobincr',
        'type': 'bool',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'true',
        'short_help': 'Job ID Autoincrement Mode ',
        'param_help': "jobincr <true>",
        'example': ["cli: -jobincr",
                    "api: chip.set('jobincr','true')"],
        'help': """
        Autoincrements the jobid value based on the latest
        executed job in the design build directory. If no jobs are found,
        the value in the 'jobid' parameter is used.
        """
    }

    cfg['steplist'] = {
        'switch': '-steplist',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Compilation step list',
        'param_help': "steplist <str>",
        'example': ["cli: -steplist 'import'",
                    "api: chip.set('steplist','import')"],
        'help': """
        List of steps to execute. The default is to execute all steps defined
        in the flow graph.
        """
    }

    cfg['msgevent'] = {
        'switch': '-msgevent',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Message Event',
        'param_help': "msgevent <str>",
        'example': ["cli: -msgevent export",
                    "api: chip.set('msgevent','export')"],
        'help': """
        A list of steps after which to notify a recipient. For example if
        values of syn, place, cts are entered separate messages would be sent
        after the completion of the syn, place, and cts steps.
        """
    }

    cfg['msgcontact'] = {
        'switch': '-msgcontact',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Message Contact',
        'param_help': "msgcontact <str>",
        'example': ["cli: -msgcontact 'wile.e.coyote@acme.com'",
                    "api: chip.set('msgcontact','wile.e.coyote@acme.com')"],
        'help': """
        A list of phone numbers or email addresses to message on a event event
        within the msg_event param.
        """
    }

    cfg['optmode'] = {
        'switch': '-O',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'O0',
        'short_help': 'Optimization Mode',
        'param_help': "optmode <str>",
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
        'switch': '-relax',
        'type': 'bool',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'false',
        'short_help': 'Relaxed RTL Linting',
        'param_help': "relax <bool>",
        'example': ["cli: -relax",
                    "api: chip.set('relax', 'true')"],
        'help': """
        Specifies that tools should be lenient and supress some warnigns that
        may or may not indicate design issues. The default is to enforce strict
        checks for all steps.
        """
    }

    cfg['clean'] = {
        'switch': '-clean',
        'type': 'bool',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'false',
        'short_help': 'Keep essential files only',
        'param_help': "clean <bool>",
        'example': ["cli: -clean",
                    "api: chip.set('clean', 'true')"],
        'help': """
        Deletes all non-essential files at the end of each step and creates a
        'zip' archive of the job folder.
        """
    }

    cfg['bkpt'] = {
        'switch': '-bkpt',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': "A list of flow breakpoints",
        'param_help': "bkpt <str>",
        'example': ["cli: -bkpt place",
                    "api: chip.add('bkpt', 'place')"],
        'help': """
        Specifies a list of step stop (break) points. If the step is
        a TCL based tool, then the breakpoints stops the flow inside the EDA
        tool. If the step is a command line tool, then the flow drops into
        a Python interpreter.
        """
    }

    # Path to a config file defining multiple remote jobs to run.
    cfg['permutations'] = {
        'switch': '-permutations',
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': "Run Permutations File",
        'param_help': "permutations <file>",
        'example': ["cli: -permutations permute.py",
                    "api: chip.add('permuations', 'permute.py')"],
        'help': """
        Sets the path to a Python file containing a generator which yields
        multiple configurations of a job to run in parallel. This lets you
        sweep various configurations such as die size or clock speed.
        """
    }

    cfg['copyall'] = {
        'switch': '-copyall',
        'type': 'bool',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': 'false',
        'short_help': "Copy All Input Files to Jobdir",
        'param_help': "copyall <bool>",
        'example': ["cli: -copyall",
                    "api: chip.set('copyall', 'true')"],
        'help': """
        Specifies that all used files should be copied into the jobdir,
        overriding the per schema entry copy settings. The default
        is false.
        """
    }

    cfg['show'] = {
        'switch': '-show',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': "Display step output",
        'param_help': "show <step>",
        'example': ["cli: -show route",
                    "api: chip.set('show', 'route')"],
        'help': """
        Step output to display using thee graphical
        viewer defined by the flowgraph showtool parameter.
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
        'switch': '-remote_addr',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Remote Server Address',
        'param_help': "remote addr <str>",
        'example': ["cli: -remote_addr 192.168.1.100",
                    "api: chip.add('remote', 'addr', '192.168.1.100')"],
        'help': """
        Dicates that all steps after the compilation step should be executed
        on the remote server specified by the IP address or domain name.
        """
    }

    # Port number that the remote host is running 'sc-server' on.
    cfg['remote']['port'] = {
        'switch': '-remote_port',
        'type': 'int',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': '443',
        'short_help': 'Remote Server Port',
        'param_help': "remote port <str>",
        'example': ["cli: -remote_port 8080",
                    "api: chip.add('remote', 'port', '8080')"],
        'help': """
        Sets the server port to be used in communicating with the remote host.
        """
    }

    # Job hash. Used to resume or cancel remote jobs after they are started.
    cfg['remote']['hash'] = {
        'switch': '-remote_hash',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Job hash/UUID value',
        'param_help': "remote hash <str>",
        'example': ["cli: -remote_hash 0123456789abcdeffedcba9876543210",
                    "api: chip.set('remote', 'filehash','0123456789abcdeffedcba9876543210')"],
        'help': """
        A unique ID associated with a job run. This field should be left blank
        when starting a new job, but it can be provided to resume an interrupted
        remote job, or to clean up after unexpected failures.
        """
    }

    # Remote start step
    cfg['remote']['start'] = {
        'switch': '-remote_start',
        'type': 'str',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': 'syn',
        'short_help': 'Remote Execution Starting Step',
        'param_help': "remote start <str>",
        'example': ["cli: -remote_start syn",
                    "api: chip.add('remote', 'start', 'syn')"],
        'help': """
        Specifies which step that remote execution starts from.
        """
    }

    # Remote stop step
    cfg['remote']['stop'] = {
        'switch': '-remote_stop',
        'type': 'str',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': 'export',
        'short_help': 'Remote Execution Stop Step',
        'param_help': "remote stop <str>",
        'example': ["cli: -remote_stop export",
                    "api: chip.add('remote', 'stop', 'export')"],
        'help': """
        Specifies which step that remote execution stopns on.
        """
    }

    # Remote username
    cfg['remote']['user'] = {
        'switch': '-remote_user',
        'type': 'str',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': None,
        'short_help': 'Remote authentication username.',
        'param_help': "remote user <str>",
        'example': ["cli: -remote_user testuser",
                    "api: chip.add('remote', 'user', 'testuser')"],
        'help': """
        Specifies a username for authenticating calls with a remote server.
        """
    }

    # Remote private key file.
    cfg['remote']['key'] = {
        'switch': '-remote_key',
        'type': 'str',
        'lock': 'false',
        'copy': 'false',
        'requirement': 'remote',
        'defvalue': None,
        'short_help': 'Remote authentication private key file.',
        'param_help': "remote key <str>",
        'example': ["cli: -remote_key ~/.ssh/decrypt_key",
                    "api: chip.add('remote', 'key', './decrypt_key')"],
        'help': """
        Specifies a private key file which will allow the server to
        authenticate the given user and decrypt data associated with them.
        """
    }

    # Number of temporary hosts to request for the job. (Default: 0)
    cfg['remote']['hosts'] = {
        'switch': '-remote_hosts',
        'type': 'int',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': '0',
        'short_help': 'Number of temporary compute nodes to request.',
        'param_help': "remote hosts <num>",
        'example': ["cli: -remote_hosts 2",
                    "api: chip.add('remote', 'hosts', '2')"],
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
        'switch': '-remote_ram',
        'type': 'float',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': None,
        'short_help': 'GiB of RAM to request in temporary cloud hosts.',
        'param_help': "remote ram <num>",
        'example': ["cli: -remote_ram 16",
                    "api: chip.add('remote', 'ram', '16')"],
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
        'switch': '-remote_threads',
        'type': 'int',
        'lock': 'false',
        'requirement': 'remote',
        'defvalue': None,
        'short_help': 'Number of harts to request in each remote host.',
        'param_help': "remote threads <num>",
        'example': ["cli: -remote_threads 4",
                    "api: chip.add('remote', 'threads', '4')"],
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
# Thread safe per step runtime status
#############################################

def schema_status(cfg):

    cfg['status'] = {}
    cfg['status']['default'] = {}
    cfg['status']['default']['active'] = {
        'switch': '-status_active',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step Active Indicator',
        'param_help': "status stepvar active <bool>",
        'example': ["cli: -status_active 'syn true'",
                    "api: chip.get('status', 'syn', 'active', True)"],
        'help': """
        Status field with boolean indicating step activity. The variable is
        managed by the run function and not writable by the user.
        0 = done, !0 = active
        """
        }

    cfg['status']['default']['error'] = {
        'switch': '-status_error',
        'type': 'int',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Step Error Indicator',
        'param_help': "status stepvar active <bool>",
        'example': ["cli: -status_active 'syn true'",
                    "api: chip.get('status', 'syn', 'active', True)"],
        'help': """
        Error indicator on a per step basis. The variable is
        managed by the run function and not writable by the user.
        0 = ok, !0 = Error
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
        'switch': 'None',
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
        'param_help': "source <file>",
        'example': ["cli: hello_world.v",
                    "api: chip.add('source', 'hello_world.v')"],
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

    cfg['component'] = {
        'switch': '-component',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'all',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Component',
        'param_help': "component <file>",
        'example': ["cli: -component padring_manifest.json",
                    "api: chip.add('component', 'padring_manifest.json')"],
        'help': """
        A list of SC manifest files with with complete information needed
        to enable instantation at the current design level.
        """
    }

    cfg['repo'] = {
        'switch': '-repo',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Design Repository',
        'param_help': "rev <str>",
        'example': ["cli: -repo git@github.com:aolofsson/oh.git",
                    "api: chip.set('repo','git@github.com:aolofsson/oh.git')"],
        'help': """
        Optional address to the design repositories used in design.
        """
    }

    cfg['doc'] = {
        'switch': '-doc',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'all',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Documentation',
        'param_help': "doc <file>",
        'example': ["cli: -doc spec.pdf",
                    "api: chip.add('doc', 'spec.pdf')"],
        'help': """
        A list of design documents. Files are read in order from first to last.
        """
    }

    cfg['rev'] = {
        'switch': '-rev',
        'type': 'str',
        'lock': 'false',
        'requirement': 'all',
        'defvalue': None,
        'short_help': 'Design Revision',
        'param_help': "rev <str>",
        'example': ["cli: -rev 1.0",
                    "api: chip.add('rev', '1.0')"],
        'help': """
        Specifies the revision of the current design. Can be a branch, tag, or
        commit has or simple string.
        """
    }

    cfg['license'] = {
        'switch': '-license',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'all',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design License File',
        'param_help': "license <file>",
        'example': ["cli: -license ./LICENSE",
                    "api: chip.add('license', './LICENSE')"],
        'help': """
        Filepath to the technology license for currrent design.
        """
    }

    cfg['design'] = {
        'switch': '-design',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Top Module Name',
        'param_help': "design <str>",
        'example': ["cli: -design hello_world",
                    "api: chip.add('design', 'hello_world')"],
        'help': """
        Name of the top level design to compile. Required for all designs with
        more than one module.
        """
    }

    cfg['name'] = {
        'switch': '-name',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Package Name',
        'param_help': "name <str>",
        'example': ["cli: -name hello",
                    "api: chip.add('name', 'hello')"],
        'help': """
        An alias for the top level design name. Can be useful when top level
        designs have long and confusing names or when multiple configuration
        packages are created for the same design. The nickname is used in all
        output file prefixes. The top level design name is used if no
        'name' parameter is defined.
        """
    }

    cfg['origin'] = {
        'switch': '-origin',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Origin',
        'param_help': "origin <str>",
        'example': ["cli: -origin mars",
                    "api: chip.add('origin', 'mars')"],
        'help': """
        Record of design country of origin.
        """
    }

    cfg['clock'] = {}
    cfg['clock']['default'] = {}
    cfg['clock']['default']['pin'] = {
        'switch': '-clock_pin',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Clock Driver',
        'param_help': "clock clkvar pin <str>",
        'example': ["cli: -clock_pin 'clk top.pll.clkout'",
                    "api: chip.add('clock', 'clk','pin','top.pll.clkout')"],
        'help': """
        Defines a clock name alias to assign to a clock source.
        """
    }

    cfg['clock']['default']['period'] = {
        'switch': '-clock_period',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Clock Period',
        'param_help': "clock clkvar period <num>",
        'example': ["cli: -clock_period 'clk 10'",
                    "api: chip.add('clock','clk','period','10')"],
        'help': """
        Specifies the period for a clock source in nanoseconds.
        """
    }

    cfg['clock']['default']['jitter'] = {
        'switch': '-clock_jitter',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Clock Jitter',
        'param_help': "clock clkvar jitter <num>",
        'example': ["cli: -clock_jitter 'clk 0.01'",
                    "api: chip.add('clock','clk','jitter','0.01')"],
        'help': """
        Specifies the jitter for a clock source in nanoseconds.
        """
    }

    cfg['supply'] = {}
    cfg['supply']['default'] = {}

    cfg['supply']['default']['pin'] = {
        'switch': '-supply_pin',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Power Supply Name',
        'param_help': "supply supplyvar pin <str>",
        'example': ["cli: -supply_pin 'vdd vdd_0'",
                    "api: chip.add('supply','vdd','pin','vdd_0')"],
        'help': """
        Defines a supply name alias to assign to a power source.
        A power supply source can be a list of block pins or a regulator
        output pin.

        Examples:
        cli: -supply_name 'vdd_0 vdd'
        api: chip.add('supply','vdd_0', 'pin', 'vdd')
        """
    }

    cfg['supply']['default']['level'] = {
        'switch': '-supply_level',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Power Supply Level',
        'param_help': "supply supplyvar level <num>",
        'example': ["cli: -supply_level 'vdd 1.0'",
                    "api: chip.add('supply','vdd','level','1.0')"],
        'help': """
        Specifies level in Volts for a power source.
        """
    }

    cfg['supply']['default']['noise'] = {
        'switch': '-supply_noise',
        'type': 'float',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Power Supply Noise',
        'param_help': "supply supplyvar noise <num>",
        'example': ["cli: -supply_noise 'vdd 0.05'",
                    "api: chip.add('supply','vdd','noise','0.05')"],
        'help': """
        Specifies the noise in Volts for a power source.
        """
    }

    cfg['param'] = {}
    cfg['param']['default'] = {
        'switch': '-param',
        'type': 'str',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': None,
        'short_help': 'Design Parameter Override',
        'param_help': "param paramvar <str>",
        'example': ["cli: -param 'N 64'",
                    "api: chip.add('param','N', '64')"],
        'help': """
        Overrides the given parameter of the top level module. The value
        is limited to basic data literals. The parameter override is
        passed into tools such as Verilator and Yosys. The parameters
        support Verilog integer literals (64'h4, 2'b0, 4) and strings.
        """
    }

    cfg['define'] = {
        'switch': '-D',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Design Preprocessor Symbols',
        'param_help': "define <str>",
        'example': ["cli: -D 'CFG_ASIC=1'",
                    "api: chip.add('define','CFG_ASIC=1')"],
        'help': """
        Sets a preprocessor symbol for verilog source imports.
        """
    }

    cfg['ydir'] = {
        'switch': '-y',
        'type': '[dir]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Module Search Paths',
        'param_help': "ydir <dir>",
        'example': ["cli: -y './mylib'",
                    "api: chip.add('ydir','./mylib')"],
        'help': """
        Provides a search paths to look for modules found in the the source
        list. The import engine will look for modules inside files with the
        specified +libext+ param suffix
        """
    }

    cfg['idir'] = {
        'switch': '+incdir+',
        'type': '[dir]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Include Search Paths',
        'param_help': "idir <dir>",
        'example': ["cli: '+incdir+./mylib'",
                    "api: chip.add('idir','./mylib')"],
        'help': """
        Provides a search paths to look for files included in the design using
        the ```include`` statement.
        """
    }

    cfg['vlib'] = {
        'switch': '-v',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Verilog Library',
        'param_help': "vlib <file>",
        'example': ["cli: -v './mylib.v'",
                    "api: chip.add('vlib','./mylib.v')"],
        'help': """
        Declares source files to be read in, for which modules are not to be
        interpreted as root modules.
        """
    }

    cfg['libext'] = {
        'switch': '+libext+',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'optional',
        'defvalue': [],
        'short_help': 'Verilog File Extensions',
        'param_help': "libext <str>",
        'example': ["cli: +libext+sv",
                    "api: chip.add('libext','sv')"],
        'help': """
        Specifes the file extensions that should be used for finding modules.
        For example, if -y is specified as ./lib", and '.v' is specified as
        libext then the files ./lib/\\*.v ", will be searched for module matches.
        """
    }

    cfg['cmdfile'] = {
        'switch': '-f',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Verilog Options File',
        'param_help': "cmdfile <file>",
        'example': ["cli: -f design.f",
                    "api: chip.add('cmdfile','design.f')"],
        'help': """
        Read the specified file, and act as if all text inside it was specified
        as command line parameters. Supported by most verilog simulators
        including Icarus and Verilator.
        """
    }

    cfg['constraint'] = {
        'switch': '-constraint',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Constraint Files',
        'param_help': "constraint <file>",
        'example': ["cli: -constraint top.sdc",
                    "api: chip.add('constraint','top.sdc')"],
        'help': """
        List of default constraints for the design to use during compilation.
        Types of constraints include timing (SDC) and pin mappings for FPGAs.
        More than one file can be supplied. Timing constraints are global and
        sourced in all MCMM scenarios.
        """
    }

    cfg['vcd'] = {
        'switch': '-vcd',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Value Change Dump File',
        'param_help': "vcd <file>",
        'example': ["cli: -vcd mytrace.vcd",
                    "api: chip.add('vcd','mytrace.vcd')"],
        'help': """
        A digital simulation trace that can be used to model the peak and
        average power consumption of a design.
        """
    }

    cfg['spef'] = {
        'switch': '-spef',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'SPEF File',
        'param_help': "spef <file>",
        'example': ["cli: -spef mydesign.spef",
                    "api: chip.add('spef','mydesign.spef')"],
        'help': """
        File containing parastics specified in the Standard Parasitic Exchange
        format. The file is used in signoff static timing analysis and power
        analysis and should be generated by an accurate parasitic extraction
        engine.
        """
    }

    cfg['sdf'] = {
        'switch': '-sdf',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'SDF File',
        'param_help': "sdf <file>",
        'example': ["cli: -sdf mydesign.sdf",
                    "api: chip.add('sdf','mydesign.sdf')"],
        'help': """
        File containing timing data in Standard Delay Format (SDF).
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
        'switch': '-asic_stackup',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Metal Stackup',
        'param_help': "asic stackup <str>",
        'example': ["cli: -asic_stackup 2MA4MB2MC",
                    "api: chip.add('asic','stackup','2MA4MB2MC')"],
        'help': """
        Specifies the target stackup to use in the design. The stackup name
        must match a value defined in the pdk_stackup list.
        """
    }

    cfg['asic']['targetlib'] = {
        'switch': '-asic_targetlib',
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'requirement': 'asic',
        'short_help': 'Target Libraries',
        'param_help': "asic targetlib <str>",
        'example': ["cli: -asic_targetlib asap7sc7p5t_lvt",
                    "api: chip.add('asic', 'targetlib', 'asap7sc7p5t_lvt')"],
        'help': """
        A list of library names to use for synthesis and automated place and
        route. Names must match up exactly with the library name handle in the
        'stdcells' dictionary.
        """
    }

    cfg['asic']['macrolib'] = {
        'switch': '-asic_macrolib',
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'requirement': 'optional',
        'short_help': 'Macro Libraries',
        'param_help': "asic macrolib <str>",
        'example': ["cli: -asic_macrolib sram64x1024",
                    "api: chip.add('asic', 'macrolib', 'sram64x1024')"],
        'help': """
        A list of macro libraries to be linked in during synthesis and place
        and route. Macro libraries are used for resolving instances but are
        not used as target for automated synthesis.
        """
    }

    cfg['asic']['delaymodel'] = {
        'switch': '-asic_delaymodel',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'requirement': 'asic',
        'short_help': 'Library Delay Model',
        'param_help': "asic delaymodel <str>",
        'example': ["cli: -asic_delaymodel ccs",
                    "api: chip.add('asic', 'delaymodel', 'ccs')"],
        'help': """
        Specifies the delay model to use for the target libs. Supported values
        are nldm and ccs.
        """
    }

    cfg['asic']['ndr'] = {
        'switch': '-asic_ndr',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': '',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Design Non-default Rules',
        'param_help': "asic ndr <str>",
        'example': ["cli: -asic_ndr myndr.txt",
                    "api: chip.add('asic', 'ndr', 'myndr.txt')"],
        'help': """
        A file containing a list of nets with non-default width and spacing,
        with one net per line and no wildcards.
        The file format is: <netname width space>. The netname should include
        the full hierarchy from the root module while width space should be
        specified in the resolution specified in the technology file.
        The values are specified in microns.
        """
    }

    cfg['asic']['minlayer'] = {
        'switch': '-asic_minlayer',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': [],
        'short_help': 'Design Minimum Routing Layer',
        'param_help': "asic minlayer <str>",
        'example': ["cli: -asic_minlayer m2",
                    "api: chip.add('asic', 'minlayer', 'm2')"],
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
        'switch': '-asic_maxlayer',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Maximum Routing Layer',
        'param_help': "asic maxlayer <str>",
        'example': ["cli: -asic_maxlayer m6",
                    "api: chip.add('asic', 'maxlayer', 'm6')"],
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
        'switch': '-asic_maxfanout',
        'type': 'int',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Maximum Fanout',
        'param_help': "asic maxfanout <str>",
        'example': ["cli: -asic_maxfanout 64",
                    "api: chip.add('asic', 'maxfanout', '64')"],
        'help': """
        The maximum driver fanout allowed during automated place and route.
        The parameter directs the APR tool to break up any net with fanout
        larger than maxfanout into subnets and buffer.
        """
    }

    cfg['asic']['maxlength'] = {
        'switch': '-asic_maxlength',
        'type': 'float',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Maximum Wire Length',
        'param_help': "asic maxlength <str>",
        'example': ["cli: -asic_maxlength 1000",
                    "api: chip.add('asic', 'maxlength', '1000')"],
        'help': """
        The maximum total wire length allowed in design during APR. Any
        net that is longer than maxlength is broken up into segments by
        the tool.
        """
    }

    cfg['asic']['maxcap'] = {
        'switch': '-asic_maxcap',
        'type': 'float',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Maximum Net Capacitance',
        'param_help': "asic maxcap <str>",
        'example': ["cli: -asic_maxcap '0.25e-12'",
                    "api: chip.add('asic', 'maxcap', '0.25e-12')"],
        'help': """
        The maximum allowed capacitance per net. The number is specified
        in Farads.
        """
    }

    cfg['asic']['maxslew'] = {
        'switch': '-asic_maxslew',
        'type': 'float',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Maximum Net Slew',
        'param_help': "asic maxslew <str>",
        'example': ["cli: -asic_maxslew '01e-9'",
                    "api: chip.add('asic', 'maxslew', '1e-9')"],
        'help': """
        The maximum allowed capacitance per net. The number is specified
        in seconds.
        """
    }

    cfg['asic']['rclayer'] = {
        'switch': '-asic_rclayer',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Parasitic Extraction Estimation Layer',
        'param_help': "asic rclayer <str>",
        'example': ["cli: -asic_rclayer m3",
                    "api: chip.add('asic', 'rclayer', 'm3')"],
        'help': """
        The technology agnostic metal layer to be used for parasitic
        extraction estimation during APR. Allowed layers are m1 to
        mn. Actual technology metal layers are looked up through the
        'grid' dictionary.
        """
    }

    cfg['asic']['clklayer'] = {
        'switch': '-asic_clklayer',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Clock Layer',
        'param_help': "asic clklayer <str>",
        'example': ["cli: -asic_clklayer m5",
                    "api: chip.add('asic', 'clklayer', 'm5')"],
        'help': """
        Metal layer to use for clock net parasitic estimation.
        """
    }

    cfg['asic']['vpinlayer'] = {
        'switch': '-asic_vpinlayer',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Vertical Pin Layer',
        'param_help': "asic vpinlayer <str>",
        'example': ["cli: -asic_vpinlayer m3",
                    "api: chip.add('asic', 'vpinlayer', 'm3')"],
        'help': """
        Metal layer to use for automated vertical pin placement
        during APR.
        """
    }

    cfg['asic']['hpinlayer'] = {
        'switch': '-asic_hpinlayer',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'Design Horizontal Pin Layer',
        'param_help': "asic hpinlayer <str>",
        'example': ["cli: -asic_hpinlayer m2",
                    "api: chip.add('asic', 'hpinlayer', 'm2')"],
        'help': """
        Metal layer to use for automated horizontalpin placement
        during APR.
        """
    }


    # For density driven floorplanning
    cfg['asic']['density'] = {
        'switch': '-asic_density',
        'type': 'float',
        'lock': 'false',
        'requirement': '!diesize',
        'defvalue': None,
        'short_help': 'APR Target Core Density',
        'param_help': "asic density <num>",
        'example': ["cli: -asic_density 30",
                    "api: chip.add('asic', 'density', '30')"],
        'help': """"
        Provides a target density based on the total design cell area reported
        after synthesis. This number is used when no die size or floorplan is
        supplied. Any number between 1 and 100 is legal, but values above 50
        may fail due to area/congestion issues during apr.
        """
    }

    cfg['asic']['coremargin'] = {
        'switch': '-asic_coremargin',
        'type': 'float',
        'lock': 'false',
        'requirement': 'density',
        'defvalue': None,
        'short_help': 'APR Block Core Margin',
        'param_help': "asic coremargin <num>",
        'example': ["cli: -asic_coremargin 1",
                    "api: chip.add('asic', 'coremargin', '1')"],
        'help': """
        Sets the halo/margin between the core area to use for automated
        floorplanning and the outer core boundary. The value is specified in
        microns and is only used when no diesize or floorplan is supplied.
        """
    }

    cfg['asic']['aspectratio'] = {
        'switch': '-asic_aspectratio',
        'type': 'float',
        'lock': 'false',
        'requirement': 'density',
        'defvalue': '1',
        'short_help': 'APR Block Aspect Ratio',
        'param_help': "asic aspectratio <num>",
        'example': ["cli: -asic_aspectratio 2.0",
                    "api: chip.add('asic', 'aspectratio', '2.0')"],
        'help': """
        Specifies the height to width ratio of the block for automated
        floor-planning. Values below 0.1 and above 10 should be avoided as
        they will likely fail to converge during placement and routing. The
        ideal aspect ratio for most designs is 1. This value is only used when
        no diesize or floorplan is supplied.
        """
        }

    # For spec driven floorplanning
    cfg['asic']['diesize'] = {
        'switch': '-asic_diesize',
        'type': 'float4',
        'lock': 'false',
        'requirement': '!density',
        'defvalue': [],
        'short_help': 'Target Die Size',
        'param_help': "asic diesize <float float float float>",
        'example': ["cli: -asic_diesize '0 0 100 100'",
                    "api: chip.add('asic', 'diesize', '0 0 100 100')"],
        'help': """
        Provides the outer boundary of the physical design. The number is
        provided as a tuple (x0 y0 x1 y1), where (x0, y0), specifes the lower
        left corner of the block and (x1, y1) specifies the upper right corner.
        Only rectangular blocks are supported with the diesize parameter. All
        values are specified in microns.
        """
    }

    cfg['asic']['coresize'] = {
        'switch': '-asic_coresize',
        'type': 'float4',
        'lock': 'false',
        'requirement': 'diesize',
        'defvalue': [],
        'short_help': 'Target Core Size',
        'param_help': "asic coresize <float float float float>",
        'example': ["cli: -asic_coresize '0 0 90 90'",
                    "api: chip.add('asic', 'coresize', '0 0 90 90')"],
        'help': """
        Provides the core cell area of the physical design. The number is
        provided as a tuple (x0 y0 x1 y1), where (x0, y0), specifes the lower
        left corner of the block and (x1, y1) specifies the upper right corner.
        Only rectangular blocks are supported with the diesize parameter. For
        advanced geometries and blockages, a floor-plan file should is better.
        All values are specified in microns.
        """
    }

    # Parameterized floorplanning
    cfg['asic']['floorplan'] = {
        'switch': '-asic_floorplan',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Floorplanning Script',
        'param_help': "asic floorplan <file>",
        'example': ["cli: -asic_floorplan hello.py",
                    "api: chip.add('asic', 'floorplan', 'hello.py')"],
        'help': """
        Provides a python based floorplan to be used during the floorplan step
        of compilation to generate a fixed DEF ready for use by the APR tool.
        Supported formats are tcl and py.
        """
    }

    # Def file
    cfg['asic']['def'] = {
        'switch': '-asic_def',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'optional',
        'defvalue': [],
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'short_help': 'Harc coded DEF floorplan',
        'param_help': "asic def <file>",
        'example': ["cli: -asic_def 'hello.def'",
                    "api: chip.add('asic', 'def', 'hello.def')"],
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
        'switch': '-mcmm_voltage',
        'type': 'float',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'MCMM Voltage',
        'param_help': "mcmm scenariovar voltage <num>",
        'example': ["cli: -mcmm_voltage 'worst 0.9'",
                    "api: chip.add('mcmm', 'worst', 'voltage', '0.9')"],
        'help': """
        Specifies the on chip primary core operating voltage for the scenario.
        The value is specified in Volts.
        """
    }

    cfg['mcmm']['default']['temperature'] = {
        'switch': '-mcmm_temperature',
        'type': 'float',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'MCMM Temperature',
        'param_help': "mcmm scenariovar temperature <num>",
        'example': ["cli: -mcmm_temperature 'worst 0.9'",
                    "api: chip.add('mcmm', 'worst', 'temperature', '125')"],
        'help': """
        Specifies the on chip temperature for the scenario. The value is specified in
        degrees Celsius.
        """
    }

    cfg['mcmm']['default']['libcorner'] = {
        'switch': '-mcmm_libcorner',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'MCMM Library Corner Name',
        'param_help': "mcmm scenariovar libcorner <str>",
        'example': ["cli: -mcmm_libcorner 'worst ttt'",
                    "api: chip.add('mcmm', 'worst', 'libcorner', 'ttt')"],
        'help': """
        Specifies the library corner for the scenario. The value is used to access the
        stdcells library timing model. The 'libcorner' value must match the corner
        in the 'stdcells' dictionary exactly.
        """
    }

    cfg['mcmm']['default']['opcond'] = {
        'switch': '-mcmm_opcond',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'MCMM Operating Condition',
        'param_help': "mcmm scenariovar opcond <str>",
        'example': ["cli: -mcmm_opcond 'worst typical_1.0'",
                    "api: chip.add('mcmm', 'worst', 'opcond', 'typical_1.0')"],
        'help': """
        Specifies the operating condition for the scenario. The value can be used
        to access specific conditions within the library timing models of the
        'target_libs'. The 'opcond' value must match the corner in the
        timing model.
        """
    }

    cfg['mcmm']['default']['pexcorner'] = {
        'switch': '-mcmm_pexcorner',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'MCMM PEX Corner Name',
        'param_help': "mcmm scenariovar pexcorner <str>",
        'example': ["cli: -mcmm_pexcorner 'worst max'",
                    "api: chip.add('mcmm','worst','pexcorner','max')"],
        'help': """
        Specifies the parasitic corner for the scenario. The 'pexcorner' string must
        match the value 'pdk','pexmodel' dictionary exactly.
        """
    }

    cfg['mcmm']['default']['mode'] = {
        'switch': '-mcmm_mode',
        'type': 'str',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': None,
        'short_help': 'MCMM Mode Name',
        'param_help': "mcmm scenariovar mode <str>",
        'example': ["cli: -mcmm_mode 'worst test'",
                    "api: chip.add('mcmm', 'worst', 'mode', 'test')"],
        'help': """
        Specifies the operating mode for the scenario. Operating mode strings can be
        values such as "test, functional, standby".
        """
    }

    cfg['mcmm']['default']['constraint'] = {
        'switch': '-mcmm_constraint',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'requirement': 'asic',
        'filehash': [],
        'date': [],
        'author': [],
        'signature': [],
        'defvalue': [],
        'short_help': 'MCMM Timing Constraints',
        'param_help': "mcmm scenariovar constraint <file>",
        'example': ["cli: -mcmm_constraint 'worst hello.sdc'",
                    "api: chip.add('mcmm','worst','constraint','hello.sdc')"],
        'help': """
        Specifies a list of timing contstraint files to use for the scenario.
        The values are combined with any constraints specified by the design
        'constraint' parameter. If no constraints are found, a default constraint
        file is used based on the clock definitions.
        """
    }

    cfg['mcmm']['default']['check'] = {
        'switch': '-mcmm_check',
        'type': '[str]',
        'lock': 'false',
        'requirement': 'asic',
        'defvalue': [],
        'short_help': 'MCMM Checks',
        'param_help': "mcmm scenariovar check <str>",
        'example': ["cli: -mcmm_check 'worst check setup'",
                    "api: chip.add('mcmm','worst','check','setup')"],
        'help': """
        Specifies a list of checks for to perform for the scenario aligned. The checks
        must align with the capabilities of the EDA tools. Checks generally include
        objectives like meeting setup and hold goals and minimize power.
        Standard check names include setup, hold, power, noise, reliability.
        """
    }

    return cfg
