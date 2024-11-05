from siliconcompiler import Chip
from siliconcompiler.tools.opensta import report_libraries


def main():
    chip = Chip('report_libs')
    args = chip.create_cmdline(switchlist=['-target'])

    if 'target' not in args or not args['target']:
        raise ValueError('-target is required')

    chip.node('report_lib', 'report', report_libraries)
    chip.set('option', 'flow', 'report_lib')
    chip.set('option', 'clean', True)

    chip.run()

    return 0


if __name__ == "__main__":
    main()
