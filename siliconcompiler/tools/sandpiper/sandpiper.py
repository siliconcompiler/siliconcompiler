
'''
Transaction-Level Verilog (TL-Verilog) is an emerging extension to SystemVerilog that supports a new design methodology, called transaction-level design. 
A transaction, in this methodology, is an entity that moves through structures like pipelines, arbiters, and queues. 
A transaction might be a machine instruction, a flit of a packet, or a memory read/write. Transaction logic, like packet header decode or instruction execution, 
that operates on the transaction can be placed anywhere along the transaction's flow. Tools produce the logic to carry signals through their flows to stitch the transaction logic.

Documentation: https://makerchip.com/sandbox/#

Sources: https://github.com/TL-X-org/tlv-comp

Installation of Sandpiper-SaaS: pip install sandpiper-saas
'''

from siliconcompiler.tools.sandpiper import convert


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    convert.setup(chip)
    return chip


# Directory inside step/index dir to store tlv intermediate results.
VLOG_DIR = 'verilog'


################################
# Setup Tool (pre executable)
################################
def parse_version(stdout):
    # Sandpiper does not have an explicit versioning system
    pass



################################
#  Custom runtime options
################################
def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    cmdlist = []

    design = chip.top()
    sources = chip.find_files('input', 'hll', 'tlv', step=step, index=index)
    print("sources ",sources)
    if len(sources) != 1:
        raise ValueError('Sandpiper-saas only supports one source file!')
    cmdlist.append('-i '+sources[0])
    cmdlist.append(f'-o {design}.sv')
    cmdlist.append('--bestsv')
    cmdlist.append(f'--outdir {VLOG_DIR}')
    cmdlist.append('--inlineGen')
    cmdlist.append('--noline')
    cmdlist.append(f'--default_includes')

    return cmdlist
