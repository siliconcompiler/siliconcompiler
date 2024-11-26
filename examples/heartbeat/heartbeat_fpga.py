#!/usr/bin/env python3

import siliconcompiler                               # import python package
import os
from siliconcompiler.targets import fpgaflow_demo


def main():
    root = os.path.dirname(__file__)
    chip = siliconcompiler.Chip('heartbeat')         # create chip object
    chip.set('fpga', 'partname', 'xc7a100tcsg324')   # set fpga part name
    chip.input(os.path.join(root, "heartbeat.v"))    # define list of source files
    chip.input(os.path.join(root, "heartbeat.xdc"))  # set constraints file
    chip.use(fpgaflow_demo)                          # load predefined target
    chip.run()                                       # run compilation
    chip.summary()                                   # print results summary


if __name__ == '__main__':
    main()
