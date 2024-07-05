import siliconcompiler


def setup(chip):
    '''Subset of OH! library tapeout checklist.

    https://github.com/aolofsson/oh/blob/master/docs/tapeout_checklist.md
    '''
    standard = 'oh_tapeout'

    checklist = siliconcompiler.Checklist(chip, standard)

    # Automated
    checklist.set('checklist', standard, 'drc_clean', 'description',
                  'Is block DRC clean?')
    checklist.set('checklist', standard, 'drc_clean', 'criteria', 'drcs==0')

    checklist.set('checklist', standard, 'lvs_clean', 'description',
                  'Is block LVS clean?')
    checklist.set('checklist', standard, 'lvs_clean', 'criteria', 'drcs==0')

    checklist.set('checklist', standard, 'setup_time', 'description',
                  'Setup time met?')
    checklist.set('checklist', standard, 'setup_time', 'criteria', 'setupslack>=0')

    checklist.set('checklist', standard, 'errors_warnings', 'description',
                  'Are all EDA warnings/errors acceptable?')
    checklist.set('checklist', standard, 'errors_warnings', 'criteria',
                  ['errors==0', 'warnings==0'])

    # Manual
    checklist.set('checklist', standard, 'spec', 'description',
                  'Is there a written specification?')

    return checklist


##################################################
if __name__ == "__main__":
    checklist = setup(siliconcompiler.Chip('<checklist>'))
    checklist.write_manifest(f"{checklist.top()}.json")
