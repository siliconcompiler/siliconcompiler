#!/usr/bin/env python3

import siliconcompiler
from siliconcompiler.flows import dvflow
import os


def main():
    root = os.path.dirname(__file__)

    chip = siliconcompiler.Chip('heartbeat')
    chip.input(os.path.join(root, "heartbeat.v"))

    chip.input(os.path.join(root, "testbench.v"))

    flowname = 'heartbeat_sim'
    chip.use(dvflow, flowname=flowname, tool='icarus')
    chip.set('option', 'flow', flowname)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
