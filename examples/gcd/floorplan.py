from siliconcompiler.floorplan import snap

def setup_floorplan(fp, chip):
    cell_h = fp.std_cell_height
    fp.create_die_area(72 * cell_h, 72 * cell_h, core_area=(8 * cell_h, 8 * cell_h, 64 * cell_h, 64 * cell_h))
    die_w, die_h = fp.die_area

    in_pins = ['clk']
    in_pins += [f'req_msg[{i}]' for i in range(32)]
    in_pins += ['req_val', 'reset', 'resp_rdy']

    out_pins = ['req_rdy']
    out_pins += [f'resp_msg[{i}]' for i in range(16)]
    out_pins += ['resp_val']

    metal = 'm3'
    width = 1 * fp.layers[metal]['width']
    depth = 3 * fp.layers[metal]['width']

    spacing_we = die_h / (len(in_pins) + 1)
    pitch_we = snap(spacing_we, fp.layers[metal]['ypitch'])
    offset_we = fp.snap_to_y_track(spacing_we, metal)

    spacing_ea = die_h / (len(out_pins) + 1)
    pitch_ea = snap(spacing_ea, fp.layers[metal]['ypitch'])
    offset_ea = fp.snap_to_y_track(spacing_ea, metal)

    fp.place_pins(in_pins, offset_we, pitch_we, 'w', width, depth, metal)
    fp.place_pins(out_pins, offset_ea, pitch_ea, 'e', width, depth, metal)

    return fp
