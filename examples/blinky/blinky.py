#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import fpgaflow_demo


def main():
    chip = Chip('blinky')

    chip.register_source("blinky-example", __file__)

    chip.input("blinky.v", package="blinky-example")
    chip.input("icebreaker.pcf", package="blinky-example")
    chip.set('fpga', 'partname', 'ice40up5k-sg48')

    chip.use(fpgaflow_demo)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
