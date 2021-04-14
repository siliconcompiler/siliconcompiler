def setup_floorplan(fp, chip):
    w = fp.std_cell_width
    h = fp.std_cell_height

    fp.create_die_area(64 * w, 9 * h, core_area=(8 * w, 1 * h, 56 * w, 8 * h))

    metal = 'm3'
    width = 1
    depth = 3
    fp.place_pins(['clk'], 'w', width, depth, metal)
    fp.place_pins(['c[0]', 'c[1]'], 'e', width, depth, metal)

    return fp
