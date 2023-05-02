
from siliconcompiler.tools.verilator.verilator import setup as setup_tool


def setup(chip):
    '''
    Lints Verilog source. Takes in a single pickled Verilog file from
    ``inputs/<design>.v`` and produces no outputs. Results of linting can be
    programatically queried using errors/warnings metrics.
    '''

    # Generic tool setup.
    setup_tool(chip)

    tool = 'verilator'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    chip.add('tool', tool, 'task', task, 'option', ['--lint-only', '--debug'], step=step, index=index)
    chip.set('tool', tool, 'task', task, 'input', f'inputs/{design}.v', step=step, index=index)
