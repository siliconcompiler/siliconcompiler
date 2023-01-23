import importlib
import os

import siliconcompiler
from siliconcompiler.tools.netgen import count_lvs

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    Netgen is a tool for comparing netlists. By comparing a Verilog netlist with
    one extracted from a circuit layout, it can be used to perform LVS
    verification.

    Documentation: http://www.opencircuitdesign.com/netgen/

    Installation: https://github.com/RTimothyEdwards/netgen

    Sources: https://github.com/RTimothyEdwards/netgen

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.load_pdk('skywater130')
    step = 'lvs'
    index = '<index>'
    flow = '<flow>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('option', 'flow', flow)
    chip.set('flowgraph', flow, step, index, 'task', '<task>')
    from tools.netgen.lvs import setup
    setup(chip)

    return chip

################################
# Version Check
################################

def parse_version(stdout):
    # First line: Netgen 1.5.190 compiled on Fri Jun 25 16:05:36 EDT 2021
    return stdout.split()[1]

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution

    Reads error count from output and fills in appropriate entry in metrics
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    design = chip.top()

    with open(f'{step}.errors', 'r') as f:
        errors = len(f.readlines())
    chip.set('metric', step, index, 'errors', errors)

    if step == 'lvs':
        # Export metrics
        lvs_report = f'reports/{design}.lvs.json'
        if not os.path.isfile(lvs_report):
            chip.logger.warning('No LVS report generated. Netgen may have encountered errors.')
            return

        lvs_failures = count_lvs.count_LVS_failures(lvs_report)

        # We don't count top-level pin mismatches as errors b/c we seem to get
        # false positives for disconnected pins. Report them as warnings
        # instead, the designer can then take a look at the full report for
        # details.
        pin_failures = lvs_failures[3]
        errors = lvs_failures[0] - pin_failures
        chip.set('metric', step, index, 'drvs', errors)
        chip.set('metric', step, index, 'warnings', pin_failures)

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("netgen.json")
