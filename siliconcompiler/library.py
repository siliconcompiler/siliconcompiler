from typing import final

from siliconcompiler.design import DesignSchema

from siliconcompiler.schema import EditableSchema, Parameter, Scope, PerNode
from siliconcompiler.schema.utils import trim


class LibrarySchema(DesignSchema):
    def __init__(self, name=None):
        super().__init__()
        self.set_name(name)

    @final
    def define_tool_parameter(self, tool, name, type, help, **kwargs):
        shorthelp = help.splitlines()[0].strip()

        EditableSchema(self).insert(
            "tool", tool, name,
            Parameter(
                type,
                scope=Scope.GLOBAL,
                pernode=PerNode.NEVER,
                shorthelp=shorthelp,
                help=help,
                **kwargs
            ))


class StdCellLibrarySchema(LibrarySchema):
    def __init__(self, name=None):
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)

        schema.insert('asic', 'cornerfilesets', 'default', Parameter('[str]'))

        libarch = 'default'
        schema.insert(
            'asic', 'pdk',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="ASIC: library sites",
                example=[
                    "api: chip.set('asic', 'site', '12track', 'Site_12T')"],
                help="Site names for a given library architecture."))

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
                'asic', 'cells', item,
                Parameter(
                    '[str]',
                    scope=Scope.GLOBAL,
                    shorthelp=f"ASIC: {item} cell list",
                    example=[
                        f"api: chip.set('asic', 'cells', '{item}', '*eco*')"],
                    help=trim("""
                    List of cells grouped by a property that can be accessed
                    directly by the designer and tools. The example below shows how
                    all cells containing the string 'eco' could be marked as dont use
                    for the tool.""")))

        libarch = 'default'
        schema.insert(
            'asic', 'site', libarch,
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                shorthelp="ASIC: library sites",
                example=[
                    "api: chip.set('asic', 'site', '12track', 'Site_12T')"],
                help="Site names for a given library architecture."))

    def add_timing_fileset(self, corner, fileset):
        self.add("asic", "cornerfilesets", corner, fileset)
        # TODO Add check for fileset existance

    def add_cell_list(self, type, cells):
        self.add("asic", "cells", type, cells)


if __name__ == "__main__":
    class Test(StdCellLibrarySchema):
        def __init__(self):
            super().__init__()
            self.set_name("testlib")

    t = Test()
    print(t.name())
    t.write_manifest('Test.json')
