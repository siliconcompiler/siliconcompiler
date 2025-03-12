#!/usr/bin/env python3

from siliconcompiler import Chip                              # import python package
from siliconcompiler.targets import freepdk45_demo


def main():
    chip = Chip('heartbeat')                                  # create chip object
    chip.register_source("heartbeat-example", __file__)       # register file source
    chip.input("heartbeat.v", package="heartbeat-example")    # define source files
    chip.input("heartbeat.sdc", package="heartbeat-example")  # set constraints file
    chip.use(freepdk45_demo)                                  # load predefined target
    chip.run()                                                # run compilation
    chip.summary()                                            # print results summary
    chip.show()                                               # show layout file


if __name__ == '__main__':
    main()
