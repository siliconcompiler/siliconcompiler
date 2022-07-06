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
    chip.set('arg','index','<index>')
    chip.set('arg','step', 'lvs')
    setup(chip)

    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Setup function for 'magic' tool
    '''

    tool = 'netgen'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # magic used for drc and lvs
    script = 'sc_lvs.tcl'

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '-batch')
    chip.set('tool', tool, 'version', '>=1.5.192', clobber=False)
    chip.set('tool', tool, 'format', 'tcl')
    chip.set('tool', tool, 'threads', step, index, 4, clobber=False)
    chip.set('tool', tool, 'refdir', step, index, refdir, clobber=False)
    chip.set('tool', tool, 'script', step, index, script, clobber=False)

    # set options
    options = []
    options.append('-batch')
    options.append('source')
    chip.set('tool', tool, 'option', step, index, options, clobber=False)

    design = chip.get_entrypoint()
    chip.add('tool', tool, 'input', step, index, f'{design}.spice')
    if chip.valid('input', 'netlist'):
        chip.add('tool', tool, 'require', step, index, ','.join(['input', 'netlist']))
    else:
        chip.add('tool', tool, 'input', step, index, f'{design}.vg')

    # Netgen doesn't have a standard error prefix that we can grep for, but it
    # does print all errors to stderr, so we can redirect them to <step>.errors
    # and use that file to count errors.
    chip.set('tool', tool, 'stderr', step, index, 'suffix', 'errors')
    chip.set('tool', tool, 'report', step, index, 'errors', f'{step}.errors')

    chip.set('tool', tool, 'regex', step, index, 'warnings', '^Warning:', clobber=False)

    report_path = f'reports/{design}.lvs.out'
    chip.set('tool', tool, 'report', step, index, 'drvs', report_path)
    chip.set('tool', tool, 'report', step, index, 'warnings', report_path)

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
    design = chip.get_entrypoint()

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
