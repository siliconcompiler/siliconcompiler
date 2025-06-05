import json
from pathlib import Path
from enum import Enum
from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim
from siliconcompiler import utils

class Option(str, Enum):
    lib = 'lib'
    libdir = 'libdir'
    define = 'define'
    undefine = 'undefine'
    topmodule = 'topmodule'
    idir = 'idir'

class DesignSchema(NamedSchema):

    #TODO: do we want to have a hiararchy scheme for .use()?
    #TODO: use, dependency should move elsewhere
    #For example, dep="top.one.two"

    def __init__(self, name=None):
        NamedSchema.__init__(self, name=name)
        schema_design(self)
        self.__dependency = {}
        self.__fileset = None

    def set_fileset(self, value):
        """Sets the active fileset."""
        self.__fileset = value

    def get_fileset(self):
        """Returns the active fileset."""
        return self.__fileset

    def set_option(self, option: Option, value, fileset=None):
        """Sets an fileset option."""
        if fileset is None:
            fileset =  self.__fileset
        self.set('fileset', fileset, option.value, value)

    def get_option(self, option: Option, fileset=None, package=None):
        """Returns a fileset option."""
        if fileset is None:
            fileset =  self.__fileset
        return self.get('fileset', fileset, option.value)

    def set_param(self, name, value, fileset=None):
        """Adds named design parameter value."""
        if fileset is None:
            fileset =  self.__fileset
        self.set('fileset', fileset, 'param', name, value)

    def get_param(self, name, fileset=None, package=None):
        """Returns a design parameter value."""
        if fileset is None:
            fileset =  self.__fileset
        if not package:
            return self.get('fileset', fileset, 'param', name)
        else:
            return self.__dependency[package].get('fileset', fileset, 'param', name)

    def use(self, module):
        '''
        Stores module in local design dependency structure.
        Records dependency in design schema.
        '''
        self.__dependency[module.name()] = {}
        self.__dependency[module.name()] = module
        self.add('dependency', module.name())

    def add_file(self, filename, fileset=None, filetype=None, package=None):
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
            filename (str or list[str] or Path): File path or list of paths to add.
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

        if not fileset and self.__fileset:
            fileset =  self.__fileset
        elif not fileset:
            fileset = default_fileset

        if not filetype:
            filetype = default_filetype

        # final error checking
        if not fileset or not filetype:
            raise SiliconCompilerError(
                f'Unable to infer {category} fileset and/or filetype for '
                f'{filename} based on file extension.')

        # adding files to dictionary
        self.add('fileset', fileset, 'file', filetype, filename)

    def get_file(self, fileset=None, filetype=None, package=None):
        """
        Returns a list of files.
        """

        if fileset is None:
            fileset = self.__fileset
        if not isinstance(fileset, list):
            fileset = [fileset]

        if filetype and not isinstance(filetype, list):
            filetype = [filetype]

        if package:
            obj = self.__dependency[package]
        else:
            obj = self

        filelist = []
        for i in fileset:
            # handle scalar+list in argumnet
            if not filetype:
                filetype = list(obj.getkeys('fileset', i, 'file'))
            # grab the files
            for j in filetype:
                filelist.extend(obj.get('fileset', i, 'file',j))

        return filelist

    def export(self, filename, fileset=None, filetype=None):
        '''
        Export design configuration.
        Would be nice to insert this into schema with only
        non-zero values set.
        '''

        # select which filesets to dump
        if fileset is None:
            fileset = self.__fileset
        if not isinstance(fileset, list):
            fileset = [fileset]

        # file extension lookup
        if not filetype:
            formats = {}
            formats['f'] = 'flist'
            filetype = formats[Path(filename).suffix.strip('.')]

        if filetype == "flist":
            # TODO: handle dependency tree
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
            parameter is transalted to the '-y' option in verilog based tools.""")))

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

    ###########################
    # Dependencies
    ###########################

    schema.insert(
        'dependency',
        Parameter(
            ['str'],
            scope=Scope.GLOBAL,
            shorthelp="List of design dependencies",
            example=["api: chip.set('dependency', 'stdlib')"],
            help=trim("""
            List of design packages this design depends on.""")))
