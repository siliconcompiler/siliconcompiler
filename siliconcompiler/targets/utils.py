# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

def set_common_showtools(chip):

    # Physical only
    chip.set('option', 'showtool', 'gds', 'klayout')
    chip.set('option', 'showtool', 'lef', 'klayout')

    # Design
    chip.set('option', 'showtool', 'def', 'openroad')
    chip.set('option', 'showtool', 'odb', 'openroad')
