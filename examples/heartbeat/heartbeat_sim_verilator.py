#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.flows import dvflow


def main():
    chip = Chip('heartbeat')

    chip.register_source("heartbeat-example", __file__)
    chip.input("heartbeat.v", package="heartbeat-example")
    chip.input("testbench.cc", package="heartbeat-example")

    chip.use(dvflow, flowname='heartbeat_sim', tool='verilator')
    chip.set('option', 'flow', 'heartbeat_sim')
    chip.set('tool', 'verilator', 'task', 'compile', 'var', 'trace', True)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
