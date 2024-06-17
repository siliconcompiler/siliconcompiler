from siliconcompiler import Chip
from siliconcompiler.tools.opensta import report_libraries

if __name__ == "__main__":
    chip = Chip('report_libs')
    chip.create_cmdline(switchlist=['-target'])

    if not chip.get('option', 'target'):
        raise ValueError('-target is required')

    chip.node('report_lib', 'report', report_libraries)
    chip.set('option', 'flow', 'report_lib')

    chip.run()
