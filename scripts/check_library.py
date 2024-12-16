import argparse

from siliconcompiler import Chip
from siliconcompiler.tools.opensta import check_library


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-target', help='Reference target', required=True)
    parser.add_argument('-library', nargs='+', help='Library to check', required=True)
    args = parser.parse_args()

    chip = Chip('check_libs')

    chip.node('check_lib', 'check', check_library)
    chip.set('option', 'flow', 'check_lib')
    chip.set('option', 'clean', True)

    target = chip._load_module(args.target)
    chip.use(target)

    chip.unset('asic', 'logiclib')

    for lib in args.library:
        mod = chip._load_module(lib)

        libraries = mod.setup()
        if not isinstance(libraries, (list, tuple)):
            libraries = [libraries]

        for library in libraries:
            if library.design.startswith('lambdalib_'):
                continue
            chip.use(library)
            chip.add('asic', 'logiclib', library.design)

    chip.run()

    return 0


if __name__ == "__main__":
    main()
