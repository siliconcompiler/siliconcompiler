# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

def set_common_showtools(chip):

    # Physical only
    chip.set('option', 'showtool', 'gds', 'klayout', clobber=False)
    chip.set('option', 'showtool', 'lef', 'klayout', clobber=False)

    # Design
    chip.set('option', 'showtool', 'def', 'openroad', clobber=False)
    chip.set('option', 'showtool', 'odb', 'openroad', clobber=False)
