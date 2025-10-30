from typing import final, Union, List, Tuple, Optional, Dict, Set, TYPE_CHECKING

from siliconcompiler.schema_support.packageschema import PackageSchema

from siliconcompiler.schema_support.dependencyschema import DependencySchema
from siliconcompiler.schema_support.filesetschema import FileSetSchema
from siliconcompiler.schema_support.pathschema import PathSchema
from siliconcompiler.schema import NamedSchema, BaseSchema

from siliconcompiler.schema import EditableSchema, Parameter, Scope, PerNode, LazyLoad
from siliconcompiler.schema.utils import trim


if TYPE_CHECKING:
    from siliconcompiler import PDK


class LibrarySchema(FileSetSchema, NamedSchema):
    """
    A class for managing library schemas.
    """
    def __init__(self, name: Optional[str] = None):
        """
        Initializes a LibrarySchema object.

        Args:
            name (str, optional): The name of the library. Defaults to None.
        """
        super().__init__()
        self.set_name(name)

        package = PackageSchema()
        EditableSchema(package).remove("dataroot")
        EditableSchema(self).insert("package", package)

    @property
    def package(self) -> PackageSchema:
        """
        Gets the package schema for the library.

        Returns:
            PackageSchema: The package schema associated with this library.
        """
        return self.get("package", field="schema")

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict.
        """

        return LibrarySchema.__name__


class ToolLibrarySchema(LibrarySchema):
    """
    A class for managing tool-related library schemas.
    """
    @final
    def define_tool_parameter(self, tool: str, name: str, type: str, help: str, **kwargs):
        """
        Define a new tool parameter for the library.

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

            if not help:
                raise ValueError("help is required")

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
        Returns the meta data for getdict.
        """

        return ToolLibrarySchema.__name__

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        """
        Constructs a schema from a dictionary.

        Args:
            manifest (dict): Dictionary to construct from.
            keypath (list): List of keys representing the path to the current dictionary.
            version (str, optional): Version of the manifest. Defaults to None.

        Returns:
            dict: The constructed dictionary.
        """
        if not lazyload.is_enforced and "tool" in manifest:
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
                                keypath=list(keypath) + [tool, var],
                                version=version))
                del manifest["tool"][tool][var]
                if not manifest["tool"][tool]:
                    del manifest["tool"][tool]

            if not manifest["tool"]:
                del manifest["tool"]

        return super()._from_dict(manifest, keypath, version=version, lazyload=lazyload)

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from .schema.docs.utils import build_section, strong, KeyPath, code, para, build_table
        from docutils import nodes

        if not key_offset:
            key_offset = tuple()

        tools_added = False
        if "tool" in self.getkeys():
            tools_sec = build_section("Tools", f"{ref_root}-tools")
            for tool in self.getkeys("tool"):
                tool_sec = build_section(tool, f"{ref_root}-tools-{tool}")

                # Show var definitions
                with KeyPath.fallback(...):
                    table = [[strong('Parameters'), strong('Type'), strong('Help')]]
                    for key in self.getkeys("tool", tool):
                        key_node = nodes.paragraph()
                        key_node += KeyPath.keypath(
                            list(key_offset) + list(self._keypath) +
                            ["tool", tool, key],
                            doc.env.docname)
                        table.append([
                            key_node,
                            code(self.get("tool", tool, key, field="type")),
                            para(self.get("tool", tool, key, field="help"))
                        ])
                if len(table) > 1:
                    tool_defs = build_section("Variables", f"{ref_root}-tools-{tool}-defns")
                    colspec = r'{|\X{2}{5}|\X{1}{5}|\X{2}{5}|}'
                    tool_defs += build_table(table, colspec=colspec)
                    tool_sec += tool_defs

                with KeyPath.fallback(...):
                    tool_param = BaseSchema._generate_doc(
                        self.get("tool", tool, field="schema"),
                        doc,
                        ref_root=f"{ref_root}-tools-{tool}-configs",
                        key_offset=key_offset,
                        detailed=False)

                if not tool_param:
                    continue

                tool_cfg = build_section("Configuration", f"{ref_root}-tools-{tool}-configs")
                tool_cfg += tool_param
                tool_sec += tool_cfg
                tools_sec += tool_sec
                tools_added = True

        if tools_added:
            return tools_sec
        return None


class StdCellLibrary(DependencySchema, ToolLibrarySchema):
    """
    A class for managing standard cell library schemas.
    """
    def __init__(self, name: Optional[str] = None):
        """
        Initializes a StdCellLibrary object.

        Args:
            name (str, optional): The name of the standard cell library. Defaults to None.
        """
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
            "asic", "stackup",
            Parameter(
                "{str}",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: ",
                example=[
                    "api: schema.set('asic', 'libcornerfileset', 'slow', 'nldm', 'timing.slow')"],
                help=trim("""Set of supported stackups""")))

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

    def add_asic_pdk(self, pdk: Union[str, "PDK"], default: bool = True):
        """
        Adds the PDK associated with this library.

        Args:
            pdk (class:`PDK`): pdk to associate
            default (bool): if True, sets this PDK in [asic,pdk]
        """
        from siliconcompiler import PDK
        if isinstance(pdk, PDK):
            pdk_name = pdk.name
            self.add_dep(pdk)

            if pdk.get("pdk", "stackup"):
                # copy over stackup information
                self.add_asic_stackup(pdk.get("pdk", "stackup"))
        elif default:
            if isinstance(pdk, str):
                pdk_name = pdk
            else:
                raise TypeError("pdk must be a PDK object or string")
        else:
            raise TypeError("pdk must be a PDK object")

        if default:
            return self.set("asic", "pdk", pdk_name)

    def add_asic_stackup(self, stackup: Union[str, List[str]]):
        """
        Set the stackups supported by this library.

        Args:
            stackup (str or list of str): stackups supported
        """
        return self.add("asic", "stackup", stackup)

    def add_asic_libcornerfileset(self,
                                  corner: str,
                                  model: str,
                                  fileset: Optional[Union[List[str], str]] = None):
        """
        Adds a mapping between filesets a corners defined in the library.

        Args:
            corner (str): name of the timing or parasitic corner
            model (str): type of delay modeling used, eg. ccs, nldm, etc.
            fileset (str): name of the fileset
        """
        if not fileset:
            fileset = self._get_active("fileset")

        if not isinstance(model, str):
            raise TypeError("model must be a string")

        self._assert_fileset(fileset)

        return self.add("asic", "libcornerfileset", corner, model, fileset)

    def add_asic_pexcornerfileset(self, corner: str,
                                  fileset: Optional[Union[List[str], str]] = None):
        """
        Adds a mapping between filesets a corners defined in the library.

        Args:
            corner (str): name of the timing or parasitic corner
            fileset (str): name of the fileset
        """
        if not fileset:
            fileset = self._get_active("fileset")

        self._assert_fileset(fileset)

        return self.add("asic", "pexcornerfileset", corner, fileset)

    def add_asic_aprfileset(self, fileset: str = None):
        """
        Adds a mapping between filesets defined in the library.

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
        Adds a standard site to the library.

        Args:
            site (list of str or str): sites to add
        """
        return self.add("asic", "site", site)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict.
        """

        return StdCellLibrary.__name__

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from .schema.docs.utils import build_section
        docs = []

        if not key_offset:
            key_offset = ("StdCellLibrary",)

        # Show dataroot
        dataroot = PathSchema._generate_doc(self, doc, ref_root=ref_root, key_offset=key_offset)
        if dataroot:
            docs.append(dataroot)

        # Show package information
        package = self.package._generate_doc(doc, ref_root=ref_root, key_offset=key_offset)
        if package:
            docs.append(package)

        # Show filesets
        fileset = FileSetSchema._generate_doc(self, doc, ref_root=ref_root, key_offset=key_offset)
        if fileset:
            docs.append(fileset)

        # Show ASIC
        asic_sec = build_section("ASIC", f"{ref_root}-asic")
        asic_sec += BaseSchema._generate_doc(self.get("asic", field="schema"),
                                             doc,
                                             ref_root=f"{ref_root}-asic",
                                             key_offset=key_offset,
                                             detailed=False)
        docs.append(asic_sec)

        # Show tool information
        tools_sec = ToolLibrarySchema._generate_doc(self, doc,
                                                    ref_root=ref_root,
                                                    key_offset=key_offset)
        if tools_sec:
            docs.append(tools_sec)

        return docs
