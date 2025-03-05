#!/usr/bin/env python3

import siliconcompiler                        # import python package
from siliconcompiler.targets import asap7_demo


def main():
    chip = siliconcompiler.Chip('heartbeat')  # create chip object
    chip.input("heartbeat.v")                 # define list of source files
    chip.input("heartbeat_asap7.sdc")         # set constraints file
    chip.use(asap7_demo)                      # load predefined target
    chip.set('option', 'quiet', True)         # turn off tool output
    chip.set('option', 'jobname', 'demo0')    # set jobname
    chip.run()                                # run compilation
    chip.summary()                            # print results summary


if __name__ == '__main__':
    main()
