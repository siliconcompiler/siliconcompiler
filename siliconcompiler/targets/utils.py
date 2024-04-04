# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler.tools.klayout import (
    klayout,
    show as klayout_show,
    screenshot as klayout_screenshot)
from siliconcompiler.tools.openroad import (
    openroad,
    show as openroad_show,
    screenshot as openroad_screenshot)
from siliconcompiler.tools.vpr import (
    vpr,
    show as vpr_show,
    screenshot as vpr_screenshot)


def set_common_showtools(chip):

    # Physical only
    chip.set('option', 'showtool', 'gds', 'klayout', clobber=False)
    chip.set('option', 'showtool', 'lef', 'klayout', clobber=False)
    chip._load_module(klayout.__name__)
    chip._load_module(klayout_show.__name__)
    chip._load_module(klayout_screenshot.__name__)

    # Design
    chip.set('option', 'showtool', 'def', 'openroad', clobber=False)
    chip.set('option', 'showtool', 'odb', 'openroad', clobber=False)
    chip._load_module(openroad.__name__)
    chip._load_module(openroad_show.__name__)
    chip._load_module(openroad_screenshot.__name__)

    # VPR
    chip.set('option', 'showtool', 'route', 'vpr', clobber=False)
    chip.set('option', 'showtool', 'place', 'vpr', clobber=False)
    chip._load_module(vpr.__name__)
    chip._load_module(vpr_show.__name__)
    chip._load_module(vpr_screenshot.__name__)
