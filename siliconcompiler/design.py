import io
import re
import os.path
from pathlib import Path

from typing import List, Union, Tuple, Dict, Optional, Iterable, Type

from siliconcompiler import utils

from siliconcompiler.library import LibrarySchema

from siliconcompiler.schema_support.dependencyschema import DependencySchema
from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


###########################################################################
class Design(DependencySchema, LibrarySchema):
    '''
    Schema for a 'design'.

    This class inherits from :class:`~siliconcompiler.LibrarySchema` and
    :class:`~siliconcompiler.DependencySchema`, and adds parameters and methods
    specific to describing a design, such as its top module, source filesets,
    and compilation settings.
    '''

    def __init__(self, name: Optional[str] = None):
        '''
        Initializes a new Design object.

        Args:
            name (str, optional): The name of the design. Defaults to None.
        '''
        super().__init__()

        # Mark for copy to ensure proper remote processing
        fs_file: Parameter = self.get("fileset", "default", "file", "default", field=None)
        fs_file.set(True, field="copy")

        self.set_name(name)

        schema_design(self)

    def add_dep(self, obj: NamedSchema, clobber: bool = True) -> bool:
        '''
        Adds a module dependency to this design.

        This method extends the base `add_dep` to prevent a design from
        adding a dependency on itself.

        Args:
            obj (NamedSchema): The dependency object to add.
            clobber (bool): If True, overwrite an existing dependency with the
                same name.

        Returns:
            bool: True if the dependency was added, False otherwise.

        Raises:
            TypeError: If `obj` is not a `NamedSchema`.
            ValueError: If `obj` has the same name as the current design.
        '''
        if not isinstance(obj, NamedSchema):
            raise TypeError(f"Cannot add an object of type: {type(obj)}")

        if obj.name == self.name:
            raise ValueError("Cannot add a dependency with the same name")

        return super().add_dep(obj, clobber=clobber)

    ############################################
    def set_topmodule(self,
                      value: str,
                      fileset: Optional[str] = None) -> str:
        """Sets the topmodule of a fileset.

        Args:
           value (str): Topmodule name.
           fileset (str, optional): Fileset name. If not provided, the active
            fileset is used.

        Returns:
           str: Topmodule name

        Notes:
            - first character must be letter or underscore
            - remaining characters can be letters, digits, or underscores
        """

        # topmodule safety check
        if (value is not None) and isinstance(value, str):
            if not re.match(r'^[_a-zA-Z]\w*$', value):
                raise ValueError(f"{value} is not a legal topmodule string")

        return self.__set_add(fileset, 'topmodule', value, typelist=[str])

    def get_topmodule(self, fileset: Optional[str] = None) -> str:
        """Returns the topmodule of a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           str: Topmodule name
        """
        return self.__get(fileset, 'topmodule')

    ##############################################
    def add_idir(self,
                 value: str,
                 fileset: Optional[str] = None,
                 clobber: bool = False,
                 dataroot: Optional[str] = None) -> List[str]:
        """Adds include directories to a fileset.

        Args:
           value (Path or list[Path]): Include path(s).
           fileset (str, optional): Fileset name. If not provided, the active
            fileset is used.
           clobber (bool, optional): Clears existing list before adding item.
           dataroot (str, optional): Data directory reference name.

        Returns:
           list[str]: List of include directories
        """
        return self.__set_add(fileset, 'idir', value, clobber,
                              typelist=[str, list, Path],
                              dataroot=dataroot)

    def get_idir(self, fileset: Optional[str] = None) -> List[str]:
        """Returns include directories for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[str]: List of include directories
        """
        return self.__get(fileset, 'idir', is_file=True)

    def has_idir(self, fileset: Optional[str] = None) -> bool:
        """Returns true if idirs are defined for the fileset

        Args:
            fileset (str or list[str]): Fileset(s) to query. If not provided,
                the active fileset is used.

        Returns:
            bool: True if the fileset contains directories.
        """
        return bool(self.__get(fileset, 'idir', is_file=False))

    ##############################################
    def add_define(self,
                   value: str,
                   fileset: Optional[str] = None,
                   clobber: bool = False) -> List[str]:
        """Adds preprocessor macro definitions to a fileset.

        Args:
           value (str or List[str]): Macro definition.
           fileset (str, optional): Fileset name. If not provided, the active
            fileset is used.
           clobber (bool, optional): Clears existing list before adding item.

        Returns:
           list[str]: List of macro definitions

        """
        return self.__set_add(fileset, 'define', value, clobber, typelist=[str, list])

    def get_define(self, fileset: Optional[str] = None) -> List[str]:
        """Returns defined macros for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[str]: List of macro definitions
        """
        return self.__get(fileset, 'define')

    ##############################################
    def add_undefine(self,
                     value: str,
                     fileset: Optional[str] = None,
                     clobber: bool = False) -> List[str]:
        """Adds preprocessor macro (un)definitions to a fileset.

        Args:
           value (str or List[str]): Macro (un)definition.
           fileset (str, optional): Fileset name. If not provided, the active
            fileset is used.
           clobber (bool, optional): Clears existing list before adding item.

        Returns:
           list[str]: List of macro (un)definitions
        """
        return self.__set_add(fileset, 'undefine', value, clobber, typelist=[str, list])

    def get_undefine(self, fileset: Optional[str] = None) -> List[str]:
        """Returns undefined macros for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

       Returns:
           list[str]: List of macro (un)definitions

        """
        return self.__get(fileset, 'undefine')

    ###############################################
    def add_libdir(self,
                   value: str,
                   fileset: Optional[str] = None,
                   clobber: bool = False,
                   dataroot: Optional[str] = None) -> List[str]:
        """Adds dynamic library directories to a fileset.

        Args:
           value (Path or list[Path]): Library path(s).
           fileset (str, optional): Fileset name. If not provided, the active
            fileset is used.
           clobber (bool, optional): Clears existing list before adding item.
           dataroot (str, optional): Data directory reference name.

        Returns:
           list[str]: List of library directories.
        """
        return self.__set_add(fileset, 'libdir', value, clobber,
                              typelist=[str, list, Path],
                              dataroot=dataroot)

    def get_libdir(self, fileset: Optional[str] = None) -> List[str]:
        """Returns dynamic library directories for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[str]: List of library directories.
        """
        return self.__get(fileset, 'libdir', is_file=True)

    def has_libdir(self, fileset: Optional[str] = None) -> bool:
        """Returns true if library directories are defined for the fileset

        Args:
            fileset (str or list[str]): Fileset(s) to query. If not provided,
                the active fileset is used.

        Returns:
            bool: True if the fileset contains directories.
        """
        return bool(self.__get(fileset, 'libdir', is_file=False))

    ###############################################
    def add_lib(self,
                value: str,
                fileset: Optional[str] = None,
                clobber: bool = False) -> List[str]:
        """Adds dynamic libraries to a fileset.

        Args:
           value (str or List[str]): Libraries.
           fileset (str, optional): Fileset name. If not provided, the active
            fileset is used.
           clobber (bool, optional): Clears existing list before adding item.

        Returns:
           list[str]: List of libraries.
        """
        return self.__set_add(fileset, 'lib', value, clobber, typelist=[str, list])

    def get_lib(self, fileset: Optional[str] = None) -> List[str]:
        """Returns list of dynamic libraries for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[str]: List of libraries.
        """
        return self.__get(fileset, 'lib')

    ###############################################
    def set_param(self,
                  name: str,
                  value: str,
                  fileset: Optional[str] = None) -> str:
        """Sets a named parameter for a fileset.

        Args:
            name (str): Parameter name.
            value (str): Parameter value.
            fileset (str, optional): Fileset name. If not provided, the active
                fileset is used.

        Returns:
            str: Parameter value
        """

        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")

        if not isinstance(value, str) or value is None:
            raise ValueError("param value must be a string")

        return self.set('fileset', fileset, 'param', name, value)

    def get_param(self,
                  name: str,
                  fileset: Optional[str] = None) -> str:
        """Returns value of a named fileset parameter.

        Args:
           name (str): Parameter name.
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
            str: Parameter value
        """
        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")
        return self.get('fileset', fileset, 'param', name)

    ###############################################
    def add_depfileset(self, dep: Union["Design", str],
                       depfileset: Optional[str] = None,
                       fileset: Optional[str] = None):
        """
        Record a reference to an imported dependency's fileset.

        Args:
           dep (:class:`Design` or str): Dependency name or object.
           depfileset (str): Dependency fileset, if not specified, the fileset will
            default to the same as the fileset or if only one fileset is present in
            the dep that will be chosen.
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        """
        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")

        if isinstance(dep, str):
            dep_name = dep
            if dep_name != self.name:
                dep = self.get_dep(dep_name)
            else:
                dep = self
        elif isinstance(dep, Design):
            dep_name = dep.name
            if dep is not self:
                self.add_dep(dep, clobber=True)
        else:
            raise TypeError(f"dep is not a valid type: {dep}")

        if not isinstance(dep, Design):
            raise ValueError(f"cannot associate fileset ({depfileset}) with {dep.name}")

        if depfileset is None:
            if dep.has_fileset(fileset):
                depfileset = fileset
            else:
                filesets = dep.getkeys("fileset")
                if len(filesets) == 1:
                    depfileset = filesets[0]
                else:
                    raise ValueError(f"depfileset must be specified for {dep.name}")

        if not dep.has_fileset(depfileset):
            raise ValueError(f"{dep.name} does not have {depfileset} as a fileset")

        return self.add("fileset", fileset, "depfileset", (dep_name, depfileset))

    def get_depfileset(self, fileset: Optional[str] = None):
        """
        Returns list of dependency filesets.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[tuple(str, str)]: List of dependencies and filesets.
        """
        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")

        return self.get("fileset", fileset, "depfileset")

    def __write_flist(self,
                      filename: str,
                      filesets: Union[List[str], str],
                      depalias: Optional[Dict[Tuple[str, str], Tuple[NamedSchema, str]]],
                      comments: bool = False):
        '''
        Internal helper to write a Verilog-style file list (`.f` file).

        This method iterates through the specified filesets (and their
        dependencies), writing out `+incdir+`, `+define+`, and source file
        paths.

        Args:
            filename (str): The path to the output file list.
            filesets (List[str]): A list of fileset names to include.
            depalias (Dict): A dictionary for aliasing dependencies.
            comments (bool, optional): Add comments in output file.
        '''
        written_cmd = set()

        content = io.StringIO()

        def write(cmd):
            if cmd in written_cmd:
                content.write(f"// {cmd}\n")
            else:
                written_cmd.add(cmd)
                content.write(f"{cmd}\n")

        def write_header(header):
            content.write(f"// {header}\n")

        for lib, fileset in self.get_fileset(filesets, depalias):
            if lib.get('fileset', fileset, 'idir'):
                if (comments):
                    write_header(f"{lib.name} / {fileset} / include directories")
                for idir in lib.find_files('fileset', fileset, 'idir'):
                    write(f"+incdir+{idir}")

            if lib.get('fileset', fileset, 'define'):
                if (comments):
                    write_header(f"{lib.name} / {fileset} / defines")
                for define in lib.get('fileset', fileset, 'define'):
                    write(f"+define+{define}")

            for filetype in lib.getkeys('fileset', fileset, 'file'):
                if lib.get('fileset', fileset, 'file', filetype):
                    if (comments):
                        write_header(f"{lib.name} / {fileset} / {filetype} files")
                    for file in lib.find_files('fileset', fileset, 'file', filetype):
                        write(file)

        with open(filename, "w") as f:
            f.write(content.getvalue())

    def __map_fileformat(self, path: str) -> str:
        '''
        Internal helper to determine file format from a file extension.

        Args:
            path (str): The file path.

        Returns:
            str: The determined file format (e.g., "flist").

        Raises:
            ValueError: If the file format cannot be determined from the
                extension.
        '''
        _, ext = os.path.splitext(path)

        if ext == ".f":
            return "flist"
        else:
            raise ValueError(f"Unable to determine filetype of: {path}")

    ###############################################
    def write_fileset(self,
                      filename: str,
                      fileset: Optional[Union[Iterable[str], str]] = None,
                      fileformat: Optional[str] = None,
                      depalias: Optional[Dict[Tuple[str, str], Tuple[NamedSchema, str]]] = None,
                      comments: bool = False) -> None:
        """Exports filesets to a standard formatted text file.

        Currently supports Verilog `flist` format only.
        Intended to support other formats in the future.
        Inferred from file extension if not given.

        Args:
            filename (str or Path): Output file name.
            fileset (str or list[str]): Fileset(s) to export. If not provided,
                the active fileset is used.
            fileformat (str, optional): Export format.
            depalias (dict of schema objects): Map of aliased objects.
            comments (bool, optional): Add comments in output file.
        """

        if filename is None:
            raise ValueError("filename cannot be None")

        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, list):
            fileset = [fileset]

        for fset in fileset:
            if not isinstance(fset, str):
                raise ValueError("fileset key must be a string")

        # file extension lookup
        if not fileformat:
            fileformat = self.__map_fileformat(filename)

        if fileformat == "flist":
            self.__write_flist(filename, fileset, depalias, comments)
        else:
            raise ValueError(f"{fileformat} is not a supported filetype")

    def __read_flist(self, filename: str, fileset: str):
        '''
        Internal helper to read a Verilog-style file list (`.f` file).

        This method parses the file list for `+incdir+`, `+define+`, and
        source files, and populates the specified fileset in the schema.

        Args:
            filename (str): The path to the input file list.
            fileset (str): The name of the fileset to populate.
        '''
        # Extract information
        rel_path = os.path.dirname(os.path.abspath(filename))

        def expand_path(path):
            path = os.path.expandvars(path)
            path = os.path.expanduser(path)
            if os.path.isabs(path):
                return path
            return os.path.join(rel_path, path)

        include_dirs = []
        defines = []
        files = []
        with utils.sc_open(filename) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("//"):
                    continue
                if line.startswith("+incdir+"):
                    include_dirs.append(expand_path(line[8:]))
                elif line.startswith("+define+"):
                    defines.append(os.path.expandvars(line[8:]))
                else:
                    files.append(expand_path(line))

        # Create dataroots
        all_paths = include_dirs + [os.path.dirname(f) for f in files]
        all_paths = sorted(set(all_paths))

        dataroot_root_name = f'flist-{self.name}-{fileset}-{os.path.basename(filename)}'
        dataroots = {}

        for path_dir in all_paths:
            found = False
            for pdir in dataroots:
                if path_dir.startswith(pdir):
                    found = True
                    break
            if not found:
                dataroot_name = f"{dataroot_root_name}-{len(dataroots)}"
                self.set_dataroot(dataroot_name, path_dir)
                dataroots[path_dir] = dataroot_name

        def get_dataroot(path: str) -> Tuple[Optional[str], Optional[str]]:
            for pdir, name in dataroots.items():
                if path.startswith(pdir):
                    return name, pdir
            return None, None

        # Assign data
        with self.active_fileset(fileset):
            if defines:
                self.add_define(defines)
            if include_dirs:
                for dir in include_dirs:
                    dataroot_name, pdir = get_dataroot(dir)
                    if dataroot_name:
                        dir = os.path.relpath(dir, pdir)
                    self.add_idir(dir, dataroot=dataroot_name)
            if files:
                for f in files:
                    dataroot_name, pdir = get_dataroot(f)
                    if dataroot_name:
                        f = os.path.relpath(f, pdir)
                    self.add_file(f, dataroot=dataroot_name)

    ################################################
    def read_fileset(self,
                     filename: str,
                     fileset: Optional[str] = None,
                     fileformat: Optional[str] = None) -> None:
        """Imports filesets from a standard formatted text file.

        Currently supports Verilog `flist` format only.
        Intended to support other formats in the future.

        Args:
            filename (str or Path): Input file name.
            fileset (str or list[str]): Fileset to import into. If not
                provided, the active fileset is used.
            fileformat (str, optional): Import format. Inferred from file
                extension if not provided.
        """

        if filename is None:
            raise ValueError("filename cannot be None")

        if not fileformat:
            fileformat = self.__map_fileformat(filename)

        if fileset is None:
            fileset = self._get_active("fileset")

        if fileformat == "flist":
            self.__read_flist(filename, fileset)
        else:
            raise ValueError(f"{fileformat} is not a supported filetype")

    ################################################
    # Helper Functions
    ################################################
    def __set_add(self,
                  fileset: str,
                  option: str,
                  value: Union[List[str], str],
                  clobber: bool = False,
                  typelist: Optional[List[Union[Type[str], Type[List], Type[Path]]]] = None,
                  dataroot: Optional[str] = ...):
        '''
        Internal helper to set or add a parameter value in the schema.

        This function handles common tasks for setters like `add_idir` and
        `add_define`, such as resolving the active fileset, checking value
        types, and calling the underlying schema `set()` or `add()` methods.

        Args:
            fileset (str): The fileset to modify.
            option (str): The parameter key to modify.
            value: The value to set or add.
            clobber (bool): If True, overwrite the existing value.
            typelist (list): A list of allowed types for the value.
            dataroot (str): The dataroot to associate with the value.
        '''

        if fileset is None:
            fileset = self._get_active("fileset")

        # check for a legal fileset
        if not fileset or not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")

        # Check for legal types
        legalval = False
        for item in typelist:
            if isinstance(value, item) and not isinstance(value, tuple):
                legalval = True
        if not legalval:
            raise ValueError("value must be of type string")

        # None is illegal for all setters
        if value is None:
            raise ValueError(f"None is an illegal {option} value")

        # Handling string like objects (like Path)
        value = [str(x) for x in value] if isinstance(value, list) else [str(value)]

        if dataroot is ...:
            dataroot = None
        else:
            dataroot = self._get_active_dataroot(dataroot)

        with self.active_dataroot(dataroot):
            if list in typelist and not clobber:
                params = self.add('fileset', fileset, option, value)
            else:
                params = self.set('fileset', fileset, option, value)

        return params

    def __get(self, fileset: Optional[str], option: str, is_file: bool = False) -> List[str]:
        '''
        Internal helper to get a parameter value from the schema.

        This function handles common tasks for getters, such as resolving the
        active fileset and optionally resolving file paths.

        Args:
            fileset (str): The fileset to query.
            option (str): The parameter key to retrieve.
            is_file (bool): If True, treat the value as a file path and
                resolve it using `find_files`.
        '''
        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")
        if is_file:
            return self.find_files('fileset', fileset, option)
        return self.get('fileset', fileset, option)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict.

        This is used to identify the object type during serialization.
        """

        return Design.__name__

    def __get_fileset(self,
                      filesets: Union[List[str], str],
                      alias: Dict[Tuple[str, str], Tuple[NamedSchema, str]],
                      mapping: List[Tuple[NamedSchema, str]]) -> \
            List[Tuple[NamedSchema, str]]:
        """
        Private recursive method to compute the full list of (design, fileset)
        tuples required for a given set of top-level filesets.

        This method traverses the design's dependency graph.

        Args:
            filesets (Union[List[str], str]): List of top-level filesets to evaluate.
            alias (Dict[Tuple[str, str], Tuple[NamedSchema, str]]): Map of aliased
                (design, fileset) tuples to substitute during traversal.
            mapping (List[Tuple[NamedSchema, str]]): Internal list used to track
                visited (design, fileset) nodes during recursion.

        Returns:
            List[Tuple[NamedSchema, str]]: A flattened, unique list of
            (Design, fileset) tuples.
        """
        if isinstance(filesets, str):
            # Ensure we have a list
            filesets = [filesets]

        for fileset in filesets:
            self._assert_fileset(fileset)

            if (self, fileset) in mapping:
                continue

            mapping.append((self, fileset))
            for dep, depfileset in self.get("fileset", fileset, "depfileset"):
                if (dep, depfileset) in alias:
                    dep_obj, new_depfileset = alias[(dep, depfileset)]
                    if dep_obj is None:
                        continue

                    if new_depfileset:
                        depfileset = new_depfileset
                else:
                    if dep == self.name:
                        dep_obj = self
                    else:
                        dep_obj = self.get_dep(dep)
                if not isinstance(dep_obj, Design):
                    raise TypeError(f"{dep} must be a design object.")

                mapping.extend(dep_obj.__get_fileset(depfileset, alias, mapping))

        # Cleanup
        final_map = []
        for cmap in mapping:
            if cmap not in final_map:
                final_map.append(cmap)
        return final_map

    def get_fileset(self,
                    filesets: Union[List[str], str],
                    alias: Optional[Dict[Tuple[str, str], Tuple[NamedSchema, str]]] = None) -> \
            List[Tuple[NamedSchema, str]]:
        """
        Computes the full, recursive list of (design, fileset) tuples
        required for a given set of top-level filesets.

        This method traverses the design's dependency graph to resolve all
        `depfileset` entries, returning a flattened and unique list of all
        required sources.

        Args:
            filesets (Union[List[str], str]): A single fileset name or a list of
                fileset names to evaluate.
            alias (Dict[Tuple[str, str], Tuple[NamedSchema, str]], optional): A dictionary
                mapping (design_name, fileset_name) tuples to be substituted during
                traversal. The value should be a (Design object, new_fileset_name)
                tuple. This is useful for swapping out library implementations.
                Defaults to None.

        Returns:
            List[Tuple[NamedSchema, str]]: A flattened, unique list of
            (Design, fileset) tuples representing all dependencies.
        """
        if alias is None:
            alias = {}

        return self.__get_fileset(filesets, alias, [])


###########################################################################
# Schema
###########################################################################
def schema_design(schema: Design):
    '''
    Defines the schema parameters specific to a design.

    This function is called by the `Design` constructor to set up
    its unique schema elements, such as `topmodule`, `idir`, `define`, etc.,
    under the `fileset` key.

    Args:
        schema (Design): The schema object to configure.
    '''

    edit = EditableSchema(schema)

    fileset = 'default'

    ###########################
    # Options
    ###########################

    edit.insert(
        'fileset', fileset, 'topmodule',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Top module name",
            example=[
                "api: design.set('fileset', 'rtl', 'topmodule', 'mytop')",
                "api: design.set('fileset', 'testbench', 'topmodule', 'tb')"],
            help=trim("""
            Name of top module specified on a per fileset basis.""")))

    edit.insert(
        'fileset', fileset, 'idir',
        Parameter(
            ['dir'],
            scope=Scope.GLOBAL,
            copy=True,
            shorthelp="Include file search paths",
            example=[
                "api: design.set('fileset', 'rtl', 'idir', './rtl')",
                "api: design.set('fileset', 'testbench', 'idir', '/testbench')"],
            help=trim("""
            Include paths specify directories to scan for header files during
            compilation. If multiple paths are provided, they are searched
            in the order given.""")))

    edit.insert(
        'fileset', fileset, 'define',
        Parameter(
            ['str'],
            scope=Scope.GLOBAL,
            shorthelp="Preprocessor macro definitions",
            example=[
                "api: design.set('fileset', 'rtl', 'define', 'CFG_TARGET=FPGA')"],
            help=trim("""
            Defines macros at compile time for design languages that support
            preprocessing, such as Verilog, C, and C++. The macro format is
            is `MACRONAME[=value]`, where [=value] is optional.""")))

    edit.insert(
        'fileset', fileset, 'undefine',
        Parameter(
            ['str'],
            scope=Scope.GLOBAL,
            shorthelp="Preprocessor macro undefine",
            example=[
                "api: design.set('fileset', 'rtl', 'undefine', 'CFG_TARGET')"],
            help=trim("""
            Undefines a macro that may have been previously defined via the
            compiler, options, or header files.""")))

    edit.insert(
        'fileset', fileset, 'libdir',
        Parameter(
            ['dir'],
            scope=Scope.GLOBAL,
            copy=True,
            shorthelp="Library search paths",
            example=[
                "api: design.set('fileset', 'rtl', 'libdir', '/usr/lib')"],
            help=trim("""
            Specifies directories to scan for libraries provided with the
            :keypath:`Design,fileset,<fileset>,lib` parameter. If multiple paths are provided,
            they are searched based on the order of the libdir list.""")))

    edit.insert(
        'fileset', fileset, 'lib',
        Parameter(
            ['str'],
            scope=Scope.GLOBAL,
            shorthelp="Design libraries to include",
            example=[
                "api: design.set('fileset', 'rtl', 'lib', 'mylib')"],
            help=trim("""
            Specifies libraries to use during compilation. The compiler searches for
            library in the compiler standard library paths and in the
            paths specified by :keypath:`Design,fileset,<fileset>,libdir` parameter.""")))

    name = 'default'
    edit.insert(
        'fileset', fileset, 'param', name,
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Design parameters",
            example=[
                "api: design.set('fileset', 'rtl', 'param', 'N', '64')"],
            help=trim("""
            Sets a named parameter to a string value. The value is limited to basic
            data literals. The types of parameters and values supported is tightly
            coupled to tools being used. For example, in Verilog only integer
            literals (64'h4, 2'b0, 4) and strings are supported.""")))

    edit.insert(
        'fileset', fileset, 'depfileset',
        Parameter(
            '[(str,str)]',
            scope=Scope.GLOBAL,
            shorthelp="Design dependency fileset",
            example=[
                "api: design.set('fileset', 'rtl', 'depfileset', ('lambdalib', 'rtl'))"],
            help=trim("""Sets the mapping for dependency filesets.""")))
