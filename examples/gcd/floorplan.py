def setup_floorplan(fp, chip):
    fp.create_die_area(72, 72, core_area=(8, 8, 64, 64))

    in_pins = ['clk']
    in_pins += [f'req_msg[{i}]' for i in range(32)]
    in_pins += ['req_val', 'reset', 'resp_rdy']

    out_pins = ['req_rdy']
    out_pins += [f'resp_msg[{i}]' for i in range(16)]
    out_pins += ['resp_val']

    metal = 'm3'
    width = 1
    depth = 3
    fp.place_pins(in_pins, 'w', width, depth, metal)
    fp.place_pins(out_pins, 'e', width, depth, metal)

    return fp
