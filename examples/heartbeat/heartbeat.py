#!/usr/bin/env python3

import siliconcompiler                        # import python package


def main():
    chip = siliconcompiler.Chip('heartbeat')  # create chip object
    chip.input('heartbeat.v')                 # define list of source files
    chip.input('heartbeat.sdc')               # set constraints file
    chip.load_target("freepdk45_demo")        # load predefined target
    chip.run()                                # run compilation
    chip.summary()                            # print results summary
    chip.show()                               # show layout file


if __name__ == '__main__':
    main()
