#!/usr/bin/env python3
# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import Chip
from siliconcompiler.libs import sky130io
from siliconcompiler.utils import register_sc_data_source
import os
import lambdalib

###
# Example build script: 'heartbeat' example with padring and pre-made .def floorplans.
#
# This script builds a minimal design with a padring, but it uses pre-built floorplan files
# instead of generating them using the Python floorplanning API. It is intended to demonstrate
# a hierarchical build process with a flat top-level design, without the added complexity of
# generating floorplans from scratch.
###

# Directory prefixes for third-party files.
root = os.path.dirname(__file__)


def configure_chip(design):
    # Minimal Chip object construction.
    chip = Chip(design)
    chip.load_target("skywater130_demo")

    # Include I/O macro lib.
    chip.use(sky130io)
    chip.add('asic', 'macrolib', 'sky130io')

    chip.set('tool', 'openroad', 'task', 'export', 'var', 'write_cdl', 'false')

    return chip


def build_core():
    # Build the core internal design.
    core_chip = configure_chip('heartbeat')
    core_chip.write_manifest('heartbeat_manifest.json')

    # Configure the Chip object for a full build.
    core_chip.input(f'{root}/heartbeat.v')
    core_chip.clock('clk', period=20)

    # Run the actual ASIC build flow with the resulting floorplan.
    core_chip.run()
    # (Un-comment to display a summary report)
    core_chip.summary()

    # Setup outputs
    stackup = core_chip.get('option', 'stackup')
    core_chip.set('output', stackup, 'lef', core_chip.find_result('lef', step='export', index='1'))
    core_chip.set('output', stackup, 'gds', core_chip.find_result('gds', step='export', index='0'))
    for scenario in core_chip.getkeys('constraint', 'timing'):
        libcorner = core_chip.get('constraint', 'timing', scenario, 'libcorner',
                                  step='export', index='1')[0]
        core_chip.set('output', libcorner, 'nldm',
                      core_chip.find_result(f'{libcorner}.lib', step='export', index='1'))

    return core_chip


def build_top(core_chip):
    # Build the top-level design, with padring.
    chip = configure_chip('heartbeat_top')

    register_sc_data_source(chip)

    # Use 'asictopflow' to combine the padring macros with the core 'heartbeat' macro.
    flow = 'asictopflow'
    chip.set('option', 'flow', flow)

    chip.use(core_chip)
    chip.add('asic', 'macrolib', core_chip.design)
    chip.input(f'{root}/floorplan/heartbeat_top.def')

    chip.use(lambdalib)
    chip.add('option', 'ydir', 'lambdalib/padring/rtl', package='lambdalib')
    chip.add('option', 'idir', 'lambdalib/padring/rtl', package='lambdalib')
    chip.add('option', 'ydir', 'lambdapdk/sky130/libs/sky130io/lambda', package='lambdapdk')

    chip.input(f'{root}/heartbeat_top.v')

    chip.write_manifest('top_manifest.json')

    # There are errors in KLayout export
    chip.set('option', 'flowcontinue', True)

    # Run the top-level build.
    chip.run()
    # (Un-comment to display a summary report)
    chip.summary()


def main():
    # Build the core design, which gets placed inside the padring.
    core = build_core()
    # Build the top-level design by stacking the core into the middle of the padring.
    build_top(core)


if __name__ == '__main__':
    main()
