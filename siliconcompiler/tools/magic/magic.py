import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    Magic is a chip layout viewer, editor, and circuit verifier with
    built in DRC and LVS engines.

    Documentation: http://opencircuitdesign.com/magic/userguide.html

    Installation: https://github.com/RTimothyEdwards/magic

    Sources: https://github.com/RTimothyEdwards/magic

    '''

    chip = siliconcompiler.Chip('<design>')
    from pdks import skywater130
    chip.use(skywater130)
    index = '<index>'
    flow = '<flow>'
    chip.set('arg','index',index)
    chip.set('option', 'flow', flow)

    # check drc
    from tools.magic.drc import setup as setup_drc
    chip.set('arg','step', 'drc')
    chip.set('flowgraph', flow, 'drc', index, 'task', 'drc')
    setup_drc(chip)

    # check lvs
    from tools.magic.extspice import setup as setup_extspice
    chip.set('arg','step', 'extspice')
    chip.set('flowgraph', flow, 'extspice', index, 'task', 'extspice')
    setup(chip)

    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Setup function for 'magic' tool
    '''

    tool = 'magic'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = chip._get_task(step, index)

    # magic used for drc and lvs
    #if step not in ('drc', 'extspice'):
    #    raise ValueError(f"Magic tool doesn't support step {step}.")
    script = 'sc_magic.tcl'

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=8.3.196', clobber=False)
    chip.set('tool', tool, 'format', 'tcl')

    chip.set('tool', tool, 'task', task, 'threads', step, index,  4, clobber=False)
    chip.set('tool', tool, 'task', task, 'refdir', step, index,  refdir, clobber=False)
    chip.set('tool', tool, 'task', task, 'script', step, index,  script, clobber=False)

    # set options
    options = []
    options.append('-noc')
    options.append('-dnull')
    chip.set('tool', tool, 'task', task, 'option', step, index,  options, clobber=False)

    design = chip.top()
    if chip.valid('input', 'layout', 'gds'):
        chip.add('tool', tool, 'task', task, 'require', step, index, ','.join(['input', 'layout', 'gds']))
    else:
        chip.add('tool', tool, 'task', task, 'input', step, index, f'{design}.gds')

    chip.set('tool', tool, 'task', task, 'regex', step, index, 'errors', r'^Error', clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', step, index, 'warnings', r'warning', clobber=False)

################################
# Version Check
################################

def parse_version(stdout):
    return stdout.strip('\n')

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("magic.json")
