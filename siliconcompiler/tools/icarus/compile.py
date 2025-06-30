from siliconcompiler.tools._common import \
    add_require_input, add_frontend_requires, get_input_files, get_frontend_options, \
    get_tool_task
from siliconcompiler import utils

from siliconcompiler import TaskSchema


class CompileTask(TaskSchema):
    def __init__(self):
        super().__init__()

        self.add_parameter("verilog_genration", "<1995,2001,2001-noconfig,2005,2005-sv,2009,2012>", 
                           'Select Verilog language generation for Icarus to use. Legal values are '
                           '"1995", "2001", "2001-noconfig", "2005", "2005-sv", "2009", or "2012". '
                           'See the corresponding "-g" flags in the Icarus manual for more information.')

    def tool(self):
        return "icarus"

    def task(self):
        return "compile"

    def parse_version(self, stdout):
        # First line: Icarus Verilog version 10.1 (stable) ()
        return stdout.split()[3]

    def setup(self):
        super().setup()

        self.schema("tool").set("exe", "iverilog")
        self.schema("tool").set("vswitch", "-V")
        self.schema("tool").set("version", ">=10.3")

        self.set_threads()

        self.add_output_file(ext="vpp")

    def runtime_options(self):
        options = super().runtime_options()

        options.extend(["-o", f"outputs/{self.design_topmodule}.vpp"])
        options.extend(["-s", self.design_topmodule])

        verilog_gen = self.get("var", "verilog_generation")
        if verilog_gen:
            options.append(f'-g{verilog_gen}')

        filesets = self.schema().get_filesets()
        idirs = []
        defines = []
        params = []
        for lib, fileset in filesets:
            idirs.extend(lib.find_files("fileset", fileset, "idir"))
            defines.extend(lib.get("fileset", fileset, "define"))
        fileset = self.schema().get("option", "fileset")[0]

        design = self.schema().design
        for param in design.getkeys("fileset", fileset, "param"):
            params.append((param, design.get("fileset", fileset, "param", param)))

        ###############################
        # Parameters (top module only)
        ###############################
        # Set up user-provided parameters to ensure we elaborate the correct modules
        for param, value in params:
            options.append(f"-P{self.design_topmodule}.{param}={value}")

        #####################
        # Include paths
        #####################
        for idir in idirs:
            options.append('-I' + idir)

        #######################
        # Variable Definitions
        #######################
        for define in defines:
            options.append('-D' + define)

        # add siliconcompiler specific defines
        options.append(f"-DSILICONCOMPILER_TRACE_FILE=\"reports/{self.design_topmodule}.vcd\"")

        #######################
        # Command files
        #######################
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="commandfile"):
                options.extend(['-f', value])

        #######################
        # Sources
        #######################
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="systemverilog"):
                options.append(value)
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="verilog"):
                options.append(value)

        return options


def setup(chip):
    '''
    Compile the input verilog into a vvp file that can be simulated.
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'icarus'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Standard Setup
    chip.set('tool', tool, 'exe', 'iverilog')
    chip.set('tool', tool, 'vswitch', '-V')
    chip.set('tool', tool, 'version', '>=10.3', clobber=False)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'verilog_generation',
             'Select Verilog language generation for Icarus to use. Legal values are '
             '"1995", "2001", "2001-noconfig", "2005", "2005-sv", "2009", or "2012". '
             'See the corresponding "-g" flags in the Icarus manual for more information.',
             field='help')

    add_require_input(chip, 'input', 'rtl', 'netlist')
    add_require_input(chip, 'input', 'rtl', 'verilog')
    add_require_input(chip, 'input', 'rtl', 'systemverilog')
    add_require_input(chip, 'input', 'cmdfile', 'f')
    add_frontend_requires(chip, ['ydir', 'vlib', 'idir', 'define', 'libext'])

    design = chip.top()
    chip.add('tool', tool, 'task', task, 'output', f'{design}.vvp', step=step, index=index)


################################
#  Custom runtime options
################################
def runtime_options(chip):

    ''' Custom runtime options, returns list of command line options.
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    cmdlist = []

    design = chip.top()
    cmdlist = ['-o', f'outputs/{design}.vvp']
    cmdlist += ['-s', chip.top()]

    verilog_gen = chip.get('tool', tool, 'task', task, 'var', 'verilog_generation',
                           step=step, index=index)
    if verilog_gen:
        cmdlist.append(f'-g{verilog_gen[0]}')

    opts = get_frontend_options(chip, ['ydir', 'vlib', 'idir', 'define', 'libext'])

    for libext in opts['libext']:
        cmdlist.append(f'-Y.{libext}')

    # source files
    for value in opts['ydir']:
        cmdlist.extend(['-y', value])
    for value in opts['vlib']:
        cmdlist.extend(['-v', value])
    for value in opts['idir']:
        cmdlist.append('-I' + value)
    for value in opts['define']:
        cmdlist.append('-D' + value)

    # add siliconcompiler specific defines
    cmdlist.append(f"-DSILICONCOMPILER_TRACE_FILE=\"reports/{design}.vcd\"")

    for value in get_input_files(chip, 'input', 'cmdfile', 'f'):
        cmdlist.extend(['-f', value])
    for value in get_input_files(chip, 'input', 'rtl', 'netlist'):
        cmdlist.append(value)
    for value in get_input_files(chip, 'input', 'rtl', 'verilog'):
        cmdlist.append(value)
    for value in get_input_files(chip, 'input', 'rtl', 'systemverilog'):
        cmdlist.append(value)

    return cmdlist
