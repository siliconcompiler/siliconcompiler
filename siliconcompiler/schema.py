# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import re
import os
import sys
import copy
import json

#############################################################################
# CHIP CONFIGURATION
#############################################################################

def schema_cfg():
    '''Method for defining Chip configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    # SC version number (bump on every non trivial change)
    # Version number following semver standard.
    SCHEMA_VERSION = '0.1.0'

    # Basic schema setup
    cfg = {}

    # Version handling
    cfg = schema_version(cfg, SCHEMA_VERSION)

    # Runtime options
    cfg = schema_options(cfg)

    # Project configuration
    cfg = schema_package(cfg, 'package')
    cfg = schema_design(cfg)
    cfg = schema_fpga(cfg)
    cfg = schema_asic(cfg)
    cfg = schema_mcmm(cfg)

    # Flow Information
    cfg = schema_flowgraph(cfg)
    cfg = schema_flowstatus(cfg)
    cfg = schema_eda(cfg)
    cfg = schema_arg(cfg)
    cfg = schema_jobs(cfg)

    # PDK
    cfg = schema_pdk(cfg)

    # Package management
    cfg = schema_libs(cfg)
    cfg = schema_package(cfg, 'library')

    # Compilation records
    cfg = schema_metric(cfg)
    cfg = schema_record(cfg)
    cfg = schema_package(cfg, 'record')

    return cfg

###############################################################################
# Minimal setupFPGA
###############################################################################

def schema_version(cfg, version):

    cfg['version'] = {}
    cfg['version']['schema'] = {
        'switch': "-version_schema <str>",
        'type': 'str',
        'lock': 'true',
        'require': 'all',
        'defvalue': version,
        'shorthelp': 'Schema version number',
        'example': ["cli: -version_schema",
                    "api: chip.get('version', 'schema')"],
        'help': """
        SiliconCompiler schema version number.
        """
    }

    cfg['version']['sc'] = {
        'switch': "-version_sc <str>",
        'type': 'str',
        'lock': 'true',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'SiliconCompiler version number',
        'example': ["cli: -version_sc",
                    "api: chip.get('version', 'sc')"],
        'help': """
        SiliconCompiler software version number.
        """
    }

    # Print SC version number
    cfg['version']['print'] = {
        'switch': "-version <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Print version number',
        'example': ["cli: -version",
                    "api: chip.get('version')"],
        'help': """
        Command line switch to print SC version number.
        """
    }

    return cfg


###############################################################################
# FPGA
###############################################################################

def schema_fpga(cfg):
    ''' FPGA configuration
    '''
    cfg['fpga'] = {}

    cfg['fpga']['arch'] = {
        'switch': "-fpga_arch <file>",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'FPGA architecture file',
        'example': ["cli: -fpga_arch myfpga.xml",
                    "api:  chip.set('fpga', 'arch', 'myfpga.xml')"],
        'help': """
        Architecture definition file for FPGA place and route tool. For the
        VPR tool, the file is a required XML based description, allowing
        targeting a large number of virtual and commercial architectures.
        For most commercial tools, the fpga part name provides enough
        information to enable compilation and the 'arch' parameter is
        optional.
        """
    }

    cfg['fpga']['vendor'] = {
        'switch': "-fpga_vendor <str>",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'FPGA vendor name',
        'example': ["cli: -fpga_vendor acme",
                    "api:  chip.set('fpga', 'vendor', 'acme')"],
        'help': """
        Name of the FPGA vendor. The parameter is used to check part
        name and to select the eda tool flow in case 'edaflow' is
        unspecified.
        """
    }

    cfg['fpga']['partname'] = {
        'switch': "-fpga_partname <str>",
        'require': 'fpga',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'FPGA part name',
        'example': ["cli: -fpga_partname fpga64k",
                    "api:  chip.set('fpga', 'partname', 'fpga64k')"],
        'help': """
        Complete part name used as a device target by the FPGA compilation
        tool. The part name must be an exact string match to the partname
        hard coded within the FPGA eda tool.
        """
    }

    cfg['fpga']['board'] = {
        'switch': "-fpga_board <str>",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'FPGA board name',
        'example': ["cli: -fpga_board parallella",
                    "api:  chip.set('fpga', 'board', 'parallella')"],
        'help': """
        Complete board name used as a device target by the FPGA compilation
        tool. The board name must be an exact string match to the partname
        hard coded within the FPGA eda tool. The parameter is optional and can
        be used in place of a partname and pin constraints for some tools.
        """
    }

    cfg['fpga']['program'] = {
        'switch': "-fpga_program <bool>",
        'require': 'fpga',
        'type': 'bool',
        'lock': 'false',
        'defvalue': 'false',
        'shorthelp': 'FPGA program enable',
        'example': ["cli: -fpga_program",
                    "api:  chip.set('fpga', 'program', True)"],
        'help': """
        Specifies that the bitstream should be loaded into an FPGA.
        The default is to load the bitstream into volatile memory (SRAM).
        """
    }

    cfg['fpga']['flash'] = {
        'switch': "-fpga_flash <bool>",
        'require': 'fpga',
        'type': 'bool',
        'lock': 'false',
        'defvalue': 'false',
        'shorthelp': 'FPGA flash enable',
        'example': ["cli: -fpga_flash",
                    "api:  chip.set('fpga', 'flash', True)"],
        'help': """
        Specifies that the bitstream should be flashed in the board/device.
        The default is to load the bitstream into volatile memory (SRAM).
        """
    }

    return cfg

###############################################################################
# PDK
###############################################################################

def schema_pdk(cfg, stackup='default'):
    ''' Process design kit configuration
    '''
    cfg['pdk'] = {}
    cfg['pdk']['foundry'] = {
        'switch': "-pdk_foundry <str>",
        'require': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK foundry name',
        'example': ["cli: -pdk_foundry virtual",
                    "api:  chip.set('pdk', 'foundry', 'virtual')"],
        'help': """
        Name of foundry corporation. Examples include intel, gf, tsmc,
        samsung, skywater, virtual. The \'virtual\' keyword is reserved for
        simulated non-manufacturable processes.
        """
    }

    cfg['pdk']['process'] = {
        'switch': "-pdk_process <str>",
        'require': 'asic',
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK process name',
        'example': ["cli: -pdk_process asap7",
                    "api:  chip.set('pdk', 'process', 'asap7')"],
        'help': """
        Public name of the foundry process. The string is case insensitive and
        must match the public process name exactly. Examples of virtual
        processes include freepdk45 and asap7.
        """
    }

    cfg['pdk']['node'] = {
        'switch': "-pdk_node <float>",
        'require': 'asic',
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK process node',
        'example': ["cli: -pdk_node 130",
                    "api:  chip.set('pdk', 'node', 130)"],
        'help': """
        Approximate relative minimum dimension of the process target specified
        in nanometers. The parameter is required for flows and tools that
        leverage the value to drive technology dependent synthesis and APR
        optimization. Node examples include 180, 130, 90, 65, 45, 32, 22 14,
        10, 7, 5, 3.
        """
    }

    cfg['pdk']['wafersize'] = {
        'switch': "-pdk_wafersize <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK wafer size',
        'example': ["cli: -pdk_wafersize 300",
                    "api:  chip.set('pdk', 'wafersize', 300)"],
        'help': """
        Wafer diameter used in manufacturing process specified in mm. The
        standard diameter for leading edge manufacturing is 300mm. For older
        process technologies and specialty fabs, smaller diameters such as
        200, 100, 125, 100 are common. The value is used to calculate dies per
        wafer and full factory chip costs.
        """
    }

    cfg['pdk']['wafercost'] = {
        'switch': "-pdk_wafercost <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK wafer cost',
        'example': ["cli: -pdk_wafercost 10000",
                    "api:  chip.set('pdk', 'wafercost', 10000)"],
        'help': """
        Raw cost per wafer purchased specified in USD, not accounting for
        yield loss. The values is used to calculate chip full factory costs.
        """
    }

    cfg['pdk']['d0'] = {
        'switch': "-pdk_d0 <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK process defect density',
        'example': ["cli: -pdk_d0 0.1",
                    "api:  chip.set('pdk', 'd0', 0.1)"],
        'help': """
        Process defect density (d0) expressed as random defects per cm^2. The
        value is used to calculate yield losses as a function of area, which in
        turn affects the chip full factory costs. Two yield models are
        supported: Poisson (default), and Murphy. The Poisson based yield is
        calculated as dy = exp(-area * d0/100). The Murphy based yield is
        calculated as dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.
        """
    }

    cfg['pdk']['hscribe'] = {
        'switch': "-pdk_hscribe <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK horizontal scribe line width',
        'example': ["cli: -pdk_hscribe 0.1",
                    "api:  chip.set('pdk', 'hscribe', 0.1)"],
        'help': """
        Width of the horizontal scribe line (in mm) used during die separation.
        The process is generally completed using a mechanical saw, but can be
        done through combinations of mechanical saws, lasers, wafer thinning,
        and chemical etching in more advanced technologies. The value is used
        to calculate effective dies per wafer and full factory cost.
        """
    }

    cfg['pdk']['vscribe'] = {
        'switch': "-pdk_vscribe <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK vertical scribe line width',
        'example': ["cli: -pdk_vscribe 0.1",
                    "api:  chip.set('pdk', 'vscribe', 0.1)"],
        'help': """
        Width of the vertical scribe line (in mm) used during die separation.
        The process is generally completed using a mechanical saw, but can be
        done through combinations of mechanical saws, lasers, wafer thinning,
        and chemical etching in more advanced technologies. The value is used
        to calculate effective dies per wafer and full factory cost.
        """
    }

    cfg['pdk']['edgemargin'] = {
        'switch': "-pdk_edgemargin <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK wafer edge keep-out margin',
        'example': ["cli: -pdk_edgemargin 1",
                    "api:  chip.set('pdk', 'edgemargin', 1)"],
        'help': """
        Keep-out distance/margin from the wafer edge inwards specified in mm.
        The wafer edge is prone to chipping and need special treatment that
        preclude placement of designs in this area. The edge value is used to
        calculate effective dies per wafer and full factory cost.
        """
    }

    cfg['pdk']['density'] = {
        'switch': "-pdk_density <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK transistor density',
        'example': ["cli: -pdk_density 100e6",
                    "api:  chip.set('pdk', 'density', 10e6)"],
        'help': """
        Approximate logic density expressed as # transistors / mm^2
        calculated as:
        0.6 * (Nand2 Transistor Count) / (Nand2 Cell Area) +
        0.4 * (Register Transistor Count) / (Register Cell Area)
        The value is specified for a fixed standard cell library within a node
        and will differ depending on the library vendor, library track height
        and library type. The value can be used to to normalize the effective
        density reported for the design across different process nodes. The
        value can be derived from a variety of sources, including the PDK DRM,
        library LEFs, conference presentations, and public analysis.
        """
    }

    cfg['pdk']['sramsize'] = {
        'switch': "-pdk_sramsize <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK SRAM bitcell size',
        'example': ["cli: -pdk_sramsize 0.032",
                    "api:  chip.set('pdk', 'sramsize', '0.026')"],
        'help': """
        Area of an SRAM bitcell expressed in um^2. The value can be derived
        from a variety of sources, including the PDK DRM, library LEFs,
        conference presentations, and public analysis. The number is a good
        first order indicator of SRAM density for large memory arrays where
        the bitcell dominates the array I/O logic.
        """
    }

    cfg['pdk']['version'] = {
        'switch': "-pdk_version <str>",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK version number',
        'example': ["cli: -pdk_version 1.0",
                    "api:  chip.set('pdk', 'version', '1.0')"],
        'help': """
        Alphanumeric string specifying the version of the PDK. Verification of
        correct PDK and IP versions is a hard ASIC tapeout require in all
        commercial foundries. The version number can be used for design manifest
        tracking and tapeout checklists.
        """
    }
    doctypes = ['datasheet',
                'reference',
                'userguide',
                'releasenotes',
                'tutorial']

    cfg['pdk']['doc'] = {}
    for item in doctypes:
        cfg['pdk']['doc'][item] = {
            'switch': f"-pdk_doc_{item} '<file>'",
            'type': '[file]',
            'lock': 'false',
            'copy': 'true',
            'require': None,
            'defvalue': [],
            'filehash': [],
            'hashalgo': 'sha256',
            'date': [],
            'author': [],
            'signature': [],
            'shorthelp': f"PDK {item}",
            'example': [
                f"cli: -pdk_doc_{item} 'pdk.pdf",
                f"api: chip.set('pdk','doc',{item},'pdk.pdf')"],
            'help': f"""
            List of {item} documents for the PDK.
            """
        }

    cfg['pdk']['stackup'] = {
        'switch': "-pdk_stackup <str>",
        'require': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'shorthelp': 'PDK metal stackups',
        'example': ["cli: -pdk_stackup 2MA4MB2MC",
                    "api: chip.add('pdk', 'stackup', '2MA4MB2MC')"],
        'help': """
        List of all metal stackups offered in the process node. Older process
        nodes may only offer a single metal stackup, while advanced nodes
        offer a large but finite list of metal stacks with varying combinations
        of metal line pitches and thicknesses. Stackup naming is unique to a
        foundry, but is generally a long string or code. For example, a 10
        metal stackup with two 1x wide, four 2x wide, and 4x wide metals,
        might be identified as 2MA4MB2MC, where MA, MB, and MC denote wiring
        layers with different properties (thickness, width, space). Each
        stackup will come with its own set of routing technology files and
        parasitic models specified in the pdk_pexmodel and pdk_aprtech
        parameters.
        """
    }

    cfg['pdk']['devmodel'] = {}
    cfg['pdk']['devmodel'][stackup] = {}
    cfg['pdk']['devmodel'][stackup]['default'] = {}
    cfg['pdk']['devmodel'][stackup]['default']['default'] = {
        'switch': "-pdk_devmodel 'stackup simtype tool <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK device models',
        'example': [
            "cli: -pdk_devmodel 'M10 spice xyce asap7.sp'",
            "api: chip.set('pdk','devmodel','M10','spice','xyce','asap7.sp')"],
        'help': """
        List of filepaths to PDK device models for different simulation
        purposes and for different tools. Examples of device model types
        include spice, aging, electromigration, radiation. An example of a
        'spice' tool is xyce. Device models are specified on a per metal stack
        basis. Process nodes with a single device model across all stacks will
        have a unique parameter record per metal stack pointing to the same
        device model file.  Device types and tools are dynamic entries
        that depend on the tool setup and device technology. Pseud-standardized
        device types include spice, em (electromigration), and aging.
        """
    }

    cfg['pdk']['pexmodel'] = {}
    cfg['pdk']['pexmodel'][stackup] = {}
    cfg['pdk']['pexmodel'][stackup]['default'] = {}
    cfg['pdk']['pexmodel'][stackup]['default']['default'] = {
        'switch': "-pdk_pexmodel 'stackup corner tool <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK parasitic TCAD models',
        'example': [
            "cli: -pdk_pexmodel 'M10 max fastcap wire.mod'",
            "api: chip.set('pdk','pexmodel','M10','max','fastcap','wire.mod')"],
        'help': """
        List of filepaths to PDK wire TCAD models used during automated
        synthesis, APR, and signoff verification. Pexmodels are specified on
        a per metal stack basis. Corner values depend on the process being
        used, but typically include nomenclature such as min, max, nominal.
        For exact names, refer to the DRM. Pexmodels are generally not
        standardized and specified on a per tool basis. An example of pexmodel
        type is 'fastcap'.
        """
    }

    cfg['pdk']['layermap'] = {}
    cfg['pdk']['layermap'][stackup] = {}
    cfg['pdk']['layermap'][stackup]['default'] = {}
    cfg['pdk']['layermap'][stackup]['default']['default'] = {
        'switch': "-pdk_layermap 'stackup src dst <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK layout data mapping file',
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
        types of EDA databases. Layer maps are specified on a per metal
        stackup basis. The 'src' and 'dst' can be names of SC supported tools
        or file formats (like 'gds').
        """
    }

    cfg['pdk']['display'] = {}
    cfg['pdk']['display'][stackup] = {}
    cfg['pdk']['display'][stackup]['default'] = {
        'switch': "-pdk_display 'stackup tool <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK display configuration file',
        'example': [
            "cli: -pdk_display 'M10 klayout display.lyt'",
            "api: chip.set('pdk','display','M10','klayout','display.cfg')"],
        'help': """
        Display configuration files describing colors and pattern schemes for
        all layers in the PDK. The display configuration file is entered on a
        stackup and tool basis.
        """
    }

    cfg['pdk']['plib'] = {}
    cfg['pdk']['plib'][stackup] = {}
    cfg['pdk']['plib'][stackup]['default'] = {
        'switch': "-pdk_plib 'stackup tool <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK process primitive cell libraries',
        'example': [
            "cli: -pdk_plib 'M10 klayout ~/devlib'",
            "api: chip.set('pdk','plib','M10','klayout','~/devlib')"],
        'help': """
        Filepaths to primitive cell libraries supported by the PDK specified
        on a per stackup and per tool basis. The plib cells is the first layer
        of design abstraction encountered above the basic device models, and
        generally include parameterized transistors, resistors, capacitors,
        inductors, etc, enabling ground up custom design. All modern PDKs
        ship with parameterized plib cells.
        """
    }

    cfg['pdk']['aprtech'] = {}
    cfg['pdk']['aprtech'][stackup] = {}
    cfg['pdk']['aprtech'][stackup]['default'] = {}
    cfg['pdk']['aprtech'][stackup]['default']['default'] = {
        'switch': "-pdk_aprtech 'stackup libarch filetype <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK APR technology file',
        'example': [
            "cli: -pdk_aprtech 'M10 12t lef tech.lef'",
            "api: chip.set('pdk','aprtech','M10','12t','lef','tech.lef')"],
        'help': """
        Technology file containing the design rule and setup information needed
        to enable DRC clean APR for the specified stackup, libarch, and format.
        The 'libarch' specifies the library architecture (e.g. library height).
        For example a PDK with support for 9 and 12 track libraries might have
        'libarchs' called 9t and 12t. During APR there
        can only be on technology file, so all libraries used for synthesis
        and APR must point to the same libarch technology file. The standard
        filetype for specifying place and route design rules for a process node
        is through a 'lef' format technology file.
        """
    }

    # LVS runsets
    tool = 'default'
    cfg['pdk']['lvs'] = {}
    cfg['pdk']['lvs'][tool] = {}
    cfg['pdk']['lvs'][tool][stackup] = {}
    cfg['pdk']['lvs'][tool][stackup]['runset'] = {
        'switch': "-pdk_lvs_runset 'stackup tool <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK LVS runset files',
        'example': [
            "cli: -pdk_lvs_runset 'magic M10 $PDK/lvs.magicrc'",
            "api: chip.set('pdk','lvs','magic', 'M10', 'runset', '$PDK/lvs.magicrc')"],
        'help': """
        Runset files for runset LVS verification
        """
    }

    # DRC settings
    cfg['pdk']['drc'] = {}
    cfg['pdk']['drc'][tool] = {}
    cfg['pdk']['drc'][tool][stackup] = {}
    cfg['pdk']['drc'][tool][stackup]['runset'] = {
        'switch': "-pdk_drc_runset 'stackup tool <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK DRC runset files',
        'example': [
            "cli: -pdk_drc_runset 'magic M10 $PDK/drc.magicrc'",
            "api: chip.set('pdk','drc','magic', 'M10', 'runset', '$PDK/drc.magicrc')"],
        'help': """
        Runset files for runset DRC verification
        """
    }

    cfg['pdk']['drc'][tool][stackup]['waiver'] = {
        'switch': "-pdk_drc_waiver 'stackup tool <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK DRC runset waiver files',
        'example': [
            "cli: -pdk_drc_waiver 'magic M10 waiver $PDK/waiver.txt'",
            "api: chip.set('pdk','drc','magic', 'M10', 'waiver', '$PDK/waiver.txt')"],
        'help': """
        Design rule waiver file for DRC verification
        """
    }

    # ERC runsets
    cfg['pdk']['erc'] = {}
    cfg['pdk']['erc'][tool] = {}
    cfg['pdk']['erc'][tool][stackup] = {}
    cfg['pdk']['erc'][tool][stackup]['runset'] = {
        'switch': "-pdk_erc_runset 'stackup tool <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'PDK ERC runset files',
        'example': [
            "cli: -pdk_erc_runset 'magic M10 $PDK/erc.magicrc'",
            "api: chip.set('pdk','erc','magic', 'M10', 'runset', '$PDK/erc.magicrc')"],
        'help': """
        Runset files for runset ERC verification
        """
    }

    #############################
    # Routing grid
    #############################

    layer = 'default'
    cfg['pdk']['grid'] = {}
    cfg['pdk']['grid'][stackup] = {}
    cfg['pdk']['grid'][stackup][layer] = {}

    # Name map
    cfg['pdk']['grid'][stackup][layer]['name'] = {
        'switch': "-pdk_grid_name 'stackup layer <str>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK metal layer name map',
        'example': [
            "cli: -pdk_grid_name 'M10 m1 metal1'""",
            "api: chip.set('pdk','grid','M10','m1','name','metal1')"],
        'help': """
        Maps PDK metal names found in the tech to the SC standardized
        metal naming scheme that starts with m1 (lowest routing layer)
        and ends with m<n>(highest routing layer). The map is
        specified on a per metal stack basis.
        """
    }

    # Preferred routing direction
    cfg['pdk']['grid'][stackup][layer]['dir'] = {
        'switch': "-pdk_grid_dir 'stackup layer <str>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK preferred metal routing direction',
        'example': [
            "cli: -pdk_grid_dir 'M10 m1 x'""",
            "api: chip.set('pdk','grid','M10','m1','dir','x')"],
        'help': """
        Preferred routing direction specified on a per stackup
        and per SC metal basis.  Valid directions are x for horizontal
        and y for vertical wires. If not defined, the value is taken
        from the PDK tech.lef.
        """
    }

    # Vertical wires
    cfg['pdk']['grid'][stackup][layer]['xpitch'] = {
        'switch': "-pdk_grid_xpitch 'stackup layer <float>'",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK routing grid vertical wire pitch',
        'example': [
            "cli: -pdk_grid_xpitch 'M10 m1 0.5'",
            "api: chip.set('pdk','grid','M10','m1','xpitch','0.5')"],
        'help': """
        Defines the routing pitch for vertical wires on a per stackup and
        per metal basis, specified in um. Metal layers are ordered
        from m1 to m<n>, where m1 is the lowest routing layer in the tech.lef.
        If not defined, the value is taken from the PDK tech.lef.
        """
    }

    # Horizontal wires
    cfg['pdk']['grid'][stackup][layer]['ypitch'] = {
        'switch': "-pdk_grid_ypitch 'stackup layer <float>'",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK routing grid horizontal wire pitch',
        'example': [
            "cli: -pdk_grid_ypitch 'M10 m2 0.5'",
            "api: chip.set('pdk','grid','M10','m2','ypitch','0.5')"],
        'help': """
        Defines the routing pitch for horizontal wires on a per stackup and
        per metal basis, specified in um. Metal layers are ordered
        from m1 to mn, where m1 is the lowest routing layer in the tech.lef.
        If not defined, the value is taken from the PDK tech.lef.
        """
    }

    # Vertical Grid Offset
    cfg['pdk']['grid'][stackup][layer]['xoffset'] = {
        'switch': "-pdk_grid_xoffset 'stackup layer <float>'",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK routing grid vertical wire offset',
        'example': [
            "cli: -pdk_grid_xoffset 'M10 m2 0.5'",
            "api: chip.set('pdk','grid','M10','m2','xoffset','0.5')"],
        'help': """
        Defines the grid offset of a vertical metal layer specified on a per
        stackup and per metal basis, specified in um.
        If not defined, the value is taken from the PDK tech.lef.
        """
    }

    # Horizontal Grid Offset
    cfg['pdk']['grid'][stackup][layer]['yoffset'] = {
        'switch': "-pdk_grid_yoffset 'stackup layer <float>'",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK routing grid horizontal wire offset',
        'example': [
            "cli: -pdk_grid_yoffset 'M10 m2 0.5'",
            "api: chip.set('pdk','grid','M10','m2','yoffset','0.5')"],
        'help': """
        Defines the grid offset of a horizontal metal layer specified on a per
        stackup and per metal basis, specified in um.
        If not defined, the value is taken from the PDK tech.lef.
        """
    }

    # Routing Layer Adjustment
    cfg['pdk']['grid'][stackup][layer]['adj'] = {
        'switch': "-pdk_grid_adj 'stackup layer <float>'",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK routing grid resource adjustment',
        'example': [
            "cli: -pdk_grid_adj 'M10 m2 0.5'",
            "api: chip.set('pdk','grid','M10','m2','adj','0.5')"],
        'help': """
        Defines the routing resources adjustments for the design on a per layer
        basis. The value is expressed as a fraction from 0 to 1. A value of
        0.5 reduces the routing resources by 50%. If not defined, 100%
        routing resource utilization is permitted.
        """
    }

    # Routing Layer Capacitance
    cfg['pdk']['grid'][stackup][layer]['cap'] = {
        'switch': "-pdk_grid_cap 'stackup layer <float>'",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK routing layer unit capacitance',
        'example': [
            "cli: -pdk_grid_cap 'M10 m2 0.2'",
            "api: chip.set('pdk','grid','M10','m2','cap','0.2')"],
        'help': """
        Unit capacitance of a wire defined by the grid width and spacing values
        in the 'grid' structure. The value is specified as ff/um on a per
        stackup and per metal basis. As a rough rule of thumb, this value
        tends to stay around 0.2ff/um. This number should only be used for
        reality confirmation. Accurate analysis should use the PEX models.
        """
    }

    # Routing Layer Resistance
    cfg['pdk']['grid'][stackup][layer]['res'] = {
        'switch': "-pdk_grid_res 'stackup layer <float>'",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK routing layer unit resistance',
        'example': [
            "cli: -pdk_grid_res 'M10 m2 0.2'",
            "api: chip.set('pdk','grid','M10','m2','res','0.2')"],
        'help': """
        Resistance of a wire defined by the grid width and spacing values
        in the 'grid' structure.  The value is specified as ohms/um. The number
        is only meant to be used as a sanity check and for coarse design
        planning. Accurate analysis should use the PEX models.
        """
    }

    # Wire Temperature Coefficient
    cfg['pdk']['grid'][stackup][layer]['tcr'] = {
        'switch': "-pdk_grid_tcr 'stackup layer <float>'",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK routing layer temperature coefficient',
        'example': [
            "cli: -pdk_grid_tcr 'M10 m2 0.1'",
            "api: chip.set('pdk','grid','M10','m2','tcr','0.1')"],
        'help': """
        Temperature coefficient of resistance of the wire defined by the grid
        width and spacing values in the 'grid' structure. The value is specified
        in %/ deg C. The number is only meant to be used as a sanity check and
        for coarse design planning. Accurate analysis should use the PEX models.
        """
    }

    cfg['pdk']['tapmax'] = {
        'switch': '-pdk_tapmax <float>',
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK tap cell max distance rule',
        'example': [
            "cli: -pdk_tapmax 100",
            "api: chip.set('pdk', 'tapmax','100')"],
        'help': """
        Maximum distance allowed between tap cells in the PDK specified in
        um. The value is required for APR.
        """
    }

    cfg['pdk']['tapoffset'] = {
        'switch': "-pdk_tapoffset <float>",
        'require': None,
        'type': 'float',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'PDK tap cell offset rule',
        'example': [
            "cli: -pdk_tapoffset 100",
            "api: chip.set('pdk, 'tapoffset','100')"],
        'help': """
        Offset from the edge of the block to the tap cell grid specified
        in um. The value is required for APR.
        """
    }

    return cfg

###############################################################################
# Library Configuration
###############################################################################

#TODO: refactor to pull project parameters diretly from 'project'

def schema_libs(cfg, lib='default', stackup='default', corner='default'):

    cfg['library'] = {}
    cfg['library'][lib] = {}
    cfg['library'][lib][corner] = {}

    #data related fields
    cfg['library'][lib]['type'] = {
        'switch': "-library_type 'lib <str>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'Library type',
        'example': ["cli: -library_type 'mylib stdcell'",
                    "api: chip.set('library','mylib','type','stdcell')"],
        'help': """
        Type of the library being configured. A 'stdcell' type is reserved
        for fixed height standard cell libraries. A 'soft' type indicates
        a library that is provided as technology agnostic source code, and
        a 'hard' type indicates a technology specific non stdcell library.
        """
    }

    cfg['library'][lib]['source'] = {
        'switch': "-library_source 'lib <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library source files',
        'example': [
            "cli: -library_source 'mylib hello.v'",
            "api: chip.set('library','mylib','source','hello.v')"],
        'help': """
        List of library source files. File type is inferred from the
        file suffix. The parameter is required or 'soft' library types and
        optional for 'hard' and 'stdcell' library types.
        (\\*.v, \\*.vh) = Verilog
        (\\*.vhd)      = VHDL
        (\\*.sv)       = SystemVerilog
        (\\*.c)        = C
        (\\*.cpp, .cc) = C++
        (\\*.py)       = Python
        """
    }

    cfg['library'][lib]['testbench'] = {}
    cfg['library'][lib]['testbench']['default'] = {
        'switch': "-library_testbench 'lib simtype <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library testbench',
        'example': [
            "cli: -library_testbench 'mylib rtl ./mylib_tb.v'",
            "api: chip.set('library','mylib','testbench','rtl','/lib_tb.v')"],
        'help': """
        Filepaths to testbench specified on a per library and per simtype basis.
        Typical simulation types include rtl, spice.
        """
    }

    cfg['library'][lib]['pdk'] = {
        'switch': "-library_pdk 'lib <str>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'Library PDK',
        'example': ["cli: -library_pdk 'mylib freepdk45",
                    "api:  chip.set('library', 'mylib', 'pdk', 'freepdk45')"],
        'help': """
        Name of the PDK module used to create the library package. The module
        is checked and loaded based on the 'scpath' schema parameter. The
        parameter is required for hardened technology specific library types.
        """
    }

    cfg['library'][lib]['stackup'] = {
        'switch': "-library_stackup 'lib <str>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'Library stackup',
        'example': ["cli: -library_stackup 'mylib M10",
                    "api:  chip.set('library', 'mylib', 'stackup', '10')"],
        'help': """
        Name of the PDK metal stackup used by the library. The parameter is
        required for hardened technology specific library types.
        """
    }

    cfg['library'][lib]['arch'] = {
        'switch': "-library_arch 'lib <str>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'Library architecture type',
        'example': [
            "cli: -library_arch 'mylib 12t'",
            "api: chip.set('library','mylib','arch,'12t')"],
        'help': """
        A unique string that identifies the row height or performance
        class of a standard cell library for APR. The arch must match up with
        the name used in the pdk_aprtech dictionary. Mixing of library archs
        in a flat place and route block is not allowed. Examples of library
        archs include 6 track libraries, 9 track libraries, 10 track
        libraries, etc. The parameter is optional for 'component' libtypes.
        """
    }

    ###############################
    #Models (Timing, Power, Noise)
    ###############################

    #Operating Conditions (per corner)
    cfg['library'][lib]['opcond'] = {}
    cfg['library'][lib]['opcond'][corner] = {
        'switch': "-library_opcond 'lib corner <str>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'Library operating condition',
        'example': [
            "cli: -library_opcond 'lib ss_1.0v_125c WORST'",
            "api: chip.set('library','lib','opcond','ss_1.0v_125c','WORST')"],
        'help': """
        Default operating condition to use for mcmm optimization and
        signoff specified on a per corner basis.
        """
    }

    #Checks To Do (per corner)
    cfg['library'][lib]['check'] = {}
    cfg['library'][lib]['check'][corner] = {
        'switch': "-library_check 'lib corner <str>'",
        'require': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'shorthelp': 'Library corner checks',
        'example': [
            "cli: -library_check 'lib ss_1.0v_125c setup'",
            "api: chip.set('library','lib','check','ss_1.0v_125c','setup')"],
        'help': """
        Corner checks to perform during optimization and STA signoff.
        Names used in the 'mcmm' scenarios must align with the 'check' names
        used in this dictionary. Standard 'check' values include setup,
        hold, power, noise, reliability but can be extended based on eda
        support and methodology.
        """
    }

    #NLDM
    cfg['library'][lib]['nldm'] = {}
    cfg['library'][lib]['nldm'][corner] = {}
    cfg['library'][lib]['nldm'][corner]['default'] = {
        'switch': "-library_nldm 'lib corner format <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library NLDM timing model',
        'example': [
            "cli: -library_nldm 'lib ss lib ss.lib.gz'",
            "api: chip.set('library','lib','nldm','ss','lib','ss.lib.gz')"],
        'help': """
        Filepaths to NLDM models. Timing files are specified on a per lib,
        per corner, and per format basis. Legal file formats are lib (ascii)
        and ldb (binary). File decompression is handled automatically for
        gz, zip, and bz2 compression formats.
        """
    }

    #CCS
    cfg['library'][lib]['ccs'] = {}
    cfg['library'][lib]['ccs'][corner] = {}
    cfg['library'][lib]['ccs'][corner]['default'] = {
        'switch': "-library_ccs 'lib corner format <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library CCS timing model',
        'example': [
            "cli: -library_ccs 'lib ss lib ss.lib.gz'",
            "api: chip.set('library','lib','ccs','ss','lib','ss.lib.gz')"],
        'help': """
        Filepaths to CCS models. Timing files are specified on a per lib,
        per corner, and per format basis. Legal file formats are lib (ascii)
        and ldb (binary). File decompression is handled automatically for
        gz, zip, and bz2 compression formats.
        """
    }

    #SCM
    cfg['library'][lib]['scm'] = {}
    cfg['library'][lib]['scm'][corner] = {}
    cfg['library'][lib]['scm'][corner]['default'] = {
        'switch': "-library_scm 'lib corner format <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library SCM timing model',
        'example': [
            "cli: -library_scm 'lib ss lib ss.lib.gz'",
            "api: chip.set('library','lib','scm,'ss','lib','ss.lib.gz')"],
        'help': """
        Filepaths to SCM models. Timing files are specified on a per lib,
        per corner, and per format basis. Legal file formats are lib (ascii)
        and ldb (binary). File decompression is handled automatically for
        gz, zip, and bz2 compression formats.
        """
    }

    #AOCV
    cfg['library'][lib]['aocv'] = {}
    cfg['library'][lib]['aocv'][corner] = {
        'switch': "-library_aocv 'lib corner <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library AOCV timing model',
        'example': [
            "cli: -library_aocv 'lib ss lib.aocv'",
            "api: chip.set('library','lib','aocv','ss','lib_ss.aocv')"],
        'help': """
        Filepaths to AOCV models. Timing files are specified on a per lib,
        per corner basis. File decompression is handled automatically for
        gz, zip, and bz2 compression formats.
        """
    }

    #LEF
    cfg['library'][lib]['lef'] = {
        'switch': "-library_lef 'lib <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library LEF files',
        'example': ["cli: -library_lef 'mylib mylib.lef'",
                    "api: chip.set('library','mylib','lef,'mylib.lef')"],
        'help': """
        Abstracted view of library cells that gives a complete description
        of the cell's place and route boundary, pin positions, pin metals, and
        metal routing blockages.
        """
    }

    #GDS
    cfg['library'][lib]['gds'] = {
        'switch': "-library_gds 'lib <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library GDS files',
        'example': ["cli: -library_gds 'mylib mylib.gds'",
                    "api: chip.set('library','mylib','gds','mylib.gds')"],
        'help': """
        Complete mask layout of the library cells.
        """
    }
    cfg['library'][lib]['netlist'] = {}
    cfg['library'][lib]['netlist']['default'] = {
        'switch': "-library_netlist 'lib cdl <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library LVS netlists',
        'example': [
            "cli: -library_netlist 'mylib cdl mylib.cdl'",
            "api: chip.set('library','mylib','netlist','cdl','mylib.cdl')"],
        'help': """
        List of files containing the golden netlist used for layout versus
        schematic (LVS) checks. For transistor level libraries such as
        standard cell libraries and SRAM macros, this should be a CDL type
        netlist. For higher level modules like place and route blocks, it
        should be a verilog gate level netlist.
        """
    }
    cfg['library'][lib]['spice'] = {}
    cfg['library'][lib]['spice']['default'] = {
        'switch': "-library_spice 'lib format <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library spice netlists',
        'example': [
            "cli: -library_spice 'mylib pspice mylib.sp'",
            "api: chip.set('library','mylib','spice','pspice','mylib.sp')"],
        'help': """
        List of files containing simulation spice netlists specified on a
        per format basis.
        """
    }

    cfg['library'][lib]['hdl'] = {}
    cfg['library'][lib]['hdl']['default'] = {
        'switch': "-library_hdl 'lib format <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library HDL models',
        'example': [
            "cli: -library_hdl 'mylib verilog mylib.v'",
            "api: chip.set('library','mylib','hdl','verilog','mylib.v')"],
        'help': """
        Library HDL models, specified on a per format basis. Examples
        of legal formats include verilog, vhdl, systemc, c++, python.
        """
    }

    cfg['library'][lib]['atpg'] = {
        'switch': "-library_atpg 'lib <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library ATPG models',
        'example': ["cli: -library_atpg 'mylib mylib.atpg'",
                    "api: chip.set('library','mylib','atpg','mylib.atpg')"],
        'help': """
        Library models used for ATPG based automated fault based post
        manufacturing testing.
        """
    }

    cfg['library'][lib]['pgmetal'] = {
        'switch': "-library_pgmetal 'lib <str>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'Library power/ground layer',
        'example': ["cli: -library_pgmetal 'mylib m1'",
                    "api: chip.set('library','mylib','pgmetal','m1')"],
        'help': """
        Top metal layer used for power and ground routing within the library.
        The parameter can be used to guide cell power grid hookup by APR tools.
        """
    }


    cfg['library'][lib]['tag'] = {
        'switch': "-library_tag 'lib <str>'",
        'require': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'shorthelp': 'Library tags',
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
        'require': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'shorthelp': 'Library default driver cell',
        'example': ["cli: -library_driver 'mylib BUFX1/Z'",
                    "api: chip.set('library','mylib','driver','BUFX1/Z')"],
        'help': """
        Name of a library cell to be used as the default driver for
        block timing constraints. The cell should be strong enough to drive
        a block input from another block including wire capacitance.
        In cases where the actual driver is known, the actual driver cell
        should be used. The output driver should include the output pin.
        """
    }


    cfg['library'][lib]['site'] = {
        'switch': "-library_site 'lib <str>'",
        'require': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'shorthelp': 'Library site name',
        'example': ["cli: -library_site 'mylib core'",
                    "api: chip.set('library','mylib','site','core')"],
        'help': """
        List of sites to use for APR.
        """
    }

    cfg['library'][lib]['cells'] = {}
    cfg['library'][lib]['cells']['default'] = {
        'switch': "-library_cells 'lib group <str>'",
        'require': None,
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'shorthelp': 'Library cell lists',
        'example': [
            "cli: -library_cells 'mylib dontuse *eco*'",
            "api: chip.set('library','mylib','cells','dontuse','*eco*')"],
        'help': """
        List of cells grouped by a property that can be accessed
        directly by the designer and tools. The example below shows how
        all cells containing the string 'eco' could be marked as dont use
        for the tool.
        """
    }
    filetype = 'default'
    cfg['library'][lib]['binary'] = {}
    cfg['library'][lib]['binary'][filetype] = {
        'switch': "-library_binary 'lib filetype <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Library binary database',
        'example': [
            "cli: -library_binary 'lib oa ~/libdb'",
            "api: chip.set('library','lib','binary', 'oa','~/libdb')"],
        'help': """
        Filepaths to compiled library database specified on a per format
        basis. Example formats include oa, mw, ndm, opendb.
        """
    }

    return cfg

###############################################################################
# Flow Configuration
###############################################################################

def schema_flowgraph(cfg, step='default', index='default'):

    cfg['flowgraph'] = {}
    cfg['flowgraph'][step] =  {}
    cfg['flowgraph'][step][index] =  {}

    # Execution flowgraph
    cfg['flowgraph'][step][index]['input'] = {
        'switch': "-flowgraph_input 'step index <(str,str)>'",
        'type': '[(str,str)]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Flowgraph step input',
        'example': [
            "cli: -flowgraph_input 'cts 0 (place,0)'",
            "api:  chip.set('flowgraph','cts','0','input', ('place','0'))"],
        'help': """
        A list of inputs for the current step and index, specified as a
        (step,index) tuple.
        """
    }

    # Flow graph score weights
    cfg['flowgraph'][step][index]['weight'] = {}
    cfg['flowgraph'][step][index]['weight']['default'] = {
        'switch': "-flowgraph_weight 'step metric <float>'",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Flowgraph metric weights',
        'example': [
            "cli: -flowgraph_weight 'cts 0 area_cells 1.0'",
            "api:  chip.set('flowgraph','cts','0','weight','area_cells',1.0)"],
        'help': """
        Weights specified on a per step and per metric basis used to give
        effective "goodnes" score for a step by calculating the sum all step
        real metrics results by the corresponding per step weights.
        """
    }

    # Task tool/function
    cfg['flowgraph'][step][index]['tool'] = {
        'switch': "-flowgraph_tool 'step <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Flowgraph tool selection',
        'example': ["cli: -flowgraph_tool 'place openroad'",
                    "api: chip.set('flowgraph','place','0','tool','openroad')"],
        'help': """
        Name of the tool name used for task execution. Builtin tool names
        associated bound to core API functions include: minimum, maximum, join,
        verify, mux.
        """
    }

    # Arguments passed by user to setup function
    cfg['flowgraph'][step][index]['args'] = {
        'switch': "-flowgraph_args 'step index <str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Flowgraph function selection',
        'example': [
            "cli: -flowgraph_args 'cts 0 0'",
            "api:  chip.add('flowgraph','cts','0','args','0')"],
        'help': """
        User specified flowgraph string arguments specified on a
        per step and per index basis.
        """
    }

    # Valid bits set by user
    cfg['flowgraph'][step][index]['valid'] = {
        'switch': "-flowgraph_valid 'step 0 <str>'",
        'type': 'bool',
        'lock': 'false',
        'require': None,
        'defvalue': 'false',
        'shorthelp': 'Flowgraph task valid bit',
        'example': [
            "cli: -flowgraph_valid 'cts 0 true'",
            "api:  chip.set('flowgraph','cts','0','valid',True)"],
        'help': """
        Flowgraph valid bit specified on a per step and per index basis.
        The parameter can be used to control flow execution. If the bit
        is cleared (0), then the step/index combination is invalid and
        should not be run.
        """
    }

    # Valid bits set by user
    cfg['flowgraph'][step][index]['timeout'] = {
        'switch': "-flowgraph_timeout 'step 0 <float>'",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Flowgraph step/index timeout value',
        'example': [
            "cli: -flowgraph_timeout 'cts 0 3600'",
            "api:  chip.set('flowgraph','cts','0','timeout', 3600)"],
        'help': """
        Timeout value in seconds specified on a per step and per index
        basis. The flowgraph timeout value is compared against the
        wall time tracked by the SC runtime to determine if an
        operation should continue. Timeout values help in situations
        where 1.) an operation is stuck and may never finish. 2.) the
        operation progress has saturated and continued execution has
        a negative return on investment.
        """
    }

    return cfg

###########################################################################
# Flow Status
###########################################################################
def schema_flowstatus(cfg, step='default', index='default'):

    cfg['flowstatus'] = {}
    cfg['flowstatus'][step] =  {}
    cfg['flowstatus'][step][index] = {}

    # Flow error indicator
    cfg['flowstatus'][step][index]['error'] = {
        'switch': "-flowstatus_error 'step index <int>'",
        'type': 'int',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Flowgraph index error status',
        'example': [
            "cli: -flowstatus_error 'cts 10 1'",
            "api:  chip.set('flowstatus','cts','10','error',1)"],
        'help': """
        Status parameter that tracks runstep errors.
        """
    }

    # Flow input selector
    cfg['flowstatus'][step][index]['select'] = {
        'switch': "-flowstatus_select 'step index <(str,str)>'",
        'type': '[(str,str)]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Flowgraph select record',
        'example': [
            "cli: -flowstatus_select 'cts 0 (place,42)'",
            "api:  chip.set('flowstatus', 'cts', '0', 'select', ('place','42'))"],
        'help': """
        A list of selected inputs for the current step/index specified as
        (in_step,in_index) tuple.
        """
    }

    # Flow step max
    cfg['flowstatus'][step][index]['max'] = {
        'switch': "-flowstatus_max 'step index <int>'",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Flowgraph max value',
        'example': [
            "cli: -flowstatus_max 'cts 0 99.99'",
            "api:  chip.set('flowstatus', 'cts, '0', 'max', '99.99')"],
        'help': """
        Status parameter of selected value recorded from the maximum()
        function.
        """
    }

    # Flow step min
    cfg['flowstatus'][step][index]['min'] = {
        'switch': "-flowstatus_min 'step index <int>'",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Flowgraph max value',
        'example': [
            "cli: -flowstatus_min 'cts 0 0.0'",
            "api:  chip.set('flowstatus', 'cts, '0', 'max', '0.0')"],
        'help': """
        Status parameter of selected value recorded from the minimum()
        calculation.
        """
    }

    return cfg


###########################################################################
# Job flow
###########################################################################

def schema_jobs (cfg, job='default', step='default', index='default'):

    # Flow step min
    cfg['jobinput'] = {}
    cfg['jobinput'][job] = {}
    cfg['jobinput'][job][step] = {}
    cfg['jobinput'][job][step][index] = {
        'switch': "-jobinput 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Jobname inputs to current run',
        'example': [
            "cli: -jobinput 'job1 cts 0 job0'",
            "api:  chip.set('jobinput', 'job1', 'cts, '0', 'job0')"],
        'help': """
        Specifies jobname inputs for the current run() on a per step
        and per index basis. During execution, the default behavior is to
        copy inputs from the current job.
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

    cfg['eda'][tool][step][index]['exe'] = {
        'switch': "-eda_exe 'tool step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Tool executable name',
        'example': [
            "cli: -eda_exe 'openroad cts 0 openroad'",
            "api:  chip.set('eda','openroad','cts','0','exe','openroad')"],
        'help': """
        Name of the executable or the full path to the executable
        specified on a per tool and step basis.
        """
    }

    cfg['eda'][tool][step][index]['path'] = {
        'switch': "-eda_path 'tool step index <str>'",
        'type': '[dir]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool executable path',
        'example': [
            "cli: -eda_path 'openroad cts 0 /usr/local/bin'",
            "api:  chip.set('eda','openroad','cts','0','path','/usr/local/bin')"],
        'help': """
        File system path to tool executable. The path is appended to the 'exe'
        parameter for batch runs and output as an environment variable for
        interactive setup.
        """
    }

    # version-check
    cfg['eda'][tool][step][index]['vswitch'] = {
        'switch': "-eda_vswitch 'tool step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Tool executable version switch',
        'example': [
            "cli: -eda_vswitch 'openroad cts 0 -version'",
            "api:  chip.set('eda','openroad','cts','0','vswitch','-version')"],
        'help': """
        Command line switch to use with executable used to print out
        the version number. Common switches include -v, -version,
        --version.
        """
    }

    # exe vendor
    cfg['eda'][tool][step][index]['vendor'] = {
        'switch': "-eda_vendor 'tool step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Tool vendor',
        'example': ["cli: -eda_vendor 'yosys syn 0 yosys'",
                    "api: chip.set('eda','yosys','syn','0','vendor','yosys')"],
        'help': """
        Name of the tool vendor specified on a per tool and step basis.
        Parameter can be used to set vendor specific technology variables
        in the PDK and libraries. For open source projects, the project
        name should be used in place of vendor.
        """
    }

    # exe version
    cfg['eda'][tool][step][index]['version'] = {
        'switch': "-eda_version 'tool step index <str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool version number',
        'example': [
            "cli: -eda_version 'openroad cts 0 1.0'",
            "api:  chip.set('eda','openroad','cts','0','version','1.0')"],
        'help': """
        Version of the tool executable specified on a per tool and per step
        basis. Mismatch between the step specified and the step available results
        in an error.
        """
    }

    # licenseserver
    cfg['eda'][tool][step][index]['licenseserver'] = {}
    cfg['eda'][tool][step][index]['licenseserver']['default'] = {
        'switch': "-eda_licenseserver 'tool step index name <str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool license server',
        'example': [
            "cli: -eda_licenseserver 'atool place 0 ACME_LICENSE_FILE 1700@server'",
            "api:  chip.set('eda','atool','place','0','licenseserver', 'ACME_LICENSE_FILE', '1700@server')"],
        'help': """
        Defines a set of tool specific environment variables used by the executables
        that depend on license key servers to control access. For multiple servers,
        separate each server by a 'colon'. The named license variable are read at
        runtime (run()) and the environment variables are set.
        """
    }

    # options
    cfg['eda'][tool][step][index]['option'] = {
        'switch': "-eda_option 'tool step index name <str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool options',
        'example': [
            "cli: -eda_option 'openroad cts 0 -no_init'",
            "api: chip.set('eda','openroad','cts','0','option','-no_init')"],
        'help': """
        List of command line options for the tool executable, specified on
        a per tool and per step basis. Options should not include spaces.
        For multiple argument options, each option is a separate list element.
        """
    }

    # variables
    cfg['eda'][tool][step][index]['variable'] = {}
    cfg['eda'][tool][step][index]['variable']['default'] = {
        'switch': "-eda_variable 'tool step index name <str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool script variables',
        'example': [
            "cli: -eda_variable 'openroad cts 0 myvar 42'",
            "api: chip.set('eda','openroad','cts','0','variable','myvar', '42')"],
        'help': """
        Executable script variables specified as key value pairs. Variable
        names and value types must match the name and type of tool and reference
        script consuming the variable.
        """
    }

    # input files
    cfg['eda'][tool][step][index]['input'] = {
        'switch': "-eda_input 'tool step index <str>'",
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool input files',
        'example': [
            "cli: -eda_input 'openroad place 0 oh_add.def'",
            "api: chip.set('eda','openroad','place','0','input','oh_add.def')"],
        'help': """
        List of data files to be copied from previous flowgraph steps 'output'
        directory. The list of steps to copy files from is defined by the
        list defined by the dictionary key ['flowgraph', step, 'input'].
        'All files must be available for flow to continue. If a file
        is missing, the program exists on an error.
        """
    }

    # output files
    cfg['eda'][tool][step][index]['output'] = {
        'switch': "-eda_output 'tool step index <str>'",
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool output files ',
        'example': ["cli: -eda_output 'openroad place 0 oh_add.def'",
                    "api: chip.set('eda','openroad','place','0','output','oh_add.def')"],
        'help': """
        List of data files produced by the current task and placed in the
        'output' directory. During execution, if a file is missing, the
        program exists on an error.
        """
    }

    # report files
    report_type = 'default'
    cfg['eda'][tool][step][index]['report'] = {}
    cfg['eda'][tool][step][index]['report'][report_type] = {
        'switch': "-eda_report 'tool step index report_type <str>'",
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool report files ',
        'example': [
            "cli: -eda_report 'yosys syn 0 hold hold.rpt'",
            "api: chip.set('eda','yosys','syn','0','report','hold','hold.rpt')"],
        'help': """
        List of reports of type of a certain kind produced by the task within the
        local 'reports' directory.
        """
    }

    # list of parameters used by tool
    cfg['eda'][tool][step][index]['require'] = {
        'switch': "-eda_req 'tool step index <str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Tool parameter requirements',
        'example': [
            "cli: -eda_require 'openroad cts 0 design'",
            "api: chip.set('eda','openroad', 'cts','0','require','design')"],
        'help': """
        List of keypaths to required tool parameters. The list is used
        by check() to verify that all parameters have been set up before
        step execution begins.
        """
    }

    # refdir
    cfg['eda'][tool][step][index]['refdir'] = {
        'switch': "-eda_refdir 'tool step index <dir>'",
        'type': 'dir',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Tool reference directory',
        'example': [
            "cli: -eda_refdir 'yosys syn 0 ./myref'",
            "api:  chip.set('eda','yosys','syn','0','refdir','./myref')"],
        'help': """
        Path to directories  containing compilation scripts, specified
        on a per step basis.
        """
    }

    # entry point scripts
    cfg['eda'][tool][step][index]['script'] = {
        'switch': "-eda_script 'tool step index <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Tool entry script',
        'example': [
            "cli: -eda_script 'yosys syn 0 syn.tcl'",
            "api: chip.set('eda','yosys','syn','0','script','syn.tcl')"],
        'help': """
        Path to the entry point compilation script called by the executable,
        specified on a per tool and per step basis.
        """
    }

    # manifest format
    cfg['eda'][tool][step][index]['format'] = {
        'switch': "-eda_format 'tool step index <file>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': 'tcl',
        'shorthelp': 'Tool manifest file format',
        'example': [
            "cli: -eda_format 'yosys syn 0 tcl'",
            "api: chip.set('eda','yosys','syn','0','format','tcl')"],
        'help': """
        File format for manifest handoff to tool. Supported formats are tcl,
        yaml, and json.
        """
    }


    # pre execution script
    cfg['eda'][tool][step][index]['prescript'] = {
        'switch': "-eda_prescript 'tool step index <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Tool pre-script plugin',
        'example': [
            "cli: -eda_prescript 'yosys syn 0 pre.tcl'",
            "api: chip.set('eda','yosys','syn','0','prescript','pre.tcl')"],
        'help': """
        Path to a user supplied script to execute after reading in the design
        but before the main execution stage of the step. Exact entry point
        depends on the step and main script being executed. An example
        of a prescript entry point would be immediately before global
        placement.
        """
    }

    # post execution script
    cfg['eda'][tool][step][index]['postscript'] = {
        'switch': "-eda_postscript 'tool step index <file>'",
        'require': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Tool post-script plugin',
        'example': ["cli: -eda_postscript 'yosys syn 0 post.tcl'",
                    "api: chip.set('eda','yosys','syn','0','postscript','post.tcl')"],
        'help': """
        Path to a user supplied script to execute after reading in the design
        but before the main execution stage of the step. Exact entry point
        depends on the step and main script being executed. An example
        of a postscript entry point would be immediately after global
        placement.
        """
    }

    # copy
    cfg['eda'][tool][step][index]['copy'] = {
        'switch': "-eda_copy 'tool step index <bool>'",
        'type': 'bool',
        'lock': 'false',
        'require': None,
        'defvalue': "false",
        'shorthelp': 'Tool copy-local option',
        'example': ["cli: -eda_copy 'openroad cts 0 true'",
                    "api: chip.set('eda','openroad','cts','0','copy',true)"],
        'help': """
        Specifies that the reference script directory should be copied and run
        from the local run directory. The option is specified on a per tool and
        per step basis.
        """
    }

    # parallelism
    cfg['eda'][tool][step][index]['threads'] = {
        'switch': "-eda_threads 'tool step index <int>'",
        'type': 'int',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Tool job parallelism',
        'example': ["cli: -eda_threads 'magic drc 0 64'",
                    "api: chip.set('eda','magic','drc','0','threads','64')"],
        'help': """
        Thread parallelism to use for execution specified on a per tool and per
        step basis. If not specified, SC queries the operating system and sets
        the threads based on the maximum thread count supported by the
        hardware.
        """
    }

    # turn off warning
    cfg['eda'][tool][step][index]['woff'] = {
        'switch': "-eda_woff 'tool step index name <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Tool warning filter',
        'example': ["cli: -eda_woff 'verilator import 0 COMBDLY'",
                    "api: chip.set('eda','verilator','import','0','woff','COMBDLY')"],
        'help': """
        A list of EDA warnings for which printing should be suppressed specified
        on a per tool and per step basis. Generally this is done on a per
        design basis after review has determined that warning can be safely
        ignored The code for turning off warnings can be found in the specific
        tool reference manual.
        """
    }

    # continue
    cfg['eda'][tool][step][index]['continue'] = {
        'switch': "-eda_continue 'tool step index <bool>'",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': "Tool continue-on-error",
        'example': [
            "cli: -eda_continue 'verilator import 0 true'",
            "api: chip.set('eda','verilator','import','0','continue',true)"],
        'help': """
        Directs tool to not exit on error.
        """
    }

    return cfg

###########################################################################
# Local (not global!) parameters for controlling tools
###########################################################################
def schema_arg(cfg):


    cfg['arg'] = {}

    cfg['arg']['step'] = {
        'switch': "-arg_step <str>",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Current execution step',
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
        'require': None,
        'defvalue': '0',
        'shorthelp': 'Current step Index',
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

def schema_metric(cfg, step='default', index='default',group='default', ):

    cfg['metric'] = {}
    cfg['metric'][step] = {}
    cfg['metric'][step][index] = {}

    cfg['metric'][step][index]['errors'] = {}
    cfg['metric'][step][index]['errors'][group] = {
        'switch': "-metric_errors 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric total errors',
        'example': [
            "cli: -metric_errors 'dfm 0 goal 0'",
            "api: chip.set('metric','dfm','0','errors','real','0')"],
        'help': """
        Metric tracking the total number of errors on a per step basis.
        """
    }

    cfg['metric'][step][index]['warnings'] = {}
    cfg['metric'][step][index]['warnings'][group] = {
        'switch': "-metric_warnings 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric total warnings',
        'example': [
            "cli: -metric_warnings 'dfm 0 goal 0'",
            "api: chip.set('metric','dfm','0','warnings','real','0')"],

        'help': """
        Metric tracking the total number of warnings on a per step basis.
        """
    }

    cfg['metric'][step][index]['drvs'] = {}
    cfg['metric'][step][index]['drvs'][group] = {
        'switch': "-metric_drv 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric design rule violations',
        'example': [
            "cli: -metric_drvs 'dfm 0 goal 0'",
            "api: chip.set('metric','dfm','0','drvs','real','0')"],
        'help': """
        Metric tracking the total number of design rule violations on per step
        basis.
        """
    }

    cfg['metric'][step][index]['unconstrained'] = {}
    cfg['metric'][step][index]['unconstrained'][group] = {
        'switch': "-metric_unconstrained 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric unconstrained paths',
        'example': [
            "cli: -metric_unconstrained 'place 0 goal 0'",
            "api: chip.set('metric','place','0','unconstrained','goal','0')"],
        'help': """
        Metric tracking the total number of unconstrained timing paths.
        """
    }

    cfg['metric'][step][index]['coverage'] = {}
    cfg['metric'][step][index]['coverage'][group] = {
        'switch': "-metric_coverage 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric coverage',
        'example': [
            "cli: -metric_coverage 'place 0 goal 99.9'",
            "api: chip.set('metric','place','0','coverage','goal','99.9')"],
        'help': """
        Metric tracking the test coverage in the design expressed as a percentage
        with 100 meaning full coverage. The meaning of the metric depends on the
        task being executed. It can refer to code coverage, feature coverage,
        stuck at fault coverage.
        """
    }

    cfg['metric'][step][index]['security'] = {}
    cfg['metric'][step][index]['security'][group] = {
        'switch': "-metric_security 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric security',
        'example': [
            "cli: -metric_security 'place 0 goal 100'",
            "api: chip.set('metric','place','0','security','goal','100')"],
        'help': """
        Metric tracking the level of security (1/vulnerability) of the design.
        A completely secure design would have a score of 100. There is no
        absolute scale for the security metrics (like with power, area, etc)
        so the metric will be task and tool dependent.
        """
    }


    cfg['metric'][step][index]['luts'] = {}
    cfg['metric'][step][index]['luts'][group] = {
        'switch': '-metric_luts step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'fpga',
        'defvalue': None,
        'shorthelp': 'Metric FPGA LUT count',
        'example': [
            "cli: -metric_luts 'place 0 goal 100'",
            "api: chip.set('metric','place','0','luts','real','100')"],
        'help': """
        Metric tracking the total FPGA LUTs used by the design as reported
        by the implementation tool. There is no standard LUT definition,
        so metric comparisons can generally only be done between runs on
        identical tools and device families.
        """
    }

    cfg['metric'][step][index]['dsps'] = {}
    cfg['metric'][step][index]['dsps'][group] = {
        'switch': '-metric_dsps step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'fpga',
        'defvalue': None,
        'shorthelp': 'Metric FPGA DSP count',
        'example': [
            "cli: -metric_dsps 'place 0 goal 100'",
            "api: chip.set('metric','place','0','dsps','real','100')"],
        'help': """
        Metric tracking the total FPGA DSP slices used by the design as reported
        by the implementation tool. There is no standard DSP definition,
        so metric comparisons can generally only be done between runs on
        identical tools and device families.
        """
    }

    cfg['metric'][step][index]['brams'] = {}
    cfg['metric'][step][index]['brams'][group] = {
        'switch': '-metric_brams step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'fpga',
        'defvalue': None,
        'shorthelp': 'Metric FPGA BRAM count',
        'example': [
            "cli: -metric_bram 'place 0 goal 100'",
            "api: chip.set('metric','place','0','brams','real','100')"],
        'help': """
        Metric tracking the total FPGA BRAM tiles used by the design as
        reported by the implementation tool. There is no standard DSP
        definition, so metric comparisons can generally only be done between
        runs on identical tools and device families.
        """
    }

    cfg['metric'][step][index]['cellarea'] = {}
    cfg['metric'][step][index]['cellarea'][group] = {
        'switch': '-metric_cellarea step index group <float>',
        'type': 'float',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric cell area',
        'example': [
            "cli: -metric_cellarea 'place 0 goal 100.00'",
            "api: chip.set('metric','place','0','cellarea','real','100.00')"],
        'help': """
        Metric tracking the sum of all non-filler standard cells on a per and per
        index basis specified in um^2.
        """
    }

    cfg['metric'][step][index]['totalarea'] = {}
    cfg['metric'][step][index]['totalarea'][group] = {
        'switch': '-metric_totalarea step index group <float>',
        'type': 'float',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric total area',
        'example': [
            "cli: -metric_totalarea 'place 0 goal 100.00'",
            "api: chip.set('metric','place','0','totalarea','real','100.00')"],
        'help': """
        Metric tracking the total physical area occupied by the design,
        including cellarea, fillers, and any addiotnal white space/margins. The
        number is specified in um^2.
        """
    }

    cfg['metric'][step][index]['utilization'] = {}
    cfg['metric'][step][index]['utilization'][group] = {
        'switch': '-metric_utilization step index group <float>',
        'type': 'float',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric area utilization',
        'example': [
            "cli: -metric_utilization 'place 0 goal 50.00'",
            "api: chip.set('metric','place','0','utilization','real','50.00')"],
        'help': """
        Metric tracking the area utilization of the design calculated as
        100 * (cellarea/totalarea).
        """
    }

    cfg['metric'][step][index]['peakpower'] = {}
    cfg['metric'][step][index]['peakpower'][group] = {
        'switch': '-metric_peakpower step index group <float>',
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric total power',
        'example': [
            "cli: -metric_peakpower 'place 0 real 0.001'",
            "api: chip.set('metric','place','0','peakpower','real','0.001')"],
        'help': """
        Metric tracking the worst case total power of the design on a per
        step basis calculated based on setup config and VCD stimulus.
        stimulus. Metric unit is Watts.
        """
    }

    cfg['metric'][step][index]['standbypower'] = {}
    cfg['metric'][step][index]['standbypower'][group] = {
        'switch': '-metric_standbypower step index group <float>',
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric leakage power',
        'example': [
            "cli: -metric_standbypower 'place 0 real 1e-6'",
            "api: chip.set('metric',place','0','standbypower','real','1e-6')"],
        'help': """
        Metric tracking the leakage power of the design on a per step
        basis. Metric unit is Watts.
        """
    }

    cfg['metric'][step][index]['irdrop'] = {}
    cfg['metric'][step][index]['irdrop'][group] = {
        'switch': "-metric_irdrop 'step index group <int>'",
        'type': 'float',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric peak IR drop',
        'example': [
            "cli: -metric_irdrop 'place 0 real 0.05'",
            "api: chip.set('metric','place','0','irdrop','real','0.05')"],
        'help': """
        Metric tracking the peak IR drop in the design based on extracted
        power and ground rail parasitics, library power models, and
        switching activity. The switching activity calculated on a per
        node basis is taken from one of three possible sources, in order
        of priority: VCD file, SAIF file, 'activityfactor' parameter.
        """
    }

    cfg['metric'][step][index]['holdslack'] = {}
    cfg['metric'][step][index]['holdslack'][group] = {
        'switch': "-metric_holdslack 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric hold slack',
        'example': [
            "cli: -metric_holdslack 'place 0 real 0.0'",
            "api: chip.set('metric','place','0','holdslack','real','0')"],
        'help': """
        Metric tracking of worst hold slack (positive or negative) on
        a per per step and index basis. Metric unit is nanoseconds.
        """
    }

    cfg['metric'][step][index]['holdwns'] = {}
    cfg['metric'][step][index]['holdwns'][group] = {
        'switch': "-metric_holdwns 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric hold worst negative slack',
        'example': [
            "cli: -metric_holdwns 'place 0 real 0.42",
            "api: chip.set('metric','place','0','holdwns','real,'0.43')"],
        'help': """
        Metric tracking the worst hold/min timing path slack in the design.
        Positive values means there is spare/slack, negative slack means the design
        is failing a hold timing constraint. The metric unit is nanoseconds.
        """
    }

    cfg['metric'][step][index]['holdtns'] = {}
    cfg['metric'][step][index]['holdtns'][group] = {
        'switch': "-metric_holdtns 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Metric hold total negative slack',
        'example': [
            "cli: -metric_holdtns 'place 0 real 0.0'",
            "api: chip.set('metric','place','0','holdtns','real','0')"],
        'help': """
        Metric tracking of total negative hold slack (TNS) on a per step basis.
        Metric unit is nanoseconds.
        """
    }

    cfg['metric'][step][index]['holdpaths'] = {}
    cfg['metric'][step][index]['holdpaths'][group] = {
        'switch': "-metric_holdpaths 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric hold path violations',
        'example': [
            "cli: -metric_holdpaths 'place 0 real 0'",
            "api: chip.set('metric','place','0','holdpaths','real','0')"],
        'help': """
        Metric tracking the total number of timing paths violating hold
        constraints.
        """
    }


    cfg['metric'][step][index]['setupslack'] = {}
    cfg['metric'][step][index]['setupslack'][group] = {
        'switch': "-metric_setupslack 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric setup slack',
        'example': [
            "cli: -metric_setupslack 'place 0 real 0.0'",
            "api: chip.set('metric','place','0','setupslack','real','0')"],
        'help': """
        Metric tracking of worst setup slack (positive or negative) on
        a per per step and index basis. Metric unit is nanoseconds.
        """
    }

    cfg['metric'][step][index]['setupwns'] = {}
    cfg['metric'][step][index]['setupwns'][group] = {
        'switch': "-metric_setupwns 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric setup worst negative slack',
        'example': [
            "cli: -metric_setupwns 'place 0 goal 0.0",
            "api: chip.set('metric','place','0','setupwns','real','0.0')"],
        'help': """
        Metric tracking the worst setup timing path slack in the design (WNS)
        on a per step and per index basis. The maximum WNS is 0.0. The metric
        unit is nanoseconds.
        """
    }

    cfg['metric'][step][index]['setuptns'] = {}
    cfg['metric'][step][index]['setuptns'][group] = {
        'switch': "-metric_setuptns 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric setup total negative slack',
        'example': [
            "cli: -metric_setuptns 'place 0 goal 0.0'",
            "api: chip.set('metric','place','0','setuptns','real','0.0')"],
        'help': """
        Metric tracking of total negative setup slack (TNS) on a per step basis.
        The maximum TNS is 0.0.  Metric unit is nanoseconds.
        """
    }

    cfg['metric'][step][index]['setuppaths'] = {}
    cfg['metric'][step][index]['setuppaths'][group] = {
        'switch': "-metric_setuppaths 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric setup path violations',
        'example': [
            "cli: -metric_setuppaths 'place 0 real 0'",
            "api: chip.set('metric','place','0','setuppaths','real','0')"],
        'help': """
        Metric tracking the total number of timing paths violating setup
        constraints.
        """
    }

    cfg['metric'][step][index]['cells'] = {}
    cfg['metric'][step][index]['cells'][group] = {
        'switch': '-metric_cells step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric instance count',
        'example': [
            "cli: -metric_cells 'place 0 goal 100'",
            "api: chip.set('metric','place','0','cells','goal,'100')"],
        'help': """
        Metric tracking the total number of instances on a per step basis.
        Total cells includes registers. In the case of FPGAs, the it
        represents the number of LUTs.
        """
    }

    cfg['metric'][step][index]['registers'] = {}
    cfg['metric'][step][index]['registers'][group] = {
        'switch': "-metric_registers 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric register count',
        'example': [
            "cli: -metric_registers 'place 0 real 100'",
            "api: chip.set('metric','place','0','registers','real','100')"],
        'help': """
        Metric tracking the total number of register cells.
        """
    }

    cfg['metric'][step][index]['buffers'] = {}
    cfg['metric'][step][index]['buffers'][group] = {
        'switch': "-metric_buffers 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric buffer count',
        'example': [
            "cli: -metric_buffers 'place 0 real 100'",
            "api: chip.set('metric','place','0','buffers','real','100')"],
        'help': """
        Metric tracking the total number of buffers and inverters in
        the design. An excessive count usually indicates a flow, design,
        or constraints problem.
        """
    }

    cfg['metric'][step][index]['transistors'] = {}
    cfg['metric'][step][index]['transistors'][group] = {
        'switch': '-metric_transistors step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric transistor count',
        'example': [
            "cli: -metric_transistors 'place 0 goal 100'",
            "api: chip.set('metric','place','0','transistors','real','100')"],
        'help': """
        Metric tracking the total number of transistors in the design
        on a per step basis.
        """
    }
    cfg['metric'][step][index]['nets'] = {}
    cfg['metric'][step][index]['nets'][group] = {
        'switch': '-metric_nets step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric net count',
        'example': [
            "cli: -metric_nets 'place 0 real 100'",
            "api: chip.set('metric','place','0','nets','real','100')"],
        'help': """
        Metric tracking the total number of net segments on a per step
        basis.
        """
    }
    cfg['metric'][step][index]['pins'] = {}
    cfg['metric'][step][index]['pins'][group] = {
        'switch': '-metric_pins step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric pin count',
        'example': [
            "cli: -metric_pins 'place 0 real 100'",
            "api: chip.set('metric','place','0','pins','real','100')"],
        'help': """
        Metric tracking the total number of I/O pins on a per step
        basis.
        """
    }
    cfg['metric'][step][index]['vias'] = {}
    cfg['metric'][step][index]['vias'][group] = {
        'switch': '-metric_vias step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric via count',
        'example': [
            "cli: -metric_vias 'route 0 real 100'",
            "api: chip.set('metric','place','0','vias','real','100')"],
        'help': """
        Metric tracking the total number of vias in the design.
        """
    }
    cfg['metric'][step][index]['wirelength'] = {}
    cfg['metric'][step][index]['wirelength'][group] = {
        'switch': '-metric_wirelength step index group <float>',
        'type': 'float',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric wirelength',
        'example': [
            "cli: -metric_wirelength 'route 0 real 100.00'",
            "api: chip.set('metric','place','0','wirelength','real','100.42')"],
        'help': """
        Metric tracking the total wirelength in the design in meters.
        """
    }

    cfg['metric'][step][index]['overflow'] = {}
    cfg['metric'][step][index]['overflow'][group] = {
        'switch': '-metric_overflow step index group <int>',
        'type': 'int',
        'lock': 'false',
        'require': 'asic',
        'defvalue': None,
        'shorthelp': 'Metric routing overflow',
        'example': [
            "cli: -metric_overflow 'route 0 real 0'",
            "api: chip.set('metric','place','0','overflow','real','0')"],
        'help': """
        Metric tracking the total number of overflow tracks for the routing.
        Any non-zero number suggests an over congested design. To analyze
        where the congestion is occurring inspect the router log files for
        detailed per metal overflow reporting and open up the design to find
        routing hotspots.
        """
    }

    cfg['metric'][step][index]['runtime'] = {}
    cfg['metric'][step][index]['runtime'][group] = {
        'switch': "-metric_runtime 'step index group <float>",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric total runtime',
        'example': [
            "cli: -metric_runtime 'dfm 0 goal 35.3'",
            "api: chip.set('metric','dfm','0','runtime','real','35.3')"],
        'help': """
        Metric tracking the total runtime on a per step basis. Time recorded
        as wall clock time specified in seconds.
        """
    }

    cfg['metric'][step][index]['memory'] = {}
    cfg['metric'][step][index]['memory'][group] = {
        'switch': "-metric_memory 'step index group <float>'",
        'type': 'float',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Metric total memory',
        'example': [
            "cli: -metric_memory 'dfm 0 goal 10e9'",
            "api: chip.set('metric','dfm','0','memory','real,'10e6')"],
        'help': """
        Metric tracking the total memory on a per step basis, specified
        in bytes.
        """
    }

    return cfg

###########################################################################
# Design Tracking
###########################################################################

def schema_record(cfg, job='default', step='default', index='default'):

    cfg['record'] = {}
    cfg['record'][job] = {}
    cfg['record'][job][step] = {}
    cfg['record'][job][step][index] = {}


    cfg['record'][job][step][index]['input'] = {
        'switch': "-record_input 'job step index <file>'",
        'require': None,
        'type': '[file]',
        'copy': 'false',
        'lock': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Record input files',
        'example': [
            "cli: -record_input 'job0 import 0 adder.v'",
            "api: chip.set('record','job0','import','0','input','adder.v')"],
        'help': """
        Record tracking all input files on a per step and index basis.
        """
    }

    cfg['record'][job][step][index]['output'] = {
        'switch': "-record_output 'job step index <file>'",
        'require': None,
        'type': '[file]',
        'copy': 'false',
        'lock': 'false',
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Record output files',
        'example': [
            "cli: -record_output 'job0 syn 0 outputs/adder.vg'",
            "api: chip.set('record','job0', 'syn','0','output','outputs/adder.vg')"],
        'help': """
        Record tracking all input files on a per step and index basis.
        """
    }

    cfg['record'][job][step][index]['tool'] = {
        'switch': "-record_tool 'job step index <file>'",
        'require': None,
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'shorthelp': 'Record tool name',
        'example': [
            "cli: -record_tool 'job0 syn 0 yosys'",
            "api: chip.set('record','job0', 'syn','0','tool','yosys')"],
        'help': """
        Record tracking the name of the tool on a per step and index basis.
        """
    }

    cfg['record'][job][step][index]['chipid'] = {
        'switch': "-record_chipid 'job step index <str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Record chip ID',
        'example': [
            "cli: -record_chipid 'job0 dfm 0 42'",
            "api: chip.set('record', 'job0','dfm','0','chipid','42')"],
        'help': """
        A unique ID for the chip object. The parameter is used to
        store a new ID for steps that generate a unique chip ID number
        and as readback verification for steps that process the chip
        but does not generate a new chip ID.
        """
    }

    cfg['record'][job][step][index]['exitstatus'] = {
        'switch': "-record_exitstatus 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record exit status',
        'example': [
            "cli: -record_exitstatus 'job0 dfm 0 0'",
            "api: chip.set('record', 'job0', 'dfm','0','exitstatus','0')"],
        'help': """
        Record with exit status code for step index. A zero indicates
        success, non-zero values represents an error. Non-zero values
        are not standard and tool/platform dependent.
        """
    }

    cfg['record'][job][step][index]['version']={}
    cfg['record'][job][step][index]['version']['sc'] = {
        'switch': "-record_version_sc 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record sc version',
        'example': [
            "cli: -record_version_sc 'job0 dfm 0 1.0'",
            "api: chip.set('record','job0', 'dfm','0', 'version', 'sc', '1.0')"],
        'help': """
        Record tracking the sc version number on the compute node.
        """
    }

    cfg['record'][job][step][index]['version']['tool'] = {
        'switch': "-record_version_tool 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record tool version',
        'example': [
            "cli: -record_version_tool 'job0 dfm 0 1.0'",
            "api: chip.set('record','job0','dfm','0','version','tool','1.0')"],
        'help': """
        Record tracking the version number of the executable, specified
        on per step and per index basis.
        """
    }

    cfg['record'][job][step][index]['starttime'] = {
        'switch': "-record_starttime 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record start-time',
        'example': [
            "cli: -record_starttime 'job0 dfm 2021-09-06 12:20:20'",
            "api: chip.set('record','job0', 'dfm','0','starttime','2021-09-06 12:20:20')"],
        'help': """
        Record tracking the start time stamp on a per step and index basis.
        The date format is the ISO 8601 format YYYY-MM-DD HR:MIN:SEC.
        """
    }

    cfg['record'][job][step][index]['endtime'] = {
        'switch': "-record_endtime 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record end-time',
        'example': ["cli: -record_endtime 'job0 dfm 0 2021-09-06 12:20:20'",
                    "api: chip.set('record','job0', 'dfm','0','endtime','2021-09-06 12:20:20')"],
        'help': """
        Record tracking the end time stamp on a per step and index basis.
        The date format is the ISO 8601 format YYYY-MM-DD HR:MIN:SEC.
        """
    }

    cfg['record'][job][step][index]['machine'] = {
        'switch': "-record_machine 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record machine name',
        'example': [
            "cli: -record_machine 'job0 dfm 0 carbon'",
            "api: chip.set('record','job0', 'dfm','0','machine','carbon')"],
        'help': """
        Record tracking the machine name for the step/index execution.
        (eg. carbon, silicon, mars, host0)
        """
    }

    cfg['record'][job][step][index]['region'] = {
        'switch': "-record_region 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record cloud region',
        'example': ["cli: -record_region 'job0 dfm 0 US Gov Boston'",
                    "api: chip.set('record','job0', 'dfm','0', 'region','US Gov Boston')"],
        'help': """
        Record tracking the operational region of the node. Recommended naming methodology:
        local: node is the local machine
        onprem: node in on-premises IT infrastructure
        public: generic public cloud
        govcloud: generic US government cloud
        <region>: cloud and entity specific region string name
        """
    }

    cfg['record'][job][step][index]['macaddr'] = {
        'switch': "-record_macaddr 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record MAC address',
        'example': [
            "cli: -record_macaddr 'job0 dfm 0 <addr>'",
            "api: chip.set('record', 'job0', 'dfm', '0', 'macaddr', '<addr>')"],
        'help': """
        Record tracking the MAC address of the node.
        """
    }

    cfg['record'][job][step][index]['ipaddr'] = {
        'switch': "-record_ipaddr 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record IP address',
        'example': [
            "cli: -record_ipaddr 'job0 dfm 0 <addr>'",
            "api: chip.set('record', 'job0', 'dfm', '0', 'ipaddr', '<addr>')"],
        'help': """
        Record tracking the IP address of the node.
        """
    }

    cfg['record'][job][step][index]['platform'] = {
        'switch': "-record_platform 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record platform',
        'example': [
            "cli: -record_platform 'job0 dfm 0 linux'",
            "api: chip.set('record', 'job0', 'dfm', '0', 'platform', 'linux')"],
        'help': """
        Record tracking the platform name on the node.
        (linux, windows, freebsd, macos, ...).
        """
    }

    cfg['record'][job][step][index]['distro'] = {
        'switch': "-record_distro 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record O/S distribution',
        'example': [
            "cli: -record_distro 'job0 dfm 0 ubuntu'",
            "api: chip.set('record', 'job0', 'dfm', '0', 'distro', 'ubuntu')"],
        'help': """
        Record tracking the platform distribution name on the node.
        (ubuntu, centos, redhat,...).
        """
    }

    cfg['record'][job][step][index]['version']['os'] = {
        'switch': "-record_version_os 'job step index machine <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record O/S version',
        'example': [
            "cli: -record_version_os 'job0 dfm 0 20.04.1-Ubuntu'",
            "api: chip.set('record', 'job0', 'dfm', '0', 'version', 'os', '20.04.1-Ubuntu')"],
        'help': """
        Record tracking the complete operating system version name. Since there is
        not standarrd version system for operating systems, extracting information
        from is platform dependent. For Linux based operating systems, the
        'osversion' is the version of the distro.
        """
    }

    cfg['record'][job][step][index]['version']['kernel'] = {
        'switch': "-record_version_kernel 'job step index <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record O/S kernel version',
        'example': [
            "cli: -record_version_kernel 'job0 dfm 0 5.11.0-34-generic'",
            "api: chip.set('record', 'job0', 'dfm', '0', 'version','kernel', '5.11.0-34-generic')"],
        'help': """
        Record tracking the operating system kernel version for platforms that
        support a distinction between os kernels and os distributions.
        """
    }

    cfg['record'][job][step][index]['arch'] = {
        'switch': "-record_arch 'job step index machine <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Record architecture',
        'example': [
            "cli: -record_arch 'job0 dfm 0 x86_64'",
            "api: chip.set('record', 'job0', 'dfm', '0', 'arch', 'x86_64')"],
        'help': """
        Record tracking the hardware architecture on the node.
        """
    }

    return cfg

###########################################################################
# Run Options
###########################################################################

def schema_options(cfg):
    ''' Run-time options
    '''


    cfg['remote'] = {
        'switch': "-remote <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': None,
        'defvalue': False,
        'shorthelp': 'Enable remote processing',
        'example': ["cli: -remote",
                    "api: chip.set('remote', True)"],
        'help': """
        Determines whether the job should be run locally, or on a remote server.
        """
    }

    cfg['credentials'] = {
        'switch': "-credentials <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'User credentials file',
        'example': ["cli: -credentials /home/user/.sc/credentials",
                    "api: chip.set('credentials','/home/user/.sc/credentials')"],
        'help': """
        Filepath to credentials used for remote processing. If the
        credentials parameter is empty, the remote processing client program
        tries to access the ".sc/credentials" file in the user's home
        directory. The file supports the following fields:

        userid=<user id>
        secret_key=<secret key used for authentication>
        server=<ipaddr or url>

        """
        }

    cfg['mode'] = {
        'switch': "-mode <str>",
        'type': 'str',
        'lock': 'false',
        'require': 'all',
        'defvalue': None,
        'shorthelp': 'Compilation mode',
        'example': ["cli: -mode fpga",
                    "api: chip.set('mode','fpga')"],
        'help': """
        Sets the compilation flow.
        """
    }

    cfg['target'] = {
        'switch': "-target <str>",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Compilation target',
        'example': ["cli: -target 'asicflow_freepdk45'",
                    "api: chip.set('target','asicflow_freepdk45')"],
        'help': """
        Compilation target double string separated by a single underscore,
        specified as "<process>_<edaflow>" for ASIC compilation and
        "<partname>_<edaflow>" for FPGA compilation. The process, edaflow,
        partname fields must be alphanumeric and cannot contain underscores.
        """
    }

    cfg['techarg'] = {}
    cfg['techarg']['default'] = {
        'switch': "-techarg 'arg <str>",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Target technology argument',
        'example': ["cli: -techarg 'mimcap true",
                    "api: chip.set('techarg','mimcap', 'true')"],
        'help': """
        Parameter passed in as key/value pair to the technology target
        referenced in the target() API call. See the target technology
        for specific guidelines regarding configuration parameters.
        """
    }

    cfg['flowarg'] = {}
    cfg['flowarg']['default'] = {
        'switch': "-flowarg 'arg <str>",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Target flow argument',
        'example': ["cli: -flowarg 'n 100",
                    "api: chip.set('flowarg','n', '100')"],
        'help': """
        Parameter passed in as key/value pair to the technology target
        referenced in the target() API call. See the target flow for
        specific guidelines regarding configuration parameters.
        """
    }

    cfg['cfg'] = {
        'switch': "-cfg <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Configuration file',
        'example': ["cli: -cfg mypdk.json",
                    "api: chip.set('cfg','mypdk.json')"],
        'help': """
        List of filepaths to legal SC schema configuration dictionaries
        saved as a JSON files using the writecfg() method. The files are
        read in automatically when using the 'sc' command line application.
        In Python programs, the cfg parameter is accessed by the readcfg()
        method to read and merge all files specified into the current
        project configuration schema.
        """
        }

    cfg['jobscheduler'] = {
        'switch': "-jobscheduler <str>",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Job scheduler name',
        'example': ["cli: -jobscheduler slurm",
                    "api: chip.set('jobscheduler','slurm')"],
        'help': """
        Sets the type of job scheduler to be used for each individual
        flowgraph steps. If the parameter is undefined, the steps are executed
        on the same machine that the SC was launched on. If 'slurm' is used,
        the host running the 'sc' command must be running a 'slurmctld' daemon
        managing a Slurm cluster. Additionally, the build directory ('-dir')
        must be located in shared storage which can be accessed by all hosts
        in the cluster.
        """
    }

    cfg['env'] = {}
    cfg['env']['default'] = {
        'switch': "-env 'var <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Environment variables',
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
        'require': None,
        'defvalue': [],
        'shorthelp': 'Search path',
        'example': ["cli: -scpath '/home/$USER/sclib'",
                    "api: chip.set('scpath', '/home/$USER/sclib')"],
        'help': """
        Specifies python modules paths for target import.
        """
    }

    cfg['clean'] = {
        'switch': "-clean <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Clean up files after run',
        'example': ["cli: -clean",
                    "api: chip.set('clean', True)"],
        'help': """
        Clean up all intermediate and non essential files at the end
        of a task, leaving only the log file and 'report' and
        'output' parameters associated with the task tool.
        """
    }

    cfg['hash'] = {
        'switch': "-hash <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Enable file hashing',
        'example': ["cli: -hash",
                    "api: chip.set('hash', True)"],
        'help': """
        Enables hashing of all inputs and outputs during
        compilation. The hash values are stored in the hashvalue field
        of the individual parameters.
        """
    }

    cfg['quiet'] = {
        'switch': "-quiet <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Quiet execution',
        'example': ["cli: -quiet",
                    "api: chip.set('quiet', True)"],
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
        'require': 'all',
        'defvalue': 'WARNING',
        'shorthelp': 'Logging level',
        'example': ["cli: -loglevel INFO",
                    "api: chip.set('loglevel', 'INFO')"],
        'help': """
        The debug param provides explicit control over the level of debug
        logging printed. Valid entries include INFO, DEBUG, WARNING, ERROR. The
        default value is WARNING.
        """
    }

    cfg['dir'] = {
        'switch': "-dir <dir>",
        'type': 'dir',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'build',
        'shorthelp': 'Build directory',
        'example': ["cli: -dir ./build_the_future",
                    "api: chip.set('dir','./build_the_future')"],
        'help': """
        The default build directory is in the local './build' where SC was
        executed. The 'dir' parameters can be used to set an alternate
        compilation directory path.
        """
    }

    cfg['jobname'] = {
        'switch': "-jobname <str>",
        'type': 'str',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'job0',
        'shorthelp': 'Job name',
        'example': ["cli: -jobname may1",
                    "api: chip.set('jobname','may1')"],
        'help': """
        Jobname during invocation of run(). The jobname combined with a
        defined director structure (<dir>/<design>/<jobname>/<step>/<index>)
        enables multiple levels of transparent job, step, and index
        introspection.
        """
    }

    cfg['jobincr'] = {
        'switch': "-jobincr <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Auto-increment jobname',
        'example': ["cli: -jobincr",
                    "api: chip.set('jobincr', True)"],
        'help': """
        Forces an auto-update of the jobname parameter if a directory
        matching the jobname is found in the build directory. If the
        jobname does not include a trailing digit, then a the number
        '1' is added to the jobname before updating the jobname
        parameter.  The option can be useful for automatically keeping
        all jobs ever run in a directory for tracking and debugging
        purposes.
        """
    }

    cfg['steplist'] = {
        'switch': "-steplist <str>",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Compilation step list',
        'example': ["cli: -steplist 'import'",
                    "api: chip.set('steplist','import')"],
        'help': """
        List of steps to execute. The default is to execute all steps defined
        in the flow graph.
        """
    }

    cfg['indexlist'] = {
        'switch': "-indexlist <str>",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Compilation index list',
        'example': ["cli: -indexlist '0'",
                    "api: chip.set('indexlist','0')"],
        'help': """
        List of indices to run. The default is to execute all indices for
        each step to be run.
        """
    }

    cfg['msgevent'] = {
        'switch': "-msgevent <str>",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Message event',
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
        'require': None,
        'defvalue': [],
        'shorthelp': 'Message contact',
        'example': ["cli: -msgcontact 'wile.e.coyote@acme.com'",
                    "api: chip.set('msgcontact','wile.e.coyote@acme.com')"],
        'help': """
        A list of phone numbers or email addresses to message on a event event
        within the msg_event param.
        """
    }

    cfg['optmode'] = {
        'switch': '-O<str>',
        'type': 'str',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'O0',
        'shorthelp': 'Optimization mode',
        'example': ["cli: -O3",
                    "api: chip.set('optmode','3')"],
        'help': """
        The compiler has modes to prioritize run time and ppa. Modes include:

        (0) = Exploration mode for debugging setup
        (1) = Higher effort and better PPA than O0
        (2) = Higher effort and better PPA than O1
        (3) = Signoff quality. Better PPA and higher run times than O2
        (4) = Experimental highest effort, may be unstable.
        """
    }

    cfg['vercheck'] = {
        'switch': "-vercheck <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Enforce version checking',
        'example': ["cli: -vercheck",
                    "api: chip.set('vercheck', 'true')"],
        'help': """
        Enforces strict version checking on all invoked tools if True. The
        list of supported version numbers is defined in the 'version'
        parameter in the 'eda' dictionary for each tool.
        """
    }

    cfg['relax'] = {
        'switch': "-relax <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Relax RTL linting',
        'example': ["cli: -relax",
                    "api: chip.set('relax', 'true')"],
        'help': """
        Specifies that tools should be lenient and suppress some warnings that
        may or may not indicate design issues. The default is to enforce strict
        checks for all steps.
        """
    }

    cfg['track'] = {
        'switch': "-track <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Enable execution tracking',
        'example': ["cli: -track",
                    "api: chip.set('track', 'true')"],
        'help': """
        Turns on tracking of all 'record' parameters during each task. Tracking
        will result in potentially sensitive data being recorded in the manifest
        so only turn on this feature if you have control of the final manifest.
        """
    }

    cfg['trace'] = {
        'switch': "-trace <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': 'Enable simulation trace output',
        'example': ["cli: -trace",
                    "api: chip.set('trace', True)"],
        'help': """
        Enables tracing during compilation and/or runtime.
        """
    }

    cfg['bkpt'] = {
        'switch': "-bkpt <str>",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': "List of flow breakpoints",
        'example': ["cli: -bkpt place",
                    "api: chip.set('bkpt','place')"],
        'help': """
        Specifies a list of step stop (break) points. If the step is
        a TCL based tool, then the breakpoints stops the flow inside the EDA
        tool. If the step is a command line tool, then the flow drops into
        a Python interpreter.
        """
    }

    cfg['checkonly'] = {
        'switch': "-checkonly <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': "false",
        'shorthelp': "Exit after checking flow",
        'example': ["cli: -checkonly true",
                    "api: chip.set('checkonly','true')"],
        'help': """
        Checks the legality of the configuration but doesn't run the flow.
        """
    }

    cfg['copyall'] = {
        'switch': "-copyall <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': "Copy all inputs to working directory",
        'example': ["cli: -copyall",
                    "api: chip.set('copyall', 'true')"],
        'help': """
        Specifies that all used files should be copied into the jobdir,
        overriding the per schema entry copy settings. The default
        is false.
        """
    }

    cfg['show'] = {
        'switch': "-show <bool>",
        'type': 'bool',
        'lock': 'false',
        'require': 'all',
        'defvalue': 'false',
        'shorthelp': "Show layout",
        'example': ["cli: -show",
                    "api: chip.set('show', 'true')"],
        'help': """
        Specifies that the final hardware layout should be
        shown after the compilation has been completed. The
        final layout and tool used to display the layout is
        flow dependent.
        """
    }

    # Linking show tools with filetypes
    filetype = 'default'
    cfg['showtool'] = {}
    cfg['showtool'][filetype] = {
        'switch': "-showtool 'filetype <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Selects tool for file display',
        'example': ["cli: -showtool 'gds klayout'",
                    "api: chip.set('showtool', 'gds', 'klayout')"],
        'help': """
        Selects the tool to use by the show function for displaying the
        specified filetype.
        """
    }

    return cfg

############################################
# Package information
############################################

def schema_package(cfg, group):

    localcfg = {}

    if group == 'package':
        lib = ""
        libapi= ""
    elif group == 'library':
        lib = 'lib '
        libapi = "'lib','package',"
    elif group == 'record':
        lib = 'job step index '
        libapi = "'job0','import','0','package',"

    localcfg['name'] = {
        'switch': f"-{group}_name '{lib}<str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} name",
        'example': [
            f"cli: -{group}_name {lib}yac",
            f"api: chip.set('{group}',{libapi}'name', 'yac')"],
        'help': f"""
        Name of {group}.
        """
    }

    localcfg['version'] = {
        'switch': f"-{group}_version '{lib}<str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} version number",
        'example': [
            f"cli: -{group}_version '{lib}1.0'",
            f"api: chip.set({group},{libapi}'version', '1.0')"],
        'help': f"""
        Version number. Can be a branch, tag, commit hash, or a major.minor
        type version string. Versions shall fllow the semver standard.
        """
    }

    localcfg['description'] = {
        'switch': f"-{group}_description '{lib}<str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} short description",
        'example': [
            f"cli: -{group}_description '{lib}Yet another cpu'",
            f"api: chip.set('{group}',{libapi}'description', 'Yet another cpu')"],
        'help': """
        Short one line description for package managers and summary reports.
        """
    }

    localcfg['keyword'] = {
        'switch': f"-{group}_keyword '{lib}<str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} keywords",
        'example': [
            f"cli: -{group}_keyword yac",
            f"api: chip.set('{group}','{libapi}'keyword', 'yac')"],
        'help': f"""
        List of keyword(s) used to search for {group}.
        """
    }

    localcfg['homepage'] = {
        'switch': f"-{group}_homepage '{lib}<str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} homepage",
        'example': [
            f"cli: -{group}_homepage yac",
            f"api: chip.set('{group}','{libapi}'homepage', 'yac')"],
        'help': f"""
        Homepage for {group}.
        """
    }

    doctypes = ['datasheet',
                'reference',
                'userguide',
                'releasenotes',
                'testplan',
                'tutorial']
    localcfg['doc'] = {}
    for item in doctypes:
        localcfg['doc'][item] = {
            'switch': f"-{group}_doc_{item} '{lib}<file>'",
            'type': '[file]',
            'lock': 'false',
            'copy': 'true',
            'require': None,
            'defvalue': [],
            'filehash': [],
            'hashalgo': 'sha256',
            'date': [],
            'author': [],
            'signature': [],
            'shorthelp': f"{group.capitalize()} {item}",
            'example': [
                f"cli: -{group}_doc_{item} '{lib}design.pdf",
                f"api: chip.set('{group}',{libapi}'doc',{item},'design.pdf')"],
            'help': f"""
            List of {item} documents.
            """
        }

    localcfg['signoff'] = {
        'switch': f"-{group}_signoff '{lib}<file>'",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': f"{group.capitalize()} signoff documents",
        'example': [
            f"cli: -{group}_signoff '{lib}hello_review.md",
            f"api: chip.set('{group}',{libapi}'signoff','hello_review.md')"],
        'help': """
        Final signoff report(s).
        """
    }

    localcfg['checklist'] = {}
    localcfg['checklist']['default'] = {
        'switch': f"-{group}_checklist '{lib}name <bool>'",
        'type': 'bool',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} signoff checklist",
        'example': [
            f"cli: -{group}_checklist '{lib}LINT_PASS True",
            f"api: chip.set('{group}',{libapi}'checklist',LINT_PASS,True)"],
        'help': """
        Final signoff checklist specified as a key value pair. Values are
        True/False booleans.
        """
    }

    localcfg['repo'] = {
        'switch': f"-{group}_repo '{lib}<str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': f"{group.capitalize()} repository",
        'example': [
            f"cli: -{group}_repo git@github.com:aolofsson/oh.git",
            f"api: chip.set('{group}',{libapi}'repo','git@github.com:aolofsson/oh.git')"],
        'help': f"""
        Optional address to the {group} repository.
        """
    }

    dep = 'default'
    localcfg['dependency'] = {}
    localcfg['dependency'][dep] = {
        'switch': f"-{group}_dependency '{lib}<dep> <version>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': f"{group.capitalize()} dependency version",
        'example': [
            f"cli: -{group}_dependency '{lib}hello 1.0.0'",
            f"api: chip.set('{group}',{libapi}'dependency','hello','1.0.0')"],
        'help': """
        Package dependency specifed as a key value pair. Versions shall follow
        the semver standard.
        """
    }

    localcfg['target'] = {
        'switch': f"-{group}_target '{lib}<str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} target list",
        'example': [
            f"cli: -{group}_target '{lib}asicflow_freepdk45",
            f"api: chip.set('{group}',{libapi}'target', 'asicflow_freepdk45')"],
        'help': f"""
        List of tested and qualified targets for the package.
        """
    }

    localcfg['license'] = {
        'switch': f"-{group}_license '{lib}<file>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} license name",
        'example': [
            f"cli: -{group}_license '{lib}./LICENSE",
            f"api: chip.set('{group}',{libapi}'license', './LICENSE')"],
        'help': f"""
        The license for {group}. SPDX identifiers should be used when
        applicable.
        """
    }

    localcfg['location'] = {
        'switch': f"-{group}_location '{lib}<str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': f"{group.capitalize()} location",
        'example': [
            f"cli: -{group}_location mars",
            f"api: chip.set('{group}', {libapi}'location', 'mars')"],
        'help': """
        Location of origin for project.
        """
    }

    localcfg['organization'] = {
        'switch': f"-{group}_organization '{lib}<str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': f"{group} organization",
        'example': [
            f"cli: -{group}_organization '{lib}humanity'",
            f"api: chip.set('{group}',{libapi}'organization', 'humanity')"],
        'help': """
        Projection organization name.
        """
    }

    localcfg['author'] = {
        'switch': f"-{group}_author '{lib}<str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': f"{group.capitalize()} author",
        'example': [
            f"cli: -{group}_author '{lib}wiley",
            f"api: chip.set('{group}',{libapi}'author', 'wiley')"],
        'help': """
        Author name(s).
        """
    }

    localcfg['userid'] = {
        'switch': f"-{group}_userid '{lib}<str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': f"{group.capitalize()} author user ID",
        'example': [
            f"cli: -{group}_userid '{lib}0123",
            f"api: chip.set('{group}',{libapi}'userid', '0123')"],
        'help': """
        List of anonymized authoer user ID(s).
        """
    }

    localcfg['publickey'] = {
        'switch': f"-{group}_publickey '{lib}<str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': f"{group.capitalize()} public key",
        'example': [
            f"cli: -{group}_publickey '{lib}6EB695706EB69570'",
            f"api: chip.set('{group}',{libapi}'publickey','6EB695706EB69570')"],
        'help': f"""
        Public key for {group}.
        """
    }

    # copy package dictionary into library/project
    if group == 'package':
        cfg['package'] = copy.deepcopy(localcfg)
    elif group == 'record':
        cfg['record']['default']['default']['default']['package'] = copy.deepcopy(localcfg)
    elif group == 'library':
        cfg['library']['default']['package'] = copy.deepcopy(localcfg)
    return cfg

############################################
# Design Setup
############################################

def schema_design(cfg):
    ''' Design Sources
    '''

    cfg['design'] = {
        'switch': "-design <str>",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Design top module name',
        'example': ["cli: -design hello_world",
                    "api: chip.set('design', 'hello_world')"],
        'help': """
        Name of the top level module to compile. Required for all designs with
        more than one module.
        """
    }

    cfg['source'] = {
        'switch': None,
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Primary source files',
        'example': ["cli: hello_world.v",
                    "api: chip.set('source', 'hello_world.v')"],
        'help': """
        A list of source files to read in for elaboration. The files are read
        in order from first to last entered. File type is inferred from the
        file suffix.
        (\\*.v, \\*.vh) = Verilog
        (\\*.vhd)       = VHDL
        (\\*.sv)        = SystemVerilog
        (\\*.c)         = C
        (\\*.cpp, .cc)  = C++
        (\\*.py)        = Python
        """
    }

    cfg['netlist'] = {
        'switch': '-netlist <file>',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Technology mapped verilog netlist',
        'example': ["cli: netlist.v",
                    "api: chip.add('netlist', 'netlist.v')"],
        'help': """
        List of technology mapped Verilog modules for post-synthesis
        implementation steps. The actual entry point of the netlist
        depends on the flow used. In the standard 'asicflow', the
        netlist is read in as part of the floorplan step.
        """
    }

    cfg['testbench'] = {
        'switch': '-testbench <file>',
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Testbench files',
        'example': ["cli: -testbench tb_top.v",
                    "api: chip.set('testbench', 'tb_top.v')"],
        'help': """
        A list of testbench sources. The files are read in order from first to
        last entered. File type is inferred from the file suffix:
        (\\*.v, \\*.vh) = Verilog
        (\\*.vhd)      = VHDL
        (\\*.sv)       = SystemVerilog
        (\\*.c)        = C
        (\\*.cpp, .cc) = C++
        (\\*.py)       = Python
        """
    }


    cfg['clock'] = {}
    cfg['clock']['default'] = {}
    cfg['clock']['default']['pin'] = {
        'switch': "-clock_pin 'clkname <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Clock driver pin',
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
        'require': None,
        'defvalue': None,
        'shorthelp': 'Clock period',
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
        'require': None,
        'defvalue': None,
        'shorthelp': 'Clock jitter',
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
        'require': None,
        'defvalue': None,
        'shorthelp': 'Supply pin mapping',
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
        'require': None,
        'defvalue': None,
        'shorthelp': 'Supply level',
        'example': ["cli: -supply_level 'vdd 1.0'",
                    "api: chip.set('supply','vdd','level','1.0')"],
        'help': """
        Voltage level for the name supply, specified in Volts.
        """
    }

    cfg['supply']['default']['noise'] = {
        'switch': "-supply_noise 'supplyname <float>'",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Supply noise',
        'example': ["cli: -supply_noise 'vdd 0.05'",
                    "api: chip.set('supply','vdd','noise','0.05')"],
        'help': """
        Noise level for the name supply, specified in Volts.
        """
    }

    cfg['param'] = {}
    cfg['param']['default'] = {
        'switch': "-param 'name <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Design parameter',
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
        'require': None,
        'defvalue': [],
        'shorthelp': 'Design preprocessor symbol',
        'example': ["cli: -DCFG_ASIC=1",
                    "api: chip.set('define','CFG_ASIC=1')"],
        'help': """
        Preprocessor symbol for verilog source imports.
        """
    }

    cfg['ydir'] = {
        'switch': "-y <dir>",
        'type': '[dir]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Design module search path',
        'example': ["cli: -y './mylib'",
                    "api: chip.set('ydir','./mylib')"],
        'help': """
        Search paths to look for modules found in the the source list.
        The import engine will look for modules inside files with the
        specified +libext+ param suffix
        """
    }

    cfg['idir'] = {
        'switch': "+incdir+<dir>",
        'type': '[dir]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Include search paths',
        'example': ["cli: '+incdir+./mylib'",
                    "api: chip.set('idir','./mylib')"],
        'help': """
        Search paths to look for files included in the design using
        the ```include`` statement.
        """
    }

    cfg['vlib'] = {
        'switch': "-v <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Verilog library',
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
        'require': None,
        'defvalue': [],
        'shorthelp': 'Verilog file extensions',
        'example': ["cli: +libext+sv",
                    "api: chip.set('libext','sv')"],
        'help': """
        Specifies the file extensions that should be used for finding modules.
        For example, if -y is specified as ./lib", and '.v' is specified as
        libext then the files ./lib/\\*.v ", will be searched for module matches.
        """
    }

    cfg['cmdfile'] = {
        'switch': "-f <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Verilog compilation command file',
        'example': ["cli: -f design.f",
                    "api: chip.set('cmdfile','design.f')"],
        'help': """
        Read the specified file, and act as if all text inside it was specified
        as command line parameters. Supported by most verilog simulators
        including Icarus and Verilator. The format of the file is not strongly
        standardized. Support for comments and environment variables within
        the file varies and depends on the tool used. SC simply passes on
        the filepath toe the tool executable.
        """
    }

    cfg['constraint'] = {
        'switch': "-constraint <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'Design constraints files',
        'example': ["cli: -constraint top.sdc",
                    "api: chip.set('constraint','top.sdc')"],
        'help': """
        List of default constraints for the design to use during compilation.
        Types of constraints include timing (SDC) and pin mappings files (PCF)
        for FPGAs. More than one file can be supplied. Timing constraints are
        global and sourced in all MCMM scenarios.
        """
    }

    cfg['vcd'] = {
        'switch': "-vcd <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'VCD file',
        'example': ["cli: -vcd mytrace.vcd",
                    "api: chip.set('vcd','mytrace.vcd')"],
        'help': """
        Simulation trace that can be used to model the peak and
        average power consumption of a design.
        """
    }

    cfg['saif'] = {
        'switch': "-saif <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'SAIF file',
        'example': ["cli: -saif mytrace.saif",
                    "api: chip.set('saif','mytrace.saif')"],
        'help': """
        Simulation trace with static probability and toggle rates for nets
        in the design. The file can be used for coarse power modeling during
        compilation.
        """
    }

    cfg['activityfactor'] = {
        'switch': "-activityfactor <float>",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Global toggle activity factor',
        'example': ["cli: -activityfactor 0.1",
                    "api: chip.set('activityfactor,'0.1')"],
        'help': """
        Sets a global activity factor for all nodes in the design. Note
        accurate, but better than nothing. The 'activityfactor' parameter can
        be used in cases when a VCD file or SAIF file is unavailable. Typical
        activity factors: clock(1), max_data(0.5), random_data(0.25),
        typical_rate(0.1).
        """
    }

    cfg['spef'] = {
        'switch': "-spef <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'SPEF file',
        'example': ["cli: -spef mydesign.spef",
                    "api: chip.set('spef','mydesign.spef')"],
        'help': """
        File containing parasitics specified in the Standard Parasitic Exchange
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
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'SDF file',
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
        'require': None,
        'defvalue': [],
        'shorthelp': 'List of cells to exclude',
        'example': ["cli: -exclude sram_macro",
                    "api: chip.set('exclude','sram_macro')"],
        'help': """
        List of physical cells to exclude during execution. The process
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
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC metal stackup',
        'example': ["cli: -asic_stackup 2MA4MB2MC",
                    "api: chip.set('asic','stackup','2MA4MB2MC')"],
        'help': """
        Target stackup to use in the design. The stackup is required
        parameter for PDKs with multiple metal stackups.
        """
    }

    cfg['asic']['targetlib'] = {
        'switch': "-asic_targetlib <str>",
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'require': None,
        'shorthelp': 'ASIC target libraries',
        'example': ["cli: -asic_targetlib asap7sc7p5t_lvt",
                    "api: chip.set('asic', 'targetlib', 'asap7sc7p5t_lvt')"],
        'help': """
        List of library names to use for synthesis and automated place and
        route. Names must match up exactly with the library name handle in the
        'stdcells' dictionary.
        """
    }

    cfg['asic']['macrolib'] = {
        'switch': "-asic_macrolib <str>",
        'type': '[str]',
        'lock': 'false',
        'defvalue': [],
        'require': None,
        'shorthelp': 'ASIC macro libraries',
        'example': ["cli: -asic_macrolib sram64x1024",
                    "api: chip.set('asic', 'macrolib', 'sram64x1024')"],
        'help': """
        List of macro libraries to be linked in during synthesis and place
        and route. Macro libraries are used for resolving instances but are
        not used as target for automated synthesis.
        """
    }

    cfg['asic']['delaymodel'] = {
        'switch': "-asic_delaymodel <str>",
        'type': 'str',
        'lock': 'false',
        'defvalue': None,
        'require': None,
        'shorthelp': 'ASIC library delay model',
        'example': ["cli: -asic_delaymodel ccs",
                    "api: chip.set('asic', 'delaymodel', 'ccs')"],
        'help': """
        Delay model to use for the target libs. Supported values
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
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'ASIC non-default routing rule',
        'example': ["cli: -asic_ndr_width 'clk (0.2,0.2)",
                    "api: chip.set('asic','ndr','clk', (0.2,0.2))"],
        'help': """
        Definitions of non-default routing rule specified on a per net
        basis. Constraints are entered as a tuples specified in microns.
        """
    }

    cfg['asic']['minlayer'] = {
        'switch': "-asic_minlayer <str>",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'ASIC minimum routing layer',
        'example': ["cli: -asic_minlayer m2",
                    "api: chip.set('asic', 'minlayer', 'm2')"],
        'help': """
        Minimum SC metal layer name to be used for automated place and route .
        Alternatively the layer can be a string that matches a layer hard coded
        in the pdk_aprtech file. Designers wishing to use the same setup across
        multiple process nodes should use the integer approach. For processes
        with ambiguous starting routing layers, exact strings should be used.
        """
    }

    cfg['asic']['maxlayer'] = {
        'switch': "-asic_maxlayer <str>",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC maximum routing layer',
        'example': ["cli: -asic_maxlayer m6",
                    "api: chip.set('asic', 'maxlayer', 'm6')"],
        'help': """
        Maximum SC metal layer name to be used for automated place and route .
        Alternatively the layer can be a string that matches a layer hard coded
        in the pdk_aprtech file. Designers wishing to use the same setup across
        multiple process nodes should use the integer approach. For processes
        with ambiguous starting routing layers, exact strings should be used.
        """
    }

    cfg['asic']['maxfanout'] = {
        'switch': "-asic_maxfanout <int>",
        'type': 'int',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC maximum fanout',
        'example': ["cli: -asic_maxfanout 64",
                    "api: chip.set('asic', 'maxfanout', '64')"],
        'help': """
        Maximum driver fanout allowed during automated place and route.
        The parameter directs the APR tool to break up any net with fanout
        larger than maxfanout into sub nets and buffer.
        """
    }

    cfg['asic']['maxlength'] = {
        'switch': "-asic_maxlength <float>",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC maximum wire length',
        'example': ["cli: -asic_maxlength 1000",
                    "api: chip.set('asic', 'maxlength', '1000')"],
        'help': """
        Maximum total wire length allowed in design during APR. Any
        net that is longer than maxlength is broken up into segments by
        the tool.
        """
    }

    cfg['asic']['maxcap'] = {
        'switch': "-asic_maxcap <float>",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC maximum net capacitance',
        'example': ["cli: -asic_maxcap '0.25e-12'",
                    "api: chip.set('asic', 'maxcap', '0.25e-12')"],
        'help': """
        Maximum allowed capacitance per net. The number is specified
        in Farads.
        """
    }

    cfg['asic']['maxslew'] = {
        'switch': "-asic_maxslew <float>",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC maximum slew',
        'example': ["cli: -asic_maxslew '01e-9'",
                    "api: chip.set('asic', 'maxslew', '1e-9')"],
        'help': """
        Maximum allowed capacitance per net. The number is specified
        in seconds.
        """
    }

    cfg['asic']['rclayer'] = {}
    cfg['asic']['rclayer']['default'] = {
        'switch': "-asic_rclayer 'name <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC extraction estimation layer',
        'example': ["cli: -asic_rclayer 'clk m3",
                    "api: chip.set('asic', 'rclayer', 'clk', 'm3')"],
        'help': """
        Technology agnostic metal layer to be used for parasitic
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
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC vertical pin layer',
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
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC horizontal pin layer',
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
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC target core density',
        'example': ["cli: -asic_density 30",
                    "api: chip.set('asic', 'density', '30')"],
        'help': """"
        Target density based on the total design cell area reported
        after synthesis. This number is used when no diearea or floorplan is
        supplied. Any number between 1 and 100 is legal, but values above 50
        may fail due to area/congestion issues during apr.
        """
    }

    cfg['asic']['coremargin'] = {
        'switch': "-asic_coremargin <float>",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC block core margin',
        'example': ["cli: -asic_coremargin 1",
                    "api: chip.set('asic', 'coremargin', '1')"],
        'help': """
        Halo/margin between the core area to use for automated floorplanning
        and the outer core boundary specified in microns.  The value is used
        when no diearea or floorplan is supplied.
        """
    }

    cfg['asic']['aspectratio'] = {
        'switch': "-asic_aspectratio <float>",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'ASIC block aspect ratio',
        'example': ["cli: -asic_aspectratio 2.0",
                    "api: chip.set('asic', 'aspectratio', '2.0')"],
        'help': """
        Height to width ratio of the block for automated floor-planning.
        Values below 0.1 and above 10 should be avoided as they will likely fail
        to converge during placement and routing. The ideal aspect ratio for
        most designs is 1. This value is only used when no diearea or floorplan
        is supplied.
        """
        }

    # For spec driven floorplanning
    cfg['asic']['diearea'] = {
        'switch': "-asic_diearea '<[(float,float)]'>",
        'type': '[(float,float)]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'ASIC die area outline',
        'example': ["cli: -asic_diearea '(0,0)'",
                    "api: chip.set('asic', 'diearea', (0,0))"],
        'help': """
        List of (x,y) points that define the outline of the die area for the
        physical design. Simple rectangle areas can be defined with two points,
        one for the lower left corner and one for the upper right corner. All
        values are specified in microns.
        """
    }

    cfg['asic']['corearea'] = {
        'switch': "-asic_corearea '<[(float,float)]'>",
        'type': '[(float,float)]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'ASIC core area outline',
        'example': ["cli: -asic_corearea '(0,0)'",
                    "api: chip.set('asic', 'corearea', (0,0))"],
        'help': """
        List of (x,y) points that define the outline of the core area for the
        physical design. Simple rectangle areas can be defined with two points,
        one for the lower left corner and one for the upper right corner. All
        values are specified in microns.
        """
    }

    # DEF file
    cfg['asic']['def'] = {
        'switch': "-asic_def <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'ASIC DEF file',
        'example': ["cli: -asic_def 'hello.def'",
                    "api: chip.set('asic', 'def', 'hello.def')"],
        'help': """
        Design Exchange Format (DEF) file read in during the floorplanning step.
        The file is a standardized ASIC text representation of the physical
        layout of an integrated circuit in an ASCII format. Any references
        within the DEF to pins, nets, and components must match the verilog
        netlist read in during the floorplan step.
        """
    }

    # GDS file
    cfg['asic']['gds'] = {
        'switch': "-asic_gds <file>",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'defvalue': [],
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'shorthelp': 'ASIC GDS file',
        'example': ["cli: -asic_gds 'guardring.gds'",
                    "api: chip.set('asic', 'gds', 'guardring.gds')"],
        'help': """
        List of hardcoded GDSII files to be merged during the final
        compilation gds export step.
        """
    }

    return cfg

############################################
# MCMM Constraints
############################################

def schema_mcmm(cfg, scenario='default'):

    cfg['mcmm'] = {}
    cfg['mcmm'][scenario] = {}


    cfg['mcmm'][scenario]['voltage'] = {
        'switch': "-mcmm_voltage 'scenario <float>'",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Scenario voltage level',
        'example': ["cli: -mcmm_voltage 'worst 0.9'",
                    "api: chip.set('mcmm', 'worst','voltage', '0.9')"],
        'help': """
        Operating voltage applied to the scenario, specified in Volts.
        """
    }

    cfg['mcmm'][scenario]['temperature'] = {
        'switch': "-mcmm_temperature 'scenario <float>'",
        'type': 'float',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Scenario temperature',
        'example': ["cli: -mcmm_temperature 'worst 125'",
                    "api: chip.set('mcmm', 'worst', 'temperature','125')"],
        'help': """
        Chip temperature applied to the scenario specified in degrees Celsius.
        """
    }
    cfg['mcmm'][scenario]['libcorner'] = {
        'switch': "-mcmm_libcorner 'scenario <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Scenario library corner',
        'example': ["cli: -mcmm_libcorner 'worst ttt'",
                    "api: chip.set('mcmm', 'worst', 'libcorner', 'ttt')"],
        'help': """
        Library corner applied to the scenario to scale library timing
        models based on the libcorner value for models that support it.
        The parameter is ignored for libraries that have one hard coded
        model per libcorner.
        """
    }

    cfg['mcmm'][scenario]['pexcorner'] = {
        'switch': "-mcmm_pexcorner 'scenario <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Scenario PEX corner',
        'example': ["cli: -mcmm_pexcorner 'worst max'",
                    "api: chip.set('mcmm','worst','pexcorner','max')"],
        'help': """
        Parasitic corner applied to the scenario. The 'pexcorner' string
        must match a corner found in the pdk pexmodel setup parameter.
        """
    }


    cfg['mcmm'][scenario]['opcond'] = {
        'switch': "-mcmm_opcond 'scenario <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Scenario operating condition',
        'example': ["cli: -mcmm_opcond 'worst typical_1.0'",
                    "api: chip.set('mcmm', 'worst', 'opcond',  'typical_1.0')"],
        'help': """
        Operating condition applied to the scenario. The value can be used
        to access specific conditions within the library timing models of the
        'target_libs'.
        """
    }

    cfg['mcmm'][scenario]['mode'] = {
        'switch': "-mcmm_mode 'scenario <str>'",
        'type': 'str',
        'lock': 'false',
        'require': None,
        'defvalue': None,
        'shorthelp': 'Scenario operating mode',
        'example': ["cli: -mcmm_mode 'worst test'",
                    "api: chip.set('mcmm',  'worst','mode', 'test')"],
        'help': """
        Operating mode for the scenario. Operating mode strings
        can be values such as test, functional, standby.
        """
    }
    cfg['mcmm'][scenario]['constraint'] = {
        'switch': "-mcmm_constraint 'scenario <file>'",
        'type': '[file]',
        'lock': 'false',
        'copy': 'true',
        'require': None,
        'filehash': [],
        'hashalgo': 'sha256',
        'date': [],
        'author': [],
        'signature': [],
        'defvalue': [],
        'shorthelp': 'Scenario constraints files',
        'example': ["cli: -mcmm_constraint 'worst hello.sdc'",
                    "api: chip.set('mcmm','worst','constraint',  'hello.sdc')"],
        'help': """
        List of timing constraint files to use for the scenario. The values
        are combined with any constraints specified by the design
        'constraint' parameter. If no constraints are found, a default
        constraint file is used based on the clock definitions.
        """
    }
    cfg['mcmm'][scenario]['check'] = {
        'switch': "-mcmm_check 'scenario <str>'",
        'type': '[str]',
        'lock': 'false',
        'require': None,
        'defvalue': [],
        'shorthelp': 'Scenario checks',
        'example': ["cli: -mcmm_check 'worst check setup'",
                    "api: chip.add('mcmm','worst','check','setup')"],
        'help': """
        List of checks for to perform for the scenario. The checks must
        align with the capabilities of the EDA tools and flow being used.
        Checks generally include objectives like meeting setup and hold goals
        and minimize power. Standard check names include setup, hold, power,
        noise, reliability.
        """
    }

    return cfg


##############################################################################
# Main routie
if __name__ == "__main__":
    cfg = schema_cfg()
    print(json.dumps(cfg, indent=4, sort_keys=True))
