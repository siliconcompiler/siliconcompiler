import siliconcompiler

def make_docs():
    '''Subset of OH! library tapeout checklist.

    https://github.com/aolofsson/oh/blob/master/docs/tapeout_checklist.md
    '''
    chip = siliconcompiler.Chip()
    setup(chip)
    return chip

def setup(chip):
    standard = 'oh_tapeout'

    # Automated
    chip.set('checklist', standard, 'drc_clean', 'description',
             'Is block DRC clean?')
    chip.set('checklist', standard, 'drc_clean', 'criteria', 'drvs==0')

    chip.set('checklist', standard, 'lvs_clean', 'description',
             'Is block LVS clean?')
    chip.set('checklist', standard, 'lvs_clean', 'criteria', 'drvs==0')

    chip.set('checklist', standard, 'setup_time', 'description',
             'Setup time met?')
    chip.set('checklist', standard, 'setup_time', 'criteria', 'setupslack>=0')

    chip.set('checklist', standard, 'errors_warnings', 'description',
             'Are all EDA warnings/errors acceptable?')
    chip.set('checklist', standard, 'errors_warnings', 'criteria',
              ['errors==0', 'warnings==0'])

    # Manual
    chip.set('checklist', standard, 'spec', 'description',
        'Is there a written specification?')
