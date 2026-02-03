import re

import os.path

from pathlib import Path

from typing import List, Tuple, Optional, Union, Set, TYPE_CHECKING

from siliconcompiler import utils

from siliconcompiler.schema_support.pathschema import PathSchemaBase
from siliconcompiler.schema import EditableSchema, Parameter, Scope, BaseSchema, NamedSchema
from siliconcompiler.schema.utils import trim

if TYPE_CHECKING:
    from siliconcompiler import Design


###########################################################################
class FileSetSchema(NamedSchema, PathSchemaBase):
    '''
    Schema for storing and managing file sets.

    This class provides methods to add, retrieve, and manage named groups of
    files, known as filesets.
    '''

    def __init__(self):
        '''Initializes the FileSetSchema.'''
        super().__init__()

        schema = EditableSchema(self)

        filetype = 'default'

        schema.insert(
            'file', filetype,
            Parameter(
                '[file]',
                scope=Scope.GLOBAL,
                copy=True,
                shorthelp="Fileset files",
                example=[
                    "api: schema.set('fileset', 'rtl', 'file', 'verilog', 'mytop.v')",
                    "api: schema.set('fileset', 'testbench', 'file', 'verilog', 'tb.v')"],
                help=trim("""
                List of files grouped as a named set ('fileset'). The exact names of
                filetypes and filesets must match the names used in tasks
                called during flowgraph execution. The files are processed in
                the order specified by the ordered file list.""")))

        schema.insert(
            'topmodule',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="Top module name",
                example=[
                    "api: design.set('fileset', 'rtl', 'topmodule', 'mytop')",
                    "api: design.set('fileset', 'testbench', 'topmodule', 'tb')"],
                help=trim("""
                Name of top module specified on a per fileset basis.""")))

        schema.insert(
            'idir',
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

        schema.insert(
            'define',
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

        schema.insert(
            'undefine',
            Parameter(
                ['str'],
                scope=Scope.GLOBAL,
                shorthelp="Preprocessor macro undefine",
                example=[
                    "api: design.set('fileset', 'rtl', 'undefine', 'CFG_TARGET')"],
                help=trim("""
                Undefines a macro that may have been previously defined via the
                compiler, options, or header files.""")))

        schema.insert(
            'libdir',
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

        schema.insert(
            'lib',
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
        schema.insert(
            'param', name,
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

        schema.insert(
            'depfileset',
            Parameter(
                '[(str,str)]',
                scope=Scope.GLOBAL,
                shorthelp="Design dependency fileset",
                example=[
                    "api: design.set('fileset', 'rtl', 'depfileset', ('lambdalib', 'rtl'))"],
                help=trim("""Sets the mapping for dependency filesets.""")))

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict.

        This is used to identify the object type during serialization.
        """

        return FileSetSchema.__name__

    @property
    def __design(self) -> 'Design':
        return self._parent()._parent()

    ###############################################
    def add_file(self,
                 filename: Union[List[Union[Path, str]], Set[Union[Path, str]],
                                 Tuple[Union[Path, str], ...], Path, str],
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
        # handle list inputs
        if isinstance(filename, (list, set, tuple)):
            if isinstance(filename, set):
                filename = sorted(filename)
            params = []
            for item in filename:
                params.extend(
                    self.add_file(
                        item,
                        clobber=clobber,
                        filetype=filetype,
                        dataroot=dataroot))
            return params

        if filename is None:
            raise ValueError("add_file cannot process None")

        # map extension to default filetype
        if not filetype:
            ext = utils.get_file_ext(filename)
            filetype = utils.get_default_iomap().get(ext, ext)

        try:
            dataroot = self.__design._get_active_dataroot(dataroot)
        except ValueError:
            if not os.path.isabs(filename):
                raise

        # adding files to dictionary
        with self.__design.active_dataroot(dataroot):
            if clobber:
                return self.set('file', filetype, filename)
            else:
                return self.add('file', filetype, filename)

    ###############################################
    def get_file(self, filetype: Optional[str] = None) -> List[str]:
        """Returns a list of files.

        Args:
            filetype (str or list[str], optional): File type(s) to filter by
                (e.g., 'verilog'). If not provided, all filetypes in the
                fileset are returned.

        Returns:
            list[str]: A list of resolved file paths.
        """

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        # handle scalar+list in argument
        if not filetype:
            filetype = self.getkeys('file')

        # grab the files
        filelist = []
        for ftype in filetype:
            filelist.extend(self.find_files('file', ftype))

        return filelist

    ###############################################
    def has_file(self, filetype: Optional[str] = None) -> bool:
        """Returns true if the fileset contains files.

        Args:
            filetype (str or list[str], optional): File type(s) to filter by
                (e.g., 'verilog'). If not provided, all filetypes in the
                fileset are returned.

        Returns:
            bool: True if the fileset contains files.
        """

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        # handle scalar+list in argument
        if not filetype:
            filetype = self.getkeys('file')
        # grab the files
        for ftype in filetype:
            if self.get('file', ftype):
                return True

        return False

    ############################################
    def set_topmodule(self, value: str) -> str:
        """Sets the topmodule of a fileset.

        Args:
           value (str): Topmodule name.

        Returns:
           str: Topmodule name

        Notes:
            - first character must be letter or underscore
            - remaining characters can be letters, digits, or underscores
        """
        if value is None:
            raise ValueError("set_topmodule cannot process None")

        if not isinstance(value, str):
            raise ValueError("topmodule must be a string")

        # topmodule safety check
        if not re.match(r'^[_a-zA-Z]\w*$', value):
            raise ValueError(f"{value} is not a legal topmodule string")

        return self.set('topmodule', value)

    def get_topmodule(self) -> str:
        """Returns the topmodule of a fileset.

        Args:
           fileset (str): Fileset name. If not provided, the active fileset is
            used.

        Returns:
           str: Topmodule name
        """
        return self.get('topmodule')

    ##############################################
    def add_idir(self, value: str, clobber: bool = False,
                 dataroot: Optional[str] = None) -> List[str]:
        """Adds include directories to a fileset.

        Args:
           value (Path or list[Path]): Include path(s).
           clobber (bool, optional): Clears existing list before adding item.
           dataroot (str, optional): Data directory reference name.

        Returns:
           list[str]: List of include directories
        """
        try:
            dataroot = self.__design._get_active_dataroot(dataroot)
        except ValueError:
            values = value if isinstance(value, (list, tuple, set)) else [value]
            if any(not os.path.isabs(v) for v in values):
                raise

        if value is None:
            raise ValueError("add_idir cannot process None")

        with self.__design.active_dataroot(dataroot):
            if clobber:
                params = self.set('idir', value)
            else:
                params = self.add('idir', value)

        return params

    def get_idir(self) -> List[str]:
        """Returns include directories for a fileset.

        Returns:
           list[str]: List of include directories
        """
        return self.find_files('idir')

    def has_idir(self) -> bool:
        """Returns true if idirs are defined for the fileset

        Returns:
            bool: True if the fileset contains directories.
        """
        return bool(self.get('idir'))

    ##############################################
    def add_define(self, value: str, clobber: bool = False) -> List[str]:
        """Adds preprocessor macro definitions to a fileset.

        Args:
           value (str or List[str]): Macro definition.
           clobber (bool, optional): Clears existing list before adding item.

        Returns:
           list[str]: List of macro definitions

        """
        if value is None:
            raise ValueError("add_define cannot process None")

        if clobber:
            return self.set('define', value)
        else:
            return self.add('define', value)

    def get_define(self) -> List[str]:
        """Returns defined macros for a fileset.

        Returns:
           list[str]: List of macro definitions
        """
        return self.get('define')

    ##############################################
    def add_undefine(self, value: str, clobber: bool = False) -> List[str]:
        """Adds preprocessor macro (un)definitions to a fileset.

        Args:
           value (str or List[str]): Macro (un)definition.
           clobber (bool, optional): Clears existing list before adding item.

        Returns:
           list[str]: List of macro (un)definitions
        """
        if value is None:
            raise ValueError("add_undefine cannot process None")

        if clobber:
            return self.set('undefine', value)
        else:
            return self.add('undefine', value)

    def get_undefine(self) -> List[str]:
        """Returns undefined macros for a fileset.

       Returns:
           list[str]: List of macro (un)definitions

        """
        return self.get('undefine')

    ###############################################
    def add_libdir(self, value: str, clobber: bool = False,
                   dataroot: Optional[str] = None) -> List[str]:
        """Adds dynamic library directories to a fileset.

        Args:
           value (Path or list[Path]): Library path(s).
           clobber (bool, optional): Clears existing list before adding item.
           dataroot (str, optional): Data directory reference name.

        Returns:
           list[str]: List of library directories.
        """
        try:
            dataroot = self.__design._get_active_dataroot(dataroot)
        except ValueError:
            values = value if isinstance(value, (list, tuple, set)) else [value]
            if any(not os.path.isabs(v) for v in values):
                raise

        if value is None:
            raise ValueError("add_libdir cannot process None")

        with self.__design.active_dataroot(dataroot):
            if clobber:
                params = self.set('libdir', value)
            else:
                params = self.add('libdir', value)

        return params

    def get_libdir(self) -> List[str]:
        """Returns dynamic library directories for a fileset.

        Returns:
           list[str]: List of library directories.
        """
        return self.find_files('libdir')

    def has_libdir(self) -> bool:
        """Returns true if library directories are defined for the fileset

        Returns:
            bool: True if the fileset contains directories.
        """
        return bool(self.get('libdir'))

    ###############################################
    def add_lib(self, value: str, clobber: bool = False) -> List[str]:
        """Adds dynamic libraries to a fileset.

        Args:
           value (str or List[str]): Libraries.
           clobber (bool, optional): Clears existing list before adding item.

        Returns:
           list[str]: List of libraries.
        """
        if value is None:
            raise ValueError("add_lib cannot process None")

        if clobber:
            return self.set('lib', value)
        else:
            return self.add('lib', value)

    def get_lib(self) -> List[str]:
        """Returns list of dynamic libraries for a fileset.

        Returns:
           list[str]: List of libraries.
        """
        return self.get('lib')

    ###############################################
    def set_param(self, name: str, value: str) -> str:
        """Sets a named parameter for a fileset.

        Args:
            name (str): Parameter name.
            value (str): Parameter value.

        Returns:
            str: Parameter value
        """
        if name is None:
            raise ValueError("set_param cannot process None")

        if not isinstance(value, str) or value is None:
            raise ValueError("param value must be a string")

        return self.set('param', name, value)

    def get_param(self, name: str) -> str:
        """Returns value of a named fileset parameter.

        Args:
           name (str): Parameter name.

        Returns:
            str: Parameter value
        """
        return self.get('param', name)

    ###############################################
    def add_depfileset(self, dep: str, depfileset: Optional[str] = None):
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
        from siliconcompiler import Design

        if isinstance(dep, str):
            dep_name = dep
            if dep_name != self.__design.name:
                dep = self.__design.get_dep(dep_name)
            else:
                dep = self.__design
        elif isinstance(dep, Design):
            dep_name = dep.name
            if dep is not self.__design:
                self.__design.add_dep(dep, clobber=True)
        else:
            raise TypeError(f"dep is not a valid type: {dep}")

        if not isinstance(dep, Design):
            raise ValueError(f"cannot associate fileset ({depfileset}) with {dep.name}")

        if depfileset is None:
            if dep.has_fileset(self.name):
                depfileset = self.name
            else:
                filesets = dep.getkeys("fileset")
                if len(filesets) == 1:
                    depfileset = filesets[0]
                else:
                    raise ValueError(f"depfileset must be specified for {dep.name}")

        if not dep.has_fileset(depfileset):
            raise ValueError(f"{dep.name} does not have {depfileset} as a fileset")

        return self.add("depfileset", (dep_name, depfileset))

    def get_depfileset(self):
        """
        Returns list of dependency filesets.

        Returns:
           list[tuple(str, str)]: List of dependencies and filesets.
        """
        return self.get("depfileset")

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from ..schema.docs.utils import build_section

        fileset_sec = build_section(self.name, f"{ref_root}-fileset-{self.name}")

        params = BaseSchema._generate_doc(self,
                                          doc,
                                          ref_root=f"{ref_root}-fileset-{self.name}",
                                          key_offset=key_offset,
                                          detailed=False)
        if not params:
            return None

        fileset_sec += params

        return fileset_sec
