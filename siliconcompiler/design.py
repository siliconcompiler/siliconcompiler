from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter
from siliconcompiler.schema.utils import trim


class DesignSchema(NamedSchema):

    def __init__(self, name=None):
        NamedSchema.__init__(self, name=name)
        schema_design(self)


###############################################################################
# Design
###############################################################################
def schema_design(schema):
    schema = EditableSchema(schema)

    fileset = 'default'

    ###########################
    # General compile options
    ###########################

    filetype = 'default'
    schema.insert(
        fileset, 'file', filetype,
        Parameter(
            ['file'],
            shorthelp="Design files",
            example=["api: chip.set('rtl', 'file', 'verilog', 'mytop.v')",
                     "api: chip.set('testbench', 'file', 'verilog', 'tb.v')"],
            help=trim("""
            List of files grouped as a named set ('fileset'). The exact names of
            filetypes and filesets must match the names used in tasks
            called during flowgraph execution. The files are processed in
            the order specified by the ordered file list.""")))

    schema.insert(
        fileset, 'top',
        Parameter(
            'str',
            shorthelp="Top module name",
            example=["api: chip.set('rtl', 'top', 'mytop')",
                     "api: chip.set('testbench', 'top', 'tb')"],
            help=trim("""
            Name of top module specified on a per fileset basis.""")))

    schema.insert(
        fileset, 'idir',
        Parameter(
            ['dir'],
            shorthelp="Include file search paths",
            example=["api: chip.set('rtl, 'idir', './rtl')",
                     "api: chip.set('testbench', 'idir', '/testbench')"],
            help=trim("""
            Include paths specify directories to scan for header files during
            compilation. If multiple paths are provided, they are searched
            in the order given.""")))

    schema.insert(
        fileset, 'define',
        Parameter(
            ['str'],
            shorthelp="Preprocessor macro definitions",
            example=["api: chip.set('rtl', 'define', 'CFG_TARGET=FPGA')"],
            help=trim("""
            Defines macros at compile time for design languages that support
            preprocessing, such as Verilog, C, and C++. The macro format is
            is `MACRONAME[=value]`, where [=value] is optional.""")))

    schema.insert(
        fileset, 'undefine',
        Parameter(
            ['str'],
            shorthelp="Preprocessor macro undefine",
            example=["api: chip.set('rtl', 'undefine', 'CFG_TARGET')"],
            help=trim("""
            Undefines a macro that may have been previously defined via the
            compiler, options, or header files.""")))

    name = 'default'
    schema.insert(
        fileset, 'param', name,
        Parameter(
            'str',
            shorthelp="Design parameters",
            example=["api: chip.set('rtl, 'param', 'N', '64')"],
            help=trim("""
            Sets a named parameter to a string value. The value is limited to basic
            data literals. The types of parameters and values supported is tightly
            coupled to tools being used. For example, in Verilog only integer
            literals (64'h4, 2'b0, 4) and strings are supported.""")))

    schema.insert(
        fileset, 'libdir',
        Parameter(
            ['dir'],
            shorthelp="Library search paths",
            example=["api: chip.set('rtl, 'libdir', '/usr/lib')"],
            help=trim("""
            Specifies directories to scan for libraries provided with the
            :keypath:`lib` parameter. If multiple paths are provided, they are
            searched based on the order of the libdir list. The libdir
            parameter is transalted to the '-y' option in verilog based tools.""")))

    schema.insert(
        fileset, 'lib',
        Parameter(
            ['str'],
            shorthelp="Design libraries to include",
            example=["api: chip.set('rtl', 'lib', 'mylib')"],
            help=trim("""
            Specifies libraries to use during compilation. The compiler searches for
            library in the compiler standard library paths and in the
            paths specified by :keypath:`libdir` parameter.""")))

    schema.insert(
        fileset, 'libext',
        Parameter(
            ['str'],
            shorthelp="Library file suffixes",
            example=["api: chip.set('rtl', 'libext', 'sv')"],
            help=trim("""
            List of file extensions to use when searching for design modules.
            For example, if :keypath:`libdir` is set to `./mylib` and libext is set
            to `.v`, then the tool will search for modules in all files matching
            `./mylib/*.v`. For GCC, libext is hard coded as '.a' and '.so'.""")))
