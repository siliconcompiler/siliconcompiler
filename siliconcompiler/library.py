from typing import final, Union, List

from siliconcompiler.design import DesignSchema

from siliconcompiler.schema import EditableSchema, Parameter, Scope, PerNode
from siliconcompiler.schema.utils import trim


class LibrarySchema(DesignSchema):
    def __init__(self, name: str = None):
        super().__init__()
        self.set_name(name)

    @final
    def define_tool_parameter(self, tool: str, name: str, type: str, help: str, **kwargs):
        """
        Define a new tool parameter for the library

        Args:
            tool (str): name of the tool
            name (str): name of the parameter
            type (str): type of parameter, see :class:`.Parameter`.
            help (str): help information for this parameter
            kwargs: passthrough for :class:`.Parameter`.
        """
        if isinstance(help, str):
            # grab first line for short help
            help = trim(help)
            shorthelp = help.splitlines()[0].strip()
        else:
            raise TypeError("help must be a string")

        kwargs["scope"] = Scope.GLOBAL
        kwargs["pernode"] = PerNode.NEVER
        kwargs["shorthelp"] = shorthelp
        kwargs["help"] = help

        EditableSchema(self).insert(
            "tool", tool, name,
            Parameter(type, **kwargs)
        )


class StdCellLibrarySchema(LibrarySchema):
    def __init__(self, name: str = None):
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)

        schema.insert(
            'asic', 'cornerfilesets', 'default',
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                shorthelp="ASIC: map of filesets to timing or pex corners",
                example=["api: schema.set('asic', 'cornerfilesets', 'slow', 'timing.slow')"],
                help=trim("""Map between filesets and timing or pex corners.""")))

        # TODO: Expand on the exact definitions of these types of cells.
        # minimize typing
        for item in [
                'decap',
                'tie',
                'hold',
                'clkbuf',
                'clkgate',
                'clklogic',
                'dontuse',
                'filler',
                'tap',
                'endcap',
                'antenna']:
            schema.insert(
                'asic', 'cells', item,
                Parameter(
                    '[str]',
                    scope=Scope.GLOBAL,
                    shorthelp=f"ASIC: {item} cell list",
                    example=[f"api: schema.set('asic', 'cells', '{item}', '*eco*')"],
                    help=trim("""
                    List of cells grouped by a property that can be accessed
                    directly by the designer and tools. The example below shows how
                    all cells containing the string 'eco' could be marked as dont use
                    for the tool.""")))

        schema.insert(
            'asic', 'site',
            Parameter(
                '[str]',
                scope=Scope.GLOBAL,
                shorthelp="ASIC: library sites",
                example=["api: schema.set('asic', 'site', 'Site_12T')"],
                help="Site names for a given library architecture."))

    def add_asic_corner_fileset(self, corner: str, fileset: str = None):
        """
        Adds a mapping between filesets a corners defined in the library

        Args:
            corner (str): name of the timing or parasitic corner
            fileset (str): name of the fileset
        """
        if not fileset:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise TypeError("fileset must be a string")

        if fileset not in self.getkeys("fileset"):
            raise ValueError(f"{fileset} is not defined")

        return self.add("asic", "cornerfilesets", corner, fileset)

    def add_asic_cell_list(self, type: str, cells: Union[List[str], str]):
        """
        Adds a standard cell library to the specified type.

        Args:
            type (str): category of cell type
            cells (list of str): cells to add
        """
        return self.add("asic", "cells", type, cells)

    def add_asic_site(self, site: Union[List[str], str]):
        """
        Adds a standard site to the library

        Args:
            type (str): category of cell type
            cells (list of str): cells to add
        """
        return self.add("asic", "site", site)
