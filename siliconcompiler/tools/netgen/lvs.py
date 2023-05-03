import os

from siliconcompiler.tools.netgen import count_lvs


def setup(chip):
    '''
    Perform LVS on the supplied netlists
    '''

    tool = 'netgen'
    refdir = 'tools/' + tool
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    # magic used for drc and lvs
    script = 'sc_lvs.tcl'

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '-batch')
    chip.set('tool', tool, 'version', '>=1.5.192', clobber=False)
    chip.set('tool', tool, 'format', 'tcl')

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'script', script,
             step=step, index=index, clobber=False)

    # set options
    options = []
    options.append('-batch')
    options.append('source')
    chip.set('tool', tool, 'task', task, 'option', options, step=step, index=index, clobber=False)

    design = chip.top()
    chip.add('tool', tool, 'task', task, 'input', f'{design}.spice', step=step, index=index)
    if chip.valid('input', 'netlist', 'verilog'):
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['input', 'netlist', 'verilog']),
                 step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'input', f'{design}.vg', step=step, index=index)

    # Netgen doesn't have a standard error prefix that we can grep for, but it
    # does print all errors to stderr, so we can redirect them to <step>.errors
    # and use that file to count errors.
    chip.set('tool', tool, 'task', task, 'stderr', 'suffix', 'errors', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'regex', 'warnings', '^Warning:',
             step=step, index=index, clobber=False)


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
    chip._record_metric(step, index, 'errors', errors, f'{step}.errors')

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
    chip._record_metric(step, index, 'drvs', errors, lvs_report)
    chip._record_metric(step, index, 'warnings', pin_failures, lvs_report)
