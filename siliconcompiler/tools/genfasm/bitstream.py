import shutil
from siliconcompiler import utils
from siliconcompiler.tools.genfasm import genfasm
from siliconcompiler.tools.vpr import vpr
from siliconcompiler.tools.vpr.vpr import VPRTask
from siliconcompiler.tools._common import get_tool_task


class BitstreamTask(VPRTask):
    def __init__(self):
        super().__init__()

    def tool(self):
        return "genfasm"

    def task(self):
        return "bitstream"

    def setup(self):
        super().setup()

        self.set_exe("genfasm", clobber=True)

        self.add_input_file(ext="route")
        self.add_input_file(ext="blif")
        self.add_input_file(ext="net")
        self.add_input_file(ext="place")

        self.add_output_file(ext="fasm")

    def runtime_options(self):
        options = super().runtime_options()

        options.append(f"inputs/{self.design_topmodule}.blif")

        options.extend(['--net_file', f'inputs/{self.design_topmodule}.net'])
        options.extend(['--place_file', f'inputs/{self.design_topmodule}.place'])
        options.extend(['--route_file', f'inputs/{self.design_topmodule}.route'])

        return options

    def post_process(self):
        super().post_process()

        shutil.move(f'{self.design_topmodule}.fasm', 'outputs')


def setup(chip):
    '''
    Generates a bitstream
    '''
    genfasm.setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(),
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'regex', 'warnings', "^Warning",
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', "^Error",
             step=step, index=index, clobber=False)

    design = chip.top()

    chip.set('tool', tool, 'task', task, 'input', design + '.route', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'input', design + '.blif', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'input', design + '.net', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'input', design + '.place', step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', design + '.fasm', step=step, index=index)


def runtime_options(chip):
    options = vpr.runtime_options(chip)

    design = chip.top()

    blif = f"inputs/{design}.blif"
    options.append(blif)

    options.extend(['--net_file', f'inputs/{design}.net'])
    options.extend(['--place_file', f'inputs/{design}.place'])
    options.extend(['--route_file', f'inputs/{design}.route'])

    return options

################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    vpr.vpr_post_process(chip)

    design = chip.top()
    shutil.move(f'{design}.fasm', 'outputs')
