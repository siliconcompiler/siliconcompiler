# Copyright 2022 Silicon Compiler Authors. All Rights Reserved.

import json
import re

# Default import must be relative, to facilitate tools with Python interfaces
# (such as KLayout) directly importing the schema package. However, the fallback
# allows running this script directly to generate defaults.json.
try:
    from .utils import trim
except ImportError:
    from siliconcompiler.schema.utils import trim

SCHEMA_VERSION = '0.44.2'

#############################################################################
# PARAM DEFINITION
#############################################################################


def scparam(cfg,
            keypath,
            sctype=None,
            require=False,
            defvalue=None,
            scope='job',
            copy=False,
            lock=False,
            hashalgo='sha256',
            signature=None,
            notes=None,
            unit=None,
            shorthelp=None,
            switch=None,
            example=None,
            schelp=None,
            enum=None,
            pernode='never'):

    # 1. descend keypath until done
    # 2. create key if missing
    # 3. populate leaf cell when keypath empty
    if keypath:
        key = keypath[0]
        keypath.pop(0)
        if key not in cfg.keys():
            cfg[key] = {}
        scparam(cfg[key],
                keypath,
                sctype=sctype,
                scope=scope,
                require=require,
                defvalue=defvalue,
                copy=copy,
                lock=lock,
                hashalgo=hashalgo,
                signature=signature,
                notes=notes,
                unit=unit,
                shorthelp=shorthelp,
                switch=switch,
                example=example,
                schelp=schelp,
                enum=enum,
                pernode=pernode)
    else:

        # removing leading spaces as if schelp were a docstring
        schelp = trim(schelp)

        # setting values based on types
        # note (bools are never lists)
        if re.match(r'bool', sctype):
            if defvalue is None:
                defvalue = False
        if re.match(r'\[', sctype) and signature is None:
            signature = []
        if re.match(r'\[', sctype) and defvalue is None:
            defvalue = []

        # mandatory for all
        cfg['type'] = sctype
        cfg['scope'] = scope
        cfg['require'] = require
        cfg['lock'] = lock
        if switch and not isinstance(switch, list):
            switch = [switch]
        cfg['switch'] = switch
        cfg['shorthelp'] = shorthelp
        cfg['example'] = example
        cfg['help'] = schelp
        cfg['notes'] = notes
        # never, optional, required
        cfg['pernode'] = pernode
        cfg['node'] = {}
        cfg['node']['default'] = {}
        cfg['node']['default']['default'] = {}
        cfg['node']['default']['default']['value'] = defvalue
        cfg['node']['default']['default']['signature'] = signature

        if enum is not None:
            cfg['enum'] = enum

        # unit for floats/ints
        if unit is not None:
            cfg['unit'] = unit

        # file only values
        if re.search(r'file', sctype):
            cfg['hashalgo'] = hashalgo
            cfg['copy'] = copy
            cfg['node']['default']['default']['date'] = []
            cfg['node']['default']['default']['author'] = []
            cfg['node']['default']['default']['filehash'] = []
            cfg['node']['default']['default']['package'] = []

        if re.search(r'dir', sctype):
            cfg['hashalgo'] = hashalgo
            cfg['copy'] = copy
            cfg['node']['default']['default']['filehash'] = []
            cfg['node']['default']['default']['package'] = []


#############################################################################
# CHIP CONFIGURATION
#############################################################################
def schema_cfg():
    '''Method for defining Chip configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    # SC version number (bump on every non trivial change)
    # Version number following semver standard.
    # Software version syncs with SC releases (from _metadata)

    # Basic schema setup
    cfg = {}

    # Place holder dictionaries updated by core methods()
    cfg['history'] = {}
    cfg['library'] = {}

    scparam(cfg, ['schemaversion'],
            sctype='str',
            scope='global',
            defvalue=SCHEMA_VERSION,
            require=True,
            shorthelp="Schema version number",
            lock=True,
            switch="-schemaversion <str>",
            example=["api: chip.get('schemaversion')"],
            schelp="""SiliconCompiler schema version number.""")

    # Design topmodule/entrypoint
    scparam(cfg, ['design'],
            sctype='str',
            scope='global',
            require=True,
            shorthelp="Design top module name",
            switch="-design <str>",
            example=["cli: -design hello_world",
                     "api: chip.set('design', 'hello_world')"],
            schelp="""Name of the top level module or library. Required for all
            chip objects.""")

    # input/output
    io = {'input': ['Input', True],
          'output': ['Output', False]}

    filetype = 'default'
    fileset = 'default'

    for item, val in io.items():
        scparam(cfg, [item, fileset, filetype],
                sctype='[file]',
                pernode='optional',
                copy=val[1],
                shorthelp=f"{val[0]}: files",
                switch=f"-{item} 'fileset filetype <file>'",
                example=[
                    f"cli: -{item} 'rtl verilog hello_world.v'",
                    f"api: chip.set('{item}', 'rtl', 'verilog', 'hello_world.v')"],
                schelp="""
                List of files of type ('filetype') grouped as a named set ('fileset').
                The exact names of filetypes and filesets must match the string names
                used by the tasks called during flowgraph execution. By convention,
                the fileset names should match the the name of the flowgraph being
                executed.""")

    # Constraints
    cfg = schema_constraint(cfg)

    # Options
    cfg = schema_option(cfg)
    cfg = schema_arg(cfg)

    # Technology configuration
    cfg = schema_fpga(cfg)
    cfg = schema_asic(cfg)
    cfg = schema_pdk(cfg)

    # Tool flows
    cfg = schema_tool(cfg)
    cfg = schema_task(cfg)
    cfg = schema_flowgraph(cfg)

    # Metrics
    cfg = schema_checklist(cfg)
    cfg = schema_metric(cfg)
    cfg = schema_record(cfg)

    # Datasheet
    cfg = schema_datasheet(cfg)

    # Packaging
    cfg = schema_package(cfg)

    return cfg


###############################################################################
# FPGA
###############################################################################
def schema_fpga(cfg):
    ''' FPGA configuration
    '''

    partname = 'default'
    key = 'default'

    scparam(cfg, ['fpga', 'partname'],
            sctype='str',
            shorthelp="FPGA: part name",
            switch="-fpga_partname <str>",
            example=["cli: -fpga_partname fpga64k",
                     "api: chip.set('fpga', 'partname', 'fpga64k')"],
            schelp="""
            Complete part name used as a device target by the FPGA compilation
            tool. The part name must be an exact string match to the partname
            hard coded within the FPGA EDA tool.""")

    scparam(cfg, ['fpga', partname, 'vendor'],
            sctype='str',
            shorthelp="FPGA: vendor name",
            switch="-fpga_vendor 'partname <str>'",
            example=["cli: -fpga_vendor 'fpga64k acme'",
                     "api: chip.set('fpga', 'fpga64k', 'vendor', 'acme')"],
            schelp="""
            Name of the FPGA vendor for the FPGA partname.""")

    scparam(cfg, ['fpga', partname, 'lutsize'],
            sctype='int',
            shorthelp="FPGA: lutsize",
            switch="-fpga_lutsize 'partname <int>'",
            example=["cli: -fpga_lutsize 'fpga64k 4'",
                     "api: chip.set('fpga', 'fpga64k', 'lutsize', '4')"],
            schelp="""
            Specify the number of inputs in each lookup table (LUT) for the
            FPGA partname.  For architectures with fracturable LUTs, this is
            the number of inputs of the unfractured LUT.""")

    scparam(cfg, ['fpga', partname, 'file', key],
            sctype='[file]',
            scope='global',
            shorthelp="FPGA: file",
            switch="-fpga_file 'partname key <file>'",
            example=["cli: -fpga_file 'fpga64k file archfile my_arch.xml'",
                     "api: chip.set('fpga', 'fpga64k', 'file', 'archfile', 'my_arch.xml')"],
            schelp="""
            Specify a file for the FPGA partname.""")

    scparam(cfg, ['fpga', partname, 'var', key],
            sctype='[str]',
            shorthelp="FPGA: var",
            switch="-fpga_var 'partname key <str>'",
            example=["cli: -fpga_var 'fpga64k channelwidth 100'",
                     "api: chip.set('fpga', 'fpga64k', 'var', 'channelwidth', '100')"],
            schelp="""
            Specify a variable value for the FPGA partname.""")

    return cfg


###############################################################################
# PDK
###############################################################################
def schema_pdk(cfg, stackup='default'):
    ''' Process design kit configuration
    '''

    tool = 'default'
    filetype = 'default'
    pdkname = 'default'

    scparam(cfg, ['pdk', pdkname, 'foundry'],
            sctype='str',
            scope='global',
            shorthelp="PDK: foundry name",
            switch="-pdk_foundry 'pdkname <str>'",
            example=["cli: -pdk_foundry 'asap7 virtual'",
                     "api: chip.set('pdk', 'asap7', 'foundry', 'virtual')"],
            schelp="""
            Name of foundry corporation. Examples include intel, gf, tsmc,
            samsung, skywater, virtual. The \'virtual\' keyword is reserved for
            simulated non-manufacturable processes.""")

    scparam(cfg, ['pdk', pdkname, 'node'],
            sctype='float',
            scope='global',
            shorthelp="PDK: process node",
            switch="-pdk_node 'pdkname <float>'",
            example=["cli: -pdk_node 'asap7 130'",
                     "api: chip.set('pdk', 'asap7', 'node', 130)"],
            schelp="""
            Approximate relative minimum dimension of the process target specified
            in nanometers. The parameter is required for flows and tools that
            leverage the value to drive technology dependent synthesis and APR
            optimization. Node examples include 180, 130, 90, 65, 45, 32, 22 14,
            10, 7, 5, 3.""")

    scparam(cfg, ['pdk', pdkname, 'version'],
            sctype='str',
            scope='global',
            shorthelp="PDK: version",
            switch="-pdk_version 'pdkname <str>'",
            example=["cli: -pdk_version 'asap7 1.0'",
                     "api: chip.set('pdk', 'asap7', 'version', '1.0')"],
            schelp="""
            Alphanumeric string specifying the version of the PDK. Verification of
            correct PDK and IP versions is a hard ASIC tapeout require in all
            commercial foundries. The version number can be used for design manifest
            tracking and tapeout checklists.""")

    scparam(cfg, ['pdk', pdkname, 'stackup'],
            sctype='[str]',
            scope='global',
            shorthelp="PDK: metal stackups",
            switch="-pdk_stackup 'pdkname <str>'",
            example=["cli: -pdk_stackup 'asap7 2MA4MB2MC'",
                     "api: chip.add('pdk', 'asap7', 'stackup', '2MA4MB2MC')"],
            schelp="""
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
            parameters.""")

    scparam(cfg, ['pdk', pdkname, 'minlayer', stackup],
            sctype='str',
            scope='global',
            shorthelp="PDK: minimum routing layer",
            switch="-pdk_minlayer 'pdk stackup <str>'",
            example=[
                "cli: -pdk_minlayer 'asap7 2MA4MB2MC M2'",
                "api: chip.set('pdk', 'asap7', 'minlayer', '2MA4MB2MC', 'M2')"],
            schelp="""
            Minimum metal layer to be used for automated place and route
            specified on a per stackup basis.""")

    scparam(cfg, ['pdk', pdkname, 'maxlayer', stackup],
            sctype='str',
            scope='global',
            shorthelp="PDK: maximum routing layer",
            switch="-pdk_maxlayer 'pdk stackup <str>'",
            example=[
                "cli: -pdk_maxlayer 'asap7 2MA4MB2MC M8'",
                "api: chip.set('pdk', 'asap7', 'maxlayer', 'MA4MB2MC', 'M8')"],
            schelp="""
            Maximum metal layer to be used for automated place and route
            specified on a per stackup basis.""")

    scparam(cfg, ['pdk', pdkname, 'wafersize'],
            sctype='float',
            scope='global',
            unit='mm',
            shorthelp="PDK: wafer size",
            switch="-pdk_wafersize 'pdkname <float>'",
            example=["cli: -pdk_wafersize 'asap7 300'",
                     "api: chip.set('pdk', 'asap7', 'wafersize', 300)"],
            schelp="""
            Wafer diameter used in wafer based manufacturing process.
            The standard diameter for leading edge manufacturing is 300mm. For
            older process technologies and specialty fabs, smaller diameters
            such as 200, 100, 125, 100 are common. The value is used to
            calculate dies per wafer and full factory chip costs.""")

    scparam(cfg, ['pdk', pdkname, 'panelsize'],
            sctype='[(float,float)]',
            scope='global',
            unit='mm',
            shorthelp="PDK: panel size",
            switch="-pdk_panelsize 'pdkname <(float,float)>'",
            example=[
                "cli: -pdk_panelsize 'asap7 (45.72,60.96)'",
                "api: chip.set('pdk', 'asap7', 'panelsize', (45.72, 60.96))"],
            schelp="""
            List of panel sizes supported in the manufacturing process.
            """)

    scparam(cfg, ['pdk', pdkname, 'unitcost'],
            sctype='float',
            scope='global',
            unit='USD',
            shorthelp="PDK: unit cost",
            switch="-pdk_unitcost 'pdkname <float>'",
            example=["cli: -pdk_unitcost 'asap7 10000'",
                     "api: chip.set('pdk', 'asap7', 'unitcost', 10000)"],
            schelp="""
            Raw cost per unit shipped by the factory, not accounting for yield
            loss.""")

    scparam(cfg, ['pdk', pdkname, 'd0'],
            sctype='float',
            scope='global',
            shorthelp="PDK: process defect density",
            switch="-pdk_d0 'pdkname <float>'",
            example=["cli: -pdk_d0 'asap7 0.1'",
                     "api: chip.set('pdk', 'asap7', 'd0', 0.1)"],
            schelp="""
            Process defect density (d0) expressed as random defects per cm^2. The
            value is used to calculate yield losses as a function of area, which in
            turn affects the chip full factory costs. Two yield models are
            supported: Poisson (default), and Murphy. The Poisson based yield is
            calculated as dy = exp(-area * d0/100). The Murphy based yield is
            calculated as dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.""")

    scparam(cfg, ['pdk', pdkname, 'scribe'],
            sctype='(float,float)',
            scope='global',
            unit='mm',
            shorthelp="PDK: horizontal scribe line width",
            switch="-pdk_scribe 'pdkname <(float,float)>'",
            example=["cli: -pdk_scribe 'asap7 (0.1,0.1)'",
                     "api: chip.set('pdk', 'asap7', 'scribe', (0.1, 0.1))"],
            schelp="""
            Width of the horizontal and vertical scribe line used during die separation.
            The process is generally completed using a mechanical saw, but can be
            done through combinations of mechanical saws, lasers, wafer thinning,
            and chemical etching in more advanced technologies. The value is used
            to calculate effective dies per wafer and full factory cost.""")

    scparam(cfg, ['pdk', pdkname, 'edgemargin'],
            sctype='float',
            scope='global',
            unit='mm',
            shorthelp="PDK: wafer edge keep-out margin",
            switch="-pdk_edgemargin 'pdkname <float>'",
            example=[
                "cli: -pdk_edgemargin 'asap7 1'",
                "api: chip.set('pdk', 'asap7', 'edgemargin', 1)"],
            schelp="""
            Keep-out distance/margin from the edge inwards. The edge
            is prone to chipping and need special treatment that preclude
            placement of designs in this area. The edge value is used to
            calculate effective units per wafer/panel and full factory cost.""")

    simtype = 'default'
    scparam(cfg, ['pdk', pdkname, 'devmodel', tool, simtype, stackup],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: device models",
            switch="-pdk_devmodel 'pdkname tool simtype stackup <file>'",
            example=[
            "cli: -pdk_devmodel 'asap7 xyce spice M10 asap7.sp'",
            "api: chip.set('pdk', 'asap7', 'devmodel', 'xyce', 'spice', 'M10', 'asap7.sp')"],
            schelp="""
            List of filepaths to PDK device models for different simulation
            purposes and for different tools. Examples of device model types
            include spice, aging, electromigration, radiation. An example of a
            'spice' tool is xyce. Device models are specified on a per metal stack
            basis. Process nodes with a single device model across all stacks will
            have a unique parameter record per metal stack pointing to the same
            device model file. Device types and tools are dynamic entries
            that depend on the tool setup and device technology. Pseudo-standardized
            device types include spice, em (electromigration), and aging.""")

    corner = 'default'
    scparam(cfg, ['pdk', pdkname, 'pexmodel', tool, stackup, corner],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: parasitic TCAD models",
            switch="-pdk_pexmodel 'pdkname tool stackup corner <file>'",
            example=[
                "cli: -pdk_pexmodel 'asap7 fastcap M10 max wire.mod'",
                "api: chip.set('pdk', 'asap7', 'pexmodel', 'fastcap', 'M10', 'max', 'wire.mod')"],
            schelp="""
            List of filepaths to PDK wire TCAD models used during automated
            synthesis, APR, and signoff verification. Pexmodels are specified on
            a per metal stack basis. Corner values depend on the process being
            used, but typically include nomenclature such as min, max, nominal.
            For exact names, refer to the DRM. Pexmodels are generally not
            standardized and specified on a per tool basis. An example of pexmodel
            type is 'fastcap'.""")

    src = 'default'
    dst = 'default'
    scparam(cfg, ['pdk', pdkname, 'layermap', tool, src, dst, stackup],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: layer map file",
            switch="-pdk_layermap 'pdkname tool src dst stackup <file>'",
            example=[
                "cli: -pdk_layermap 'asap7 klayout db gds M10 asap7.map'",
                "api: chip.set('pdk', 'asap7', 'layermap', 'klayout', 'db', 'gds', 'M10', "
                "'asap7.map')"],
            schelp="""
            Files describing input/output mapping for streaming layout data from
            one format to another. A foundry PDK will include an official layer
            list for all user entered and generated layers supported in the GDS
            accepted by the foundry for processing, but there is no standardized
            layer definition format that can be read and written by all EDA tools.
            To ensure mask layer matching, key/value type mapping files are needed
            to convert EDA databases to/from GDS and to convert between different
            types of EDA databases. Layer maps are specified on a per metal
            stackup basis. The 'src' and 'dst' can be names of SC supported tools
            or file formats (like 'gds').""")

    scparam(cfg, ['pdk', pdkname, 'display', tool, stackup],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: display file",
            switch="-pdk_display 'pdkname tool stackup <file>'",
            example=[
                "cli: -pdk_display 'asap7 klayout M10 display.lyt'",
                "api: chip.set('pdk', 'asap7', 'display', 'klayout', 'M10', 'display.cfg')"],
            schelp="""
            Display configuration files describing colors and pattern schemes for
            all layers in the PDK. The display configuration file is entered on a
            stackup and tool basis.""")

    # TODO: create firm list of accepted files
    libarch = 'default'
    scparam(cfg, ['pdk', pdkname, 'aprtech', tool, stackup, libarch, filetype],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: APR technology files",
            switch="-pdk_aprtech 'pdkname tool stackup libarch filetype <file>'",
            example=[
                "cli: -pdk_aprtech 'asap7 openroad M10 12t lef tech.lef'",
                "api: chip.set('pdk', 'asap7', 'aprtech', 'openroad', 'M10', '12t', 'lef', "
                "'tech.lef')"],
            schelp="""
            Technology file containing setup information needed to enable DRC clean APR
            for the specified stackup, libarch, and format. The 'libarch' specifies the
            library architecture (e.g. library height). For example a PDK with support
            for 9 and 12 track libraries might have 'libarchs' called 9t and 12t.
            The standard filetype for specifying place and route design rules for a
            process node is through a 'lef' format technology file. The
            'filetype' used in the aprtech is used by the tool specific APR TCL scripts
            to set up the technology parameters. Some tools may require additional
            files beyond the tech.lef file. Examples of extra file types include
            antenna, tracks, tapcell, viarules, em.""")

    checks = ['lvs', 'drc', 'erc', 'fill']
    name = 'default'
    for item in checks:
        scparam(cfg, ['pdk', pdkname, item, 'runset', tool, stackup, name],
                sctype='[file]',
                scope='global',
                shorthelp=f"PDK: {item.upper()} runset files",
                switch=f"-pdk_{item}_runset 'pdkname tool stackup name <file>'",
                example=[
                    f"cli: -pdk_{item}_runset 'asap7 magic M10 basic $PDK/{item}.rs'",
                    f"api: chip.set('pdk', 'asap7', '{item}', 'runset', 'magic', 'M10', 'basic', "
                    f"'$PDK/{item}.rs')"],
                schelp=f"""Runset files for {item.upper()} task.""")

        scparam(cfg, ['pdk', pdkname, item, 'waiver', tool, stackup, name],
                sctype='[file]',
                scope='global',
                shorthelp=f"PDK: {item.upper()} waiver files",
                switch=f"-pdk_{item}_waiver 'pdkname tool stackup name <file>'",
                example=[
                    f"cli: -pdk_{item}_waiver 'asap7 magic M10 basic $PDK/{item}.txt'",
                    f"api: chip.set('pdk', 'asap7', '{item}', 'waiver', 'magic', 'M10', 'basic', "
                    f"'$PDK/{item}.txt')"],
                schelp=f"""Waiver files for {item.upper()} task.""")

    ###############
    # EDA vars
    ###############

    key = 'default'
    scparam(cfg, ['pdk', pdkname, 'file', tool, key, stackup],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: special file",
            switch="-pdk_file 'pdkname tool key stackup <file>'",
            example=[
                "cli: -pdk_file 'asap7 xyce spice M10 asap7.sp'",
                "api: chip.set('pdk', 'asap7', 'file', 'xyce', 'spice', 'M10', 'asap7.sp')"],
            schelp="""
            List of named files specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly supported by the SiliconCompiler PDK schema.""")

    scparam(cfg, ['pdk', pdkname, 'dir', tool, key, stackup],
            sctype='[dir]',
            scope='global',
            shorthelp="PDK: special directory",
            switch="-pdk_dir 'pdkname tool key stackup <dir>'",
            example=[
                "cli: -pdk_dir 'asap7 xyce rfmodel M10 rftechdir'",
                "api: chip.set('pdk', 'asap7', 'dir', 'xyce', 'rfmodel', 'M10', "
                "'rftechdir')"],
            schelp="""
            List of named directories specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly supported by the SiliconCompiler PDK schema.""")

    scparam(cfg, ['pdk', pdkname, 'var', tool, key, stackup],
            sctype='[str]',
            scope='global',
            shorthelp="PDK: special variable",
            switch="-pdk_var 'pdkname tool stackup key <str>'",
            example=[
                "cli: -pdk_var 'asap7 xyce modeltype M10 bsim4'",
                "api: chip.set('pdk', 'asap7', 'var', 'xyce', 'modeltype', 'M10', 'bsim4')"],
            schelp="""
            List of key/value strings specified on a per tool and per stackup basis.
            The parameter should only be used for specifying variables that are
            not directly supported by the SiliconCompiler PDK schema.""")

    ###############
    # Docs
    ###############

    doctype = 'default'
    scparam(cfg, ['pdk', pdkname, 'doc', doctype],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: documentation",
            switch="-pdk_doc 'pdkname doctype <file>'",
            example=["cli: -pdk_doc 'asap7 reference reference.pdf'",
                     "api: chip.set('pdk', 'asap7', 'doc', 'reference', 'reference.pdf')"],
            schelp="""
            Filepath to pdk documentation.""")

    return cfg


###############################################################################
# Datasheet ("specification/contract")
###############################################################################
def schema_datasheet(cfg, name='default', mode='default'):

    # Part type
    scparam(cfg, ['datasheet', 'type'],
            sctype='enum',
            enum=['digital', 'analog', 'ams', 'passive',
                  'soc', 'fpga',
                  'adc', 'dac',
                  'pmic', 'buck', 'boost', 'ldo',
                  'sram', 'dram', 'flash', 'rom',
                  'interface', 'clock', 'amplifier',
                  'filter', 'mixer', 'modulator', 'lna'],
            shorthelp="Datasheet: part type",
            switch="-datasheet_type '<str>'",
            example=[
                "cli: -datasheet_type 'digital'",
                "api: chip.set('datasheet', 'type', 'digital')"],
            schelp="""Part type.""")

    # Documentation
    scparam(cfg, ['datasheet', 'doc'],
            sctype='[file]',
            shorthelp="Datasheet: part documentation",
            switch="-datasheet_doc '<file>'",
            example=[
                "cli: -datasheet_doc 'za001.pdf'",
                "api: chip.set('datasheet', 'doc', 'za001.pdf)"],
            schelp="""Device datasheet document.""")

    # Series
    scparam(cfg, ['datasheet', 'series'],
            sctype='str',
            shorthelp="Datasheet: device series",
            switch="-datasheet_series '<str>'",
            example=[
                "cli: -datasheet_series 'ZA0'",
                "api: chip.set('datasheet', 'series', 'ZA0)"],
            schelp="""Device series describing a family of devices or
            a singular device with multiple packages and/or qualification
            SKUs.""")

    # Manufacturer
    scparam(cfg, ['datasheet', 'manufacturer'],
            sctype='str',
            shorthelp="Datasheet: part manufacturer",
            switch="-datasheet_manufacturer '<str>'",
            example=[
                "cli: -datasheet_manufacturer 'Acme'",
                "api: chip.set('datasheet', 'manufacturer', 'Acme')"],
            schelp="""Device manufacturer/vendor.""")

    # Device description
    scparam(cfg, ['datasheet', 'description'],
            sctype='str',
            shorthelp="Datasheet: description",
            switch="-datasheet_description '<str>'",
            example=[
                "cli: -datasheet_description 'Yet another CPU'",
                "api: chip.set('datasheet', 'description', 'Yet another CPU')"],
            schelp="""Free text device description""")

    # Features
    scparam(cfg, ['datasheet', 'features'],
            sctype='[str]',
            shorthelp="Datasheet: part features",
            switch="-datasheet_features '<str>'",
            example=[
                "cli: -datasheet_features 'usb3.0'",
                "api: chip.set('datasheet', 'features', 'usb3.0')"],
            schelp="""List of manufacturer specified device features""")

    # Grade
    scparam(cfg, ['datasheet', 'grade'],
            sctype='enum',
            enum=['consumer', 'industrial',
                  'medical', 'automotive',
                  'military', 'space'],
            shorthelp="Datasheet: part manufacturing grade",
            switch="-datasheet_grade '<str>'",
            example=[
                "cli: -datasheet_grade 'automotive'",
                "api: chip.set('datasheet', 'grade', 'automotive')"],
            schelp="""Device end application qualification grade.""")

    # Qualification
    scparam(cfg, ['datasheet', 'qual'],
            sctype='[str]',
            shorthelp="Datasheet: qualification",
            switch="-datasheet_qual '<str>'",
            example=[
                "cli: -datasheet_qual 'AEC-Q100'",
                "api: chip.set('datasheet', 'qual', 'AEC-Q100')"],
            schelp="""List of qualification standards passed by device.""")

    # TRL
    scparam(cfg, ['datasheet', 'trl'],
            sctype='int',
            shorthelp="Datasheet: technology readiness level",
            switch="-datasheet_trl '<int>'",
            example=[
                "cli: -datasheet_trl 9",
                "api: chip.set('datasheet', 'trl', 9)"],
            schelp="""Technology readiness level (TRL) of device. For more
            information, see:
            https://en.wikipedia.org/wiki/Technology_readiness_level""")

    # Status
    scparam(cfg, ['datasheet', 'status'],
            sctype='enum',
            enum=['preview', 'active', 'deprecated',
                  'last time buy', 'obsolete'],
            shorthelp="Datasheet: product status",
            switch="-datasheet_status '<str>'",
            example=[
                "cli: -datasheet_status 'active'",
                "api: chip.set('datasheet', 'status', 'active')"],
            schelp="""Device production status.""")

    # Maximum Frequency
    scparam(cfg, ['datasheet', 'fmax'],
            sctype='float',
            unit='MHz',
            shorthelp="Datasheet: device maximum frequency",
            switch="-datasheet_fmax '<float>'",
            example=[
                "cli: -datasheet_fmax 100'",
                "api: chip.set('datasheet', 'fmax', 100')"],
            schelp="""Device maximum operating frequency.""")

    # Total OPS
    scparam(cfg, ['datasheet', 'ops'],
            sctype='float',
            shorthelp="Datasheet: total device operations per second",
            switch="-datasheet_ops '<float>'",
            example=[
                "cli: -datasheet_ops 1e18'",
                "api: chip.set('datasheet', 'ops', 1e18)"],
            schelp="""Device peak total operations per second, describing
            the total mathematical operations performed by all on-device
            processing units.""")

    # Total I/O bandwidth
    scparam(cfg, ['datasheet', 'iobw'],
            sctype='float',
            unit='bps',
            shorthelp="Datasheet: total I/O bandwidth",
            switch="-datasheet_iobw '<float>'",
            example=[
                "cli: -datasheet_iobw 1e18'",
                "api: chip.set('datasheet', 'iobw', 1e18)"],
            schelp="""Device peak off-device bandwidth in bits per second.""")

    # Total I/O count
    scparam(cfg, ['datasheet', 'iocount'],
            sctype='int',
            shorthelp="Datasheet: total number of I/Os",
            switch="-datasheet_iocount '<int>'",
            example=[
                "cli: -datasheet_iocount 100'",
                "api: chip.set('datasheet', 'iocount', 100)"],
            schelp="""Device total number of I/Os (not counting supplies).""")

    # Total on-device RAM
    scparam(cfg, ['datasheet', 'ram'],
            sctype='float',
            unit='bits',
            shorthelp="Datasheet: total device RAM",
            switch="-datasheet_ram '<float>'",
            example=[
                "cli: -datasheet_ram 128'",
                "api: chip.set('datasheet', 'ram', 128)"],
            schelp="""Device total RAM.""")

    # Total power
    scparam(cfg, ['datasheet', 'peakpower'],
            sctype='float',
            unit='W',
            shorthelp="Datasheet: peak power",
            switch="-datasheet_peakpower '<float>'",
            example=[
                "cli: -datasheet_peakpower 1'",
                "api: chip.set('datasheet', 'peakpower', 1)"],
            schelp="""Device total peak power.""")

    ######################
    # IO
    ######################

    scparam(cfg, ['datasheet', 'io', name, 'arch'],
            sctype='enum',
            enum=['spi', 'uart', 'i2c', 'pwm', 'qspi', 'sdio', 'can', 'jtag',
                  'spdif', 'i2s',
                  'gpio', 'lvds', 'serdes', 'pio',
                  'ddr3', 'ddr4', 'ddr5',
                  'lpddr4', 'lpddr5',
                  'hbm2', 'hbm3', 'hbm4',
                  'onfi', 'sram',
                  'hdmi', 'mipi-csi', 'mipi-dsi', 'slvs',
                  'sata',
                  'usb1', 'usb2', 'usb3',
                  'pcie3', 'pcie4', 'pcie5', 'pcie6',
                  'cxl',
                  'ethernet', 'rmii', 'rgmii', 'sgmii', 'xaui',
                  '10gbase-kr', '25gbase-kr', 'xfi', 'cei28g',
                  'jesd204', 'cpri'],
            shorthelp="Datasheet: io standard",
            switch="-datasheet_io_arch 'name <str>'",
            example=[
                "cli: -datasheet_io_arch 'pio spi'",
                "api: chip.set('datasheet', 'io', 'pio', 'arch', 'spi')"],
            schelp="""Datasheet: List of IO standard architectures supported
            by the named port.""")

    metrics = {'fmax': ['maximum frequency', 100, 'float', 'MHz'],
               'width': ['width', 4, 'int', None],
               'channels': ['channels', 4, 'int', None]
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'io', name, i],
                unit=v[3],
                sctype=v[2],
                shorthelp=f"Datasheet: io {v[0]}",
                switch=f"-datasheet_io_{i} 'name <{v[2]}>'",
                example=[
                    f"cli: -datasheet_io_{i} 'name {v[1]}'",
                    f"api: chip.set('datasheet', 'io', name, '{i}', {v[1]})"],
                schelp=f"""Datasheet: IO {v[1]} metrics specified on a named port basis.
                """)

    ######################
    # Processor
    ######################

    scparam(cfg, ['datasheet', 'proc', name, 'arch'],
            sctype='str',
            shorthelp="Datasheet: processor architecture",
            switch="-datasheet_proc_arch 'name <str>'",
            example=[
                "cli: -datasheet_proc_arch '0 RV64GC'",
                "api: chip.set('datasheet', 'proc', name, 'arch', 'openfpga')"],
            schelp="""Processor architecture.""")

    scparam(cfg, ['datasheet', 'proc', name, 'features'],
            sctype='[str]',
            shorthelp="Datasheet: processor features",
            switch="-datasheet_proc_features 'name <str>'",
            example=[
                "cli: -datasheet_proc_features '0 SIMD'",
                "api: chip.set('datasheet','proc','cpu','features', 'SIMD')"],
            schelp="""List of maker specified processor features.""")

    scparam(cfg, ['datasheet', 'proc', name, 'datatypes'],
            sctype='[enum]',
            enum=['int4', 'int8', 'int16', 'int32', 'int64', 'int128',
                  'uint4', 'uint8', 'uint16', 'uint32', 'uint64', 'uint128',
                  'bfloat16', 'fp16', 'fp32', 'fp64', 'fp128'],
            shorthelp="Datasheet: processor datatypes",
            switch="-datasheet_proc_datatypes 'name <str>'",
            example=[
                "cli: -datasheet_proc_datatypes '0 int8'",
                "api: chip.set('datasheet', 'proc', 'cpu', 'datatypes', 'int8')"],
            schelp="""List of datatypes supported by the processor.""")

    metrics = {'archsize': ['architecture size', 64, None],
               'cores': ['number of cores', 4, None],
               'fmax': ['maximum frequency', 100, 'MHz'],
               'ops': ['operations per cycle per core', 4, None],
               'mults': ['hard multiplier units per core', 100, None],
               'icache': ['l1 icache size', 32, 'KB'],
               'dcache': ['l1 dcache size', 32, 'KB'],
               'l2cache': ['l2 cache size', 1024, 'KB'],
               'l3cache': ['l3 cache size', 1024, 'KB'],
               'sram': ['local sram', 128, 'KB'],
               'nvm': ['local non-volatile memory', 128, 'KB']}

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'proc', name, i],
                unit=v[2],
                sctype='int',
                shorthelp=f"Datasheet: processor {v[0]}",
                switch=f"-datasheet_proc_{i} 'name <int>'",
                example=[
                    f"cli: -datasheet_proc_{i} 'cpu {v[1]}'",
                    f"api: chip.set('datasheet', 'proc', 'cpu', '{i}', {v[1]})"],
                schelp=f"""Processor metric: {v[0]}.""")

    ######################
    # Memory
    ######################

    scparam(cfg, ['datasheet', 'memory', name, 'bits'],
            sctype='int',
            shorthelp="Datasheet: memory total bits",
            switch="-datasheet_memory_bits 'name <int>'",
            example=[
                "cli: -datasheet_memory_bits 'm0 1024'",
                "api: chip.set('datasheet', 'memory', 'm0', 'bits', 1024)"],
            schelp="""Memory total number of bits.""")

    scparam(cfg, ['datasheet', 'memory', name, 'width'],
            sctype='int',
            shorthelp="Datasheet: memory width",
            switch="-datasheet_memory_width 'name <int>'",
            example=[
                "cli: -datasheet_memory_width 'm0 16'",
                "api: chip.set('datasheet', 'memory', 'm0', 'width', 16)"],
            schelp="""Memory width.""")

    scparam(cfg, ['datasheet', 'memory', name, 'depth'],
            sctype='int',
            shorthelp="Datasheet: memory depth",
            switch="-datasheet_memory_depth 'name <int>'",
            example=[
                "cli: -datasheet_memory_depth 'm0 128'",
                "api: chip.set('datasheet', 'memory', 'm0', 'depth', 128)"],
            schelp="""Memory depth.""")

    scparam(cfg, ['datasheet', 'memory', name, 'banks'],
            sctype='int',
            shorthelp="Datasheet: memory banks",
            switch="-datasheet_memory_banks 'name <int>'",
            example=[
                "cli: -datasheet_memory_banks 'm0 4'",
                "api: chip.set('datasheet', 'memory', 'm0', 'banks', 4)"],
            schelp="""Memory banks.""")

    # Timing
    metrics = {'fmax': ['max frequency', (1e9, 1e9, 1e9), 'Hz'],
               'tcycle': ['access clock cycle', (9.0, 10.0, 11.0), 'ns'],
               'twr': ['write clock cycle', (0.9, 1, 1.1), 'ns'],
               'trd': ['read clock cycle', (0.9, 1, 1.1), 'ns'],
               'trefresh': ['refresh time', (99, 100, 101), 'ns'],
               'terase': ['erase time', (1e-6, 1e-6, 1e-6), 's'],
               'bwrd': ['maximum read bandwidth', (1e9, 1e9, 1e9), 'bps'],
               'bwwr': ['maximum write bandwidth', (1e9, 1e9, 1e9), 'bps'],
               'erd': ['read energy', (1e-12, 2e-12, 3e-12), 'J'],
               'ewr': ['write energy', (1e-12, 2e-12, 3e-12), 'J'],
               'twearout': ['write/erase wear-out', (100e3, 100e4, 100e5), 'cycles']
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'memory', name, i],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: memory {v[0]}",
                switch=f"-datasheet_memory_{i} 'name <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_memory_{i} 'name {v[1]}'",
                    f"api: chip.set('datasheet', 'memory', name, '{i}', {v[1]})"],
                schelp=f"""Memory {v[1]}.""")

    # Latency (cycles)
    metrics = {'tcl': ['column address latency', (100, 100, 100), 'cycles'],
               'trcd': ['row address latency', (100, 100, 100), 'cycles'],
               'trp': ['row precharge time latency', (100, 100, 100), 'cycles'],
               'tras': ['row active time latency', (100, 100, 100), 'cycles']
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'memory', name, i],
                unit=v[2],
                sctype='(int,int,int)',
                shorthelp=f"Datasheet: memory {v[0]}",
                switch=f"-datasheet_memory_{i} 'name <(int,int,int)>'",
                example=[
                    f"cli: -datasheet_memory_{i} 'name {v[1]}'",
                    f"api: chip.set('datasheet', 'memory', name, '{i}', {v[1]})"],
                schelp=f"""Memory {v[1]}.""")

    ######################
    # FPGA
    ######################

    scparam(cfg, ['datasheet', 'fpga', name, 'arch'],
            sctype='str',
            shorthelp="Datasheet: fpga architecture",
            switch="-datasheet_fpga_arch 'name <str>'",
            example=[
                "cli: -datasheet_fpga_arch 'i0 openfpga'",
                "api: chip.set('datasheet', 'fpga', 'i0', 'arch', 'openfpga')"],
            schelp="""FPGA architecture.
            """)

    metrics = {'luts': ['LUTs (4 input)', 32000, None],
               'registers': ['registers', 100, None],
               'plls': ['pll blocks', 1, None],
               'mults': ['multiplier/dsp elements', 100, None],
               'totalram': ['total ram', 128, 'Kb'],
               'distram': ['distributed ram', 128, 'Kb'],
               'blockram': ['block ram', 128, 'Kb']}

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'fpga', name, i],
                unit=v[2],
                sctype='int',
                shorthelp=f"Datasheet: fpga {v[0]}",
                switch=f"-datasheet_fpga_{i} 'name <int>'",
                example=[
                    f"cli: -datasheet_fpga_{i} 'i0 {v[1]}'",
                    f"api: chip.set('datasheet', 'fpga', 'i0', '{i}', {v[1]})"],
                schelp=f"""FPGA {v[1]}.""")

    ######################
    # Analog
    ######################

    scparam(cfg, ['datasheet', 'analog', name, 'arch'],
            sctype='str',
            shorthelp="Datasheet: analog architecture",
            switch="-datasheet_analog_arch 'name <str>'",
            example=[
                "cli: -datasheet_analog_arch 'adc0 pipelined'",
                "api: chip.set('datasheet', 'analog', 'adc0', 'arch', 'pipelined')"],
            schelp="""Analog component architecture.""")

    scparam(cfg, ['datasheet', 'analog', name, 'features'],
            sctype='[str]',
            shorthelp="Datasheet: analog features",
            switch="-datasheet_analog_features 'name <str>'",
            example=[
                "cli: -datasheet_analog_features '0 differential input'",
                "api: chip.set('datasheet','analog','adc0','features', 'differential input')"],
            schelp="""List of maker specified analog features.""")

    metrics = {'resolution': ['architecture resolution', 8],
               'channels': ['parallel channels', 8]}

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'analog', name, i],
                sctype='int',
                shorthelp=f"Datasheet: Analog {v[0]}",
                switch=f"-datasheet_analog_{i} 'name <int>'",
                example=[
                    f"cli: -datasheet_analog_{i} 'i0 {v[1]}'",
                    f"api: chip.set('datasheet', 'analog', 'abc123', '{i}', {v[1]})"],
                schelp=f"""Analog {v[1]}.""")

    metrics = {'samplerate': ['sample rate', (1e9, 1e9, 1e9), 'Hz'],
               'enob': ['effective number of bits', (8, 9, 10), 'bits'],
               'inl': ['integral nonlinearity', (-7, 0.0, 7), 'LSB'],
               'dnl': ['differential nonlinearity', (-1.0, 0.0, +1.0), 'LSB'],
               'snr': ['signal to noise ratio', (70, 72, 74), 'dB'],
               'sinad': ['signal to noise and distortion ratio', (71, 72, 73), 'dB'],
               'sfdr': ['spurious-free dynamic range', (82, 88, 98), 'dBc'],
               'thd': ['total harmonic distortion', (82, 88, 98), 'dB'],
               'imd3': ['3rd order intermodulation distortion', (82, 88, 98), 'dBc'],
               'hd2': ['2nd order harmonic distortion', (62, 64, 66), 'dBc'],
               'hd3': ['3rd order harmonic distortion', (62, 64, 66), 'dBc'],
               'hd4': ['4th order harmonic distortion', (62, 64, 66), 'dBc'],
               'nsd': ['noise spectral density', (-158, -158, -158), 'dBFS/Hz'],
               'phasenoise': ['phase noise', (-158, -158, -158), 'dBc/Hz'],
               'gain': ['gain', (11.4, 11.4, 11.4), 'dB'],
               'pout': ['output power', (12.2, 12.2, 12.2), 'dBm'],
               'pout2': ['2nd harmonic power', (-14, -14, -14), 'dBm'],
               'pout3': ['3rd harmonic power', (-28, -28, -28), 'dBm'],
               'vofferror': ['offset error', (-1.0, 0.0, +1.0), 'mV'],
               'vgainerror': ['gain error', (-1.0, 0.0, +1.0), 'mV'],
               'cmrr': ['common mode rejection ratio', (70, 80, 90), 'dB'],
               'psnr': ['power supply noise rejection', (61, 61, 61), 'dB'],
               's21': ['rf gain', (10, 11, 12), 'dB'],
               's11': ['rf input return loss', (7, 7, 7), 'dB'],
               's22': ['rf output return loss', (10, 10, 10), 'dB'],
               's12': ['rf reverse isolation', (-20, -20, -20), 'dB'],
               'noisefigure': ['rf noise figure', (4.6, 4.6, 4.6), 'dB'],
               'ib1db': ['rf in band 1 dB compression point', (-1, 1, 1), 'dBm'],
               'oob1db': ['rf out of band 1 dB compression point', (3, 3, 3), 'dBm'],
               'iip3': ['rf 3rd order input intercept point', (3, 3, 3), 'dBm']
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'analog', name, i],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: Analog {v[0]}",
                switch=f"-datasheet_analog_{i} 'name <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_analog_{i} 'i0 {v[1]}'",
                    f"api: chip.set('datasheet', 'analog', 'abc123', '{i}', {v[1]})"],
                schelp=f"""Analog {v[1]}.""")

    ######################
    # Absolute Limits
    ######################

    metrics = {'tstorage': ['storage temperature limits', (-40, 125), 'C'],
               'tsolder': ['solder temperature limits', (-40, 125), 'C'],
               'tj': ['junction temperature limits', (-40, 125), 'C'],
               'ta': ['ambient temperature limits', (-40, 125), 'C'],
               'tid': ['total ionizing dose threshold', (3e5, 3e5), 'rad'],
               'sel': ['single event latchup threshold', (75, 75), 'MeV-cm2/mg'],
               'seb': ['single event burnout threshold', (75, 75), 'MeV-cm2/mg'],
               'segr': ['single event gate rupture threshold', (75, 75), 'MeV-cm2/mg'],
               'set': ['single event transient threshold', (75, 75), 'MeV-cm2/mg'],
               'seu': ['single event upset threshold', (75, 75), 'MeV-cm2/mg'],
               'vhbm': ['ESD human body model voltage level', (200, 250), 'V'],
               'vcdm': ['ESD charge device model voltage level', (150, 150), 'V'],
               'vmm': ['ESD machine model voltage level', (125, 125), 'V']
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'limit', i],
                unit=v[2],
                sctype='(float,float)',
                shorthelp=f"Datasheet: limit {v[0]}",
                switch=f"-datasheet_limit_{i} '<(float,float)>'",
                example=[
                    f"cli: -datasheet_limit_{i} '{v[1]}'",
                    f"api: chip.set('datasheet', 'limit', '{i}', {v[1]}"],
                schelp=f"""Limit {v[0]}. Values are tuples of (min, max).
                """)

    ######################
    # Thermal Model
    ######################

    metrics = {'rja': 'thermal junction to ambient resistance',
               'rjct': 'thermal junction to case (top) resistance',
               'rjcb': 'thermal junction to case (bottom) resistance',
               'rjb': 'thermal junction to board resistance',
               'tjt': 'thermal junction to top model',
               'tjb': 'thermal junction to bottom model'}

    for item, val in metrics.items():
        scparam(cfg, ['datasheet', 'thermal', item],
                unit='C/W',
                sctype='float',
                shorthelp=f"Datasheet: {val}",
                switch=f"-datasheet_thermal_{item} '<float>'",
                example=[
                    f"cli: -datasheet_thermal_{item} '30.4'",
                    f"api: chip.set('datasheet', 'thermal', '{item}', 30.4)"],
                schelp=f"""Device {item}.""")

    #########################
    # Package Description
    #########################

    scparam(cfg, ['datasheet', 'package', name, 'type'],
            sctype='enum',
            enum=['bga', 'lga', 'csp', 'qfn', 'qfp', 'sop', 'die', 'wafer'],
            shorthelp="Datasheet: package type",
            switch="-datasheet_package_type 'name <str>'",
            example=[
                "cli: -datasheet_package_type 'abcd bga'",
                "api: chip.set('datasheet', 'package', 'abcd', 'type', 'bga')"],
            schelp="""Datasheet: package type.""")

    scparam(cfg, ['datasheet', 'package', name, 'drawing'],
            sctype='[file]',
            shorthelp="Datasheet: package drawing",
            switch="-datasheet_package_drawing 'name <file>'",
            example=[
                "cli: -datasheet_package_drawing 'abcd p484.pdf'",
                "api: chip.set('datasheet', 'package', 'abcd', 'drawing', 'p484.pdf')"],
            schelp="""Datasheet: package drawing""")

    scparam(cfg, ['datasheet', 'package', name, 'pincount'],
            sctype='int',
            shorthelp="Datasheet: package pincount",
            switch="-datasheet_package_pincount 'name <int>'",
            example=[
                "cli: -datasheet_package_pincount 'abcd 484'",
                "api: chip.set('datasheet', 'package', 'abcd', 'pincount', '484')"],
            schelp="""Datasheet: package pincount""")

    metrics = {'length': ['length', (20, 20, 20), 'mm'],
               'width': ['width', (20, 20, 20), 'mm'],
               'thickness': ['thickness', (1.0, 1.1, 1.2), 'mm'],
               'pitch': ['pitch', (0.8, 0.85, 0.9), 'mm']
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'package', name, i],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: package {v[0]}",
                switch=f"-datasheet_package_{i} 'name <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_package_{i} 'abcd {v[1]}'",
                    f"api: chip.set('datasheet', 'package', 'abcd', '{i}', {v[1]}"],
                schelp=f"""Datasheet: package {v[0]}. Values are tuples of
                (min, nominal, max).""")

    scparam(cfg, ['datasheet', 'package', name, 'pinshape', name],
            sctype='enum',
            enum=['circle', 'rectangle'],
            shorthelp="Datasheet: package pin shape",
            switch="-datasheet_package_pinshape 'name name <str>'",
            example=[
                "cli: -datasheet_package_pinshape 'abcd B1 circle'",
                "api: chip.set('datasheet', 'package', 'abcd', 'pinshape', 'B1', 'circle')"],
            schelp="""Datasheet: pin shape (rectangle or circle) specified on a per package
            and per pin basis.""")

    metrics = {'pinwidth': ['pinwidth', (0.2, 0.25, 0.3), 'mm'],
               'pinlength': ['pinlength', (0.2, 0.25, 0.3), 'mm']
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'package', name, i, name],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: package pin {v[0]}",
                switch=f"-datasheet_package_{i} 'name name <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_package_{i} 'abcd B1 {v[1]}'",
                    f"api: chip.set('datasheet', 'package', 'abcd', '{i}', 'B1', {v[1]}"],
                schelp=f"""Datsheet: {v[0]} specified on a per package and per pin basis.
                Values are tuples of (min, nominal, max).""")

    scparam(cfg, ['datasheet', 'package', name, 'pinloc', name],
            sctype='(float,float)',
            unit='mm',
            shorthelp="Datasheet: package pin location",
            switch="-datasheet_package_pinloc 'name name <(float,float)>'",
            example=[
                "cli: -datasheet_package_pinloc 'abcd B1 (0.5,0.5)'",
                "api: chip.set('datasheet', 'package', 'abcd', 'pinloc', 'B1', (0.5,0.5)"],
            schelp="""Datsheet: Pin location specified as an (x,y) tuple. Locations
            specify the center of the pin with respect to the center of the package.
            """)

    scparam(cfg, ['datasheet', 'package', name, 'netname', name],
            sctype='str',
            shorthelp="Datasheet: package pin netname",
            switch="-datasheet_package_netname 'name name <str>'",
            example=[
                "cli: -datasheet_package_netname 'abcd B1 VDD'",
                "api: chip.set('datasheet', 'package', 'abcd', 'netname', 'B1', 'VDD')"],
            schelp="""Datsheet: Net name connected to package pin.""")

    ######################
    # Pin Specifications
    ######################

    # Pin type
    scparam(cfg, ['datasheet', 'pin', name, 'type', mode],
            sctype='enum',
            enum=['digital', 'analog', 'clock', 'supply', 'ground'],
            shorthelp="Datasheet: pin type",
            switch="-datasheet_pin_type 'name mode <str>'",
            example=[
                "cli: -datasheet_pin_type 'vdd global supply'",
                "api: chip.set('datasheet', 'pin', 'vdd', 'type', 'global', 'supply')"],
            schelp="""Pin type specified on a per mode basis.""")

    # Pin direction
    scparam(cfg, ['datasheet', 'pin', name, 'dir', mode],
            sctype='enum',
            enum=['input', 'output', 'inout'],
            shorthelp="Datasheet: pin direction",
            switch="-datasheet_pin_dir 'name mode <str>'",
            example=[
                "cli: -datasheet_pin_dir 'clk global input'",
                "api: chip.set('datasheet', 'pin', 'clk', 'dir', 'global', 'input')"],
            schelp="""Pin direction specified on a per mode basis. Acceptable pin
            directions include: input, output, inout.""")

    # Pin complement (for differential pair)
    scparam(cfg, ['datasheet', 'pin', name, 'complement', mode],
            sctype='str',
            shorthelp="Datasheet: pin complement",
            switch="-datasheet_pin_complement 'name mode <str>'",
            example=[
                "cli: -datasheet_pin_complement 'ina global inb'",
                "api: chip.set('datasheet', 'pin', 'ina', 'complement', 'global', 'inb')"],
            schelp="""Pin complement specified on a per mode basis for differential
            signals.""")

    # Pin standard
    scparam(cfg, ['datasheet', 'pin', name, 'standard', mode],
            sctype='[str]',
            shorthelp="Datasheet: pin standard",
            switch="-datasheet_pin_standard 'name mode <str>'",
            example=[
                "cli: -datasheet_pin_standard 'clk def LVCMOS'",
                "api: chip.set('datasheet', 'pin', 'clk', 'standard', 'def', 'LVCMOS')"],
            schelp="""Pin electrical signaling standard (LVDS, LVCMOS, TTL, ...).""")

    # Pin interface map
    scparam(cfg, ['datasheet', 'pin', name, 'interface', mode],
            sctype='[str]',
            shorthelp="Datasheet: pin interface map",
            switch="-datasheet_pin_interface 'name mode <str>'",
            example=[
                "cli: -datasheet_pin_interface 'clk0 ddr4 CLKN'",
                "api: chip.set('datasheet', 'pin', 'clk0', 'interface', 'ddr4', 'CLKN')"],
            schelp="""Pin mapping to standardized interface names.""")

    # Pin reset value
    scparam(cfg, ['datasheet', 'pin', name, 'resetvalue', mode],
            sctype='enum',
            enum=['weak1', 'weak0', 'strong0', 'strong1', 'highz'],
            shorthelp="Datasheet: pin reset value",
            switch="-datasheet_pin_resetvalue 'name mode <str>'",
            example=[
                "cli: -datasheet_pin_resetvalue 'clk global weak1'",
                "api: chip.set('datasheet', 'pin', 'clk', 'resetvalue', 'global', 'weak1')"],
            schelp="""Pin reset value specified on a per mode basis.""")

    # Per pin specifications
    metrics = {'vmax': ['absolute maximum voltage', (0.2, 0.3, 0.9), 'V'],
               'vnominal': ['nominal operating voltage', (1.72, 1.80, 1.92), 'V'],
               'vol': ['low output voltage level', (-0.2, 0, 0.2), 'V'],
               'voh': ['high output voltage level', (4.6, 4.8, 5.2), 'V'],
               'vil': ['low input voltage level', (-0.2, 0, 1.0), 'V'],
               'vih': ['high input voltage level', (1.4, 1.8, 2.2), 'V'],
               'vcm': ['common mode voltage', (0.3, 1.2, 1.6), 'V'],
               'vdiff': ['differential voltage', (0.2, 0.3, 0.9), 'V'],
               'voffset': ['offset voltage', (0.2, 0.3, 0.9), 'V'],
               'vnoise': ['random voltage noise', (0, 0.01, 0.1), 'V'],
               'vslew': ['slew rate', (1e-9, 2e-9, 4e-9), 'V/s'],
               # ESD
               'vhbm': ['ESD human body model voltage level', (200, 250, 300), 'V'],
               'vcdm': ['ESD charge device model voltage level', (125, 150, 175), 'V'],
               'vmm': ['ESD machine model voltage level', (100, 125, 150), 'V'],
               # RC
               'cap': ['capacitance', (1e-12, 1.2e-12, 1.5e-12), 'F'],
               'rdiff': ['differential pair resistance', (45, 50, 55), 'Ohm'],
               'rin': ['input resistance', (1000, 1200, 3000), 'Ohm'],
               'rup': ['output pullup resistance', (1000, 1200, 3000), 'Ohm'],
               'rdown': ['output pulldown resistance', (1000, 1200, 3000), 'Ohm'],
               'rweakup': ['weak pullup resistance', (1000, 1200, 3000), 'Ohm'],
               'rweakdown': ['weak pulldown resistance', (1000, 1200, 3000), 'Ohm'],
               # Power (per supply)
               'power': ['power consumption', (1, 2, 3), 'W'],
               # Current
               'isupply': ['supply current', (1e-3, 12e-3, 15e-3), 'A'],
               'ioh': ['output high current', (10e-3, 12e-3, 15e-3), 'A'],
               'iol': ['output low current', (10e-3, 12e-3, 15e-3), 'A'],
               'iinject': ['injection current', (1e-3, 1.2e-3, 1.5e-3), 'A'],
               'ishort': ['short circuit current', (1e-3, 1.2e-3, 1.5e-3), 'A'],
               'ioffset': ['offset current', (1e-3, 1.2e-3, 1.5e-3), 'A'],
               'ibias': ['bias current', (1e-3, 1.2e-3, 1.5e-3), 'A'],
               'ileakage': ['leakage current', (1e-6, 1.2e-6, 1.5e-6), 'A'],
               # Clocking
               'tperiod': ['minimum period', (1e-9, 2e-9, 4e-9), 's'],
               'tpulse': ['pulse width', (1e-9, 2e-9, 4e-9), 's'],
               'tjitter': ['rms jitter', (1e-9, 2e-9, 4e-9), 's'],
               'thigh': ['pulse width high', (1e-9, 2e-9, 4e-9), 's'],
               'tlow': ['pulse width low', (1e-9, 2e-9, 4e-9), 's'],
               'tduty': ['duty cycle', (45, 50, 55), '%']
               }

    for item, val in metrics.items():
        scparam(cfg, ['datasheet', 'pin', name, item, mode],
                unit=val[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: pin {val[0]}",
                switch=f"-datasheet_pin_{item} 'pin mode <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_pin_{item} 'sclk global {val[1]}'",
                    f"api: chip.set('datasheet', 'pin', 'sclk', '{item}', "
                    f"'global', {val[1]}"],
                schelp=f"""Pin {val[0]}. Values are tuples of (min, typical, max).""")

    # Timing
    metrics = {'tsetup': ['setup time', (1e-9, 2e-9, 4e-9), 's'],
               'thold': ['hold time', (1e-9, 2e-9, 4e-9), 's'],
               'tskew': ['timing skew', (1e-9, 2e-9, 4e-9), 's'],
               'tdelayr': ['propagation delay (rise)', (1e-9, 2e-9, 4e-9), 's'],
               'tdelayf': ['propagation delay (fall)', (1e-9, 2e-9, 4e-9), 's'],
               'trise': ['rise transition', (1e-9, 2e-9, 4e-9), 's'],
               'tfall': ['fall transition', (1e-9, 2e-9, 4e-9), 's']}

    relpin = 'default'

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'pin', name, i, mode, relpin],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: pin {v[0]}",
                switch=f"-datasheet_pin_{i} 'pin mode relpin <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_pin_{i} 'a glob clock {v[1]}'",
                    f"api: chip.set('datasheet', 'pin', 'a', '{i}', 'glob', 'ck', {v[1]}"],
                schelp=f"""Pin {v[0]} specified on a per pin, mode, and relpin basis.
                Values are tuples of (min, typical, max).""")

    return cfg


###############################################################################
# Flow Configuration
###############################################################################
def schema_flowgraph(cfg, flow='default', step='default', index='default'):

    # flowgraph input
    scparam(cfg, ['flowgraph', flow, step, index, 'input'],
            sctype='[(str,str)]',
            shorthelp="Flowgraph: step input",
            switch="-flowgraph_input 'flow step index <(str,str)>'",
            example=[
                "cli: -flowgraph_input 'asicflow cts 0 (place,0)'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))"],
            schelp="""A list of inputs for the current step and index, specified as a
            (step, index) tuple.""")

    # flowgraph metric weights
    metric = 'default'
    scparam(cfg, ['flowgraph', flow, step, index, 'weight', metric],
            sctype='float',
            shorthelp="Flowgraph: metric weights",
            switch="-flowgraph_weight 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_weight 'asicflow cts 0 area_cells 1.0'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'weight', 'area_cells', 1.0)"],
            schelp="""Weights specified on a per step and per metric basis used to give
            effective "goodness" score for a step by calculating the sum all step
            real metrics results by the corresponding per step weights.""")

    scparam(cfg, ['flowgraph', flow, step, index, 'goal', metric],
            sctype='float',
            shorthelp="Flowgraph: metric goals",
            switch="-flowgraph_goal 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_goal 'asicflow cts 0 area_cells 1.0'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'goal', 'errors', 0)"],
            schelp="""Goals specified on a per step and per metric basis used to
            determine whether a certain task can be considered when merging
            multiple tasks at a minimum or maximum node. A task is considered
            failing if the absolute value of any of its metrics are larger than
            the goal for that metric, if set.""")

    # flowgraph tool
    scparam(cfg, ['flowgraph', flow, step, index, 'tool'],
            sctype='str',
            shorthelp="Flowgraph: tool selection",
            switch="-flowgraph_tool 'flow step index <str>'",
            example=[
                "cli: -flowgraph_tool 'asicflow place 0 openroad'",
                "api: chip.set('flowgraph', 'asicflow', 'place', '0', 'tool', 'openroad')"],
            schelp="""Name of the tool name used for task execution. The 'tool' parameter
            is ignored for builtin tasks.""")

    # task (belonging to tool)
    scparam(cfg, ['flowgraph', flow, step, index, 'task'],
            sctype='str',
            shorthelp="Flowgraph: task selection",
            switch="-flowgraph_task 'flow step index <str>'",
            example=[
                "cli: -flowgraph_task 'asicflow myplace 0 place'",
                "api: chip.set('flowgraph', 'asicflow', 'myplace', '0', 'task', 'place')"],
            schelp="""Name of the tool associated task used for step execution. Builtin
            task names include: minimum, maximum, join, verify, mux. """)

    scparam(cfg, ['flowgraph', flow, step, index, 'taskmodule'],
            sctype='str',
            shorthelp="Flowgraph: task module",
            switch="-flowgraph_taskmodule 'flow step index <str>'",
            example=[
                "cli: -flowgraph_taskmodule 'asicflow place 0 "
                "siliconcompiler.tools.openroad.place'",
                "api: chip.set('flowgraph', 'asicflow', 'place', '0', 'taskmodule', "
                "'siliconcompiler.tools.openroad.place')"],
            schelp="""
            Full python module name of the task module used for task setup and execution.
            """)

    # flowgraph arguments
    scparam(cfg, ['flowgraph', flow, step, index, 'args'],
            sctype='[str]',
            shorthelp="Flowgraph: setup arguments",
            switch="-flowgraph_args 'flow step index <str>'",
            example=[
                "cli: -flowgraph_args 'asicflow cts 0 0'",
                "api: chip.add('flowgraph', 'asicflow', 'cts', '0', 'args', '0')"],
            schelp="""User specified flowgraph string arguments specified on a per
            step and per index basis.""")

    return cfg


###########################################################################
# Tool Setup
###########################################################################

def schema_tool(cfg, tool='default'):

    version = 'default'

    scparam(cfg, ['tool', tool, 'exe'],
            sctype='str',
            shorthelp="Tool: executable name",
            switch="-tool_exe 'tool <str>'",
            example=["cli: -tool_exe 'openroad openroad'",
                     "api: chip.set('tool', 'openroad', 'exe', 'openroad')"],
            schelp="""Tool executable name.""")

    scparam(cfg, ['tool', tool, 'sbom', version],
            sctype='[file]',
            pernode='optional',
            shorthelp="Tool: software BOM",
            switch="-tool_sbom 'tool version <file>'",
            example=[
                "cli: -tool_sbom 'yosys 1.0.1 ys_sbom.json'",
                "api: chip.set('tool', 'yosys', 'sbom', '1.0', 'ys_sbom.json')"],
            schelp="""
            Paths to software bill of material (SBOM) document file of the tool
            specified on a per version basis. The SBOM includes critical
            package information about the tool including the list of included
            components, licenses, and copyright. The SBOM file is generally
            provided as in a a standardized open data format such as SPDX.""")

    scparam(cfg, ['tool', tool, 'path'],
            sctype='dir',
            pernode='optional',
            shorthelp="Tool: executable path",
            switch="-tool_path 'tool <dir>'",
            example=[
                "cli: -tool_path 'openroad /usr/local/bin'",
                "api: chip.set('tool', 'openroad', 'path', '/usr/local/bin')"],
            schelp="""
            File system path to tool executable. The path is prepended to the
            system PATH environment variable for batch and interactive runs. The
            path parameter can be left blank if the 'exe' is already in the
            environment search path.""")

    scparam(cfg, ['tool', tool, 'vswitch'],
            sctype='[str]',
            shorthelp="Tool: executable version switch",
            switch="-tool_vswitch 'tool <str>'",
            example=["cli: -tool_vswitch 'openroad -version'",
                     "api: chip.set('tool', 'openroad', 'vswitch', '-version')"],
            schelp="""
            Command line switch to use with executable used to print out
            the version number. Common switches include -v, -version,
            --version. Some tools may require extra flags to run in batch mode.""")

    scparam(cfg, ['tool', tool, 'vendor'],
            sctype='str',
            shorthelp="Tool: vendor",
            switch="-tool_vendor 'tool <str>'",
            example=["cli: -tool_vendor 'yosys yosys'",
                     "api: chip.set('tool', 'yosys', 'vendor', 'yosys')"],
            schelp="""
            Name of the tool vendor. Parameter can be used to set vendor
            specific technology variables in the PDK and libraries. For
            open source projects, the project name should be used in
            place of vendor.""")

    scparam(cfg, ['tool', tool, 'version'],
            sctype='[str]',
            pernode='optional',
            shorthelp="Tool: version",
            switch="-tool_version 'tool <str>'",
            example=["cli: -tool_version 'openroad >=v2.0'",
                     "api: chip.set('tool', 'openroad', 'version', '>=v2.0')"],
            schelp="""
            List of acceptable versions of the tool executable to be used. Each
            entry in this list must be a version specifier as described by Python
            `PEP-440 <https://peps.python.org/pep-0440/#version-specifiers>`_.
            During task execution, the tool is called with the 'vswitch' to
            check the runtime executable version. If the version of the system
            executable is not allowed by any of the specifiers in 'version',
            then the job is halted pre-execution. For backwards compatibility,
            entries that do not conform to the standard will be interpreted as a
            version with an '==' specifier. This check can be disabled by
            setting 'novercheck' to True.""")

    scparam(cfg, ['tool', tool, 'format'],
            sctype='enum',
            enum=["json", "tcl", "yaml"],
            shorthelp="Tool: file format",
            switch="-tool_format 'tool <str>'",
            example=["cli: -tool_format 'yosys tcl'",
                     "api: chip.set('tool', 'yosys', 'format', 'tcl')"],
            schelp="""
            File format for tool manifest handoff.""")

    key = 'default'
    scparam(cfg, ['tool', tool, 'licenseserver', key],
            sctype='[str]',
            pernode='optional',
            shorthelp="Tool: license servers",
            switch="-tool_licenseserver 'name key <str>'",
            example=[
                "cli: -tool_licenseserver 'atask ACME_LICENSE 1700@server'",
                "api: chip.set('tool', 'acme', 'licenseserver', 'ACME_LICENSE', '1700@server')"],
            schelp="""
            Defines a set of tool specific environment variables used by the executable
            that depend on license key servers to control access. For multiple servers,
            separate each server by a 'colon'. The named license variable are read at
            runtime (run()) and the environment variables are set.
            """)

    return cfg


def schema_task(cfg, tool='default', task='default', step='default', index='default'):

    key = 'default'
    suffix = 'default'

    scparam(cfg, ['tool', tool, 'task', task, 'warningoff'],
            sctype='[str]',
            pernode='optional',
            shorthelp="Task: warning filter",
            switch="-tool_task_warningoff 'tool task <str>'",
            example=[
                "cli: -tool_task_warningoff 'verilator lint COMBDLY'",
                "api: chip.set('tool', 'verilator', 'task', 'lint', 'warningoff', 'COMBDLY')"],
            schelp="""
            A list of tool warnings for which printing should be suppressed.
            Generally this is done on a per design basis after review has
            determined that warning can be safely ignored The code for turning
            off warnings can be found in the specific task reference manual.
            """)

    scparam(cfg, ['tool', tool, 'task', task, 'regex', suffix],
            sctype='[str]',
            pernode='optional',
            shorthelp="Task: regex filter",
            switch="-tool_task_regex 'tool task suffix <str>'",
            example=[
                "cli: -tool_task_regex 'openroad place errors \"-v ERROR\"'",
                "api: chip.set('tool', 'openroad', 'task', 'place', 'regex', 'errors', "
                "'-v ERROR')"],
            schelp="""
            A list of piped together grep commands. Each entry represents a set
            of command line arguments for grep including the regex pattern to
            match. Starting with the first list entry, each grep output is piped
            into the following grep command in the list. Supported grep options
            include ``-v`` and ``-e``. Patterns starting with "-" should be
            directly preceded by the ``-e`` option. The following example
            illustrates the concept.

            UNIX grep:

            .. code-block:: bash

                $ grep WARNING place.log | grep -v "bbox" > place.warnings

            SiliconCompiler::

                chip.set('task', 'openroad', 'regex', 'place', '0', 'warnings',
                         ["WARNING", "-v bbox"])

            The "errors" and "warnings" suffixes are special cases. When set,
            the number of matches found for these regexes will be added to the
            errors and warnings metrics for the task, respectively. This will
            also cause the logfile to be added to the :keypath:`tool, <tool>,
            task, <task>, report` parameter for those metrics, if not already present.""")

    # Configuration: cli-option, tcl var, env var, file
    scparam(cfg, ['tool', tool, 'task', task, 'option'],
            sctype='[str]',
            pernode='optional',
            shorthelp="Task: executable options",
            switch="-tool_task_option 'tool task <str>'",
            example=[
                "cli: -tool_task_option 'openroad cts -no_init'",
                "api: chip.set('tool', 'openroad', 'task', 'cts', 'option', '-no_init')"],
            schelp="""
            List of command line options for the task executable, specified on
            a per task and per step basis. Options must not include spaces.
            For multiple argument options, each option is a separate list element.
            """)

    scparam(cfg, ['tool', tool, 'task', task, 'var', key],
            sctype='[str]',
            pernode='optional',
            shorthelp="Task: script variables",
            switch="-tool_task_var 'tool task key <str>'",
            example=[
                "cli: -tool_task_var 'openroad cts myvar 42'",
                "api: chip.set('tool', 'openroad', 'task', 'cts', 'var', 'myvar', '42')"],
            schelp="""
            Task script variables specified as key value pairs. Variable
            names and value types must match the name and type of task and reference
            script consuming the variable.""")

    scparam(cfg, ['tool', tool, 'task', task, 'env', key],
            sctype='str',
            pernode='optional',
            shorthelp="Task: environment variables",
            switch="-tool_task_env 'tool task env <str>'",
            example=[
                "cli: -tool_task_env 'openroad cts MYVAR 42'",
                "api: chip.set('tool', 'openroad', 'task', 'cts', 'env', 'MYVAR', '42')"],
            schelp="""
            Environment variables to set for individual tasks. Keys and values
            should be set in accordance with the task's documentation. Most
            tasks do not require extra environment variables to function.""")

    scparam(cfg, ['tool', tool, 'task', task, 'file', key],
            sctype='[file]',
            pernode='optional',
            shorthelp="Task: setup files",
            switch="-tool_task_file 'tool task key <file>'",
            example=[
                "cli: -tool_task_file 'openroad floorplan macroplace macroplace.tcl'",
                "api: chip.set('tool', 'openroad', 'task', 'floorplan', 'file', 'macroplace', "
                    "'macroplace.tcl')"],
            schelp="""
            Paths to user supplied files mapped to keys. Keys and filetypes must
            match what's expected by the task/reference script consuming the
            file.
            """)

    scparam(cfg, ['tool', tool, 'task', task, 'dir', key],
            sctype='[dir]',
            pernode='optional',
            shorthelp="Task: setup directories",
            switch="-tool_task_dir 'tool task key <dir>'",
            example=[
                "cli: -tool_task_dir 'verilator compile cincludes include'",
                "api: chip.set('tool', 'verilator', 'task', 'compile', 'dir', 'cincludes', "
                    "'include')"],
            schelp="""
            Paths to user supplied directories mapped to keys. Keys must match
            what's expected by the task/reference script consuming the
            directory.
            """)

    # Definitions of inputs, outputs, requirements
    scparam(cfg, ['tool', tool, 'task', task, 'input'],
            sctype='[file]',
            pernode='required',
            shorthelp="Task: inputs",
            switch="-tool_task_input 'tool task <file>'",
            example=[
                "cli: -tool_task_input 'openroad place place 0 oh_add.def'",
                "api: chip.set('tool', 'openroad', 'task', 'place', 'input', 'oh_add.def', "
                    "step='place', index='0')"],
            schelp="""
            List of data files to be copied from previous flowgraph steps 'output'
            directory. The list of steps to copy files from is defined by the
            list defined by the dictionary key ['flowgraph', step, index, 'input'].
            All files must be available for flow to continue. If a file
            is missing, the program exists on an error.""")

    scparam(cfg, ['tool', tool, 'task', task, 'output'],
            sctype='[file]',
            pernode='required',
            shorthelp="Task: outputs",
            switch="-tool_task_output 'tool task <file>'",
            example=[
                "cli: -tool_task_output 'openroad place place 0 oh_add.def'",
                "api: chip.set('tool', 'openroad', 'task', 'place', 'output', 'oh_add.def', "
                    "step='place', index='0')"],
            schelp="""
            List of data files written to the 'output' directory of the
            tool/task/step/index used in the keypath. All files must be available
            for flow to continue. If a file is missing, the program exists on an error.""")

    dest_enum = ['log', 'output', 'none']
    scparam(cfg, ['tool', tool, 'task', task, 'stdout', 'destination'],
            sctype='enum',
            enum=dest_enum,
            defvalue='log',
            scope='job',
            pernode='optional',
            shorthelp="Task: Destination for stdout",
            switch="-tool_task_stdout_destination 'tool task <str>'",
            example=["cli: -tool_task_stdout_destination 'ghdl import log'",
                     "api: chip.set('tool', 'ghdl', 'task', 'import', 'stdout', 'destination', "
                     "'log')"],
            schelp="""
            Defines where to direct the output generated over stdout.
            Supported options are:
            none: the stream generated to STDOUT is ignored.
            log: the generated stream is stored in <step>.<suffix>; if not in quiet mode,
            it is additionally dumped to the display.
            output: the generated stream is stored in outputs/<design>.<suffix>.""")

    scparam(cfg, ['tool', tool, 'task', task, 'stdout', 'suffix'],
            sctype='str',
            defvalue='log',
            scope='job',
            pernode='optional',
            shorthelp="Task: File suffix for redirected stdout",
            switch="-tool_task_stdout_suffix 'tool task <str>'",
            example=["cli: -tool_task_stdout_suffix 'ghdl import log'",
                     "api: chip.set('tool', ghdl', 'task', 'import', 'stdout', 'suffix', 'log')"],
            schelp="""
            Specifies the file extension for the content redirected from stdout.""")

    scparam(cfg, ['tool', tool, 'task', task, 'stderr', 'destination'],
            sctype='enum',
            enum=dest_enum,
            defvalue='log',
            scope='job',
            pernode='optional',
            shorthelp="Task: Destination for stderr",
            switch="-tool_task_stderr_destination 'tool task <str>'",
            example=["cli: -tool_task_stderr_destination 'ghdl import log'",
                     "api: chip.set('tool', ghdl', 'task', 'import', 'stderr', 'destination', "
                     "'log')"],
            schelp="""
            Defines where to direct the output generated over stderr.
            Supported options are:
            none: the stream generated to STDERR is ignored
            log: the generated stream is stored in <step>.<suffix>; if not in quiet mode,
            it is additionally dumped to the display.
            output: the generated stream is stored in outputs/<design>.<suffix>""")

    scparam(cfg, ['tool', tool, 'task', task, 'stderr', 'suffix'],
            sctype='str',
            defvalue='log',
            scope='job',
            pernode='optional',
            shorthelp="Task: File suffix for redirected stderr",
            switch="-tool_task_stderr_suffix 'tool task <str>'",
            example=["cli: -tool_task_stderr_suffix 'ghdl import log'",
                     "api: chip.set('tool', 'ghdl', 'task', 'import', 'stderr', 'suffix', 'log')"],
            schelp="""
            Specifies the file extension for the content redirected from stderr.""")

    scparam(cfg, ['tool', tool, 'task', task, 'require'],
            sctype='[str]',
            pernode='optional',
            shorthelp="Task: parameter requirements",
            switch="-tool_task_require 'tool task <str>'",
            example=[
                "cli: -tool_task_require 'openroad cts design'",
                "api: chip.set('tool', 'openroad', 'task', 'cts', 'require', 'design')"],
            schelp="""
            List of keypaths to required task parameters. The list is used
            by check_manifest() to verify that all parameters have been set up before
            step execution begins.""")

    metric = 'default'
    scparam(cfg, ['tool', tool, 'task', task, 'report', metric],
            sctype='[file]',
            pernode='required',
            shorthelp="Task: reports",
            switch="-tool_task_report 'tool task metric <file>'",
            example=[
                "cli: -tool_task_report 'openroad place holdtns place 0 place.log'",
                "api: chip.set('tool', 'openroad', 'task', 'place', 'report', 'holdtns', "
                    "'place.log', step='place', index='0')"],
            schelp="""
            List of report files associated with a specific 'metric'. The file path
            specified is relative to the run directory of the current task.""")

    scparam(cfg, ['tool', tool, 'task', task, 'refdir'],
            sctype='[dir]',
            pernode='optional',
            shorthelp="Task: script directory",
            switch="-tool_task_refdir 'tool task <dir>'",
            example=[
                "cli: -tool_task_refdir 'yosys syn ./myref'",
                "api: chip.set('tool', 'yosys', 'task', 'syn_asic', 'refdir', './myref')"],
            schelp="""
            Path to directories containing reference flow scripts, specified
            on a per step and index basis.""")

    scparam(cfg, ['tool', tool, 'task', task, 'script'],
            sctype='[file]',
            pernode='optional',
            shorthelp="Task: entry script",
            switch="-tool_task_script 'tool task <file>'",
            example=[
                "cli: -tool_task_script 'yosys syn syn.tcl'",
                "api: chip.set('tool', 'yosys', 'task', 'syn_asic', 'script', 'syn.tcl')"],
            schelp="""
            Path to the entry script called by the executable specified
            on a per task and per step basis.""")

    scparam(cfg, ['tool', tool, 'task', task, 'prescript'],
            sctype='[file]',
            pernode='optional',
            shorthelp="Task: pre-step script",
            switch="-tool_task_prescript 'tool task <file>'",
            example=[
                "cli: -tool_task_prescript 'yosys syn syn_pre.tcl'",
                "api: chip.set('tool', 'yosys', 'task', 'syn_asic', 'prescript', 'syn_pre.tcl')"],
            schelp="""
            Path to a user supplied script to execute after reading in the design
            but before the main execution stage of the step. Exact entry point
            depends on the step and main script being executed. An example
            of a prescript entry point would be immediately before global
            placement.""")

    scparam(cfg, ['tool', tool, 'task', task, 'postscript'],
            sctype='[file]',
            pernode='optional',
            shorthelp="Task: post-step script",
            switch="-tool_task_postscript 'tool task <file>'",
            example=[
                "cli: -tool_task_postscript 'yosys syn syn_post.tcl'",
                "api: chip.set('tool', 'yosys', 'task', 'syn_asic', 'postscript', 'syn_post.tcl')"],
            schelp="""
            Path to a user supplied script to execute after the main execution
            stage of the step but before the design is saved.
            Exact entry point depends on the step and main script being
            executed. An example of a postscript entry point would be immediately
            after global placement.""")

    scparam(cfg, ['tool', tool, 'task', task, 'threads'],
            sctype='int',
            pernode='optional',
            shorthelp="Task: thread parallelism",
            switch="-tool_task_threads 'tool task <int>'",
            example=["cli: -tool_task_threads 'magic drc 64'",
                     "api: chip.set('tool', 'magic', 'task', 'drc', 'threads', '64')"],
            schelp="""
            Thread parallelism to use for execution specified on a per task and per
            step basis. If not specified, SC queries the operating system and sets
            the threads based on the maximum thread count supported by the
            hardware.""")

    return cfg


###########################################################################
# Function arguments
###########################################################################
def schema_arg(cfg):

    scparam(cfg, ['arg', 'step'],
            sctype='str',
            scope='scratch',
            shorthelp="ARG: Step argument",
            switch="-arg_step <str>",
            example=["cli: -arg_step 'route'",
                     "api: chip.set('arg', 'step', 'route')"],
            schelp="""
            Dynamic parameter passed in by the SC runtime as an argument to
            a runtime task. The parameter enables configuration code
            (usually TCL) to use control flow that depend on the current
            'step'. The parameter is used the run() function and
            is not intended for external use.""")

    scparam(cfg, ['arg', 'index'],
            sctype='str',
            scope='scratch',
            shorthelp="ARG: Index argument",
            switch="-arg_index <str>",
            example=["cli: -arg_index 0",
                     "api: chip.set('arg', 'index', '0')"],
            schelp="""
            Dynamic parameter passed in by the SC runtime as an argument to
            a runtime task. The parameter enables configuration code
            (usually TCL) to use control flow that depend on the current
            'index'. The parameter is used the run() function and
            is not intended for external use.""")

    return cfg


###########################################################################
# Metrics to Track
###########################################################################
def schema_metric(cfg, step='default', index='default'):

    metrics = {'errors': 'errors',
               'warnings': 'warnings',
               'drvs': 'design rule violations',
               'drcs': 'physical design rule violations',
               'unconstrained': 'unconstrained timing paths'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', item],
                sctype='int',
                shorthelp=f"Metric: total {item}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'dfm 0 0'",
                    f"api: chip.set('metric', '{item}', 0, step='dfm', index=0)"],
                pernode='required',
                schelp=f"""Metric tracking the total number of {val} on a
                per step and index basis.""")

    scparam(cfg, ['metric', 'coverage'],
            sctype='float',
            unit='%',
            shorthelp="Metric: coverage",
            switch="-metric_coverage 'step index <float>'",
            example=[
                "cli: -metric_coverage 'place 0 99.9'",
                "api: chip.set('metric', 'coverage', 99.9, step='place', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking the test coverage in the design expressed as a percentage
            with 100 meaning full coverage. The meaning of the metric depends on the
            task being executed. It can refer to code coverage, feature coverage,
            stuck at fault coverage.""")

    scparam(cfg, ['metric', 'security'],
            sctype='float',
            unit='%',
            shorthelp="Metric: security",
            switch="-metric_security 'step index <float>'",
            example=[
                "cli: -metric_security 'place 0 100'",
                "api: chip.set('metric', 'security', 100, step='place', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking the level of security (1/vulnerability) of the design.
            A completely secure design would have a score of 100. There is no
            absolute scale for the security metrics (like with power, area, etc)
            so the metric will be task and tool dependent.""")

    metrics = {'luts': 'FPGA LUTs used',
               'dsps': 'FPGA DSP slices used',
               'brams': 'FPGA BRAM tiles used'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', item],
                sctype='int',

                shorthelp=f"Metric: {val}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100'",
                    f"api: chip.set('metric', '{item}', 100, step='place', index=0)"],
                pernode='required',
                schelp=f"""
                Metric tracking the total {val} used by the design as reported
                by the implementation tool. There is no standardized definition
                for this metric across vendors, so metric comparisons can
                generally only be done between runs on identical tools and
                device families.""")

    metrics = {'cellarea': 'cell area (ignoring fillers)',
               'totalarea': 'physical die area'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', item],
                sctype='float',
                unit='um^2',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100.00'",
                    f"api: chip.set('metric', '{item}', 100.00, step='place', index=0)"],
                pernode='required',
                schelp=f"""
                Metric tracking the total {val} occupied by the design.""")

    scparam(cfg, ['metric', 'utilization'],
            sctype='float',
            unit='%',
            shorthelp="Metric: area utilization",
            switch="-metric_utilization step index <float>",
            example=[
                "cli: -metric_utilization 'place 0 50.00'",
                "api: chip.set('metric', 'utilization', 50.00, step='place', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking the area utilization of the design calculated as
            100 * (cellarea/totalarea).""")

    scparam(cfg, ['metric', 'logicdepth'],
            sctype='int',
            shorthelp="Metric: logic depth",
            switch="-metric_logicdepth step index <int>",
            example=[
                "cli: -metric_logicdepth 'place 0 8'",
                "api: chip.set('metric', 'logicdepth', 8, step='place', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking the logic depth of the design. This is determined
            by the number of logic gates between the start of the critital timing
            path to the end of the path.""")

    metrics = {'peakpower': 'worst case total peak power',
               'averagepower': 'average workload power',
               'leakagepower': 'leakage power with rails active but without any dynamic '
                               'switching activity'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', item],
                sctype='float',
                unit='mw',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 0.01'",
                    f"api: chip.set('metric', '{item}', 0.01, step='place', index=0)"],
                pernode='required',
                schelp=f"""
                Metric tracking the {val} of the design specified on a per step
                and index basis. Power metric depend heavily on the method
                being used for extraction: dynamic vs static, workload
                specification (vcd vs saif), power models, process/voltage/temperature.
                The power {item} metric tries to capture the data that would
                usually be reflected inside a datasheet given the appropriate
                footnote conditions.""")

    scparam(cfg, ['metric', 'irdrop'],
            sctype='float',
            unit='mv',
            shorthelp="Metric: peak IR drop",
            switch="-metric_irdrop 'step index <float>'",
            example=[
                "cli: -metric_irdrop 'place 0 0.05'",
                "api: chip.set('metric', 'irdrop', 0.05, step='place', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking the peak IR drop in the design based on extracted
            power and ground rail parasitics, library power models, and
            switching activity. The switching activity calculated on a per
            node basis is taken from one of three possible sources, in order
            of priority: VCD file, SAIF file, 'activityfactor' parameter.""")

    metrics = {'holdpaths': 'hold',
               'setuppaths': 'setup'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', item],
                sctype='int',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'place 0 10'",
                    f"api: chip.set('metric', '{item}', 10, step='place', index=0)"],
                pernode='required',
                schelp=f"""
                Metric tracking the total number of timing paths violating {val}
                constraints.""")

    metrics = {'holdslack': 'worst hold slack (positive or negative)',
               'holdwns': 'worst negative hold slack (positive values truncated to zero)',
               'holdtns': 'total negative hold slack (TNS)',
               'holdskew': 'hold clock skew',
               'setupslack': 'worst setup slack (positive or negative)',
               'setupwns': 'worst negative setup slack (positive values truncated to zero)',
               'setuptns': 'total negative setup slack (TNS)',
               'setupskew': 'setup clock skew'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', item],
                sctype='float',
                unit='ns',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 0.01'",
                    f"api: chip.set('metric', '{item}', 0.01, step='place', index=0)"],
                pernode='required',
                schelp=f"""
                Metric tracking the {val} on a per step and index basis.""")

    metrics = {'fmax': 'maximum clock frequency'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', item],
                sctype='float',
                unit='Hz',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100e6'",
                    f"api: chip.set('metric', '{item}', 100e6, step='place', index=0)"],
                pernode='required',
                schelp=f"""
                Metric tracking the {val} on a per step and index basis.""")

    metrics = {'macros': 'macros',
               'cells': 'cell instances',
               'registers': 'register instances',
               'buffers': 'buffer instances',
               'inverters': 'inverter instances',
               'transistors': 'transistors',
               'pins': 'pins',
               'nets': 'nets',
               'vias': 'vias'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', item],
                sctype='int',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100'",
                    f"api: chip.set('metric', '{item}', 50, step='place', index=0)"],
                pernode='required',
                schelp=f"""
                Metric tracking the total number of {val} in the design
                on a per step and index basis.""")

    item = 'wirelength'
    scparam(cfg, ['metric', item],
            sctype='float',
            unit='um',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'place 0 100.0'",
                f"api: chip.set('metric', '{item}', 50.0, step='place', index=0)"],
            pernode='required',
            schelp=f"""
            Metric tracking the total {item} of the design on a per step
            and index basis.""")

    item = 'overflow'
    scparam(cfg, ['metric', item],
            sctype='int',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <int>'",
            example=[
                f"cli: -metric_{item} 'place 0 0'",
                f"api: chip.set('metric', '{item}', 50, step='place', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking the total number of overflow tracks for the routing
            on per step and index basis. Any non-zero number suggests an over
            congested design. To analyze where the congestion is occurring
            inspect the router log files for detailed per metal overflow
            reporting and open up the design to find routing hotspots.""")

    item = 'memory'
    scparam(cfg, ['metric', item],
            sctype='float',
            unit='B',
            scope='job',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 10e9'",
                f"api: chip.set('metric', '{item}', 10e9, step='dfm', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking total peak program memory footprint on a per
            step and index basis.""")

    item = 'exetime'
    scparam(cfg, ['metric', item],
            sctype='float',
            unit='s',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 10.0'",
                f"api: chip.set('metric', '{item}', 10.0, step='dfm', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking time spent by the EDA executable 'exe' on a
            per step and index basis. It does not include the SiliconCompiler
            runtime overhead or time waiting for I/O operations and
            inter-processor communication to complete.""")

    item = 'tasktime'
    scparam(cfg, ['metric', item],
            sctype='float',
            unit='s',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 10.0'",
                f"api: chip.set('metric', '{item}', 10.0, step='dfm', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking the total amount of time spent on a task from
            beginning to end, including data transfers and pre/post
            processing.""")

    item = 'totaltime'
    scparam(cfg, ['metric', item],
            sctype='float',
            unit='s',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 10.0'",
                f"api: chip.set('metric', '{item}', 10.0, step='dfm', index=0)"],
            pernode='required',
            schelp="""
            Metric tracking the total amount of time spent from the beginning
            of the run up to and including the current step and index.""")

    return cfg


###########################################################################
# Design Tracking
###########################################################################
def schema_record(cfg, step='default', index='default'):

    # setting up local data structure
    # <key> : ['short help', 'example' 'extended help']

    records = {'userid': ['userid',
                          'wiley',
                          ''],
               'publickey': ['public key',
                             '<key>',
                             ''],
               'machine': ['machine name',
                           'carbon',
                           '(myhost, localhost, ...'],
               'macaddr': ['MAC address',
                           '<addr>',
                           ''],
               'ipaddr': ['IP address',
                          '<addr>',
                          ''],
               'platform': ['platform name',
                            'linux',
                            '(linux, windows, freebsd)'],
               'distro': ['distro name',
                          'ubuntu',
                          '(ubuntu, redhat, centos)'],
               'arch': ['hardware architecture',
                        'x86_64',
                        '(x86_64, rv64imafdc)'],
               'starttime': ['start time',
                             '2021-09-06 12:20:20',
                             'Time is reported in the ISO 8601 format YYYY-MM-DD HR:MIN:SEC'],
               'endtime': ['end time',
                           '2021-09-06 12:20:20',
                           'Time is reported in the ISO 8601 format YYYY-MM-DD HR:MIN:SEC'],
               'region': ['cloud region',
                          'US Gov Boston',
                          """Recommended naming methodology:

                          * local: node is the local machine
                          * onprem: node in on-premises IT infrastructure
                          * public: generic public cloud
                          * govcloud: generic US government cloud
                          * <region>: cloud and entity specific region string name
                          """],
               'scversion': ['software version',
                             '1.0',
                             """Version number for the SiliconCompiler software."""],
               'toolversion': ['tool version',
                               '1.0',
                               """The tool version captured corresponds to the 'tool'
                               parameter within the 'tool' dictionary."""],
               'toolpath': ['tool path',
                            '/usr/bin/openroad',
                            """Full path to tool executable used to run this
                            task."""],
               'toolargs': ['tool CLI arguments',
                            '-I include/ foo.v',
                            'Arguments passed to tool via CLI.'],
               'osversion': ['O/S version',
                             '20.04.1-Ubuntu',
                             """Since there is not standard version system for operating
                             systems, extracting information from is platform dependent.
                             For Linux based operating systems, the 'osversion' is the
                             version of the distro."""],
               'kernelversion': ['O/S kernel version',
                                 '5.11.0-34-generic',
                                 """Used for platforms that support a distinction
                                 between os kernels and os distributions."""]}

    for item, val in records.items():
        helpext = trim(val[2])
        scparam(cfg, ['record', item],
                sctype='str',
                shorthelp=f"Record: {val[0]}",
                switch=f"-record_{item} 'step index <str>'",
                example=[
                    f"cli: -record_{item} 'dfm 0 {val[1]}'",
                    f"api: chip.set('record', '{item}', '{val[1]}', step='dfm', index=0)"],
                pernode='required',
                schelp=f'Record tracking the {val[0]} per step and index basis. {helpext}')

    scparam(cfg, ['record', 'toolexitcode'],
            sctype='int',
            shorthelp="Record: tool exit code",
            switch="-record_toolexitcode 'step index <int>'",
            example=[
                "cli: -record_toolexitcode 'dfm 0 0'",
                "api: chip.set('record', 'toolexitcode', 0, step='dfm', index=0)"],
            pernode='required',
            schelp='Record tracking the tool exit code per step and index basis.')

    # Unlike most other 'record' fields, job ID is not set per-node.
    scparam(cfg, ['record', 'remoteid'],
            sctype='str',
            shorthelp="Record: remote job ID",
            switch="-record_remoteid 'step index <str>'",
            example=[
                "cli: -record_remoteid '0123456789abcdeffedcba9876543210'",
                "api: chip.set('record', 'remoteid', '0123456789abcdeffedcba9876543210')"],
            schelp='Record tracking the job ID for a remote run.')

    # flowgraph status
    scparam(cfg, ['record', 'status'],
            sctype='enum',
            pernode='required',
            enum=[  # keep in sync with NodeStatus
                "pending",
                "queued",
                "running",
                "success",
                "error",
                "skipped",
                "timeout"],
            shorthelp="Record: node execution status",
            switch="-record_status 'step index <str>'",
            example=[
                "cli: -record_status 'syn 0 success'",
                "api: chip.set('record', 'status', 'success', step='syn', index='0')"],
            schelp="""Record tracking for the status of a node.""")

    # flowgraph select
    scparam(cfg, ['record', 'inputnode'],
            sctype='[(str,str)]',
            pernode='required',
            shorthelp="Record: node inputs",
            switch="-record_inputnode 'step index <(str,str)>'",
            example=[
                "cli: -record_inputnode 'cts 0 (place,42)'",
                "api: chip.set('record', 'inputnode', ('place', '42'), step='syn', index='0')"],
            schelp="""
            List of selected inputs for the current step/index specified as
            (in_step, in_index) tuple.""")

    return cfg


###########################################################################
# Run Options
###########################################################################
def schema_option(cfg):
    ''' Technology agnostic run time options
    '''

    scparam(cfg, ['option', 'remote'],
            sctype='bool',
            scope='job',
            shorthelp="Enable remote processing",
            switch="-remote <bool>",
            example=[
                "cli: -remote",
                "api: chip.set('option', 'remote', True)"],
            schelp="""
            Sends job for remote processing if set to true. The remote
            option requires a credentials file to be placed in the home
            directory. Fore more information, see the credentials
            parameter.""")

    scparam(cfg, ['option', 'credentials'],
            sctype='file',
            scope='job',
            shorthelp="User credentials file",
            switch="-credentials <file>",
            example=[
                "cli: -credentials /home/user/.sc/credentials",
                "api: chip.set('option', 'credentials', '/home/user/.sc/credentials')"],
            schelp="""
            Filepath to credentials used for remote processing. If the
            credentials parameter is empty, the remote processing client program
            tries to access the ".sc/credentials" file in the user's home
            directory. The file supports the following fields:

            address=<server address>

            port=<server port> (optional)

            username=<user id> (optional)

            password=<password / key used for authentication> (optional)""")

    scparam(cfg, ['option', 'cachedir'],
            sctype='file',
            scope='job',
            shorthelp="User cache directory",
            switch="-cachedir <file>",
            example=[
                "cli: -cachedir /home/user/.sc/cache",
                "api: chip.set('option', 'cachedir', '/home/user/.sc/cache')"],
            schelp="""
            Filepath to cache used for package data sources. If the
            cache parameter is empty, ".sc/cache" directory in the user's home
            directory will be used.""")

    scparam(cfg, ['option', 'nice'],
            sctype='int',
            scope='job',
            pernode='optional',
            shorthelp="Tool execution scheduling priority",
            switch="-nice <int>",
            example=[
                "cli: -nice 5",
                "api: chip.set('option', 'nice', 5)"],
            schelp="""
            Sets the type of execution priority of each individual flowgraph steps.
            If the parameter is undefined, nice will not be used. For more information see
            `Unix 'nice' <https://en.wikipedia.org/wiki/Nice_(Unix)>`_.""")

    # Compilation
    scparam(cfg, ['option', 'target'],
            sctype='str',
            scope='job',
            shorthelp="Compilation target",
            switch="-target <str>",
            example=["cli: -target freepdk45_demo",
                     "api: chip.set('option', 'target', 'freepdk45_demo')"],
            schelp="""
            Sets a target module to be used for compilation. The target
            module must set up all parameters needed. The target module
            may load multiple flows and libraries.
            """)

    scparam(cfg, ['option', 'pdk'],
            sctype='str',
            scope='job',
            shorthelp="PDK target",
            switch="-pdk <str>",
            example=["cli: -pdk freepdk45",
                     "api: chip.set('option', 'pdk', 'freepdk45')"],
            schelp="""
            Target PDK used during compilation.""")

    scparam(cfg, ['option', 'stackup'],
            sctype='str',
            scope='job',
            shorthelp="Stackup target",
            switch="-stackup <str>",
            example=["cli: -stackup 2MA4MB2MC",
                     "api: chip.set('option', 'stackup', '2MA4MB2MC')"],
            schelp="""
            Target stackup used during compilation. The stackup is required
            parameter for PDKs with multiple metal stackups.""")

    scparam(cfg, ['option', 'flow'],
            sctype='str',
            scope='job',
            shorthelp="Flow target",
            switch="-flow <str>",
            example=["cli: -flow asicflow",
                     "api: chip.set('option', 'flow', 'asicflow')"],
            schelp="""
            Sets the flow for the current run. The flow name
            must match up with a 'flow' in the flowgraph""")

    scparam(cfg, ['option', 'optmode'],
            sctype='str',
            pernode='optional',
            scope='job',
            defvalue='O0',
            shorthelp="Optimization mode",
            switch=["-O<str>",
                    "-optmode <str>"],
            example=["cli: -O3",
                     "cli: -optmode O3",
                     "api: chip.set('option', 'optmode', 'O3')"],
            schelp="""
            The compiler has modes to prioritize run time and ppa. Modes
            include.

            (O0) = Exploration mode for debugging setup
            (O1) = Higher effort and better PPA than O0
            (O2) = Higher effort and better PPA than O1
            (O3) = Signoff quality. Better PPA and higher run times than O2
            (O4-O98) = Reserved (compiler/target dependent)
            (O99) = Experimental highest possible effort, may be unstable
            """)

    scparam(cfg, ['option', 'cfg'],
            sctype='[file]',
            scope='job',
            shorthelp="Configuration manifest",
            switch="-cfg <file>",
            example=["cli: -cfg mypdk.json",
                     "api: chip.set('option', 'cfg', 'mypdk.json')"],
            schelp="""
            List of filepaths to JSON formatted schema configuration
            manifests. The files are read in automatically when using the
            'sc' command line application. In Python programs, JSON manifests
            can be merged into the current working manifest using the
            read_manifest() method.""")

    key = 'default'
    scparam(cfg, ['option', 'env', key],
            sctype='str',
            scope='job',
            shorthelp="Environment variables",
            switch="-env 'key <str>'",
            example=[
                "cli: -env 'PDK_HOME /disk/mypdk'",
                "api: chip.set('option', 'env', 'PDK_HOME', '/disk/mypdk')"],
            schelp="""
            Certain tools and reference flows require global environment
            variables to be set. These variables can be managed externally or
            specified through the env variable.""")

    scparam(cfg, ['option', 'var', key],
            sctype='[str]',
            scope='job',
            shorthelp="Custom variables",
            switch="-var 'key <str>'",
            example=[
                "cli: -var 'openroad_place_density 0.4'",
                "api: chip.set('option', 'var', 'openroad_place_density', '0.4')"],
            schelp="""
            List of key/value strings specified. Certain tools and
            reference flows require special parameters, this
            should only be used for specifying variables that are
            not directly supported by the SiliconCompiler schema.""")

    scparam(cfg, ['option', 'file', key],
            sctype='[file]',
            scope='job',
            shorthelp="Custom files",
            switch="-file 'key <file>'",
            example=[
                "cli: -file 'openroad_tapcell ./tapcell.tcl'",
                "api: chip.set('option', 'file', 'openroad_tapcell', './tapcell.tcl')"],
            schelp="""
            List of named files specified. Certain tools and
            reference flows require special parameters, this
            parameter should only be used for specifying files that are
            not directly supported by the schema.""")

    scparam(cfg, ['option', 'dir', key],
            sctype='[dir]',
            scope='job',
            shorthelp="Custom directories",
            switch="-dir 'key <dir>'",
            example=[
                "cli: -dir 'openroad_tapcell ./tapcell.tcl'",
                "api: chip.set('option', 'dir', 'openroad_files', './openroad_support/')"],
            schelp="""
            List of named directories specified. Certain tools and
            reference flows require special parameters, this
            parameter should only be used for specifying directories that are
            not directly supported by the schema.""")

    scparam(cfg, ['option', 'loglevel'],
            sctype='enum',
            enum=["info", "warning", "error", "critical", "debug"],
            pernode='optional',
            scope='job',
            defvalue='info',
            shorthelp="Logging level",
            switch="-loglevel <str>",
            example=[
                "cli: -loglevel info",
                "api: chip.set('option', 'loglevel', 'info')"],
            schelp="""
            Provides explicit control over the level of debug logging printed.""")

    scparam(cfg, ['option', 'builddir'],
            sctype='dir',
            scope='job',
            defvalue='build',
            shorthelp="Build directory",
            switch="-builddir <dir>",
            example=[
                "cli: -builddir ./build_the_future",
                "api: chip.set('option', 'builddir', './build_the_future')"],
            schelp="""
            The default build directory is in the local './build' where SC was
            executed. The 'builddir' parameter can be used to set an alternate
            compilation directory path.""")

    scparam(cfg, ['option', 'jobname'],
            sctype='str',
            scope='job',
            defvalue='job0',
            shorthelp="Job name",
            switch="-jobname <str>",
            example=[
                "cli: -jobname may1",
                "api: chip.set('option', 'jobname', 'may1')"],
            schelp="""
            Jobname during invocation of run(). The jobname combined with a
            defined director structure (<dir>/<design>/<jobname>/<step>/<index>)
            enables multiple levels of transparent job, step, and index
            introspection.""")

    scparam(cfg, ['option', 'from'],
            sctype='[str]',
            scope='job',
            shorthelp="Start flowgraph execution from",
            switch="-from <str>",
            example=[
                "cli: -from 'import'",
                "api: chip.set('option', 'from', 'import')"],
            schelp="""
            Inclusive list of steps to start execution from. The default is to start
            at all entry steps in the flow graph.""")

    scparam(cfg, ['option', 'to'],
            sctype='[str]',
            scope='job',
            shorthelp="End flowgraph execution with",
            switch="-to <str>",
            example=[
                "cli: -to 'syn'",
                "api: chip.set('option', 'to', 'syn')"],
            schelp="""
            Inclusive list of steps to end execution with. The default is to go
            to all exit steps in the flow graph.""")

    scparam(cfg, ['option', 'prune'],
            sctype='[(str,str)]',
            scope='job',
            shorthelp="Prune flowgraph branches starting with",
            switch="-prune 'node <(str,str)>'",
            example=[
                "cli: -prune (syn,0)",
                "api: chip.set('option', 'prune', ('syn', '0'))"],
            schelp="""
            List of starting nodes for branches to be pruned.
            The default is to not prune any nodes/branches.""")

    scparam(cfg, ['option', 'breakpoint'],
            sctype='bool',
            scope='job',
            pernode='optional',
            shorthelp="Breakpoint list",
            switch="-breakpoint <bool>",
            example=[
                "cli: -breakpoint true",
                "api: chip.set('option, 'breakpoint', True)"],
            schelp="""
            Set a breakpoint on specific steps. If the step is a TCL
            based tool, then the breakpoints stops the flow inside the
            EDA tool. If the step is a command line tool, then the flow
            drops into a Python interpreter.""")

    scparam(cfg, ['option', 'library'],
            sctype='[str]',
            scope='job',
            pernode='optional',
            shorthelp="Soft libraries",
            switch="-library <str>",
            example=["cli: -library lambdalib_asap7",
                     "api: chip.set('option', 'library', 'lambdalib_asap7')"],
            schelp="""
            List of soft libraries to be linked in during import.""")

    # Booleans
    scparam(cfg, ['option', 'clean'],
            sctype='bool',
            scope='job',
            shorthelp="Start a job from the beginning",
            switch="-clean <bool>",
            example=["cli: -clean",
                     "api: chip.set('option', 'clean', True)"],
            schelp="""
            Run a job from the start and do not use any of the previous job.
            If :keypath:`option, jobincr` is True, the old job is preserved and
            a new job number is assigned.
            """)

    scparam(cfg, ['option', 'hash'],
            sctype='bool',
            scope='job',
            shorthelp="Enable file hashing",
            switch="-hash <bool>",
            example=["cli: -hash",
                     "api: chip.set('option', 'hash', True)"],
            schelp="""
            Enables hashing of all inputs and outputs during
            compilation. The hash values are stored in the hashvalue
            field of the individual parameters.""")

    scparam(cfg, ['option', 'nodisplay'],
            sctype='bool',
            scope='job',
            shorthelp="Headless execution",
            switch="-nodisplay <bool>",
            example=["cli: -nodisplay",
                     "api: chip.set('option', 'nodisplay', True)"],
            schelp="""
            The '-nodisplay' flag prevents SiliconCompiler from
            opening GUI windows such as the final metrics report.""")

    scparam(cfg, ['option', 'quiet'],
            sctype='bool',
            pernode='optional',
            scope='job',
            shorthelp="Quiet execution",
            switch="-quiet <bool>",
            example=["cli: -quiet",
                     "api: chip.set('option', 'quiet', True)"],
            schelp="""
            The -quiet option forces all steps to print to a log file.
            This can be useful with Modern EDA tools which print
            significant content to the screen.""")

    scparam(cfg, ['option', 'jobincr'],
            sctype='bool',
            scope='job',
            shorthelp="Autoincrement jobname",
            switch="-jobincr <bool>",
            example=["cli: -jobincr",
                     "api: chip.set('option', 'jobincr', True)"],
            schelp="""
            Forces an auto-update of the jobname parameter if a directory
            matching the jobname is found in the build directory. If the
            jobname does not include a trailing digit, then the number
            '1' is added to the jobname before updating the jobname
            parameter.""")

    scparam(cfg, ['option', 'novercheck'],
            sctype='bool',
            pernode='optional',
            defvalue=False,
            scope='job',
            shorthelp="Disable version checking",
            switch="-novercheck <bool>",
            example=["cli: -novercheck",
                     "api: chip.set('option', 'novercheck', True)"],
            schelp="""
            Disables strict version checking on all invoked tools if True.
            The list of supported version numbers is defined in the
            'version' parameter in the 'tool' dictionary for each tool.""")

    scparam(cfg, ['option', 'track'],
            sctype='bool',
            pernode='optional',
            scope='job',
            shorthelp="Enable provenance tracking",
            switch="-track <bool>",
            example=["cli: -track",
                     "api: chip.set('option', 'track', True)"],
            schelp="""
            Turns on tracking of all 'record' parameters during each
            task, otherwise only tool and runtime information will be recorded.
            Tracking will result in potentially sensitive data
            being recorded in the manifest so only turn on this feature
            if you have control of the final manifest.""")

    scparam(cfg, ['option', 'entrypoint'],
            sctype='str',
            pernode='optional',
            shorthelp="Program entry point",
            switch="-entrypoint <str>",
            example=["cli: -entrypoint top",
                     "api: chip.set('option', 'entrypoint', 'top')"],
            schelp="""Alternative entrypoint for compilation and
            simulation. The default entry point is 'design'.""")

    scparam(cfg, ['option', 'idir'],
            sctype='[dir]',
            shorthelp="Design search paths",
            switch=['+incdir+<dir>',
                    '-I <dir>',
                    '-idir <dir>'],
            example=[
                "cli: +incdir+./mylib",
                "cli: -I ./mylib",
                "cli: -idir ./mylib",
                "api: chip.set('option', 'idir', './mylib')"],
            schelp="""
            Search paths to look for files included in the design using
            the ```include`` statement.""")

    scparam(cfg, ['option', 'ydir'],
            sctype='[dir]',
            shorthelp="Design module search paths",
            switch=['-y <dir>',
                    '-ydir <dir>'],
            example=[
                "cli: -y './mylib'",
                "cli: -ydir './mylib'",
                "api: chip.set('option', 'ydir', './mylib')"],
            schelp="""
            Search paths to look for verilog modules found in the the
            source list. The import engine will look for modules inside
            files with the specified +libext+ param suffix.""")

    scparam(cfg, ['option', 'vlib'],
            sctype='[file]',
            shorthelp="Design libraries",
            switch=['-v <file>',
                    '-vlib <file>'],
            example=["cli: -v './mylib.v'",
                     "cli: -vlib './mylib.v'",
                     "api: chip.set('option', 'vlib', './mylib.v')"],
            schelp="""
            List of library files to be read in. Modules found in the
            libraries are not interpreted as root modules.""")

    scparam(cfg, ['option', 'define'],
            sctype='[str]',
            shorthelp="Design pre-processor symbol",
            switch=["-D<str>",
                    "-define <str>"],
            example=["cli: -DCFG_ASIC=1",
                     "cli: -define CFG_ASIC=1",
                     "api: chip.set('option', 'define', 'CFG_ASIC=1')"],
            schelp="""Symbol definition for source preprocessor.""")

    scparam(cfg, ['option', 'libext'],
            sctype='[str]',
            shorthelp="Design file extensions",
            switch=["+libext+<str>",
                    "-libext <str>"],
            example=[
                "cli: +libext+sv",
                "cli: -libext sv",
                "api: chip.set('option', 'libext', 'sv')"],
            schelp="""
            List of file extensions that should be used for finding modules.
            For example, if -y is specified as ./lib", and '.v' is specified as
            libext then the files ./lib/\\*.v ", will be searched for
            module matches.""")

    name = 'default'
    scparam(cfg, ['option', 'param', name],
            sctype='str',
            shorthelp="Design parameter",
            switch="-param 'name <str>'",
            example=[
                "cli: -param 'N 64'",
                "api: chip.set('option', 'param', 'N', '64')"],
            schelp="""
            Sets a top verilog level design module parameter. The value
            is limited to basic data literals. The parameter override is
            passed into tools such as Verilator and Yosys. The parameters
            support Verilog integer literals (64'h4, 2'b0, 4) and strings.
            Name of the top level module to compile.""")

    scparam(cfg, ['option', 'continue'],
            sctype='bool',
            pernode='optional',
            shorthelp='continue-on-error',
            switch='-continue <bool>',
            example=["cli: -continue",
                     "api: chip.set('option', 'continue', True)"],
            schelp="""
            Attempt to continue even when errors are encountered in the SC
            implementation. The default behavior is to quit executing the flow
            if a task ends and the errors metric is greater than 0. Note that
            the flow will always cease executing if the tool returns a nonzero
            status code.
            """)

    scparam(cfg, ['option', 'timeout'],
            sctype='float',
            pernode='optional',
            scope='job',
            unit='s',
            shorthelp="Option: Timeout value",
            switch="-timeout <float>",
            example=["cli: -timeout 3600",
                     "api: chip.set('option', 'timeout', 3600)"],
            schelp="""
            Timeout value in seconds. The timeout value is compared
            against the wall time tracked by the SC runtime to determine
            if an operation should continue. The timeout value is also
            used by the jobscheduler to automatically kill jobs.""")

    scparam(cfg, ['option', 'strict'],
            sctype='bool',
            shorthelp="Option: Strict checking",
            switch="-strict <bool>",
            example=["cli: -strict true",
                     "api: chip.set('option', 'strict', True)"],
            schelp="""
            Enable additional strict checking in the SC Python API. When this
            parameter is set to True, users must provide step and index keyword
            arguments when reading from parameters with the pernode field set to
            'optional'.""")

    # job scheduler
    scparam(cfg, ['option', 'scheduler', 'name'],
            sctype='enum',
            enum=["slurm", "lsf", "sge", "docker"],
            scope='job',
            pernode='optional',
            shorthelp="Option: Scheduler platform",
            switch="-scheduler <str>",
            example=[
                "cli: -scheduler slurm",
                "api: chip.set('option', 'scheduler', 'name', 'slurm')"],
            schelp="""
            Sets the type of job scheduler to be used for each individual
            flowgraph steps. If the parameter is undefined, the steps are executed
            on the same machine that the SC was launched on. If 'slurm' is used,
            the host running the 'sc' command must be running a 'slurmctld' daemon
            managing a Slurm cluster. Additionally, the build directory ('-dir')
            must be located in shared storage which can be accessed by all hosts
            in the cluster.""")

    scparam(cfg, ['option', 'scheduler', 'cores'],
            sctype='int',
            scope='job',
            pernode='optional',
            shorthelp="Option: Scheduler core constraint",
            switch="-cores <int>",
            example=["cli: -cores 48",
                     "api: chip.set('option', 'scheduler', 'cores', '48')"],
            schelp="""
            Specifies the number CPU cores required to run the job.
            For the slurm scheduler, this translates to the '-c'
            switch. For more information, see the job scheduler
            documentation""")

    scparam(cfg, ['option', 'scheduler', 'memory'],
            sctype='int',
            unit='MB',
            scope='job',
            pernode='optional',
            shorthelp="Option: Scheduler memory constraint",
            switch="-memory <int>",
            example=["cli: -memory 8000",
                     "api: chip.set('option', 'scheduler', 'memory', '8000')"],
            schelp="""
            Specifies the amount of memory required to run the job,
            specified in MB. For the slurm scheduler, this translates to
            the '--mem' switch. For more information, see the job
            scheduler documentation""")

    scparam(cfg, ['option', 'scheduler', 'queue'],
            sctype='str',
            scope='job',
            pernode='optional',
            shorthelp="Option: Scheduler queue",
            switch="-queue <str>",
            example=["cli: -queue nightrun",
                     "api: chip.set('option', 'scheduler', 'queue', 'nightrun')"],
            schelp="""
            Send the job to the specified queue. With slurm, this
            translates to 'partition'. The queue name must match
            the name of an existing job scheduler queue. For more information,
            see the job scheduler documentation""")

    scparam(cfg, ['option', 'scheduler', 'defer'],
            sctype='str',
            scope='job',
            pernode='optional',
            shorthelp="Option: Scheduler start time",
            switch="-defer <str>",
            example=["cli: -defer 16:00",
                     "api: chip.set('option', 'scheduler', 'defer', '16:00')"],
            schelp="""
            Defer initiation of job until the specified time. The parameter
            is pass through string for remote job scheduler such as slurm.
            For more information about the exact format specification, see
            the job scheduler documentation. Examples of valid slurm specific
            values include: now+1hour, 16:00, 010-01-20T12:34:00. For more
            information, see the job scheduler documentation.""")

    scparam(cfg, ['option', 'scheduler', 'options'],
            sctype='[str]',
            pernode='optional',
            shorthelp="Option: Scheduler arguments",
            switch="-scheduler_options <str>",
            example=[
                "cli: -scheduler_options \"--pty\"",
                "api: chip.set('option', 'scheduler', 'options', \"--pty\")"],
            schelp="""
            Advanced/export options passed through unchanged to the job
            scheduler as-is. (The user specified options must be compatible
            with the rest of the scheduler parameters entered.(memory etc).
            For more information, see the job scheduler documentation.""")

    scparam(cfg, ['option', 'scheduler', 'msgevent'],
            sctype='[enum]',
            enum=['all', 'summary', 'begin', 'end', 'timeout', 'fail'],
            scope='job',
            pernode='optional',
            shorthelp="Option: Message event trigger",
            switch="-msgevent <str>",
            example=[
                "cli: -msgevent all",
                "api: chip.set('option', 'scheduler', 'msgevent', 'all')"],
            schelp="""
            Directs job scheduler to send a message to the user in
            ['optoion', 'scheduler', 'msgcontact'] when certain events occur
            during a task.

            * fail: send an email on failures
            * timeout: send an email on timeouts
            * begin: send an email at the start of a node task
            * end: send an email at the end of a node task
            * summary: send a summary email at the end of the run
            * all: send an email on any event
            """)

    scparam(cfg, ['option', 'scheduler', 'msgcontact'],
            sctype='[str]',
            scope='job',
            pernode='optional',
            shorthelp="Option: Message contact",
            switch="-msgcontact <str>",
            example=[
                "cli: -msgcontact 'wile.e.coyote@acme.com'",
                "api: chip.set('option', 'scheduler', 'msgcontact', 'wiley@acme.com')"],
            schelp="""
            List of email addresses to message on a 'msgevent'. Support for
            email messages relies on job scheduler daemon support.
            For more information, see the job scheduler documentation. """)

    scparam(cfg, ['option', 'scheduler', 'maxnodes'],
            sctype='int',
            shorthelp="Option: Maximum concurrent nodes",
            switch="-maxnodes <int>",
            example=["cli: -maxnodes 4",
                     "api: chip.set('option', 'scheduler', 'maxnodes', 4)"],
            schelp="""
            Maximum number of concurrent nodes to run in a job. If not set this will default
            to the number of cpu cores available.""")

    return cfg


############################################
# Package information
############################################
def schema_package(cfg):

    userid = 'default'

    scparam(cfg, ['package', 'version'],
            sctype='str',
            scope='global',
            shorthelp="Package: version",
            switch="-package_version <str>",
            example=[
                "cli: -package_version 1.0",
                "api: chip.set('package', 'version', '1.0')"],
            schelp="""Package version. Can be a branch, tag, commit hash,
            or a semver compatible version.""")

    scparam(cfg, ['package', 'description'],
            sctype='str',
            scope='global',
            shorthelp="Package: description",
            switch="-package_description <str>",
            example=[
                "cli: -package_description 'Yet another cpu'",
                "api: chip.set('package', 'description', 'Yet another cpu')"],
            schelp="""Package short one line description for package
            managers and summary reports.""")

    scparam(cfg, ['package', 'keyword'],
            sctype='str',
            scope='global',
            shorthelp="Package: keyword",
            switch="-package_keyword <str>",
            example=[
                "cli: -package_keyword cpu",
                "api: chip.set('package', 'keyword', 'cpu')"],
            schelp="""Package keyword(s) used to characterize package.""")
    scparam(cfg, ['package', 'doc', 'homepage'],
            sctype='str',
            scope='global',
            shorthelp="Package: documentation homepage",
            switch="-package_doc_homepage <str>",
            example=[
                "cli: -package_doc_homepage index.html",
                "api: chip.set('package', 'doc', 'homepage', 'index.html')"],
            schelp="""
            Package documentation homepage. Filepath to design docs homepage.
            Complex designs can can include a long non standard list of
            documents dependent. A single html entry point can be used to
            present an organized documentation dashboard to the designer.""")

    doctypes = ['datasheet',
                'reference',
                'userguide',
                'quickstart',
                'releasenotes',
                'testplan',
                'signoff',
                'tutorial']

    for item in doctypes:
        scparam(cfg, ['package', 'doc', item],
                sctype='[file]',
                scope='global',
                shorthelp=f"Package: {item} document",
                switch=f"-package_doc_{item} <file>",
                example=[
                    f"cli: -package_doc_{item} {item}.pdf",
                    f"api: chip.set('package', 'doc', '{item}', '{item}.pdf')"],
                schelp=f""" Package list of {item} documents.""")

    scparam(cfg, ['package', 'license'],
            sctype='[str]',
            scope='global',
            shorthelp="Package: license identifiers",
            switch="-package_license <str>",
            example=[
                "cli: -package_license 'Apache-2.0'",
                "api: chip.set('package', 'license', 'Apache-2.0')"],
            schelp="""Package list of SPDX license identifiers.""")

    scparam(cfg, ['package', 'licensefile'],
            sctype='[file]',
            scope='global',
            shorthelp="Package: license files",
            switch="-package_licensefile <file>",
            example=[
                "cli: -package_licensefile './LICENSE'",
                "api: chip.set('package', 'licensefile', './LICENSE')"],
            schelp="""Package list of license files for to be
            applied in cases when a SPDX identifier is not available.
            (eg. proprietary licenses).list of SPDX license identifiers.""")

    scparam(cfg, ['package', 'organization'],
            sctype='[str]',
            scope='global',
            shorthelp="Package: sponsoring organization",
            switch="-package_organization <str>",
            example=[
                "cli: -package_organization 'humanity'",
                "api: chip.set('package', 'organization', 'humanity')"],
            schelp="""Package sponsoring organization. The field can be left
            blank if not applicable.""")

    record = ['name',
              'email',
              'username',
              'location',
              'organization',
              'publickey']

    for item in record:
        scparam(cfg, ['package', 'author', userid, item],
                sctype='str',
                scope='global',
                shorthelp=f"Package: author {item}",
                switch=f"-package_author_{item} 'userid <str>'",
                example=[
                    f"cli: -package_author_{item} 'wiley wiley@acme.com'",
                    f"api: chip.set('package', 'author', 'wiley', '{item}', 'wiley@acme.com')"],
                schelp=f"""Package author {item} provided with full name as key and
                {item} as value.""")

    source = 'default'

    scparam(cfg, ['package', 'source', source, 'path'],
            sctype='str',
            scope='global',
            shorthelp="Package data source path",
            switch="-package_source_path 'source <str>'",
            example=[
                "cli: -package_source_path "
                "'freepdk45_data ssh://git@github.com/siliconcompiler/freepdk45/'",
                "api: chip.set('package', 'source', "
                "'freepdk45_data', 'path', 'ssh://git@github.com/siliconcompiler/freepdk45/')"],
            schelp="""
            Package data source path, allowed paths:

            * /path/on/network/drive
            * file:///path/on/network/drive
            * git+https://github.com/xyz/xyz
            * git://github.com/xyz/xyz
            * git+ssh://github.com/xyz/xyz
            * ssh://github.com/xyz/xyz
            * https://github.com/xyz/xyz/archive
            * https://zeroasic.com/xyz.tar.gz
            * python://siliconcompiler
            """)

    scparam(cfg, ['package', 'source', source, 'ref'],
            sctype='str',
            scope='global',
            shorthelp="Package data source reference",
            switch="-package_source_ref 'source <str>'",
            example=[
                "cli: -package_source_ref 'freepdk45_data 07ec4aa'",
                "api: chip.set('package', 'source', 'freepdk45_data', 'ref', '07ec4aa')"],
            schelp="""
            Package data source reference
            """)

    return cfg


############################################
# Design Checklist
############################################
def schema_checklist(cfg):

    item = 'default'
    standard = 'default'
    metric = 'default'

    scparam(cfg, ['checklist', standard, item, 'description'],
            sctype='str',
            scope='global',
            shorthelp="Checklist: item description",
            switch="-checklist_description 'standard item <str>'",
            example=[
                "cli: -checklist_description 'ISO D000 A-DESCRIPTION'",
                "api: chip.set('checklist', 'ISO', 'D000', 'description', 'A-DESCRIPTION')"],
            schelp="""
            A short one line description of the checklist item.""")

    scparam(cfg, ['checklist', standard, item, 'requirement'],
            sctype='str',
            scope='global',
            shorthelp="Checklist: item requirement",
            switch="-checklist_requirement 'standard item <str>'",
            example=[
                "cli: -checklist_requirement 'ISO D000 DOCSTRING'",
                "api: chip.set('checklist', 'ISO', 'D000', 'requirement', 'DOCSTRING')"],
            schelp="""
            A complete requirement description of the checklist item
            entered as a multi-line string.""")

    scparam(cfg, ['checklist', standard, item, 'dataformat'],
            sctype='str',
            scope='global',
            shorthelp="Checklist: item data format",
            switch="-checklist_dataformat 'standard item <str>'",
            example=[
                "cli: -checklist_dataformat 'ISO D000 dataformat README'",
                "api: chip.set('checklist', 'ISO', 'D000', 'dataformat', 'README')"],
            schelp="""
            Free text description of the type of data files acceptable as
            checklist signoff validation.""")

    scparam(cfg, ['checklist', standard, item, 'rationale'],
            sctype='[str]',
            scope='global',
            shorthelp="Checklist: item rational",
            switch="-checklist_rationale 'standard item <str>'",
            example=[
                "cli: -checklist_rationale 'ISO D000 reliability'",
                "api: chip.set('checklist', 'ISO', 'D000', 'rationale', 'reliability')"],
            schelp="""
            Rationale for the the checklist item. Rationale should be a
            unique alphanumeric code used by the standard or a short one line
            or single word description.""")

    scparam(cfg, ['checklist', standard, item, 'criteria'],
            sctype='[str]',
            scope='global',
            shorthelp="Checklist: item criteria",
            switch="-checklist_criteria 'standard item <str>'",
            example=[
                "cli: -checklist_criteria 'ISO D000 errors==0'",
                "api: chip.set('checklist', 'ISO', 'D000', 'criteria', 'errors==0')"],
            schelp="""
            Simple list of signoff criteria for checklist item which
            must all be met for signoff. Each signoff criteria consists of
            a metric, a relational operator, and a value in the form.
            'metric op value'.""")

    scparam(cfg, ['checklist', standard, item, 'task'],
            sctype='[(str,str,str)]',
            scope='global',
            shorthelp="Checklist: item task",
            switch="-checklist_task 'standard item <(str,str,str)>'",
            example=[
                "cli: -checklist_task 'ISO D000 (job0,place,0)'",
                "api: chip.set('checklist', 'ISO', 'D000', 'task', ('job0', 'place', '0'))"],
            schelp="""
            Flowgraph job and task used to verify the checklist item.
            The parameter should be left empty for manual and for tool
            flows that bypass the SC infrastructure.""")

    scparam(cfg, ['checklist', standard, item, 'report'],
            sctype='[file]',
            scope='global',
            shorthelp="Checklist: item report",
            switch="-checklist_report 'standard item <file>'",
            example=[
                "cli: -checklist_report 'ISO D000 my.rpt'",
                "api: chip.set('checklist', 'ISO', 'D000', 'report', 'my.rpt')"],
            schelp="""
            Filepath to report(s) of specified type documenting the successful
            validation of the checklist item.""")

    scparam(cfg, ['checklist', standard, item, 'waiver', metric],
            sctype='[file]',
            scope='global',
            shorthelp="Checklist: item metric waivers",
            switch="-checklist_waiver 'standard item metric <file>'",
            example=[
                "cli: -checklist_waiver 'ISO D000 bold my.txt'",
                "api: chip.set('checklist', 'ISO', 'D000', 'waiver', 'hold', 'my.txt')"],
            schelp="""
            Filepath to report(s) documenting waivers for the checklist
            item specified on a per metric basis.""")

    scparam(cfg, ['checklist', standard, item, 'ok'],
            sctype='bool',
            scope='global',
            shorthelp="Checklist: item ok",
            switch="-checklist_ok 'standard item <bool>'",
            example=[
                "cli: -checklist_ok 'ISO D000 true'",
                "api: chip.set('checklist', 'ISO', 'D000', 'ok', True)"],
            schelp="""
            Boolean check mark for the checklist item. A value of
            True indicates a human has inspected the all item dictionary
            parameters check out.""")

    return cfg


###########################
# ASIC Setup
###########################
def schema_asic(cfg):
    '''ASIC Automated Place and Route Parameters'''

    scparam(cfg, ['asic', 'logiclib'],
            sctype='[str]',
            scope='job',
            pernode='optional',
            shorthelp="ASIC: logic libraries",
            switch="-asic_logiclib <str>",
            example=["cli: -asic_logiclib nangate45",
                     "api: chip.set('asic', 'logiclib', 'nangate45')"],
            schelp="""List of all selected logic libraries libraries
            to use for optimization for a given library architecture
            (9T, 11T, etc).""")

    scparam(cfg, ['asic', 'macrolib'],
            sctype='[str]',
            scope='job',
            pernode='optional',
            shorthelp="ASIC: macro libraries",
            switch="-asic_macrolib <str>",
            example=["cli: -asic_macrolib sram64x1024",
                     "api: chip.set('asic', 'macrolib', 'sram64x1024')"],
            schelp="""
            List of macro libraries to be linked in during synthesis and place
            and route. Macro libraries are used for resolving instances but are
            not used as targets for logic synthesis.""")

    scparam(cfg, ['asic', 'delaymodel'],
            sctype='str',
            scope='job',
            pernode='optional',
            shorthelp="ASIC: delay model",
            switch="-asic_delaymodel <str>",
            example=["cli: -asic_delaymodel ccs",
                     "api: chip.set('asic', 'delaymodel', 'ccs')"],
            schelp="""
            Delay model to use for the target libs. Supported values
            are nldm and ccs.""")

    # TODO: Expand on the exact definitions of these types of cells.
    # minimize typing
    names = ['decap',
             'tie',
             'hold',
             'clkbuf',
             'clkgate',
             'clklogic',
             'dontuse',
             'filler',
             'tap',
             'endcap',
             'antenna']

    for item in names:
        scparam(cfg, ['asic', 'cells', item],
                sctype='[str]',
                pernode='optional',
                shorthelp=f"ASIC: {item} cell list",
                switch=f"-asic_cells_{item} '<str>'",
                example=[
                    f"cli: -asic_cells_{item} '*eco*'",
                    f"api: chip.set('asic', 'cells', '{item}', '*eco*')"],
                schelp="""
                List of cells grouped by a property that can be accessed
                directly by the designer and tools. The example below shows how
                all cells containing the string 'eco' could be marked as dont use
                for the tool.""")

    scparam(cfg, ['asic', 'libarch'],
            sctype='str',
            pernode='optional',
            shorthelp="ASIC: library architecture",
            switch="-asic_libarch '<str>'",
            example=[
                "cli: -asic_libarch '12track'",
                "api: chip.set('asic', 'libarch', '12track')"],
            schelp="""
            The library architecture (e.g. library height) used to build the
            design. For example a PDK with support for 9 and 12 track libraries
            might have 'libarchs' called 9t and 12t.""")

    libarch = 'default'
    scparam(cfg, ['asic', 'site', libarch],
            sctype='[str]',
            pernode='optional',
            shorthelp="ASIC: Library sites",
            switch="-asic_site 'libarch <str>'",
            example=[
                "cli: -asic_site '12track Site_12T'",
                "api: chip.set('asic', 'site', '12track', 'Site_12T')"],
            schelp="""
            Site names for a given library architecture.""")

    return cfg


############################################
# Constraints
############################################
def schema_constraint(cfg):

    # TIMING

    scenario = 'default'

    pin = 'default'
    scparam(cfg, ['constraint', 'timing', scenario, 'voltage', pin],
            sctype='float',
            pernode='optional',
            unit='V',
            scope='job',
            shorthelp="Constraint: pin voltage level",
            switch="-constraint_timing_voltage 'scenario pin <float>'",
            example=["cli: -constraint_timing_voltage 'worst VDD 0.9'",
                     "api: chip.set('constraint', 'timing', 'worst', 'voltage', 'VDD', '0.9')"],
            schelp="""Operating voltage applied to a specific pin in the scenario.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'temperature'],
            sctype='float',
            pernode='optional',
            unit='C',
            scope='job',
            shorthelp="Constraint: temperature",
            switch="-constraint_timing_temperature 'scenario <float>'",
            example=["cli: -constraint_timing_temperature 'worst 125'",
                     "api: chip.set('constraint', 'timing', 'worst', 'temperature', '125')"],
            schelp="""Chip temperature applied to the scenario specified in degrees C.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'libcorner'],
            sctype='[str]',
            pernode='optional',
            scope='job',
            shorthelp="Constraint: library corner",
            switch="-constraint_timing_libcorner 'scenario <str>'",
            example=["cli: -constraint_timing_libcorner 'worst ttt'",
                     "api: chip.set('constraint', 'timing', 'worst', 'libcorner', 'ttt')"],
            schelp="""List of characterization corners used to select
            timing files for all logiclibs and macrolibs.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'pexcorner'],
            sctype='str',
            pernode='optional',
            scope='job',
            shorthelp="Constraint: pex corner",
            switch="-constraint_timing_pexcorner 'scenario <str>'",
            example=["cli: -constraint_timing_pexcorner 'worst max'",
                     "api: chip.set('constraint', 'timing', 'worst', 'pexcorner', 'max')"],
            schelp="""Parasitic corner applied to the scenario. The
            'pexcorner' string must match a corner found in the pdk
            pexmodel setup.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'opcond'],
            sctype='str',
            pernode='optional',
            scope='job',
            shorthelp="Constraint: operating condition",
            switch="-constraint_timing_opcond 'scenario <str>'",
            example=["cli: -constraint_timing_opcond 'worst typical_1.0'",
                     "api: chip.set('constraint', 'timing', 'worst', 'opcond', 'typical_1.0')"],
            schelp="""Operating condition applied to the scenario. The value
            can be used to access specific conditions within the library
            timing models from the 'logiclib' timing models.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'mode'],
            sctype='str',
            pernode='optional',
            scope='job',
            shorthelp="Constraint: operating mode",
            switch="-constraint_timing_mode 'scenario <str>'",
            example=["cli: -constraint_timing_mode 'worst test'",
                     "api: chip.set('constraint', 'timing', 'worst', 'mode', 'test')"],
            schelp="""Operating mode for the scenario. Operating mode strings
            can be values such as test, functional, standby.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'file'],
            sctype='[file]',
            pernode='optional',
            scope='job',
            copy=True,
            shorthelp="Constraint: SDC files",
            switch="-constraint_timing_file 'scenario <file>'",
            example=[
                "cli: -constraint_timing_file 'worst hello.sdc'",
                "api: chip.set('constraint', 'timing', 'worst', 'file', 'hello.sdc')"],
            schelp="""List of timing constraint files to use for the scenario. The
            values are combined with any constraints specified by the design
            'constraint' parameter. If no constraints are found, a default
            constraint file is used based on the clock definitions.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'check'],
            sctype='[str]',
            pernode='optional',
            scope='job',
            shorthelp="Constraint: timing checks",
            switch="-constraint_timing_check 'scenario <str>'",
            example=[
                "cli: -constraint_timing_check 'worst setup'",
                "api: chip.add('constraint', 'timing', 'worst', 'check', 'setup')"],
            schelp="""
            List of checks for to perform for the scenario. The checks must
            align with the capabilities of the EDA tools and flow being used.
            Checks generally include objectives like meeting setup and hold goals
            and minimize power. Standard check names include setup, hold, power,
            noise, reliability.""")

    # COMPONENTS

    inst = 'default'

    scparam(cfg, ['constraint', 'component', inst, 'placement'],
            sctype='(float,float,float)',
            pernode='optional',
            unit='um',
            shorthelp="Constraint: Component placement",
            switch="-constraint_component_placement 'inst <(float,float,float)>'",
            example=[
                "cli: -constraint_component_placement 'i0 (2.0,3.0,0.0)'",
                "api: chip.set('constraint', 'component', 'i0', 'placement', (2.0, 3.0, 0.0))"],
            schelp="""
            Placement location of a named instance, specified as a (x, y, z) tuple of
            floats. The location refers to the placement of the center/centroid of the
            component. The 'placement' parameter is a goal/intent, not an exact specification.
            The compiler and layout system may adjust coordinates to meet competing
            goals such as manufacturing design rules and grid placement
            guidelines. The 'z' coordinate shall be set to 0 for planar systems
            with only (x, y) coordinates. Discretized systems like PCB stacks,
            package stacks, and breadboards only allow a reduced
            set of floating point values (0, 1, 2, 3). The user specifying the
            placement will need to have some understanding of the type of
            layout system the component is being placed in (ASIC, SIP, PCB) but
            should not need to know exact manufacturing specifications.""")

    scparam(cfg, ['constraint', 'component', inst, 'partname'],
            sctype='str',
            pernode='optional',
            shorthelp="Constraint: Component part name",
            switch="-constraint_component_partname 'inst <str>'",
            example=[
                "cli: -constraint_component_partname 'i0 filler_x1'",
                "api: chip.set('constraint', 'component', 'i0', 'partname', 'filler_x1')"],
            schelp="""
            Part name of a named instance. The parameter is required for instances
            that are not contained within the design netlist (ie. physical only cells).
            """)

    scparam(cfg, ['constraint', 'component', inst, 'halo'],
            sctype='(float,float)',
            pernode='optional',
            unit='um',
            shorthelp="Constraint: Component halo",
            switch="-constraint_component_halo 'inst <(float,float)>'",
            example=[
                "cli: -constraint_component_halo 'i0 (1,1)'",
                "api: chip.set('constraint', 'component', 'i0', 'halo', (1, 1))"],
            schelp="""
            Placement keepout halo around the named component, specified as a
            (horizontal, vertical) tuple represented in microns.
            """)

    scparam(cfg, ['constraint', 'component', inst, 'rotation'],
            sctype='float',
            pernode='optional',
            shorthelp="Constraint: Component rotation",
            switch="-constraint_component_rotation 'inst <float>'",
            example=[
                "cli: -constraint_component_rotation 'i0 90'",
                "api: chip.set('constraint', 'component', 'i0', 'rotation', '90')"],
            schelp="""
            Placement rotation of the component specified in degrees. Rotation
            goes counter-clockwise for all parts on top and clock-wise for parts
            on the bottom. In both cases, this is from the perspective of looking
            at the top of the board. Rotation is specified in degrees. Most gridded
            layout systems (like ASICs) only allow a finite number of rotation
            values (0, 90, 180, 270).""")

    scparam(cfg, ['constraint', 'component', inst, 'flip'],
            sctype='bool',
            pernode='optional',
            shorthelp="Constraint: Component flip option",
            switch="-constraint_component_flip 'inst <bool>'",
            example=[
                "cli: -constraint_component_flip 'i0 true'",
                "api: chip.set('constraint', 'component', 'i0', 'flip', True)"],
            schelp="""
            Boolean parameter specifying that the instanced library component should be flipped
            around the vertical axis before being placed on the substrate. The need to
            flip a component depends on the component footprint. Most dies have pads
            facing up and so must be flipped when assembled face down (eg. flip-chip,
            WCSP).""")

    # PINS
    name = 'default'

    scparam(cfg, ['constraint', 'pin', name, 'placement'],
            sctype='(float,float,float)',
            pernode='optional',
            unit='um',
            shorthelp="Constraint: Pin placement",
            switch="-constraint_pin_placement 'name <(float,float,float)>'",
            example=[
                "cli: -constraint_pin_placement 'nreset (2.0,3.0,0.0)'",
                "api: chip.set('constraint', 'pin', 'nreset', 'placement', (2.0, 3.0, 0.0))"],
            schelp="""
            Placement location of a named pin, specified as a (x, y, z) tuple of
            floats. The location refers to the placement of the center of the
            pin. The 'placement' parameter is a goal/intent, not an exact specification.
            The compiler and layout system may adjust sizes to meet competing
            goals such as manufacturing design rules and grid placement
            guidelines. The 'z' coordinate shall be set to 0 for planar components
            with only (x, y) coordinates. Discretized systems like 3D chips with
            pins on top and bottom may choose to discretize the top and bottom
            layer as 0, 1 or use absolute coordinates. Values are specified
            in microns.""")

    scparam(cfg, ['constraint', 'pin', name, 'layer'],
            sctype='str',
            pernode='optional',
            shorthelp="Constraint: Pin layer",
            switch="-constraint_pin_layer 'name <str>'",
            example=[
                "cli: -constraint_pin_layer 'nreset m4'",
                "api: chip.set('constraint', 'pin', 'nreset', 'layer', 'm4')"],
            schelp="""
            Pin metal layer specified based on the SC standard layer stack
            starting with m1 as the lowest routing layer and ending
            with m<n> as the highest routing layer.""")

    scparam(cfg, ['constraint', 'pin', name, 'side'],
            sctype='int',
            pernode='optional',
            shorthelp="Constraint: Pin side",
            switch="-constraint_pin_side 'name <int>'",
            example=[
                "cli: -constraint_pin_side 'nreset 1'",
                "api: chip.set('constraint', 'pin', 'nreset', 'side', 1)"],
            schelp="""
            Side of block where the named pin should be placed. Sides are
            enumerated as integers with '1' being the lower left side,
            with the side index incremented on right turn in a clock wise
            fashion. In case of conflict between 'lower' and 'left',
            'left' has precedence. The side option and order option are
            orthogonal to the placement option.""")

    scparam(cfg, ['constraint', 'pin', name, 'order'],
            sctype='int',
            pernode='optional',
            shorthelp="Constraint: Pin order",
            switch="-constraint_pin_order 'name <int>'",
            example=[
                "cli: -constraint_pin_order 'nreset 1'",
                "api: chip.set('constraint', 'pin', 'nreset', 'order', 1)"],
            schelp="""
            The relative position of the named pin in a vector of pins
            on the side specified by the 'side' option. Pin order counting
            is done clockwise. If multiple pins on the same side have the
            same order number, the actual order is at the discretion of the
            tool.""")

    # NETS
    scparam(cfg, ['constraint', 'net', name, 'maxlength'],
            sctype='float',
            pernode='optional',
            unit='um',
            shorthelp="Constraint: Net max length",
            switch="-constraint_net_maxlength 'name <float>'",
            example=[
                "cli: -constraint_net_maxlength 'nreset 1000'",
                "api: chip.set('constraint', 'net', 'nreset', 'maxlength', '1000')"],
            schelp="""
            Maximum total length of a net, specified in microns.
            Wildcards ('*') can be used for net names.""")

    scparam(cfg, ['constraint', 'net', name, 'maxresistance'],
            sctype='float',
            pernode='optional',
            unit='ohm',
            shorthelp="Constraint: Net max resistance",
            switch="-constraint_net_maxresistance 'name <float>'",
            example=[
                "cli: -constraint_net_maxresistance 'nreset 1'",
                "api: chip.set('constraint', 'net', 'nreset', 'maxresistance', '1')"],
            schelp="""
            Maximum resistance of named net between driver and receiver
            specified in ohms. Wildcards ('*') can be used for net names.""")

    scparam(cfg, ['constraint', 'net', name, 'ndr'],
            sctype='(float,float)',
            pernode='optional',
            unit='um',
            shorthelp="Constraint: Net routing rule",
            switch="-constraint_net_ndr 'name <(float,float)>'",
            example=[
                "cli: -constraint_net_ndr 'nreset (0.4,0.4)'",
                "api: chip.set('constraint', 'net', 'nreset', 'ndr', (0.4, 0.4))"],
            schelp="""
            Definitions of non-default routing rule specified on a per
            net basis. Constraints are entered as a (width, space) tuples
            specified in microns. Wildcards ('*') can be used
            for net names.""")

    scparam(cfg, ['constraint', 'net', name, 'minlayer'],
            sctype='str',
            pernode='optional',
            shorthelp="Constraint: Net minimum routing layer",
            switch="-constraint_net_minlayer 'name <str>'",
            example=[
                "cli: -constraint_net_minlayer 'nreset m1'",
                "api: chip.set('constraint', 'net', 'nreset', 'minlayer', 'm1')"],
            schelp="""
            Minimum metal layer to be used for automated place and route
            specified on a per net basis. Metal names should either be the PDK
            specific metal stack name or an integer with '1' being the lowest
            routing layer. Wildcards ('*') can be used for net names.""")

    scparam(cfg, ['constraint', 'net', name, 'maxlayer'],
            sctype='str',
            pernode='optional',
            shorthelp="Constraint: Net maximum routing layer",
            switch="-constraint_net_maxlayer 'name <str>'",
            example=[
                "cli: -constraint_net_maxlayer 'nreset m1'",
                "api: chip.set('constraint', 'net', 'nreset', 'maxlayer', 'm1')"],
            schelp="""
            Maximum metal layer to be used for automated place and route
            specified on a per net basis. Metal names should either be the PDK
            specific metal stack name or an integer with '1' being the lowest
            routing layer. Wildcards ('*') can be used for net names.""")

    scparam(cfg, ['constraint', 'net', name, 'shield'],
            sctype='str',
            pernode='optional',
            shorthelp="Constraint: Net shielding",
            switch="-constraint_net_shield 'name <str>'",
            example=[
                "cli: -constraint_net_shield 'clk vss'",
                "api: chip.set('constraint', 'net', 'clk', 'shield', 'vss')"],
            schelp="""
            Specifies that the named net should be shielded by the given
            signal on both sides of the net.""")

    scparam(cfg, ['constraint', 'net', name, 'match'],
            sctype='[str]',
            pernode='optional',
            shorthelp="Constraint: Net matched routing",
            switch="-constraint_net_match 'name <str>'",
            example=[
                "cli: -constraint_net_match 'clk1 clk2'",
                "api: chip.set('constraint', 'net', 'clk1', 'match', 'clk2')"],
            schelp="""
            List of nets whose routing should closely matched the named
            net in terms of length, layer, width, etc. Wildcards ('*') can
            be used for net names.""")

    scparam(cfg, ['constraint', 'net', name, 'diffpair'],
            sctype='str',
            pernode='optional',
            shorthelp="Constraint: Net diffpair",
            switch="-constraint_net_diffpair 'name <str>'",
            example=[
                "cli: -constraint_net_diffpair 'clkn clkp'",
                "api: chip.set('constraint', 'net', 'clkn', 'diffpair', 'clkp')"],
            schelp="""
            Differential pair signal of the named net (only used for actual
            differential pairs).""")

    scparam(cfg, ['constraint', 'net', name, 'sympair'],
            sctype='str',
            pernode='optional',
            shorthelp="Constraint: Net sympair",
            switch="-constraint_net_sympair 'name <str>'",
            example=[
                "cli: -constraint_net_sympair 'netA netB'",
                "api: chip.set('constraint', 'net', 'netA', 'sympair', 'netB')"],
            schelp="""
            Symmetrical pair signal to the named net. The two nets should be routed
            as reflections around the vertical or horizontal axis to minimize on-chip
            variability.""")

    # AREA
    scparam(cfg, ['constraint', 'outline'],
            sctype='[(float,float)]',
            pernode='optional',
            unit='um',
            scope='job',
            shorthelp="Constraint: Layout outline",
            switch="-constraint_outline <(float,float)>",
            example=["cli: -constraint_outline '(0,0)'",
                     "api: chip.set('constraint', 'outline', (0, 0))"],
            schelp="""
            List of (x, y) points that define the outline physical layout
            physical design. Simple rectangle areas can be defined with two points,
            one for the lower left corner and one for the upper right corner. All
            values are specified in microns.""")

    scparam(cfg, ['constraint', 'corearea'],
            sctype='[(float,float)]',
            pernode='optional',
            unit='um',
            scope='job',
            shorthelp="Constraint: Layout core area",
            switch="-constraint_corearea <(float,float)>",
            example=["cli: -constraint_corearea '(0,0)'",
                     "api: chip.set('constraint', 'corearea', (0, 0))"],
            schelp="""
            List of (x, y) points that define the outline of the core area for the
            physical design. Simple rectangle areas can be defined with two points,
            one for the lower left corner and one for the upper right corner. All
            values are specified in microns.""")

    scparam(cfg, ['constraint', 'coremargin'],
            sctype='float',
            pernode='optional',
            unit='um',
            scope='job',
            shorthelp="Constraint: Layout core margin",
            switch="-constraint_coremargin <float>",
            example=["cli: -constraint_coremargin 1",
                     "api: chip.set('constraint', 'coremargin', '1')"],
            schelp="""
            Halo/margin between the outline and core area for fully
            automated layout sizing and floorplanning, specified in
            microns.""")

    scparam(cfg, ['constraint', 'density'],
            sctype='float',
            pernode='optional',
            scope='job',
            shorthelp="Constraint: Layout density",
            switch="-constraint_density <float>",
            example=["cli: -constraint_density 30",
                     "api: chip.set('constraint', 'density', '30')"],
            schelp="""
            Target density based on the total design cells area reported
            after synthesis/elaboration. This number is used when no outline
            or floorplan is supplied. Any number between 1 and 100 is legal,
            but values above 50 may fail due to area/congestion issues during
            automated place and route.""")

    scparam(cfg, ['constraint', 'aspectratio'],
            sctype='float',
            pernode='optional',
            defvalue='1.0',
            scope='job',
            shorthelp="Constraint: Layout aspect ratio",
            switch="-constraint_aspectratio <float>",
            example=["cli: -constraint_aspectratio 2.0",
                     "api: chip.set('constraint', 'aspectratio', '2.0')"],
            schelp="""
            Height to width ratio of the block for automated floorplanning.
            Values below 0.1 and above 10 should be avoided as they will likely fail
            to converge during placement and routing. The ideal aspect ratio for
            most designs is 1. This value is only used when no diearea or floorplan
            is supplied.""")

    return cfg


##############################################################################
# Main routine
if __name__ == "__main__":
    cfg = schema_cfg()
    print(json.dumps(cfg, indent=4, sort_keys=True))
