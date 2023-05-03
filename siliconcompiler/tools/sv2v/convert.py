import os


def setup(chip):
    '''
    Convert SystemVerilog to verilog
    '''

    chip.logger.debug("Setting up sv2v")

    tool = 'sv2v'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = 'convert'

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '--numeric-version')
    chip.set('tool', tool, 'version', '>=0.0.9', clobber=False)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    # Since we run sv2v after the import/preprocess step, there should be no
    # need for specifying include dirs/defines. However we don't want to pass
    # --skip-preprocessor because there may still be unused preprocessor
    # directives not removed by the importer and passing the --skip-preprocessor
    # flag would cause sv2v to error.

    # since this step should run after import, the top design module should be
    # set and we can read the pickled Verilog without accessing the original
    # sources
    topmodule = chip.top()
    chip.set('tool', tool, 'task', task, 'option', [], step=step, index=index)
    chip.add('tool', tool, 'task', task, 'option', "inputs/" + topmodule + ".v",
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'option', "--write=outputs/" + topmodule + ".v",
             step=step, index=index)

    chip.set('tool', tool, 'task', task, 'input', f'{topmodule}.v', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', f'{topmodule}.v', step=step, index=index)
