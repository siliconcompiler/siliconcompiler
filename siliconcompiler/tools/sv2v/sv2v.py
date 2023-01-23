import importlib

import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    sv2v converts SystemVerilog (IEEE 1800-2017) to Verilog
    (IEEE 1364-2005), with an emphasis on supporting synthesizable
    language constructs. The primary goal of this project is to
    create a completely free and open-source tool for converting
    SystemVerilog to Verilog. While methods for performing this
    conversion already exist, they generally either rely on
    commercial tools, or are limited in scope.

    Documentation: https://github.com/zachjs/sv2v

    Sources: https://github.com/zachjs/sv2v

    Installation: https://github.com/zachjs/sv2v

    '''

    chip = siliconcompiler.Chip('<design>')
    step = '<step>'
    index = '<index>'
    flow = '<flow>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('option', 'flow', flow)
    chip.set('flowgraph', flow, step, index, 'task', '<task>')
    from tools.sv2v.convert import setup
    setup = getattr(importlib.import_module('tools.sv2v.convert'), 'setup')
    setup(chip)
    return chip

def parse_version(stdout):
    # 0.0.7-130-g1aa30ea
    return '-'.join(stdout.split('-')[:-1])

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("sv2v.json")
