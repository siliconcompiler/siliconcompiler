#!/usr/bin/env python3

import siliconcompiler                        # import python package
from siliconcompiler.flows import dvflow


def main():
    chip = siliconcompiler.Chip('heartbeat')  # create chip object
    chip.input('heartbeat.v')                 # define list of source files
    chip.input('testbench.v')                 # define list of source files

    chip.set('option', 'mode', 'sim')
    flowname = 'heartbeat_sim'
    chip.use(dvflow, flowname=flowname)
    chip.set('option', 'flow', flowname)

    chip.run()                                # run compilation
    chip.summary()                            # print results summary


if __name__ == '__main__':
    main()
