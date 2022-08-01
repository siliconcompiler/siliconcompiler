# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import utils

import re
import os
import sys
import copy as pycopy
import json

SCHEMA_VERSION = '0.9.0'

#############################################################################
# PARAM DEFINITION
#############################################################################

def scparam(cfg,
            keypath,
            sctype=None,
            require=None,
            defvalue=None,
            scope='job',
            copy='false',
            lock='false',
            hashalgo='sha256',
            signature=None,
            notes=None,
            unit=None,
            shorthelp=None,
            switch=None,
            example=None,
            schelp=None):

    # 1. decend keypath until done
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
                schelp=schelp)
    else:

        # removing leading spaces as if schelp were a docstring
        schelp = utils.trim(schelp)

        # setting valus based on types
        # note (bools are never lists)
        if re.match(r'bool',sctype):
            require = 'all'
            if defvalue is None:
                defvalue = 'false'
        if re.match(r'\[',sctype) and signature is None:
            signature = []
        if re.match(r'\[',sctype) and defvalue is None:
            defvalue = []

        # mandatory for all
        cfg['defvalue'] = defvalue
        cfg['value'] = pycopy.copy(defvalue)
        cfg['type'] = sctype
        cfg['scope'] = scope
        cfg['require'] = require
        cfg['lock'] = lock
        cfg['switch'] = switch
        cfg['shorthelp'] = shorthelp
        cfg['example'] = example
        cfg['help'] = schelp
        cfg['signature'] = signature
        cfg['notes'] = notes

        # unit for floats/ints
        if unit is not None:
            cfg['unit'] = unit

        # file only values
        if re.search(r'file',sctype):
            cfg['hashalgo'] = hashalgo
            cfg['copy'] = copy
            cfg['filehash'] = []
            cfg['date'] = []
            cfg['author'] = []


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

    SCHEMA_VERSION = '0.8.0'

    # Basic schema setup
    cfg = {}

    # Place holder dictionaries updated by core methods()
    cfg['history'] = {}
    cfg['library'] = {}

    scparam(cfg,['schemaversion'],
            sctype='str',
            scope='global',
            defvalue=SCHEMA_VERSION,
            require='all',
            shorthelp="Schema version number",
            lock='true',
            switch="-schemaversion <str>",
            example=["api: chip.get('schemaversion')"],
            schelp="""SiliconCompiler schema version number.""")

    # Design topmodule/entrypoint
    scparam(cfg,['design'],
            sctype='str',
            scope='global',
            require='all',
            shorthelp="Design top module name",
            switch="-design <str>",
            example=["cli: -design hello_world",
                    "api: chip.set('design', 'hello_world')"],
            schelp="""Name of the top level module or library. Required for all
            chip objects.""")

    # input/output
    io = {'input': ['Input','true'],
          'output': ['Output','false']
    }

    filetype = 'default'
    for item, val in io.items():
        scparam(cfg,[item, filetype],
                sctype='[file]',
                copy=f"{val[1]}",
                shorthelp=f"{val[0]} files",
                switch=f"-{item} 'filetype <file>'",
                example=[
                    f"cli: -{item} 'verilog hello_world.v'",
                    f"api: chip.set({item},'verilog','hello_world.v')"],
                schelp=f"""
                List of {item} files specifed by type. The filetype name must
                align with the parameter names within the flow and tool setup
                scripts. Examples of acceptable file types include python, c,
                systemc, verilog, vhdl, netlist, def, gds, gerber, saif, sdc,
                saif, vcd, spef, sdf.""")

    # Inputs and constraints
    cfg = schema_constraint(cfg)

    # Options
    cfg = schema_option(cfg)
    cfg = schema_arg(cfg)
    cfg = schema_unit(cfg)

    # Technology configuration
    cfg = schema_fpga(cfg)
    cfg = schema_asic(cfg)
    cfg = schema_pdk(cfg)

    # Flows
    cfg = schema_tool(cfg)
    cfg = schema_flowgraph(cfg)

    # Metrics
    cfg = schema_checklist(cfg)
    cfg = schema_metric(cfg)
    cfg = schema_record(cfg)

    # Modeling
    cfg = schema_model(cfg)

    # Datasheeet
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

    scparam(cfg,['fpga', 'arch'],
            sctype='[file]',
            copy='true',
            shorthelp="FPGA: architecture file",
            switch="-fpga_arch <file>",
            example=["cli: -fpga_arch myfpga.xml",
                     "api:  chip.set('fpga', 'arch', 'myfpga.xml')"],
            schelp=""" Architecture definition file for FPGA place and route
            tool. For the VPR tool, the file is a required XML based description,
            allowing targeting a large number of virtual and commercial
            architectures. For most commercial tools, the fpga part name provides
            enough information to enable compilation and the 'arch' parameter is
            optional.""")

    scparam(cfg,['fpga', 'vendor'],
            sctype='str',
            shorthelp="FPGA: vendor name",
            switch="-fpga_vendor <str>",
            example=["cli: -fpga_vendor acme",
                    "api:  chip.set('fpga', 'vendor', 'acme')"],
            schelp="""
            Name of the FPGA vendor. The parameter is used to check part
            name and to select the eda tool flow in case 'edaflow' is
            unspecified.""")

    scparam(cfg,['fpga', 'partname'],
            sctype='str',
            require='fpga',
            shorthelp="FPGA: part name",
            switch="-fpga_partname <str>",
            example=["cli: -fpga_partname fpga64k",
                     "api:  chip.set('fpga', 'partname', 'fpga64k')"],
            schelp="""
            Complete part name used as a device target by the FPGA compilation
            tool. The part name must be an exact string match to the partname
            hard coded within the FPGA eda tool.""")

    scparam(cfg,['fpga', 'board'],
            sctype='str',
            shorthelp="FPGA: board name",
            switch="-fpga_board <str>",
            example=["cli: -fpga_board parallella",
                     "api:  chip.set('fpga', 'board', 'parallella')"],
            schelp="""
            Complete board name used as a device target by the FPGA compilation
            tool. The board name must be an exact string match to the partname
            hard coded within the FPGA eda tool. The parameter is optional and can
            be used in place of a partname and pin constraints for some tools.""")

    scparam(cfg,['fpga', 'program'],
            sctype='bool',
            shorthelp="FPGA: program enable",
            switch="-fpga_program <bool>",
            example=["cli: -fpga_program",
                     "api:  chip.set('fpga', 'program', True)"],
            schelp="""Specifies that the bitstream should be loaded into an FPGA.""")

    scparam(cfg,['fpga', 'flash'],
            sctype='bool',
            shorthelp="FPGA: flash enable",
            switch="-fpga_flash <bool>",
            example=["cli: -fpga_flash",
                     "api:  chip.set('fpga', 'flash', True)"],
            schelp="""Specifies that the bitstream should be flashed in the board/device.
            The default is to load the bitstream into volatile memory (SRAM).""")

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
            require="asic",
            shorthelp="PDK: foundry name",
            switch="-pdk_foundry 'pdkname <str>'",
            example=["cli: -pdk_foundry 'asap7 virtual'",
                    "api:  chip.set('pdk', 'asap7', 'foundry', 'virtual')"],
            schelp="""
            Name of foundry corporation. Examples include intel, gf, tsmc,
            samsung, skywater, virtual. The \'virtual\' keyword is reserved for
            simulated non-manufacturable processes.""")

    scparam(cfg, ['pdk', pdkname, 'node'],
            sctype='float',
            scope='global',
            require="asic",
            shorthelp="PDK: process node",
            switch="-pdk_node 'pdkname <float>'",
            example=["cli: -pdk_node 'asap7 130'",
                    "api:  chip.set('pdk', 'asap7', 'node', 130)"],
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
                    "api:  chip.set('pdk', 'asap7', 'version', '1.0')"],
            schelp="""
            Alphanumeric string specifying the version of the PDK. Verification of
            correct PDK and IP versions is a hard ASIC tapeout require in all
            commercial foundries. The version number can be used for design manifest
            tracking and tapeout checklists.""")

    scparam(cfg, ['pdk', pdkname, 'stackup'],
            sctype='[str]',
            scope='global',
            require='asic',
            shorthelp="PDK: metal stackups",
            switch="-pdk_stackup 'pdkname <str>'",
            example=["cli: -pdk_stackup 'asap7 2MA4MB2MC'",
                     "api: chip.add('pdk', 'asap7','stackup','2MA4MB2MC')"],
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

    scparam(cfg, ['pdk', pdkname, 'thickness', stackup],
            sctype='float',
            scope='global',
            unit='mm',
            shorthelp="PDK: unit thickness",
            switch="-pdk_thickness 'pdkname stackup <float>'",
            example=["cli: -pdk_thickness 'asap7 2MA4MB2MC 1.57'",
                    "api:  chip.set('pdk', 'asap7', 'thickness', '2MA4MB2MC', 1.57)"],
            schelp="""
            Thickness of a manfuatured unit specified on a per stackup basis.""")

    scparam(cfg, ['pdk', pdkname, 'wafersize'],
            sctype='float',
            scope='global',
            unit='mm',
            require="asic",
            shorthelp="PDK: wafer size",
            switch="-pdk_wafersize 'pdkname <float>'",
            example=["cli: -pdk_wafersize 'asap7 300'",
                    "api:  chip.set('pdk', 'asap7', 'wafersize', 300)"],
            schelp="""
            Wafer diameter used in wafer based manufacturing process. The standard diameter
            for leading edge manufacturing is 300mm. For older process technologies
            and specialty fabs, smaller diameters such as 200, 100, 125, 100 are common.
            The value is used to calculate dies per wafer and full factory chip costs.""")

    scparam(cfg, ['pdk', pdkname, 'panelsize'],
            sctype='[(float,float)]',
            scope='global',
            unit='mm',
            shorthelp="PDK: panel size",
            switch="-pdk_panelsize 'pdkname <float>'",
            example=["cli: -pdk_panelsize 'asap7 (45.72,60.96)'",
                    "api:  chip.set('pdk', 'asap7', 'panelsize', (45.72,60.96))"],
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
                     "api:  chip.set('pdk', 'asap7', 'unitcost', 10000)"],
            schelp="""
            Raw cost per unit shipped by the factory, not accounting for yield
            loss.""")

    scparam(cfg, ['pdk', pdkname, 'd0'],
            sctype='float',
            scope='global',
            shorthelp="PDK: process defect density",
            switch="-pdk_d0 'pdkname <float>'",
            example=["cli: -pdk_d0 'asap7 0.1'",
                     "api:  chip.set('pdk', 'asap7', 'd0', 0.1)"],
            schelp="""
            Process defect density (d0) expressed as random defects per cm^2. The
            value is used to calculate yield losses as a function of area, which in
            turn affects the chip full factory costs. Two yield models are
            supported: Poisson (default), and Murphy. The Poisson based yield is
            calculated as dy = exp(-area * d0/100). The Murphy based yield is
            calculated as dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.""")

    scparam(cfg, ['pdk', pdkname, 'hscribe'],
            sctype='float',
            scope='global',
            unit='mm',
            shorthelp="PDK: horizontal scribe line width",
            switch="-pdk_hscribe 'pdkname <float>'",
            example=["cli: -pdk_hscribe 'asap7 0.1'",
                     "api:  chip.set('pdk', 'asap7', 'hscribe', 0.1)"],
            schelp="""
            Width of the horizontal scribe line used during die separation.
            The process is generally completed using a mechanical saw, but can be
            done through combinations of mechanical saws, lasers, wafer thinning,
            and chemical etching in more advanced technologies. The value is used
            to calculate effective dies per wafer and full factory cost.""")

    scparam(cfg, ['pdk', pdkname, 'vscribe'],
            sctype='float',
            scope='global',
            unit='mm',
            shorthelp="PDK: vertical scribe line width",
            switch="-pdk_vscribe 'pdkname <float>'",
            example=["cli: -pdk_vscribe 'asap7 0.1'",
                     "api:  chip.set('pdk', 'asap7', 'vscribe', 0.1)"],
            schelp="""
             Width of the vertical scribe line used during die separation.
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
                "api:  chip.set('pdk', 'asap7', 'edgemargin', 1)"],
            schelp="""
            Keep-out distance/margin from the edge inwards. The edge
            is prone to chipping and need special treatment that preclude
            placement of designs in this area. The edge value is used to
            calculate effective units per wafer/panel and full factory cost.""")

    scparam(cfg, ['pdk', pdkname, 'density'],
            sctype='float',
            scope='global',
            shorthelp="PDK: transistor density",
            switch="-pdk_density 'pdkname <float>'",
            example=["cli: -pdk_density 'asap7 100e6'",
                    "api:  chip.set('pdk', 'asap7', 'density', 10e6)"],
            schelp="""
            Approximate logic density expressed as # transistors / mm^2
            calculated as:
            0.6 * (Nand2 Transistor Count) / (Nand2 Cell Area) +
            0.4 * (Register Transistor Count) / (Register Cell Area)
            The value is specified for a fixed standard cell library within a node
            and will differ depending on the library vendor, library track height
            and library type. The value can be used to to normalize the effective
            density reported for the design across different process nodes. The
            value can be derived from a variety of sources, including the PDK DRM,
            library LEFs, conference presentations, and public analysis.""")

    simtype = 'default'
    scparam(cfg, ['pdk', pdkname, 'devmodel', tool, simtype, stackup],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: device models",
            switch="-pdk_devmodel 'pdkname tool simtype stackup <file>'",
            example=[
            "cli: -pdk_devmodel 'asap7 xyce spice M10 asap7.sp'",
            "api: chip.set('pdk','asap7','devmodel','xyce','spice','M10','asap7.sp')"],
            schelp="""
            List of filepaths to PDK device models for different simulation
            purposes and for different tools. Examples of device model types
            include spice, aging, electromigration, radiation. An example of a
            'spice' tool is xyce. Device models are specified on a per metal stack
            basis. Process nodes with a single device model across all stacks will
            have a unique parameter record per metal stack pointing to the same
            device model file.  Device types and tools are dynamic entries
            that depend on the tool setup and device technology. Pseud-standardized
            device types include spice, em (electromigration), and aging.""")

    corner='default'
    scparam(cfg, ['pdk', pdkname, 'pexmodel', tool, stackup, corner],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: parasitic TCAD models",
            switch="-pdk_pexmodel 'pdkname tool stackup corner <file>'",
            example=[
                "cli: -pdk_pexmodel 'asap7 fastcap M10 max wire.mod'",
                "api: chip.set('pdk','asap7','pexmodel','fastcap','M10','max','wire.mod')"],
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
                "api: chip.set('pdk','asap7','layermap','klayout','db','gds','M10','asap7.map')"],
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
                "api: chip.set('pdk','asap7','display','klayout','M10','display.cfg')"],
            schelp="""
            Display configuration files describing colors and pattern schemes for
            all layers in the PDK. The display configuration file is entered on a
            stackup and tool basis.""")

    #TODO: create firm list of accepted files
    libarch = 'default'
    scparam(cfg, ['pdk', pdkname, 'aprtech', tool, stackup, libarch, filetype],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: APR technology files",
            switch="-pdk_aprtech 'pdkname tool stackup libarch filetype <file>'",
            example=[
                "cli: -pdk_aprtech 'asap7 openroad M10 12t lef tech.lef'",
                "api: chip.set('pdk','asap7','aprtech','openroad','M10','12t','lef','tech.lef')"],
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
                    f"api: chip.set('pdk', 'asap7','{item}','runset','magic','M10','basic','$PDK/{item}.rs')"],
                schelp=f"""Runset files for {item.upper()} task.""")

        scparam(cfg, ['pdk', pdkname, item, 'waiver', tool, stackup, name],
                sctype='[file]',
                scope='global',
                shorthelp=f"PDK: {item.upper()} waiver files",
                switch=f"-pdk_{item}_waiver 'tool stackup name <file>'",
                example=[
                    f"cli: -pdk_{item}_waiver 'asap7 magic M10 basic $PDK/{item}.txt'",
                    f"api: chip.set('pdk', 'asap7','{item}','waiver','magic','M10','basic','$PDK/{item}.txt')"],
                schelp=f"""Waiver files for {item.upper()} task.""")

    ################
    # Routing grid
    ################

    layer = 'default'
    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'name'],
            sctype='str',
            scope='global',
            shorthelp="PDK: routing grid name map",
            switch="-pdk_grid_name 'pdkname stackup layer <str>'",
            example=[
                "cli: -pdk_grid_name 'asap7 M10 metal1 m1'",
                "api: chip.set('pdk','asap7','grid','M10','metal1','name','m1')"],
            schelp="""
            Maps PDK metal names to the SC standardized layer stack
            starting with m1 as the lowest routing layer and ending
            with m<n> as the highest routing layer. The map is
            specified on a per metal stack basis.""")

    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'dir'],
            sctype='str',
            scope='global',
            shorthelp="PDK: routing grid preferred direction",
            switch="-pdk_grid_dir 'pdkname stackup layer <str>'",
            example=[
                "cli: -pdk_grid_dir 'asap7 M10 m1 horizontal'",
                "api: chip.set('pdk','asap7','grid','M10','m1','dir','horizontal')"],
            schelp="""
            Preferred routing direction specified on a per stackup
            and per metal basis. Valid routing directions are horizontal
            and vertical.""")

    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'xpitch'],
            sctype='float',
            scope='global',
            unit='um',
            shorthelp="PDK: routing grid vertical wire pitch",
            switch="-pdk_grid_xpitch 'pdkname stackup layer <float>'",
            example= [
                "cli: -pdk_grid_xpitch 'asap7 M10 m1 0.5'",
                "api: chip.set('pdk', 'asap7','grid','M10','m1','xpitch','0.5')"],
            schelp="""
            Defines the routing pitch for vertical wires on a per stackup and
            per metal basis.""")

    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'ypitch'],
            sctype='float',
            scope='global',
            unit='um',
            shorthelp="PDK: routing grid horizontal wire pitch",
            switch="-pdk_grid_ypitch 'pdkname stackup layer <float>'",
            example= [
                "cli: -pdk_grid_ypitch 'asap7 M10 m1 0.5'",
                "api: chip.set('pdk','asap7','grid','M10','m1','ypitch','0.5')"],
            schelp="""
            Defines the routing pitch for horizontal wires on a per stackup and
            per metal basis.""")

    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'xoffset'],
            sctype='float',
            scope='global',
            unit='um',
            shorthelp="PDK: routing grid vertical wire offset",
            switch="-pdk_grid_xoffset 'pdkname stackup layer <float>'",
            example= [
                "cli: -pdk_grid_xoffset 'asap7 M10 m2 0.5'",
                "api: chip.set('pdk','asap7','grid','M10','m2','xoffset','0.5')"],
            schelp="""
            Defines the grid offset of a vertical metal layer specified on a per
            stackup and per metal basis.""")

    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'yoffset'],
            sctype='float',
            scope='global',
            unit='um',
            shorthelp="PDK: routing grid horizontal wire offset",
            switch="-pdk_grid_yoffset 'pdkname stackup layer <float>'",
            example= [
                "cli: -pdk_grid_yoffset 'asap7 M10 m2 0.5'",
                "api: chip.set('pdk', 'asap7','grid','M10','m2','yoffset','0.5')"],
            schelp="""
            Defines the grid offset of a horizontal metal layer specified on a per
            stackup and per metal basis.""")

    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'adj'],
            sctype='float',
            scope='global',
            shorthelp="PDK: routing grid resource adjustment",
            switch="-pdk_grid_adj 'pdkname stackup layer <float>'",
            example= [
                "cli: -pdk_grid_adj 'asap7 M10 m2 0.5'",
                "api: chip.set('pdk','asap7','grid','M10','m2','adj','0.5')"],
            schelp="""
            Defines the routing resources adjustments for the design on a per layer
            basis. The value is expressed as a fraction from 0 to 1. A value of
            0.5 reduces the routing resources by 50%. If not defined, 100%
            routing resource utilization is permitted.""")

    corner='default'
    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'cap', corner],
            sctype='float',
            scope='global',
            unit='ff/um',
            shorthelp="PDK: routing grid unit capacitance",
            switch="-pdk_grid_cap 'pdkname stackup layer corner <float>''",
            example= [
                "cli: -pdk_grid_cap 'asap7 M10 m2 fast 0.2'",
                "api: chip.set('pdk','asap7','grid','M10','m2','cap','fast','0.2')"],
            schelp="""
            Unit capacitance of a wire defined by the grid width and spacing values
            in the 'grid' structure specified on a per
            stackup, metal, and corner basis. As a rough rule of thumb, this value
            tends to stay around 0.2ff/um. This number should only be used for
            reality confirmation. Accurate analysis should use the PEX models.""")

    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'res', corner],
            sctype='float',
            scope='global',
            unit='ohm/um',
            shorthelp="PDK: routing grid unit resistance",
            switch="-pdk_grid_res 'pdkname stackup layer corner <float>''",
            example= [
                "cli: -pdk_grid_res 'asap7 M10 m2 fast 0.2'",
                "api: chip.set('pdk','asap7','grid','M10','m2','res','fast','0.2')"],
            schelp="""
            Resistance of a wire defined by the grid width and spacing values
            in the 'grid' structure specified as ohms/um on a per
            stackup, metal, and corner basis. The parameter is only meant to be
            used as a sanity check and for coarse design planning. Accurate
            analysis should use the TCAD PEX models.""")

    scparam(cfg, ['pdk', pdkname, 'grid', stackup, layer, 'tcr', corner],
            sctype='float',
            scope='global',
            unit='%/degree(T)',
            shorthelp="PDK: routing grid temperature coefficient",
            switch="-pdk_grid_tcr 'pdkname stackup layer corner <float>'",
            example= [
                "cli: -pdk_grid_tcr 'asap7 M10 m2 fast 0.2'",
                "api: chip.set('pdk','asap7','grid','M10','m2','tcr','fast','0.2')"],
            schelp="""
            Temperature coefficient of resistance of the wire defined by the grid
            width and spacing values in the 'grid' structure on a per stackup,
            layer, and corner basis. The number is only meant to be used as a
            sanity check and for coarse design planning. Accurate analysis
            should use the PEX models.""")

    ###############
    # EDA vars
    ###############

    key='default'
    scparam(cfg, ['pdk', pdkname, 'file', tool, key, stackup],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: special file",
            switch="-pdk_file 'pdkname tool key stackup <file>'",
            example=[
                "cli: -pdk_file 'asap7 xyce spice M10 asap7.sp'",
                "api: chip.set('pdk','asap7','file','xyce','spice','M10','asap7.sp')"],
            schelp="""
            List of named files specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly  supported by the SiliconCompiler PDK schema.""")

    scparam(cfg, ['pdk', pdkname, 'directory', tool, key, stackup],
            sctype='[dir]',
            scope='global',
            shorthelp="PDK: special directory",
            switch="-pdk_directory 'pdkname tool key stackup <file>'",
            example=[
                "cli: -pdk_directory 'asap7 xyce rfmodel M10 rftechdir'",
                "api: chip.set('pdk','asap7','directory','xyce','rfmodel','M10','rftechdir')"],
            schelp="""
            List of named directories specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly  supported by the SiliconCompiler PDK schema.""")

    scparam(cfg, ['pdk', pdkname, 'var', tool, key, stackup],
            sctype='[str]',
            scope='global',
            shorthelp="PDK: special variable",
            switch="-pdk_var 'pdkname tool stackup key <str>'",
            example=[
                "cli: -pdk_var 'asap7 xyce modeltype M10 bsim4'""",
                "api: chip.set('pdk','asap7','var','xyce','modeltype','M10','bsim4')"],
            schelp="""
            List of key/value strings specified on a per tool and per stackup basis.
            The parameter should only be used for specifying variables that are
            not directly  supported by the SiliconCompiler PDK schema.""")

    ###############
    # Docs
    ###############

    scparam(cfg,['pdk', pdkname, 'doc', 'homepage'],
            sctype='[file]',
            scope='global',
            shorthelp="PDK: documentation homepage",
            switch="-pdk_doc_homepage 'pdkname <file>'",
            example=["cli: -pdk_doc_homepage 'asap7 index.html'",
                     "api: chip.set('pdk','asap7','doc','homepage','index.html')"],
            schelp="""
            Filepath to PDK docs homepage. Modern PDKs can include tens or
            hundreds of individual documents. A single html entry point can
            be used to present an organized documentation dashboard to the
            designer.""")

    doctypes = ['datasheet',
                'reference',
                'userguide',
                'install',
                'quickstart',
                'releasenotes',
                'tutorial']

    for item in doctypes:
        scparam(cfg,['pdk', pdkname, 'doc', item],
                sctype='[file]',
                scope='global',
                shorthelp=f"PDK: {item}",
                switch= f"-pdk_doc_{item} 'pdkname <file>'",
                example=[f"cli: -pdk_doc_{item} 'asap7 {item}.pdf'",
                         f"api: chip.set('pdk','asap7','doc',{item},'{item}.pdf')"],
                schelp=f"""Filepath to {item} document.""")

    return cfg

###############################################################################
# Design Modeling
###############################################################################

def schema_model(cfg):

    corner = 'default'
    filetype = 'default'
    stackup =  'default'

    # functional
    scparam(cfg,['model', 'functional', filetype],
            sctype='[file]',
            scope='global',
            shorthelp=f"Model: Functional",
            switch=f"-model_functional 'filetype <file>'",
            example=[
                f"cli: -model_functional 'systemc adder.sc'",
                f"api: chip.set('model','functional','systemc','adder.sc')"],
            schelp=f"""
            Filepaths to (fast) functional models specified on a per filetype
            basis.""")

    # formal
    scparam(cfg,['model', 'formal', filetype],
            sctype='[file]',
            scope='global',
            shorthelp=f"Model: Formal",
            switch=f"-model_formal 'filetype <file>'",
            example=[
                f"cli: -model_formal 'smv adder.smv'",
                f"api: chip.set('model','formal','smv','adder.smv')"],
            schelp=f"""
            Filepaths to formal models specified on a per filetype basis.""")

    # rtl
    scparam(cfg,['model', 'rtl', filetype],
            sctype='[file]',
            scope='global',
            shorthelp=f"Model: RTL",
            switch=f"-model_rtl 'filetype <file>'",
            example=[
                f"cli: -model_rtl 'systemc adder.sc'",
                f"api: chip.set('model','rtl','systemc','adder.sc')"],
            schelp=f"""
            Filepaths to cycle accurate model specified on a per filetype
            basis.""")

    # IO
    scparam(cfg,['model', 'io', filetype],
            sctype='[file]',
            scope='global',
            shorthelp=f"Model: IO",
            switch=f"-model_io 'filetype <file>'",
            example=[
                f"cli: -model_io 'ibis top.ibs'",
                f"api: chip.set('model','io','ibis','top.ibis')"],
            schelp=f"""
            Filepaths to IO models specified on a per filetype basis.""")

    # thermal
    scparam(cfg,['model', 'thermal', filetype],
            sctype='[file]',
            scope='global',
            shorthelp=f"Model: Thermal",
            switch=f"-model_thermal 'filetype corner <file>'",
            example=[
                f"cli: -model_thermal 'delphi adder_thermal.sp'",
                f"api: chip.set('model','thermal','delphi','adder_thermal.sp')"],
            schelp=f"""
            Filepaths to thermal models.""")

    # timing
    scparam(cfg,['model', 'timing', filetype, corner],
            sctype='[file]',
            scope='global',
            shorthelp=f"Model: Timing",
            switch=f"-model_timing 'filetype corner <file>'",
            example=[
                f"cli: -model_timing 'nldm-libgz ss ss.lib.gz'",
                f"api: chip.set('model','timing','nldm-ldb','ss','ss.ldb')"],
            schelp=f"""
            Filepaths to static timing models specified on a per filetype and
            per corner basis.  Examples of filetypes include: nldm, nldm-ldb,
            nldm-libgz, ccs, ccs-libgz, ccs-ldb, scm, scm-libgz, scm-ldb,
            aocv, aocv-libgz, aocv-ldb.""")

    # power
    scparam(cfg,['model', 'power', filetype, corner],
            sctype='[file]',
            scope='global',
            shorthelp=f"Model: Power",
            switch=f"-model_power 'filetype corner <file>'",
            example=[
                f"cli: -model_power 'apl ss adder.ss.apl'",
                f"api: chip.set('model','power','apl','ss','adder.ss.apl')"],
            schelp=f"""
            Filepaths to power/current models.""")

    # layout
    scparam(cfg,['model', 'layout', filetype, stackup],
            sctype='[file]',
            scope='global',
            shorthelp=f"Model: Layout",
            switch=f"-model_layout 'filetype stackup <file>'",
            example=[
                f"cli: -model_layout 'lef 10M adder.lef'",
                f"api: chip.set('model','layout','lef','10M','adder.lef')"],
            schelp=f"""
            Filepaths to abstract layout views specified on a per filetype
            and per stackup basis.""")

    return cfg

###############################################################################
# Datasheet
###############################################################################

def schema_datasheet(cfg, design='default', name='default', mode='default'):

    # Device Features
    scparam(cfg, ['datasheet', design, 'feature', name],
            sctype='float',
            shorthelp=f"Datasheet: device feature specification",
            switch=f"-datasheet_feature 'design name <float>'",
            example=[
                f"cli: -datasheet_feature 'mydevice ram 64e6'",
                f"api: chip.set('datasheet','mydevice','feature','ram', 1e9)"],
            schelp=f"""Quantity of a specified feature. The 'unit'
            field should be used to specify the units used when unclear.""")

    # Absolute max voltage
    scparam(cfg, ['datasheet', design, 'limits', 'voltage', name],
            sctype='(float,float)',
            shorthelp=f"Datasheet: absolute voltage limits",
            switch=f"-datasheet_limits_voltage 'design pin <(float,float)>'",
            example=[
                f"cli: -datasheet_limits_voltage 'mydevice vdd (-0.4,1.1)'",
                f"api: chip.set('datasheet','mydevice','limits','voltage','vdd', (-0.4,1.1))"],
            schelp=f"""Device absolute minimum/maximum voltage not to be
            exceeded, specified on a per pin basis.""")

    # Absolute max temperatures
    metrics = {'storagetemp': 'storage temperature limits',
               'junctiontemp' :'junction temperature limits'}

    for item, val in metrics.items():
        scparam(cfg, ['datasheet', design, 'limits', item],
                sctype='(float,float)',
                shorthelp=f"Datasheet: absolute {val}",
                switch=f"-datasheet_{item} 'design <(float,float)>'",
                example=[
                    f"cli: -datasheet_{item} 'mydevice (-40,125)'",
                    f"api: chip.set('datasheet','mydevice','limits','{item}',(-40,125))"],
                schelp=f"""Device absolute {val} not to be exceeded.""")

    # Package Pin Map
    package = 'default'
    scparam(cfg, ['datasheet', design, 'pin', name, 'map', package],
            sctype='str',
            shorthelp=f"Datasheet: package pin map",
            switch=f"-datasheet_pin_map 'design name package <str>'",
            example=[
                f"cli: -datasheet_pin_map 'mydevice in0 bga512 B4'",
                f"api: chip.set('datasheet','mydevice','pin','in0','map','bga512','B4')"],
            schelp=f"""Signal to package pin mapping specified on a per package basis.""")

    # Pin type
    scparam(cfg, ['datasheet', design, 'pin', name, 'type', mode],
            sctype='str',
            shorthelp=f"Datasheet: pin type",
            switch=f"-datasheet_pin_type 'design name mode <str>'",
            example=[
                f"cli: -datasheet_pin_type 'mydevice vdd type power'",
                f"api: chip.set('datasheet','mydevice','pin','vdd','type','global','power')"],
            schelp=f"""Pin type specified on a per mode basis. Acceptable pin types
            include: digital, analog, clk, power, ground""")

    # Pin direction
    scparam(cfg, ['datasheet', design, 'pin', name, 'dir', mode],
            sctype='str',
            shorthelp=f"Datasheet: pin direction",
            switch=f"-datasheet_pin_dir 'design name mode <str>'",
            example=[
                f"cli: -datasheet_pin_dir 'mydevice clk global input'",
                f"api: chip.set('datasheet','mydevice','pin','clk','dir','global','input')"],
            schelp=f"""Pin direction specified on a per mode basis. Acceptable pin
            directions include: input, output, inout.""")

    # Complementary pin (for differential pair)
    scparam(cfg, ['datasheet', design, 'pin', name, 'complement', mode],
            sctype='str',
            shorthelp=f"Datasheet: pin complement",
            switch=f"-datasheet_pin_complement 'design name mode <str>'",
            example=[
                f"cli: -datasheet_pin_complement 'mydevice ina global inb'",
                f"api: chip.set('datasheet','mydevice','pin','ina','complement','global','inb')"],
            schelp=f"""Pin complement specified on a per mode basis for differential
            signals.""")

    # Related clock
    scparam(cfg, ['datasheet', design, 'pin', name, 'clk', mode],
                sctype='str',
                shorthelp=f"Datasheet: pin related clock",
                switch=f"-datasheet_pin_clk 'design name mode <str>'",
                example=[
                    f"cli: -datasheet_pin_clk 'mydevice ina global clka'",
                    f"api: chip.set('datasheet','mydevice','pin','ina','clk','global','clka')"],
            schelp=f"""Pin related clock specified on a per mode basis.""")

    # Related supply
    scparam(cfg, ['datasheet', design, 'pin', name, 'supply', mode],
                sctype='str',
                shorthelp=f"Datasheet: pin related power supply",
                switch=f"-datasheet_pin_supply 'design name mode <str>'",
                example=[
                    f"cli: -datasheet_pin_supply 'mydevice ina global vdd'",
                    f"api: chip.set('datasheet','mydevice','pin','ina','supply','global','vdd')"],
            schelp=f"""Pin related power supply specified on a per mode basis.""")

    # Related ground
    scparam(cfg, ['datasheet', design, 'pin', name, 'ground', mode],
                sctype='str',
                shorthelp=f"Datasheet: pin related ground",
                switch=f"-datasheet_pin_ground 'design name mode <str>'",
                example=[
                    f"cli: -datasheet_pin_ground 'mydevice ina ground vss'",
                    f"api: chip.set('datasheet','mydevice','pin','ina','ground','global','vss')"],
            schelp=f"""Pin related ground rail specified on a per mode basis.""")

    # Standard
    scparam(cfg, ['datasheet', design, 'pin', name, 'standard', mode],
            sctype='[str]',
            shorthelp=f"Datasheet: pin standard",
            switch=f"-datasheet_pin_standard 'design name mode <str>'",
            example=[
                f"cli: -datasheet_pin_standard 'mydevice ba0 global ddr4'",
                f"api: chip.set('datasheet','mydevice','pin','ina','standard','global','ddr4')"],
            schelp=f"""Pin communication standard specified on a per mode basis.""")

    # Reset value
    scparam(cfg, ['datasheet', design, 'pin', name, 'resetvalue', mode],
            sctype='[str]',
            shorthelp=f"Datasheet: pin reset value",
            switch=f"-datasheet_pin_resetvalue 'design name mode <str>'",
            example=[
                f"cli: -datasheet_pin_resetvalue 'mydevice clk global weak1'",
                f"api: chip.set('datasheet','mydevice','pin','clk','resetvalue','global','weak1')"],
            schelp=f"""Pin reset value specified on a per mode basis. Legal reset
            values include weak1, weak0, strong0, strong1, highz.""")

    # DC levels
    metrics = {'vol': ['low output voltage level', (-0.2,0,0.2), 'V'],
               'voh': ['high output voltage level', (4.6,4.8,5.2), 'V'],
               'vil': ['low input voltage level', (-0.2, 0, 1.0), 'V'],
               'vih': ['high input voltage level', (1.4, 1.8, 2.2), 'V'],
               'vcm': ['common mode voltage', (0.3, 1.2, 1.6), 'V'],
               'vdiff': ['differential voltage', (0.2, 0.3, 0.9), 'V'],
               'vnoise': ['random voltage noise', (0,0.01,0.1), 'V'],
               'vhbm': ['machine model ESD tolerance', (100, 300, 500), 'V'],
               'vcdm': ['human body model ESD tolerance', (100,300,500), 'V'],
               'rdiff': ['differential pair resistance', (45,50,55), 'ohm'],
               'rpullup': ['pullup resistance', (1000, 1200, 3000), 'ohm'],
               'rpulldown': ['pulldown resistance', (1000, 1200, 3000), 'ohm'],
               'idrive': ['drive current', (10e-3, 12e-3, 15e-3), 'A'],
               'iinject': ['injection current', (1e-3, 1.2e-3, 1.5e-3), 'A'],
               'ileakage': ['leakage current', (1e-6, 1.2e-6, 1.5e-6), 'A'],
               'capacitance': ['capacitance', (1e-12, 1.2e-12, 1.5e-12), 'F']}

    for item, val in metrics.items():
        scparam(cfg, ['datasheet', design, 'pin', name, item, mode],
                unit=val[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: {val[0]}",
                switch=f"-datasheet_pin_{item} 'design pin mode <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_pin_{item} 'mydevice sclk global {val[1]}'",
                    f"api: chip.set('datasheet','mydevice','pin','sclk','{item}','global',{val[1]}"],
                schelp=f"""Pin {val[0]}. Values are tuples of (min, typical, max).""")

    # AC Timing
    metrics = {'tsetup': ['setup time', (1e-9, 2e-9, 4e-9), 's'],
               'thold': ['hold time', (1e-9, 2e-9, 4e-9), 's'],
               'trise': ['rise transition', (1e-9, 2e-9, 4e-9), 's'],
               'tfall': ['fall transition', (1e-9, 2e-9, 4e-9), 's'],
               'tperiod': ['minimum period', (1e-9, 2e-9, 4e-9), 's'],
               'tpulse': ['pulse width', (1e-9, 2e-9, 4e-9), 's'],
               'tjitter': ['rms jitter', (1e-9, 2e-9, 4e-9), 's'],
               'dutycycle': ['duty cycle', (45, 50, 55), '%']}

    for item, val in metrics.items():
        scparam(cfg, ['datasheet', design, 'pin', name, item, mode],
                unit=val[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: {val[0]}",
                switch=f"-datasheet_pin_{item} 'design pin mode <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_pin_{item} 'mydevice sclk global {val[1]}'",
                    f"api: chip.set('datasheet','mydevice','pin','sclk','{item}','global',{val[1]}"],
                schelp=f"""Pin {val[0]}. Values are tuples of (min, typical, max).""")

    return cfg

###############################################################################
# Flow Configuration
###############################################################################

def schema_flowgraph(cfg, flow='default', step='default', index='default'):

    # flowgraph input
    scparam(cfg,['flowgraph', flow, step, index, 'input'],
            sctype='[(str,str)]',
            shorthelp="Flowgraph: step input",
            switch="-flowgraph_input 'flow step index <(str,str)>'",
            example=[
                "cli: -flowgraph_input 'asicflow cts 0 (place,0)'",
                "api:  chip.set('flowgraph','asicflow','cts','0','input',('place','0'))"],
            schelp="""A list of inputs for the current step and index, specified as a
            (step,index) tuple.""")

    # flowgraph metric weights
    metric='default'
    scparam(cfg,['flowgraph', flow, step, index, 'weight', metric],
            sctype='float',
            shorthelp="Flowgraph: metric weights",
            switch="-flowgraph_weight 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_weight 'asicflow cts 0 area_cells 1.0'",
                "api:  chip.set('flowgraph','asicflow','cts','0','weight','area_cells',1.0)"],
            schelp="""Weights specified on a per step and per metric basis used to give
            effective "goodnes" score for a step by calculating the sum all step
            real metrics results by the corresponding per step weights.""")

    scparam(cfg,['flowgraph', flow, step, index, 'goal', metric],
            sctype='float',
            shorthelp="Flowgraph: metric goals",
            switch="-flowgraph_goal 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_goal 'asicflow cts 0 area_cells 1.0'",
                "api:  chip.set('flowgraph','asicflow','cts','0','goal','errors', 0)"],
            schelp="""Goals specified on a per step and per metric basis used to
            determine whether a certain task can be considered when merging
            multiple tasks at a minimum or maximum node. A task is considered
            failing if the absolute value of any of its metrics are larger than
            the goal for that metric, if set.""")

    # flowgraph tool
    scparam(cfg,['flowgraph', flow, step, index, 'tool'],
            sctype='str',
            shorthelp="Flowgraph: tool selection",
            switch="-flowgraph_tool 'flow step <str>'",
            example=[
                "cli: -flowgraph_tool 'asicflow place 0 openroad'",
                "api: chip.set('flowgraph','asicflow','place','0','tool','openroad')"],
            schelp="""Name of the tool name used for task execution. Builtin tool names
            associated bound to core API functions include: minimum, maximum, join,
            verify, mux.""")

    # flowgraph arguments
    scparam(cfg,['flowgraph', flow, step, index, 'args'],
            sctype='[str]',
            shorthelp="Flowgraph: setup arguments",
            switch="-flowgraph_args 'flow step index <str>'",
            example=[
                "cli: -flowgraph_args 'asicflow cts 0 0'",
                "api:  chip.add('flowgraph','asicflow','cts','0','args','0')"],
            schelp="""User specified flowgraph string arguments specified on a per
            step and per index basis.""")

    # flowgraph valid bits
    scparam(cfg,['flowgraph', flow, step, index, 'valid'],
            sctype='bool',
            shorthelp="Flowgraph: task valid bit",
            switch="-flowgraph_valid 'flow step index <str>'",
            example=[
                "cli: -flowgraph_valid 'asicflow cts 0 true'",
                "api:  chip.set('flowgraph','asicflow','cts','0','valid',True)"],
            schelp="""Flowgraph valid bit specified on a per step and per index basis.
            The parameter can be used to control flow execution. If the bit
            is cleared (0), then the step/index combination is invalid and
            should not be run.""")

    # flowgraph timeout value
    scparam(cfg,['flowgraph', flow, step, index, 'timeout'],
            sctype='float',
            unit='s',
            shorthelp="Flowgraph: task timeout value",
            switch="-flowgraph_timeout 'flow step 0 <float>'",
            example=[
                "cli: -flowgraph_timeout 'asicflow cts 0 3600'",
                "api:  chip.set('flowgraph','asicflow','cts','0','timeout', 3600)"],
            schelp="""Timeout value in seconds specified on a per step and per index
            basis. The flowgraph timeout value is compared against the
            wall time tracked by the SC runtime to determine if an
            operation should continue. Timeout values help in situations
            where 1.) an operation is stuck and may never finish. 2.) the
            operation progress has saturated and continued execution has
            a negative return on investment.""")

    # flowgraph status
    scparam(cfg,['flowgraph', flow, step, index, 'status'],
            sctype='str',
            shorthelp="Flowgraph: task status",
            switch="-flowgraph_status 'flow step index <str>'",
            example=[
                "cli: -flowgraph_status 'asicflow cts 10 success'",
                "api:  chip.set('flowgraph','asicflow', 'cts','10','status', 'success')"],
            schelp="""Parameter that tracks the status of a task. Valid values are:

            * "success": task ran successfully
            * "error": task failed with an error

            An empty value indicates the task has not yet been completed.""")

    # flowgraph select
    scparam(cfg,['flowgraph', flow, step, index, 'select'],
            sctype='[(str,str)]',
            shorthelp="Flowgraph: task select record",
            switch="-flowgraph_select 'flow step index <(str,str)>'",
            example= [
                "cli: -flowgraph_select 'asicflow cts 0 (place,42)'",
                "api:  chip.set('flowgraph','asicflow', 'cts','0','select',('place','42'))"],
            schelp="""
            List of selected inputs for the current step/index specified as
            (in_step,in_index) tuple.""")

    return cfg


###########################################################################
# Tool Setup
###########################################################################

def schema_tool(cfg, tool='default', step='default', index='default'):

    key = 'default'
    suffix = 'default'
    metric = 'default'

    scparam(cfg, ['tool', tool, 'exe'],
            sctype='str',
            shorthelp="Tool: executable name",
            switch="-tool_exe 'tool <str>'",
            example=["cli: -tool_exe 'openroad openroad'",
                     "api:  chip.set('tool','openroad','exe','openroad')"],
            schelp="""Tool executable name.""")

    scparam(cfg, ['tool', tool, 'path'],
            sctype='dir',
            shorthelp="Tool: executable path",
            switch="-tool_path 'tool <dir>'",
            example=["cli: -tool_path 'openroad /usr/local/bin'",
                     "api:  chip.set('tool','openroad','path','/usr/local/bin')"],
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
                     "api:  chip.set('tool','openroad','vswitch','-version')"],
            schelp="""
            Command line switch to use with executable used to print out
            the version number. Common switches include -v, -version,
            --version. Some tools may require extra flags to run in batch mode.""")

    scparam(cfg, ['tool', tool, 'vendor'],
            sctype='str',
            shorthelp="Tool: vendor",
            switch="-tool_vendor 'tool <str>'",
            example=["cli: -tool_vendor 'yosys yosys'",
                     "api: chip.set('tool','yosys','vendor','yosys')"],
            schelp="""
            Name of the tool vendor. Parameter can be used to set vendor
            specific technology variables in the PDK and libraries. For
            open source projects, the project name should be used in
            place of vendor.""")

    scparam(cfg, ['tool', tool, 'version'],
            sctype='[str]',
            shorthelp="Tool: version",
            switch="-tool_version 'tool <str>'",
            example=["cli: -tool_version 'openroad >=v2.0'",
                     "api:  chip.set('tool','openroad','version','>=v2.0')"],
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
            sctype='str',
            shorthelp="Tool: manifest file format",
            switch="-tool_format 'tool <file>'",
            example=[ "cli: -tool_format 'yosys tcl'",
                      "api: chip.set('tool','yosys','format','tcl')"],
            schelp="""
            File format for tool manifest handoff. Supported formats are tcl,
            yaml, and json.""")

    scparam(cfg, ['tool', tool, 'warningoff'],
            sctype='[str]',
            shorthelp="Tool: warning filter",
            switch="-tool_warningoff 'tool <str>'",
            example=["cli: -tool_warningoff 'verilator COMBDLY'",
                     "api: chip.set('tool','verilator','warningoff','COMBDLY')"],
            schelp="""
            A list of EDA warnings for which printing should be suppressed.
            Generally this is done on a per design basis after review has
            determined that warning can be safely ignored The code for turning
            off warnings can be found in the specific tool reference manual.
            """)

    scparam(cfg, ['tool', tool, 'continue'],
            sctype='bool',
            shorthelp="Tool: continue-on-error option",
            switch="-tool_continue 'tool <bool>'",
            example=["cli: -tool_continue 'verilator true'",
                     "api: chip.set('tool','verilator','continue', true)"],
            schelp="""
            Directs tool to continue operating even if errors are
            encountered.""")

    scparam(cfg, ['tool', tool, 'licenseserver', key],
            sctype='[str]',
            shorthelp="Tool: license servers",
            switch="-tool_licenseserver 'name key <str>'",
            example=[
                "cli: -tool_licenseserver 'atool ACME_LICENSE 1700@server'",
                "api: chip.set('tool','atool','licenseserver','ACME_LICENSE','1700@server')"],
            schelp="""
            Defines a set of tool specific environment variables used by the executables
            that depend on license key servers to control access. For multiple servers,
            separate each server by a 'colon'. The named license variable are read at
            runtime (run()) and the environment variables are set.
            """)

    #######################
    # Per step/index
    ########################

    scparam(cfg, ['tool', tool, 'regex', step, index, suffix],
            sctype='[str]',
            shorthelp="Tool: regex filter",
            switch="-tool_regex 'tool step index suffix <str>'",
            example=[
                "cli: -tool_regex 'openroad place 0 errors -v ERROR'",
                "api: chip.set('tool','openroad','regex','place','0','errors','-v ERROR')"],
            schelp="""
            A list of piped together grep commands. Each entry represents a set
            of command line arguments for grep including the regex pattern to
            match. Starting with the first list entry, each grep output is piped
            into the following grep command in the list. Supported grep options
            include ``-v`` and ``-e``. Patterns starting with "-" should be
            directly preceeded by the ``-e`` option. The following example
            illustrates the concept.

            UNIX grep:

            .. code-block:: bash

                $ grep WARNING place.log | grep -v "bbox" > place.warnings

            SiliconCompiler::

                chip.set('tool', 'openroad', 'regex', 'place', '0', 'warnings', ["WARNING", "-v bbox"])

            The "errors" and "warnings" suffixes are special cases. When set,
            the number of matches found for these regexes will be added to the
            errors and warnings metrics for the task, respectively. This will
            also cause the logfile to be added to the :keypath:`tool, <tool>,
            report` parameter for those metrics, if not already present.""")


    scparam(cfg, ['tool', tool, 'option', step, index],
            sctype='[str]',
            shorthelp="Tool: executable options",
            switch="-tool_option 'tool step index <str>'",
            example=[
                "cli: -tool_option 'openroad cts 0 -no_init'",
                "api: chip.set('tool','openroad','option','cts','0','-no_init')"],
            schelp="""
            List of command line options for the tool executable, specified on
            a per tool and per step basis. Options must not include spaces.
            For multiple argument options, each option is a separate list element.
            """)

    scparam(cfg, ['tool', tool, 'var', step, index, key],
            sctype='[str]',
            shorthelp="Tool: script variables",
            switch="-tool_variable 'tool step index key <str>'",
            example=[
                "cli: -tool_variable 'openroad cts 0 myvar 42'",
                "api: chip.set('tool','openroad','var','cts','0','myvar','42')"],
            schelp="""
            Tool script variables specified as key value pairs. Variable
            names and value types must match the name and type of tool and reference
            script consuming the variable.""")

    scparam(cfg, ['tool', tool, 'env', step, index, key],
            sctype='str',
            shorthelp="Tool: environment variables",
            switch="-tool_env 'tool step index name <str>'",
            example=[
                "cli: -tool_env 'openroad cts 0 MYVAR 42'",
                "api: chip.set('tool','openroad','env','cts','0','MYVAR','42')"],
            schelp="""
            Environment variables to set for individual tasks. Keys and values
            should be set in accordance with the tool's documentation. Most
            tools do not require extra environment variables to function.""")

    scparam(cfg, ['tool', tool, 'input', step, index],
            sctype='[file]',
            shorthelp="Tool: input files",
            switch="-tool_input 'tool step index <str>'",
            example=[
                "cli: -tool_input 'openroad place 0 oh_add.def'",
                "api: chip.set('tool','openroad','input','place','0','oh_add.def')"],
            schelp="""
            List of data files to be copied from previous flowgraph steps 'output'
            directory. The list of steps to copy files from is defined by the
            list defined by the dictionary key ['flowgraph', step, index, 'input'].
            All files must be available for flow to continue. If a file
            is missing, the program exists on an error.""")

    scparam(cfg, ['tool', tool, 'output', step, index],
            sctype='[file]',
            shorthelp="Tool: output files",
            switch="-tool_output 'tool step index <str>'",
            example=[
                "cli: -tool_output 'openroad place 0 oh_add.def'",
                "api: chip.set('tool','openroad','output','place','0','oh_add.def')"],
            schelp="""
            List of data files to be copied from previous flowgraph steps 'output'
            directory. The list of steps to copy files from is defined by the
            list defined by the dictionary key ['flowgraph', step, index, 'output'].
            All files must be available for flow to continue. If a file
            is missing, the program exists on an error.""")

    scparam(cfg, ['tool', tool, 'stdout', step, index, 'destination'],
            sctype='str',
            defvalue='log',
            scope='job',
            shorthelp="Tool: Destination for stdout",
            switch="-tool_stdout_destination 'tool step index [log|output|none]'",
            example=["cli: -tool_stdout_destination 'ghdl import 0 log'",
                    "api: chip.set('tool','ghdl','stdout','import','0','destination','log')"],
            schelp="""
            Defines where to direct the output generated over stdout.
            Supported options are:
            none: the stream generated to STDOUT is ignored
            log: the generated stream is stored in <step>.<suffix>; if not in quiet mode,
            it is additionally dumped to the display output: the generated stream is stored
            in outputs/<design>.<suffix>""")

    scparam(cfg, ['tool', tool, 'stdout', step, index, 'suffix'],
            sctype='str',
            defvalue='log',
            scope='job',
            shorthelp="Tool: File suffix for redirected stdout",
            switch="-tool_stdout_suffix 'tool step index <str>'",
            example=["cli: -tool_stdout_suffix 'ghdl import 0 log'",
                    "api: chip.set('tool','ghdl','stdout','import','0','suffix','log')"],
            schelp="""
            Specifies the file extension for the content redirected from stdout.""")

    scparam(cfg, ['tool', tool, 'stderr', step, index, 'destination'],
            sctype='str',
            defvalue='log',
            scope='job',
            shorthelp="Tool: Destination for stderr",
            switch="-tool_stderr_destination 'tool step index [log|output|none]'",
            example=["cli: -tool_stderr_destination 'ghdl import 0 log'",
                    "api: chip.set('tool','ghdl','stderr','import','0','destination','log')"],
            schelp="""
            Defines where to direct the output generated over stderr.
            Supported options are:
            none: the stream generated to STDERR is ignored
            log: the generated stream is stored in <step>.<suffix>; if not in quiet mode,
            it is additionally dumped to the display output: the generated stream is
            stored in outputs/<design>.<suffix>""")

    scparam(cfg, ['tool', tool, 'stderr', step, index, 'suffix'],
            sctype='str',
            defvalue='log',
            scope='job',
            shorthelp="Tool: File suffix for redirected stderr",
            switch="-tool_stderr_suffix 'tool step index <str>'",
            example=["cli: -tool_stderr_suffix 'ghdl import 0 log'",
                    "api: chip.set('tool','ghdl','stderr','import','0','suffix','log')"],
            schelp="""
            Specifies the file extension for the content redirected from stderr.""")

    scparam(cfg, ['tool', tool, 'require', step, index],
            sctype='[str]',
            shorthelp="Tool: parameter requirements",
            switch="-tool_require 'tool step index <str>'",
            example=[
                "cli: -tool_require 'openroad cts 0 design'",
                "api: chip.set('tool','openroad','require','cts','0','design')"],
            schelp="""
            List of keypaths to required tool parameters. The list is used
            by check() to verify that all parameters have been set up before
            step execution begins.""")

    scparam(cfg, ['tool', tool, 'report', step, index, metric],
            sctype='[file]',
            shorthelp="Tool: report files",
            switch="-tool_report 'tool step index metric <str>'",
            example=[
                 "cli: -tool_report 'openroad place 0 holdtns place.log'",
                "api: chip.set('tool','openroad','report','syn','0','holdtns','place.log')"],
            schelp="""
            List of report files associated with a specific 'metric'. The file path
            specified is relative to the run directory of the current task.""")

    scparam(cfg, ['tool', tool, 'refdir', step, index],
            sctype='[dir]',
            shorthelp="Tool: script directory",
            switch="-tool_refdir 'tool step index <dir>'",
            example=[
                "cli: -tool_refdir 'yosys syn 0 ./myref'",
                "api:  chip.set('tool','yosys','refdir','syn','0','./myref')"],
            schelp="""
            Path to directories containing reference flow scripts, specified
            on a per step and index basis.""")

    scparam(cfg, ['tool', tool, 'script', step, index],
            sctype='[file]',
            shorthelp="Tool: entry script",
            switch="-tool_script 'tool step index <file>'",
            example=[
                "cli: -tool_script 'yosys syn 0 syn.tcl'",
                "api: chip.set('tool','yosys','script','syn','0','syn.tcl')"],
            schelp="""
            Path to the entry script called by the executable specified
            on a per tool and per step basis.""")

    scparam(cfg, ['tool', tool, 'keep', step, index],
            sctype='[str]',
            shorthelp="Tool: files to keep",
            switch="-tool_keep 'tool step index <str>'",
            example=[
                "cli: -tool_keep 'surelog import 0 slp_all'",
                "api: chip.set('tool','surelog','script','import','0','slpp_all')"],
            schelp="""
            Names of additional files and directories in the work directory that
            should be kept when :keypath:`option, clean` is true.""")

    scparam(cfg, ['tool', tool, 'threads', step, index],
            sctype='int',
            shorthelp="Tool: thread parallelism",
            switch="-tool_threads 'tool step index <int>'",
            example=["cli: -tool_threads 'magic drc 0 64'",
                     "api: chip.set('tool','magic','threads','drc','0','64')"],
            schelp="""
            Thread parallelism to use for execution specified on a per tool and per
            step basis. If not specified, SC queries the operating system and sets
            the threads based on the maximum thread count supported by the
            hardware.""")

    return cfg

###########################################################################
#  Function arguments
###########################################################################

def schema_arg(cfg):

    key = 'default'
    scparam(cfg, ['arg', 'pdk', key],
            sctype='[str]',
            scope='scratch',
            shorthelp="ARG: PDK argument",
            switch="-arg_pdk 'key <str>",
            example=[
                "cli: -arg_pdk 'mimcap true'",
                "api: chip.set('arg','pdk','mimcap','true')"],
            schelp="""
            Parameter passed in as key/value pair to the technology target
            referenced in the load_pdk() API call. See the target technology
            for specific guidelines regarding configuration parameters.""")

    scparam(cfg, ['arg', 'flow', key],
            sctype='[str]',
            scope='scratch',
            shorthelp="ARG: Flow argument",
            switch="-arg_flow 'key <str>'",
            example=[
                "cli: -arg_flow 'n 100'",
                "api: chip.set('arg','flow','n', 100)"],
            schelp="""
            Parameter passed in as key/value pair to the flow target
            referenced in the load_flow() API call. See the target flow
            for specific guidelines regarding configuration parameters.""")

    scparam(cfg, ['arg', 'step'],
            sctype='str',
            scope='scratch',
            shorthelp="ARG: Step argument",
            switch="-arg_step <str>",
            example=["cli: -arg_step 'route'",
                    "api: chip.set('arg', 'step', 'route')"],
            schelp="""
            Dynamic parameter passed in by the sc runtime as an argument to
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
                    "api: chip.set('arg','index','0')"],
            schelp="""
            Dynamic parameter passed in by the sc runtime as an argument to
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
               'warnings' :'warnings',
               'drvs' : 'design rule violations',
               'unconstrained' : 'unconstrained timing paths'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item],
                sctype='int',
                shorthelp=f"Metric: total {item}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'dfm 0 0'",
                    f"api: chip.set('metric','dfm','0','{item}', 0)"],
                schelp=f"""Metric tracking the total number of {val} on a
                per step and index basis.""")

    scparam(cfg, ['metric', step, index, 'coverage'],
            sctype='float',
            unit='%',
            shorthelp=f"Metric: coverage",
            switch="-metric_coverage 'step index <float>'",
            example=[
                "cli: -metric_coverage 'place 0 99.9'",
                "api: chip.set('metric','place','0','coverage', 99.9)"],
            schelp=f"""
            Metric tracking the test coverage in the design expressed as a percentage
            with 100 meaning full coverage. The meaning of the metric depends on the
            task being executed. It can refer to code coverage, feature coverage,
            stuck at fault coverage.""")

    scparam(cfg, ['metric', step, index, 'security'],
            sctype='float',
            unit='%',
            shorthelp="Metric: security",
            switch="-metric_security 'step index <float>'",
            example=[
                "cli: -metric_security 'place 0 100'",
                "api: chip.set('metric','place','0','security', 100)"],
            schelp=f"""
            Metric tracking the level of security (1/vulnerability) of the design.
            A completely secure design would have a score of 100. There is no
            absolute scale for the security metrics (like with power, area, etc)
            so the metric will be task and tool dependent.""")

    metrics = {'luts': 'FPGA LUTs',
               'dsps' :'FPGA DSP slices',
               'brams' : 'FPGA BRAM tiles'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item],
                sctype='int',

                shorthelp=f"Metric: {val}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100'",
                    f"api: chip.set('metric','place','0','{item}', 100)"],
                schelp=f"""
                Metric tracking the total {val} used by the design as reported
                by the implementation tool. There is no standardized definition
                for this metric across vendors, so metric comparisons can
                generally only be done between runs on identical tools and
                device families.""")

    metrics = {'cellarea': 'cell area (ignoring fillers)',
               'totalarea' :'physical die area'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item],
                sctype='float',
                unit='um^2',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100.00'",
                    f"api: chip.set('metric','place','0','{item}', 100.00)"],
                schelp=f"""
                Metric tracking the total {val} occupied by the design.""")

    scparam(cfg, ['metric', step, index, 'utilization'],
            sctype='float',
            unit='%',
            shorthelp=f"Metric: area utilization",
            switch=f"-metric_utilization step index <float>",
            example=[
                f"cli: -metric_utilization 'place 0 50.00'",
                f"api: chip.set('metric','place','0','utilization', 50.00)"],
            schelp=f"""
            Metric tracking the area utilization of the design calculated as
            100 * (cellarea/totalarea).""")

    metrics = {'peakpower': 'worst case total peak power',
               'averagepower': 'average workload power',
               'dozepower': 'power consumed while in low frequency operating mode',
               'idlepower': 'power while not performing useful work',
               'leakagepower' :'leakage power with rails active but without any dynamic switching activity',
               'sleeppower': 'power consumed with some or all power rails gated off'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item],
                sctype='float',
                unit='mw',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 0.01'",
                    f"api: chip.set('metric','place','0','{item}', 0.01)"],
                schelp=f"""
                Metric tracking the {val} of the design specified on a per step
                and index basis. Power metric depend heavily on the method
                being used for extraction: dynamic vs static, workload
                specification (vcd vs saif), power models, process/voltage/temperature.
                The power {item} metric tries to capture the data that would
                usually be reflected inside a datasheet given the approprate
                footnote conditions.""")

    scparam(cfg, ['metric', step, index, 'irdrop'],
            sctype='float',
            unit='mv',
            shorthelp=f"Metric: peak IR drop",
            switch="-metric_irdrop 'step index <float>'",
            example=[
                f"cli: -metric_irdrop 'place 0 0.05'",
                f"api: chip.set('metric','place','0','irdrop', 0.05)"],
            schelp=f"""
            Metric tracking the peak IR drop in the design based on extracted
            power and ground rail parasitics, library power models, and
            switching activity. The switching activity calculated on a per
            node basis is taken from one of three possible sources, in order
            of priority: VCD file, SAIF file, 'activityfactor' parameter.""")

    metrics = {'holdpaths': 'hold',
               'setuppaths': 'setup'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item],
                sctype='int',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 10'",
                    f"api: chip.set('metric','place','0','{item}', 10)"],
                schelp=f"""
                Metric tracking the total number of timing paths violating {val}
                constraints.""")

    metrics = {'holdslack': 'worst hold slack (positive or negative)',
               'holdwns': 'worst negative hold slack (positive values truncated to zero)',
               'holdtns': 'total negative hold slack (TNS)',
               'setupslack': 'worst setup slack (positive or negative)',
               'setupwns': 'worst negative setup slack (positive values truncated to zero)',
               'setuptns': 'total negative setup slack (TNS)'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item],
                sctype='float',
                unit='ns',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 0.01'",
                    f"api: chip.set('metric','place','0','{item}', 0.01)"],
                schelp=f"""
                Metric tracking the {val} on a per step and index basis.""")

    metrics = {'macros': 'macros',
               'cells': 'cell instances',
               'registers': 'register instances',
               'buffers': 'buffer and inverter instances',
               'transistors': 'transistors',
               'pins': 'pins',
               'nets': 'nets',
               'vias': 'vias'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item],
                sctype='int',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100'",
                    f"api: chip.set('metric','place','0','{item}', 50)"],
                schelp=f"""
                Metric tracking the total number of {val} in the design
                on a per step and index basis.""")

    item = 'wirelength'
    scparam(cfg, ['metric', step, index, item],
            sctype='float',
            unit='um',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'place 0 100.0'",
                f"api: chip.set('metric','place','0','{item}', 50.0)"],
            schelp=f"""
            Metric tracking the total {item} of the design on a per step
            and index basis.""")

    item = 'overflow'
    scparam(cfg, ['metric', step, index, item],
            sctype='int',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'place 0 0'",
                f"api: chip.set('metric','place','0','{item}', 50)"],
            schelp=f"""
            Metric tracking the total number of overflow tracks for the routing
            on per step and index basis. Any non-zero number suggests an over
            congested design. To analyze where the congestion is occurring
            inspect the router log files for detailed per metal overflow
            reporting and open up the design to find routing hotspots.""")

    item = 'memory'
    scparam(cfg, ['metric', step, index, item],
            sctype='float',
            unit='B',
            scope='job',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 10e9'",
                f"api: chip.set('metric','dfm','0','{item}', 10e9)"],
            schelp=f"""
            Metric tracking total peak program memory footprint on a per
            step and index basis.""")

    item = 'exetime'
    scparam(cfg, ['metric', step, index, item],
            sctype='float',
            unit='s',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 10.0'",
                f"api: chip.set('metric','dfm','0','{item}', 10.0)"],
            schelp=f"""
            Metric tracking time spent by the eda executable 'exe' on a
            per step and index basis. It does not include the siliconcompiler
            runtime overhead or time waitig for I/O operations and
            inter-processor communication to complete.""")

    item = 'tasktime'
    scparam(cfg, ['metric', step, index, item],
            sctype='float',
            unit='s',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 10.0'",
                f"api: chip.set('metric','dfm','0','{item}', 10.0)"],
            schelp=f"""
            Metric trakcing the total amount of time spent on a task from
            beginning to end, including data transfers and pre/post
            processing.""")

    item = 'totaltime'
    scparam(cfg, ['metric', step, index, item],
            sctype='float',
            unit='s',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 10.0'",
                f"api: chip.set('metric','dfm','0','{item}', 10.0)"],
            schelp=f"""
            Metric tracking the total amount of time spent from the beginning
            of the run up to and including the current step and index.""")

    return cfg

###########################################################################
# Design Tracking
###########################################################################

def schema_record(cfg, step='default', index='default'):

    # setting up local data structure
    # <key>  : ['short help', 'example' 'extended help']

    records = {'userid': ['userid',
                          'wiley',
                          ''],
               'publickey' : ['public key',
                              '<key>',
                              ''],
               'machine' : ['machine name',
                            'carbon',
                            '(myhost, localhost, ...'],
               'macaddr' : ['MAC address',
                            '<addr>',
                            ''],
               'ipaddr' : ['IP address',
                           '<addr>',
                           ''],
               'platform' : ['platform name',
                             'linux',
                             '(linux, windows, freebsd)'],
               'distro' : ['distro name',
                           'ubuntu',
                           '(ubuntu, redhat, centos)'],
               'arch' : ['hardware architecture',
                         'x86_64',
                         '(x86_64, rv64imafdc)'],
               'starttime' : ['start time',
                              '2021-09-06 12:20:20',
                              'Time is reported in the ISO 8601 format YYYY-MM-DD HR:MIN:SEC'],
               'endtime' : ['end time',
                            '2021-09-06 12:20:20',
                            'Time is reported in the ISO 8601 format YYYY-MM-DD HR:MIN:SEC'],
               'region' : ['cloud region',
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
                               """The tool version captured correspnds to the 'tool'
                               parameter within the 'eda' dictionary."""],
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
               'kernelversion' : ['O/S kernel version',
                                  '5.11.0-34-generic',
                                  """Used for platforms that support a distinction
                                  between os kernels and os distributions."""]
    }

    for item,val in records.items():
        helpext = utils.trim(val[2])
        scparam(cfg, ['record', step, index, item],
                sctype='str',
                shorthelp=f"Record: {val[0]}",
                switch=f"-record_{item} 'step index <str>'",
                example=[
                    f"cli: -record_{item} 'dfm 0 <{val[1]}>'",
                    f"api: chip.set('record','dfm','0','{item}', <{val[1]}>)"],
                schelp=f'Record tracking the {val[0]} per step and index basis. {helpext}')

    return cfg

###########################################################################
# Global units
###########################################################################

def schema_unit(cfg):
    '''

    '''

    units = {
        'time' : 'ns',
        'length' : 'um',
        'mass' : 'g',
        'capacitance' : 'pf',
        'resistance' : 'ohm',
        'inductance' : 'nh',
        'voltage' : 'mv',
        'current' : 'ma',
        'power' : 'mw',
        'energy' : 'pj'
    }

    for item,val in units.items():
        scparam(cfg, ['unit', item],
                sctype='str',
                defvalue=val,
                shorthelp=f"Unit: {item}",
                switch=f"-unit_{item} '<str>'",
                example=[
                    f"cli: -unit_{item} '{val}'",
                    f"api: chip.set('unit','{item}',{val})"],
                schelp=f"""
                Units used for {item} when not explicitly specified.""")

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
                "api: chip.set('option','remote', True)"],
            schelp="""
            Sends job for remote processing if set to true. The remote
            option requires a credentials file to be placed in the home
            directory. Fore more information, see the credentials
            parameter.""")

    scparam(cfg, ['option', 'credentials'],
            sctype='[file]',
            scope='job',
            shorthelp="User credentials file",
            switch="-credentials <file>'",
            example=[
                "cli: -credentials /home/user/.sc/credentials",
                "api: chip.set('option', 'credentials','/home/user/.sc/credentials')"],
            schelp="""
            Filepath to credentials used for remote processing. If the
            credentials parameter is empty, the remote processing client program
            tries to access the ".sc/credentials" file in the user's home
            directory. The file supports the following fields:

            userid=<user id>
            secret_key=<secret key used for authentication>
            server=<ipaddr or url>""")

    scparam(cfg, ['option', 'jobscheduler'],
            sctype='str',
            scope='job',
            shorthelp="Job scheduler name",
            switch="-jobscheduler <str>",
            example=[
                "cli: -jobscheduler slurm",
                "api: chip.set('option','jobscheduler','slurm')"],
            schelp="""
            Sets the type of job scheduler to be used for each individual
            flowgraph steps. If the parameter is undefined, the steps are executed
            on the same machine that the SC was launched on. If 'slurm' is used,
            the host running the 'sc' command must be running a 'slurmctld' daemon
            managing a Slurm cluster. Additionally, the build directory ('-dir')
            must be located in shared storage which can be accessed by all hosts
            in the cluster.""")

    # Compilation
    scparam(cfg, ['option', 'mode'],
            sctype='str',
            scope='job',
            shorthelp="Compilation mode",
            switch="-mode <str>",
            example=[
            "cli: -mode asic",
            "api: chip.set('option','mode','asic')"],
            schelp="""
            Sets the operating mode of the compiler. Valid modes are:
            asic: RTL to GDS ASIC compilation
            fpga: RTL to bitstream FPGA compilation
            sim: simulation to verify design and compilation
            """)

    scparam(cfg, ['option','target'],
            sctype='str',
            scope='job',
            shorthelp="Compilation target",
            switch="-target <str>",
            example=["cli: -target freepdk45_demo",
                     "api: chip.set('option','target','freepdk45_demo')"],
            schelp="""
            Sets a target module to be used for compilation. The target
            module must set up all paramaters needed. The target module
            may load multiple flows and libraries.
            """)

    scparam(cfg, ['option','flow'],
            sctype='str',
            scope='job',
            shorthelp="Flow target",
            switch="-flow <str>",
            example=["cli: -flow asicfow",
                     "api: chip.set('option','flow','asicflow')"],
            schelp="""
            Sets the flow for the current run. The flow name
            must match up with a 'flow' in the flowgraph""")

    scparam(cfg, ['option','pdk'],
            sctype='str',
            scope='job',
            shorthelp="PDK target",
            switch="-pdk <str>",
            example=["cli: -pdk asap7",
                     "api: chip.set('option','pdk','asap7')"],
            schelp="""
            Sets the pdk for the current run. The pdk name
            must match up with a 'pdk' loaded with load_pdk.""")

    scparam(cfg, ['option','optmode'],
            sctype='str',
            scope='job',
            require='all',
            defvalue='O0',
            shorthelp="Optimization mode",
            switch="-O<str>",
            example=["cli: -O3",
                    "api: chip.set('option','optmode','O3')"],
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

    #TODO: with modular flows does this go away?
    scparam(cfg, ['option','frontend'],
            sctype='str',
            scope='job',
            defvalue='verilog',
            shorthelp="Compilation frontend",
            switch="-frontend <frontend>",
            example=["cli: -frontend systemverilog",
                     "api: chip.set('option','frontend', 'systemverilog')"],
            schelp="""
            Specifies the frontend that flows should use for importing and
            processing source files. Default option is 'verilog', also supports
            'systemverilog' and 'chisel'. When using the Python API, this parameter
            must be configured before calling load_target().""")

    scparam(cfg, ['option','cfg'],
            sctype='[file]',
            scope='job',
            shorthelp="Configuration manifest",
            switch="-cfg <file>",
            example=["cli: -cfg mypdk.json",
                    "api: chip.set('option','cfg','mypdk.json')"],
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
            switch="-env 'key <str>",
            example=[
            "cli: -env 'PDK_HOME /disk/mypdk'",
            "api: chip.set('option','env', 'PDK_HOME', '/disk/mypdk')"],
            schelp="""
            Certain tools and reference flows require global environment
            variables to be set. These variables can be managed externally or
            specified through the env variable.""")

    scparam(cfg, ['option', 'scpath'],
            sctype='[dir]',
            scope='job',
            shorthelp="Search path",
            switch="-scpath <dir>",
            example=[
                "cli: -scpath '/home/$USER/sclib'",
                "api: chip.set('option', 'scpath','/home/$USER/sclib')"],
            schelp="""
            Specifies python modules paths for target import.""")

    scparam(cfg, ['option', 'loglevel'],
            sctype='str',
            scope='job',
            defvalue='INFO',
            shorthelp="Logging level",
            switch="-loglevel <str>",
            example=[
                "cli: -loglevel INFO",
                "api: chip.set('option', 'loglevel', 'INFO')"],
            schelp="""
            Provides explicit control over the level of debug logging printed.
            Valid entries include INFO, DEBUG, WARNING, ERROR.""")

    scparam(cfg, ['option', 'builddir'],
            sctype='dir',
            scope='job',
            defvalue='build',
            shorthelp="Build directory",
            switch="-builddir <dir>",
            example=[
                "cli: -builddir ./build_the_future",
                "api: chip.set('option', 'builddir','./build_the_future')"],
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
                "api: chip.set('option','jobname','may1')"],
            schelp="""
            Jobname during invocation of run(). The jobname combined with a
            defined director structure (<dir>/<design>/<jobname>/<step>/<index>)
            enables multiple levels of transparent job, step, and index
            introspection.""")

    #TODO: remove?
    scparam(cfg, ['option','jobinput','default','default'],
            sctype='str',
            scope='job',
            shorthelp="Input job name",
            switch="-jobinput 'step index <str>'",
            example=[
                "cli: -jobinput 'cts 0 job0'",
                "api:  chip.set('option','jobinput','cts,'0','job0')"],
            schelp="""
            Specifies jobname inputs for the current run() on a per step
            and per index basis. During execution, the default behavior is to
            copy inputs from the current job.""")

    scparam(cfg, ['option', 'steplist'],
            sctype='[str]',
            scope='job',
            shorthelp="Compilation step list",
            switch="-steplist <step>",
            example=[
                "cli: -steplist 'import'",
                "api: chip.set('option','steplist','import')"],
            schelp="""
            List of steps to execute. The default is to execute all steps
            defined in the flow graph.""")

    scparam(cfg, ['option', 'skipstep'],
            sctype='[str]',
            scope='job',
            shorthelp="Skip step list",
            switch="-skipstep <str>",
            example=[
                "cli: -skipstep lvs",
                "api: chip.set('option','skipstep','lvs')"],
            schelp="""
            List of steps to skip during execution.The default is to
            execute all steps  defined in the flow graph.""")

    scparam(cfg, ['option', 'indexlist'],
            sctype='[str]',
            scope='job',
            shorthelp="Compilation index list",
            switch="-indexlist <index>",
            example=["cli: -indexlist 0",
                    "api: chip.set('option','indexlist','0')"],
            schelp="""
            List of indices to execute. The default is to execute all
            indices for each step of a run.""")

    scparam(cfg, ['option', 'bkpt'],
            sctype='[str]',
            scope='job',
            shorthelp="Breakpoint list",
            switch="-bkpt <str>",
            example=[
                "cli: -bkpt place",
                "api: chip.set('option,'bkpt','place')"],
            schelp="""
            List of step stop (break) points. If the step is a TCL
            based tool, then the breakpoints stops the flow inside the
            EDA tool. If the step is a command line tool, then the flow
            drops into a Python interpreter.""")

    scparam(cfg, ['option', 'msgevent'],
            sctype='[str]',
            scope='job',
            shorthelp="Message event trigger",
            switch="-msgevent <str>",
            example=["cli: -msgevent export",
                    "api: chip.set('option','msgevent','export')"],
            schelp="""
            A list of steps after which to notify a recipient. For
            example if values of syn, place, cts are entered separate
            messages would be sent after the completion of the syn,
            place, and cts steps.""")

    scparam(cfg, ['option', 'msgcontact'],
            sctype='[str]',
            scope='job',
            shorthelp="Message contact",
            switch="-msgcontact <str>",
            example=[
                "cli: -msgcontact 'wile.e.coyote@acme.com'",
                "api: chip.set('option','msgcontact','wiley@acme.com')"],
            schelp="""
            A list of phone numbers or email addresses to message
            on a event event within the msg_event param. Actual
            support for email and phone messages is platform
            dependent.""")

    filetype = 'default'
    scparam(cfg, ['option', 'showtool', filetype],
            sctype='str',
            scope='job',
            shorthelp="Select data display tool",
            switch="-showtool 'filetype <tool>'",
            example=["cli: -showtool 'gds klayout'",
                    "api: chip.set('option','showtool','gds','klayout')"],
            schelp="""
            Selects the tool to use by the show function for displaying
            the specified filetype.""")

    scparam(cfg, ['option', 'metricoff'],
            sctype='[str]',
            scope='job',
            shorthelp="Metric summary filter",
            switch="-metricoff '<str>'",
            example=[
                "cli: -metricoff 'wirelength'",
                "api: chip.set('option','metricoff','wirelength')"],
            schelp="""
            List of metrics to supress when printing out the run
            summary.""")

    # Booleans
    scparam(cfg, ['option', 'clean'],
            sctype='bool',
            scope='job',
            shorthelp="Clean up after run",
            switch="-clean <bool>",
            example=["cli: -clean",
                     "api: chip.set('option','clean',True)"],
            schelp="""
            Clean up all intermediate and non essential files at the end
            of a task, leaving the following:

            * log file
            * replay.sh
            * inputs/
            * outputs/
            * reports/
            * autogenerated manifests
            * any files generated by schema-specified regexes
            * files specified by :keypath:`tool, <tool>, keep`""")

    scparam(cfg, ['option', 'hash'],
            sctype='bool',
            scope='job',
            shorthelp="Enable file hashing",
            switch="-hash <bool>",
            example=["cli: -hash",
                     "api: chip.set('option','hash',True)"],
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
                     "api: chip.set('option','nodisplay',True)"],
            schelp="""
            The '-nodisplay' flag prevents SiliconCompiler from
            opening GUI windows such as the final metrics report.""")

    scparam(cfg, ['option', 'quiet'],
            sctype='bool',
            scope='job',
            shorthelp="Quiet execution",
            switch="-quiet <bool>",
            example=["cli: -quiet",
                    "api: chip.set('option','quiet',True)"],
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
                    "api: chip.set('option','jobincr',True)"],
            schelp="""
            Forces an auto-update of the jobname parameter if a directory
            matching the jobname is found in the build directory. If the
            jobname does not include a trailing digit, then the number
            '1' is added to the jobname before updating the jobname
            parameter.""")

    scparam(cfg, ['option', 'novercheck'],
            sctype='bool',
            defvalue='false',
            scope='job',
            shorthelp="Disable version checking",
            switch="-novercheck <bool>",
            example=["cli: -novercheck",
                    "api: chip.set('option','novercheck',True)"],
            schelp="""
            Disables strict version checking on all invoked tools if True.
            The list of supported version numbers is defined in the
            'version' parameter in the 'eda' dictionary for each tool.""")

    scparam(cfg, ['option', 'relax'],
            sctype='bool',
            scope='job',
            shorthelp="Relax RTL linting",
            switch="-relax <bool>",
            example=["cli: -relax",
                    "api: chip.set('option','relax',True)"],
            schelp="""
            Specifies that tools should be lenient and suppress some
            warnings that may or may not indicate design issues.""")

    scparam(cfg, ['option', 'resume'],
            sctype='bool',
            scope='job',
            shorthelp="Resume build",
            switch="-resume <bool>",
            example=["cli: -resume",
                    "api: chip.set('option','resume',True)"],
            schelp="""
            If results exist for current job, then don't re-run any steps that
            had at least one index run successfully. Useful for debugging a
            flow that failed partway through.
            """)

    scparam(cfg, ['option', 'track'],
            sctype='bool',
            scope='job',
            shorthelp="Enable provenance tracking",
            switch="-track <bool>",
            example=["cli: -track",
                    "api: chip.set('option','track',True)"],
            schelp="""
            Turns on tracking of all 'record' parameters during each
            task. Tracking will result in potentially sensitive data
            being recorded in the manifest so only turn on this feature
            if you have control of the final manifest.""")

    scparam(cfg, ['option', 'trace'],
            sctype='bool',
            scope='job',
            shorthelp="Enable debug traces",
            switch="-trace <bool>",
            example=["cli: -trace",
                    "api: chip.set('option','trace',True)"],
            schelp="""
            Enables debug tracing during compilation and/or runtime.""")

    scparam(cfg, ['option', 'skipall'],
            sctype='bool',
            scope='job',
            shorthelp="Skip all tasks",
            switch="-skipall <bool>",
            example=["cli: -skipall",
                    "api: chip.set('option','skipall',True)"],
            schelp="""
            Skips the execution of all tools in run(), enabling a quick
            check of tool and setup without having to run through each
            step of a flow to completion.""")

    scparam(cfg, ['option', 'skipcheck'],
            sctype='bool',
            scope='job',
            shorthelp="Skip manifest check",
            switch="-skipcheck <bool>",
            example=["cli: -skipcheck",
                     "api: chip.set('option','skipcheck',True)"],
            schelp="""
            Bypasses the strict runtime manifest check. Can be used for
            accelerating initial bringup of tool/flow/pdk/libs targets.
            The flag should not be used for production compilation.""")

    scparam(cfg, ['option', 'copyall'],
            sctype='bool',
            scope='job',
            shorthelp="Copy all inputs to build directory",
            switch="-copyall <bool>",
            example=["cli: -copyall",
                    "api: chip.set('option','copyall',True)"],
            schelp="""
            Specifies that all used files should be copied into the
            build directory, overriding the per schema entry copy
            settings.""")

    scparam(cfg, ['option', 'show'],
            sctype='bool',
            scope='job',
            shorthelp="Show layout",
            switch="-show <bool>",
            example=["cli: -show",
                    "api: chip.set('option','show',True)"],
            schelp="""
            Specifies that the final hardware layout should be
            shown after the compilation has been completed. The
            final layout and tool used to display the layout is
            flow dependent.""")

    scparam(cfg, ['option', 'autoinstall'],
            sctype='bool',
            shorthelp=f"Option: auto install packages",
            switch=f"-autoinstall <bool>",
            example=[
                f"cli: -autoinstall true'",
                f"api: chip.set('option', 'autoinstall', True)"],
            schelp=f"""
            Enables automatic installation of missing dependencies from
            the registry.""")

    scparam(cfg, ['option', 'registry'],
            sctype='[dir]',
            shorthelp=f"Option: package registry",
            switch=f"-registry <dir>",
            example=[
                f"cli: -registry '~/myregistry'",
                f"api: chip.set('option','registry','~/myregistry')"],
            schelp=f"""
            List of Silicon Unified Packager (SUP) registry directories.
            Directories can be local file system folders or
            publicly available registries served up over http. The naming
            convention for registry packages is:
            <name>/<name>-<version>.json(.<gz>)?
            """)

    scparam(cfg,['option', 'entrypoint'],
            sctype='str',
            shorthelp="Program entry point",
            switch="-entrypoint <str>",
            example=["cli: -entrypoint top",
                    "api: chip.set('option', 'entrypoint', 'top')"],
            schelp="""Alternative entrypoint for compilation and
            simulation. The default entry point is 'design'.""")

    scparam(cfg,['option', 'idir'],
            sctype='[dir]',
            shorthelp="Design search paths",
            switch=['+incdir+<dir>', '-I <dir>'],
            example=[
                "cli: +incdir+./mylib",
                "api: chip.set('option','idir','./mylib')"],
            schelp="""
            Search paths to look for files included in the design using
            the ```include`` statement.""")

    scparam(cfg,['option', 'ydir'],
            sctype='[dir]',
            shorthelp="Design module search paths",
            switch='-y <dir>',
            example=[
                "cli: -y './mylib'",
                "api: chip.set('option','ydir','./mylib')"],
            schelp="""
            Search paths to look for verilog modules found in the the
            source list. The import engine will look for modules inside
            files with the specified +libext+ param suffix.""")

    scparam(cfg,['option', 'vlib'],
            sctype='[file]',
            shorthelp="Design libraries",
            switch='-v <file>',
            example=["cli: -v './mylib.v'",
                     "api: chip.set('option', 'vlib','./mylib.v')"],
            schelp="""
            List of library files to be read in. Modules found in the
            libraries are not interpreted as root modules.""")

    scparam(cfg,['option', 'define'],
            sctype='[str]',
            shorthelp="Design pre-processor symbol",
            switch="-D<str>",
            example=["cli: -DCFG_ASIC=1",
                     "api: chip.set('option','define','CFG_ASIC=1')"],
            schelp="""Symbol definition for source preprocessor.""")

    scparam(cfg,['option', 'libext'],
            sctype='[str]',
            shorthelp="Design file extensions",
            switch="+libext+<str>",
            example=[
                "cli: +libext+sv",
                "api: chip.set('option','libext','sv')"],
            schelp="""
            List of file extensions that should be used for finding modules.
            For example, if -y is specified as ./lib", and '.v' is specified as
            libext then the files ./lib/\\*.v ", will be searched for
            module matches.""")

    name = 'default'
    scparam(cfg,['option', 'param', name],
            sctype='str',
            shorthelp="Design parameter",
            switch="-param 'name <str>'",
            example=[
                "cli: -param 'N 64'",
                "api: chip.set('option','param','N','64')"],
            schelp="""
            Sets a top verilog level design module parameter. The value
            is limited to basic data literals. The parameter override is
            passed into tools such as Verilator and Yosys. The parameters
            support Verilog integer literals (64'h4, 2'b0, 4) and strings.
            Name of the top level module to compile.""")


    scparam(cfg,['option', 'cmdfile'],
            sctype='[file]',
            shorthelp="Design compilation command file",
            switch='-f <file>',
            example=["cli: -f design.f",
                     "api: chip.set('option', 'cmdfile','design.f')"],
            schelp="""
            Read the specified file, and act as if all text inside it was specified
            as command line parameters. Supported by most verilog simulators
            including Icarus and Verilator. The format of the file is not strongly
            standardized. Support for comments and environment variables within
            the file varies and depends on the tool used. SC simply passes on
            the filepath toe the tool executable.""")

    scparam(cfg,['option', 'flowcontinue'],
            sctype='bool',
            shorthelp="Flow continue-on-error",
            switch='-flowcontinue',
            example=["cli: -flowcontinue",
                     "api: chip.set('option', 'flowcontinue', True)"],
            schelp="""
            Continue executing flow after a tool logs errors. The default
            behavior is to quit executing the flow if a task ends and the errors
            metric is greater than 0. Note that the flow will always cease
            executing if the tool returns a nonzero status code. """)

    scparam(cfg,['option', 'continue'],
            sctype='bool',
            shorthelp='Implementation continue-on-error',
            switch='-continue',
            example=["cli: -continue",
                     "api: chip.set('option', 'continue', True)"],
            schelp="""
            Attempt to continue even when errors are encountered in the SC
            implementation. If errors are encountered, execution will halt
            before a run.
            """)

    return cfg

############################################
# Package information
############################################

def schema_package(cfg):

    userid = 'default'
    module = 'default'

    scparam(cfg, ['package', 'depgraph', module],
            sctype='[(str,str)]',
            scope='global',
            shorthelp=f"Package dependency list",
            switch=f"-package_depgraph 'module <(str,str)>'",
            example=[
                f"cli: -package_depgraph 'top (cpu,1.0.1)'",
                f"api: chip.set('package','depgraph','top',('cpu','1.0.1'))"],
            schelp=f"""
            List of Silicon Unified Packager (SUP) dependencies
            used by the design specified on a per module basis a
            list of string tuples ('name','version').""")

    scparam(cfg,['package', 'name'],
            sctype='str',
            scope='global',
            shorthelp=f"Package: name",
            switch=f"-package_name <str>",
            example=[
                f"cli: -package_name yac",
                f"api: chip.set('package','name','yac')"],
            schelp=f"""Package name.""")

    scparam(cfg,['package', 'version'],
            sctype='str',
            scope='global',
            shorthelp=f"Package: version",
            switch=f"-package_version <str>",
            example=[
                f"cli: -package_version 1.0",
                f"api: chip.set('package','version','1.0')"],
            schelp=f"""Package version. Can be a branch, tag, commit hash,
            or a semver compatible version.""")

    scparam(cfg,['package', 'description'],
            sctype='str',
            scope='global',
            shorthelp=f"Package: description",
            switch=f"-package_description <str>",
            example=[
                f"cli: -package_description 'Yet another cpu'",
                f"api: chip.set('package','description','Yet another cpu')"],
            schelp=f"""Package short one line description for package
            managers and summary reports.""")

    scparam(cfg,['package', 'keyword'],
            sctype='str',
            scope='global',
            shorthelp=f"Package: keyword",
            switch=f"-package_keyword <str>",
            example=[
                f"cli: -package_keyword cpu",
                f"api: chip.set('package','keyword','cpu')"],
            schelp=f"""Package keyword(s) used to characterize package.""")

    scparam(cfg,['package', 'homepage'],
            sctype='str',
            scope='global',
            shorthelp=f"Package: project homepage",
            switch=f"-package_homepage <str>",
            example=[
                f"cli: -package_homepage index.html",
                f"api: chip.set('package','homepage','index.html')"],
            schelp=f"""Package homepage.""")

    scparam(cfg,['package', 'doc', 'homepage'],
            sctype='str',
            scope='global',
            shorthelp=f"Package: documentation homepage",
            switch=f"-package_doc_homepage <str>",
            example=[
                f"cli: -package_doc_homepage index.html",
                f"api: chip.set('package','doc', 'homepage','index.html')"],
            schelp=f"""
            Package documentation homepage. Filepath to design docs homepage.
            Complex designs can can include a long non standard list of
            documents dependent.  A single html entry point can be used to
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
        scparam(cfg,['package', 'doc', item],
            sctype='[file]',
            scope='global',
            shorthelp=f"Package: {item} document",
            switch=f"-package_doc_{item} <str",
            example=[
                f"cli: -package_doc_{item} {item}.pdf",
                f"api: chip.set('package','doc',{item},'{item}.pdf')"],
            schelp=f""" Package list of {item} documents.""")

    scparam(cfg,['package', 'repo'],
            sctype='[str]',
            scope='global',
            shorthelp=f"Package: code repository",
            switch=f"-package_repo <str>",
            example=[
                f"cli: -package_repo 'git@github.com:aolofsson/oh.git'",
                f"api: chip.set('package','repo','git@github.com:aolofsson/oh.git')"],
            schelp=f"""Package IP address to source code repository.""")

    scparam(cfg,['package', 'dependency', module],
            sctype='[str]',
            scope='global',
            shorthelp=f"Package: version dependancies",
            switch=f"-package_dependency 'module <str>'",
            example=[
                f"cli: -package_dependency 'hello 1.0'",
                f"api: chip.set('package','dependency','hello','1.0')"],
            schelp=f"""Package dependencies specified as a key value pair.
            Versions shall follow the semver standard.""")

    scparam(cfg,['package', 'target'],
            sctype='[str]',
            scope='global',
            shorthelp=f"Package: qualified targets",
            switch=f"-package_target <str>",
            example=[
                f"cli: -package_target 'asicflow_freepdk45'",
                f"api: chip.set('package','target','asicflow_freepdk45')"],
            schelp=f"""Package list of qualified compilation targets.""")

    scparam(cfg,['package', 'license'],
            sctype='[str]',
            scope='global',
            shorthelp=f"Package: license identifiers",
            switch=f"-package_license <str>",
            example=[
                f"cli: -package_license 'Apache-2.0'",
                f"api: chip.set('package','license','Apache-2.0')"],
            schelp=f"""Package list of SPDX license identifiers.""")

    scparam(cfg,['package', 'licensefile'],
            sctype='[file]',
            scope='global',
            shorthelp=f"Package: license files",
            switch=f"-package_licensefile <file>",
            example=[
                f"cli: -package_licensefile './LICENSE'",
                f"api: chip.set('package','licensefile','./LICENSE')"],
            schelp=f"""Package list of license files for to be
            applied in cases when a SPDX identifier is not available.
            (eg. proprietary licenses).list of SPDX license identifiers.""")

    scparam(cfg,['package', 'location'],
            sctype='[str]',
            scope='global',
            shorthelp=f"Package: location",
            switch=f"-package_location <file>",
            example=[
                f"cli: -package_location 'mars'",
                f"api: chip.set('package','location','mars')"],
            schelp=f"""Package country of origin specified as standardized
            international country codes. The field can be left blank
            if the location is unknown or global.""")

    scparam(cfg,['package', 'organization'],
            sctype='[str]',
            scope='global',
            shorthelp=f"Package: sponsoring organization",
            switch=f"-package_organization <str>",
            example=[
                f"cli: -package_organization 'humanity'",
                f"api: chip.set('package','organization','humanity')"],
            schelp=f"""Package sponsoring organization. The field can be left
            blank if not applicable.""")

    scparam(cfg,['package', 'publickey'],
            sctype='str',
            scope='global',
            shorthelp=f"Package: public key",
            switch=f"-package_publickey <str>",
            example=[
                f"cli: -package_publickey '6EB695706EB69570'",
                f"api: chip.set('package','publickey','6EB695706EB69570')"],
            schelp=f"""Package public project key.""")

    record = ['name',
              'email',
              'username',
              'location',
              'organization',
              'publickey']

    for item in record:
        scparam(cfg,['package', 'author', userid, item],
                sctype='str',
                scope='global',
                shorthelp=f"Package: author {item}",
                switch=f"-package_author_{item} 'userid <str>'",
                example=[
                    f"cli: -package_author_{item} 'wiley wiley@acme.com'",
                    f"api: chip.set('package','author','wiley','{item}','wiley@acme.com')"],
                schelp=f"""Package author {item} provided with full name as key and
                {item} as value.""")

    return cfg

############################################
# Design Checklist
############################################

def schema_checklist(cfg):

    item = 'default'
    standard = 'default'
    metric = 'default'

    scparam(cfg,['checklist', standard, item, 'description'],
            sctype='str',
            scope='global',
            shorthelp="Checklist: item description",
            switch="-checklist_description 'standard item <str>",
            example=[
                "cli: -checklist_description 'ISO D000 A-DESCRIPTION'",
                "api: chip.set('checklist','ISO','D000','description','A-DESCRIPTION')"],
            schelp="""
            A short one line description of the checklist item.""")

    scparam(cfg,['checklist', standard, item, 'requirement'],
            sctype='str',
            scope='global',
            shorthelp="Checklist: item requirement",
            switch="-checklist_requirement 'standard item <str>",
            example=[
                "cli: -checklist_requirement 'ISO D000 DOCSTRING'",
                "api: chip.set('checklist','ISO','D000','requirement','DOCSTRING')"],
            schelp="""
            A complete requirement description of the checklist item
            entered as a multi-line string.""")

    scparam(cfg,['checklist', standard, item, 'dataformat'],
            sctype='str',
            scope='global',
            shorthelp="Checklist: item data format",
            switch="-checklist_dataformat 'standard item <float>'",
            example=[
                "cli: -checklist_dataformat 'ISO D000 dataformat README'",
                "api: chip.set('checklist','ISO','D000','dataformat','README')"],
            schelp="""
            Free text description of the type of data files acceptable as
            checklist signoff validation.""")

    scparam(cfg,['checklist', standard, item, 'rationale'],
            sctype='[str]',
            scope='global',
            shorthelp="Checklist: item rational",
            switch="-checklist_rationale 'standard item <str>",
            example=[
                "cli: -checklist_rational 'ISO D000 reliability'",
                "api: chip.set('checklist','ISO','D000','rationale','reliability')"],
            schelp="""
            Rationale for the the checklist item. Rationale should be a
            unique alphanumeric code used by the standard or a short one line
            or single word description.""")

    scparam(cfg,['checklist', standard, item, 'criteria'],
            sctype='[str]',
            scope='global',
            shorthelp="Checklist: item criteria",
            switch="-checklist_criteria 'standard item <float>'",
            example=[
                "cli: -checklist_criteria 'ISO D000 errors==0'",
                "api: chip.set('checklist','ISO','D000','criteria','errors==0')"],
            schelp="""
            Simple list of signoff criteria for checklist item which
            must all be met for signoff. Each signoff criteria consists of
            a metric, a relational operator, and a value in the form.
            'metric op value'.""")

    scparam(cfg,['checklist', standard, item, 'task'],
            sctype='[(str,str,str)]',
            scope='global',
            shorthelp="Checklist: item task",
            switch="-checklist_task 'standard item <(str, str, str)>'",
            example=[
                "cli: -checklist_task 'ISO D000 (job0,place,0)'",
                "api: chip.set('checklist','ISO','D000','task',('job0','place','0'))"],
            schelp="""
            Flowgraph job and task used to verify the checklist item.
            The parameter should be left empty for manual and for tool
            flows that bypass the SC infrastructure.""")

    scparam(cfg,['checklist', standard, item, 'report'],
            sctype='[file]',
            scope='global',
            shorthelp="Checklist: item report",
            switch="-checklist_report 'standard item <file>'",
            example=[
                "cli: -checklist_report 'ISO D000 my.rpt'",
                "api: chip.set('checklist','ISO','D000','report','my.rpt')"],
            schelp="""
            Filepath to report(s) of specified type documenting the successful
            validation of the checklist item.""")

    scparam(cfg,['checklist', standard, item, 'waiver', metric],
            sctype='[file]',
            scope='global',
            shorthelp="Checklist: item metric waivers",
            switch="-checklist_waiver 'standard item metric <file>'",
            example=[
                "cli: -checklist_waiver 'ISO D000 bold my.txt'",
                "api: chip.set('checklist','ISO','D000','waiver','hold', 'my.txt')"],
            schelp="""
            Filepath to report(s) documenting waivers for the checklist
            item specified on a per metric basis.""")

    scparam(cfg,['checklist', standard, item, 'ok'],
            sctype='bool',
            scope='global',
            shorthelp="Checklist: item ok",
            switch="-checklist_ok 'standard item <str>'",
            example=[
                "cli: -checklist_ok 'ISO D000 true'",
                "api: chip.set('checklist','ISO','D000','ok', True)"],
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

    step = 'default'
    index = 'default'

    scparam(cfg, ['asic', 'stackup'],
            sctype='str',
            scope='job',
            shorthelp="ASIC Stackup target",
            switch="-asic_stackup <str>",
            example=["cli: -asic_stackup 2MA4MB2MC",
                     "api: chip.set('asic','stackup','2MA4MB2MC')"],
            schelp="""
            Target ASIC stackup to use in the design. The stackup is required
            parameter for PDKs with multiple metal stackups.""")

    scparam(cfg, ['asic', 'pdk'],
            sctype='str',
            scope='job',
            shorthelp="ASIC PDK target",
            switch="-asic_pdk <str>",
            example=["cli: -asic_pdk freepdk45",
                     "api: chip.set('asic','pdk','freepdk45')"],
            schelp="""
            Target ASIC PDK to use in the design.""")

    scparam(cfg, ['asic', 'logiclib'],
            sctype='[str]',
            scope='job',
            shorthelp="ASIC: logic libraries",
            switch="-asic_logiclib <str>",
            example=["cli: -asic_logiclib nangate45",
                     "api: chip.set('asic', 'logiclib','nangate45')"],
            schelp="""List of all selected logic libraries libraries
            to use for optimization for a given library architecture
            (9T, 11T, etc).""")

    scparam(cfg, ['asic', 'macrolib'],
            sctype='[str]',
            scope='job',
            shorthelp="ASIC: macro libraries",
            switch="-asic_macrolib <str>",
            example=["cli: -asic_macrolib sram64x1024",
                     "api: chip.set('asic', 'macrolib','sram64x1024')"],
            schelp="""
            List of macro libraries to be linked in during synthesis and place
            and route. Macro libraries are used for resolving instances but are
            not used as targets for logic synthesis.""")

    scparam(cfg, ['asic', 'delaymodel'],
            sctype='str',
            scope='job',
            shorthelp="ASIC: delay model",
            switch="-asic_delaymodel <str>",
            example= ["cli: -asic_delaymodel ccs",
                      "api: chip.set('asic', 'delaymodel', 'ccs')"],
            schelp="""
            Delay model to use for the target libs. Supported values
            are nldm and ccs.""")

    net = 'default'
    scparam(cfg, ['asic', 'ndr', net],
            sctype='(float,float)',
            scope='job',
            shorthelp="ASIC: non-default routing rule",
            switch="-asic_ndr 'netname <(float,float)>",
            example= ["cli: -asic_ndr 'clk (0.2,0.2)'",
                    "api: chip.set('asic','ndr','clk', (0.2,0.2))"],
            schelp="""
            Definitions of non-default routing rule specified on a per
            net basis. Constraints are entered as a (width,space) tuples
            specified in microns.""")

    scparam(cfg, ['asic', 'minlayer'],
            sctype='str',
            scope='job',
            shorthelp="ASIC: minimum routing layer",
            switch="-asic_minlayer <str>",
            example= ["cli: -asic_minlayer m2",
                    "api: chip.set('asic', 'minlayer', 'm2')"],
            schelp="""
            Minimum SC metal layer name to be used for automated place and route .
            Alternatively the layer can be a string that matches a layer hard coded
            in the pdk_aprtech file. Designers wishing to use the same setup across
            multiple process nodes should use the integer approach. For processes
            with ambiguous starting routing layers, exact strings should be used.
            """)

    scparam(cfg, ['asic', 'maxlayer'],
            sctype='str',
            scope='job',
            shorthelp="ASIC: maximum routing layer",
            switch="-asic_maxlayer <str>",
            example= ["cli: -asic_maxlayer m2",
                    "api: chip.set('asic', 'maxlayer', 'm2')"],
            schelp="""
            Maximum SC metal layer name to be used for automated place and route .
            Alternatively the layer can be a string that matches a layer hard coded
            in the pdk_aprtech file. Designers wishing to use the same setup across
            multiple process nodes should use the integer approach. For processes
            with ambiguous starting routing layers, exact strings should be used.
            """)

    scparam(cfg, ['asic', 'maxfanout'],
            sctype='int',
            scope='job',
            shorthelp="ASIC: maximum fanout",
            switch="-asic_maxfanout <int>",
            example= ["cli: -asic_maxfanout 64",
                    "api: chip.set('asic', 'maxfanout', '64')"],
            schelp="""
             Maximum driver fanout allowed during automated place and route.
            The parameter directs the APR tool to break up any net with fanout
            larger than maxfanout into sub nets and buffer.""")

    scparam(cfg, ['asic', 'maxlength'],
            sctype='float',
            unit='um',
            scope='job',
            shorthelp="ASIC: maximum wire length",
            switch="-asic_maxlength <float>",
            example= ["cli: -asic_maxlength 1000",
                    "api: chip.set('asic', 'maxlength', '1000')"],
            schelp="""
            Maximum total wire length allowed in design during APR. Any
            net that is longer than maxlength is broken up into segments by
            the tool.""")

    scparam(cfg, ['asic', 'maxcap'],
            sctype='float',
            unit='F',
            scope='job',
            shorthelp="ASIC: maximum net capacitance",
            switch="-asic_maxcap <float>",
            example= ["cli: -asic_maxcap '0.25e-12'",
                      "api: chip.set('asic', 'maxcap', '0.25e-12')"],
            schelp="""Maximum allowed capacitance per net.""")

    scparam(cfg, ['asic', 'maxslew'],
            sctype='float',
            unit='s',
            scope='job',
            shorthelp="ASIC: maximum slew",
            switch="-asic_maxslew <float>",
            example= ["cli: -asic_maxslew '0.25e-9'",
                    "api: chip.set('asic', 'maxslew', '0.25e-9')"],
            schelp="""Maximum allowed transition time per net.""")

    sigtype='default'
    scparam(cfg, ['asic', 'rclayer', sigtype],
            sctype='str',
            scope='job',
            shorthelp="ASIC: parasitics layer",
            switch="-asic_rclayer 'sigtype <str>'",
            example= ["cli: -asic_rclayer 'clk m3'",
                    "api: chip.set('asic', 'rclayer', 'clk', 'm3')"],
            schelp="""
            Technology agnostic metal layer to be used for parasitic
            extraction estimation during APR for the wire type specified
            Current the supported wire types are: clk, data. The metal
            layers can be specified as technology agnostic SC layers
            starting with m1 or as hard PDK specific layer names.""")

    scparam(cfg, ['asic', 'vpinlayer'],
            sctype='str',
            scope='job',
            shorthelp="ASIC: vertical pin layer",
            switch="-asic_vpinlayer <str>",
            example= ["cli: -asic_vpinlayer m3",
                    "api: chip.set('asic', 'vpinlayer', 'm3')"],
            schelp="""
            Metal layer to use for automated vertical pin placement
            during APR.  The metal layers can be specified as technology
            agnostic SC layers starting with m1 or as hard PDK specific
            layer names.""")

    scparam(cfg, ['asic', 'hpinlayer'],
            sctype='str',
            scope='job',
            shorthelp="ASIC: vertical pin layer",
            switch="-asic_hpinlayer <str>",
            example= ["cli: -asic_hpinlayer m4",
                    "api: chip.set('asic', 'hpinlayer', 'm4')"],
            schelp="""
            Metal layer to use for automated horizontal pin placement
            during APR.  The metal layers can be specified as technology
            agnostic SC layers starting with m1 or as hard PDK specific
            layer names.""")

    scparam(cfg, ['asic', 'density'],
            sctype='float',
            scope='job',
            shorthelp="ASIC: target core density",
            switch="-asic_density <float>",
            example= ["cli: -asic_density 30",
                      "api: chip.set('asic', 'density', '30')"],
            schelp="""
            Target density based on the total design cell area reported
            after synthesis. This number is used when no diearea or floorplan is
            supplied. Any number between 1 and 100 is legal, but values above 50
            may fail due to area/congestion issues during apr.""")

    scparam(cfg, ['asic', 'coremargin'],
            sctype='float',
            unit='um',
            scope='job',
            shorthelp="ASIC: block core margin",
            switch="-asic_coremargin <float>",
            example= ["cli: -asic_coremargin 1",
                      "api: chip.set('asic', 'coremargin', '1')"],
            schelp="""
            Halo/margin between the die boundary and core placement for
            automated floorplanning when no diearea or floorplan is
            supplied.""")

    scparam(cfg, ['asic', 'aspectratio'],
            sctype='float',
            scope='job',
            shorthelp="ASIC: block aspect ratio",
            switch="-asic_aspectratio <float>",
            example= ["cli: -asic_aspectratio 2.0",
                    "api: chip.set('asic', 'aspectratio', '2.0')"],
            schelp="""
            Height to width ratio of the block for automated floor-planning.
            Values below 0.1 and above 10 should be avoided as they will likely fail
            to converge during placement and routing. The ideal aspect ratio for
            most designs is 1. This value is only used when no diearea or floorplan
            is supplied.""")

    scparam(cfg, ['asic', 'diearea'],
            sctype='[(float,float)]',
            unit='um',
            scope='job',
            shorthelp="ASIC: die area outline",
            switch="-asic_diearea <[(float,float)]>",
            example= ["cli: -asic_diearea '(0,0)'",
                    "api: chip.set('asic', 'diearea', (0,0))"],
            schelp="""
            List of (x,y) points that define the outline of the die area for the
            physical design. Simple rectangle areas can be defined with two points,
            one for the lower left corner and one for the upper right corner. All
            values are specified in microns.""")

    scparam(cfg, ['asic', 'corearea'],
            sctype='[(float,float)]',
            unit='um',
            scope='job',
            shorthelp="ASIC: core area outline",
            switch="-asic_corearea <[(float,float)]>",
            example= ["cli: -asic_corearea '(0,0)'",
                    "api: chip.set('asic', 'corearea', (0,0))"],
            schelp="""
            List of (x,y) points that define the outline of the core area for the
            physical design. Simple rectangle areas can be defined with two points,
            one for the lower left corner and one for the upper right corner. All
            values are specified in microns.""")

    tool = 'default'
    key = 'default'
    scparam(cfg, ['asic', 'file', tool, key],
            sctype='[file]',
            shorthelp="ASIC: special file",
            switch="-asic_file 'tool key<file>'",
            example=[
                "cli: -asic_file 'yosys presyn ~/presyn.tcl'",
                "api: chip.set('asic','file','yosys','presyn','~/presyn.tcl')"],
            schelp="""
            List of named files specified on a per tool basis.
            The parameter should only be used for specifying files that are
            not directly supported by the ASIC schema.""")

    scparam(cfg, ['asic', 'dir', tool, key],
            sctype='[dir]',
            shorthelp="ASIC: special directory",
            switch="-asic_dir 'tool key <dir>'",
            example=[
                "cli: -asic_dir 'lib atool db ~/libdb'",
                "api: chip.set('asic','dir','atool','db','~/libdb')"],
            schelp="""
            List of named dirs specified on a per tool basis. The parameter
            should only be used for specifying dirs that are not directly
            supported by the ASIC schema.""")

    scparam(cfg, ['asic', 'var', tool, key],
            sctype='[str]',
            shorthelp="ASIC: special variable",
            switch="-asic_variable 'tool key <str>'",
            example=[
                "cli: -asic_variable 'xyce modeltype bsim4'""",
                "api: chip.set('asic','var','xyce','modeltype','bsim4')"],
            schelp="""
            List of key/value strings specified on a per basis. The parameter
            should only be used for specifying variables that are
            not directly supported by the SiliconCompiler PDK schema.""")


    # TODO: Expand on the exact definitions of these types of cells.
    # minimize typing
    names = ['driver',
             'load',
             'buf',
             'decap',
             'delay',
             'tie',
             'hold',
             'clkbuf',
             'clkdelay',
             'clkinv',
             'clkgate',
             'clkicg',
             'clklogic',
             'ignore',
             'filler',
             'tap',
             'endcap',
             'antenna']

    for item in names:
        scparam(cfg, ['asic', 'cells', item],
                sctype='[str]',
                shorthelp=f"ASIC: {item} cell list",
                switch=f"-asic_cells_{item} '<str>'",
                example=[
                    f"cli: -asic_cells_{item} '*eco*'",
                    f"api: chip.set('asic','cells',{item},'*eco*')"],
                schelp="""
                List of cells grouped by a property that can be accessed
                directly by the designer and tools. The example below shows how
                all cells containing the string 'eco' could be marked as dont use
                for the tool.""")

    # Place and route parameters (optional)
    scparam(cfg, ['asic', 'pgmetal'],
            sctype='str',
            shorthelp="ASIC: powergrid layer",
            switch="-asic_pgmetal '<str>'",
            example=["cli: -asic_pgmetal m1",
                    "api: chip.set('asic','pgmetal','m1')"],
            schelp="""
            Top metal layer used for power and ground routing within the
            library. The parameter can be used to guide cell power grid
            hookup by APR tools.""")

    scparam(cfg,['asic', 'libarch'],
            sctype='str',
            shorthelp="ASIC: library architecture",
            switch="-asic_libarch '<str>'",
            example=[
                "cli: -asic_libarch '12track'",
                "api: chip.set('asic','libarch','12track')"],
            schelp="""
            The library architecture (e.g. library height) used to build the
            design. For example a PDK with support for 9 and 12 track libraries
            might have 'libarchs' called 9t and 12t.""")

    # footprint
    key = 'default'
    scparam(cfg,['asic', 'footprint', key, 'alias'],
            sctype='[str]',
            shorthelp="ASIC: Footprint name aliases",
            switch="-asic_footprint_alias 'key <str>'",
            example=[
                "cli: -asic_footprint_alias '12track FreeCell'",
                "api: chip.set('asic','footprint','12track','alias','FreeCell')"],
            schelp="""
            Alias for the footprint key that is sometimes needed when the footprint can
            be referenced by multiple names. The key is the 'official' footprint.""")

    scparam(cfg, ['asic', 'footprint', key, 'symmetry'],
            sctype='str',
            shorthelp="ASIC: Footprint symmetry",
            switch="-asic_footprint_symmetry 'key <str>'",
            example=[
                "cli: -asic_footprint_symmetry 'core X Y'",
                "api: chip.set('asic','footprint','core','symmetry','X Y')"],
            schelp="""
            Footprint symmetry based on LEF standard definition. 'X' implies
            symmetric about the x axis, 'Y' implies symmetry about the y axis, and
            'X Y' implies symmetry about the x and y axis.""")


    scparam(cfg, ['asic', 'footprint', key, 'size'],
            sctype='(float,float)',
            shorthelp="ASIC: Footprint size",
            switch="-asic_footprint_size 'key <str>'",
            example=[
                "cli: -asic_footprint_size 'core (1.0,1.0)'",
                "api: chip.set('asic','footprint','core','size',(1.0,1.0))"],
            schelp="""
            Size of the footprint described as a (width, height) tuple in
            microns.""")


    return cfg

############################################
# Constraints
############################################

def schema_constraint(cfg, scenario='default'):

    scparam(cfg,['constraint', scenario, 'voltage'],
            sctype='float',
            unit='V',
            scope='job',
            shorthelp="Constraint voltage level",
            switch="-constraint_voltage 'scenario <float>'",
            example=["cli: -constraint_voltage 'worst 0.9'",
                     "api: chip.set('constraint', 'worst','voltage', '0.9')"],
            schelp="""Operating voltage applied to the scenario.""")

    scparam(cfg,['constraint', scenario, 'temperature'],
            sctype='float',
            scope='job',
            shorthelp="Constraint temperature",
            switch="-constraint_temperature 'scenario <float>'",
            example=["cli: -constraint_temperature 'worst 125'",
                     "api: chip.set('constraint', 'worst', 'temperature','125')"],
            schelp="""Chip temperature applied to the scenario specified in degrees C.""")

    scparam(cfg,['constraint', scenario, 'libcorner'],
            sctype='str',
            scope='job',
            shorthelp="Constraint library corner",
            switch="-constraint_libcorner 'scenario <str>'",
            example=["cli: -constraint_libcorner 'worst ttt'",
                    "api: chip.set('constraint', 'worst', 'libcorner', 'ttt')"],
            schelp="""Library corner applied to the scenario to scale
            library timing models based on the libcorner value for models
            that support it. The parameter is ignored for libraries that
            have one hard coded model per libcorner.""")

    scparam(cfg,['constraint', scenario, 'pexcorner'],
            sctype='str',
            scope='job',
            shorthelp="Constraint pex corner",
            switch="-constraint_pexcorner 'scenario <str>'",
            example=["cli: -constraint_pexcorner 'worst max'",
                    "api: chip.set('constraint', 'worst', 'pexcorner', 'max')"],
            schelp="""Parasitic corner applied to the scenario. The
            'pexcorner' string must match a corner found in the pdk
            pexmodel setup.""")

    scparam(cfg,['constraint', scenario, 'opcond'],
            sctype='str',
            scope='job',
            shorthelp="Constraint operating condition",
            switch="-constraint_opcond 'scenario <str>'",
            example=["cli: -constraint_opcond 'worst typical_1.0'",
                     "api: chip.set('constraint', 'worst', 'opcond',  'typical_1.0')"],
            schelp="""Operating condition applied to the scenario. The value
            can be used to access specific conditions within the library
            timing models from the 'logiclib' timing models.""")

    scparam(cfg,['constraint', scenario, 'mode'],
            sctype='str',
            scope='job',
            shorthelp="Constraint operating mode",
            switch="-constraint_mode 'scenario <str>'",
            example=["cli: -constraint_mode 'worst test'",
                     "api: chip.set('constraint',  'worst','mode', 'test')"],
            schelp="""Operating mode for the scenario. Operating mode strings
            can be values such as test, functional, standby.""")

    scparam(cfg,['constraint', scenario, 'file'],
            sctype='[file]',
            scope='job',
            copy='true',
            shorthelp="Constraint files",
            switch="-constraint_file 'scenario <file>'",
            example=["cli: -constraint_file 'worst hello.sdc'",
                     "api: chip.set('constraint','worst','file', 'hello.sdc')"],
            schelp="""List of timing constraint files to use for the scenario. The
            values are combined with any constraints specified by the design
            'constraint' parameter. If no constraints are found, a default
            constraint file is used based on the clock definitions.""")

    scparam(cfg,['constraint', scenario, 'check'],
            sctype='[str]',
            scope='job',
            shorthelp="Constraint checks to perform",
            switch="-constraint_check 'scenario <str>'",
            example=["cli: -constraint_check 'worst check setup'",
                    "api: chip.add('constraint','worst','check','setup')"],
            schelp="""
            List of checks for to perform for the scenario. The checks must
            align with the capabilities of the EDA tools and flow being used.
            Checks generally include objectives like meeting setup and hold goals
            and minimize power. Standard check names include setup, hold, power,
            noise, reliability.""")

    return cfg

##############################################################################
# Main routine
if __name__ == "__main__":
    cfg = schema_cfg()
    print(json.dumps(cfg, indent=4, sort_keys=True))
