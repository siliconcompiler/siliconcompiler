from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.utils import trim


class ASICSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_asic(self)


###############################################################################
# ASIC
###############################################################################
def schema_asic(schema):
    schema = EditableSchema(schema)

    schema.insert(
        'logiclib',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: logic libraries",
            switch="-asic_logiclib <str>",
            example=["cli: -asic_logiclib nangate45",
                     "api: chip.set('asic', 'logiclib', 'nangate45')"],
            help=trim("""List of all selected logic libraries libraries
            to use for optimization for a given library architecture
            (9T, 11T, etc).""")))

    schema.insert(
        'macrolib',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: macro libraries",
            switch="-asic_macrolib <str>",
            example=["cli: -asic_macrolib sram64x1024",
                     "api: chip.set('asic', 'macrolib', 'sram64x1024')"],
            help=trim("""
            List of macro libraries to be linked in during synthesis and place
            and route. Macro libraries are used for resolving instances but are
            not used as targets for logic synthesis.""")))

    schema.insert(
        'delaymodel',
        Parameter(
            'str',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: delay model",
            switch="-asic_delaymodel <str>",
            example=["cli: -asic_delaymodel ccs",
                     "api: chip.set('asic', 'delaymodel', 'ccs')"],
            help=trim("""
            Delay model to use for the target libs. Commonly supported values
            are nldm and ccs.""")))

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
        schema.insert(
            'cells', item,
            Parameter(
                '[str]',
                pernode=PerNode.OPTIONAL,
                shorthelp=f"ASIC: {item} cell list",
                switch=f"-asic_cells_{item} '<str>'",
                example=[
                    f"cli: -asic_cells_{item} '*eco*'",
                    f"api: chip.set('asic', 'cells', '{item}', '*eco*')"],
                help=trim("""
                List of cells grouped by a property that can be accessed
                directly by the designer and tools. The example below shows how
                all cells containing the string 'eco' could be marked as dont use
                for the tool.""")))

    schema.insert(
        'libarch',
        Parameter(
            'str',
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: library architecture",
            switch="-asic_libarch '<str>'",
            example=[
                "cli: -asic_libarch '12track'",
                "api: chip.set('asic', 'libarch', '12track')"],
            help=trim("""
            The library architecture (e.g. library height) used to build the
            design. For example a PDK with support for 9 and 12 track libraries
            might have 'libarchs' called 9t and 12t.""")))

    libarch = 'default'
    schema.insert(
        'site', libarch,
        Parameter(
            '[str]',
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: library sites",
            switch="-asic_site 'libarch <str>'",
            example=[
                "cli: -asic_site '12track Site_12T'",
                "api: chip.set('asic', 'site', '12track', 'Site_12T')"],
            help=trim("""
            Site names for a given library architecture.""")))
