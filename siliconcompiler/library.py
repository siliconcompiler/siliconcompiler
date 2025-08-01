from typing import final, Union, List

from siliconcompiler import PackageSchema

from siliconcompiler.dependencyschema import DependencySchema
from siliconcompiler.filesetschema import FileSetSchema
from siliconcompiler.schema import NamedSchema

from siliconcompiler.schema import EditableSchema, Parameter, Scope, PerNode
from siliconcompiler.schema.utils import trim


class LibrarySchema(FileSetSchema, PackageSchema, NamedSchema):
    def __init__(self, name: str = None):
        super().__init__()
        self.set_name(name)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return LibrarySchema.__name__


class ToolLibrarySchema(LibrarySchema):
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

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return ToolLibrarySchema.__name__

    def _from_dict(self, manifest, keypath, version=None):
        if "tool" in manifest:
            # collect tool keys
            tool_keys = self.allkeys("tool")

            # collect manifest
            manifest_keys = set()
            for tool, tool_var in manifest["tool"].items():
                for var in tool_var:
                    manifest_keys.add((tool, var))

            edit = EditableSchema(self)
            for tool, var in sorted(manifest_keys.difference(tool_keys)):
                edit.insert("tool", tool, var,
                            Parameter.from_dict(
                                manifest["tool"][tool][var],
                                keypath=keypath + [tool, var],
                                version=version))
                del manifest["tool"][tool][var]
                if not manifest["tool"][tool]:
                    del manifest["tool"][tool]

            if not manifest["tool"]:
                del manifest["tool"]

        return super()._from_dict(manifest, keypath, version)


class StdCellLibrarySchema(ToolLibrarySchema, DependencySchema):
    def __init__(self, name: str = None):
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)

        schema.insert(
            "asic", "pdk",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: ",
                example=[
                    "api: schema.set('asic', 'libcornerfileset', 'slow', 'nldm', 'timing.slow')"],
                help=trim("""""")))

        schema.insert(
            'asic', 'libcornerfileset', 'default', 'default',
            Parameter(
                '{str}',
                scope=Scope.GLOBAL,
                shorthelp="ASIC: map of filesets to timing corners",
                example=[
                    "api: schema.set('asic', 'libcornerfileset', 'slow', 'nldm', 'timing.slow')"],
                help=trim("""Map between filesets and timing corners.""")))

        schema.insert(
            'asic', 'pexcornerfileset', 'default',
            Parameter(
                '{str}',
                scope=Scope.GLOBAL,
                shorthelp="ASIC: map of filesets to pex corners",
                example=[
                    "api: schema.set('asic', 'pexcornerfileset', 'slow', 'timing.slow')"],
                help=trim("""Map between filesets and pex corners.""")))

        schema.insert(
            'asic', 'aprfileset',
            Parameter(
                '{str}',
                scope=Scope.GLOBAL,
                shorthelp="ASIC: map of filesets to APR files",
                example=[
                    "api: schema.set('asic', 'aprfileset', 'model.lef')"],
                help=trim("""Map between filesets and automated place and route tool files.""")))

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

    def set_asic_pdk(self, pdk: Union[str, "PDKSchema"]):
        """
        Set the PDK associated with this library

        Args:
            pdk (str or class:`PDKSchema`): pdk to associate
        """
        from siliconcompiler import PDKSchema
        if isinstance(pdk, PDKSchema):
            pdk_name = pdk.name
            self.add_dep(pdk)
        elif isinstance(pdk, str):
            pdk_name = pdk
        else:
            raise TypeError("pdk must be a PDK object or string")

        return self.set("asic", "pdk", pdk_name)

    def add_asic_libcornerfileset(self, corner: str, model: str, fileset: str = None):
        """
        Adds a mapping between filesets a corners defined in the library

        Args:
            corner (str): name of the timing or parasitic corner
            model(str): type of delay modeling used, eg. ccs, nldm, etc.
            fileset (str): name of the fileset
        """
        if not fileset:
            fileset = self._get_active("fileset")

        if not isinstance(model, str):
            raise TypeError("model must be a string")

        self._assert_fileset(fileset)

        return self.add("asic", "libcornerfileset", corner, model, fileset)

    def add_asic_pexcornerfileset(self, corner: str, model: str, fileset: str = None):
        """
        Adds a mapping between filesets a corners defined in the library

        Args:
            corner (str): name of the timing or parasitic corner
            model(str): type of delay modeling used, eg. spice, etc.
            fileset (str): name of the fileset
        """
        if not fileset:
            fileset = self._get_active("fileset")

        if not isinstance(model, str):
            raise TypeError("model must be a string")

        self._assert_fileset(fileset)

        return self.add("asic", "pexcornerfileset", corner, model, fileset)

    def add_asic_aprfileset(self, fileset: str = None):
        """
        Adds a mapping between filesets defined in the library

        Args:
            fileset (str): name of the fileset
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        return self.add("asic", "aprfileset", fileset)

    def add_asic_celllist(self, type: str, cells: Union[List[str], str]):
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

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return StdCellLibrarySchema.__name__
