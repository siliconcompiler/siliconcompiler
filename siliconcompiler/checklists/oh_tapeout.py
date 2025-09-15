from siliconcompiler import Checklist


class OHTapeoutChecklist(Checklist):
    '''
    Subset of OH! library tapeout checklist.

    https://github.com/aolofsson/oh/blob/b8a962e61b7ea359ba6dacf6e4c12171287164f1/docs/tapeout_checklist.md
    '''
    def __init__(self):
        super().__init__("oh_tapeout")

        # Automated
        self.set('drc_clean', 'description', 'Is block DRC clean?')
        self.set('drc_clean', 'criteria', 'drcs==0')

        self.set('lvs_clean', 'description', 'Is block LVS clean?')
        self.set('lvs_clean', 'criteria', 'drcs==0')

        self.set('setup_time', 'description', 'Setup time met?')
        self.set('setup_time', 'criteria', 'setupslack>=0')

        self.set('errors_warnings', 'description', 'Are all EDA warnings/errors acceptable?')
        self.set('errors_warnings', 'criteria', ['errors==0', 'warnings==0'])

        # Manual
        self.set('spec', 'description', 'Is there a written specification?')
