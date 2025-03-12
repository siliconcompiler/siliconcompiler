#!/usr/bin/env python3

from siliconcompiler import Chip                              # import python package
from siliconcompiler.targets import fpgaflow_demo


def main():
    chip = Chip('heartbeat')                                  # create chip object
    chip.set('fpga', 'partname', 'xc7a100tcsg324')            # set fpga part name
    chip.register_source("heartbeat-example", __file__)       # register file source
    chip.input("heartbeat.v", package="heartbeat-example")    # define list of source files
    chip.input("heartbeat.xdc", package="heartbeat-example")  # set constraints file
    chip.use(fpgaflow_demo)                                   # load predefined target
    chip.run()                                                # run compilation
    chip.summary()                                            # print results summary


if __name__ == '__main__':
    main()
