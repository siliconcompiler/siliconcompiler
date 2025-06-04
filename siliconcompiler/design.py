import json
from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter
from siliconcompiler.schema.utils import trim
from siliconcompiler import utils

class DesignSchema(NamedSchema):

    def __init__(self, name=None):
        NamedSchema.__init__(self, name=name)
        schema_design(self)
        self.dependency = {}

    #############################################
    def add_file(self, files=None, fileset=None, filetype=None):
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

        #TODO: could we handle path resolution in this function
        #ie: always pass in unix paths?

        # Handle list inputs
        if isinstance(files, (list, tuple)):
            for item in files:
                self.add_file(
                    item,
                    fileset=fileset,
                    filetype=filetype)
            return

        # Normalize value to string in case we receive a pathlib.Path
        filename = str(files)

        ext = utils.get_file_ext(files)

        # map extension to default filetype/fileset
        default_fileset, default_filetype = utils.get_default_iomap()[ext]

        if not fileset:
            fileset = default_fileset

        if not filetype:
            filetype = default_filetype

        # final error checking
        if not fileset or not filetype:
            raise SiliconCompilerError(
                f'Unable to infer {category} fileset and/or filetype for '
                f'{filename} based on file extension.')

        # adding files to dictionary
        self.add('fileset', fileset, 'file', filetype, files)

    #############################################
    def option(self, fileset=None, **kwargs):
        """
        Configures an option defined by the Design schema.

        If the key is associated with a string-type field, the value is set directly.
        For all lists, the value is appended using the `add` method.

        Args:
        key (str): The name of the option to configure.
        value (Any): The value to set or append for the given option.
        fileset (str): The name of the fileset where the option is applied.

        """

        for key, value in kwargs.items():
            if self.get('fileset', fileset, key, field="type") == "str":
                self.set('fileset', fileset, key, value)
            elif key=='param':
                self.set('fileset', fileset, 'param', value)
            else:
                self.add('fileset', fileset, key, value)

    #############################################
    def use(self, module):
        '''
        Stores module in local design dependency structure.
        Records dependency in design schema.
        '''
        self.dependency[module.name] = {}
        self.dependency[module.name] = module
        self.add('dependency', module.name)

    #############################################
    def export(self, filename=None, filetype=None):
        '''
        Export design configuration.
        Would be nice to insert this into schema with only
        non-zero values set.
        '''

        cfg = {}
        # exporting simple dictionary
        for keys in self.allkeys(include_default=False):
            local = cfg
            val = self.get(*keys)
            if val:
                for i, k in enumerate(list(keys)):
                    if k not in local:
                        local[k] = {}
                    if (i == len(keys) - 1):
                        local[k] = val
                    local = local[k]

        # write to file
        if filename:
            if filetype == 'flist':
                pass
            elif filetype == 'bender':
                pass
            elif filetype == 'fusesoc':
                pass
            else:
                json.dumps(filename, indent=4)

        return cfg

###########################################################################
# Schema
###########################################################################
def schema_design(schema):

    schema = EditableSchema(schema)

    ###########################
    # General compile options
    ###########################

    fileset = 'default'
    filetype = 'default'
    schema.insert(
        'fileset', fileset, 'file', filetype,
        Parameter(
            ['file'],
            shorthelp="Design files",
            example=[
                "api: chip.set('fileset', 'rtl', 'file', 'verilog', 'mytop.v')",
                "api: chip.set('fileset', 'testbench', 'file', 'verilog', 'tb.v')"],
            help=trim("""
            List of files grouped as a named set ('fileset'). The exact names of
            filetypes and filesets must match the names used in tasks
            called during flowgraph execution. The files are processed in
            the order specified by the ordered file list.""")))

    schema.insert(
        'fileset', fileset, 'topmodule',
        Parameter(
            'str',
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
            shorthelp="Preprocessor macro undefine",
            example=[
                "api: chip.set('fileset', 'rtl', 'undefine', 'CFG_TARGET')"],
            help=trim("""
            Undefines a macro that may have been previously defined via the
            compiler, options, or header files.""")))

    name = 'default'
    schema.insert(
        'fileset', fileset, 'param',
        Parameter(
            '[(str,str)]',
            shorthelp="Design parameters",
            example=[
                "api: chip.set('fileset', 'rtl, 'param', ('N','64')"],
            help=trim("""
            Sets a named parameter to a string value. The value is limited to basic
            data literals. The types of parameters and values supported is tightly
            coupled to tools being used. For example, in Verilog only integer
            literals (64'h4, 2'b0, 4) and strings are supported.""")))

    schema.insert(
        'fileset', fileset, 'libdir',
        Parameter(
            ['dir'],
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
            shorthelp="Design libraries to include",
            example=[
                "api: chip.set('fileset', 'rtl', 'lib', 'mylib')"],
            help=trim("""
            Specifies libraries to use during compilation. The compiler searches for
            library in the compiler standard library paths and in the
            paths specified by :keypath:`libdir` parameter.""")))

    schema.insert(
        'fileset', fileset, 'libext',
        Parameter(
            ['str'],
            shorthelp="Library file suffixes",
            example=[
                "api: chip.set('fileset', 'rtl', 'libext', 'sv')"],
            help=trim("""
            List of file extensions to use when searching for design modules.
            For example, if :keypath:`libdir` is set to `./mylib` and libext is set
            to `.v`, then the tool will search for modules in all files matching
            `./mylib/*.v`. For GCC, libext is hard coded as '.a' and '.so'.""")))

    ###########################
    # Dependencies
    ###########################

    schema.insert(
        'dependency',
        Parameter(
            ['str'],
            shorthelp="List of design dependencies",
            example=["api: chip.set('dependency', 'stdlib')"],
            help=trim("""
            List of design packages this design depends on.""")))
