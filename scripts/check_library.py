from siliconcompiler import Chip
from siliconcompiler.tools.opensta import check_library


def main():
    chip = Chip('check_libs')
    args = chip.create_cmdline(switchlist=['-target'])

    if 'target' not in args or not args['target']:
        raise ValueError('-target is required')

    chip.node('check_lib', 'check', check_library)
    chip.set('option', 'flow', 'check_lib')
    chip.set('option', 'clean', True)

    chip.run()

    return 0


if __name__ == "__main__":
    main()
