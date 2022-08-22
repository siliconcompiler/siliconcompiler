# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
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
CORE_W = 899.76
CORE_H = 598.4
# Margins are set to ~10mm, snapped to placement site dimensions (0.46mm x 2.72mm in sky130hd)
MARGIN_W = 9.66
#MARGIN_W = 9.52
MARGIN_H = 8.16
#MARGIN_H = 6.256

# Path to 'caravel' repository root.
CARAVEL_ROOT = '/path/to/caravel'

def configure_chip(design):
    # Minimal Chip object construction.
    chip = Chip(design)
    chip.load_target('skywater130_demo')
    chip.load_flow('mpwflow')
    chip.set('option', 'flow', 'mpwflow')
    return chip

def build_core():
    # Harden the 'heartbeat' module. Following the example set in 'user_proj_example',
    # We can skip a detailed floorplan and let the router connect top-level I/O signals.
    core_chip = configure_chip('heartbeat')
    design = core_chip.get('design')
    core_chip.set('input', 'verilog', 'heartbeat.v')
    core_chip.set('tool', 'openroad', 'var', 'floorplan', '0', 'pin_thickness_h', ['2'])
    core_chip.set('tool', 'openroad', 'var', 'floorplan', '0', 'pin_thickness_v', ['2'])
    core_chip.set('tool', 'openroad', 'var', 'place', '0', 'place_density', ['0.15'])
    core_chip.set('tool', 'openroad', 'var', 'route', '0', 'grt_allow_congestion', ['true'])
    core_chip.clock('clk', period=20)

    # Optional: These configurations can add padding around cells during the placement steps,
    # which can help to reduce routing congestion at the expense of placement density.
    #core_chip.add('tool', 'openroad', 'var', 'place', '0', 'pad_global_place', ['2'])
    #core_chip.add('tool', 'openroad', 'var', 'place', '0', 'pad_detail_place', ['2'])

    # Set user design die/core area.
    core_chip.set('asic', 'diearea', (0, 0))
    core_chip.add('asic', 'diearea', (CORE_W, CORE_H))
    core_chip.set('asic', 'corearea', (MARGIN_W, MARGIN_H))
    core_chip.add('asic', 'corearea', (CORE_W - MARGIN_W, CORE_H - MARGIN_H))

    # No routing on met4-met5.
    stackup = core_chip.get('asic', 'stackup')
    libtype = 'unithd'
    core_chip.set('asic', 'maxlayer', 'met3')

    # Build the core design.
    core_chip.run()

    # Copy GDS/DEF/LEF files for use in the top-level build.
    shutil.copy(core_chip.find_result('gds', step='export'), f'{design}.gds')
    shutil.copy(core_chip.find_result('vg', step='dfm'), f'{design}.vg')
    shutil.copy(core_chip.find_result('def', step='dfm'), f'{design}.def')
    shutil.copy(core_chip.find_result('lef', step='dfm'), f'{design}.lef')

def build_top():
    # The 'hearbeat' RTL goes in a modified 'user_project_wrapper' object, see sources.
    design = 'user_project_wrapper'
    chip = configure_chip(design)
    chip.set('tool', 'openroad', 'var', 'place', '0', 'place_density', ['0.15'])
    #chip.add('tool', 'openroad', 'var', 'place', '0', 'pad_global_place', ['2'])
    #chip.add('tool', 'openroad', 'var', 'place', '0', 'pad_detail_place', ['2'])
    chip.set('tool', 'openroad', 'var', 'route', '0', 'grt_allow_congestion', ['true'])
    chip.clock('user_clock2', period=20)

    # Set top-level source files.
    chip.set('input', 'verilog', f'{CARAVEL_ROOT}/verilog/rtl/defines.v')
    chip.add('input', 'verilog', 'heartbeat.bb.v')
    chip.add('input', 'verilog', 'user_project_wrapper.v')

    # Set top-level die/core area.
    chip.set('asic', 'diearea', (0, 0))
    chip.add('asic', 'diearea', (TOP_W, TOP_H))
    chip.set('asic', 'corearea', (MARGIN_W, MARGIN_H))
    chip.add('asic', 'corearea', (TOP_W - MARGIN_W, TOP_H - MARGIN_H))

    # Add core design macro as a library.
    libname = 'heartbeat'
    stackup = chip.get('asic', 'stackup')
    chip.add('asic', 'macrolib', libname)
    heartbeat_lib = Chip('heartbeat')
    heartbeat_lib.add('model', 'layout', 'lef', stackup, 'heartbeat.lef')
    heartbeat_lib.add('model', 'layout', 'def', stackup, 'heartbeat.def')
    heartbeat_lib.add('model', 'layout', 'gds', stackup, 'heartbeat.gds')
    heartbeat_lib.add('model', 'layout', 'vg', stackup, 'heartbeat.vg')
    heartbeat_lib.set('asic', 'pdk', 'skywater130')
    heartbeat_lib.set('option', 'pdk', 'skywater130')
    heartbeat_lib.set('asic', 'stackup', stackup)
    chip.import_library(heartbeat_lib)

    # Use pre-defined floorplan for the wrapper..
    chip.set('input', 'floorplan.def', f'{CARAVEL_ROOT}/def/user_project_wrapper.def')

    # (No?) filler cells in the top-level wrapper.
    #chip.set('library', 'sky130hd', 'cells', 'filler', [])
    #chip.add('library', 'sky130hd', 'cells', 'ignore', 'sky130_fd_sc_hd__conb_1')

    # (No?) tapcells in the top-level wrapper.
    libtype = 'unithd'
    #chip.cfg['pdk']['aprtech']['openroad'][stackup][libtype].pop('tapcells')

    # No I/O buffers in the top-level wrapper, but keep tie-hi/lo cells.
    #chip.set('library', 'sky130hd', 'cells', 'tie', [])
    chip.set('asic', 'cells', 'buf', [])

    # Create PDN-generation script.
    pdk = chip.get('option', 'pdk')
    with open('pdngen_top.tcl', 'w') as pdnf:
        # TODO: Jinja template?
        pdnf.write('''
# Add PDN connections for each voltage domain.
add_global_connection -net vccd1 -pin_pattern "^VPWR$" -power
add_global_connection -net vssd1 -pin_pattern "^VGND$" -ground
add_global_connection -net vccd1 -pin_pattern "^POWER$" -power
add_global_connection -net vssd1 -pin_pattern "^GROUND$" -ground
global_connect

set_voltage_domain -name Core -power vccd1 -ground vssd1

define_pdn_grid -name core_grid -macro -grid_over_pg_pins -default -voltage_domain Core -starts_with POWER
add_pdn_stripe -grid core_grid -layer met1 -width 0.48 -starts_with POWER -followpins
add_pdn_connect -grid core_grid -layers {met1 met4}

# Done defining commands; generate PDN.
pdngen''')
    chip.set('pdk', pdk, 'aprtech', 'openroad', stackup, libtype, 'pdngen', 'pdngen_top.tcl')

    # Generate macro-placement script.
    with open('macroplace_top.tcl', 'w') as mf:
        mf.write('''
# 'mprj' user-defined project macro, near the center of the die area.
#place_cell -inst_name mprj -origin {1174.84 1689.02} -orient R0 -status FIRM
place_cell -inst_name mprj -origin {1188.64 1689.12} -orient R0 -status FIRM
''')
    chip.set('pdk', pdk, 'aprtech', 'openroad', stackup, libtype, 'macroplace', 'macroplace_top.tcl')

    # Run the top-level build.
    chip.run()

    # Add via definitions to the gate-level netlist.
    shutil.copy(chip.find_result('vg', step='addvias'), f'{design}.vg')

def main():
    # Build the core design, which gets placed inside the padring.
    build_core()
    # Build the top-level design by stacking the core into the middle of the padring.
    build_top()

if __name__ == '__main__':
    main()
