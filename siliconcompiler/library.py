from typing import final

from siliconcompiler.design import DesignSchema

from siliconcompiler.schema import EditableSchema, Parameter, Scope, PerNode
from siliconcompiler.schema.utils import trim


class LibrarySchema(DesignSchema):
    def __init__(self, name):
        super().__init__(name)

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
    def __init__(self, name):
        super().__init__(name)

        schema = EditableSchema(self)

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


class YosysStdCellLibbrarySchema(StdCellLibrarySchema):
    def __init__(self):
        super().__init__(name=self.name())

        self.define_tool_parameter("yosys", "abc_clock_multiplier", "float", "long-blah")
        self.define_tool_parameter("yosys", "abc_constraint_load", "float", "long-blah")

        self.define_tool_parameter("yosys", "driver_cell", "str", "long-blah")
        self.define_tool_parameter("yosys", "buffer_cell", "(str,str,str)", "long-blah")
        self.define_tool_parameter("yosys", "tiehigh_cell", "(str,str)",  "long-blah")
        self.define_tool_parameter("yosys", "tielow_cell", "(str,str)", "long-blah")

        self.define_tool_parameter("yosys", "techmap", "[file]", "long-blah")
        self.define_tool_parameter("yosys", "tristatebuffermap", "file", "long-blah")
        self.define_tool_parameter("yosys", "addermap", "file", "long-blah")

    def add_yosys_buffer_cell(self, cell, input_port, output_port):
        pass

    def add_yosys_tiehigh_cell(self, cell, output_port):
        pass

    def add_yosys_tielow_cell(self, cell, output_port):
        pass


class OpenROADStdCellLibbrarySchema(StdCellLibrarySchema):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("openroad", "place_density", "float", "long-blah")
        self.define_tool_parameter("openroad", "pdngen", "[file]", "long-blah")


if __name__ == "__main__":
    class Test(YosysStdCellLibbrarySchema, StdCellLibrarySchema):
        def __init__(self):
            YosysStdCellLibbrarySchema.__init__(self)
            StdCellLibrarySchema.__init__(self, "testlib")

    t = Test()
    print(t.name())
    #t.write_manifest('Test.json')
