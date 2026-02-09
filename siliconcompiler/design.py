import contextlib
import io
import os.path
from pathlib import Path

from typing import List, Set, Union, Tuple, Dict, Optional, Iterable

from siliconcompiler import utils

from siliconcompiler.schema_support.filesetschema import FileSetSchema
from siliconcompiler.schema_support.packageschema import PackageSchema
from siliconcompiler.schema_support.pathschema import PathSchema
from siliconcompiler.schema_support.dependencyschema import DependencySchema
from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema


###########################################################################
class Design(DependencySchema, PathSchema, NamedSchema):
    '''
    Schema for a 'design'.

    This class inherits from
    :class:`~siliconcompiler.schema_support.dependencyschema.DependencySchema` and
    :class:`~siliconcompiler.schema_support.filesetschema.FileSetSchema`, adds
    parameters and methods specific to describing a design, such as its top module,
    source filesets, and compilation settings.
    '''

    def __init__(self, name: Optional[str] = None):
        '''
        Initializes a new Design object.

        Args:
            name (str, optional): The name of the design. Defaults to None.
        '''
        super().__init__()

        self.set_name(name)

        edit = EditableSchema(self)

        edit.insert("fileset", "default", FileSetSchema())

        package = PackageSchema()
        EditableSchema(package).remove("dataroot")
        edit.insert("package", package)

    @property
    def package(self) -> PackageSchema:
        """
        Gets the package schema for the design.

        Returns:
            PackageSchema: The package schema associated with this design.
        """
        return self.get("package", field="schema")

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

    ###############################################
    def add_file(self,
                 filename: Union[List[Union[Path, str]], Set[Union[Path, str]],
                                 Tuple[Union[Path, str], ...], Path, str],
                 fileset: Optional[str] = None,
                 filetype: Optional[str] = None,
                 clobber: bool = False,
                 dataroot: Optional[str] = None) -> List[str]:
        """
        Adds files to a fileset.

        Based on the file's extension, this method can often infer the correct
        fileset and filetype. For example:

        * .v -> (source, verilog)
        * .vhd -> (source, vhdl)
        * .sdc -> (constraint, sdc)
        * .lef -> (input, lef)
        * .def -> (input, def)
        * etc.

        Args:
            filename (Path, str, or collection): File path (Path or str), or a collection
                (list, tuple, set) of file paths to add.
            fileset (str): Logical group to associate the file with.
            filetype (str, optional): Type of the file (e.g., 'verilog', 'sdc').
            clobber (bool, optional): If True, clears the list before adding the
                item. Defaults to False.
            dataroot (str, optional): Data directory reference name.

        Raises:
            ValueError: If `fileset` or `filetype` cannot be inferred from
                the file extension.

        Returns:
           list[str]: A list of the file paths that were added.

        Notes:
           * This method normalizes `filename` to a string for consistency.
           * If `filetype` is not specified, it is inferred from the
               file extension.
        """
        fs = self.__get_filesetobj(fileset)
        return fs.add_file(filename=filename, filetype=filetype, clobber=clobber, dataroot=dataroot)

    ###############################################
    def get_file(self,
                 fileset: Optional[str] = None,
                 filetype: Optional[str] = None) -> List[str]:
        """Returns a list of files from one or more filesets.

        Args:
            fileset (str or list[str]): Fileset(s) to query. If not provided,
                the active fileset is used.
            filetype (str or list[str], optional): File type(s) to filter by
                (e.g., 'verilog'). If not provided, all filetypes in the
                fileset are returned.

        Returns:
            list[str]: A list of resolved file paths.
        """

        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, list):
            fileset = [fileset]

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        filelist = []
        for fs in fileset:
            if not isinstance(fs, str):
                raise ValueError("fileset key must be a string")
            fsobj = self.__get_filesetobj(fs)
            filelist.extend(fsobj.get_file(filetype))

        return filelist

    ###############################################
    def has_file(self, fileset: Optional[str] = None, filetype: Optional[str] = None) -> bool:
        """Returns true if the fileset contains files.

        Args:
            fileset (str or list[str]): Fileset(s) to query. If not provided,
                the active fileset is used.
            filetype (str or list[str], optional): File type(s) to filter by
                (e.g., 'verilog'). If not provided, all filetypes in the
                fileset are returned.

        Returns:
            bool: True if the fileset contains files.
        """

        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, list):
            fileset = [fileset]

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        for fs in fileset:
            if not isinstance(fs, str):
                raise ValueError("fileset key must be a string")
            if not self.has_fileset(fs):
                continue
            fsobj = self.__get_filesetobj(fs)
            if fsobj.has_file(filetype):
                return True

        return False

    def __get_filesetobj(self, fileset: Optional[str]) -> FileSetSchema:
        if fileset is None:
            fileset = self._get_active("fileset")

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")

        return self.get("fileset", fileset, field="schema")

    @contextlib.contextmanager
    def active_fileset(self, fileset: str):
        """
        Provides a context to temporarily set an active design fileset.

        This is useful for applying a set of configurations to a specific
        fileset without repeatedly passing its name.

        Raises:
            TypeError: If `fileset` is not a string.
            ValueError: If `fileset` is an empty string.

        Args:
            fileset (str): The name of the fileset to activate.

        Example:
            >>> with design.active_fileset("rtl"):
            ...     design.set_topmodule("top")
            # This sets the top module for the 'rtl' fileset to 'top'.
        """
        if not isinstance(fileset, str):
            raise TypeError("fileset must a string")
        if not fileset:
            raise ValueError("fileset cannot be an empty string")

        with self._active(fileset=fileset):
            yield

    def copy_fileset(self, src_fileset: str, dst_fileset: str, clobber: bool = False) -> None:
        """
        Creates a new copy of a source fileset.

        The entire configuration of the source fileset is duplicated and stored
        under the destination fileset's name.

        Args:
            src_fileset (str): The name of the source fileset to copy.
            dst_fileset (str): The name of the new destination fileset.
            clobber (bool): If True, an existing destination fileset will be
                overwritten. Defaults to False.

        Raises:
            ValueError: If the destination fileset already exists and `clobber`
                is False.
        """
        if not clobber and self.has_fileset(dst_fileset):
            raise ValueError(f"{dst_fileset} already exists")

        new_fs = self.__get_filesetobj(src_fileset).copy()
        EditableSchema(self).insert("fileset", dst_fileset, new_fs, clobber=True)

    def _assert_fileset(self, fileset: Union[None, Iterable[str], str]) -> None:
        """
        Raises an error if the specified fileset does not exist.

        Raises:
            TypeError: If `fileset` is not a string.
            LookupError: If the fileset is not found.
        """

        if isinstance(fileset, (list, set, tuple)):
            for fs in fileset:
                self._assert_fileset(fs)
            return

        if not isinstance(fileset, str):
            raise TypeError("fileset must be a string")

        if not self.has_fileset(fileset):
            name = getattr(self, "name", None)
            if name:
                raise LookupError(f"{fileset} is not defined in {name}")
            else:
                raise LookupError(f"{fileset} is not defined")

    def has_fileset(self, fileset: str) -> bool:
        """
        Checks if a fileset exists in the schema.

        Args:
            fileset (str): The name of the fileset to check.

        Returns:
            bool: True if the fileset exists, False otherwise.
        """

        return fileset in self.getkeys("fileset")

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
        fs = self.__get_filesetobj(fileset)
        return fs.set_topmodule(value)

    def get_topmodule(self, fileset: Optional[str] = None) -> str:
        """Returns the topmodule of a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           str: Topmodule name
        """
        fs = self.__get_filesetobj(fileset)
        return fs.get_topmodule()

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
        fs = self.__get_filesetobj(fileset)
        return fs.add_idir(value, clobber=clobber, dataroot=dataroot)

    def get_idir(self, fileset: Optional[str] = None) -> List[str]:
        """Returns include directories for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[str]: List of include directories
        """
        fs = self.__get_filesetobj(fileset)
        return fs.get_idir()

    def has_idir(self, fileset: Optional[str] = None) -> bool:
        """Returns true if idirs are defined for the fileset

        Args:
            fileset (str or list[str]): Fileset(s) to query. If not provided,
                the active fileset is used.

        Returns:
            bool: True if the fileset contains directories.
        """
        return self.__get_filesetobj(fileset).has_idir()

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
        fs = self.__get_filesetobj(fileset)
        return fs.add_define(value, clobber=clobber)

    def get_define(self, fileset: Optional[str] = None) -> List[str]:
        """Returns defined macros for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[str]: List of macro definitions
        """
        fs = self.__get_filesetobj(fileset)
        return fs.get_define()

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
        fs = self.__get_filesetobj(fileset)
        return fs.add_undefine(value, clobber=clobber)

    def get_undefine(self, fileset: Optional[str] = None) -> List[str]:
        """Returns undefined macros for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

       Returns:
           list[str]: List of macro (un)definitions

        """
        fs = self.__get_filesetobj(fileset)
        return fs.get_undefine()

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
        fs = self.__get_filesetobj(fileset)
        return fs.add_libdir(value, clobber=clobber, dataroot=dataroot)

    def get_libdir(self, fileset: Optional[str] = None) -> List[str]:
        """Returns dynamic library directories for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[str]: List of library directories.
        """
        fs = self.__get_filesetobj(fileset)
        return fs.get_libdir()

    def has_libdir(self, fileset: Optional[str] = None) -> bool:
        """Returns true if library directories are defined for the fileset

        Args:
            fileset (str or list[str]): Fileset(s) to query. If not provided,
                the active fileset is used.

        Returns:
            bool: True if the fileset contains directories.
        """
        return self.__get_filesetobj(fileset).has_libdir()

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
        fs = self.__get_filesetobj(fileset)
        return fs.add_lib(value, clobber=clobber)

    def get_lib(self, fileset: Optional[str] = None) -> List[str]:
        """Returns list of dynamic libraries for a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[str]: List of libraries.
        """
        fs = self.__get_filesetobj(fileset)
        return fs.get_lib()

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
        fs = self.__get_filesetobj(fileset)
        return fs.set_param(name, value)

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
        fs = self.__get_filesetobj(fileset)
        return fs.get_param(name)

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
        fs = self.__get_filesetobj(fileset)
        return fs.add_depfileset(dep, depfileset)

    def get_depfileset(self, fileset: Optional[str] = None):
        """
        Returns list of dependency filesets.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           list[tuple(str, str)]: List of dependencies and filesets.
        """
        fs = self.__get_filesetobj(fileset)
        return fs.get_depfileset()

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

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from .schema.docs.utils import build_section

        filesets_sec = build_section("Filesets", f"{ref_root}-filesets")
        filesets_added = False
        for fileset in self.getkeys("fileset"):
            fs = self.__get_filesetobj(fileset)
            fileset_sec = fs._generate_doc(doc,
                                           ref_root=ref_root,
                                           key_offset=key_offset,
                                           detailed=detailed)
            if fileset_sec:
                filesets_sec += fileset_sec
                filesets_added = True

        if not filesets_added:
            return None

        return filesets_sec
