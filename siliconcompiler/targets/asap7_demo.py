import siliconcompiler

def make_docs():
    '''
    Demonstration target for compiling ASICs with ASAP7 and the open-source
    asicflow.
    '''

    chip = siliconcompiler.Chip('asap7_demo')
    setup(chip)
    return chip

def setup(chip):
    '''
    ASAP7 Demo Target
    '''

    #0. Defining the project
    target = 'asap7_demo'
    chip.set('option', 'target', target)

    #2. Load PDK, flow, libs combo
    from pdks import asap7
    from flows import asicflow
    from libs import asap7sc7p5t
    chip.use(asap7)
    chip.use(asicflow)
    chip.use(asap7sc7p5t)

    #3. Select default flow/PDK
    chip.set('option', 'flow', 'asicflow')
    chip.set('option', 'pdk', 'asap7')
    chip.set('option', 'stackup', '10M')

    #4. Select libraries
    chip.set('asic', 'logiclib', 'asap7sc7p5t_rvt')

    #5. Project specific design choices
    chip.set('asic', 'delaymodel', 'nldm')
    chip.set('constraint', 'density', 10)
    chip.set('constraint', 'coremargin', 0.270)

    #5. Timing corners
    corner = 'typical'
    chip.set('constraint', 'timing', 'worst', 'libcorner', corner)
    chip.set('constraint', 'timing', 'worst', 'pexcorner', corner)
    chip.set('constraint', 'timing', 'worst', 'mode', 'func')
    chip.set('constraint', 'timing', 'worst', 'check', ['setup','hold'])

#########################
if __name__ == "__main__":

    chip = make_docs()
