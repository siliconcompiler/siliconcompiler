#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('main_kernel')
    chip.register_source("mlir-hls-example", __file__)
    chip.input("main_kernel.ll", package="mlir-hls-example")
    chip.clock(pin='clock', period=5)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()
    chip.show()


if __name__ == '__main__':
    main()
