# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import utils

import re
import os
import sys
import copy
import json

#############################################################################
# PARAM DEFINITION
#############################################################################

def scparam(cfg,
            keypath,
            sctype=None,
            require=None,
            defvalue=None,
            scope='global',
            copy='false',
            lock='false',
            hashalgo='sha256',
            signature=None,
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
                signature=signature,
                hashalgo=hashalgo,
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
        cfg['type'] = sctype
        cfg['scope'] = scope
        cfg['require'] = require
        cfg['lock'] = lock
        cfg['switch'] = switch
        cfg['shorthelp'] = shorthelp
        cfg['example'] = example
        cfg['help'] = schelp
        cfg['defvalue'] = defvalue
        cfg['value'] = defvalue
        cfg['signature'] = signature

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
    cfg['history'] = {}

    # Version handling
    cfg = schema_version(cfg, SCHEMA_VERSION)

    # Runtime options
    cfg = schema_options(cfg)
    cfg = schema_arg(cfg)

    # Primary sources
    cfg = schema_design(cfg)

    # Constraints
    #cfg = schema_constraints(cfg)

    # Project configuration
    cfg = schema_package(cfg, 'package')
    cfg = schema_checklist(cfg)
    cfg = schema_design(cfg)
    cfg = schema_read(cfg)
    cfg = schema_fpga(cfg)
    cfg = schema_asic(cfg)
    cfg = schema_mcmm(cfg)

    # Flow Information
    cfg = schema_flowgraph(cfg)
    cfg = schema_flowstatus(cfg)
    cfg = schema_eda(cfg)

    # PDK
    cfg = schema_pdk(cfg)

    # Package management
    cfg = schema_libs(cfg)
    cfg = schema_package(cfg, 'library')
    cfg = schema_checklist(cfg, 'library')

    # Compilation records
    cfg = schema_metric(cfg)
    cfg = schema_record(cfg)

    return cfg

###############################################################################
# Minimal setup FPGA
###############################################################################

def schema_version(cfg, version):

    scparam(cfg,['version', 'schema'],
            sctype='str',
            defvalue=version,
            shorthelp="Schema version number",
            switch="-version_schema <str>",
            example=["cli: -version_schema",
                     "api: chip.get('version', 'schema')"],
            schelp="""SiliconCompiler schema version number.""")

    scparam(cfg,['version', 'software'],
            sctype='str',
            shorthelp="Software version number",
            switch="-version_software <str>",
            example=["cli: -version_software",
                     "api: chip.get('version', 'software')"],
            schelp="""SiliconCompiler software version number.""")

    scparam(cfg,['version', 'print'],
            sctype='bool',
            shorthelp="Prints version number",
            switch="-version <bool>",
            example=["cli: -version",
                    "api: chip.get('version', 'print')"],
            schelp="""Command line switch to print the schema and software
            version numbers in an 'sc' command line app.""")

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
            scope='job',
            shorthelp="FPGA architecture file",
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
            scope='job',
            shorthelp="FPGA vendor name",
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
            scope='job',
            shorthelp="FPGA part name",
            switch="-fpga_partname <str>",
            example=["cli: -fpga_partname fpga64k",
                     "api:  chip.set('fpga', 'partname', 'fpga64k')"],
            schelp="""
            Complete part name used as a device target by the FPGA compilation
            tool. The part name must be an exact string match to the partname
            hard coded within the FPGA eda tool.""")

    scparam(cfg,['fpga', 'board'],
            sctype='str',
            scope='job',
            shorthelp="FPGA board name",
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
            scope='job',
            shorthelp="FPGA program enable",
            switch="-fpga_program <bool>",
            example=["cli: -fpga_program",
                     "api:  chip.set('fpga', 'program', True)"],
            schelp="""Specifies that the bitstream should be loaded into an FPGA.""")

    scparam(cfg,['fpga', 'flash'],
            sctype='bool',
            scope='job',
            shorthelp="FPGA flash enable",
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

    scparam(cfg, ['pdk', 'foundry'],
            sctype='str',
            require="asic",
            shorthelp="PDK foundry name",
            switch="-pdk_foundry <str>",
            example=["cli: -pdk_foundry virtual",
                    "api:  chip.set('pdk', 'foundry', 'virtual')"],
            schelp="""
            Name of foundry corporation. Examples include intel, gf, tsmc,
            samsung, skywater, virtual. The \'virtual\' keyword is reserved for
            simulated non-manufacturable processes.""")

    scparam(cfg, ['pdk', 'process'],
            sctype='str',
            require="asic",
            shorthelp="PDK process name",
            switch="-pdk_process <str>",
            example=["cli: -pdk_process asap7",
                     "api:  chip.set('pdk', 'process', 'asap7')"],
            schelp="""
            Public name of the foundry process. The string is case insensitive and
            must match the public process name exactly. Examples of virtual
            processes include freepdk45 and asap7.""")

    scparam(cfg, ['pdk', 'version'],
            sctype='str',
            shorthelp="PDK version number",
            switch="-pdk_version <str>",
            example=["cli: -pdk_version 1.0",
                    "api:  chip.set('pdk', 'version', '1.0')"],
            schelp="""
            Alphanumeric string specifying the version of the PDK. Verification of
            correct PDK and IP versions is a hard ASIC tapeout require in all
            commercial foundries. The version number can be used for design manifest
            tracking and tapeout checklists.""")

    scparam(cfg, ['pdk', 'stackup'],
            sctype='[str]',
            require='asic',
            shorthelp="PDK metal stackups",
            switch="-pdk_stackup <str>",
            example=["cli: -pdk_stackup 2MA4MB2MC",
                     "api: chip.add('pdk','stackup','2MA4MB2MC')"],
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

    scparam(cfg, ['pdk', 'node'],
            sctype='float',
            require="asic",
            shorthelp="PDK process node",
            switch="-pdk_node <float>",
            example=["cli: -pdk_node 130",
                    "api:  chip.set('pdk', 'node', 130)"],
            schelp="""
            Approximate relative minimum dimension of the process target specified
            in nanometers. The parameter is required for flows and tools that
            leverage the value to drive technology dependent synthesis and APR
            optimization. Node examples include 180, 130, 90, 65, 45, 32, 22 14,
            10, 7, 5, 3.""")

    scparam(cfg, ['pdk', 'wafersize'],
            sctype='float',
            require="asic",
            shorthelp="PDK process node",
            switch="-pdk_wafersize <float>",
            example=["cli: -pdk_wafersize 300",
                    "api:  chip.set('pdk', 'wafersize', 300)"],
            schelp="""
            Wafer diameter used in manufacturing process specified in mm. The
            standard diameter for leading edge manufacturing is 300mm. For older
            process technologies and specialty fabs, smaller diameters such as
            200, 100, 125, 100 are common. The value is used to calculate dies per
            wafer and full factory chip costs.""")

    scparam(cfg, ['pdk', 'wafercost'],
            sctype='float',
            shorthelp="PDK wafer cost",
            switch="-pdk_wafercost <float>",
            example=["cli: -pdk_wafercost 10000",
                     "api:  chip.set('pdk', 'wafercost', 10000)"],
            schelp="""
            Raw cost per wafer purchased specified in USD, not accounting for
            yield loss. The values is used to calculate chip full factory costs.""")

    scparam(cfg, ['pdk', 'd0'],
            sctype='float',
            shorthelp="PDK process defect density",
            switch="-pdk_d0 <float>",
            example=["cli: -pdk_d0 0.1",
                     "api:  chip.set('pdk', 'd0', 0.1)"],
            schelp="""
            Process defect density (d0) expressed as random defects per cm^2. The
            value is used to calculate yield losses as a function of area, which in
            turn affects the chip full factory costs. Two yield models are
            supported: Poisson (default), and Murphy. The Poisson based yield is
            calculated as dy = exp(-area * d0/100). The Murphy based yield is
            calculated as dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.""")

    scparam(cfg, ['pdk', 'hscribe'],
            sctype='float',
            shorthelp="PDK horizontal scribe line width",
            switch="-pdk_hscribe <float>",
            example=["cli: -pdk_hscribe 0.1",
                     "api:  chip.set('pdk', 'hscribe', 0.1)"],
            schelp="""
             Width of the horizontal scribe line (in mm) used during die separation.
            The process is generally completed using a mechanical saw, but can be
            done through combinations of mechanical saws, lasers, wafer thinning,
            and chemical etching in more advanced technologies. The value is used
            to calculate effective dies per wafer and full factory cost.""")

    scparam(cfg, ['pdk', 'vscribe'],
            sctype='float',
            shorthelp="PDK vertical scribe line width",
            switch="-pdk_vscribe <float>",
            example=["cli: -pdk_vscribe 0.1",
                     "api:  chip.set('pdk', 'vscribe', 0.1)"],
            schelp="""
             Width of the vertical scribe line (in mm) used during die separation.
            The process is generally completed using a mechanical saw, but can be
            done through combinations of mechanical saws, lasers, wafer thinning,
            and chemical etching in more advanced technologies. The value is used
            to calculate effective dies per wafer and full factory cost.""")

    scparam(cfg, ['pdk', 'edgemargin'],
            sctype='float',
            shorthelp="PDK wafer edge keep-out margin",
            switch="-pdk_edgemargin <float>",
            example=["cli: -pdk_edgemargin 1",
                     "api:  chip.set('pdk', 'edgemargin', 1)"],
            schelp="""
            Keep-out distance/margin from the wafer edge inwards specified in mm.
            The wafer edge is prone to chipping and need special treatment that
            preclude placement of designs in this area. The edge value is used to
            calculate effective dies per wafer and full factory cost.""")

    scparam(cfg, ['pdk', 'density'],
            sctype='float',
            shorthelp="PDK transistor density",
            switch="-pdk_density <float>",
            example=["cli: -pdk_density 100e6",
                    "api:  chip.set('pdk', 'density', 10e6)"],
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

    scparam(cfg, ['pdk', 'sramsize'],
            sctype='float',
            shorthelp="PDK SRAM bitcell size",
            switch="-pdk_sramsize <float>",
            example=["cli: -pdk_sramsize 0.032",
                     "api:  chip.set('pdk', 'sramsize', '0.026')"],
            schelp="""
            Area of an SRAM bitcell expressed in um^2. The value can be derived
            from a variety of sources, including the PDK DRM, library LEFs,
            conference presentations, and public analysis. The number is a good
            first order indicator of SRAM density for large memory arrays where
            the bitcell dominates the array I/O logic.""")

    simtype = 'default'
    scparam(cfg, ['pdk', 'devmodel', tool, simtype, stackup],
            sctype='[file]',
            shorthelp="PDK device models",
            switch="-pdk_devmodel 'tool simtype stackup <file>'",
            example=[
            "cli: -pdk_devmodel 'xyce spice M10 asap7.sp'",
            "api: chip.set('pdk','devmodel','xyce','spice','M10','asap7.sp')"],
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
    scparam(cfg, ['pdk', 'pexmodel', tool, stackup, corner],
            sctype='[file]',
            shorthelp="PDK parasitic TCAD models",
            switch="-pdk_pexmodel 'tool stackup corner <file>'",
            example=[
                "cli: -pdk_pexmodel 'fastcap M10 max wire.mod'",
                "api: chip.set('pdk','pexmodel','fastcap','M10','max','wire.mod')"],
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
    scparam(cfg, ['pdk', 'layermap', tool, src, dst, stackup],
            sctype='[file]',
            shorthelp="PDK layer map file",
            switch="-pdk_layermap 'tool src dst stackup <file>'",
            example=[
                "cli: -pdk_layermap 'klayout db gds M10 asap7.map'",
                "api: chip.set('pdk','layermap','klayout','db','gds','M10','asap7.map')"],
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


    scparam(cfg, ['pdk', 'display', tool, stackup],
            sctype='[file]',
            shorthelp="PDK display file",
            switch="-pdk_display 'tool stackup <file>'",
            example=[
                "cli: -pdk_display 'klayout M10 display.lyt'",
                "api: chip.set('pdk','display','klayout','M10','display.cfg')"],
            schelp="""
            Display configuration files describing colors and pattern schemes for
            all layers in the PDK. The display configuration file is entered on a
            stackup and tool basis.""")

    #TODO: create firm list of accepted files
    libarch = 'default'
    scparam(cfg, ['pdk', 'aprtech', tool, stackup, libarch, filetype],
            sctype='[file]',
            shorthelp="PDK APR technology files",
            switch="-pdk_aprtech 'tool stackup libarch filetype <file>'",
            example=[
                "cli: -pdk_aprtech 'openroad M10 12t lef tech.lef'",
                "api: chip.set('pdk','aprtech','openroad','M10','12t','lef','tech.lef')"],
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

    checks = ['lvs', 'drc', 'erc']
    name = 'default'
    for item in checks:
        scparam(cfg, ['pdk', item, 'runset', tool, stackup, name],
                sctype='[file]',
                shorthelp=f"PDK {item.upper()} runset files",
                switch=f"-pdk_{item}_runset 'tool stackup name <file>'",
                example=[
                    f"cli: -pdk_{item}_runset 'magic M10 basic $PDK/{item}.rs'",
                    f"api: chip.set('pdk','{item}','runset','magic','M10','basic','$PDK/{item}.rs')"],
                schelp=f"""Runset files for {item.upper()} verification.""")

        scparam(cfg, ['pdk', item, 'waiver', tool, stackup, name],
                sctype='[file]',
                shorthelp=f"PDK {item.upper()} waiver files",
                switch=f"-pdk_{item}_waiver 'tool stackup name <file>'",
                example=[
                    f"cli: -pdk_{item}_waiver 'magic M10 basic $PDK/{item}.txt'",
                    f"api: chip.set('pdk','{item}','waiver','magic','M10','basic','$PDK/{item}.txt')"],
                schelp=f"""Waiver files for {item.upper()} verification.""")

    ################
    # Routing grid
    ################

    layer = 'default'
    scparam(cfg, ['pdk', 'grid', stackup, layer, 'name'],
            sctype='str',
            shorthelp="PDK routing grid name map",
            switch="-pdk_grid_name 'stackup layer <str>'",
            example=[
                "cli: -pdk_grid_name 'M10 metal1 m1'",
                "api: chip.set('pdk','grid','M10','metal1','name','m1')"],
            schelp="""
            Maps PDK metal names to the SC standardized layer stack
            starting with m1 as the lowest routing layer and ending
            with m<n> as the highest routing layer. The map is
            specified on a per metal stack basis.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'dir'],
            sctype='str',
            shorthelp="PDK routing grid preferred direction",
            switch="-pdk_grid_dir 'stackup layer <str>'",
            example=[
                "cli: -pdk_grid_dir 'M10 m1 horizontal'",
                "api: chip.set('pdk','grid','M10','m1','dir','horizontal')"],
            schelp="""
            Preferred routing direction specified on a per stackup
            and per metal basis. Valid routing directions are horizontal
            and vertical.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'xpitch'],
            sctype='float',
            shorthelp="PDK routing grid vertical wire pitch",
            switch="-pdk_grid_xpitch 'stackup layer <float>'",
            example= [
                "cli: -pdk_grid_xpitch 'M10 m1 0.5'",
                "api: chip.set('pdk','grid','M10','m1','xpitch','0.5')"],
            schelp="""
            Defines the routing pitch for vertical wires on a per stackup and
            per metal basis, specified in um.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'ypitch'],
            sctype='float',
            shorthelp="PDK routing grid horizontal wire pitch",
            switch="-pdk_grid_ypitch 'stackup layer <float>'",
            example= [
                "cli: -pdk_grid_ypitch 'M10 m1 0.5'",
                "api: chip.set('pdk','grid','M10','m1','ypitch','0.5')"],
            schelp="""
            Defines the routing pitch for horizontal wires on a per stackup and
            per metal basis, specified in um.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'xoffset'],
            sctype='float',
            shorthelp="PDK routing grid vertical wire offset",
            switch="-pdk_grid_xoffset 'stackup layer <float>'",
            example= [
                "cli: -pdk_grid_xoffset 'M10 m2 0.5'",
                "api: chip.set('pdk','grid','M10','m2','xoffset','0.5')"],
            schelp="""
            Defines the grid offset of a vertical metal layer specified on a per
            stackup and per metal basis, specified in um.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'yoffset'],
            sctype='float',
            shorthelp="PDK routing grid horizontal wire offset",
            switch="-pdk_grid_yoffset 'stackup layer <float>'",
            example= [
                "cli: -pdk_grid_yoffset 'M10 m2 0.5'",
                "api: chip.set('pdk','grid','M10','m2','yoffset','0.5')"],
            schelp="""
            Defines the grid offset of a horizontal metal layer specified on a per
            stackup and per metal basis, specified in um.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'adj'],
            sctype='float',
            shorthelp="PDK routing grid resource adjustment",
            switch="-pdk_grid_adj 'stackup layer <float>'",
            example= [
                "cli: -pdk_grid_adj 'M10 m2 0.5'",
                "api: chip.set('pdk','grid','M10','m2','adj','0.5')"],
            schelp="""
            Defines the routing resources adjustments for the design on a per layer
            basis. The value is expressed as a fraction from 0 to 1. A value of
            0.5 reduces the routing resources by 50%. If not defined, 100%
            routing resource utilization is permitted.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'adj'],
            sctype='float',
            shorthelp="PDK routing grid resource adjustment",
            switch="-pdk_grid_adj 'stackup layer <float>'",
            example= [
                "cli: -pdk_grid_adj 'M10 m2 0.5'",
                "api: chip.set('pdk','grid','M10','m2','adj','0.5')"],
            schelp="""
            Defines the routing resources adjustments for the design on a per layer
            basis. The value is expressed as a fraction from 0 to 1. A value of
            0.5 reduces the routing resources by 50%. If not defined, 100%
            routing resource utilization is permitted.""")

    corner='default'
    scparam(cfg, ['pdk', 'grid', stackup, layer, 'cap', corner],
            sctype='float',
            shorthelp="PDK routing grid unit capacitance",
            switch="-pdk_grid_cap 'stackup layer corner <float>''",
            example= [
                "cli: -pdk_grid_cap 'M10 m2 fast 0.2'",
                "api: chip.set('pdk','grid','M10','m2','cap','fast','0.2')"],
            schelp="""
            Unit capacitance of a wire defined by the grid width and spacing values
            in the 'grid' structure. The value is specified as ff/um on a per
            stackup, metal, and corner basis. As a rough rule of thumb, this value
            tends to stay around 0.2ff/um. This number should only be used for
            reality confirmation. Accurate analysis should use the PEX models.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'res', corner],
            sctype='float',
            shorthelp="PDK routing grid unit resistance",
            switch="-pdk_grid_res 'stackup layer corner <float>''",
            example= [
                "cli: -pdk_grid_res 'M10 m2 fast 0.2'",
                "api: chip.set('pdk','grid','M10','m2','res','fast','0.2')"],
            schelp="""
            Resistance of a wire defined by the grid width and spacing values
            in the 'grid' structure.  The value is specified as ohms/um on a per
            stackup, metal, and corner basis. The parameter is only meant to be
            used as a sanity check and for coarse design planning. Accurate
            analysis should use the TCAD PEX models.""")

    scparam(cfg, ['pdk', 'grid', stackup, layer, 'tcr', corner],
            sctype='float',
            shorthelp="PDK routing grid temperature coefficient",
            switch="-pdk_grid_tcr 'stackup layer corner <float>'",
            example= [
                "cli: -pdk_grid_tcr 'M10 m2 fast 0.2'",
                "api: chip.set('pdk','grid','M10','m2','tcr','fast','0.2')"],
            schelp="""
            Temperature coefficient of resistance of the wire defined by the grid
            width and spacing values in the 'grid' structure. The value is specified
            in %/ deg C on a per stackup, layer, and corner basis. The number is
            only meant to be used as a sanity check and for coarse design
            planning. Accurate analysis should use the PEX models.""")

    ###############
    # EDA vars
    ###############

    key='default'
    scparam(cfg, ['pdk', 'file', tool, key, stackup],
            sctype='[file]',
            shorthelp="PDK named file",
            switch="-pdk_file 'tool key stackup <file>'",
            example=[
                "cli: -pdk_file 'xyce spice M10 asap7.sp'",
                "api: chip.set('pdk','file','xyce','spice','M10','asap7.sp')"],
            schelp="""
            List of named files specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly  supported by the SiliconCompiler PDK schema.""")


    scparam(cfg, ['pdk', 'directory', tool, key, stackup],
            sctype='[dir]',
            shorthelp="PDK named directory",
            switch="-pdk_directory 'tool key stackup <file>'",
            example=[
                "cli: -pdk_directory 'xyce rfmodel M10 rftechdir'",
                "api: chip.set('pdk','directory','xyce','rfmodel','M10','rftechdir')"],
            schelp="""
            List of named directories specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly  supported by the SiliconCompiler PDK schema.""")

    scparam(cfg, ['pdk', 'variable', tool, key, stackup],
            sctype='[str]',
            shorthelp="PDK named variable",
            switch="-pdk_variable 'tool stackup key <str>'",
            example=[
                "cli: -pdk_variable 'xyce modeltype M10 bsim4'""",
                "api: chip.set('pdk','variable','xyce','modeltype','M10','bsim4')"],
            schelp="""
             List of key/value strings specified on a per tool and per stackup basis.
            The parameter should only be used for specifying variables that are
            not directly  supported by the SiliconCompiler PDK schema.""")

    ###############
    # Docs
    ###############

    scparam(cfg,['pdk', 'doc', 'homepage'],
            sctype='[file]',
            shorthelp="PDK documentation homepage",
            switch="-pdk_doc_homepage <file>",
            example=["cli: -pdk_doc_homepage 'index.html",
                     "api: chip.set('pdk','doc','homepage','index.html')"],
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
        scparam(cfg,['pdk', 'doc', item],
                sctype='[file]',
                shorthelp=f"PDK {item}",
                switch= f"-pdk_doc_{item} <file>",
                example=[f"cli: -pdk_doc_{item} {item}.pdf",
                         f"api: chip.set('pdk','doc',{item},'{item}.pdf')"],
                schelp=f"""Filepath to {item} document.""")

    return cfg

###############################################################################
# Library Configuration
###############################################################################

def schema_libs(cfg, lib='default', stackup='default', corner='default'):

    design = 'default'
    filetype = 'default'
    pdk = 'default'
    name = 'default'
    tool = 'default'
    key = 'default'

    scparam(cfg, ['library', lib, 'type'],
            sctype='str',
            shorthelp="Library type",
            switch="-library_type 'lib <str>'",
            example=["cli: -library_type 'mylib logiclib'",
                    "api: chip.set('library','mylib','type','logiclib')"],
            schelp="""
            Type of the library being configured. A 'logiclib' type is reserved
            for fixed height cell libraries. A 'soft' type indicates a library
            that is provided as target agnostic source code, and a 'hard'
            type indicates a non-logiclib target specificlibrary.""")

    scparam(cfg, ['library', lib, 'design'],
            sctype='[str]',
            shorthelp="Library designs",
            switch="-library_design 'lib <str>'",
            example=["cli: -library_design 'mylib mytop'",
                    "api: chip.set('library','mylib','design','mytop')"],
            schelp="""
            List of complete design functions within the library that can
            be instantiated directly by the caller.""")

    scparam(cfg, ['library', lib, design, 'testmodule'],
            sctype='[str]',
            shorthelp="Library testbench top module",
            switch="-library_testmodule 'lib design <str>'",
            example=[
                "cli: -libtary_testmodule 'mylib hello test_top'",
                "api: chip.set('library','mylib','hello','testmodule', 'test_top')"],
            schelp="""Top level test module specified on a per design basis.""")

    scparam(cfg, ['library', lib, design, 'source'],
            sctype='[file]',
            shorthelp="Library source files",
            switch="-library_source 'lib design <file>'",
            example=[
                "cli: -library_source 'mylib hello hello.v'",
                "api: chip.set('library','mylib','hello','source','hello.v')"],
            schelp="""
            List of library source files specified on a per design basis. File type
            is inferred from the file suffix. The parameter is required or
            'soft' library types and optional for 'hard' and 'stdcell'
            library types.
            (\\*.v, \\*.vh) = Verilog
            (\\*.vhd)      = VHDL
            (\\*.sv)       = SystemVerilog
            (\\*.c)        = C
            (\\*.cpp, .cc) = C++
            (\\*.py)       = Python
            """)

    scparam(cfg,['library', lib, design, 'testbench'],
            sctype='[file]',
            shorthelp="Library testbench files",
            switch="-library_testbench 'lib design <file>'",
            example=[
                "cli: -library_testbench 'mylib hello tb_top.v'",
                "api: chip.set('library','mylib, 'hello','testbench','tb_top.v')"],
            schelp="""
            A list of all library testbench sources. The files are read in order
            from first to last entered. File type is inferred from the file suffix:
            (\\*.v, \\*.vh) = Verilog
            (\\*.vhd)      = VHDL
            (\\*.sv)       = SystemVerilog
            (\\*.c)        = C
            (\\*.cpp, .cc) = C++
            (\\*.py)       = Python""")

    scparam(cfg,['library', lib, design, 'waveform'],
            sctype='[file]',
            shorthelp="Library golden waveforms",
            switch= "-library_waveform 'lib design <file>'",
            example=[
                "cli: -library_waveform 'mylib hello mytrace.vcd'",
                "api: chip.set('library','mylib','hello','waveform','mytrace.vcd')"],
            schelp="""
            Library waveform(s) used as a golden test vectors to ensure that
            compilation transformations do not modify the functional behavior of
            the source code. The waveform file must be compatible with the
            testbench and compilation flow tools. The wavefor is supplied
            on a per design basis.""")

    scparam(cfg, ['library',lib, 'pdk'],
            sctype='[str]',
            shorthelp="Library PDK",
            switch="-library_pdk 'lib <str>'",
            example=[
                "cli: -library_pdk 'mylib freepdk45",
                "api:  chip.set('library', 'mylib', 'pdk', 'freepdk45')"],
            schelp="""
            List of PDK modules supported by the library. The
            parameter is required for technology hardened ASIC libraries.""")

    scparam(cfg, ['library',lib, pdk, 'stackup'],
            sctype='[str]',
            shorthelp="Library stackups",
            switch="-library_stackup 'lib pdk <str>'",
            example=[
                "cli: -library_stackup 'mylib freepdk45 M10",
                "api:  chip.set('library','mylib','freepdk45','stackup','M10')"],
            schelp="""
            List of stackups supported for the specified PDK.""")

    scparam(cfg, ['library',lib, 'arch'],
            sctype='str',
            shorthelp="Library architecture",
            switch="-library_arch 'lib <str>'",
            example=[
                "cli: -library_arch 'mylib 12t'",
                "api: chip.set('library','mylib','arch,'12t')"],
            schelp="""
            Specifier string that identifies the row height or performance
            class of a standard cell library for APR. The arch must match up with
            the name used in the pdk_aprtech dictionary. Mixing of library archs
            in a flat place and route block is not allowed. Examples of library
            archs include 6 track libraries, 9 track libraries, 10 track
            libraries, etc. The parameter is optional for 'component'
            libtypes.""")

    models = ['nldm',
              'ccs',
              'scm',
              'aocv']

    for item in models:
        scparam(cfg,['library', lib, item, corner, filetype],
                sctype='[file]',
                shorthelp=f"Library {item.upper()} timing model",
                switch=f"-library_{item} 'lib corner filetype <file>'",
                example=[
                    f"cli: -library_{item} 'lib ss lib ss.lib.gz'",
                    f"api: chip.set('library','lib','{item}','ss','lib','ss.lib.gz')"],
                schelp=f"""
                Filepaths to {item.upper()} models. Timing files are specified
                per lib, corner, and filetype basis. Acceptable file formats
                include 'lib', 'lib.gz', and 'ldb'. """)

    layout = ['lef',
              'gds',
              'def',
              'gerber']

    for item in layout:
        scparam(cfg,['library', lib, item, stackup],
                sctype='[file]',
                shorthelp=f'Library {item.upper()} layout files',
                switch=f"-library_{item} 'lib stackup <file>'",
                example=[
                    f"cli: -library_{item} 'mylib 10M mylib.{item}'",
                    f"api: chip.set('library','mylib','{item}','10M','mylib.{item}')"],
                schelp=f"""
                List of library {item.upper()} layout files specified on a
                per stackup basis.""")

    formats = ['cdl',
               'verilog',
               'vhdl',
               'edif',
               'pspice',
               'hspice',
               'spectre',
               'edif']

    for item in formats:
        scparam(cfg,['library', lib, 'netlist', item],
            sctype='[file]',
            shorthelp=f'Library {item} netlist',
            switch=f"-library_{item}_netlist 'lib <file>'",
            example=[
                f"cli: -library_{item}_netlist 'mylib cdl mylib.{item}'",
                f"api: chip.set('library','mylib','netlist','{item}','mylib.{item}')"],
            schelp=f"""List of library netlists in the {item} format.""")

    modeltypes = ['verilog',
                  'vhdl',
                  'systemc',
                  'iss',
                  'qemu',
                  'gem5']

    for item in modeltypes:
        scparam(cfg,['library', lib, 'model', stackup],
                sctype='[file]',
                shorthelp=f"Library {item} model",
                switch=f"-library_model_{item} 'lib <file>'",
                example=[
                    f"cli: -library_model_{item} 'mylib model.{item}'",
                    f"api: chip.set('library','mylib','model',{item},'model.{item}')"],
                schelp=f"""List of library {item} models.""")

    scparam(cfg, ['library',lib, 'pgmetal'],
            sctype='str',
            shorthelp="Library PG layer",
            switch="-library_pgmetal 'lib <str>'",
            example=["cli: -library_pgmetal 'mylib m1'",
                    "api: chip.set('library','mylib','pgmetal','m1')"],
            schelp="""
            Top metal layer used for power and ground routing within the
            library. The parameter can be used to guide cell power grid
            hookup by APR tools.""")

    scparam(cfg, ['library',lib, 'tag'],
            sctype='[str]',
            shorthelp="Library tags",
            switch="-library_tag 'lib <str>'",
            example=["cli: -library_tag 'mylib virtual'",
                     "api: chip.set('library','mylib','tag','virtual')"],
            schelp="""
            Marks a library with a set of tags that can be used by the designer
            and EDA tools for optimization purposes. The tags are meant to cover
            features not currently supported by built in EDA optimization flows,
            but which can be queried through EDA tool TCL commands and lists.
            The example below demonstrates tagging the whole library as
            virtual.""")

    scparam(cfg, ['library',lib, 'site', name, 'symmetry'],
            sctype='str',
            shorthelp="Library site symmetry",
            switch="-library_site_symmetry 'lib name <str>'",
            example=[
                "cli: -library_site_symmetry 'mylib core X Y'",
                "api: chip.set('library','mylib','site','core','symmetry','X Y')"],
            schelp="""
             Site flip-symmetry based on LEF standard definition. 'X' implies
            symmetric about the x axis, 'Y' implies symmetry about the y axis, and
            'X Y' implies symmetry about the x and y axis.""")

    scparam(cfg, ['library',lib, 'site', name, 'size'],
            sctype='(float,float)',
            shorthelp="Library site size",
            switch="-library_site_size 'lib name <str>'",
            example=[
                "cli: -library_site_size 'mylib core (1.0,1.0)'",
                "api: chip.set('library','mylib','site','core','size',(1.0,1.0))"],
            schelp="""
            Size of the library size described as a (width, height) tuple in
            microns.""")

    # Cell types
    names = ['driver',
             'load',
             'buf',
             'tie',
             'hold',
             'clkbuf',
             'clkinv',
             'clkgate',
             'clklogic',
             'ignore',
             'filler',
             'tap',
             'endcap',
             'antenna']

    for item in names:
        scparam(cfg, ['library',lib, 'cells', item],
                sctype='[str]',
                shorthelp=f"Library {item} cell list",
                switch=f"-library_cells_{item} 'lib <str>'",
                example=[
                    f"cli: -library_cells_{item} 'mylib *eco*'",
                    f"api: chip.set('library','mylib','cells',{item},'*eco*')"],
                schelp="""
                List of cells grouped by a property that can be accessed
                directly by the designer and tools. The example below shows how
                all cells containing the string 'eco' could be marked as dont use
                for the tool.""")


    # tool specific hacks
    scparam(cfg, ['library',lib, 'techmap', tool],
            sctype='[file]',
            shorthelp="Library techmap file",
            switch="-library_techmap 'lib tool <file>'",
            example=[
                "cli: -library_techmap 'lib mylib yosys map.v'",
                "api: chip.set('library', 'mylib', 'techmap', 'yosys','map.v')"],
            schelp="""
            Filepaths specifying mappings from tool-specific generic cells to
            library cells.""")

    scparam(cfg, ['library',lib, 'file', tool, key, stackup],
            sctype='[file]',
            shorthelp="Library named file",
            switch="-library_file 'lib tool key stackup <file>'",
            example=[
                "cli: -library_file 'lib atool db 10M ~/libdb'",
                "api: chip.set('library','lib','file','atool','db',10M,'~/libdb')"],
            schelp="""
            List of named files specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly supported by the Library schema.""")

    scparam(cfg, ['library',lib, 'dir', tool, key, stackup],
            sctype='[dir]',
            shorthelp="Library named directory",
            switch="-library_dir 'lib tool key stackup <dir>'",
            example=[
                "cli: -library_dir 'lib atool db 10M ~/libdb'",
                "api: chip.set('library','lib','dir','atool','db',10M,'~/libdb')"],
            schelp="""
            List of named dirs specified on a per tool and per stackup basis.
            The parameter should only be used for specifying dirs that are
            not directly supported by the Library schema.""")

    return cfg

###############################################################################
# Flow Configuration
###############################################################################

def schema_flowgraph(cfg, flow='default', step='default', index='default'):

    #flowgraph input
    scparam(cfg,['flowgraph', flow, step, index, 'input'],
            sctype='[(str,str)]',
            scope='job',
            shorthelp="Flowgraph step input",
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
            scope='job',
            shorthelp="Flowgraph metric weights",
            switch="-flowgraph_weight 'flow step metric <float>'",
            example=[
                "cli: -flowgraph_weight 'asicflow cts 0 area_cells 1.0'",
                "api:  chip.set('flowgraph','asicflow','cts','0','weight','area_cells',1.0)"],
            schelp="""Weights specified on a per step and per metric basis used to give
            effective "goodnes" score for a step by calculating the sum all step
            real metrics results by the corresponding per step weights.""")

    # flowgraph tool
    scparam(cfg,['flowgraph', flow, step, index, 'tool'],
            sctype='str',
            scope='job',
            shorthelp="Flowgraph tool selection",
            switch="-flowgraph_tool 'flow step <str>'",
            example=[
                "cli: -flowgraph_tool 'asicflow place openroad'",
                "api: chip.set('flowgraph','asicflow','place','0','tool','openroad')"],
            schelp="""Name of the tool name used for task execution. Builtin tool names
            associated bound to core API functions include: minimum, maximum, join,
            verify, mux.""")

    # flowgraph arguments
    scparam(cfg,['flowgraph', flow, step, index, 'args'],
            sctype='[str]',
            scope='job',
            shorthelp="Flowgraph setup arguments",
            switch="-flowgraph_args 'flow step index <str>'",
            example=[
                "cli: -flowgraph_args 'asicflow cts 0 0'",
                "api:  chip.add('flowgraph','asicflow','cts','0','args','0')"],
            schelp="""User specified flowgraph string arguments specified on a per
            step and per index basis.""")

    #flowgraph valid bits
    scparam(cfg,['flowgraph', flow, step, index, 'valid'],
            sctype='bool',
            scope='job',
            shorthelp="Flowgraph task valid bit",
            switch="-flowgraph_valid 'flow step index <str>'",
            example=[
                "cli: -flowgraph_valid 'asicflow cts 0 true'",
                "api:  chip.set('flowgraph','asicflow','cts','0','valid',True)"],
            schelp="""Flowgraph valid bit specified on a per step and per index basis.
            The parameter can be used to control flow execution. If the bit
            is cleared (0), then the step/index combination is invalid and
            should not be run.""")

    #flowgraph timeout value
    scparam(cfg,['flowgraph', flow, step, index, 'timeout'],
            sctype='float',
            scope='job',
            shorthelp="Flowgraph task timeout value",
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

    return cfg

###########################################################################
# Flow Status
###########################################################################
def schema_flowstatus(cfg, step='default', index='default'):

    scparam(cfg,['flowstatus', step, index, 'status'],
            sctype='str',
            scope='job',
            shorthelp="Flowgraph task status",
            switch="-flowstatus_status 'step index <str>'",
            example=["cli: -flowstatus_status 'cts 10 success'",
                     "api:  chip.set('flowstatus','cts','10','status', 'success')"],
            schelp="""Parameter that tracks the status of a task. Valid values are:

            * "success": task ran successfully
            * "error": task failed with an error

            An empty value indicates the task has not yet been completed.""")

    scparam(cfg,['flowstatus', step, index, 'select'],
            sctype='[(str,str)]',
            scope='job',
            shorthelp="Flowgraph task select record",
            switch="-flowstatus_select 'step index <(str,str)>'",
            example= [
                "cli: -flowstatus_select 'cts 0 (place,42)'",
                "api:  chip.set('flowstatus','cts','0','select',('place','42'))"],
            schelp="""
            List of selected inputs for the current step/index specified as
            (in_step,in_index) tuple.""")

    return cfg

###########################################################################
# EDA Tool Setup
###########################################################################

def schema_eda(cfg, tool='default', step='default', index='default'):

    scparam(cfg, ['eda', tool, 'exe'],
            sctype='str',
            scope='job',
            shorthelp="Tool executable name",
            switch="-eda_exe 'tool<str>'",
            example=["cli: -eda_exe 'openroad openroad'",
                     "api:  chip.set('eda','openroad','exe','openroad')"],
            schelp="""Tool executable name.""")

    scparam(cfg, ['eda', tool, 'path'],
            sctype='dir',
            scope='job',
            shorthelp="Tool executable path",
            switch="-eda_path 'tool <dir>'",
            example=["cli: -eda_path 'openroad /usr/local/bin'",
                     "api:  chip.set('eda','openroad','path','/usr/local/bin')"],
            schelp="""
            File system path to tool executable. The path is pre pended to the 'exe'
            parameter for batch runs and output as an environment variable for
            interactive setup. The path parameter can be left blank if the 'exe'
            is already in the environment search path.
            Tool executable name.""")

    scparam(cfg, ['eda', tool, 'vswitch'],
            sctype='[str]',
            scope='job',
            shorthelp="Tool executable version switch",
            switch="-eda_vswitch 'tool <str>'",
            example=["cli: -eda_vswitch 'openroad -version'",
                     "api:  chip.set('eda','openroad','vswitch','-version')"],
            schelp="""
            Command line switch to use with executable used to print out
            the version number. Common switches include -v, -version,
            --version. Some tools may require extra flags to run in batch mode.""")

    scparam(cfg, ['eda', tool, 'vendor'],
            sctype='str',
            scope='job',
            shorthelp="Tool vendor",
            switch="-eda_vendor 'tool <str>'",
            example=["cli: -eda_vendor 'yosys yosys'",
                     "api: chip.set('eda','yosys','vendor','yosys')"],
            schelp="""
            Name of the tool vendor. Parameter can be used to set vendor
            specific technology variables in the PDK and libraries. For
            open source projects, the project name should be used in
            place of vendor.""")

    scparam(cfg, ['eda', tool, 'version'],
            sctype='[str]',
            scope='job',
            shorthelp="Tool version number",
            switch="-eda_version 'tool <str>'",
            example=["cli: -eda_version 'openroad >=v2.0'",
                     "api:  chip.set('eda','openroad','version','>=v2.0')"],
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

    scparam(cfg, ['eda', tool, 'format'],
            sctype='str',
            scope='job',
            shorthelp="Tool manifest file format",
            switch="-eda_format 'tool <file>'",
            example=[ "cli: -eda_format 'yosys tcl'",
                      "api: chip.set('eda','yosys','format','tcl')"],
            schelp="""
            File format for tool manifest handoff. Supported formats are tcl,
            yaml, and json.""")

    scparam(cfg, ['eda', tool, 'warningoff'],
            sctype='[str]',
            scope='job',
            shorthelp="Tool warning filter",
            switch="-eda_warningoff 'tool <str>'",
            example=["cli: -eda_warningoff 'verilator COMBDLY'",
                     "api: chip.set('eda','verilator','warningoff','COMBDLY')"],
            schelp="""
            A list of EDA warnings for which printing should be suppressed.
            Generally this is done on a per design basis after review has
            determined that warning can be safely ignored The code for turning
            off warnings can be found in the specific tool reference manual.
            """)

    scparam(cfg, ['eda', tool, 'continue'],
            sctype='bool',
            scope='job',
            shorthelp="Tool continue-on-error option",
            switch="-eda_continue 'tool <bool>'",
            example=["cli: -eda_continue 'verilator true'",
                     "api: chip.set('eda','verilator','continue', true)"],
            schelp="""
            Directs tool to continue operating even if errors are
            encountered.""")

    scparam(cfg, ['eda', tool, 'copy'],
            sctype='bool',
            scope='job',
            shorthelp="Tool copy option",
            switch="-eda_copy 'tool <bool>'",
            example=["cli: -eda_copy 'openroad true'",
                    "api: chip.set('eda','openroad','copy',true)"],
            schelp="""
            Specifies that the reference script directory should be copied and run
            from the local run directory.""")

    name = 'default'
    scparam(cfg, ['eda', tool, 'licenseserver', name],
            sctype='[str]',
            scope='job',
            shorthelp="Tool license servers",
            switch="-eda_licenseserver 'tool name <str>'",
            example=[
                "cli: -eda_licenseserver 'atool ACME_LICENSE 1700@server'",
                "api: chip.set('eda','atool','licenseserver','ACME_LICENSE','1700@server')"],
            schelp="""
            Defines a set of tool specific environment variables used by the executables
            that depend on license key servers to control access. For multiple servers,
            separate each server by a 'colon'. The named license variable are read at
            runtime (run()) and the environment variables are set.
            """)

    #######################
    # Per step/index
    ########################

    suffix = 'default'
    scparam(cfg, ['eda', tool, 'regex', step, index, suffix],
            sctype='[str]',
            scope='job',
            shorthelp="Tool regex filter",
            switch="-eda_regex 'tool step index suffix <str>'",
            example=[
                "cli: -eda_regex 'openroad place 0 error -v ERROR",
                "api: chip.set('eda','openroad','regex','place','0','error','-v ERROR')"],
            schelp="""
             A list of piped together grep commands. Each entry represents a set
            of command line arguments for grep including the regex pattern to
            match. Starting with the first list entry, each grep output is piped
            into the following grep command in the list. Supported grep options
            include, -t, -i, -E, -x, -e. Patterns starting with "-" should be
            directly preceeded by the "-e" option. The following example
            illustrates the concept.

            UNIX grep:
            >> grep WARNING place.log | grep -v "bbox" > place.warnings

            siliconcompiler:
            chip.set('eda','openroad','regex','place',0','warnings',["WARNING","-v bbox"])

            Defines a set of tool specific environment variables used by the executables
            that depend on license key servers to control access. For multiple servers,
            separate each server by a 'colon'. The named license variable are read at
            runtime (run()) and the environment variables are set.""")


    scparam(cfg, ['eda', tool, 'option', step, index],
            sctype='[str]',
            scope='job',
            shorthelp="Tool executable options",
            switch="-eda_option 'tool step index name <str>'",
            example=[
                "cli: -eda_option 'openroad cts 0 -no_init'",
                "api: chip.set('eda','openroad','option','cts','0','-no_init')"],
            schelp="""
            List of command line options for the tool executable, specified on
            a per tool and per step basis. Options must not include spaces.
            For multiple argument options, each option is a separate list element.
            """)

    name = 'default'
    scparam(cfg, ['eda', tool, 'variable', step, index, name],
            sctype='[str]',
            scope='job',
            shorthelp="Tool script variables",
            switch="-eda_variable 'tool step index name <str>'",
            example=[
                "cli: -eda_variable 'openroad cts 0 myvar 42'",
                "api: chip.set('eda','openroad','variable','cts','0','myvar','42')"],
            schelp="""
            Tool script variables specified as key value pairs. Variable
            names and value types must match the name and type of tool and reference
            script consuming the variable.""")

    name = 'default'
    scparam(cfg, ['eda', tool, 'env', step, index, name],
            sctype='str',
            scope='job',
            shorthelp="Tool environment variables",
            switch="-eda_env 'tool step index name <str>'",
            example=[
                "cli: -eda_env 'openroad cts 0 MYVAR 42'",
                "api: chip.set('eda','openroad','env','cts','0','MYVAR','42')"],
            schelp="""
            Environment variables to set for individual tasks. Keys and values
            should be set in accordance with the tool's documentation. Most
            tools do not require extra environment variables to function.""")

    scparam(cfg, ['eda', tool, 'input', step, index],
            sctype='[file]',
            scope='job',
            shorthelp="Tool input files",
            switch="-eda_input 'tool step index <str>'",
            example=[
                "cli: -eda_input 'openroad place 0 oh_add.def'",
                "api: chip.set('eda','openroad','input','place','0','oh_add.def')"],
            schelp="""
            List of data files to be copied from previous flowgraph steps 'output'
            directory. The list of steps to copy files from is defined by the
            list defined by the dictionary key ['flowgraph', step, index, 'input'].
            All files must be available for flow to continue. If a file
            is missing, the program exists on an error.""")

    scparam(cfg, ['eda', tool, 'output', step, index],
            sctype='[file]',
            scope='job',
            shorthelp="Tool output files",
            switch="-eda_output 'tool step index <str>'",
            example=[
                "cli: -eda_output 'openroad place 0 oh_add.def'",
                "api: chip.set('eda','openroad','output','place','0','oh_add.def')"],
            schelp="""
            List of data files to be copied from previous flowgraph steps 'output'
            directory. The list of steps to copy files from is defined by the
            list defined by the dictionary key ['flowgraph', step, index, 'output'].
            All files must be available for flow to continue. If a file
            is missing, the program exists on an error.""")

    scparam(cfg, ['eda', tool, 'require', step, index],
            sctype='[str]',
            scope='job',
            shorthelp="Tool parameter requirements",
            switch="-eda_require 'tool step index <str>'",
            example=[
                "cli: -eda_require 'openroad cts 0 design'",
                "api: chip.set('eda','openroad','require','cts','0','design')"],
            schelp="""
            List of keypaths to required tool parameters. The list is used
            by check() to verify that all parameters have been set up before
            step execution begins.""")

    metric = 'default'
    scparam(cfg, ['eda', tool, 'report', step, index, metric],
            sctype='[file]',
            scope='job',
            shorthelp="Tool report files",
            switch="-eda_report 'tool step index metric <str>'",
            example=[
                 "cli: -eda_report 'openroad place 0 holdtns place.log'",
                "api: chip.set('eda','openroad','report','syn','0','holdtns','place.log')"],
            schelp="""
            List of report files associated with a specific 'metric'. The file path
            specified is relative to the run directory of the current task.""")

    scparam(cfg, ['eda', tool, 'refdir', step, index],
            sctype='[dir]',
            scope='job',
            shorthelp="Tool script directory",
            switch="-eda_refdir 'tool step index <dir>'",
            example=[
                "cli: -eda_refdir 'yosys syn 0 ./myref'",
                "api:  chip.set('eda','yosys','refdir','syn','0','./myref')"],
            schelp="""
            Path to directories containing reference flow scripts, specified
            on a per step and index basis.""")

    scparam(cfg, ['eda', tool, 'script', step, index],
            sctype='[file]',
            scope='job',
            shorthelp="Tool entry script",
            switch="-eda_script 'tool step index <file>'",
            example=[
                "cli: -eda_script 'yosys syn 0 syn.tcl'",
                "api: chip.set('eda','yosys','script','syn','0','syn.tcl')"],
            schelp="""
            Path to the entry script called by the executable specified
            on a per tool and per step basis.""")

    scparam(cfg, ['eda', tool, 'prescript', step, index],
            sctype='[file]',
            scope='job',
            shorthelp="Tool pre-step script",
            switch="-eda_prescript 'tool step index <file>'",
            example=[
                 "cli: -eda_prescript 'yosys syn 0 pre.tcl'",
                "api: chip.set('eda','yosys','prescript','syn','0','pre.tcl')"],
            schelp="""
            Path to a user supplied script to execute after reading in the design
            but before the main execution stage of the step. Exact entry point
            depends on the step and main script being executed. An example
            of a prescript entry point would be immediately before global
            placement.""")

    scparam(cfg, ['eda', tool, 'postscript', step, index],
            sctype='[file]',
            scope='job',
            shorthelp="Tool post-step script",
            switch="-eda_postscript 'tool step index <file>'",
            example=[
                "cli: -eda_postscript 'yosys syn 0 post.tcl'",
                "api: chip.set('eda','yosys','postscript','syn','0','post.tcl')"],
            schelp="""
            Path to a user supplied script to be executed after all built in
            tasks (except for data export) have completed.""")

    scparam(cfg, ['eda', tool, 'threads', step, index],
            sctype='int',
            scope='job',
            shorthelp="Tool thread parallelism",
            switch="-eda_threads 'tool step index <int>'",
            example=["cli: -eda_threads 'magic drc 0 64'",
                     "api: chip.set('eda','magic','threads','drc','0','64')"],
            schelp="""
            Thread parallelism to use for execution specified on a per tool and per
            step basis. If not specified, SC queries the operating system and sets
            the threads based on the maximum thread count supported by the
            hardware.""")

    return cfg

###########################################################################
# Scratch parameters (for internal use only)
###########################################################################

def schema_arg(cfg):

    scparam(cfg, ['arg', 'step'],
            sctype='str',
            scope='scratch',
            shorthelp="Current step",
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
            shorthelp="Current sindex",
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

def schema_metric(cfg, step='default', index='default',group='default'):

    metrics = {'errors': 'errors',
               'warnings' :'warnings',
               'drvs' : 'design rule violations',
               'unconstrained' : 'unconstrained timing paths'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item, group],
                sctype='int',
                scope='job',
                require='all',
                shorthelp=f"Metric: total {item}",
                switch=f"-metric_{item} 'step index group <int>'",
                example=[
                    f"cli: -metric_{item} 'dfm 0 goal 0'",
                    f"api: chip.set('metric','dfm','0','{item}','real',0)"],
                schelp=f"""Metric tracking the total number of {val} on a
                per step and index basis.""")

    scparam(cfg, ['metric', step, index, 'coverage', group],
            sctype='float',
            scope='job',
            require='all',
            shorthelp=f"Metric: coverage",
            switch="-metric_coverage 'step index group <float>'",
            example=[
                "cli: -metric_coverage 'place 0 goal 99.9'",
                "api: chip.set('metric','place','0','coverage','goal',99.9)"],
            schelp=f"""
            Metric tracking the test coverage in the design expressed as a percentage
            with 100 meaning full coverage. The meaning of the metric depends on the
            task being executed. It can refer to code coverage, feature coverage,
            stuck at fault coverage.""")

    scparam(cfg, ['metric', step, index, 'security', group],
            sctype='float',
            scope='job',
            require='all',
            shorthelp="Metric: security",
            switch="-metric_security 'step index group <float>'",
            example=[
                "cli: -metric_security 'place 0 goal 100'",
                "api: chip.set('metric','place','0','security','goal',100)"],
            schelp=f"""
            Metric tracking the level of security (1/vulnerability) of the design.
            A completely secure design would have a score of 100. There is no
            absolute scale for the security metrics (like with power, area, etc)
            so the metric will be task and tool dependent.""")

    metrics = {'luts': 'FPGA LUTs',
               'dsps' :'FPGA DSP slices',
               'brams' : 'FPGA BRAM tiles'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item, group],
                sctype='int',
                scope='job',
                require='fpga',
                shorthelp=f"Metric: {val}",
                switch=f"-metric_{item} 'step index group <int>'",
                example=[
                    f"cli: -metric_{item} 'place 0 goal 100'",
                    f"api: chip.set('metric','place','0','{item}','real',100)"],
                schelp=f"""
                Metric tracking the total {val} used by the design as reported
                by the implementation tool. There is no standardized definition
                for this metric across vendors, so metric comparisons can
                generally only be done between runs on identical tools and
                device families.""")

    metrics = {'cellarea': 'cell area (ignoring fillers)',
               'totalarea' :'physical die area'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item, group],
                sctype='float',
                scope='job',
                require='asic',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index group <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 goal 100.00'",
                    f"api: chip.set('metric','place','0','{item}','real',100.00)"],
                schelp=f"""
                Metric tracking the total {val} occupied by the design. The
                metric is specified in um^2.""")

    scparam(cfg, ['metric', step, index, 'utilization', group],
            sctype='float',
            scope='job',
            require='asic',
            shorthelp=f"Metric: area utilization",
            switch=f"-metric_utilization step index group <float>",
            example=[
                f"cli: -metric_utilization 'place 0 goal 50.00'",
                f"api: chip.set('metric','place','0','utilization','real',50.00)"],
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
        scparam(cfg, ['metric', step, index, item, group],
                sctype='float',
                scope='job',
                require='all',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index group <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 goal 0.01'",
                    f"api: chip.set('metric','place','0','{item}','real',0.01)"],
                schelp=f"""
                Metric tracking the {val} of the design specified on a per step
                and index basis. Power metric depend heavily on the method
                being used for extraction: dynamic vs static, workload
                specification (vcd vs saif), power models, process/voltage/temperature.
                The power {item} metric tries to capture the data that would
                usually be reflected inside a datasheet given the approprate
                footnote conditions.""")

    scparam(cfg, ['metric', step, index, 'irdrop', group],
            sctype='float',
            scope='job',
            require='asic',
            shorthelp=f"Metric: peak IR drop",
            switch="-metric_irdrop 'step index group <float>'",
            example=[
                f"cli: -metric_irdrop 'place 0 real 0.05'",
                f"api: chip.set('metric','place','0','irdrop','real',0.05)"],
            schelp=f"""
            Metric tracking the peak IR drop in the design based on extracted
            power and ground rail parasitics, library power models, and
            switching activity. The switching activity calculated on a per
            node basis is taken from one of three possible sources, in order
            of priority: VCD file, SAIF file, 'activityfactor' parameter.""")

    metrics = {'holdpaths': 'hold',
               'setuppaths': 'setup'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item, group],
                sctype='int',
                scope='job',
                require='all',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index group <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 goal 10'",
                    f"api: chip.set('metric','place','0','{item}','real',10)"],
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
        scparam(cfg, ['metric', step, index, item, group],
                sctype='float',
                scope='job',
                require='all',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index group <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 goal 0.01'",
                    f"api: chip.set('metric','place','0','{item}','real', 0.01)"],
                schelp=f"""
                Metric tracking the {val} on a per step and index basis.
                Metric unit is nanoseconds.""")

    metrics = {'macros': 'macros',
               'cells': 'cell instances',
               'registers': 'register instances',
               'buffers': 'buffer and inverter instances',
               'transistors': 'transistors',
               'pins': 'pins',
               'nets': 'nets',
               'vias': 'vias'}

    for item, val in metrics.items():
        scparam(cfg, ['metric', step, index, item, group],
                sctype='int',
                scope='job',
                require='asic',
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index group <float>'",
                example=[
                    f"cli: -metric_{item} 'place 0 goal 100'",
                    f"api: chip.set('metric','place','0','{item}','real', 50)"],
                schelp=f"""
                Metric tracking the total number of {val} in the design
                on a per step and index basis.""")

    item = 'wirelength'
    scparam(cfg, ['metric', step, index, item, group],
            sctype='float',
            scope='job',
            require='asic',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index group <float>'",
            example=[
                f"cli: -metric_{item} 'place 0 goal 100.0'",
                f"api: chip.set('metric','place','0','{item}','real', 50.0)"],
            schelp=f"""
            Metric tracking the total {item} of the design on a per step
            and index basis. The unit is meters.""")

    item = 'overflow'
    scparam(cfg, ['metric', step, index, item, group],
            sctype='int',
            scope='job',
            require='asic',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index group <float>'",
            example=[
                f"cli: -metric_{item} 'place 0 goal 0'",
                f"api: chip.set('metric','place','0','{item}','real', 50)"],
            schelp=f"""
            Metric tracking the total number of overflow tracks for the routing
            on per step and index basis. Any non-zero number suggests an over
            congested design. To analyze where the congestion is occurring
            inspect the router log files for detailed per metal overflow
            reporting and open up the design to find routing hotspots.""")

    item = 'memory'
    scparam(cfg, ['metric', step, index, item, group],
            sctype='float',
            scope='job',
            require='asic',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index group <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 goal 10e9'",
                f"api: chip.set('metric','dfm','0','{item}','real', 10e9)"],
            schelp=f"""
            Metric tracking total peak program memory footprint on a per
            step and index basis, specified in bytes.""")

    item = 'exetime'
    scparam(cfg, ['metric', step, index, item, group],
            sctype='float',
            scope='job',
            require='asic',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index group <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 goal 10.0'",
                f"api: chip.set('metric','dfm','0','{item}','real, 10.0)"],
            schelp=f"""
            Metric tracking time spent by the eda executable 'exe' on a
            per step and index basis. It does not include the siliconcompiler
            runtime overhead or time waitig for I/O operations and
            inter-processor communication to complete. The metric unit
            is seconds.""")

    item = 'tasktime'
    scparam(cfg, ['metric', step, index, item, group],
            sctype='float',
            scope='job',
            require='asic',
            shorthelp=f"Metric: {item}",
            switch=f"-metric_{item} 'step index group <float>'",
            example=[
                f"cli: -metric_{item} 'dfm 0 goal 10.0'",
                f"api: chip.set('metric','dfm','0','{item}','real, 10.0)"],
            schelp=f"""
            Metric trakcing the total amount of time spent on a task from
            beginning to end, including data transfers and pre/post processing.
            The metric unit is seconds.""")

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
               'toolversion': ['tool version',
                               '1.0',
                               """The tool version captured correspnds to the 'tool'
                               parameter within the 'eda' dictionary."""],
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
                scope='job',
                shorthelp=f"Record: {val[0]}",
                switch=f"-record_{item} 'step index <str>'",
                example=[
                    f"cli: -record_{item} 'dfm 0 <{val[1]}>'",
                    f"api: chip.set('record','dfm','0','{item}', <{val[1]}>)"],
                schelp=f'Record tracking the {val[0]} per step and index basis. {helpext}')

    return cfg

###########################################################################
# Run Options
###########################################################################

#TODO add scope below

def schema_options(cfg):
    ''' Run-time options
    '''

    # Units
    units = {
        'time' : 'ns',
        'capacitance' : 'pf',
        'resistance' : 'ohm',
        'inducatance' : 'nh',
        'voltage' : 'mv',
        'current' : 'ma',
        'power' : 'mw'
    }

    for item,val in units.items():
        scparam(cfg, ['unit', item],
                sctype='str',
                defvalue=val,
                shorthelp=f"Units used for {item}",
                switch=f"-record_{item} '<str>'",
                example=[
                    f"cli: -unit_{item} '{val}'",
                    f"api: chip.set('unit','{item}',{val})"],
                schelp=f"""
                Units used for {item} when not explicitly specified.""")

    # Remote processing
    scparam(cfg, ['remote'],
            sctype='bool',
            scope='job',
            shorthelp="Enable remote processing",
            switch="-remote <bool>",
            example=["cli: -remote",
                    "api: chip.set('remote', True)"],
            schelp="""
            Sends job for remote processing if set to true. The remote
            option requires a credentials file to be placed in the home
            directory. Fore more information, see the credentials
            parameter.""")

    scparam(cfg, ['credentials'],
            sctype='[file]',
            scope='job',
            shorthelp="User credentials file",
            switch="-credentials <file>'",
            example=["cli: -credentials /home/user/.sc/credentials",
                    "api: chip.set('credentials','/home/user/.sc/credentials')"],
            schelp="""
            Filepath to credentials used for remote processing. If the
            credentials parameter is empty, the remote processing client program
            tries to access the ".sc/credentials" file in the user's home
            directory. The file supports the following fields:

            userid=<user id>
            secret_key=<secret key used for authentication>
            server=<ipaddr or url>""")

    scparam(cfg, ['jobscheduler'],
            sctype='str',
            scope='job',
            shorthelp="Job scheduler name",
            switch="-jobscheduler <str>",
            example=["cli: -jobscheduler slurm",
                    "api: chip.set('jobscheduler','slurm')"],
            schelp="""
            Sets the type of job scheduler to be used for each individual
            flowgraph steps. If the parameter is undefined, the steps are executed
            on the same machine that the SC was launched on. If 'slurm' is used,
            the host running the 'sc' command must be running a 'slurmctld' daemon
            managing a Slurm cluster. Additionally, the build directory ('-dir')
            must be located in shared storage which can be accessed by all hosts
            in the cluster.""")

    # Compilation
    scparam(cfg, ['mode'],
            sctype='str',
            scope='job',
            shorthelp="Compilation mode",
            switch="-mode <str>",
            require='all',
            example=["cli: -mode asic",
                    "api: chip.set('mode','asic')"],
            schelp="""
            Sets the operating mode of the compiler. Valid modes are:
            asic: RTL to GDS ASIC compilation
            fpga: RTL to bitstream FPGA compilation
            sim: simulation to verify design and compilation
            """)

    scparam(cfg, ['target'],
            sctype='str',
            scope='job',
            shorthelp="Compilation target",
            switch="-target <str>",
            example=["cli: -target freepdk45_demo",
                     "api: chip.set('target','freepdk45_demo')"],
            schelp="""
            Sets a target module to be used for compilation. The target
            module must set up all paramaters needed. The target module
            may load multiple flows and libraries.
            """)

    scparam(cfg, ['flow'],
            sctype='str',
            scope='job',
            shorthelp="Compilation flow",
            switch="-flow <str>",
            example=["cli: -flow asicfow",
                     "api: chip.set('flow','asicflow')"],
            schelp="""
            Sets the flow for the current run. The flow name
            must match up with an 'flow' in the flowgraph""")

    scparam(cfg, ['optmode'],
            sctype='str',
            scope='job',
            require='all',
            defvalue='O0',
            shorthelp="Optimization mode",
            switch="-O<str>",
            example=["cli: -O3",
                    "api: chip.set('optmode','3')"],
            schelp="""
            The compiler has modes to prioritize run time and ppa. Modes
            include.

            (0) = Exploration mode for debugging setup
            (1) = Higher effort and better PPA than O0
            (2) = Higher effort and better PPA than O1
            (3) = Signoff quality. Better PPA and higher run times than O2
            (4-98) = Reserved (compiler/target dependent)
            (99) = Experimental highest possible effort, may be unstable
            """)

    #TODO: with modular flows does this go away?
    scparam(cfg, ['frontend'],
            sctype='str',
            scope='job',
            defvalue='verilog',
            shorthelp="Compilation frontend",
            switch="-frontend <frontend>",
            example=["cli: -frontend systemverilog",
                    "api: chip.set('frontend', 'systemverilog')"],
            schelp="""
            Specifies the frontend that flows should use for importing and
            processing source files. Default option is 'verilog', also supports
            'systemverilog' and 'chisel'. When using the Python API, this parameter
            must be configured before calling load_target().""")

    key = 'default'
    scparam(cfg, ['techarg', key],
            sctype='[str]',
            scope='job',
            shorthelp="Target technology argument",
            switch="-techarg 'arg <str>",
            example=["cli: -techarg 'mimcap true",
                    "api: chip.set('techarg','mimcap', 'true')"],
            schelp="""
            Parameter passed in as key/value pair to the technology target
            referenced in the load_pdk() API call. See the target technology
            for specific guidelines regarding configuration parameters.""")

    scparam(cfg, ['flowarg', key],
            sctype='[str]',
            scope='job',
            shorthelp="Target flow argument",
            switch="-flowarg 'arg <str>",
            example=["cli: -flowarg 'n 100",
                    "api: chip.set('flowarg','n', 100)"],
            schelp="""
            Parameter passed in as key/value pair to the flow target
            referenced in the load_flow() API call. See the target flow
            for specific guidelines regarding configuration parameters.""")

    # Configuration
    scparam(cfg,['oformat'],
            sctype='str',
            scope='job',
            shorthelp="Output format",
            switch="-oformat <str>",
            example=["cli: -oformat gds",
                    "api: chip.set('oformat', 'gds')"],
            schelp="""
            File format to use for writing the final siliconcompiler output to
            disk. For cases, when only one output format exists, the 'oformat'
            parameter can be omitted. Examples of ASIC layout output formats
            include GDS and OASIS.""")


    scparam(cfg, ['cfg'],
            sctype='[file]',
            scope='job',
            shorthelp="Configuration manifest",
            switch="-cfg <file>",
            example=["cli: -cfg mypdk.json",
                    "api: chip.set('cfg','mypdk.json')"],
            schelp="""
            List of filepaths to JSON formatted schema configuration
            manifests. The files are read in automatically when using the
            'sc' command line application. In Python programs, JSON manifests
            can be merged into the current working manifest using the
            read_manifest() method.""")

    scparam(cfg, ['env', key],
            sctype='str',
            scope='job',
            shorthelp="Environment variables",
            switch="-env 'key <str>",
            example=["cli: -env 'PDK_HOME /disk/mypdk'",
                    "api: chip.set('env', 'PDK_HOME', '/disk/mypdk')"],
            schelp="""
            Certain tools and reference flows require global environment
            variables to be set. These variables can be managed externally or
            specified through the env variable.""")

    scparam(cfg, ['scpath'],
            sctype='[dir]',
            scope='job',
            shorthelp="Search path",
            switch="-scpath <dir>",
            example=["cli: -scpath '/home/$USER/sclib'",
                     "api: chip.set('scpath', '/home/$USER/sclib')"],
            schelp="""
            Specifies python modules paths for target import.""")

    scparam(cfg, ['loglevel'],
            sctype='str',
            scope='job',
            defvalue='INFO',
            shorthelp="Logging level",
            switch="-loglevel <str>",
            example=["cli: -loglevel INFO",
                    "api: chip.set('loglevel', 'INFO')"],
            schelp="""
            Provides explicit control over the level of debug logging printed.
            Valid entries include INFO, DEBUG, WARNING, ERROR.""")

    scparam(cfg, ['dir'],
            sctype='dir',
            scope='job',
            defvalue='build',
            shorthelp="Build directory",
            switch="-dir <dir>",
            example=["cli: -dir ./build_the_future",
                    "api: chip.set('dir','./build_the_future')"],
            schelp="""
            The default build directory is in the local './build' where SC was
            executed. The 'dir' parameters can be used to set an alternate
            compilation directory path.""")

    scparam(cfg, ['jobname'],
            sctype='str',
            scope='job',
            defvalue='job0',
            shorthelp="Job name",
            switch="-jobname <str>",
            example=["cli: -jobname may1",
                    "api: chip.set('jobname','may1')"],
            schelp="""
            Jobname during invocation of run(). The jobname combined with a
            defined director structure (<dir>/<design>/<jobname>/<step>/<index>)
            enables multiple levels of transparent job, step, and index
            introspection.""")

    scparam(cfg, ['jobinput','default','default','default'],
            sctype='str',
            scope='job',
            shorthelp="Input job name",
            switch="-jobinput 'job step index <str>'",
            example=[
                "cli: -jobinput 'job1 cts 0 job0'",
                "api:  chip.set('jobinput', 'job1', 'cts, '0', 'job0')"],
            schelp="""
            Specifies jobname inputs for the current run() on a per step
            and per index basis. During execution, the default behavior is to
            copy inputs from the current job.""")

    scparam(cfg, ['steplist'],
            sctype='[str]',
            scope='job',
            shorthelp="Compilation step list",
            switch="-steplist <step>",
            example=["cli: -steplist 'import'",
                    "api: chip.set('steplist','import')"],
            schelp="""
            List of steps to execute. The default is to execute all steps
            defined in the flow graph.""")

    scparam(cfg, ['skipstep'],
            sctype='[str]',
            scope='job',
            shorthelp="Skip step list",
            switch="-skipstep <str>",
            example=["cli: -skipstep lvs",
                    "api: chip.set('skipstep', 'lvs')"],
            schelp="""
            List of steps to skip during execution.The default is to
            execute all steps  defined in the flow graph.""")

    scparam(cfg, ['indexlist'],
            sctype='[str]',
            scope='job',
            shorthelp="Compilation index list",
            switch="-indexlist <index>",
            example=["cli: -indexlist 0",
                    "api: chip.set('indexlist','0')"],
            schelp="""
            List of indices to execute. The default is to execute all
            indices for each step of a run.""")

    scparam(cfg, ['bkpt'],
            sctype='[str]',
            scope='job',
            shorthelp="Breakpoint list",
            switch="-bkpt <str>",
            example=["cli: -bkpt place",
                    "api: chip.set('bkpt','place')"],
            schelp="""
            List of step stop (break) points. If the step is a TCL
            based tool, then the breakpoints stops the flow inside the
            EDA tool. If the step is a command line tool, then the flow
            drops into a Python interpreter.""")

    scparam(cfg, ['msgevent'],
            sctype='[str]',
            scope='job',
            shorthelp="Message event trigger",
            switch="-msgevent <str>",
            example=["cli: -msgevent export",
                    "api: chip.set('msgevent','export')"],
            schelp="""
            A list of steps after which to notify a recipient. For
            example if values of syn, place, cts are entered separate
            messages would be sent after the completion of the syn,
            place, and cts steps.""")

    scparam(cfg, ['msgcontact'],
            sctype='[str]',
            scope='job',
            shorthelp="Message contact",
            switch="-msgcontact <str>",
            example=[
                "cli: -msgcontact 'wile.e.coyote@acme.com'",
                "api: chip.set('msgcontact','wile.e.coyote@acme.com')"],
            schelp="""
            A list of phone numbers or email addresses to message
            on a event event within the msg_event param. Actual
            support for email and phone messages is platform
            dependent.""")

    filetype = 'default'
    scparam(cfg, ['showtool', filetype],
            sctype='str',
            scope='job',
            shorthelp="Select data display tool",
            switch="-showtool 'filetype <tool>'",
            example=["cli: -showtool 'gds klayout'",
                    "api: chip.set('showtool', 'gds', 'klayout')"],
            schelp="""
            Selects the tool to use by the show function for displaying
            the specified filetype.""")

    scparam(cfg, ['metricoff'],
            sctype='[str]',
            scope='job',
            shorthelp="Metric summary filter",
            switch="-metricoff '<str>'",
            example=["cli: -metricoff 'wirelength'",
                     "api: chip.set('metricoff','wirelength')"],
            schelp="""
            List of metrics to supress when printing out the run
            summary.""")

    # Booleans
    scparam(cfg, ['clean'],
            sctype='bool',
            scope='job',
            shorthelp="Clean up after run",
            switch="-clean <bool>",
            example=["cli: -clean",
                     "api: chip.set('clean', True)"],
            schelp="""
            Clean up all intermediate and non essential files at the end
            of a task, leaving only the log file and 'report' and
            'output' parameters associated with the task tool.""")

    scparam(cfg, ['hash'],
            sctype='bool',
            scope='job',
            shorthelp="Enable file hashing",
            switch="-hash <bool>",
            example=["cli: -hash",
                    "api: chip.set('hash', True)"],
            schelp="""
            Enables hashing of all inputs and outputs during
            compilation. The hash values are stored in the hashvalue
            field of the individual parameters.""")

    scparam(cfg, ['nodisplay'],
            sctype='bool',
            scope='job',
            shorthelp="Headless execution",
            switch="-nodisplay <bool>",
            example=["cli: -nodisplay",
                    "api: chip.set('nodisplay', True)"],
            schelp="""
            The '-nodisplay' flag prevents SiliconCompiler from
            opening GUI windows such as the final metrics report.""")

    scparam(cfg, ['quiet'],
            sctype='bool',
            scope='job',
            shorthelp="Quiet execution",
            switch="-quiet <bool>",
            example=["cli: -quiet",
                    "api: chip.set('quiet', True)"],
            schelp="""
            The -quiet option forces all steps to print to a log file.
            This can be useful with Modern EDA tools which print
            significant content to the screen.""")

    scparam(cfg, ['jobincr'],
            sctype='bool',
            scope='job',
            shorthelp="Autoincrement jobname",
            switch="-jobincr <bool>",
            example=["cli: -jobincr",
                    "api: chip.set('jobincr', True)"],
            schelp="""
            Forces an auto-update of the jobname parameter if a directory
            matching the jobname is found in the build directory. If the
            jobname does not include a trailing digit, then a the number
            '1' is added to the jobname before updating the jobname
            parameter.""")

    scparam(cfg, ['novercheck'],
            sctype='bool',
            defvalue='false',
            scope='job',
            shorthelp="Disable version checking",
            switch="-novercheck <bool>",
            example=["cli: -novercheck",
                    "api: chip.set('novercheck', 'true')"],
            schelp="""
            Disables strict version checking on all invoked tools if True.
            The list of supported version numbers is defined in the
            'version' parameter in the 'eda' dictionary for each tool.""")

    scparam(cfg, ['relax'],
            sctype='bool',
            scope='job',
            shorthelp="Relax RTL linting",
            switch="-relax <bool>",
            example=["cli: -relax",
                    "api: chip.set('relax', 'true')"],
            schelp="""
            Specifies that tools should be lenient and suppress some
            warnings that may or may not indicate design issues.""")

    scparam(cfg, ['track'],
            sctype='bool',
            scope='job',
            shorthelp="Enable provenance tracking",
            switch="-track <bool>",
            example=["cli: -track",
                    "api: chip.set('track', 'true')"],
            schelp="""
            Turns on tracking of all 'record' parameters during each
            task. Tracking will result in potentially sensitive data
            being recorded in the manifest so only turn on this feature
            if you have control of the final manifest.""")

    scparam(cfg, ['trace'],
            sctype='bool',
            scope='job',
            shorthelp="Enable debug traces",
            switch="-trace <bool>",
            example=["cli: -trace",
                    "api: chip.set('trace', True)"],
            schelp="""
            Enables debug tracing during compilation and/or runtime.""")

    scparam(cfg, ['skipall'],
            sctype='bool',
            scope='job',
            shorthelp="Skip all tasks",
            switch="-skipall <bool>",
            example=["cli: -skipall",
                    "api: chip.set('skipall', 'true')"],
            schelp="""
            Skips the execution of all tools in run(), enabling a quick
            check of tool and setup without having to run through each
            step of a flow to completion.""")

    scparam(cfg, ['skipcheck'],
            sctype='bool',
            scope='job',
            shorthelp="Skip manifest check",
            switch="-skipcheck <bool>",
            example=["cli: -skipcheck",
                     "api: chip.set('skipcheck', True)"],
            schelp="""
            Bypasses the strict runtime manifest check. Can be used for
            accelerating initial bringup of tool/flow/pdk/libs targets.
            The flag should not be used for production compilation.""")

    scparam(cfg, ['copyall'],
            sctype='bool',
            scope='job',
            shorthelp="Copy all inputs to build directory",
            switch="-copyall <bool>",
            example=["cli: -copyall",
                    "api: chip.set('copyall', 'true')"],
            schelp="""
            Specifies that all used files should be copied into the
            build directory, overriding the per schema entry copy
            settings.""")

    scparam(cfg, ['show'],
            sctype='bool',
            scope='job',
            shorthelp="Show layout",
            switch="-show <bool>",
            example=["cli: -show",
                    "api: chip.set('show', 'true')"],
            schelp="""
            Specifies that the final hardware layout should be
            shown after the compilation has been completed. The
            final layout and tool used to display the layout is
            flow dependent.""")

    return cfg

############################################
# Package information
############################################

def schema_package(cfg, group):

    # hack code to enable reuse of patternf for main/lib
    if group == 'library':
        path = ['library', 'default', 'package']
        shelp = "Library package"
        switch = 'library_package'
        keys = "lib "
        api = "'library', 'lib', 'package'"
    else:
        path = ['package']
        shelp = "Package"
        switch = 'package'
        keys = ""
        api = "package"

    name = 'default'

    scparam(cfg,[*path, 'name'],
            sctype='str',
            shorthelp=f"{shelp} name",
            switch=f"-{switch}_name '{keys}<str>'",
            example=[
                f"cli: -{switch}_name '{keys}yac'",
                f"api: chip.set({api},'name','yac')"],
            schelp=f"""{shelp} name.""")

    scparam(cfg,[*path, 'version'],
            sctype='str',
            shorthelp=f"{shelp} version",
            switch=f"-{switch}_version '{keys}<str>'",
            example=[
                f"cli: -{switch}_version '{keys}1.0'",
                f"api: chip.set({api},'version','1.0')"],
            schelp=f"""{shelp} version. Can be a branch, tag, commit hash,
            or a semver compatible version.""")

    scparam(cfg,[*path, 'description'],
            sctype='str',
            shorthelp=f"{shelp} description",
            switch=f"-{switch}_description '{keys}<str>'",
            example=[
                f"cli: -{switch}_description '{keys}Yet another cpu'",
                f"api: chip.set({api},'description','Yet another cpu')"],
            schelp=f"""{shelp} short one line description for package
            managers and summary reports.""")

    scparam(cfg,[*path, 'keyword'],
            sctype='str',
            shorthelp=f"{shelp} keyword",
            switch=f"-{switch}_keyword '{keys}<str>'",
            example=[
                f"cli: -{switch}_keyword '{keys}cpu'",
                f"api: chip.set({api},'keyword','cpu')"],
            schelp=f"""{shelp} keyword(s) used to characterize package.""")

    scparam(cfg,[*path, 'homepage'],
            sctype='str',
            shorthelp=f"{shelp} project homepage",
            switch=f"-{switch}_homepage '{keys}<str>'",
            example=[
                f"cli: -{switch}_homepage '{keys}index.html'",
                f"api: chip.set({api},'homepage','index.html')"],
            schelp=f"""{shelp} homepage.""")

    scparam(cfg,[*path, 'doc', 'homepage'],
            sctype='str',
            shorthelp=f"{shelp} documentation homepage",
            switch=f"-{switch}_doc_homepage '{keys}<str>'",
            example=[
                f"cli: -{switch}_doc_homepage '{keys}index.html'",
                f"api: chip.set({api},'doc', 'homepage','index.html')"],
            schelp=f"""
            {shelp} documentation homepage. Filepath to design docs homepage.
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
        scparam(cfg,[*path, 'doc', item],
            sctype='[file]',
            shorthelp=f"{shelp} {item} document",
            switch=f"-{switch}_doc_{item} '{keys}<str>'",
            example=[
                f"cli: -{switch}_doc_{item} '{keys}{item}.pdf'",
                f"api: chip.set({api},'doc',{item},'{item}.pdf')"],
            schelp=f""" {shelp} list of {item} documents.""")

    scparam(cfg,[*path, 'repo'],
            sctype='[str]',
            shorthelp=f"{shelp} code repository",
            switch=f"-{switch}_repo '{keys}<str>'",
            example=[
                f"cli: -{switch}_repo '{keys}git@github.com:aolofsson/oh.git'",
                f"api: chip.set({api},'repo','git@github.com:aolofsson/oh.git')"],
            schelp=f"""{shelp} IP address to source code repository.""")


    scparam(cfg,[*path, 'dependency', name],
            sctype='[str]',
            shorthelp=f"{shelp} version dependancies",
            switch=f"-{switch}_dependency '{keys}<str>'",
            example=[
                f"cli: -{switch}_dependency '{keys}hell0 1.0'",
                f"api: chip.set({api},'dependency','hello', '1.0')"],
            schelp=f"""{shelp} dependencies specified as a key value pair.
            Versions shall follow the semver standard.""")

    scparam(cfg,[*path, 'target'],
            sctype='[str]',
            shorthelp=f"{shelp} qualified targets",
            switch=f"-{switch}_target '{keys}<str>'",
            example=[
                f"cli: -{switch}_target '{keys}asicflow_freepdk45'",
                f"api: chip.set({api},'target','asicflow_freepdk45')"],
            schelp=f"""{shelp} list of qualified compilation targets.""")

    scparam(cfg,[*path, 'license'],
            sctype='[str]',
            shorthelp=f"{shelp} license identifiers",
            switch=f"-{switch}_license '{keys}<str>'",
            example=[
                f"cli: -{switch}_license '{keys}Apache-2.0'",
                f"api: chip.set({api},'license','Apache-2.0')"],
            schelp=f"""{shelp} list of SPDX license identifiers.""")

    scparam(cfg,[*path, 'licensefile'],
            sctype='[file]',
            shorthelp=f"{shelp} license files",
            switch=f"-{switch}_licensefile '{keys}<file>'",
            example=[
                f"cli: -{switch}_licensefile '{keys}./LICENSE'",
                f"api: chip.set({api},'licensefile','./LICENSE')"],
            schelp=f"""{shelp} list of license files for {group} to be
            applied in cases when a SPDX identifier is not available.
            (eg. proprietary licenses).list of SPDX license identifiers.""")

    scparam(cfg,[*path, 'location'],
            sctype='[str]',
            shorthelp=f"{shelp} location",
            switch=f"-{switch}_location '{keys}<file>'",
            example=[
                f"cli: -{switch}_location '{keys}mars'",
                f"api: chip.set({api},'location','mars')"],
            schelp=f"""{shelp} country of origin specified as standardized
            international country codes. The field can be left blank
            if the location is unknown or global.""")

    scparam(cfg,[*path, 'organization'],
            sctype='[str]',
            shorthelp=f"{shelp} sponsoring organization",
            switch=f"-{switch}_organzation '{keys}<str>'",
            example=[
                f"cli: -{switch}_organization '{keys}humanity'",
                f"api: chip.set({api},'organization','humanity')"],
            schelp=f"""{shelp} sponsoring organization. The field can be left
            blank if not applicable.""")

    scparam(cfg,[*path, 'publickey'],
            sctype='str',
            shorthelp=f"{shelp} public key",
            switch=f"-{switch}_publickey '{keys}<str>'",
            example=[
                f"cli: -{switch}_publickey '{keys}6EB695706EB69570'",
                f"api: chip.set({api},'publickey','6EB695706EB69570')"],
            schelp=f"""{shelp} public project key.""")

    record = ['name',
              'email',
              'username',
              'location',
              'organization',
              'publickey']

    userid = 'default'
    for item in record:
        scparam(cfg,[*path, 'author', userid, item],
                sctype='str',
                shorthelp=f"{shelp} author {item}",
                switch=f"-{switch}_author_{item} '{keys} userid <str>'",
                example=[
                    f"cli: -{switch}_author_{item} '{keys}wiley wiley@acme.com'",
                    f"api: chip.set({api},'author','wiley','{item}','wiley@acme.com')"],
                schelp=f"""{shelp} author {item} provided with full name as key and
                {item} as value.""")

    return cfg

############################################
# Design Checklist
############################################

def schema_checklist(cfg, group='checklist'):

    if group == 'library':
        emit_group = "library_checklist"
        emit_switch = "lib "
        emit_api = "'library','default','checklist'"
        emit_help = "Library checklist"
    else:
        emit_group = "checklist"
        emit_switch = ""
        emit_api = "'checklist'"
        emit_help = "Checklist"

    path = emit_api.replace("\'","").split(',')

    item = 'default'
    standard = 'default'
    metric = 'default'

    scparam(cfg,[*path, standard, item, 'description'],
            sctype='str',
            shorthelp=f"{emit_help} item description",
            switch=f"-{emit_group}_description '{emit_switch}standard item <str>",
            example=[
                f"cli: -{emit_group}_description '{emit_switch}ISO D000 A-DESCRIPTION'",
                f"api: chip.set({emit_api},'ISO','D000','description','A-DESCRIPTION')"],
            schelp=f"""
            A short one line description of the {group} checklist item.""")

    scparam(cfg,[*path, standard, item, 'requirement'],
            sctype='str',
            shorthelp=f"{emit_help} item requirement",
            switch=f"-{emit_group}_requirement '{emit_switch}standard item <str>",
            example=[
                f"cli: -{emit_group}_requirement '{emit_switch}ISO D000 DOCSTRING'",
                f"api: chip.set({emit_api},'ISO','D000','requirement','DOCSTRING')"],
            schelp=f"""
            A complete requirement description of the {group} checklist item
            entered as a multi-line string.""")

    scparam(cfg,[*path, standard, item, 'dataformat'],
            sctype='str',
            shorthelp=f"{emit_help} item data format",
            switch=f"-{emit_group}_dataformat '{emit_switch}standard item <float>'",
            example=[
                f"cli: -{emit_group}_dataformat 'README'",
                f"api: chip.set({emit_api},'ISO','D000','dataformat','README')"],
            schelp=f"""
            Free text description of the type of data files acceptable as
            checklist signoff validation.""")

    scparam(cfg,[*path, standard, item, 'rationale'],
            sctype='[str]',
            shorthelp=f"{emit_help} item rational",
            switch=f"-{emit_group}_rationale '{emit_switch}standard item <str>",
            example=[
                f"cli: -{emit_group}_rational '{emit_switch}ISO D000 reliability'",
                f"api: chip.set({emit_api},'ISO','D000','rationale','reliability')"],
            schelp=f"""
            Rationale for the the {group} checklist item. Rationale should be a
            unique alphanumeric code used by the standard or a short one line
            or single word description.""")

    scparam(cfg,[*path, standard, item, 'criteria'],
            sctype='[str]',
            shorthelp=f"{emit_help} item criteria",
            switch=f"-{emit_group}_criteria '{emit_switch}standard item <float>'",
            example=[
                f"cli: -{emit_group}_criteria '{emit_switch}ISO D000 errors==0'",
                f"api: chip.set({emit_api},'ISO','D000','criteria','errors==0')"],
            schelp=f"""
            Simple list of signoff criteria for {group} checklist item which
            must all be met for signoff. Each signoff criteria consists of
            a metric, a relational operator, and a value in the form.
            'metric op value'.""")

    scparam(cfg,[*path, standard, item, 'step'],
            sctype='str',
            shorthelp=f"{emit_help} item step",
            switch=f"-{emit_group}_step '{emit_switch}standard item <str>'",
            example=[
                f"cli: -{emit_group}_step '{emit_switch}ISO D000 place'",
                f"api: chip.set({emit_api},'ISO','D000','step','place')"],
            schelp=f"""
            Flowgraph step used to verify the {group} checklist item.
            The parameter should be left empty for manual and for tool
            flows that bypass the SC infrastructure.""")

    scparam(cfg,[*path, standard, item, 'index'],
            sctype='str',
            defvalue='0',
            shorthelp=f"{emit_help} item index",
            switch=f"-{emit_group}_index '{emit_switch}standard item <str>'",
            example=[
                f"cli: -{emit_group}_index '{emit_switch}ISO D000 1'",
                f"api: chip.set({emit_api},'ISO','D000','index','1')"],
            schelp=f"""
            Flowgraph index used to verify the {group} checklist item.
            The parameter should be left empty for manual checks and
            for tool flows that bypass the SC infrastructure.""")

    scparam(cfg,[*path, standard, item, 'report', metric],
            sctype='[file]',
            shorthelp=f"{emit_help} item metric report",
            switch=f"-{emit_group}_report '{emit_switch}standard item metric <file>'",
            example=[
                f"cli: -{emit_group}_report '{emit_switch}ISO D000 bold my.rpt'",
                f"api: chip.set({emit_api},'ISO','D000','report','hold', 'my.rpt')"],
            schelp=f"""
            Filepath to report(s) of specified type documenting the successful
            validation of the {group} checklist item. Specified on a per
            metric basis.""")

    scparam(cfg,[*path, standard, item, 'waiver', metric],
            sctype='[file]',
            shorthelp=f"{emit_help} item metric waivers",
            switch=f"-{emit_group}_waiver '{emit_switch}standard item metric <file>'",
            example=[
                f"cli: -{emit_group}_waiver '{emit_switch}ISO D000 bold my.txt'",
                f"api: chip.set({emit_api},'ISO','D000','waiver','hold', 'my.txt')"],
            schelp=f"""
            Filepath to report(s) documenting waivers for the {group} checklist
            item specified on a per metric basis.""")

    scparam(cfg,[*path, standard, item, 'ok'],
            sctype='bool',
            shorthelp=f"{emit_help} item ok",
            switch=f"-{emit_group}_ok '{emit_switch}standard item <str>'",
            example=[
                f"cli: -{emit_group}_ok '{emit_switch}ISO D000 true'",
                f"api: chip.set({emit_api},'ISO','D000','ok', True)"],
            schelp=f"""
            Boolean check mark for the {group} checklist item. A value of
            True indicates a human has inspected the all item dictionary
            parameters check out.""")

    return cfg

############################################
# Design Setup
############################################

def schema_design(cfg):
    ''' Design Sources
    '''
    name = 'default'

    scparam(cfg,['design'],
            sctype='str',
            require='all',
            shorthelp="Design top module name",
            switch="-design <str>",
            example=["cli: -design hello_world",
                    "api: chip.set('design', 'hello_world')"],
            schelp="""Name of the top level module to compile.
            Required for all designs with more than one module.""")

    scparam(cfg,['source'],
            sctype='[file]',
            copy='true',
            shorthelp="Design source files",
            example=["cli: hello_world.v",
                     "api: chip.set('source', 'hello_world.v')"],
            schelp="""
            A list of source files to read in for elaboration. The files are read
            in order from first to last entered. File type is inferred from the
            file suffix.
            (\\*.v, \\*.vh) = Verilog
            (\\*.vhd)       = VHDL
            (\\*.sv)        = SystemVerilog
            (\\*.c)         = C
            (\\*.cpp, .cc)  = C++
            (\\*.py)        = Python""")

    scparam(cfg,['param', name],
            sctype='str',
            shorthelp="Design parameter",
            switch="-param 'name <str>'",
            example=["cli: -param 'N 64'",
                    "api: chip.set('param','N', '64')"],
            schelp="""
            Sets a top level module parameter. The value
            is limited to basic data literals. The parameter override is
            passed into tools such as Verilator and Yosys. The parameters
            support Verilog integer literals (64'h4, 2'b0, 4) and strings.
            Name of the top level module to compile.""")

    scparam(cfg,['define'],
            sctype='[str]',
            shorthelp="Design pre-processor symbol",
            switch="-D<str>",
            example=["cli: -DCFG_ASIC=1",
                     "api: chip.set('define','CFG_ASIC=1')"],
            schelp="""Symbol definition for source preprocessor.""")

    scparam(cfg,['idir'],
            sctype='[dir]',
            shorthelp="Design search paths",
            switch=['+incdir+<dir>', '-I <dir>'],
            example=["cli: '+incdir+./mylib'",
                    "api: chip.set('idir','./mylib')"],
            schelp="""
            Search paths to look for files included in the design using
            the ```include`` statement.""")

    scparam(cfg,['ydir'],
            sctype='[dir]',
            shorthelp="Design module search paths",
            switch='-y <dir>',
            example=["cli: -y './mylib'",
                    "api: chip.set('ydir','./mylib')"],
            schelp="""
            Search paths to look for verilog modules found in the the
            source list. The import engine will look for modules inside
            files with the specified +libext+ param suffix.""")

    scparam(cfg,['vlib'],
            sctype='[file]',
            shorthelp="Design libraries",
            switch='-v <file>',
            example=["cli: -v './mylib.v'",
                     "api: chip.set('vlib','./mylib.v')"],
            schelp="""
            List of library files to be read in. Modules found in the
            libraries are not interpreted as root modules.""")

    scparam(cfg,['libext'],
            sctype='[str]',
            shorthelp="Design file extensions",
            switch="+libext+<str>",
            example=["cli: +libext+sv",
                    "api: chip.set('libext','sv')"],
            schelp="""
            List of file extensions that should be used for finding modules.
            For example, if -y is specified as ./lib", and '.v' is specified as
            libext then the files ./lib/\\*.v ", will be searched for
            module matches.""")

    scparam(cfg,['cmdfile'],
            sctype='[file]',
            shorthelp="Design compilation command file",
            switch='-f <file>',
            example=["cli: -f design.f",
                     "api: chip.set('cmdfile','design.f')"],
            schelp="""
            Read the specified file, and act as if all text inside it was specified
            as command line parameters. Supported by most verilog simulators
            including Icarus and Verilator. The format of the file is not strongly
            standardized. Support for comments and environment variables within
            the file varies and depends on the tool used. SC simply passes on
            the filepath toe the tool executable.""")

    scparam(cfg,['constraint'],
            sctype='[file]',
            copy='true',
            shorthelp="Design constraints files",
            switch="-constraint <file>",
            example=["cli: -constraint top.sdc",
                    "api: chip.set('constraint','top.sdc')"],
            schelp="""
            List of global constraints for the design to use during compilation.
            Types of constraints include timing (SDC) and pin mappings files (PCF)
            for FPGAs. More than one file can be supplied. Timing constraints are
            global and sourced in all MCMM scenarios.""")

    scparam(cfg,['testbench'],
            sctype='[file]',
            copy='true',
            shorthelp="Testbench files",
            switch="-testbench <file>",
            example=["cli: -testbench tb_top.v",
                    "api: chip.set('testbench', 'tb_top.v')"],
            schelp="""
            A list of testbench sources. The files are read in order from first to
            last entered. File type is inferred from the file suffix:
            (\\*.v, \\*.vh) = Verilog
            (\\*.vhd)      = VHDL
            (\\*.sv)       = SystemVerilog
            (\\*.c)        = C
            (\\*.cpp, .cc) = C++
            (\\*.py)       = Python""")

    scparam(cfg,['testmodule'],
            sctype='str',
            shorthelp="Testbench top module",
            switch="-testmodule <str>",
            example=["cli: -testmodule top",
                    "api: chip.set('testmodule', 'top')"],
            schelp="""Name of the top level test module.""")

    scparam(cfg,['waveform'],
            sctype='[file]',
            shorthelp="Testbench golden waveforms",
            switch="-waveform <file>",
            example=["cli: -waveform mytrace.vcd",
                    "api: chip.set('waveform','mytrace.vcd')"],

            schelp="""
            Waveform(s) used as a golden test vectors to ensure that compilation
            transformations do not modify the functional behavior of the source
            code. The waveform file must be compatible with the testbench and
            compilation flow tools.""")

    #TODO: move this to datasheet
    scparam(cfg,['clock', name, 'pin'],
            sctype='str',
            shorthelp="Clock driver pin",
            switch="-clock_pin 'clkname <str>'",
            example=["cli: -clock_pin 'clk top.pll.clkout'",
                    "api: chip.set('clock', 'clk','pin','top.pll.clkout')"],
            schelp="""
            Defines a clock name alias to assign to a clock source.""")

    #TODO: use ns, seconds, or specify in units?
    scparam(cfg,['clock', name, 'period'],
            sctype='float',
            shorthelp="Clock period",
            switch="-clock_period 'clkname <float>",
            example=["cli: -clock_period 'clk 10'",
                    "api: chip.set('clock','clk','period','10')"],
            schelp="""
            Specifies the period for a clock source in nanoseconds.""")

    scparam(cfg,['clock', name, 'jitter'],
            sctype='float',
            shorthelp="Clock jitter",
            switch="-clock_jitter 'clkname <float>",
            example=["cli: -clock_jitter 'clk 0.01'",
                    "api: chip.set('clock','clk','jitter','0.01')"],
            schelp="""
            Specifies the jitter for a clock source in nanoseconds.""")

    scparam(cfg,['supply', name, 'pin'],
            sctype='str',
            shorthelp="Supply pin mapping",
            switch="-supply_pin 'supplyname <str>'",
            example=["cli: -supply_pin 'vdd vdd_0'",
                    "api: chip.set('supply','vdd','pin','vdd_0')"],
            schelp="""
            Defines a supply name alias to assign to a power source.
            A power supply source can be a list of block pins or a regulator
            output pin.""")

    # move to datasheet
    scparam(cfg,['supply', name, 'level'],
            sctype='float',
            shorthelp="Supply level",
            switch="-supply_level 'supplyname <float>'",
            example=["cli: -supply_level 'vdd 1.0'",
                    "api: chip.set('supply','vdd','level','1.0')"],
            schelp="""
            Voltage level for the name supply, specified in Volts.
            """)

    scparam(cfg,['supply', name, 'noise'],
            sctype='float',
            shorthelp="Supply noise",
            switch="-supply_noise 'supplyname <float>'",
            example=["cli: -supply_noise 'vdd 1.0'",
                    "api: chip.set('supply','vdd','noise','1.0')"],
            schelp="""
            Voltage noise for the name supply, specified in Volts.
            """)

    return cfg

###########################
# Reading Files
###########################

def schema_read(cfg, step='default', index='default'):

    formats = ['spef',
               'sdf',
               'vcd',
               'saif',
               'gds',
               'def',
               'gerber',
               'netlist',
               'sdc',
               'pcf']

    for item in formats:
        scparam(cfg,['read', item, step, index],
                sctype='[file]',
                scope='job',
                copy='true',
                shorthelp=f"Read {item.upper()} file",
                switch=f"-read_{item} 'step index <file>'",
                example=[f"cli: -read_{item} 'sta 0 mydesign.{item}'",
                         f"api: chip.set('read','{item}','sta','0','mydesign.{item}')"],
                schelp=f"""
                Reads files(s) formatted in {item.upper()} specified on a per step
                and index basis.""")

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
            require='asic',
            shorthelp="ASIC metal stackup",
            switch="-asic_stackup <str>",
            example=["cli: -asic_stackup 2MA4MB2MC",
                     "api: chip.set('asic','stackup','2MA4MB2MC')"],
            schelp="""
            Target stackup to use in the design. The stackup is required
            parameter for PDKs with multiple metal stackups.""")

    scparam(cfg, ['asic', 'logiclib'],
            sctype='[str]',
            scope='job',
            shorthelp="ASIC logic libraries",
            switch="-asic_logiclib <str>",
            example=["cli: -asic_logiclib nangate45",
                     "api: chip.set('asic', 'logiclib','nangate45')"],
            schelp="""List of all selected logic libraries libraries
            to use for optimization for a given library architecture
            (9T, 11T, etc).""")

    scparam(cfg, ['asic', 'macrolib'],
            sctype='[str]',
            scope='job',
            shorthelp="ASIC macro libraries",
            switch="-asic_macrolib <str>",
            example=["cli: -asic_macrolib sram64x1024",
                     "api: chip.set('asic', 'macrolib','sram64x1024')"],
            schelp="""
            List of macro libraries to be linked in during synthesis and place
            and route. Macro libraries are used for resolving instances but are
            not used as targets for logic synthesis.""")

    scparam(cfg, ['asic', 'optlib', step, index],
            sctype='[str]',
            scope='job',
            shorthelp="ASIC optimization libraries",
            switch="-asic_optlib 'step index <str>'",
            example=["cli: -asic_optlib 'place 0 asap7_lvt'",
                     "api: chip.set('asic','optlib','place','0','asap7_lvt')"],
            schelp="""
            List of logical libraries used during synthesis and place and route
            specified on a per step and per index basis.""")

    scparam(cfg, ['asic', 'delaymodel'],
            sctype='str',
            scope='job',
            shorthelp="ASIC delay model",
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
            shorthelp="ASIC non-default routing rule",
            switch="-asic_ndr 'netname <(float,float)>",
            example= ["cli: -asic_ndr_width 'clk (0.2,0.2)",
                    "api: chip.set('asic','ndr','clk', (0.2,0.2))"],
            schelp="""
            Definitions of non-default routing rule specified on a per
            net basis. Constraints are entered as a (width,space) tuples
            specified in microns.""")

    scparam(cfg, ['asic', 'minlayer'],
            sctype='str',
            scope='job',
            shorthelp="ASIC minimum routing layer",
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
            shorthelp="ASIC maximum routing layer",
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
            shorthelp="ASIC maximum fanout",
            switch="-asic_maxfanout <int>",
            example= ["cli: -asic_maxfanout 64",
                    "api: chip.set('asic', 'maxfanout', '64')"],
            schelp="""
             Maximum driver fanout allowed during automated place and route.
            The parameter directs the APR tool to break up any net with fanout
            larger than maxfanout into sub nets and buffer.""")

    scparam(cfg, ['asic', 'maxlength'],
            sctype='float',
            scope='job',
            shorthelp="ASIC maximum wire length",
            switch="-asic_maxlength <float>",
            example= ["cli: -asic_maxlength 1000",
                    "api: chip.set('asic', 'maxlength', '1000')"],
            schelp="""
            Maximum total wire length allowed in design during APR. Any
            net that is longer than maxlength is broken up into segments by
            the tool.""")

    scparam(cfg, ['asic', 'maxcap'],
            sctype='float',
            scope='job',
            shorthelp="ASIC maximum net capacitance",
            switch="-asic_maxcap <float>",
            example= ["cli: -asic_maxcap '0.25e-12'",
                      "api: chip.set('asic', 'maxcap', '0.25e-12')"],
            schelp="""Maximum allowed capacitance per net. The number is
            specified in Farads.""")

    scparam(cfg, ['asic', 'maxslew'],
            sctype='float',
            scope='job',
            shorthelp="ASIC maximum slew",
            switch="-asic_maxslew <float>",
            example= ["cli: -asic_maxslew '0.25e-9'",
                    "api: chip.set('asic', 'maxslew', '0.25e-9')"],
            schelp="""Maximum allowed transition time per net. The number
            is specified in seconds.""")

    sigtype='default'
    scparam(cfg, ['asic', 'rclayer', sigtype],
            sctype='str',
            scope='job',
            shorthelp="ASIC parasitics layer",
            switch="-asic_rclayer 'sigtype <str>'",
            example= ["cli: -asic_rclayer 'clk m3",
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
            shorthelp="ASIC vertical pin layer",
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
            shorthelp="ASIC vertical pin layer",
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
            shorthelp="ASIC target core density",
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
            scope='job',
            shorthelp="ASIC block core margin",
            switch="-asic_coremargin <float>",
            example= ["cli: -asic_coremargin 1",
                      "api: chip.set('asic', 'coremargin', '1')"],
            schelp="""
            Halo/margin between the die boundary and core placement for
            automated floorplanning when no diearea or floorplan is
            supplied. The value is specified in microns.""")

    scparam(cfg, ['asic', 'aspectratio'],
            sctype='float',
            scope='job',
            shorthelp="ASIC block aspect ratio",
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
            scope='job',
            shorthelp="ASIC die area outline",
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
            scope='job',
            shorthelp="ASIC core area outline",
            switch="-asic_corearea <[(float,float)]>",
            example= ["cli: -asic_corearea '(0,0)'",
                    "api: chip.set('asic', 'corearea', (0,0))"],
            schelp="""
            List of (x,y) points that define the outline of the core area for the
            physical design. Simple rectangle areas can be defined with two points,
            one for the lower left corner and one for the upper right corner. All
            values are specified in microns.""")

    scparam(cfg, ['asic', 'exclude', step, index],
            sctype='[str]',
            scope='job',
            shorthelp="ASIC excluded cells",
            switch="-asic_exclude 'step index <str>>",
            example=["cli: -asic_exclude drc 0 sram_macro",
                    "api: chip.set('asic','exclude','drc','0','sram_macro')"],
            schelp="""
            List of physical cells to exclude during execution. The process
            of exclusion is controlled by the flow step and tool setup. The list
            is commonly used by DRC tools and GDS export tools to direct the tool
            to exclude GDS information during GDS merge/export.""")

    return cfg

############################################
# MCMM Constraints
############################################

def schema_mcmm(cfg, scenario='default'):
    '''Scenario based timing analysis.'''

    scparam(cfg,['mcmm', scenario, 'voltage'],
            sctype='float',
            scope='job',
            shorthelp="Scenario voltage level",
            switch="-mcmm_voltage 'scenario <float>'",
            example=["cli: -mcmm_voltage 'worst 0.9'",
                     "api: chip.set('mcmm', 'worst','voltage', '0.9')"],
            schelp="""Operating voltage applied to the scenario,
            specified in Volts.""")

    scparam(cfg,['mcmm', scenario, 'temperature'],
            sctype='float',
            scope='job',
            shorthelp="Scenario temperature",
            switch="-mcmm_temperature 'scenario <float>'",
            example=["cli: -mcmm_temperature 'worst 125'",
                     "api: chip.set('mcmm', 'worst', 'temperature','125')"],
            schelp="""Chip temperature applied to the scenario specified in
            degrees Celsius.""")

    scparam(cfg,['mcmm', scenario, 'libcorner'],
            sctype='str',
            scope='job',
            shorthelp="Scenario library corner",
            switch="-mcmm_libcorner 'scenario <str>'",
            example=["cli: -mcmm_libcorner 'worst ttt'",
                    "api: chip.set('mcmm', 'worst', 'libcorner', 'ttt')"],
            schelp="""Library corner applied to the scenario to scale
            library timing models based on the libcorner value for models
            that support it. The parameter is ignored for libraries that
            have one hard coded model per libcorner.""")

    scparam(cfg,['mcmm', scenario, 'pexcorner'],
            sctype='str',
            scope='job',
            shorthelp="Scenario pex corner",
            switch="-mcmm_pexcorner 'scenario <str>'",
            example=["cli: -mcmm_pexcorner 'worst max'",
                    "api: chip.set('mcmm', 'worst', 'pexcorner', 'max')"],
            schelp="""Parasitic corner applied to the scenario. The
            'pexcorner' string must match a corner found in the pdk
            pexmodel setup.""")

    scparam(cfg,['mcmm', scenario, 'opcond'],
            sctype='str',
            scope='job',
            shorthelp="Scenario operating condition",
            switch="-mcmm_opcond 'scenario <str>'",
            example=["cli: -mcmm_opcond 'worst typical_1.0'",
                     "api: chip.set('mcmm', 'worst', 'opcond',  'typical_1.0')"],
            schelp="""Operating condition applied to the scenario. The value
            can be used to access specific conditions within the library
            timing models from the 'logiclib' timing models.""")

    scparam(cfg,['mcmm', scenario, 'mode'],
            sctype='str',
            scope='job',
            shorthelp="Scenario operating mode",
            switch="-mcmm_mode 'scenario <str>'",
            example=["cli: -mcmm_mode 'worst test'",
                     "api: chip.set('mcmm',  'worst','mode', 'test')"],
            schelp="""Operating mode for the scenario. Operating mode strings
            can be values such as test, functional, standby.""")

    scparam(cfg,['mcmm', scenario, 'constraint'],
            sctype='[file]',
            scope='job',
            copy='true',
            shorthelp="Scenario constraints files",
            switch="-mcmm_constraint 'scenario <file>'",
            example=["cli: -mcmm_constraint 'worst hello.sdc'",
                     "api: chip.set('mcmm','worst','constraint', 'hello.sdc')"],
            schelp="""List of timing constraint files to use for the scenario. The
            values are combined with any constraints specified by the design
            'constraint' parameter. If no constraints are found, a default
            constraint file is used based on the clock definitions.""")

    scparam(cfg,['mcmm', scenario, 'check'],
            sctype='[str]',
            scope='job',
            shorthelp="Scenario checks",
            switch="-mcmm_check 'scenario <str>'",
            example=["cli: -mcmm_check 'worst check setup'",
                    "api: chip.add('mcmm','worst','check','setup')"],
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
