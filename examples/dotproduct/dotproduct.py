#!/usr/bin/env python3

import siliconcompiler
import os
from siliconcompiler.targets import freepdk45_demo


def main():
    root = os.path.dirname(__file__)
    chip = siliconcompiler.Chip('mkDotProduct_nt_Int32')
    chip.input(os.path.join(root, 'DotProduct_nt_Int32.bsv'))
    chip.add('option', 'ydir', root)

    chip.set('option', 'nodisplay', True)
    chip.set('option', 'quiet', True)
    chip.clock(pin='CLK', period=1)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
