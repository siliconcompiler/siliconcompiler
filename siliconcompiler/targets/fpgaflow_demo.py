import siliconcompiler

def make_docs():
    '''
    Demonstration target for running the open-source fpgaflow.
    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    setup(chip)
    return chip

def setup(chip):
    '''
    Target setup
    '''

    #1. Defining the project
    target = 'fpgaflow_demo'
    chip.set('option', 'target', target)

    #2. Load flow
    from flows import fpgaflow
    chip.use(fpgaflow)

    #3. Select default flow
    chip.set('option', 'flow', 'fpgaflow')

#########################
if __name__ == "__main__":

    chip = make_docs()
