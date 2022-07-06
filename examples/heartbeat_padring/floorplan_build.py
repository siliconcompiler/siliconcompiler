# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import math
import shutil

from siliconcompiler.core import Chip
from siliconcompiler.floorplan import Floorplan

###
# Example build script: 'heartbeat' example with padring and scripted floorplan.
#
# This script follows the same general floorplanning approach as the ZeroSoc tutorial,
# with a simpler core design. It is less of a 'real-world' design, but also a bit less complex:
# https://docs.siliconcompiler.com/en/latest/tutorials/zerosoc.html
###

# Helper defs for skywater PDK macro cells.
GPIO = 'sky130_ef_io__gpiov2_pad_wrapped'
VDD = 'sky130_ef_io__vccd_hvc_pad'
VDDIO = 'sky130_ef_io__vddio_hvc_pad'
VSS = 'sky130_ef_io__vssd_hvc_pad'
VSSIO = 'sky130_ef_io__vssio_hvc_pad'
CORNER = 'sky130_ef_io__corner_pad'
FILL_CELLS = ['sky130_ef_io__com_bus_slice_1um',
              'sky130_ef_io__com_bus_slice_5um',
              'sky130_ef_io__com_bus_slice_10um',
              'sky130_ef_io__com_bus_slice_20um']
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

def define_dimensions(fp):
    # Define placement area for the core design.
    place_w = 256 * fp.stdcell_width
    place_h = 64 * fp.stdcell_height
    # Define margin between core and padring.
    margin_left = 60 * fp.stdcell_width
    margin_bottom = 10 * fp.stdcell_height
    # Define total core dimensions.
    core_w = place_w + (2 * margin_left)
    core_h = place_h + (2 * margin_bottom)
    # Define total chip dimensions with padring, rounded up to whole microns.
    gpio_h = fp.available_cells[GPIO].height
    top_w = math.ceil(core_w + (2 * gpio_h))
    top_h = math.ceil(core_h + (2 * gpio_h))
    # Re-define core dimensions to account for rounding.
    core_w = top_w - (2 * gpio_h)
    core_h = top_h - (2 * gpio_h)

    # Return dimensions as tuples.
    return (top_w, top_h), (core_w, core_h), (place_w, place_h), (margin_left, margin_bottom)

def calculate_even_spacing(fp, pads, distance, start):
    n = len(pads)
    pads_width = sum(fp.available_cells[pad].width for pad in pads)
    spacing = (distance - pads_width) // (n + 1)

    pos = start + spacing
    io_pos = []
    for pad in pads:
        io_pos.append((pad, pos))
        pos += fp.available_cells[pad].width + spacing

    return io_pos

def define_io_placement(fp):
    # Define I/O pad locations. Since this design only has three I/Os,
    # we can get away with one pad per edge and one no-connect.
    we_io = [GPIO, GPIO]
    no_io = [VDD]
    ea_io = [GPIO]
    so_io = [VSS]

    (top_w, top_h), _, _, _ = define_dimensions(fp)
    corner_w = fp.available_cells[CORNER].width
    corner_h = fp.available_cells[CORNER].height
    we_io_pos = calculate_even_spacing(fp, we_io, top_h - corner_h - corner_w, corner_h)
    ea_io_pos = calculate_even_spacing(fp, ea_io, top_h - corner_h - corner_w, corner_h)
    no_io_pos = calculate_even_spacing(fp, no_io, top_w - corner_h - corner_w, corner_w)
    so_io_pos = calculate_even_spacing(fp, so_io, top_w - corner_h - corner_w, corner_w)

    return we_io_pos, no_io_pos, ea_io_pos, so_io_pos

def place_pdn(fp):
    # Simple PDN placement within the core, no macros to worry about.
    dims = define_dimensions(fp)
    _, (core_w, core_h), (place_w, place_h), (margin_left, margin_bottom) = dims
    we_pads, no_pads, ea_pads, so_pads = define_io_placement(fp)

    n_vert = 4 # how many vertical straps to place
    vwidth = 5 # width of vertical straps in microns
    n_hori = 4 # how many horizontal straps to place
    hwidth = 5 # width of horizontal straps
    vlayer = 'm4' # metal layer for vertical straps
    hlayer = 'm5' # metal layer for horizontal straps
    # Calculate even spacing for straps
    vpitch = (core_w - n_vert * vwidth) / (n_vert + 1)
    hpitch = (core_h - n_hori * hwidth) / (n_hori + 1)

    # Add power nets to the floorplan.
    fp.add_net('_vdd', ['VPWR'], 'power')
    fp.add_net('_vss', ['VGND'], 'ground')
    #fp.add_net('_vddio', [], 'power')

    # Add power ring.
    vss_ring_left = margin_left - 4 * vwidth
    vss_ring_bottom = margin_bottom - 4 * hwidth
    vss_ring_width = place_w + 9 * vwidth
    vss_ring_height = place_h + 9 * hwidth
    vss_ring_right = vss_ring_left + vss_ring_width
    vss_ring_top = vss_ring_bottom + vss_ring_height

    vdd_ring_left = vss_ring_left + 2 * vwidth
    vdd_ring_bottom = vss_ring_bottom + 2 * hwidth
    vdd_ring_width = vss_ring_width - 4 * vwidth
    vdd_ring_height = vss_ring_height - 4 * hwidth
    vdd_ring_right = vdd_ring_left + vdd_ring_width
    vdd_ring_top = vdd_ring_bottom + vdd_ring_height

    fp.place_ring('_vdd', vdd_ring_left, vdd_ring_bottom, vdd_ring_width,
                  vdd_ring_height, hwidth, vwidth, hlayer, vlayer)
    fp.place_ring('_vss', vss_ring_left, vss_ring_bottom, vss_ring_width,
                  vss_ring_height, hwidth, vwidth, hlayer, vlayer)

    # Horizontal stripes
    spacing = 2 * (hpitch + hwidth)
    bottom = margin_bottom + hpitch
    fp.place_wires(['_vdd'] * (n_hori // 2), vdd_ring_left, bottom, 0, spacing,
                   vdd_ring_width, hwidth, hlayer, shape='stripe')

    bottom = margin_bottom + hpitch + (hpitch + hwidth)
    fp.place_wires(['_vss'] * (n_hori // 2), vss_ring_left, bottom, 0, spacing,
                   vss_ring_width, hwidth, hlayer, shape='stripe')

    # Vertical stripes
    spacing = 2 * (vpitch + vwidth)
    left = margin_left + vpitch
    fp.place_wires(['_vdd'] * (n_vert // 2), left, vdd_ring_bottom, spacing, 0,
                   vwidth, vdd_ring_height, vlayer, shape='stripe')

    left = margin_left + vpitch + (vpitch + vwidth)
    fp.place_wires(['_vss'] * (n_vert // 2), left, vss_ring_bottom, spacing, 0,
                   vwidth, vss_ring_height, vlayer, shape='stripe')

    gpio_h = fp.available_cells[GPIO].height
    pow_h = fp.available_cells[VDD].height
    # account for GPIO padcells being larger than power padcells
    pow_gap = gpio_h - pow_h

    pin_width = 23.9
    pin_offsets = (0.495, 50.39)

    # Place wires/pins connecting power pads to the power ring
    for pad_type, y in we_pads:
        y -= gpio_h
        for offset in pin_offsets:
            if pad_type == VDD:
                fp.place_wires(['_vdd'], -pow_gap, y + offset, 0, 0,
                               vdd_ring_left + vwidth + pow_gap, pin_width, 'm3')
                fp.place_pins (['_vdd'], 0, y + offset, 0, 0,
                               vdd_ring_left + vwidth, pin_width, 'm3', use='power')
            elif pad_type == VDDIO:
                fp.place_pins (['_vddio'], 0, y + offset, 0, 0,
                               margin_left, pin_width, 'm3')
            elif pad_type == VSS:
                fp.place_wires(['_vss'], -pow_gap, y + offset, 0, 0,
                               vss_ring_left + vwidth + pow_gap, pin_width, 'm3')
                fp.place_pins(['_vss'], 0, y + offset, 0, 0,
                              vss_ring_left + vwidth, pin_width, 'm3', use='power')

    for pad_type, x in no_pads:
        x -= gpio_h
        for offset in pin_offsets:
            if pad_type == VDD:
                fp.place_wires(['_vdd'], x + offset, vdd_ring_top - hwidth, 0, 0,
                               pin_width, core_h - vdd_ring_top + hwidth + pow_gap, 'm3')
                fp.place_pins(['_vdd'], x + offset, vdd_ring_top - hwidth, 0, 0,
                              pin_width, core_h - vdd_ring_top + hwidth, 'm3', use='power')
            elif pad_type == VDDIO:
                fp.place_pins(['_vddio'], x + offset, margin_bottom + place_h, 0, 0,
                              pin_width, core_h - (margin_bottom + place_h), 'm3')
            elif pad_type == VSS:
                fp.place_wires(['_vss'], x + offset, vss_ring_top - hwidth, 0, 0,
                               pin_width, core_h - vss_ring_top + hwidth + pow_gap, 'm3')
                fp.place_pins(['_vss'], x + offset, vss_ring_top - hwidth, 0, 0,
                              pin_width, core_h - vss_ring_top + hwidth, 'm3', use='power')

    for pad_type, y in ea_pads:
        y -= gpio_h
        pad_w = fp.available_cells[pad_type].width
        for offset in pin_offsets:
            if pad_type == VDD:
                fp.place_wires(['_vdd'], vdd_ring_right - vwidth, y + pad_w - offset - pin_width, 0, 0,
                               core_w - vdd_ring_right + vwidth + pow_gap, pin_width, 'm3')
                fp.place_pins(['_vdd'], vdd_ring_right - vwidth, y + pad_w - offset - pin_width, 0, 0,
                              core_w - vdd_ring_right + vwidth, pin_width, 'm3', use='power')
            elif pad_type == VDDIO:
                fp.place_pins(['_vddio'], margin_left + place_w, y + pad_w - offset - pin_width, 0, 0,
                              core_w - (margin_left + place_w), pin_width, 'm3')
            elif pad_type == VSS:
                fp.place_wires(['_vss'], vss_ring_right - vwidth, y + pad_w - offset - pin_width, 0, 0,
                               core_w - vss_ring_right + vwidth + pow_gap, pin_width, 'm3')
                fp.place_pins(['_vss'], vss_ring_right - vwidth, y + pad_w - offset - pin_width, 0, 0,
                              core_w - vss_ring_right + vwidth, pin_width, 'm3', use='power')

    for pad_type, x in so_pads:
        x -= gpio_h
        pad_w = fp.available_cells[pad_type].width
        for offset in pin_offsets:
            if pad_type == VDD:
                fp.place_wires(['_vdd'], x + pad_w - offset - pin_width, -pow_gap, 0, 0,
                               pin_width, vdd_ring_bottom + hwidth + pow_gap, 'm3')
                fp.place_pins(['_vdd'], x + pad_w - offset - pin_width, 0, 0, 0,
                              pin_width, vdd_ring_bottom + hwidth, 'm3', use='power')
            elif pad_type == VDDIO:
                fp.place_pins(['_vddio'], x + pad_w - offset - pin_width, 0, 0, 0,
                              pin_width, margin_bottom, 'm3')
            elif pad_type == VSS:
                fp.place_wires(['_vss'], x + pad_w - offset - pin_width, -pow_gap, 0, 0,
                               pin_width, vss_ring_bottom + hwidth + pow_gap, 'm3')
                fp.place_pins(['_vss'], x + pad_w - offset - pin_width, 0, 0, 0,
                              pin_width, vss_ring_bottom + hwidth, 'm3', use='power')

    stripe_w = 0.48
    spacing = 2 * fp.stdcell_height

    bottom = margin_bottom - stripe_w/2
    fp.place_wires(['_vdd'] * math.ceil(len(fp.rows) / 2), margin_left, bottom, 0, spacing,
                   place_w, stripe_w, 'm1', 'followpin')

    bottom = margin_bottom - stripe_w/2 + fp.stdcell_height
    fp.place_wires(['_vss'] * math.floor(len(fp.rows) / 2), margin_left, bottom, 0, spacing,
                   place_w, stripe_w, 'm1', 'followpin')

    fp.insert_vias(layers=[('m1', 'm4'), ('m3', 'm4'), ('m3', 'm5'), ('m4', 'm5')])

def core_floorplan(fp):
    # Core floorplan definition.
    dims = define_dimensions(fp)
    _, (core_w, core_h), (place_w, place_h), (margin_left, margin_bottom) = dims
    diearea = [(0, 0), (core_w, core_h)]
    corearea = [(margin_left, margin_bottom), (place_w + margin_left, place_h + margin_bottom)]
    fp.create_diearea(diearea, corearea = corearea)

    # Define I/O cell signals.
    pins = [
        # (name, offset from cell edge, # bit in vector, width of vector)
        ('din', 75.085, 0, 1), # in
        ('dout', 19.885, 0, 1), # out
        ('ie', 41.505, 0, 1), # inp_dis
        ('oen', 4.245, 0, 1), # oe_n
        ('tech_cfg', 31.845, 0, 18), # hld_h_n
        ('tech_cfg', 35.065, 1, 18), # enable_h
        ('tech_cfg', 38.285, 2, 18), # enable_inp_h
        ('tech_cfg', 13.445, 3, 18), # enable_vdda_h
        ('tech_cfg', 16.665, 4, 18), # enable_vswitch_h
        ('tech_cfg', 69.105, 5, 18), # enable_vddio
        ('tech_cfg',  7.465, 6, 18), # ib_mode_sel
        ('tech_cfg', 10.685, 7, 18), # vtrip_sel
        ('tech_cfg', 65.885, 8, 18), # slow
        ('tech_cfg', 22.645, 9, 18), # hld_ovr
        ('tech_cfg', 50.705, 10, 18), # analog_en
        ('tech_cfg', 29.085, 11, 18), # analog_sel
        ('tech_cfg', 44.265, 12, 18), # analog_pol
        ('tech_cfg', 47.485, 13, 18), # dm[0]
        ('tech_cfg', 56.685, 14, 18), # dm[1]
        ('tech_cfg', 25.865, 15, 18), # dm[2]
        ('tech_cfg', 78.305, 16, 18), # tie_lo_esd
        ('tech_cfg', 71.865, 17, 18), # tie_hi_esd
    ]
    pin_width = 0.28
    pin_depth = 1
    pin_layer = 'm2'

    we_pads, no_pads, ea_pads, so_pads = define_io_placement(fp)

    gpio_w = fp.available_cells[GPIO].width
    gpio_h = fp.available_cells[GPIO].height

    # Filter out GPIO pins, once for each edge along the corresponding axis.
    # West
    we_gpio_pos = [pos for pad, pos in we_pads if pad == GPIO]
    pin_x = 0
    for i, pad_y in enumerate(we_gpio_pos):
        pad_y -= gpio_h # account for padring height
        for pin, offset, bit, width in pins:
            # Construct name based on side, pin name, and bit # in vector
            name = f'we_{pin}[{i * width + bit}]'
            # TODO: Hack: set data inputs to specific pins for each pad.
            if pin == 'din':
                if i == 0:
                    name = 'clk'
                elif i == 1:
                    name = 'nreset'
            # Calculate pin position based on cell and offset
            pin_y = pad_y + offset
            # Place pin!
            fp.place_pins([name], pin_x, pin_y, 0, 0, pin_depth, pin_width, pin_layer)
    # North
    no_gpio_pos = [pos for pad, pos in no_pads if pad == GPIO]
    pin_y = core_h - pin_depth
    for i, pad_x in enumerate(no_gpio_pos):
        pad_x -= gpio_h
        for pin, offset, bit, width in pins:
            name = f'no_{pin}[{i * width + bit}]'
            pin_x = pad_x + offset
            fp.place_pins([name], pin_x, pin_y, 0, 0, pin_width, pin_depth, pin_layer)
    # East
    ea_gpio_pos = [pos for pad, pos in ea_pads if pad == GPIO]
    pin_x = core_w - pin_depth
    for i, pad_y in enumerate(ea_gpio_pos):
        pad_y -= gpio_h
        for pin, offset, bit, width in pins:
            name = f'ea_{pin}[{i * width + bit}]'
            if pin == 'dout':
                name = 'out'
            # TODO: Hack for 1-pad edge
            elif pin in ['din', 'ie', 'oen']:
                name = f'ea_{pin}'
            pin_y = pad_y + gpio_w - offset - pin_width
            fp.place_pins([name], pin_x, pin_y, 0, 0, pin_depth, pin_width, pin_layer)
    # South
    so_gpio_pos = [pos for pad, pos in so_pads if pad == GPIO]
    pin_y = 0
    for i, pad_x in enumerate(so_gpio_pos):
        pad_x -= gpio_h
        for pin, offset, bit, width in pins:
            name = f'so_{pin}[{i * width + bit}]'
            pin_x = pad_x + gpio_w - offset - pin_width
            fp.place_pins([name], pin_x, pin_y, 0, 0, pin_width, pin_depth, pin_layer)

    # Place PDN grid.
    place_pdn(fp)

def top_floorplan(fp):
    # Create top-level die area.
    (top_w, top_h), (core_w, core_h), (place_w, place_h), (margin_left, margin_bottom) = define_dimensions(fp)
    fp.create_diearea([(0, 0), (top_w, top_h)])

    # TODO: ...?
    we_pads, no_pads, ea_pads, so_pads = define_io_placement(fp)
    indices = {}
    indices[GPIO] = 0
    indices[VDD] = 0
    indices[VSS] = 0
    indices[VDDIO] = 0
    indices[VSSIO] = 0
    gpio_h = fp.available_cells[GPIO].height
    pow_h = fp.available_cells[VDD].height
    corner_w = fp.available_cells[CORNER].width
    corner_h = fp.available_cells[CORNER].height
    fill_cell_h = fp.available_cells[FILL_CELLS[0]].height
    pin_dim = 10
    # Calculate where to place pin based on hardcoded GPIO pad pin location
    pin_offset_width = (11.2 + 73.8) / 2 - pin_dim / 2
    pin_offset_depth = gpio_h - ((102.525 + 184.975) / 2 - pin_dim / 2)

    # Place W pads:
    for pad_type, y in we_pads:
        i = indices[pad_type]
        indices[pad_type] += 1
        if pad_type == GPIO:
            pad_name = f'padring.we_pads\\[0\\].i0.padio\\[{i}\\].i0.gpio'
            pin_name = f'we_pad'
        else:
            if pad_type == VDD:
                pin_name = 'vdd'
            elif pad_type == VSS:
                pin_name = 'vss'
            elif pad_type == VDDIO:
                pin_name = 'vddio'
            elif pad_type == VSSIO:
                pin_name = 'vssio'
            pad_name = f'{pin_name}{i}'
        fp.place_macros([(pad_name, pad_type)], 0, y, 0, 0, 'W')
        fp.place_pins([pin_name], pin_offset_depth, y + pin_offset_width,
                      0, 0, pin_dim, pin_dim, 'm5')
    # Place N pads:
    indices[GPIO] = 0
    for pad_type, x in no_pads:
        i = indices[pad_type]
        indices[pad_type] += 1
        if pad_type == GPIO:
            pad_name = f'padring.no_pads\\[0\\].i0.padio\\[{i}\\].i0.gpio'
            pin_name = f'no_pad[{i}]'
        else:
            if pad_type == VDD:
                pin_name = 'vdd'
            elif pad_type == VSS:
                pin_name = 'vss'
            elif pad_type == VDDIO:
                pin_name = 'vddio'
            elif pad_type == VSSIO:
                pin_name = 'vssio'
            pad_name = f'{pin_name}{i}'
        pad_h = fp.available_cells[pad_type].height
        fp.place_macros([(pad_name, pad_type)], x, top_h - pad_h, 0, 0, 'N')
        fp.place_pins([pin_name], x + pin_offset_width, top_h - pin_offset_depth,
                      0, 0, pin_dim, pin_dim, 'm5')
    # Place E pads:
    indices[GPIO] = 0
    for pad_type, y in ea_pads:
        i = indices[pad_type]
        indices[pad_type] += 1
        if pad_type == GPIO:
            pad_name = f'padring.ea_pads\\[0\\].i0.padio\\[{i}\\].i0.gpio'
            pin_name = f'ea_pad'
        else:
            if pad_type == VDD:
                pin_name = 'vdd'
            elif pad_type == VSS:
                pin_name = 'vss'
            elif pad_type == VDDIO:
                pin_name = 'vddio'
            elif pad_type == VSSIO:
                pin_name = 'vssio'
            pad_name = f'{pin_name}{i}'
        pad_h = fp.available_cells[pad_type].height
        fp.place_macros([(pad_name, pad_type)], top_w - pad_h, y, 0, 0, 'E')
        fp.place_pins([pin_name], top_w - pin_offset_depth, y + pin_offset_width,
                      0, 0, pin_dim, pin_dim, 'm5')
    # Place S pads:
    indices[GPIO] = 0
    for pad_type, x in so_pads:
        i = indices[pad_type]
        indices[pad_type] += 1
        if pad_type == GPIO:
            pad_name = f'padring.so_pads\\[0\\].i0.padio\\[{i}\\].i0.gpio'
            pin_name = f'so_pad[{i}]'
        else:
            if pad_type == VDD:
                pin_name = 'vdd'
            elif pad_type == VSS:
                pin_name = 'vss'
            elif pad_type == VDDIO:
                pin_name = 'vddio'
            elif pad_type == VSSIO:
                pin_name = 'vssio'
            pad_name = f'{pin_name}{i}'
        fp.place_macros([(pad_name, pad_type)], x, 0, 0, 0, 'S')
        fp.place_pins([pin_name], x + pin_offset_width, pin_offset_depth,
                       0, 0, pin_dim, pin_dim, 'm5')

    ## Connections to vddio pins (Note: no VDDIO in this design)
    pin_width = 23.9
    pin_offsets = (0.495, 50.39)
    pad_h = fp.available_cells[VDDIO].height
    pow_gap = fp.available_cells[GPIO].height - pad_h
    # Place wires/pins connecting power pads to the power ring
    fp.add_net('_vddio', [], 'power')
    for pad_type, y in we_pads:
        if pad_type == VDDIO:
            for offset in pin_offsets:
                fp.place_wires (['_vddio'], pad_h, y + offset, 0, 0,
                                margin_left + pow_gap, pin_width, 'm3')
    margin_top = core_h - (margin_bottom + place_h)
    for pad_type, x in no_pads:
        if pad_type == VDDIO:
            for offset in pin_offsets:
                fp.place_wires (['_vddio'], x + offset, top_h - pad_h - (margin_top + pow_gap), 0, 0,
                                pin_width, margin_top + pow_gap, 'm3')
    margin_right = core_w - (margin_left + place_w)
    for pad_type, y in ea_pads:
        if pad_type == VDDIO:
            for offset in pin_offsets:
                fp.place_wires (['_vddio'], top_w - pad_h - (margin_right + pow_gap), y + offset, 0, 0,
                                margin_right + pow_gap, pin_width, 'm3')
    for pad_type, x in so_pads:
        if pad_type == VDDIO:
            for offset in pin_offsets:
                fp.place_wires (['_vddio'], x + offset, pad_h, 0, 0,
                                pin_width, margin_bottom + pow_gap, 'm3')

    # Place padring corners.
    fp.place_macros([('corner_sw', CORNER)], 0, 0, 0, 0, 'S')
    fp.place_macros([('corner_nw', CORNER)], 0, top_h - corner_w, 0, 0, 'W')
    fp.place_macros([('corner_se', CORNER)], top_w - corner_h, 0, 0, 0, 'E')
    fp.place_macros([('corner_ne', CORNER)], top_w - corner_w, top_h - corner_h, 0, 0, 'N')

    # Place padring I/O fillers.
    fp.fill_io_region([(0, 0), (fill_cell_h, top_h)], FILL_CELLS, 'W', 'v')
    fp.fill_io_region([(0, top_h - fill_cell_h), (top_w, top_h)], FILL_CELLS, 'N', 'h')
    fp.fill_io_region([(top_w - fill_cell_h, 0), (top_w, top_h)], FILL_CELLS, 'E', 'v')
    fp.fill_io_region([(0, 0), (top_w, fill_cell_h)], FILL_CELLS, 'S', 'h')

    # Place core design inside the padring.
    fp.place_macros([('core', 'heartbeat')], gpio_h, gpio_h, 0, 0, 'N')

def build_core():
    # Build the core internal design.
    core_chip = configure_chip('heartbeat')
    core_chip.write_manifest('heartbeat_manifest.json')
    core_fp = Floorplan(core_chip)
    core_floorplan(core_fp)
    core_fp.write_def('heartbeat.def')
    core_fp.write_lef('heartbeat.lef')

    # Configure the Chip object for a full build.
    core_chip.set('input', 'floorplan.def', 'heartbeat.def', clobber=True)
    core_chip.set('input', 'verilog', 'heartbeat.v')
    core_chip.set('tool', 'openroad', 'var', 'place', '0', 'place_density', ['0.15'])
    core_chip.set('tool', 'openroad', 'var', 'route', '0', 'grt_allow_congestion', ['true'])
    core_chip.clock(pin='clk', period=20)

    # Run the ASIC build flow with the resulting floorplan.
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
    lib = Chip(libname)
    chip.add('asic', 'macrolib', libname)
    lib.set('model', 'layout', 'lef', stackup, 'heartbeat.lef')
    lib.set('model', 'layout', 'gds', stackup, 'heartbeat.gds')
    lib.set('output', 'netlist', 'heartbeat.vg')
    chip.import_library(lib)

    fp = Floorplan(chip)
    top_floorplan(fp)
    fp.write_def('heartbeat_top.def')
    chip.set('input', 'def', 'heartbeat_top.def')

    chip.set('input', 'verilog', 'heartbeat_top.v')
    chip.add('input', 'verilog', 'heartbeat.bb.v')
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
