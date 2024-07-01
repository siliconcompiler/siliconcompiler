# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
from siliconcompiler import SiliconCompilerError
from siliconcompiler.scheduler import _runtask, _executenode


def main():
    progname = "sc-run"
    chip = siliconcompiler.Chip(progname)
    switchlist = ['-cfg',
                  '-loglevel',
                  '-relax',
                  '-quiet']
    description = """
    -----------------------------------------------------------
    Restricted SC app that accepts one or more json based cfg files
    as inputs and executes the SC run() method.
    -----------------------------------------------------------
    """
    try:
        chip.create_cmdline(progname,
                            switchlist=switchlist,
                            description=description)
    except Exception as e:
        chip.logger.error(e)
        return 1

    # Error checking
    if not chip.get('option', 'cfg'):
        chip.logger.error(f"{progname}: the following arguments are required: -cfg")
        return 1

    try:
        # Run flow
        if chip.get('arg', 'step') and chip.get('arg', 'index'):
            _runtask(chip,
                     chip.get('option', 'flow'),
                     chip.get('arg', 'step'),
                     chip.get('arg', 'index'),
                     {},
                     _executenode)
        else:
            chip.run()
    except SiliconCompilerError:
        return 1

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
