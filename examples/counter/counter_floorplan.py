def setup_floorplan(fp):
    pin_width = 560
    pin_depth = 760
    fp.place_pinlist(['clk'], 'w', pin_width, pin_depth, 'metal3')
    fp.place_pinlist(['c[0]', 'c[1]'], 'e', pin_width, pin_depth, 'metal3', direction='output')

    return fp
