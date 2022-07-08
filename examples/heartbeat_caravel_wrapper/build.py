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
    return chip

def run_chip_flow(chip):
    # Helper method to run the design flow with an intermediary post-routing step to
    # cover 'pin' data types with 'drawing' data types. This is required for the eFabless
    # MPW prechecks, because the mask production process does not include 'pin' data types,
    # and the main DRCs can miss open circuits by counting those data types as valid connections.

    # Run the build up to the 'route' step.
    chip.set('option', 'steplist', ['syn', 'floorplan', 'physyn', 'place', 'cts', 'route'])
    chip.run()

    # Perform post-processing on the DEF file, to add overlaps for 'drawing' and 'pin' data types.
    # The easiest way to do this is to add tracks in the 'SPECIALNETS' section with identical
    # name, net, and dimensions to their corresponding 'PIN' section entry.

    # Fetch common values.
    design = chip.get('design')
    job_dir = os.path.join(chip.get('option', 'builddir'),
                           design,
                           chip.get('option', 'jobname'))
    route_dir = os.path.join(job_dir, 'route', '0')
    def_prefix = os.path.join(route_dir, 'outputs', design)
    # Rename the original DEF file, to keep as a backup.
    os.rename(f'{def_prefix}.def', f'{def_prefix}-raw.def')
    with open(f'{def_prefix}-raw.def') as f:
        with open(f'{def_prefix}.def', 'w') as wf:
            # State-tracking variables for parsing the file.
            in_pins = 0
            in_pin = ''
            in_net = ''
            in_layer = ''
            pin_w = 0
            pin_h = 0
            pin_locs = {}

            # Process the file one line at a time:
            # 1. Gather information about pin polys.
            # 2. Add overlaps in the 'SPECIALNETS' section.
            # Assumptions: 'PINS' comes before 'SPECIALNETS', and there is only one 'PINS' section.
            for line in f:
                l = line

                # We don't care about lines before the 'PINS' section; write them verbatim to new DEF.
                if not in_pins:
                    wf.write(l)
                    # Start paying attention at the start of the 'PINS' section.
                    if l.strip().startswith('PINS'):
                        in_pins = 1
                # Note name, dimensions, and net of each non-power pin. (Power nets should go thru PDN)
                elif in_pins == 1:
                    wf.write(l)
                    if l.strip().startswith('END PINS'):
                        in_pins = 2
                    elif l.strip().startswith('-'):
                        la = l.strip().split()
                        in_pin = la[1]
                        in_net = la[4]
                    # TODO: We should not use hardcoded prefixes for power nets to ignore.
                    elif ('LAYER' in l) and (not 'vcc' in in_pin) and (not 'vss' in in_pin):
                        la = l.strip().split()
                        in_layer = la[2]
                        pin_w = abs(int(la[8]) - int(la[4]))
                        pin_h = abs(int(la[9]) - int(la[5]))
                    elif ('PLACED' in l) and (not 'vcc' in in_pin) and (not 'vss' in in_pin):
                        la = l.strip().split()
                        pin_locs[in_pin] = {'layer': in_layer,
                                            'net': in_net,
                                            'x': int(la[3]),
                                            'y': int(la[4]),
                                            'w': pin_w,
                                            'h': pin_h}
                # After the 'PINS' section, look for 'SPECIALNETS' section and add tracks over each pin.
                # This section may not exist; create it if we find 'END NETS' before 'SPECIALNETS'
                elif in_pins == 2:
                    if l.strip().startswith('SPECIALNETS'):
                        la = l.strip().split()
                        numnets = int(la[1]) + len(pin_locs)
                        wf.write('SPECIALNETS %i ;\n'%numnets)
                    # (There may not be a SPECIALNETS section in the DEF output)
                    elif l.strip().startswith('END NETS'):
                        wf.write(l)
                        numnets = len(pin_locs)
                        wf.write('SPECIALNETS %i ;\n'%numnets)
                    elif (l.strip() == 'END SPECIALNETS') or (l.strip() == 'END DESIGN'):
                        for k, v in pin_locs.items():
                            ml = 0
                            if v['layer'] == 'met2':
                                ml = v['w']
                                xl = v['x']
                                xr = v['x']
                                yb = int(v['y'] - v['h'] / 2)
                                yu = int(v['y'] + v['h'] / 2)
                            elif v['layer'] == 'met3':
                                ml = v['h']
                                xl = int(v['x'] - v['w'] / 2)
                                xr = int(v['x'] + v['w'] / 2)
                                yb = v['y']
                                yu = v['y']
                            wf.write('    - %s ( PIN %s ) + USE SIGNAL\n'%(v['net'], k))
                            wf.write('      + ROUTED %s %i + SHAPE STRIPE ( %i %i ) ( %i %i )\n'%(v['layer'], int(ml), xl, yb, xr, yu))
                            wf.write('      NEW %s %i + SHAPE STRIPE ( %i %i ) ( %i %i ) ;\n'%(v['layer'], int(ml), xl, yb, xr, yu))
                        if l.strip() == 'END DESIGN':
                            wf.write('END SPECIALNETS\n')
                        wf.write(l)
                        in_pins = 3
                    else:
                        wf.write(l)
                elif in_pins == 3:
                    wf.write(l)

    # Run the rest of the build flow, using the newly-created post-routing DEF file.
    chip.set('option', 'steplist', ['dfm', 'export'])
    chip.run()

def build_core():
    # Harden the 'heartbeat' module. Following the example set in 'user_proj_example',
    # We can skip a detailed floorplan and let the router connect top-level I/O signals.
    core_chip = configure_chip('heartbeat')
    design = core_chip.get('design')
    core_chip.set('input', 'verilog', 'heartbeat.v')
    core_chip.set('tool', 'openroad', 'var', 'place', '0', 'place_density', ['0.15'])
    #core_chip.add('tool', 'openroad', 'var', 'place', '0', 'pad_global_place', ['2'])
    #core_chip.add('tool', 'openroad', 'var', 'place', '0', 'pad_detail_place', ['2'])
    core_chip.set('tool', 'openroad', 'var', 'route', '0', 'grt_allow_congestion', ['true'])
    core_chip.clock('clk', period=20)

    # Set user design die/core area.
    core_chip.set('asic', 'diearea', (0, 0))
    core_chip.add('asic', 'diearea', (CORE_W, CORE_H))
    core_chip.set('asic', 'corearea', (MARGIN_W, MARGIN_H))
    core_chip.add('asic', 'corearea', (CORE_W - MARGIN_W, CORE_H - MARGIN_H))

    # No routing on met4-met5.
    stackup = core_chip.get('asic', 'stackup')
    libtype = 'unithd'
    core_chip.set('asic', 'maxlayer', 'met3')

    # Create empty PDN script to effectively skip PDN generation.
    pdk = core_chip.get('option', 'pdk')
    with open('pdngen.tcl', 'w') as pdnf:
        pdnf.write('''#NOP''')
    core_chip.set('pdk', pdk, 'aprtech', 'openroad', stackup, libtype, 'pdngen', 'pdngen.tcl')

    # Build the core design.
    run_chip_flow(core_chip)

    # Copy GDS/DEF/LEF files for use in the top-level build.
    jobdir = (core_chip.get('option', 'builddir') +
            "/" + design + "/" +
            core_chip.get('option', 'jobname'))
    shutil.copy(f'{jobdir}/export/0/outputs/{design}.gds', f'{design}.gds')
    shutil.copy(f'{jobdir}/export/0/inputs/{design}.def', f'{design}.def')
    shutil.copy(f'{jobdir}/export/0/inputs/{design}.lef', f'{design}.lef')
    shutil.copy(f'{jobdir}/dfm/0/outputs/{design}.vg', f'{design}.vg')

def build_top():
    # The 'hearbeat' RTL goes in a modified 'user_project_wrapper' object, see sources.
    chip = configure_chip('user_project_wrapper')
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

define_pdn_grid -name core_grid -macro -grid_over_boundary -default -voltage_domain Core
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
    run_chip_flow(chip)

    # Add via definitions to the gate-level netlist.
    design = chip.get('design')
    jobdir = (chip.get('option', 'builddir') +
              "/" + design + "/" +
              chip.get('option', 'jobname'))
    shutil.copy(f'{jobdir}/dfm/0/outputs/{design}.vg', f'{design}.vg')
    in_mod = False
    done_mod = False
    with open(f'{design}.vg.v', 'w') as wf:
      with open(f'{design}.vg', 'r') as rf:
        for line in rf.readlines():
          if in_mod:
            if line.strip().startswith('endmodule'):
              wf.write(''' VIA_L1M1_PR(vssd1);
 VIA_L1M1_PR(vccd1);
 VIA_L1M1_PR_MR(vssd1);
 VIA_L1M1_PR_MR(vccd1);
 VIA_M1M2_PR(vssd1);
 VIA_M1M2_PR(vccd1);
 VIA_M1M2_PR_MR(vssd1);
 VIA_M1M2_PR_MR(vccd1);
 VIA_M2M3_PR(vssd1);
 VIA_M2M3_PR(vccd1);
 VIA_M2M3_PR_MR(vssd1);
 VIA_M2M3_PR_MR(vccd1);
 VIA_M3M4_PR(vssd1);
 VIA_M3M4_PR(vccd1);
 VIA_M3M4_PR_MR(vssd1);
 VIA_M3M4_PR_MR(vccd1);
 VIA_via2_3_3100_480_1_9_320_320(vssd1);
 VIA_via2_3_3100_480_1_9_320_320(vccd1);
 VIA_via3_4_3100_480_1_7_400_400(vssd1);
 VIA_via3_4_3100_480_1_7_400_400(vccd1);
 VIA_via4_3100x3100(vssd1);
 VIA_via4_3100x3100(vccd1);
 VIA_via4_5_3100_480_1_7_400_400(vssd1);
 VIA_via4_5_3100_480_1_7_400_400(vccd1);\n''')
          elif not done_mod:
            if line.strip().startswith('module user_project_wrapper'):
              in_mod = True
          wf.write(line)

def main():
    # Build the core design, which gets placed inside the padring.
    build_core()
    # Build the top-level design by stacking the core into the middle of the padring.
    build_top()

if __name__ == '__main__':
    main()
