#!/usr/bin/env python3

import siliconcompiler                        # import python package
from siliconcompiler.flows import dvflow
import os


def main():
    root = os.path.dirname(__file__)
    chip = siliconcompiler.Chip('heartbeat')  # create chip object
    chip.input(os.path.join(root, "heartbeat.v"))                 # define list of source files
    chip.input(os.path.join(root, "testbench.v"))                 # define list of source files

    flowname = 'heartbeat_sim'
    chip.use(dvflow, flowname=flowname)
    chip.set('option', 'flow', flowname)

    chip.run()                                # run compilation
    chip.summary()                            # print results summary


if __name__ == '__main__':
    main()
