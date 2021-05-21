# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.

# KLayout script to export a GDS file as an SVG.

import pya

# Read data from the GDS file, using the default KLayout colors/etc.
win = pya.Application.instance().main_window()
lm = win.load_layout(design_name + '.gds', 0)
ly = lm.layout()
lv = win.current_view()
cell = ly.cell(design_name)
bb = cell.bbox()
# Actual scale is micrometers: (DB units / 1000.0).
# But that makes a tiny SVG, and not all web browsers can zoom past 10x-ish.
dbu = ly.dbu * 2.0
bb_h = bb.height() * dbu
bb_w = bb.width() * dbu
ctrans = pya.CplxTrans(1.0, 0.0, True, -bb.left, bb.top)

# Write out an SVG file containing all polygons from the GDS layers.
with open('outputs/' + design_name + '.svg', 'w') as svg:
    # Write a basic SVG header.
    svg.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n')
    svg.write('<svg xmlns:svg="http://www.w3.org/2000/svg" '
              'xmlns="http://www.w3.org/2000/svg" '
              'xmlns:xlink="http://www.w3.org/1999/xlink" '
              'width="%.10fmm" '
              'height="%.10fmm" '
              'viewBox="0 0 %.10f %.10f" '
              'version="1.1">\n'%(bb_w, bb_h, bb_w, bb_h))

    # Write all relevant paths.
    for layer in range(ly.layers()):
        # Get layer properties.
        lp = None
        lpi = lv.begin_layers()
        while not lpi.at_end():
            if lpi.current().layer_index() == layer:
                lp = lpi.current()
                break
            lpi = lpi.next()
        # TODO: I'm not sure if this RGBA format is right; I like the pastel
        # sunset colors that it comes up with, but they are different from
        # the usual KLayout color schemes.
        fill_color = '%X'%lp.fill_color

        # Using <g> ('group') tags should let us write a viewer which can
        # selectively show and hide different GDS layers.
        svg.write('  <g id="' + str(layer) + '">\n')
        # Iterate over all paths in this layer, and write them in SVG format.
        citer = cell.begin_shapes_rec(layer)
        while not citer.at_end():
            sh = citer.shape()
            if sh.is_path() or sh.is_box() or sh.is_polygon():
                # Each polygon can be drawn as a single path.
                # They consist of 'hulls' and 'holes'. The first stroke marks
                # the outline, and 'z' separators demarcate new strokes.
                # Overlapping strokes within the same path are 'holes'.
                # (But most paths are rectangles, and have no holes.)
                poly = sh.polygon.transformed(ctrans * citer.trans())
                svg.write('    <path style="fill:#%s" '%fill_color)
                svg.write('d="M ')
                f = True
                for point in poly.each_point_hull():
                    if f:
                        svg.write('%.10f %.10f '%(point.x*dbu, point.y*dbu))
                        f = False
                    else:
                        svg.write('L %.10f %.10f '%(point.x*dbu, point.y*dbu))
                svg.write(' z ')
                for h in range(poly.holes()):
                    svg.write(' M ')
                    f = True
                    for point in poly.each_point_hole(h):
                        if f:
                            svg.write('%.10f %.10f '%(point.x*dbu, point.y*dbu))
                            f = False
                        else:
                            svg.write('L %.10f %.10f '%(point.x*dbu, point.y*dbu))
                    svg.write(' z ')
                svg.write('"/>\n')
            citer.next()
        svg.write('  </g>\n\n')

    # Done.
    svg.write('</svg>')

print('Done!')
win.close_all()
