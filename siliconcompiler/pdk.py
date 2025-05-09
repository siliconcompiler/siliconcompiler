from siliconcompiler.schema import NamedSchema, PackageSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


class PDKSchema(NamedSchema, PackageSchema):
    def __init__(self, name=None, package=None):
        NamedSchema.__init__(self, name=name)
        PackageSchema.__init__(self, package=package)

        schema_pdk(self)


###############################################################################
# PDK
###############################################################################
def schema_pdk(schema):
    schema = EditableSchema(schema)

    tool = 'default'
    filetype = 'default'
    stackup = 'default'

    schema.insert(
        'foundry',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="PDK: foundry name",
            switch="-pdk_foundry 'pdkname <str>'",
            example=["cli: -pdk_foundry 'asap7 virtual'",
                     "api: chip.set('pdk', 'asap7', 'foundry', 'virtual')"],
            help=trim("""
            Name of foundry corporation. Examples include intel, gf, tsmc,
            samsung, skywater, virtual. The \'virtual\' keyword is reserved for
            simulated non-manufacturable processes.""")))

    schema.insert(
        'node',
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            unit='nm',
            shorthelp="PDK: process node",
            switch="-pdk_node 'pdkname <float>'",
            example=["cli: -pdk_node 'asap7 130'",
                     "api: chip.set('pdk', 'asap7', 'node', 130)"],
            help=trim("""
            Approximate relative minimum dimension of the process target specified
            in nanometers. The parameter is required for flows and tools that
            leverage the value to drive technology dependent synthesis and APR
            optimization. Node examples include 180, 130, 90, 65, 45, 32, 22 14,
            10, 7, 5, 3.""")))

    schema.insert(
        'version',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="PDK: version",
            switch="-pdk_version 'pdkname <str>'",
            example=["cli: -pdk_version 'asap7 1.0'",
                     "api: chip.set('pdk', 'asap7', 'version', '1.0')"],
            help=trim("""
            Alphanumeric string specifying the version of the PDK. Verification of
            correct PDK and IP versions is a hard ASIC tapeout require in all
            commercial foundries. The version number can be used for design manifest
            tracking and tapeout checklists.""")))

    schema.insert(
        'stackup',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: metal stackups",
            switch="-pdk_stackup 'pdkname <str>'",
            example=["cli: -pdk_stackup 'asap7 2MA4MB2MC'",
                     "api: chip.add('pdk', 'asap7', 'stackup', '2MA4MB2MC')"],
            help=trim("""
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
            parameters.""")))

    schema.insert(
        'minlayer', stackup,
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="PDK: minimum routing layer",
            switch="-pdk_minlayer 'pdk stackup <str>'",
            example=[
                "cli: -pdk_minlayer 'asap7 2MA4MB2MC M2'",
                "api: chip.set('pdk', 'asap7', 'minlayer', '2MA4MB2MC', 'M2')"],
            help=trim("""
            Minimum metal layer to be used for automated place and route
            specified on a per stackup basis.""")))

    schema.insert(
        'maxlayer', stackup,
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="PDK: maximum routing layer",
            switch="-pdk_maxlayer 'pdk stackup <str>'",
            example=[
                "cli: -pdk_maxlayer 'asap7 2MA4MB2MC M8'",
                "api: chip.set('pdk', 'asap7', 'maxlayer', 'MA4MB2MC', 'M8')"],
            help=trim("""
            Maximum metal layer to be used for automated place and route
            specified on a per stackup basis.""")))

    schema.insert(
        'wafersize',
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            unit='mm',
            shorthelp="PDK: wafer size",
            switch="-pdk_wafersize 'pdkname <float>'",
            example=["cli: -pdk_wafersize 'asap7 300'",
                     "api: chip.set('pdk', 'asap7', 'wafersize', 300)"],
            help=trim("""
            Wafer diameter used in wafer based manufacturing process.
            The standard diameter for leading edge manufacturing is 300mm. For
            older process technologies and specialty fabs, smaller diameters
            such as 200, 150, 125, and 100 are common. The value is used to
            calculate dies per wafer and full factory chip costs.""")))

    schema.insert(
        'panelsize',
        Parameter(
            '[(float,float)]',
            scope=Scope.GLOBAL,
            unit='mm',
            shorthelp="PDK: panel size",
            switch="-pdk_panelsize 'pdkname <(float,float)>'",
            example=[
                "cli: -pdk_panelsize 'asap7 (45.72,60.96)'",
                "api: chip.set('pdk', 'asap7', 'panelsize', (45.72, 60.96))"],
            help=trim("""
            List of panel sizes supported in the manufacturing process.
            """)))

    schema.insert(
        'unitcost',
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            unit='USD',
            shorthelp="PDK: unit cost",
            switch="-pdk_unitcost 'pdkname <float>'",
            example=["cli: -pdk_unitcost 'asap7 10000'",
                     "api: chip.set('pdk', 'asap7', 'unitcost', 10000)"],
            help=trim("""
            Raw cost per unit shipped by the factory, not accounting for yield
            loss.""")))

    schema.insert(
        'd0',
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            shorthelp="PDK: process defect density",
            switch="-pdk_d0 'pdkname <float>'",
            example=["cli: -pdk_d0 'asap7 0.1'",
                     "api: chip.set('pdk', 'asap7', 'd0', 0.1)"],
            help=trim("""
            Process defect density (d0) expressed as random defects per cm^2. The
            value is used to calculate yield losses as a function of area, which in
            turn affects the chip full factory costs. Two yield models are
            supported: Poisson (default), and Murphy. The Poisson based yield is
            calculated as dy = exp(-area * d0/100). The Murphy based yield is
            calculated as dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.""")))

    schema.insert(
        'scribe',
        Parameter(
            '(float,float)',
            scope=Scope.GLOBAL,
            unit='mm',
            shorthelp="PDK: horizontal scribe line width",
            switch="-pdk_scribe 'pdkname <(float,float)>'",
            example=["cli: -pdk_scribe 'asap7 (0.1,0.1)'",
                     "api: chip.set('pdk', 'asap7', 'scribe', (0.1, 0.1))"],
            help=trim("""
            Width of the horizontal and vertical scribe line used during die separation.
            The process is generally completed using a mechanical saw, but can be
            done through combinations of mechanical saws, lasers, wafer thinning,
            and chemical etching in more advanced technologies. The value is used
            to calculate effective dies per wafer and full factory cost.""")))

    schema.insert(
        'edgemargin',
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            unit='mm',
            shorthelp="PDK: wafer edge keep-out margin",
            switch="-pdk_edgemargin 'pdkname <float>'",
            example=[
                "cli: -pdk_edgemargin 'asap7 1'",
                "api: chip.set('pdk', 'asap7', 'edgemargin', 1)"],
            help=trim("""
            Keep-out distance/margin from the edge inwards. The edge
            is prone to chipping and need special treatment that preclude
            placement of designs in this area. The edge value is used to
            calculate effective units per wafer/panel and full factory cost.""")))

    simtype = 'default'
    schema.insert(
        'devmodel', tool, simtype, stackup,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: device models",
            switch="-pdk_devmodel 'pdkname tool simtype stackup <file>'",
            example=[
                "cli: -pdk_devmodel 'asap7 xyce spice M10 asap7.sp'",
                "api: chip.set('pdk', 'asap7', 'devmodel', 'xyce', 'spice', 'M10', 'asap7.sp')"],
            help=trim("""
            List of filepaths to PDK device models for different simulation
            purposes and for different tools. Examples of device model types
            include spice, aging, electromigration, radiation. An example of a
            'spice' tool is xyce. Device models are specified on a per metal stack
            basis. Process nodes with a single device model across all stacks will
            have a unique parameter record per metal stack pointing to the same
            device model file. Device types and tools are dynamic entries
            that depend on the tool setup and device technology. Pseudo-standardized
            device types include spice, em (electromigration), and aging.""")))

    corner = 'default'
    schema.insert(
        'pexmodel', tool, stackup, corner,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: parasitic TCAD models",
            switch="-pdk_pexmodel 'pdkname tool stackup corner <file>'",
            example=[
                "cli: -pdk_pexmodel 'asap7 fastcap M10 max wire.mod'",
                "api: chip.set('pdk', 'asap7', 'pexmodel', 'fastcap', 'M10', 'max', 'wire.mod')"],
            help=trim("""
            List of filepaths to PDK wire TCAD models used during automated
            synthesis, APR, and signoff verification. Pexmodels are specified on
            a per metal stack basis. Corner values depend on the process being
            used, but typically include nomenclature such as min, max, nominal.
            For exact names, refer to the DRM. Pexmodels are generally not
            standardized and specified on a per tool basis. An example of pexmodel
            type is 'fastcap'.""")))

    src = 'default'
    dst = 'default'
    schema.insert(
        'layermap', tool, src, dst, stackup,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: layer map file",
            switch="-pdk_layermap 'pdkname tool src dst stackup <file>'",
            example=[
                "cli: -pdk_layermap 'asap7 klayout db gds M10 asap7.map'",
                "api: chip.set('pdk', 'asap7', 'layermap', 'klayout', 'db', 'gds', 'M10', "
                "'asap7.map')"],
            help=trim("""
            Files describing input/output mapping for streaming layout data from
            one format to another. A foundry PDK will include an official layer
            list for all user entered and generated layers supported in the GDS
            accepted by the foundry for processing, but there is no standardized
            layer definition format that can be read and written by all EDA tools.
            To ensure mask layer matching, key/value type mapping files are needed
            to convert EDA databases to/from GDS and to convert between different
            types of EDA databases. Layer maps are specified on a per metal
            stackup basis. The 'src' and 'dst' can be names of SC supported tools
            or file formats (like 'gds').""")))

    schema.insert(
        'display', tool, stackup,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: display file",
            switch="-pdk_display 'pdkname tool stackup <file>'",
            example=[
                "cli: -pdk_display 'asap7 klayout M10 display.lyt'",
                "api: chip.set('pdk', 'asap7', 'display', 'klayout', 'M10', 'display.cfg')"],
            help=trim("""
            Display configuration files describing colors and pattern schemes for
            all layers in the PDK. The display configuration file is entered on a
            stackup and tool basis.""")))

    # TODO: create firm list of accepted files
    libarch = 'default'
    schema.insert(
        'aprtech', tool, stackup, libarch, filetype,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: APR technology files",
            switch="-pdk_aprtech 'pdkname tool stackup libarch filetype <file>'",
            example=[
                "cli: -pdk_aprtech 'asap7 openroad M10 12t lef tech.lef'",
                "api: chip.set('pdk', 'asap7', 'aprtech', 'openroad', 'M10', '12t', 'lef', "
                "'tech.lef')"],
            help=trim("""
            Technology file containing setup information needed to enable DRC clean APR
            for the specified stackup, libarch, and format. The 'libarch' specifies the
            library architecture (e.g. library height). For example a PDK with support
            for 9 and 12 track libraries might have 'libarchs' called 9t and 12t.
            The standard filetype for specifying place and route design rules for a
            process node is through a 'lef' format technology file. The
            'filetype' used in the aprtech is used by the tool specific APR TCL scripts
            to set up the technology parameters. Some tools may require additional
            files beyond the tech.lef file. Examples of extra file types include
            antenna, tracks, tapcell, viarules, and em.""")))

    name = 'default'
    for item in ('lvs', 'drc', 'erc', 'fill'):
        schema.insert(
            item, 'runset', tool, stackup, name,
            Parameter(
                '[file]',
                scope=Scope.GLOBAL,
                shorthelp=f"PDK: {item.upper()} runset files",
                switch=f"-pdk_{item}_runset 'pdkname tool stackup name <file>'",
                example=[
                    f"cli: -pdk_{item}_runset 'asap7 magic M10 basic $PDK/{item}.rs'",
                    f"api: chip.set('pdk', 'asap7', '{item}', 'runset', 'magic', 'M10', 'basic', "
                    f"'$PDK/{item}.rs')"],
                help=trim(f"""Runset files for {item.upper()} task.""")))

        schema.insert(
            item, 'waiver', tool, stackup, name,
            Parameter(
                '[file]',
                scope=Scope.GLOBAL,
                shorthelp=f"PDK: {item.upper()} waiver files",
                switch=f"-pdk_{item}_waiver 'pdkname tool stackup name <file>'",
                example=[
                    f"cli: -pdk_{item}_waiver 'asap7 magic M10 basic $PDK/{item}.txt'",
                    f"api: chip.set('pdk', 'asap7', '{item}', 'waiver', 'magic', 'M10', 'basic', "
                    f"'$PDK/{item}.txt')"],
                help=trim(f"""Waiver files for {item.upper()} task.""")))

    ###############
    # EDA vars
    ###############

    key = 'default'
    schema.insert(
        'file', tool, key, stackup,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: custom file",
            switch="-pdk_file 'pdkname tool key stackup <file>'",
            example=[
                "cli: -pdk_file 'asap7 xyce spice M10 asap7.sp'",
                "api: chip.set('pdk', 'asap7', 'file', 'xyce', 'spice', 'M10', 'asap7.sp')"],
            help=trim("""
            List of named files specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly supported by the SiliconCompiler PDK schema.""")))

    schema.insert(
        'dir', tool, key, stackup,
        Parameter(
            '[dir]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: custom directory",
            switch="-pdk_dir 'pdkname tool key stackup <dir>'",
            example=[
                "cli: -pdk_dir 'asap7 xyce rfmodel M10 rftechdir'",
                "api: chip.set('pdk', 'asap7', 'dir', 'xyce', 'rfmodel', 'M10', "
                "'rftechdir')"],
            help=trim("""
            List of named directories specified on a per tool and per stackup basis.
            The parameter should only be used for specifying files that are
            not directly supported by the SiliconCompiler PDK schema.""")))

    schema.insert(
        'var', tool, key, stackup,
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: custom, variable",
            switch="-pdk_var 'pdkname tool stackup key <str>'",
            example=[
                "cli: -pdk_var 'asap7 xyce modeltype M10 bsim4'",
                "api: chip.set('pdk', 'asap7', 'var', 'xyce', 'modeltype', 'M10', 'bsim4')"],
            help=trim("""
            List of key/value strings specified on a per tool and per stackup basis.
            The parameter should only be used for specifying variables that are
            not directly supported by the SiliconCompiler PDK schema.""")))

    ###############
    # Docs
    ###############
    schema.insert(
        'doc', 'default',
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="PDK: documentation",
            switch="-pdk_doc 'pdkname doctype <file>'",
            example=["cli: -pdk_doc 'asap7 reference reference.pdf'",
                     "api: chip.set('pdk', 'asap7', 'doc', 'reference', 'reference.pdf')"],
            help=trim("""Filepath to pdk documentation.""")))
