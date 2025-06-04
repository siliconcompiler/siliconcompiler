# Copyright 2022 Silicon Compiler Authors. All Rights Reserved.

from . import EditableSchema, Parameter, Scope, PerNode
from .utils import trim

SCHEMA_VERSION = '0.51.4'


#############################################################################
# PARAM DEFINITION
#############################################################################
def scparam(cfg,
            keypath,
            sctype=None,
            require=False,
            defvalue=None,
            scope=Scope.JOB,
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
            pernode=PerNode.NEVER):
    cfg.insert(*keypath, Parameter(
        sctype,
        require=require,
        defvalue=defvalue,
        scope=scope,
        copy=copy,
        lock=lock,
        hashalgo=hashalgo,
        notes=notes,
        unit=unit,
        shorthelp=shorthelp,
        switch=switch,
        example=example,
        help=trim(schelp),
        pernode=pernode
    ))


#############################################################################
# CHIP CONFIGURATION
#############################################################################
def schema_cfg(schema):
    '''Method for defining Chip configuration schema
    All the keys defined in this dictionary are reserved words.
    '''

    # SC version number (bump on every non trivial change)
    # Version number following semver standard.
    # Software version syncs with SC releases (from _metadata)

    # Basic schema setup
    cfg = EditableSchema(schema)

    scparam(cfg, ['schemaversion'],
            sctype='str',
            scope=Scope.GLOBAL,
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
            scope=Scope.GLOBAL,
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
                pernode=PerNode.OPTIONAL,
                copy=val[1],
                shorthelp=f"{val[0]} files",
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
    cfg = schema_flowgraph(cfg)

    # Metrics
    cfg = schema_checklist(cfg)
    cfg = schema_metric(cfg)
    cfg = schema_record(cfg)

    # Datasheet
    cfg = schema_datasheet(cfg)

    # Packaging
    cfg = schema_package(cfg)

    # Packaging
    cfg = schema_schematic(cfg)


###############################################################################
# SCHEMATIC
###############################################################################
def schema_schematic(cfg):
    ''' Schematic
    '''
    name = 'default'
    scparam(cfg, ['schematic', 'component', name, 'partname'],
            sctype='str',
            shorthelp="Schematic: component model",
            switch="-schematic_component_partname 'name <str>'",
            example=["cli: -schematic_component_partname 'B0 NAND2X1'",
                     "api: chip.set('schematic', 'component', 'B0, 'partname', 'NAND2X1')"],
            schelp="""Component part-name ("aka cell-name") specified on a per instance basis.""")

    scparam(cfg, ['schematic', 'pin', name, 'dir'],
            sctype='<input,output,inout>',
            shorthelp="Schematic: pin direction",
            switch="-schematic_pin_dir 'name <str>'",
            example=["cli: -schematic_pin_dir 'A input'",
                     "api: chip.set('schematic', 'pin', 'A', 'dir', 'input')"],
            schelp="""Direction of pin specified on a per pin basis.""")

    scparam(cfg, ['schematic', 'net', name, 'connect'],
            sctype='[str]',
            shorthelp="Schematic: net connection",
            switch="-schematic_net_connect 'name <str>'",
            example=["cli: -schematic_net_connect 'net0 I42.Z'",
                     "api: chip.set('schematic', 'net', 'net0', 'connect', 'I42.Z')"],
            schelp="""Component and pin connectivity specified as a list
            of connection points on a per net basis. The connection point
            point format is "INSTANCE.PIN", where "." is the hierarchy
            character. Connections without ".PIN" implies the connection is
            a primary design I/O pin. Specifying "INSTANCE.*" implies that
            all pins of INSTANCE get connected to the net.""")

    scparam(cfg, ['schematic', 'hierchar'],
            sctype='str',
            defvalue='.',
            shorthelp="Schematic: hierarchy character",
            switch="-schematic_hierchar <str>",
            example=["cli: -schematic_hierchar '/'",
                     "api: chip.set('schematic', 'hierchar', '/')"],
            schelp="""Specifies the character used to express hierarchy. If
            the hierarchy character is used as part of a name, it must be
            escaped with a backslash('\').""")

    scparam(cfg, ['schematic', 'buschar'],
            sctype='str',
            defvalue='[]',
            shorthelp="Schematic: bus character",
            switch="-schematic_buschar <str>",
            example=["cli: -schematic_buschar '[]'",
                     "api: chip.set('schematic', 'buschar', '[]')"],
            schelp="""Specifies the character used to express bus bits. If the
            bus character is used as part of a name, it must be
            escaped with a backslash('\').""")

    return cfg


###############################################################################
# FPGA
###############################################################################
def schema_fpga(cfg):
    from siliconcompiler.fpga import FPGASchema
    cfg.insert("fpga", FPGASchema())
    return cfg


###############################################################################
# PDK
###############################################################################
def schema_pdk(cfg):
    from siliconcompiler.pdk import PDKSchema
    cfg.insert("pdk", "default", PDKSchema())
    return cfg


###############################################################################
# Datasheet ("specification/contract")
###############################################################################
def schema_datasheet(cfg):

    partname = 'default'
    mode = 'default'

    ds_type = ['digital', 'analog', 'ams', 'passive',
               'soc', 'fpga',
               'adc', 'dac',
               'pmic', 'buck', 'boost', 'ldo',
               'sram', 'dram', 'flash', 'rom',
               'interface', 'clock', 'amplifier',
               'filter', 'mixer', 'modulator', 'lna']
    # Part type
    scparam(cfg, ['datasheet', 'type'],
            sctype=f'<{",".join(ds_type)}>',
            shorthelp="Datasheet: type",
            switch="-datasheet_type '<str>'",
            example=[
                "cli: -datasheet_type 'digital'",
                "api: chip.set('datasheet', 'type', 'digital')"],
            schelp="""Device type.""")

    # Documentation
    scparam(cfg, ['datasheet', 'doc'],
            sctype='[file]',
            shorthelp="Datasheet: documentation",
            switch="-datasheet_doc '<file>'",
            example=[
                "cli: -datasheet_doc 'za001.pdf'",
                "api: chip.set('datasheet', 'doc', 'za001.pdf)"],
            schelp="""Datasheet document.""")

    # Series
    scparam(cfg, ['datasheet', 'series'],
            sctype='str',
            shorthelp="Datasheet: series",
            switch="-datasheet_series '<str>'",
            example=[
                "cli: -datasheet_series 'ZA0'",
                "api: chip.set('datasheet', 'series', 'ZA0)"],
            schelp="""Device series describing a family of devices or
            a singular device with multiple packages and/or qualification
            `SKUs <https://en.wikipedia.org/wiki/Stock_keeping_unit>`_.""")

    # Manufacturer
    scparam(cfg, ['datasheet', 'manufacturer'],
            sctype='str',
            shorthelp="Datasheet: manufacturer",
            switch="-datasheet_manufacturer '<str>'",
            example=[
                "cli: -datasheet_manufacturer 'Acme'",
                "api: chip.set('datasheet', 'manufacturer', 'Acme')"],
            schelp="""Device manufacturer.""")

    # Device description
    scparam(cfg, ['datasheet', 'description'],
            sctype='str',
            shorthelp="Datasheet: description",
            switch="-datasheet_description '<str>'",
            example=[
                "cli: -datasheet_description 'Yet another CPU'",
                "api: chip.set('datasheet', 'description', 'Yet another CPU')"],
            schelp="""Device description entered as free text.""")

    # Features
    scparam(cfg, ['datasheet', 'features'],
            sctype='[str]',
            shorthelp="Datasheet: features",
            switch="-datasheet_features '<str>'",
            example=[
                "cli: -datasheet_features 'usb3.0'",
                "api: chip.set('datasheet', 'features', 'usb3.0')"],
            schelp="""Device features.""")

    # Grade
    scparam(cfg, ['datasheet', 'grade'],
            sctype='<consumer,industrial,menidal,automotive,military,space>',
            shorthelp="Datasheet: manufacturing grade",
            switch="-datasheet_grade '<str>'",
            example=[
                "cli: -datasheet_grade 'automotive'",
                "api: chip.set('datasheet', 'grade', 'automotive')"],
            schelp="""Device end application qualification grade.""")

    # Qualification
    scparam(cfg, ['datasheet', 'qual'],
            sctype='[str]',
            shorthelp="Datasheet: qualification level",
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
            sctype='<preview,active,deprecated,last time buy,obsolete>',
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
            shorthelp="Datasheet: maximum frequency",
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

    io_arch = ['spi', 'uart', 'i2c', 'pwm', 'qspi', 'sdio', 'can', 'jtag',
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
               'jesd204', 'cpri']
    scparam(cfg, ['datasheet', 'io', partname, 'arch'],
            sctype=f'<{",".join(io_arch)}>',
            shorthelp="Datasheet: io standard",
            switch="-datasheet_io_arch 'partname <str>'",
            example=[
                "cli: -datasheet_io_arch 'pio spi'",
                "api: chip.set('datasheet', 'io', 'pio', 'arch', 'spi')"],
            schelp="""Datasheet: List of IO standard architectures supported
            by the named IO port.""")

    metrics = {'fmax': ['maximum frequency', 100, 'float', 'MHz'],
               'width': ['width', 4, 'int', None],
               'channels': ['channels', 4, 'int', None]
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'io', partname, i],
                unit=v[3],
                sctype=v[2],
                shorthelp=f"Datasheet: io {v[0]}",
                switch=f"-datasheet_io_{i} 'partname <{v[2]}>'",
                example=[
                    f"cli: -datasheet_io_{i} 'partname {v[1]}'",
                    f"api: chip.set('datasheet', 'io', partname, '{i}', {v[1]})"],
                schelp=f"""Datasheet: IO {v[1]} metrics specified on a per IO port basis.
                """)

    ######################
    # Processor
    ######################

    scparam(cfg, ['datasheet', 'proc', partname, 'arch'],
            sctype='str',
            shorthelp="Datasheet: processor architecture",
            switch="-datasheet_proc_arch 'partname <str>'",
            example=[
                "cli: -datasheet_proc_arch '0 RV64GC'",
                "api: chip.set('datasheet', 'proc', partname, 'arch', 'openfpga')"],
            schelp="""Processor architecture specified on a per core basis.""")

    scparam(cfg, ['datasheet', 'proc', partname, 'features'],
            sctype='[str]',
            shorthelp="Datasheet: processor features",
            switch="-datasheet_proc_features 'partname <str>'",
            example=[
                "cli: -datasheet_proc_features '0 SIMD'",
                "api: chip.set('datasheet','proc','cpu','features', 'SIMD')"],
            schelp="""List of maker specified processor features specified on a per core basis.""")

    proc_datatypes = ['int4', 'int8', 'int16', 'int32', 'int64', 'int128',
                      'uint4', 'uint8', 'uint16', 'uint32', 'uint64', 'uint128',
                      'bfloat16', 'fp16', 'fp32', 'fp64', 'fp128']
    scparam(cfg, ['datasheet', 'proc', partname, 'datatypes'],
            sctype=f'[<{",".join(proc_datatypes)}>]',
            shorthelp="Datasheet: processor datatypes",
            switch="-datasheet_proc_datatypes 'partname <str>'",
            example=[
                "cli: -datasheet_proc_datatypes '0 int8'",
                "api: chip.set('datasheet', 'proc', 'cpu', 'datatypes', 'int8')"],
            schelp="""List of datatypes supported by the processor specified
            on a per core basis.""")

    metrics = {'archsize': ['architecture size', 64, None],
               'cores': ['number of cores', 4, None],
               'fmax': ['maximum frequency', 100, 'MHz'],
               'ops': ['operations per cycle', 4, None],
               'mults': ['hard multiplier units', 100, None],
               'icache': ['l1 icache size', 32, 'KB'],
               'dcache': ['l1 dcache size', 32, 'KB'],
               'l2cache': ['l2 cache size', 1024, 'KB'],
               'l3cache': ['l3 cache size', 1024, 'KB'],
               'sram': ['local sram', 128, 'KB'],
               'nvm': ['local non-volatile memory', 128, 'KB']}

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'proc', partname, i],
                unit=v[2],
                sctype='int',
                shorthelp=f"Datasheet: processor {v[0]}",
                switch=f"-datasheet_proc_{i} 'partname <int>'",
                example=[
                    f"cli: -datasheet_proc_{i} 'cpu {v[1]}'",
                    f"api: chip.set('datasheet', 'proc', 'cpu', '{i}', {v[1]})"],
                schelp=f"""Processor metric: {v[0]} specified on a per core basis.""")

    ######################
    # Memory
    ######################

    scparam(cfg, ['datasheet', 'memory', partname, 'bits'],
            sctype='int',
            shorthelp="Datasheet: memory total bits",
            switch="-datasheet_memory_bits 'partname <int>'",
            example=[
                "cli: -datasheet_memory_bits 'm0 1024'",
                "api: chip.set('datasheet', 'memory', 'm0', 'bits', 1024)"],
            schelp="""Memory total number of bits specified on a per memory basis.""")

    scparam(cfg, ['datasheet', 'memory', partname, 'width'],
            sctype='int',
            shorthelp="Datasheet: memory width",
            switch="-datasheet_memory_width 'partname <int>'",
            example=[
                "cli: -datasheet_memory_width 'm0 16'",
                "api: chip.set('datasheet', 'memory', 'm0', 'width', 16)"],
            schelp="""Memory width specified on a per memory basis.""")

    scparam(cfg, ['datasheet', 'memory', partname, 'depth'],
            sctype='int',
            shorthelp="Datasheet: memory depth",
            switch="-datasheet_memory_depth 'partname <int>'",
            example=[
                "cli: -datasheet_memory_depth 'm0 128'",
                "api: chip.set('datasheet', 'memory', 'm0', 'depth', 128)"],
            schelp="""Memory depth specified on a per memory basis.""")

    scparam(cfg, ['datasheet', 'memory', partname, 'banks'],
            sctype='int',
            shorthelp="Datasheet: memory banks",
            switch="-datasheet_memory_banks 'partname <int>'",
            example=[
                "cli: -datasheet_memory_banks 'm0 4'",
                "api: chip.set('datasheet', 'memory', 'm0', 'banks', 4)"],
            schelp="""Memory banks specified on a per memory basis.""")

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
        scparam(cfg, ['datasheet', 'memory', partname, i],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: memory {v[0]}",
                switch=f"-datasheet_memory_{i} 'partname <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_memory_{i} "
                    f"'partname ({','.join([str(val) for val in v[1]])})'",
                    f"api: chip.set('datasheet', 'memory', partname, '{i}', {v[1]})"],
                schelp=f"""Memory {v[1]} specified on a per memory basis.""")

    # Latency (cycles)
    metrics = {'tcl': ['column address latency', (100, 100, 100), 'cycles'],
               'trcd': ['row address latency', (100, 100, 100), 'cycles'],
               'trp': ['row precharge time latency', (100, 100, 100), 'cycles'],
               'tras': ['row active time latency', (100, 100, 100), 'cycles']
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'memory', partname, i],
                unit=v[2],
                sctype='(int,int,int)',
                shorthelp=f"Datasheet: memory {v[0]}",
                switch=f"-datasheet_memory_{i} 'partname <(int,int,int)>'",
                example=[
                    f"cli: -datasheet_memory_{i} "
                    f"'partname ({','.join([str(val) for val in v[1]])})'",
                    f"api: chip.set('datasheet', 'memory', partname, '{i}', {v[1]})"],
                schelp=f"""Memory {v[1]} specified on a per memory basis.""")

    ######################
    # FPGA
    ######################

    scparam(cfg, ['datasheet', 'fpga', partname, 'arch'],
            sctype='str',
            shorthelp="Datasheet: fpga architecture",
            switch="-datasheet_fpga_arch 'partname <str>'",
            example=[
                "cli: -datasheet_fpga_arch 'i0 openfpga'",
                "api: chip.set('datasheet', 'fpga', 'i0', 'arch', 'openfpga')"],
            schelp="""FPGA architecture.
            """)

    metrics = {'luts': ['LUTs', 32000, None],
               'registers': ['registers', 100, None],
               'plls': ['pll blocks', 1, None],
               'mults': ['multiplier/dsp elements', 100, None],
               'totalram': ['total ram', 128, 'Kb'],
               'distram': ['distributed ram', 128, 'Kb'],
               'blockram': ['block ram', 128, 'Kb']}

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'fpga', partname, i],
                unit=v[2],
                sctype='int',
                shorthelp=f"Datasheet: fpga {v[0]}",
                switch=f"-datasheet_fpga_{i} 'partname <int>'",
                example=[
                    f"cli: -datasheet_fpga_{i} 'i0 {v[1]}'",
                    f"api: chip.set('datasheet', 'fpga', 'i0', '{i}', {v[1]})"],
                schelp=f"""FPGA {v[1]}.""")

    ######################
    # Analog
    ######################

    scparam(cfg, ['datasheet', 'analog', partname, 'arch'],
            sctype='str',
            shorthelp="Datasheet: analog architecture",
            switch="-datasheet_analog_arch 'partname <str>'",
            example=[
                "cli: -datasheet_analog_arch 'adc0 pipelined'",
                "api: chip.set('datasheet', 'analog', 'adc0', 'arch', 'pipelined')"],
            schelp="""Analog component architecture.""")

    scparam(cfg, ['datasheet', 'analog', partname, 'features'],
            sctype='[str]',
            shorthelp="Datasheet: analog features",
            switch="-datasheet_analog_features 'partname <str>'",
            example=[
                "cli: -datasheet_analog_features '0 \"differential input\"'",
                "api: chip.set('datasheet','analog','adc0','features', 'differential input')"],
            schelp="""List of maker specified analog features.""")

    metrics = {'resolution': ['architecture resolution', 8],
               'channels': ['parallel channels', 8]}

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'analog', partname, i],
                sctype='int',
                shorthelp=f"Datasheet: analog {v[0]}",
                switch=f"-datasheet_analog_{i} 'partname <int>'",
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
        scparam(cfg, ['datasheet', 'analog', partname, i],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: analog {v[0]}",
                switch=f"-datasheet_analog_{i} 'partname <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_analog_{i} 'i0 ({','.join([str(val) for val in v[1]])})'",
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
                    f"cli: -datasheet_limit_{i} ({','.join([str(val) for val in v[1]])})",
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

    scparam(cfg, ['datasheet', 'package', partname, 'type'],
            sctype='<bga,lga,csp,qfn,qfp,sop,die,wafer>',
            shorthelp="Datasheet: package type",
            switch="-datasheet_package_type 'partname <str>'",
            example=[
                "cli: -datasheet_package_type 'abcd bga'",
                "api: chip.set('datasheet', 'package', 'abcd', 'type', 'bga')"],
            schelp="""Package type.""")

    scparam(cfg, ['datasheet', 'package', partname, 'footprint'],
            sctype='[file]',
            shorthelp="Datasheet: package footprint",
            switch="-datasheet_package_footprint 'partname <file>'",
            example=[
                "cli: -datasheet_package_footprint 'abcd ./soic8.kicad_mod'",
                "api: chip.set('datasheet', 'package', 'abcd', 'footprint', './soic8.kicad_mod')"],
            schelp="""Package footprint file. Supported 3D model file formats include:

            * (KICAD_MOD) KiCad Standard Footprint Format

            """)

    scparam(cfg, ['datasheet', 'package', partname, '3dmodel'],
            sctype='[file]',
            shorthelp="Datasheet: package 3D model",
            switch="-datasheet_package_3dmodel 'partname <file>'",
            example=[
                "cli: -datasheet_package_3dmodel 'abcd ./soic8.step'",
                "api: chip.set('datasheet', 'package', 'abcd', '3dmodel', './soic8.step')"],
            schelp="""Package 3D model file. Supported 3D model file formats include:

            * (STEP) Standard for the Exchange of Product Data Format
            * (STL) Stereolithography Format
            * (WRL) Virtually Reality Modeling Language Format

            """)

    scparam(cfg, ['datasheet', 'package', partname, 'drawing'],
            sctype='[file]',
            shorthelp="Datasheet: package drawing",
            switch="-datasheet_package_drawing 'partname <file>'",
            example=[
                "cli: -datasheet_package_drawing 'abcd p484.pdf'",
                "api: chip.set('datasheet', 'package', 'abcd', 'drawing', 'p484.pdf')"],
            schelp="""Mechanical drawing for documentation purposes.
            Supported file formats include: PDF, DOC, SVG, and PNG.""")

    # key package metrics
    metrics = {'length': ['length', (4000, 4000, 4000), 'um'],
               'width': ['width', (4000, 4000, 4000), 'um'],
               'thickness': ['thickness', (900, 1000, 1100), 'um'],
               'pinpitch': ['pin pitch', (800, 850, 900), 'um']
               }

    for i, v in metrics.items():
        scparam(cfg, ['datasheet', 'package', partname, i],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: package {v[0]}",
                switch=f"-datasheet_package_{i} 'partname <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_package_{i} 'abcd ({','.join([str(val) for val in v[1]])})'",
                    f"api: chip.set('datasheet', 'package', 'abcd', '{i}', {v[1]}"],
                schelp=f"""Package {v[0]}. Values are tuples of
                (min, nominal, max).""")

    # pin
    scparam(cfg, ['datasheet', 'package', partname, 'pincount'],
            sctype='int',
            shorthelp="Datasheet: package pin count",
            switch="-datasheet_package_pincount 'partname <int>'",
            example=[
                "cli: -datasheet_package_pincount 'abcd 484'",
                "api: chip.set('datasheet', 'package', 'abcd', 'pincount', '484')"],
            schelp="""Total number package pins.""")

    number = 'default'
    scparam(cfg, ['datasheet', 'package', partname, 'pin', number, 'signal'],
            sctype='str',
            shorthelp="Datasheet: package pin signal map",
            switch="-datasheet_package_pin_signal 'partname number <str>'",
            example=[
                "cli: -datasheet_package_pin_signal 'abcd B1 clk'",
                "api: chip.set('datasheet', 'package', 'abcd', 'pin', 'B1', 'signal', 'clk')"],
            schelp="""Mapping between the package physical pin name ("1", "2", "A1", "B3", ...)
            and the corresponding device signal name ("VDD", "CLK", "NRST") found in the
            :keypath:`datasheet,pin`.""")

    # anchor
    scparam(cfg, ['datasheet', 'package', partname, 'anchor'],
            sctype='(float,float)',
            defvalue=(0.0, 0.0),
            unit='um',
            shorthelp="Datasheet: package anchor",
            switch="-datasheet_package_anchor 'partname <(float,float)>'",
            example=[
                "cli: -datasheet_package_anchor 'i0 (3.0,3.0)'",
                "api: chip.set('datasheet', 'package', 'i0', 'anchor', (3.0, 3.0))"],
            schelp="""
            Package anchor point with respect to the lower left corner of the package.
            When placing a component on a substrate, the placement location specifies
            the distance from the substrate origin to the anchor point of the placed
            object.""")

    ######################
    # Pin Specifications
    ######################

    # Pin type
    scparam(cfg, ['datasheet', 'pin', partname, 'type', mode],
            sctype='<digital,analog,clock,supply,ground>',
            shorthelp="Datasheet: pin type",
            switch="-datasheet_pin_type 'partname mode <str>'",
            example=[
                "cli: -datasheet_pin_type 'vdd global supply'",
                "api: chip.set('datasheet', 'pin', 'vdd', 'type', 'global', 'supply')"],
            schelp="""Pin type specified on a per mode basis.""")

    # Pin direction
    scparam(cfg, ['datasheet', 'pin', partname, 'dir', mode],
            sctype='<input,output,inout>',
            shorthelp="Datasheet: pin direction",
            switch="-datasheet_pin_dir 'partname mode <str>'",
            example=[
                "cli: -datasheet_pin_dir 'clk global input'",
                "api: chip.set('datasheet', 'pin', 'clk', 'dir', 'global', 'input')"],
            schelp="""Pin direction specified on a per mode basis.""")

    # Pin complement (for differential pair)
    scparam(cfg, ['datasheet', 'pin', partname, 'complement', mode],
            sctype='str',
            shorthelp="Datasheet: pin complement",
            switch="-datasheet_pin_complement 'partname mode <str>'",
            example=[
                "cli: -datasheet_pin_complement 'ina global inb'",
                "api: chip.set('datasheet', 'pin', 'ina', 'complement', 'global', 'inb')"],
            schelp="""Pin complement specified on a per mode basis for differential
            signals.""")

    # Pin standard
    scparam(cfg, ['datasheet', 'pin', partname, 'standard', mode],
            sctype='[str]',
            shorthelp="Datasheet: pin standard",
            switch="-datasheet_pin_standard 'partname mode <str>'",
            example=[
                "cli: -datasheet_pin_standard 'clk def LVCMOS'",
                "api: chip.set('datasheet', 'pin', 'clk', 'standard', 'def', 'LVCMOS')"],
            schelp="""Pin electrical signaling standard (LVDS, LVCMOS, TTL, ...).""")

    # Pin interface map
    scparam(cfg, ['datasheet', 'pin', partname, 'interface', mode],
            sctype='[str]',
            shorthelp="Datasheet: pin interface map",
            switch="-datasheet_pin_interface 'partname mode <str>'",
            example=[
                "cli: -datasheet_pin_interface 'clk0 ddr4 CLKN'",
                "api: chip.set('datasheet', 'pin', 'clk0', 'interface', 'ddr4', 'CLKN')"],
            schelp="""Pin mapping to standardized interface names.""")

    # Pin reset value
    scparam(cfg, ['datasheet', 'pin', partname, 'resetvalue', mode],
            sctype='<weak1,weak0,strong0,strong1,highz>',
            shorthelp="Datasheet: pin reset value",
            switch="-datasheet_pin_resetvalue 'partname mode <str>'",
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
        scparam(cfg, ['datasheet', 'pin', partname, item, mode],
                unit=val[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: pin {val[0]}",
                switch=f"-datasheet_pin_{item} 'pin mode <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_pin_{item} 'sclk global "
                    f"({','.join([str(v) for v in val[1]])})'",
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
        scparam(cfg, ['datasheet', 'pin', partname, i, mode, relpin],
                unit=v[2],
                sctype='(float,float,float)',
                shorthelp=f"Datasheet: pin {v[0]}",
                switch=f"-datasheet_pin_{i} 'pin mode relpin <(float,float,float)>'",
                example=[
                    f"cli: -datasheet_pin_{i} "
                    f"'a glob clock ({','.join([str(val) for val in v[1]])})'",
                    f"api: chip.set('datasheet', 'pin', 'a', '{i}', 'glob', 'ck', {v[1]}"],
                schelp=f"""Pin {v[0]} specified on a per pin, mode, and relpin basis.
                Values are tuples of (min, typical, max).""")

    return cfg


###############################################################################
# Flow Configuration
###############################################################################
def schema_flowgraph(cfg):
    from siliconcompiler.flowgraph import FlowgraphSchema
    cfg.insert("flowgraph", "default", FlowgraphSchema())
    return cfg


###########################################################################
# Tool Setup
###########################################################################
def schema_tool(cfg):
    from siliconcompiler.tool import ToolSchemaTmp
    cfg.insert("tool", "default", ToolSchemaTmp())
    return cfg


###########################################################################
# Function arguments
###########################################################################
def schema_arg(cfg):

    scparam(cfg, ['arg', 'step'],
            sctype='str',
            scope=Scope.SCRATCH,
            shorthelp="ARG: step argument",
            switch="-arg_step <str>",
            example=["cli: -arg_step 'route'",
                     "api: chip.set('arg', 'step', 'route')"],
            schelp="""
            Dynamic parameter passed in by the SC runtime as an argument to
            a runtime task. The parameter enables configuration code
            (usually TCL) to use control flow that depend on the current
            'step'. The parameter is used the :meth:`.run()` function and
            is not intended for external use.""")

    scparam(cfg, ['arg', 'index'],
            sctype='str',
            scope=Scope.SCRATCH,
            shorthelp="ARG: index argument",
            switch="-arg_index <str>",
            example=["cli: -arg_index 0",
                     "api: chip.set('arg', 'index', '0')"],
            schelp="""
            Dynamic parameter passed in by the SC runtime as an argument to
            a runtime task. The parameter enables configuration code
            (usually TCL) to use control flow that depend on the current
            'index'. The parameter is used the :meth:`.run()` function and
            is not intended for external use.""")

    return cfg


###########################################################################
# Metrics to Track
###########################################################################
def schema_metric(cfg):
    from siliconcompiler.metric import MetricSchema
    cfg.insert("metric", MetricSchema())
    return cfg


###########################################################################
# Design Tracking
###########################################################################
def schema_record(cfg):
    from siliconcompiler.record import RecordSchema
    cfg.insert("record", RecordSchema())
    return cfg


###########################################################################
# Run Options
###########################################################################
def schema_option(cfg):
    ''' Technology agnostic run time options
    '''

    scparam(cfg, ['option', 'remote'],
            sctype='bool',
            scope=Scope.JOB,
            shorthelp="Option: enable remote processing",
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
            scope=Scope.JOB,
            shorthelp="Option: user credentials file",
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
            scope=Scope.JOB,
            shorthelp="Option: user cache directory",
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
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: tool scheduling priority",
            switch="-nice <int>",
            example=[
                "cli: -nice 5",
                "api: chip.set('option', 'nice', 5)"],
            schelp="""
            Sets the type of execution priority of each individual flowgraph steps.
            If the parameter is undefined, nice will not be used. For more information see
            `Unix 'nice' <https://en.wikipedia.org/wiki/Nice_(Unix)>`_.""")

    # Compilation
    scparam(cfg, ['option', 'pdk'],
            sctype='str',
            scope=Scope.JOB,
            shorthelp="Option: PDK target",
            switch="-pdk <str>",
            example=["cli: -pdk freepdk45",
                     "api: chip.set('option', 'pdk', 'freepdk45')"],
            schelp="""
            Target PDK used during compilation.""")

    scparam(cfg, ['option', 'stackup'],
            sctype='str',
            scope=Scope.JOB,
            shorthelp="Option: stackup target",
            switch="-stackup <str>",
            example=["cli: -stackup 2MA4MB2MC",
                     "api: chip.set('option', 'stackup', '2MA4MB2MC')"],
            schelp="""
            Target stackup used during compilation. The stackup is required
            parameter for PDKs with multiple metal stackups.""")

    scparam(cfg, ['option', 'flow'],
            sctype='str',
            scope=Scope.JOB,
            shorthelp="Option: flow target",
            switch="-flow <str>",
            example=["cli: -flow asicflow",
                     "api: chip.set('option', 'flow', 'asicflow')"],
            schelp="""
            Sets the flow for the current run. The flow name
            must match up with a 'flow' in the flowgraph""")

    scparam(cfg, ['option', 'optmode'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            defvalue='O0',
            shorthelp="Option: optimization mode",
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
            scope=Scope.JOB,
            shorthelp="Option: configuration manifest",
            switch="-cfg <file>",
            example=["cli: -cfg mypdk.json",
                     "api: chip.set('option', 'cfg', 'mypdk.json')"],
            schelp="""
            List of filepaths to JSON formatted schema configuration
            manifests. The files are read in automatically when using the
            'sc' command line application. In Python programs, JSON manifests
            can be merged into the current working manifest using the
            :meth:`Chip.read_manifest()` method.""")

    key = 'default'
    scparam(cfg, ['option', 'env', key],
            sctype='str',
            scope=Scope.JOB,
            shorthelp="Option: environment variables",
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
            scope=Scope.JOB,
            shorthelp="Option: custom variables",
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
            scope=Scope.JOB,
            copy=True,
            shorthelp="Option: custom files",
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
            scope=Scope.JOB,
            copy=True,
            shorthelp="Option: custom directories",
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
            sctype='<info,warning,error,critical,debug,quiet>',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            defvalue='info',
            shorthelp="Option: logging level",
            switch="-loglevel <str>",
            example=[
                "cli: -loglevel info",
                "api: chip.set('option', 'loglevel', 'info')"],
            schelp="""
            Provides explicit control over the level of debug logging printed.""")

    scparam(cfg, ['option', 'builddir'],
            sctype='dir',
            scope=Scope.JOB,
            defvalue='build',
            shorthelp="Option: build directory",
            switch="-builddir <dir>",
            example=[
                "cli: -builddir ./build_the_future",
                "api: chip.set('option', 'builddir', './build_the_future')"],
            schelp="""
            The default build directory is in the local './build' where SC was
            executed. This can be used to set an alternate
            compilation directory path.""")

    scparam(cfg, ['option', 'jobname'],
            sctype='str',
            scope=Scope.JOB,
            defvalue='job0',
            shorthelp="Option: job name",
            switch="-jobname <str>",
            example=[
                "cli: -jobname may1",
                "api: chip.set('option', 'jobname', 'may1')"],
            schelp="""
            Jobname during invocation of :meth:`.run()`. The jobname combined with a
            defined director structure (<dir>/<design>/<jobname>/<step>/<index>)
            enables multiple levels of transparent job, step, and index
            introspection.""")

    scparam(cfg, ['option', 'from'],
            sctype='[str]',
            scope=Scope.JOB,
            shorthelp="Option: starting step",
            switch="-from <str>",
            example=[
                "cli: -from 'import'",
                "api: chip.set('option', 'from', 'import')"],
            schelp="""
            Inclusive list of steps to start execution from. The default is to start
            at all entry steps in the flow graph.""")

    scparam(cfg, ['option', 'to'],
            sctype='[str]',
            scope=Scope.JOB,
            shorthelp="Option: ending step",
            switch="-to <str>",
            example=[
                "cli: -to 'syn'",
                "api: chip.set('option', 'to', 'syn')"],
            schelp="""
            Inclusive list of steps to end execution with. The default is to go
            to all exit steps in the flow graph.""")

    scparam(cfg, ['option', 'prune'],
            sctype='[(str,str)]',
            scope=Scope.JOB,
            shorthelp="Option: flowgraph pruning",
            switch="-prune 'node <(str,str)>'",
            example=[
                "cli: -prune (syn,0)",
                "api: chip.set('option', 'prune', ('syn', '0'))"],
            schelp="""
            List of starting nodes for branches to be pruned.
            The default is to not prune any nodes/branches.""")

    scparam(cfg, ['option', 'breakpoint'],
            sctype='bool',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: breakpoint list",
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
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: library list",
            switch="-library <str>",
            example=["cli: -library lambdalib_asap7",
                     "api: chip.set('option', 'library', 'lambdalib_asap7')"],
            schelp="""
            List of soft libraries to be linked in during import.""")

    # Booleans
    scparam(cfg, ['option', 'clean'],
            sctype='bool',
            scope=Scope.JOB,
            shorthelp="Option: cleanup previous job",
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
            scope=Scope.JOB,
            shorthelp="Option: file hashing",
            switch="-hash <bool>",
            example=["cli: -hash",
                     "api: chip.set('option', 'hash', True)"],
            schelp="""
            Enables hashing of all inputs and outputs during
            compilation. The hash values are stored in the hashvalue
            field of the individual parameters.""")

    scparam(cfg, ['option', 'nodisplay'],
            sctype='bool',
            scope=Scope.JOB,
            shorthelp="Option: headless execution",
            switch="-nodisplay <bool>",
            example=["cli: -nodisplay",
                     "api: chip.set('option', 'nodisplay', True)"],
            schelp="""
            This flag prevents SiliconCompiler from opening GUI windows such as
            the final metrics report.""")

    scparam(cfg, ['option', 'quiet'],
            sctype='bool',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            shorthelp="Option: quiet execution",
            switch="-quiet <bool>",
            example=["cli: -quiet",
                     "api: chip.set('option', 'quiet', True)"],
            schelp="""
            The -quiet option forces all steps to print to a log file.
            This can be useful with Modern EDA tools which print
            significant content to the screen.""")

    scparam(cfg, ['option', 'jobincr'],
            sctype='bool',
            scope=Scope.JOB,
            shorthelp="Option: autoincrement jobname",
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
            pernode=PerNode.OPTIONAL,
            defvalue=False,
            scope=Scope.JOB,
            shorthelp="Option: disable version checking",
            switch="-novercheck <bool>",
            example=["cli: -novercheck",
                     "api: chip.set('option', 'novercheck', True)"],
            schelp="""
            Disables strict version checking on all invoked tools if True.
            The list of supported version numbers is defined in the
            :keypath:`tool,<tool>,version`.""")

    scparam(cfg, ['option', 'track'],
            sctype='bool',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            shorthelp="Option: enable provenance tracking",
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
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: program entry point",
            switch="-entrypoint <str>",
            example=["cli: -entrypoint top",
                     "api: chip.set('option', 'entrypoint', 'top')"],
            schelp="""Alternative entrypoint for compilation and
            simulation. The default entry point is :keypath:`design`.""")

    scparam(cfg, ['option', 'idir'],
            sctype='[dir]',
            shorthelp="Option: design search paths",
            copy=True,
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
            shorthelp="Option: design module search paths",
            copy=True,
            switch=['-y <dir>',
                    '-ydir <dir>'],
            example=[
                "cli: -y './mylib'",
                "cli: -ydir './mylib'",
                "api: chip.set('option', 'ydir', './mylib')"],
            schelp="""
            Search paths to look for verilog modules found in the the
            source list. The import engine will look for modules inside
            files with the specified :keypath:`option,libext` param suffix.""")

    scparam(cfg, ['option', 'vlib'],
            sctype='[file]',
            shorthelp="Option: design libraries",
            copy=True,
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
            shorthelp="Option: design pre-processor symbol",
            switch=["-D<str>",
                    "-define <str>"],
            example=["cli: -DCFG_ASIC=1",
                     "cli: -define CFG_ASIC=1",
                     "api: chip.set('option', 'define', 'CFG_ASIC=1')"],
            schelp="""Symbol definition for source preprocessor.""")

    scparam(cfg, ['option', 'libext'],
            sctype='[str]',
            shorthelp="Option: design file extensions",
            switch=["+libext+<str>",
                    "-libext <str>"],
            example=[
                "cli: +libext+sv",
                "cli: -libext sv",
                "api: chip.set('option', 'libext', 'sv')"],
            schelp="""
            List of file extensions that should be used for finding modules.
            For example, if :keypath:`option,ydir` is specified as ./lib", and '.v'
            is specified as libext then the files ./lib/\\*.v ", will be searched for
            module matches.""")

    name = 'default'
    scparam(cfg, ['option', 'param', name],
            sctype='str',
            shorthelp="Option: design parameter",
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
            pernode=PerNode.OPTIONAL,
            shorthelp='Option: continue-on-error',
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
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            unit='s',
            shorthelp="Option: timeout value",
            switch="-timeout <float>",
            example=["cli: -timeout 3600",
                     "api: chip.set('option', 'timeout', 3600)"],
            schelp="""
            Timeout value in seconds. The timeout value is compared
            against the wall time tracked by the SC runtime to determine
            if an operation should continue.""")

    scparam(cfg, ['option', 'strict'],
            sctype='bool',
            shorthelp="Option: strict checking",
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
            sctype='<slurm,lsf,sge,docker>',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: scheduler platform",
            switch="-scheduler <str>",
            example=[
                "cli: -scheduler slurm",
                "api: chip.set('option', 'scheduler', 'name', 'slurm')"],
            schelp="""
            Sets the type of job scheduler to be used for each individual
            flowgraph steps. If the parameter is undefined, the steps are executed
            on the same machine that the SC was launched on. If 'slurm' is used,
            the host running the 'sc' command must be running a 'slurmctld' daemon
            managing a Slurm cluster. Additionally, the build directory
            (:keypath:`option,builddir`) must be located in shared storage which
            can be accessed by all hosts in the cluster.""")

    scparam(cfg, ['option', 'scheduler', 'cores'],
            sctype='int',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
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
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: scheduler memory constraint",
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
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: scheduler queue",
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
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: scheduler start time",
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
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: scheduler arguments",
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
            sctype='[<all,summary,begin,end,timeout,fail>]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: message event trigger",
            switch="-msgevent <str>",
            example=[
                "cli: -msgevent all",
                "api: chip.set('option', 'scheduler', 'msgevent', 'all')"],
            schelp="""
            Directs job scheduler to send a message to the user in
            :keypath:`option,scheduler,msgcontact` when certain events occur
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
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Option: message contact",
            switch="-msgcontact <str>",
            example=[
                "cli: -msgcontact 'wile.e.coyote@acme.com'",
                "api: chip.set('option', 'scheduler', 'msgcontact', 'wiley@acme.com')"],
            schelp="""
            List of email addresses to message on a :keypath:`option,scheduler,msgevent`.
            Support for email messages relies on job scheduler daemon support.
            For more information, see the job scheduler documentation. """)

    scparam(cfg, ['option', 'scheduler', 'maxnodes'],
            sctype='int',
            shorthelp="Option: maximum concurrent nodes",
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
            scope=Scope.GLOBAL,
            shorthelp="Package: version",
            switch="-package_version <str>",
            example=[
                "cli: -package_version 1.0",
                "api: chip.set('package', 'version', '1.0')"],
            schelp="""Package version. Can be a branch, tag, commit hash,
            or a semver compatible version.""")

    scparam(cfg, ['package', 'description'],
            sctype='str',
            scope=Scope.GLOBAL,
            shorthelp="Package: description",
            switch="-package_description <str>",
            example=[
                "cli: -package_description 'Yet another cpu'",
                "api: chip.set('package', 'description', 'Yet another cpu')"],
            schelp="""Package short one line description for package
            managers and summary reports.""")

    scparam(cfg, ['package', 'keyword'],
            sctype='str',
            scope=Scope.GLOBAL,
            shorthelp="Package: keyword",
            switch="-package_keyword <str>",
            example=[
                "cli: -package_keyword cpu",
                "api: chip.set('package', 'keyword', 'cpu')"],
            schelp="""Package keyword(s) used to characterize package.""")
    scparam(cfg, ['package', 'doc', 'homepage'],
            sctype='str',
            scope=Scope.GLOBAL,
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
                scope=Scope.GLOBAL,
                shorthelp=f"Package: {item} document",
                switch=f"-package_doc_{item} <file>",
                example=[
                    f"cli: -package_doc_{item} {item}.pdf",
                    f"api: chip.set('package', 'doc', '{item}', '{item}.pdf')"],
                schelp=f"""Package list of {item} documents.""")

    scparam(cfg, ['package', 'license'],
            sctype='[str]',
            scope=Scope.GLOBAL,
            shorthelp="Package: license identifiers",
            switch="-package_license <str>",
            example=[
                "cli: -package_license 'Apache-2.0'",
                "api: chip.set('package', 'license', 'Apache-2.0')"],
            schelp="""Package list of SPDX license identifiers.""")

    scparam(cfg, ['package', 'licensefile'],
            sctype='[file]',
            scope=Scope.GLOBAL,
            shorthelp="Package: license files",
            switch="-package_licensefile <file>",
            example=[
                "cli: -package_licensefile './LICENSE'",
                "api: chip.set('package', 'licensefile', './LICENSE')"],
            schelp="""Package list of license files for to be
            applied in cases when a SPDX identifier is not available.
            (eg. proprietary licenses).""")

    scparam(cfg, ['package', 'organization'],
            sctype='[str]',
            scope=Scope.GLOBAL,
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
                scope=Scope.GLOBAL,
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
            scope=Scope.GLOBAL,
            shorthelp="Package: data source path",
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
            scope=Scope.GLOBAL,
            shorthelp="Package: data source reference",
            switch="-package_source_ref 'source <str>'",
            example=[
                "cli: -package_source_ref 'freepdk45_data 07ec4aa'",
                "api: chip.set('package', 'source', 'freepdk45_data', 'ref', '07ec4aa')"],
            schelp="""Package data source reference""")

    return cfg


############################################
# Design Checklist
############################################
def schema_checklist(cfg):
    from siliconcompiler.checklist import ChecklistSchema
    cfg.insert("checklist", "default", ChecklistSchema())
    return cfg


###########################
# ASIC Setup
###########################
def schema_asic(cfg):
    from siliconcompiler.asic import ASICSchema
    cfg.insert("asic", ASICSchema())
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
            pernode=PerNode.OPTIONAL,
            unit='V',
            scope=Scope.JOB,
            shorthelp="Constraint: pin voltage level",
            switch="-constraint_timing_voltage 'scenario pin <float>'",
            example=["cli: -constraint_timing_voltage 'worst VDD 0.9'",
                     "api: chip.set('constraint', 'timing', 'worst', 'voltage', 'VDD', '0.9')"],
            schelp="""Operating voltage applied to a specific pin in the scenario.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'temperature'],
            sctype='float',
            pernode=PerNode.OPTIONAL,
            unit='C',
            scope=Scope.JOB,
            shorthelp="Constraint: temperature",
            switch="-constraint_timing_temperature 'scenario <float>'",
            example=["cli: -constraint_timing_temperature 'worst 125'",
                     "api: chip.set('constraint', 'timing', 'worst', 'temperature', '125')"],
            schelp="""Chip temperature applied to the scenario specified in degrees C.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'libcorner'],
            sctype='[str]',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            shorthelp="Constraint: library corner",
            switch="-constraint_timing_libcorner 'scenario <str>'",
            example=["cli: -constraint_timing_libcorner 'worst ttt'",
                     "api: chip.set('constraint', 'timing', 'worst', 'libcorner', 'ttt')"],
            schelp="""List of characterization corners used to select
            timing files for all logiclibs and macrolibs.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'pexcorner'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            shorthelp="Constraint: pex corner",
            switch="-constraint_timing_pexcorner 'scenario <str>'",
            example=["cli: -constraint_timing_pexcorner 'worst max'",
                     "api: chip.set('constraint', 'timing', 'worst', 'pexcorner', 'max')"],
            schelp="""Parasitic corner applied to the scenario. The
            'pexcorner' string must match a corner found in :keypath:`pdk,<pdk>,pexmodel`.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'opcond'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            shorthelp="Constraint: operating condition",
            switch="-constraint_timing_opcond 'scenario <str>'",
            example=["cli: -constraint_timing_opcond 'worst typical_1.0'",
                     "api: chip.set('constraint', 'timing', 'worst', 'opcond', 'typical_1.0')"],
            schelp="""Operating condition applied to the scenario. The value
            can be used to access specific conditions within the library
            timing models from the :keypath:`asic,logiclib` timing models.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'mode'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            shorthelp="Constraint: operating mode",
            switch="-constraint_timing_mode 'scenario <str>'",
            example=["cli: -constraint_timing_mode 'worst test'",
                     "api: chip.set('constraint', 'timing', 'worst', 'mode', 'test')"],
            schelp="""Operating mode for the scenario. Operating mode strings
            can be values such as test, functional, standby.""")

    scparam(cfg, ['constraint', 'timing', scenario, 'file'],
            sctype='[file]',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
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
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
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
            sctype='(float,float)',
            pernode=PerNode.OPTIONAL,
            unit='um',
            shorthelp="Constraint: component placement",
            switch="-constraint_component_placement 'inst <(float,float)>'",
            example=[
                "cli: -constraint_component_placement 'i0 (2.0,3.0)'",
                "api: chip.set('constraint', 'component', 'i0', 'placement', (2.0, 3.0))"],
            schelp="""
            Placement location of a named instance, specified as a (x, y) tuple of
            floats. The location refers to the distance from the substrate origin to
            the anchor point of the placed component, defined by
            the :keypath:`datasheet,package,<name>,anchor` parameter.""")

    scparam(cfg, ['constraint', 'component', inst, 'partname'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: component part name",
            switch="-constraint_component_partname 'inst <str>'",
            example=[
                "cli: -constraint_component_partname 'i0 filler_x1'",
                "api: chip.set('constraint', 'component', 'i0', 'partname', 'filler_x1')"],
            schelp="""
            Name of the model, type, or variant of the placed component. In the chip
            design domain, 'partname' is synonymous to 'cellname' or 'cell'. The
            'partname' is required for instances that are not represented within
            the design netlist (ie. physical only cells).""")

    scparam(cfg, ['constraint', 'component', inst, 'halo'],
            sctype='(float,float)',
            pernode=PerNode.OPTIONAL,
            unit='um',
            shorthelp="Constraint: component halo",
            switch="-constraint_component_halo 'inst <(float,float)>'",
            example=[
                "cli: -constraint_component_halo 'i0 (1,1)'",
                "api: chip.set('constraint', 'component', 'i0', 'halo', (1, 1))"],
            schelp="""
            Placement keepout halo around the named component, specified as a
            (horizontal, vertical) tuple.""")

    rotations = ['R0', 'R90', 'R180', 'R270',
                 'MX', 'MX_R90', 'MX_R180', 'MX_R270',
                 'MY', 'MY_R90', 'MY_R180', 'MY_R270',
                 'MZ', 'MZ_R90', 'MZ_R180', 'MZ_R270',
                 'MZ_MX', 'MZ_MX_R90', 'MZ_MX_R180', 'MZ_MX_R270',
                 'MZ_MY', 'MZ_MY_R90', 'MZ_MY_R180', 'MZ_MY_R270']
    scparam(cfg, ['constraint', 'component', inst, 'rotation'],
            sctype=f'<{",".join(rotations)}>',
            pernode=PerNode.OPTIONAL,
            defvalue='R0',
            shorthelp="Constraint: component rotation",
            switch="-constraint_component_rotation 'inst <str>'",
            example=[
                "cli: -constraint_component_rotation 'i0 R90'",
                "api: chip.set('constraint', 'component', 'i0', 'rotation', 'R90')"],
            schelp="""
        Placement rotation of the component. Components are always placed
        such that the lower left corner of the cell is at the anchor point
        (0,0) after any orientation. The MZ type rotations are for 3D design and
        typically not supported by 2D layout systems like traditional
        ASIC tools. For graphical illustrations of the rotation types, see
        the SiliconCompiler documentation.

        * ``R0``: North orientation (no rotation)
        * ``R90``: West orientation, rotate 90 deg counter clockwise (ccw)
        * ``R180``: South orientation, rotate 180 deg counter ccw
        * ``R270``: East orientation, rotate 180 deg counter ccw

        * ``MX``, ``MY_R180``: Flip on x-axis
        * ``MX_R90``, ``MY_R270``: Flip on x-axis and rotate 90 deg ccw
        * ``MX_R180``, ``MY``: Flip on x-axis and rotate 180 deg ccw
        * ``MX_R270``, ``MY_R90``: Flip on x-axis and rotate 270 deg ccw

        * ``MZ``: Reverse component metal stack
        * ``MZ_R90``: Reverse metal stack and rotate 90 deg ccw
        * ``MZ_R180``: Reverse metal stack and rotate 180 deg ccw
        * ``MZ_R270``: Reverse  metal stack and rotate 270 deg ccw
        * ``MZ_MX``, ``MZ_MY_R180``: Reverse metal stack and flip on x-axis
        * ``MZ_MX_R90``, ``MZ_MY_R270``: Reverse metal stack, flip on x-axis, and rotate 90 deg ccw
        * ``MZ_MX_R180``, ``MZ_MY``: Reverse metal stack, flip on x-axis, and rotate 180 deg ccw
        * ``MZ_MX_R270``, ``MZ_MY_R90``: Reverse metal stack, flip on x-axis and rotate 270 deg ccw
            """)

    scparam(cfg, ['constraint', 'component', inst, 'substrate'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: component substrate",
            switch="-constraint_component_substrate 'inst <str>'",
            example=[
                "cli: -constraint_component_substrate 'i0 pcb0'",
                "api: chip.set('constraint', 'component', 'i0', 'substrate', 'pcb0')"],
            schelp="""
            Name of physical substrates instance that components are placed upon.
            Any flat surface can serve as a substrate (eg. wafers, dies, panels, PCBs,
            substrates, interposers).""")

    scparam(cfg, ['constraint', 'component', inst, 'side'],
            sctype='<left,right,front,back,top,bottom>',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: component side",
            switch="-constraint_component_side 'inst <str>'",
            example=[
                "cli: -constraint_component_side 'i0 top'",
                "api: chip.set('constraint', 'component', 'i0', 'side', 'top')"],
            schelp="""
            Side of the substrate where the component should be placed. The `side`
            is defined with respect to a viewer looking sideways at an object.
            Top is towards the sky, front is the side closest to the viewer, and
            right is right. The maximum number of sides per substrate is six""")

    scparam(cfg, ['constraint', 'component', inst, 'zheight'],
            sctype='float',
            pernode=PerNode.OPTIONAL,
            unit='um',
            shorthelp="Constraint: component placement zheight",
            switch="-constraint_component_zheight 'inst <float>'",
            example=[
                "cli: -constraint_component_zheight 'i0 100.0'",
                "api: chip.set('constraint', 'component', 'i0', 'zheight', 100.0)"],
            schelp="""
            Height above the substrate for component placement. The space
            between the component and substrate is occupied by material,
            supporting scaffolding, and electrical connections (eg. bumps,
            vias, pillars).""")

    # PINS
    name = 'default'
    scparam(cfg, ['constraint', 'pin', name, 'placement'],
            sctype='(float,float)',
            pernode=PerNode.OPTIONAL,
            unit='um',
            shorthelp="Constraint: pin placement",
            switch="-constraint_pin_placement 'name <(float,float)>'",
            example=[
                "cli: -constraint_pin_placement 'nreset (2.0,3.0)'",
                "api: chip.set('constraint', 'pin', 'nreset', 'placement', (2.0, 3.0))"],
            schelp="""
            Placement location of a named pin, specified as a (x,y) tuple of
            floats with respect to the lower left corner of the substrate. The location
            refers to the center of the pin. The 'placement' parameter
            is a goal/intent, not an exact specification. The layout system
            may adjust sizes to meet competing goals such as manufacturing design
            rules and grid placement guidelines.""")

    scparam(cfg, ['constraint', 'pin', name, 'width'],
            sctype='float',
            unit='um',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: pin width",
            switch="-constraint_pin_width 'name <float>'",
            example=[
                "cli: -constraint_pin_width 'nreset 1.0'",
                "api: chip.set('constraint', 'pin', 'nreset', 'width', 1.0)"],
            schelp="""
            Pin width constraint.  Package pin width is the lateral
            (side-to-side) thickness of a pin on a physical component.
            This parameter represents goal/intent, not an exact
            specification. The layout system may adjust dimensions to meet
            competing goals such as manufacturing design rules and grid placement
            guidelines.""")

    scparam(cfg, ['constraint', 'pin', name, 'length'],
            sctype='float',
            unit='um',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: pin length",
            switch="-constraint_pin_length 'name <float>'",
            example=[
                "cli: -constraint_pin_length 'nreset 1.0'",
                "api: chip.set('constraint', 'pin', 'nreset', 'length', 1.0)"],
            schelp="""
            Pin length constraint.  Package pin length refers to the
            length of the electrical pins extending out from (or into)
            a component. This parameter represents goal/intent, not an exact
            specification. The layout system may adjust dimensions to meet
            competing goals such as manufacturing design rules and grid placement
            guidelines.""")

    scparam(cfg, ['constraint', 'pin', name, 'shape'],
            sctype='<circle,rectangle,square,hexagon,octagon,oval,pill,polygon>',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: pin shape",
            switch="-constraint_pin_shape 'name <str>'",
            example=[
                "cli: -constraint_pin_shape 'nreset circle'",
                "api: chip.set('constraint', 'pin', 'nreset', 'shape', 'circle')"],
            schelp="""
            Pin shape constraint specified on a per pin basis. In 3D design systems,
            the pin shape represents the cross section of the pin in the direction
            orthogonal to the signal flow direction. The 'pill' (aka stadium) shape,
            is rectangle with semicircles at a pair of opposite sides. The other
            pin shapes represent common geometric shape definitions.""")

    scparam(cfg, ['constraint', 'pin', name, 'layer'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: pin layer",
            switch="-constraint_pin_layer 'name <str>'",
            example=[
                "cli: -constraint_pin_layer 'nreset m4'",
                "api: chip.set('constraint', 'pin', 'nreset', 'layer', 'm4')"],
            schelp="""
            Pin metal layer constraint specified on a per pin basis.
            Metal names should either be the PDK specific metal stack name or
            an integer with '1' being the lowest routing layer.
            The wildcard character '*' is supported for pin names.""")

    scparam(cfg, ['constraint', 'pin', name, 'side'],
            sctype='int',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: pin side",
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
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: pin order",
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
            pernode=PerNode.OPTIONAL,
            unit='um',
            shorthelp="Constraint: net max length",
            switch="-constraint_net_maxlength 'name <float>'",
            example=[
                "cli: -constraint_net_maxlength 'nreset 1000'",
                "api: chip.set('constraint', 'net', 'nreset', 'maxlength', '1000')"],
            schelp="""
            Maximum total length of a net. Wildcards ('*') can be used for
            net names.""")

    scparam(cfg, ['constraint', 'net', name, 'maxresistance'],
            sctype='float',
            pernode=PerNode.OPTIONAL,
            unit='ohm',
            shorthelp="Constraint: net max resistance",
            switch="-constraint_net_maxresistance 'name <float>'",
            example=[
                "cli: -constraint_net_maxresistance 'nreset 1'",
                "api: chip.set('constraint', 'net', 'nreset', 'maxresistance', '1')"],
            schelp="""
            Maximum resistance of named net between driver and receiver
            specified in ohms. Wildcards ('*') can be used for net names.""")

    scparam(cfg, ['constraint', 'net', name, 'ndr'],
            sctype='(float,float)',
            pernode=PerNode.OPTIONAL,
            unit='um',
            shorthelp="Constraint: net routing rule",
            switch="-constraint_net_ndr 'name <(float,float)>'",
            example=[
                "cli: -constraint_net_ndr 'nreset (0.4,0.4)'",
                "api: chip.set('constraint', 'net', 'nreset', 'ndr', (0.4, 0.4))"],
            schelp="""
            Definitions of non-default routing rule specified on a per
            net basis. Constraints are entered as a (width, space) tuples.
            Wildcards ('*') can be used for net names.""")

    scparam(cfg, ['constraint', 'net', name, 'minlayer'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: net minimum routing layer",
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
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: net maximum routing layer",
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
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: net shielding",
            switch="-constraint_net_shield 'name <str>'",
            example=[
                "cli: -constraint_net_shield 'clk vss'",
                "api: chip.set('constraint', 'net', 'clk', 'shield', 'vss')"],
            schelp="""
            Specifies that the named net should be shielded by the given
            signal on both sides of the net.""")

    scparam(cfg, ['constraint', 'net', name, 'match'],
            sctype='[str]',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: net matched routing",
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
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: net diffpair",
            switch="-constraint_net_diffpair 'name <str>'",
            example=[
                "cli: -constraint_net_diffpair 'clkn clkp'",
                "api: chip.set('constraint', 'net', 'clkn', 'diffpair', 'clkp')"],
            schelp="""
            Differential pair signal of the named net (only used for actual
            differential pairs).""")

    scparam(cfg, ['constraint', 'net', name, 'sympair'],
            sctype='str',
            pernode=PerNode.OPTIONAL,
            shorthelp="Constraint: net sympair",
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
            pernode=PerNode.OPTIONAL,
            unit='um',
            scope=Scope.JOB,
            shorthelp="Constraint: layout outline",
            switch="-constraint_outline <(float,float)>",
            example=["cli: -constraint_outline '(0,0)'",
                     "api: chip.set('constraint', 'outline', (0, 0))"],
            schelp="""
            List of (x, y) points that define the outline physical layout
            physical design. Simple rectangle areas can be defined with two points,
            one for the lower left corner and one for the upper right corner.""")

    scparam(cfg, ['constraint', 'corearea'],
            sctype='[(float,float)]',
            pernode=PerNode.OPTIONAL,
            unit='um',
            scope=Scope.JOB,
            shorthelp="Constraint: layout core area",
            switch="-constraint_corearea <(float,float)>",
            example=["cli: -constraint_corearea '(0,0)'",
                     "api: chip.set('constraint', 'corearea', (0, 0))"],
            schelp="""
            List of (x, y) points that define the outline of the core area for the
            physical design. Simple rectangle areas can be defined with two points,
            one for the lower left corner and one for the upper right corner.""")

    scparam(cfg, ['constraint', 'coremargin'],
            sctype='float',
            pernode=PerNode.OPTIONAL,
            unit='um',
            scope=Scope.JOB,
            shorthelp="Constraint: layout core margin",
            switch="-constraint_coremargin <float>",
            example=["cli: -constraint_coremargin 1",
                     "api: chip.set('constraint', 'coremargin', '1')"],
            schelp="""
            Halo/margin between the outline and core area for fully
            automated layout sizing and floorplanning.""")

    scparam(cfg, ['constraint', 'density'],
            sctype='float',
            pernode=PerNode.OPTIONAL,
            scope=Scope.JOB,
            shorthelp="Constraint: layout density",
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
            pernode=PerNode.OPTIONAL,
            defvalue=1.0,
            scope=Scope.JOB,
            shorthelp="Constraint: layout aspect ratio",
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
