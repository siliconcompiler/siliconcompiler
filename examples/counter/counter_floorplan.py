def setup_floorplan(fp, chip):
    fp.create_die_area(9, 9)

    metal = 'm3'
    width = 1
    depth = 3
    fp.place_pins(['clk'], 'w', width, depth, metal)
    fp.place_pins(['c[0]', 'c[1]'], 'e', width, depth, metal)

    return fp
