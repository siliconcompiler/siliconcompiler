#!/usr/bin/env python3

import siliconcompiler                        # import python package
import os


def main():
    root = os.path.dirname(__file__)
    chip = siliconcompiler.Chip('heartbeat')  # create chip object
    chip.input(f'{root}/heartbeat.v')                 # define list of source files
    chip.input(f'{root}/heartbeat.sdc')               # set constraints file
    chip.load_target("freepdk45_demo")        # load predefined target
    chip.run()                                # run compilation
    chip.summary()                            # print results summary
    chip.show()                               # show layout file


if __name__ == '__main__':
    main()
