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

def configure_chip(design):
    # Minimal Chip object construction.
    chip = Chip()
    chip.load_target('skywater130_demo')
    chip.set('design', design)

    # Include I/O macro lib.
    stackup = chip.get('asic', 'stackup')
    libname = 'io'
    chip.add('library', libname, 'nldm', 'typical', 'lib', 'asic/sky130/io/sky130_dummy_io.lib')
    chip.set('library', libname, 'lef', stackup, 'asic/sky130/io/sky130_ef_io.lef')
    chip.add('library', libname, 'gds', stackup, 'asic/sky130/io/sky130_ef_io.gds')
    chip.add('library', libname, 'gds', stackup, 'asic/sky130/io/sky130_fd_io.gds')
    chip.add('library', libname, 'gds', stackup, 'asic/sky130/io/sky130_ef_io__gpiov2_pad_wrapped.gds')
    chip.add('asic', 'macrolib', libname)
    chip.set('library', libname, 'type', 'component')

    # TODO: This param goes under ['asic', 'exclude', step, index, ...] now.
    # But I think it's used by DRC checks, which aren't currently enabled in this test design.
    #chip.set('asic', 'exclude', ['io'])

    # Configure 'show' apps, and return the Chip object.
    chip.set('showtool', 'def', 'klayout')
    chip.set('showtool', 'gds', 'klayout')
    return chip

def build_core():
    # Build the core internal design.
    core_chip = configure_chip('heartbeat')
    core_chip.write_manifest('heartbeat_manifest.json')

    # Configure the Chip object for a full build.
    core_chip.set('read', 'def', 'floorplan', '0', 'floorplan/heartbeat.def', clobber=True)
    core_chip.set('source', 'heartbeat.v')
    core_chip.add('source', 'asic/sky130/prim_sky130_clock_gating.v')
    core_chip.set('eda', 'openroad', 'variable', 'place', '0', 'place_density', ['0.15'])
    core_chip.set('eda', 'openroad', 'variable', 'route', '0', 'grt_allow_congestion', ['true'])
    core_chip.clock(name='clk', pin='clk', period=20)

    # Run the actual ASIC build flow with the resulting floorplan.
    core_chip.run()
    # (Un-comment to display a summary report)
    #core_chip.summary()

    # Copy stream files for padring integration.
    design = core_chip.get('design')
    jobdir = (core_chip.get('dir') +
            "/" + design + "/" +
            core_chip.get('jobname'))
    shutil.copy(f'{jobdir}/export/0/outputs/{design}.gds', f'{design}.gds')
    shutil.copy(f'{jobdir}/dfm/0/outputs/{design}.vg', f'{design}.vg')

def build_top():
    # Build the top-level design, with padring.
    chip = configure_chip('heartbeat_top')

    # Use 'asictopflow' to combine the padring macros with the core 'heartbeat' macro.
    flow = 'asictopflow'
    chip.set('flow', flow)

    # Configure inputs for the top-level design.
    libname = 'heartbeat'
    stackup = chip.get('asic', 'stackup')
    chip.add('asic', 'macrolib', libname)
    chip.set('library', libname, 'type', 'component')
    chip.set('library', libname, 'lef', stackup, 'floorplan/heartbeat.lef')
    chip.set('library', libname, 'gds', stackup, 'heartbeat.gds')
    #chip.set('library', libname, 'cells', 'heartbeat', 'heartbeat')
    chip.set('library', libname, 'netlist', 'verilog', 'heartbeat.vg')
    chip.set('read', 'def', 'export', '0', 'floorplan/heartbeat_top.def')

    chip.set('source', 'heartbeat_top.v')
    chip.add('source', 'heartbeat.bb.v')
    # (Padring sources needed for the 'syn' step of asictopflow)
    chip.add('source', 'oh/padring/hdl/oh_padring.v')
    chip.add('source', 'oh/padring/hdl/oh_pads_domain.v')
    chip.add('source', 'oh/padring/hdl/oh_pads_corner.v')
    chip.add('source', 'asic/sky130/io/asic_iobuf.v')
    chip.add('source', 'asic/sky130/io/asic_iovdd.v')
    chip.add('source', 'asic/sky130/io/asic_iovddio.v')
    chip.add('source', 'asic/sky130/io/asic_iovss.v')
    chip.add('source', 'asic/sky130/io/asic_iovssio.v')
    chip.add('source', 'asic/sky130/io/asic_iocorner.v')
    chip.add('source', 'asic/sky130/io/asic_iopoc.v')
    chip.add('source', 'asic/sky130/io/asic_iocut.v')
    chip.add('source', 'asic/sky130/io/sky130_io.blackbox.v')

    chip.write_manifest('top_manifest.json')

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
