from pathlib import Path
from typing import List
from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim
from siliconcompiler import utils
from siliconcompiler import SiliconCompilerError


###########################################################################
class DesignSchema(NamedSchema):

    def __init__(self, name: str):
        NamedSchema.__init__(self, name=name)
        schema_design(self)
        # TODO: move this into use schema?
        self.__dependency = {}

    ############################################
    def set_topmodule(self, value: str, fileset: str = None) -> None:
        """Sets topmodule for a fileset.

        Args:
           value (str): Topmodule name.
           fileset (str, optional): Fileset name.

        """
        self.set('fileset', fileset, 'topmodule', value)

    def get_topmodule(self, fileset: str) -> str:
        """Returns topmodule for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           str: Topmodule name

        """
        return self.get('fileset', fileset, 'topmodule')

    ##############################################
    def set_idir(self, value: str, fileset=None) -> None:
        """Sets include directories for a fileset.

        Args:
           value (str or Path): Include directory name.
           fileset (str, optional): Fileset name.

        """
        self.set('fileset', fileset, 'idir', value)

    def get_idir(self, fileset: str) -> List[str]:
        """Returns include directories for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: Topmodule name

        """
        return self.get('fileset', fileset, 'idir')

    ##############################################
    def set_define(self, value: str, fileset=None) -> None:
        """Defines a macro for a fileset.

        Args:
           value (str or List[str]): Macro definition.
           fileset (str, optional): Fileset name.
        """
        self.set('fileset', fileset, 'define', value)

    def get_define(self, fileset: str) -> List[str]:
        """Returns defined macros for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: List of macro definitions

        """
        return self.get('fileset', fileset, 'define')

    ##############################################
    def set_undefine(self, value: str, fileset: str = None) -> None:
        """Undefines a preprocessor macro for a fileset.

        Args:
           value (str or List[str]): Macro definition to undefine.
           fileset (str, optional): Fileset name.
        """
        self.set('fileset', fileset, 'undefine', value)

    def get_undefine(self, fileset: str) -> List[str]:
        """Returns undefined macros for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: List of macro (un)definitions

        """
        return self.get('fileset', fileset, 'undefine')

    ###############################################
    def set_libdir(self, value: str, fileset=None) -> None:
        """Sets dynamic library directories for a fileset.

        Args:
           value (str or List[str]): Library directories.
           fileset (str, optional): Fileset name.
        """
        self.set('fileset', fileset, 'libdir', value)

    def get_libdir(self, fileset: str) -> List[str]:
        """Returns dynamic library directories for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: List of library directories.

        """
        return self.get('fileset', fileset, 'libdir')

    ###############################################
    def set_lib(self, value: str, fileset=None) -> None:
        """Sets list of dynamic libraries for a fileset.

        Args:
           value (str or List[str]): Library directory names.
           fileset (str, optional): Fileset name.
        """
        self.set('fileset', fileset, 'lib', value)

    def get_lib(self, fileset: str) -> List[str]:
        """Returns list of dynamic libraries for a fileset.

        Args:
           fileset (str): Fileset name.

        Returns:
           list[str]: List of libraries.

        """
        return self.get('fileset', fileset, 'lib')

    ###############################################
    def set_param(self, name: str, value: str, fileset: str = None) -> None:
        """Sets a named design parameter for a fileset.

        Args:
            name (str): Parameter name.
            value (str): Parameter value.
            fileset (str, optional): Fileset name.
        """
        self.set('fileset', fileset, 'param', name, value)

    def get_param(self, name: str, fileset: str) -> str:
        """Returns value of a named design parameter.

        Args:
           name (str): Parameter name.
           fileset (str): Fileset name.

        Returns:
            str: Parameter value
        """
        return self.get('fileset', fileset, 'param', name)

    ###############################################
    def add_file(self, filename: str, fileset=None, filetype=None, package=None):
        """
        Adds a file (or list of files) to a fileset.

        If no fileset or filetype is specified, they are inferred based on the
        file extension.

        Default filetype and fileset mappings are determined by the extension
        and defined in the I/O mapping table (iotable), typically like:

        .v        → (source, verilog)
        .vhd      → (source, vhdl)
        .sdc      → (constraint, sdc)
        .lef      → (input, lef)
        .def      → (input, def)
        ...       → etc.

        Args:
            filename (Path or list[Path]): File path or list of paths to add.
            fileset (str, optional): Logical group to associate the file with.
                If not provided, it is inferred from the file extension.
            filetype (str, optional): Type of the file (e.g., 'verilog', 'sdc').
                If not provided, it is inferred from the file extension.

        Raises:
            SiliconCompilerError: If fileset or filetype cannot be inferred from
                the file extension.

        Notes:
            - If `filename` is a list or tuple, `add_file` is called recursively.
            - This method normalizes `filename` to a string for consistency.
        """

        # Handle list inputs
        if isinstance(filename, (list, tuple)):
            for item in filename:
                self.add_file(
                    item,
                    fileset=fileset,
                    filetype=filetype)
            return

        # Normalize value to string in case we receive a pathlib.Path
        filename = str(filename)
        ext = utils.get_file_ext(filename)

        # map extension to default filetype/fileset
        default_fileset, default_filetype = utils.get_default_iomap()[ext]

        if not fileset:
            fileset = default_fileset

        if not filetype:
            filetype = default_filetype

        # final error checking
        if not fileset or not filetype:
            raise SiliconCompilerError(
                f'Unable to infer fileset and/or filetype for '
                f'{filename} based on file extension.')

        # adding files to dictionary
        self.add('fileset', fileset, 'file', filetype, filename)

    ###############################################
    def get_file(self, fileset: str, filetype: str = None):
        """Returns a list of files from one or more filesets.

        Args:
            fileset (str or list[str]): Fileset(s) to query. Defaults to active fileset.
            filetype (str or list[str], optional): File type(s) to filter by (e.g., 'verilog').

        Returns:
            list[str]: List of file paths.
        """

        if not isinstance(fileset, list):
            fileset = [fileset]

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        filelist = []
        for i in fileset:
            # handle scalar+list in argument
            if not filetype:
                filetype = list(self.getkeys('fileset', i, 'file'))
            # grab the files
            for j in filetype:
                filelist.extend(self.get('fileset', i, 'file', j))

        return filelist

    ###############################################
    def write_filelist(self, filename: str, fileset: str, fileformat=None) -> None:
        """Exports filesets to a standard formatted text file.

        Currently supports Verilog `flist` format only.
        Intended to support other formats in the future.

        Args:
            filename (str or Path): Output file name.
            fileset (str or list[str]): Fileset(s) to export.
            fileformat (str, optional): Export format. Inferred from file extension if not given.

        """
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

    ################################################
    def read_filelist(self, filename: str, fileset: str, fileformat=None) -> None:
        """Imports filesets from a standard formatted text file.

        Currently supports Verilog `flist` format only.
        Intended to support other formats in the future.

        Args:
            filename (str or Path): Output file name.
            fileset (str or list[str]): Fileset(s) to export. Defaults to active fileset.
            fileformat (str, optional): Export format. Inferred from file extension if not given.

        """
        pass


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
