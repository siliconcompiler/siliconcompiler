# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import shutil

from siliconcompiler.core import Chip
from siliconcompiler.floorplan import Floorplan

###
# Example Skywater130 / "Caravel" macro hardening with SiliconCompiler
#
# This script builds a minimal 'heartbeat' example into the Caravel harness provided by
# eFabless for their MPW runs, connecting the 3 I/O signals to the wrapper's I/O pins.
# Other Caravel signals such as the Wishbone bus, IRQ, etc. are ignored.
#
# These settings have not been tested with one of eFabless' MPW runs yet, but
# it demonstrates how to run a 'caravel_user_project' build process using SiliconCompiler.
# The basic idea is to harden the core design as a macro with half of a power delivery grid and
# a blockage on the top metal layer. The top-level design's I/O signals are then routed to the
# macro pins, and the top-level PDN is connected by running its top-layer straps over the macro
# and connecting the straps with 'define_pdn_grid -existing'.
#
# The 'pdngen' and 'macroplace' parameters used here and in 'tools/openroad/sc_floorplan.tcl'
# can demonstrate one way to insert custom TCL commands into a tool flow.
###

# User project wrapper area is 2.92mm x 3.52mm
TOP_W = 2920
TOP_H = 3520
# Example design area is 0.9mm x 0.6mm
CORE_W = 900
CORE_H = 600
# Margins are set to ~10mm, snapped to placement site dimensions (0.46mm x 2.72mm in sky130hd)
MARGIN_W = 9.66
MARGIN_H = 8.16

def configure_chip(design):
    # Minimal Chip object construction.
    chip = Chip()
    chip.load_target('skywater130_demo')
    chip.set('design', design)

    # Configure 'show' apps, and return the Chip object.
    chip.set('showtool', 'def', 'klayout')
    chip.set('showtool', 'gds', 'klayout')
    return chip

def build_core():
    # Harden the 'heartbeat' module. Following the example set in 'user_proj_example',
    # We can skip a detailed floorplan and let the router connect top-level I/O signals.
    core_chip = configure_chip('heartbeat')
    design = core_chip.get('design')
    core_chip.set('source', 'heartbeat.v')
    core_chip.set('eda', 'openroad', 'variable', 'place', '0', 'place_density', ['0.15'])
    core_chip.set('eda', 'openroad', 'variable', 'route', '0', 'grt_allow_congestion', ['true'])
    core_chip.clock(name='clk', pin='clk', period=20)

    # Set user design die/core area.
    core_chip.set('asic', 'diearea', (0, 0))
    core_chip.add('asic', 'diearea', (CORE_W, CORE_H))
    core_chip.set('asic', 'corearea', (MARGIN_W, MARGIN_H))
    core_chip.add('asic', 'corearea', (CORE_W - MARGIN_W, CORE_H - MARGIN_H))

    # Create basic PDN script, with only vertical stripes.
    stackup = core_chip.get('asic', 'stackup')
    libtype = 'hd'
    with open('pdngen.tcl', 'w') as pdnf:
        # TODO: Jinja template?
        pdnf.write('''
# Add PDN connections for each voltage domain.
add_global_connection -net vccd1 -pin_pattern "^vccd.*$" -power
add_global_connection -net vssd1 -pin_pattern "^vssd.*$" -ground

# Create single-layer core-level PDN grid.
define_pdn_grid -name pdn_grid -starts_with POWER -voltage_domain CORE -pins {met4}
# Add vertical stripes. (No horizontal stripes; those come from the top level.)
add_pdn_stripe -grid pdn_grid -layer met4 -width 1.6 -pitch 150 -offset 75 -starts_with POWER

# Done defining commands; execute pdngen.
pdngen''')
    core_chip.set('pdk', 'aprtech', 'openroad', stackup, libtype, 'pdngen', 'pdngen.tcl')

    # Build the core design.
    core_chip.run()

    # Copy GDS/DEF/LEF files for use in the top-level build.
    jobdir = (core_chip.get('dir') +
            "/" + design + "/" +
            core_chip.get('jobname'))
    shutil.copy(f'{jobdir}/export/0/outputs/{design}.gds', f'{design}.gds')
    shutil.copy(f'{jobdir}/export/0/inputs/{design}.def', f'{design}.def')
    shutil.copy(f'{jobdir}/floorplan/0/outputs/{design}.lef', f'{design}.lef')
    shutil.copy(f'{jobdir}/dfm/0/outputs/{design}.vg', f'{design}.vg')

def build_top():
    # The 'hearbeat' RTL goes in a modified 'user_project_wrapper' object, see sources.
    chip = configure_chip('user_project_wrapper')
    chip.set('eda', 'openroad', 'variable', 'place', '0', 'place_density', ['0.15'])
    chip.set('eda', 'openroad', 'variable', 'route', '0', 'grt_allow_congestion', ['true'])
    chip.clock(name='clk', pin='clk', period=20)

    # Set top-level source files.
    chip.set('source', 'caravel_user_project/caravel/verilog/rtl/defines.v')
    chip.add('source', 'heartbeat.bb.v')
    chip.add('source', 'user_project_wrapper.v')

    # Set top-level die/core area.
    chip.set('asic', 'diearea', (0, 0))
    chip.add('asic', 'diearea', (TOP_W, TOP_H))
    chip.set('asic', 'corearea', (MARGIN_W, MARGIN_H))
    chip.add('asic', 'corearea', (TOP_W - MARGIN_W, TOP_H - MARGIN_H))

    # Add core design macro.
    libname = 'heartbeat'
    stackup = chip.get('asic', 'stackup')
    chip.add('asic', 'macrolib', libname)
    chip.set('library', libname, 'type', 'component')
    chip.set('library', libname, 'lef', stackup, 'heartbeat.lef')
    chip.set('library', libname, 'def', stackup, 'heartbeat.def')
    chip.set('library', libname, 'gds', stackup, 'heartbeat.gds')
    chip.set('library', libname, 'netlist', 'verilog', 'heartbeat.vg')

    # No filler cells in the top-level wrapper.
    chip.set('library', 'sky130hd', 'cells', 'filler', [])

    # No tapcells in the top-level wrapper.
    # TODO: Should the Chip object have a 'delete' manifest method to go with 'set'/'get'/'add'?
    libtype = 'hd'
    chip.cfg['pdk']['aprtech']['openroad'][stackup][libtype].pop('tapcells')

    # Create PDN-generation script.
    with open('pdngen_top.tcl', 'w') as pdnf:
        # TODO: Jinja template?
        pdnf.write('''
# Add PDN connections for each voltage domain.
add_global_connection -net vccd1 -pin_pattern "^vccd.*$" -power
add_global_connection -net vssd1 -pin_pattern "^vssd.*$" -ground

# Define top-level PDN grid.
define_pdn_grid -name pdn_grid -starts_with POWER -voltage_domain CORE -pins {met4 met5}

# Create core ring.
add_pdn_ring -grid pdn_grid -layer {met4 met5} -widths {1.6 1.6} -spacings {1.7 1.7} -core_offset {6 6}

# Add vertical / horizontal stripes.
add_pdn_stripe -grid pdn_grid -layer met4 -width 1.6 -pitch 150 -offset 75 -starts_with POWER -extend_to_core_ring
add_pdn_stripe -grid pdn_grid -layer met5 -width 1.6 -pitch 225 -offset 112.5 -starts_with POWER -extend_to_core_ring

# Connect top-level horizontal / vertical stripes.
add_pdn_connect -grid pdn_grid -layers {met4 met5}

# Connect top-level horizontal stripes to core-level vertical stripes.
define_pdn_grid -name core_grid -existing -obstructions {met4}
add_pdn_connect -grid core_grid -layers {met4 met5}

# Done defining commands; generate PDN.
pdngen''')
    chip.set('pdk', 'aprtech', 'openroad', stackup, libtype, 'pdngen', 'pdngen_top.tcl')

    # Generate macro-placement script.
    with open('macroplace_top.tcl', 'w') as mf:
        mf.write('''
# 'mprj' user-defined project macro, near the center of the die area.
place_cell -inst_name mprj -origin {1174.84 1689.12} -orient R0 -status FIRM
''')
    chip.set('pdk', 'aprtech', 'openroad', stackup, libtype, 'macroplace', 'macroplace_top.tcl')

    # Run the top-level build.
    chip.run()

def main():
    # Build the core design, which gets placed inside the padring.
    build_core()
    # Build the top-level design by stacking the core into the middle of the padring.
    build_top()

if __name__ == '__main__':
    main()
