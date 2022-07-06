# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import shutil

from siliconcompiler.core import Chip

###
# Example build script: 'heartbeat' example with padring and pre-made .def floorplans.
#
# This script builds a minimal design with a padring, but it uses pre-built floorplan files
# instead of generating them using the Python floorplanning API. It is intended to demonstrate
# a hierarchical build process with a flat top-level design, without the added complexity of
# generating floorplans from scratch.
###

# Directory prefixes for third-party files.
SCROOT = '../..'
OH_PREFIX = f'{SCROOT}/third_party/designs/oh'
SKY130IO_PREFIX = f'{SCROOT}/third_party/pdks/skywater/skywater130/libs/sky130io/v0_0_2'

def configure_chip(design):
    # Minimal Chip object construction.
    chip = Chip(design)
    chip.load_target('skywater130_demo')

    # Include I/O macro lib.
    chip.load_lib('sky130io')
    chip.add('asic', 'macrolib', 'sky130io')

    # Configure 'show' apps, and return the Chip object.
    chip.set('option', 'showtool', 'def', 'klayout')
    chip.set('option', 'showtool', 'gds', 'klayout')
    return chip

def build_core():
    # Build the core internal design.
    core_chip = configure_chip('heartbeat')
    core_chip.write_manifest('heartbeat_manifest.json')

    # Configure the Chip object for a full build.
    core_chip.set('input', 'floorplan.def', 'floorplan/heartbeat.def', clobber=True)
    core_chip.set('input', 'verilog', 'heartbeat.v')
    core_chip.set('tool', 'openroad', 'var', 'place', '0', 'place_density', ['0.15'])
    core_chip.set('tool', 'openroad', 'var', 'route', '0', 'grt_allow_congestion', ['true'])
    core_chip.clock('clk', period=20)

    # Run the actual ASIC build flow with the resulting floorplan.
    core_chip.run()
    # (Un-comment to display a summary report)
    #core_chip.summary()

    # Copy stream files for padring integration.
    design = core_chip.get_entrypoint()
    gds_result = core_chip.find_result('gds', step='export')
    vg_result = core_chip.find_result('vg', step='dfm')
    shutil.copy(gds_result, f'{design}.gds')
    shutil.copy(vg_result, f'{design}.vg')

def build_top():
    # Build the top-level design, with padring.
    chip = configure_chip('heartbeat_top')

    # Use 'asictopflow' to combine the padring macros with the core 'heartbeat' macro.
    flow = 'asictopflow'
    chip.set('option', 'flow', flow)

    # Configure inputs for the top-level design.
    libname = 'heartbeat'
    stackup = chip.get('asic', 'stackup')
    chip.add('asic', 'macrolib', libname)
    lib = Chip(libname)
    lib.set('model', 'layout', 'lef', stackup, 'floorplan/heartbeat.lef')
    lib.set('model', 'layout', 'gds', stackup, 'heartbeat.gds')
    lib.set('output', 'netlist', 'heartbeat.vg')
    chip.import_library(lib)
    chip.set('input', 'def', 'floorplan/heartbeat_top.def')

    chip.set('input', 'verilog', 'heartbeat_top.v')
    chip.add('input', 'verilog', 'heartbeat.bb.v')
    # (Padring sources needed for the 'syn' step of asictopflow)
    chip.add('input', 'verilog', f'{OH_PREFIX}/padring/hdl/oh_padring.v')
    chip.add('input', 'verilog', f'{OH_PREFIX}/padring/hdl/oh_pads_domain.v')
    chip.add('input', 'verilog', f'{OH_PREFIX}/padring/hdl/oh_pads_corner.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/asic_iobuf.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/asic_iovdd.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/asic_iovddio.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/asic_iovss.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/asic_iovssio.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/asic_iocorner.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/asic_iopoc.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/asic_iocut.v')
    chip.add('input', 'verilog', f'{SKY130IO_PREFIX}/io/sky130_io.blackbox.v')

    chip.write_manifest('top_manifest.json')

    # There are errors in KLayout export
    chip.set('option', 'flowcontinue', True)

    # Run the top-level build.
    chip.run()
    # (Un-comment to display a summary report)
    #chip.summary()

def main():
    # Build the core design, which gets placed inside the padring.
    build_core()
    # Build the top-level design by stacking the core into the middle of the padring.
    build_top()

if __name__ == '__main__':
    main()
