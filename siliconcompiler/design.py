import contextlib
import re

from pathlib import Path
from typing import List

from siliconcompiler import utils
from siliconcompiler import SiliconCompilerError

from siliconcompiler.dependencyschema import DependencySchema
from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


###########################################################################
class DesignSchema(NamedSchema, DependencySchema):

    def __init__(self, name: str):
        NamedSchema.__init__(self, name=name)
        DependencySchema.__init__(self)

        schema_design(self)

        self.__fileset = None

    ############################################
    def set_topmodule(self,
                      value: str,
                      fileset: str = None) -> str:
        """Sets the topmodule of a fileset.

        Args:
           value (str): Topmodule name.
           fileset (str, optional): Fileset name.

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

    def get_topmodule(self, fileset: str = None) -> str:
        """Returns the topmodule of a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           str: Topmodule name

        """
        return self.__get(fileset, 'topmodule')

    ##############################################
    def add_idir(self,
                 value: str,
                 fileset: str = None,
                 clobber: bool = False,
                 package: str = None) -> List[str]:
        """Adds include directories to a fileset.

        Args:
           value (str or Path): Include directory name.
           fileset (str, optional): Fileset name.
           clobber (bool, optional): Clears existing list before adding item
           package (str, optional): Package name

        Returns:
           list[str]: List of include directories

        """
        return self.__set_add(fileset, 'idir', value, clobber, typelist=[str, list])

    def get_idir(self, fileset: str = None) -> List[str]:
        """Returns include directories for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: List of include directories

        """
        return self.__get(fileset, 'idir')

    ##############################################
    def add_define(self,
                   value: str,
                   fileset: str = None,
                   clobber: bool = False) -> List[str]:
        """Adds preprocessor macro definitions to a fileset.

        Args:
           value (str or List[str]): Macro definition.
           fileset (str, optional): Fileset name.
           clobber (bool, optional): Clears existing list before adding item.

        Returns:
           list[str]: List of macro definitions

        """
        return self.__set_add(fileset, 'define', value, clobber, typelist=[str, list])

    def get_define(self, fileset: str = None) -> List[str]:
        """Returns defined macros for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: List of macro definitions

        """
        return self.__get(fileset, 'define')

    ##############################################
    def add_undefine(self,
                     value: str,
                     fileset: str = None,
                     clobber: bool = False) -> List[str]:
        """Adds preprocessor macro (un)definitions to a fileset.

        Args:
           value (str or List[str]): Macro (un)definition.
           fileset (str, optional): Fileset name.
           clobber (bool, optional): CClears existing list before adding item.

        Returns:
           list[str]: List of macro (un)definitions

        """
        return self.__set_add(fileset, 'undefine', value, clobber, typelist=[str, list])

    def get_undefine(self, fileset: str = None) -> List[str]:
        """Returns undefined macros for a fileset.

        Args:
           fileset (str): Fileset name.

       Returns:
           list[str]: List of macro (un)definitions

        """
        return self.__get(fileset, 'undefine')

    ###############################################
    def add_libdir(self,
                   value: str,
                   fileset: str = None,
                   clobber: bool = False,
                   package: str = None) -> List[str]:
        """Adds dynamic library directories to a fileset.

        Args:
           value (str or List[str]): Library directories
           fileset (str, optional): Fileset name.
           clobber (bool, optional): Clears existing list before adding item.
           package (str, optional): Package name

        Returns:
           list[str]: List of library directories.

        """
        return self.__set_add(fileset, 'libdir', value, clobber, typelist=[str, list])

    def get_libdir(self, fileset: str = None) -> List[str]:
        """Returns dynamic library directories for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: List of library directories.

        """
        return self.__get(fileset, 'libdir')

    ###############################################
    def add_lib(self,
                value: str,
                fileset: str = None,
                clobber: bool = False) -> List[str]:
        """Adds dynamic libraries to a fileset.

        Args:
           value (str or List[str]): Libraries
           fileset (str, optional): Fileset name.
           clobber (bool, optional): Clears existing list before adding item.

        Returns:
           list[str]: List of libraries.

        """
        return self.__set_add(fileset, 'lib', value, clobber, typelist=[str, list])

    def get_lib(self, fileset: str = None) -> List[str]:
        """Returns list of dynamic libraries for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: List of libraries.

        """
        return self.__get(fileset, 'lib')

    ###############################################
    def set_param(self,
                  name: str,
                  value: str,
                  fileset: str = None) -> str:
        """Sets a named parameter for a fileset.

        Args:
            name (str): Parameter name.
            value (str): Parameter value.
            fileset (str, optional): Fileset name.

        Returns:
            str: Parameter value

        """

        if fileset is None:
            fileset = self.__fileset

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")

        if not isinstance(value, str) or value is None:
            raise ValueError("param value must be a string")

        return self.set('fileset', fileset, 'param', name, value)

    def get_param(self,
                  name: str,
                  fileset: str = None) -> str:
        """Returns value of a named fileset parameter.

        Args:
           name (str): Parameter name.
           fileset (str): Fileset name.

        Returns:
            str: Parameter value
        """
        if fileset is None:
            fileset = self.__fileset

        if not isinstance(fileset, str):
            raise ValueError("fileset value must be a string")
        return self.get('fileset', fileset, 'param', name)

    ###############################################
    def add_file(self,
                 filename: str,
                 fileset: str = None,
                 filetype: str = None,
                 clobber: bool = False,
                 package: str = None) -> List[str]:
        """
        Adds files to a fileset.



        .v        → (source, verilog)
        .vhd      → (source, vhdl)
        .sdc      → (constraint, sdc)
        .lef      → (input, lef)
        .def      → (input, def)
        ...       → etc.

        Args:
            filename (Path or list[Path]): File path or list of paths to add.
            fileset (str): Logical group to associate the file with.
            filetype (str, optional): Type of the file (e.g., 'verilog', 'sdc').
            clobber (bool, optional): Clears list before adding item
            package (str, optional): Package name

        Raises:
            SiliconCompilerError: If fileset or filetype cannot be inferred from
            the file extension.

        Returns:
           list[str]: List of file paths.

        Notes:
           - This method normalizes `filename` to a string for consistency.

           - If no filetype is specified, filetype is inferred based on
           the file extension via a mapping table. (eg. .v is verilog).


        """

        if fileset is None:
            fileset = self.__fileset

        # handle list inputs
        if isinstance(filename, (list, tuple)):
            for item in filename:
                self.add_file(
                    item,
                    fileset=fileset,
                    clobber=clobber,
                    filetype=filetype)
            return

        if filename is None:
            raise ValueError("add_file cannot process None")

        # Normalize value to string in case we receive a pathlib.Path
        filename = str(filename)

        # map extension to default filetype/fileset

        if not filetype:
            ext = utils.get_file_ext(filename)
            iomap = utils.get_default_iomap()
            if ext in iomap:
                default_fileset, default_filetype = iomap[ext]
                filetype = default_filetype
            else:
                raise ValueError("illegal file extension")

        # final error checking
        if not fileset or not filetype:
            raise SiliconCompilerError(
                f'Unable to infer fileset and/or filetype for '
                f'{filename} based on file extension.')

        # adding files to dictionary
        if clobber:
            return self.set('fileset', fileset, 'file', filetype, filename)
        else:
            return self.add('fileset', fileset, 'file', filetype, filename)

    ###############################################
    def get_file(self,
                 fileset: str = None,
                 filetype: str = None):
        """Returns a list of files from one or more filesets.

        Args:
            fileset (str or list[str]): Fileset(s) to query.
            filetype (str or list[str], optional): File type(s) to filter by (e.g., 'verilog').

        Returns:
            list[str]: List of file paths.
        """

        if fileset is None:
            fileset = self.__fileset

        if not isinstance(fileset, list):
            fileset = [fileset]

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        filelist = []
        for i in fileset:
            if not isinstance(i, str):
                raise ValueError("fileset key must be a string")
            # handle scalar+list in argument
            if not filetype:
                filetype = list(self.getkeys('fileset', i, 'file'))
            # grab the files
            for j in filetype:
                filelist.extend(self.get('fileset', i, 'file', j))

        return filelist

    ###############################################
    def write_fileset(self,
                      filename: str,
                      fileset: str = None,
                      fileformat: str = None) -> None:
        """Exports filesets to a standard formatted text file.

        Currently supports Verilog `flist` format only.
        Intended to support other formats in the future.

        Args:
            filename (str or Path): Output file name.
            fileset (str or list[str]): Fileset(s) to export.
            fileformat (str, optional): Export format.

        Inferred from file extension if not given.

        """

        if filename is None:
            raise ValueError("write_fileset() filename cannot be None")

        if fileset is None:
            fileset = self.__fileset

        if not isinstance(fileset, list):
            fileset = [fileset]

        # file extension lookup
        if not fileformat:
            formats = {}
            formats['f'] = 'flist'
            fileformat = formats[Path(filename).suffix.strip('.')]

        if fileformat == "flist":
            # TODO: handle dependency tree
            # TODO: add source info for comments to flist.
            with open(filename, "w") as f:
                for i in fileset:
                    if not isinstance(i, str):
                        raise ValueError("fileset key must be a string")
                    for j in ['idir', 'define', 'file']:
                        if j == 'idir':
                            vals = self.get('fileset', i, 'idir')
                            cmd = "+incdir+"
                        elif j == 'define':
                            vals = self.get('fileset', i, 'define')
                            cmd = "+define+"
                        else:
                            vals = self.get('fileset', i, 'file', 'verilog')
                            cmd = ""
                        if vals:
                            for item in vals:
                                f.write(f"{cmd}{item}\n")
        else:
            raise ValueError(f"{fileformat} is not supported")

    ################################################
    def read_fileset(self,
                     filename: str,
                     fileset: str,
                     fileformat=None) -> None:
        """Imports filesets from a standard formatted text file.

        Currently supports Verilog `flist` format only.
        Intended to support other formats in the future.

        Args:
            filename (str or Path): Output file name.
            fileset (str or list[str]): Filesets to import.
            fileformat (str, optional): Export format.

        """

        if filename is None:
            raise ValueError("read_fileset() filename cannot be None")

        if not fileformat:
            formats = {}
            formats['f'] = 'flist'
            fileformat = formats[Path(filename).suffix.strip('.')]

        if fileformat == "flist":
            raise NotImplementedError("read_fileset is not implemented yet")
        else:
            raise ValueError(f"{fileformat} is not supported")

    ################################################
    # Helper Functions
    ################################################
    def __set_add(self, fileset, option, value, clobber=False, typelist=None):
        '''Sets a parameter value in schema.
        '''

        if fileset is None:
            fileset = self.__fileset

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

        if list in typelist and not clobber:
            return self.add('fileset', fileset, option, value)
        else:
            return self.set('fileset', fileset, option, value)

    def __get(self, fileset, option):
        '''Gets a parameter value from schema.
        '''
        if fileset is None:
            fileset = self.__fileset

        if not isinstance(fileset, str):
            raise ValueError("fileset key must be a string")
        return self.get('fileset', fileset, option)

    @contextlib.contextmanager
    def active_fileset(self, fileset: str):
        """
        Use this context to temporarily set a design fileset.

        Raises:
            TypeError: if fileset is not a string
            ValueError: if fileset if an empty string

        Args:
            fileset (str): name of the fileset

        Example:
            >>> with design.active_fileset("rtl"):
            ...     design.set_topmodule("top")
            Sets the top module for the rtl fileset as top.
        """
        if not isinstance(fileset, str):
            raise TypeError("fileset must a string")
        if not fileset:
            raise ValueError("fileset cannot be an empty string")

        self.__fileset = fileset
        yield
        self.__fileset = None


###########################################################################
# Schema
###########################################################################
def schema_design(schema):

    schema = EditableSchema(schema)

    ###########################
    # Files
    ###########################

    fileset = 'default'
    filetype = 'default'
    schema.insert(
        'fileset', fileset, 'file', filetype,
        Parameter(
            ['file'],
            scope=Scope.GLOBAL,
            shorthelp="Design files",
            example=[
                "api: chip.set('fileset', 'rtl', 'file', 'verilog', 'mytop.v')",
                "api: chip.set('fileset', 'testbench', 'file', 'verilog', 'tb.v')"],
            help=trim("""
            List of files grouped as a named set ('fileset'). The exact names of
            filetypes and filesets must match the names used in tasks
            called during flowgraph execution. The files are processed in
            the order specified by the ordered file list.""")))

    ###########################
    # Options
    ###########################

    schema.insert(
        'fileset', fileset, 'topmodule',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Top module name",
            example=[
                "api: chip.set('fileset', 'rtl', 'topmodule', 'mytop')",
                "api: chip.set('fileset', 'testbench', 'topmodule', 'tb')"],
            help=trim("""
            Name of top module specified on a per fileset basis.""")))

    schema.insert(
        'fileset', fileset, 'idir',
        Parameter(
            ['dir'],
            scope=Scope.GLOBAL,
            shorthelp="Include file search paths",
            example=[
                "api: chip.set('fileset', 'rtl, 'idir', './rtl')",
                "api: chip.set('fileset', 'testbench', 'idir', '/testbench')"],
            help=trim("""
            Include paths specify directories to scan for header files during
            compilation. If multiple paths are provided, they are searched
            in the order given.""")))

    schema.insert(
        'fileset', fileset, 'define',
        Parameter(
            ['str'],
            scope=Scope.GLOBAL,
            shorthelp="Preprocessor macro definitions",
            example=[
                "api: chip.set('fileset', 'rtl', 'define', 'CFG_TARGET=FPGA')"],
            help=trim("""
            Defines macros at compile time for design languages that support
            preprocessing, such as Verilog, C, and C++. The macro format is
            is `MACRONAME[=value]`, where [=value] is optional.""")))

    schema.insert(
        'fileset', fileset, 'undefine',
        Parameter(
            ['str'],
            scope=Scope.GLOBAL,
            shorthelp="Preprocessor macro undefine",
            example=[
                "api: chip.set('fileset', 'rtl', 'undefine', 'CFG_TARGET')"],
            help=trim("""
            Undefines a macro that may have been previously defined via the
            compiler, options, or header files.""")))

    schema.insert(
        'fileset', fileset, 'libdir',
        Parameter(
            ['dir'],
            scope=Scope.GLOBAL,
            shorthelp="Library search paths",
            example=[
                "api: chip.set('fileset', 'rtl, 'libdir', '/usr/lib')"],
            help=trim("""
            Specifies directories to scan for libraries provided with the
            :keypath:`lib` parameter. If multiple paths are provided, they are
            searched based on the order of the libdir list. The libdir
            parameter is translated to the '-y' option in verilog based tools.""")))

    schema.insert(
        'fileset', fileset, 'lib',
        Parameter(
            ['str'],
            scope=Scope.GLOBAL,
            shorthelp="Design libraries to include",
            example=[
                "api: chip.set('fileset', 'rtl', 'lib', 'mylib')"],
            help=trim("""
            Specifies libraries to use during compilation. The compiler searches for
            library in the compiler standard library paths and in the
            paths specified by :keypath:`libdir` parameter.""")))

    name = 'default'
    schema.insert(
        'fileset', fileset, 'param', name,
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Design parameters",
            example=[
                "api: chip.set('fileset', 'rtl, 'param', 'N', '64'"],
            help=trim("""
            Sets a named parameter to a string value. The value is limited to basic
            data literals. The types of parameters and values supported is tightly
            coupled to tools being used. For example, in Verilog only integer
            literals (64'h4, 2'b0, 4) and strings are supported.""")))
