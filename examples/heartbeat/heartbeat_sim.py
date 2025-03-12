#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.flows import dvflow


def main():
    chip = Chip('heartbeat_tb')
    chip.register_source("heartbeat-example", __file__)
    chip.input("heartbeat.v", package="heartbeat-example")

    chip.input("testbench.v", package="heartbeat-example")

    chip.use(dvflow, flowname='heartbeat_sim', tool='icarus')
    chip.set('option', 'flow', 'heartbeat_sim')

    chip.run()
    chip.summary()

    chip.show(chip.find_node_file('reports/heartbeat_tb.vcd', step='sim', index='0'))


if __name__ == '__main__':
    main()
