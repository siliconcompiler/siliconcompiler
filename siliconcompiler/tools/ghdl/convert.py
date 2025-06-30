from siliconcompiler.tools._common import add_require_input, add_frontend_requires, \
    get_input_files, get_tool_task, has_input_files
from siliconcompiler import utils

from siliconcompiler import TaskSchema


class ConvertTask(TaskSchema):
    def __init__(self):
        super().__init__()

        self.add_parameter("use_fsynopsys", "bool", "add the -fsynopsys flag", defvalue=False)
        self.add_parameter("use_latches", "bool", "add the --latches flag", defvalue=False)

    def set_usefsynopsys(self, value: bool):
        self.set("var", "use_fsynopsys", value)

    def set_uselatches(self, value: bool):
        self.set("var", "use_latches", value)

    def tool(self):
        return "ghdl"

    def task(self):
        return "convert"

    def parse_version(self, stdout):
        # first line: GHDL 2.0.0-dev (1.0.0.r827.ge49cb7b9) [Dunoon edition]

        # '*-dev' is interpreted by packaging.version as a "developmental release",
        # which has the correct semantics. e.g. Version('2.0.0') > Version('2.0.0-dev')
        return stdout.split()[1]

    def setup(self):
        super().setup()

        self.set_exe("ghdl", vswitch="--version")
        self.add_version(">=4.0.0-dev")

        self.set_threads(1)

        self.set_logdestination("stdout", "output", "v")

        self.add_output_file(ext="v")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.schema().get("option", "alias"):
            self.add_required_key("option", "alias")

        # Mark required
        for lib, fileset in self.schema().get_filesets():
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.get_file(fileset=fileset, filetype="vhdl"):
                self.add_required_key(lib, "fileset", fileset, "file", "vhdl")

        self.add_required_tool_key("var", "use_fsynopsys")
        self.add_required_tool_key("var", "use_latches")

    def runtime_options(self):
        options = super().runtime_options()

        # Synthesize inputs and output Verilog netlist
        options.append('--synth')
        options.append('--std=08')
        options.append('--out=verilog')
        options.append('--no-formal')

        if self.get("var", "use_fsynopsys"):
            options.append('-fsynopsys')
        if self.get("var", "use_latches"):
            options.append('--latches')

        filesets = self.schema().get_filesets()
        defines = []
        for lib, fileset in filesets:
            defines.extend(lib.get("fileset", fileset, "define"))

        # Add defines
        for define in defines:
            options.append(f'-g{define}')

        # Add sources
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="vhdl"):
                options.append(value)

        # Set top module
        options.append('-e')

        options.append(self.design_topmodule)

        return options


def setup(chip):
    '''
    Imports VHDL and converts it to verilog
    '''

    # Standard Setup
    tool = 'ghdl'
    clobber = False

    if not has_input_files(chip, 'input', 'rtl', 'vhdl'):
        return "no files in [input,rtl,vhdl]"

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'exe', 'ghdl')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=4.0.0-dev', clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'option', [],
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'stdout', 'destination', 'output',
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'stdout', 'suffix', 'v',
             step=step, index=index)

    # Schema requirements
    add_require_input(chip, 'input', 'rtl', 'vhdl')
    add_frontend_requires(chip, ['define'])

    design = chip.top()

    chip.set('tool', tool, 'task', task, 'output', f'{design}.v', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'extraopts', 'extra options to pass to ghdl',
             field='help')
    if chip.get('tool', tool, 'task', task, 'var', 'extraopts', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['tool', tool, 'task', task, 'var', 'extraopts']),
                 step=step, index=index)


################################
#  Custom runtime options
################################
def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    options = []

    # Synthesize inputs and output Verilog netlist
    options.append('--synth')
    options.append('--std=08')
    options.append('--out=verilog')
    options.append('--no-formal')

    # currently only -fsynopsys and --latches supported
    valid_extraopts = ['-fsynopsys', '--latches']

    extra_opts = chip.get('tool', 'ghdl', 'task', task, 'var', 'extraopts', step=step, index=index)
    for opt in extra_opts:
        if opt in valid_extraopts:
            options.append(opt)
        else:
            chip.error('Unsupported option ' + opt)

    # Add defines
    for define in chip.get('option', 'define'):
        options.append(f'-g{define}')

    # Add sources
    for value in get_input_files(chip, 'input', 'rtl', 'vhdl'):
        options.append(value)

    # Set top module
    options.append('-e')

    options.append(chip.top(step=step, index=index))

    return options
