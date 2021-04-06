# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.

import logging
import jinja2

# Set up Jinja
env = jinja2.Environment(loader=jinja2.BaseLoader, trim_blocks=True, lstrip_blocks=True)

# Jinja filter for rendering tuples in DEF style, e.g. (0, 0) becomes "( 0 0 )"
def render_tuple(vals):
    vals_str = ' '.join([str(val) for val in vals])
    return f"( {vals_str} )"
env.filters['render_tuple'] = render_tuple

# Jinja template for outputting layout as DEF file
DEF_TEMPLATE = """VERSION {{ layout.version }} ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;
DESIGN {{ layout.design }} ;
UNITS DISTANCE MICRONS 2000 ;
DIEAREA {% for coord in layout.diearea %}{{ coord | render_tuple }} {% endfor %};

PINS {{ layout.pin | length }} ;
{% for name, pin in layout.pin.items() %}
    - {{ name }} + NET {{ pin.net }} + DIRECTION {{ pin.direction|upper }} + USE {{ pin.use|upper }}
       + PORT
         + LAYER {{ pin.port.layer }} {{ pin.port.box | map('render_tuple') | join(' ') }}
         {% if pin.port.status %}
         + {{ pin.port.status|upper }} {{ pin.port.point | render_tuple }} {{ pin.port.orientation }} ;
         {% endif %}
{% endfor %}
END PINS

END DESIGN
"""

class Floorplan:
    '''
    Floorplan layout class
    '''

    def __init__(self, chip,
                 # TODO: read from synthesis metrics
                 die_area,
                 # TODO: read from LEF/library files
                 # layers,
                 # std_cell_width,
                 # std_cell_height,
                 scale_factor):
        '''
        Initialize Floorplan
        '''
        self.chip = chip
        self.die_area = die_area

        self.chip.layout['version'] = '5.8'
        self.chip.layout['design'] = chip.get('design')[-1]
        self.chip.layout['diearea'] = die_area

        # self.layers = layers
        # self.std_cell_width = std_cell_width
        # self.std_cell_height = std_cell_height
        self.scale_factor = scale_factor

    def save(self, filename):
        '''
        Write DEF file
        '''
        logging.info('Write DEF %s', filename)

        # TODO: come up with cleaner way to handle defaults
        old_layout = self.chip.layout
        del self.chip.layout['pin']['default']

        tmpl = env.from_string(DEF_TEMPLATE)
        with open(filename, 'w') as f:
            f.write(tmpl.render(layout=self.chip.layout))

        self.chip.layout = old_layout

    def place_pin(self, pin_name, net_name, pos, shape, layer, orientation,
                  direction='input', use='signal', fixed=True, units='relative'):
        '''
        Place pin on floorplan

        Parameters:
        - pin_name: name of pin
        - net_name: name of connected net
        - pos: position of pin, as tuple of 2 numbers
        - shape: geometry of pin, as list of 2 or more tuples of 2 numbers
        - layer: layer of pin
        - orientation: orientation of pin (must be a valid LEF/DEF orientation)
        - direction: I/O direction of pin (must be valid LEF/DEF direction)
        - use: use of pin (must be valid LEF/DEF use)
        - fixed: whether or not pin is fixed
        - units: whether to use technology-independent ('relative') or absolute
          ('absolute') units
        '''
        logging.debug('Placing a pin: %s', pin_name)

        if direction.upper() not in ('INPUT', 'OUTPUT', 'INOUT', 'FEEDTHRU'):
            raise ValueError('Invalid direction')
        if use.upper() not in ('SIGNAL', 'POWER', 'GROUND', 'CLOCK', 'TIEOFF',
                               'ANALOG', 'SCAN', 'RESET'):
            raise ValueError('Invalid use')
        self._validate_orientation(orientation)
        self._validate_units(units)

        pin = {
            'net': net_name,
            'direction': direction,
            'use': use
        }

        port = {
            'layer': layer,
            'box': self._scale(shape, units),
            'status': 'fixed' if fixed else None,
            'point': self._scale(pos, units),
            'orientation': orientation
        }

        self.chip.layout['pin'][pin_name] = pin
        self.chip.layout['pin'][pin_name]['port'] = port

    def place_pinlist(self, pinlist, side, pin_width, pin_depth, layer,
                      pitch=None, offset=2, halo=2, block_w=None, block_h=None,
                      direction='input', units='relative'):

        '''Place a list of pins along the side of a block

        Parameters:
        - pinlist: list of pin names (must be the same as the corresponding net
          name)
        - side: which side of the block to place the pins along. Options are
          'n', 's', 'e', or 'w' (case insensitive)
        - layer: the name of the layer to place the pins on
        - pitch: the spacing between pins. If None, place pins equally spaced
          along side (this overwrites provided offset, if any)
        - block_w, block_h: the width and the height of the block defining the
          sides the pins are to be placed along. If None, infers bounds from die
          area
        - direction: I/O direction of the pins
        - units: whether to use technology-independent ('relative') or absolute
          ('absolute') units

        All other parameters specify dimensions as shown in this diagram (this
        example is for the north side of the block):

                          <----------pitch-------->
        -----------+-----|-----+-------------------|-------- ...
        |<-offset->|I halo     | ^
        |          +-----------+ |           +-----------+
        |          |           | pin         |           |
        |          |    PIN    | depth       |    PIN    |
        |          |           | |           |           |
        |          +-----------+ |           +-----------+
        |          |I halo     | |
        |          +-----------+ v
        |          <-pin width->
        |
        ...

        '''
        logging.debug('Placing pins: %s', ' '.join(pinlist))

        self._validate_units(units)
        if side.upper() not in ('N', 'S', 'E', 'W'):
            raise ValueError('Invalid side')

        pin_width = self._scale(pin_width, units)
        pin_depth = self._scale(pin_depth, units)
        halo = self._scale(halo, units)

        if (block_w is None or block_h is None) and len(self.die_area) != 2:
            raise ValueError('block_w and block_h must be set explicitly for '
                             'non-rectangular die area')
        if block_w is None:
            block_w = self.die_area[1][0] - self.die_area[0][0]
        else:
            block_w = self._scale(block_w, units)
        if block_h is None:
            block_h = self.die_area[1][1] - self.die_area[0][1]
        else:
            block_h = self._scale(block_h, units)

        if pitch is None:
            # no pitch provided => infer equal pin spacing
            num_pins = len(pinlist)
            pitch = block_w / (num_pins + 1)
            offset = pitch - pin_width/2
        else:
            pitch = self._scale(pitch, units)
            offset = self._scale(offset, units)

        if side.upper() == 'N':
            x0    = offset
            y0    = block_h - halo
            x1    = x0 + pin_width
            y1    = y0 - pin_depth + 2 * halo
            xincr = pitch
            yincr = 0.0
        elif side.upper() == 'S':
            x0    = offset
            y0    = halo
            x1    = x0 + pin_width
            y1    = y0 + pin_depth - 2 * halo
            xincr = pitch
            yincr = 0.0
        elif side.upper() == 'W':
            x0    = halo
            y0    = offset
            x1    = x0 + pin_depth - 2 * halo
            y1    = y0 + pin_width
            xincr = 0.0
            yincr = pitch
        elif side.upper() == 'E':
            x0    = block_w - halo
            y0    = offset
            x1    = x0 - pin_depth + 2 * halo
            y1    = y0 + pin_width
            xincr = 0.0
            yincr = pitch

        for name in pinlist:
            shape = [(0, 0), (x1 - x0, y1 - y0)]
            self.place_pin(name, name, (x0, y0), shape, layer, 'N',
                           direction=direction, units='absolute')
            #Update with new values
            x0 += xincr
            y0 += yincr
            x1 += xincr
            y1 += yincr

    def _scale(self, val, units):
        if isinstance(val, list):
            return [self._scale(item, units) for item in val]
        elif isinstance(val, tuple):
            return tuple([self._scale(item, units) for item in val])
        else:
            if units == 'absolute':
                return val
            else:
                return val * self.scale_factor

    def _validate_units(self, units):
        if units not in ('relative', 'absolute'):
            raise ValueError("Units must be 'relative' or 'absolute'")

    def _validate_orientation(self, orientation):
        if orientation not in ('N', 'S', 'W', 'E', 'FN', 'FS', 'FW', 'FE'):
            raise ValueError("Illegal orientation")

if __name__ == '__main__':
    # Test: create floorplan with `n` equally spaced `width` x `depth` pins along
    # each side

    from siliconcompiler.core import *
    c = Chip()
    c.set('design', 'test')
    fp = Floorplan(c, [(0, 0), (100, 100)], 1)

    n = 4 # pins per side
    width = 8
    depth = 12

    pins = [f"in[{i}]" for i in range(4 * n)]
    fp.place_pinlist(pins[0:n], 'n', width, depth, 'metal1')
    fp.place_pinlist(pins[n:2*n], 'e', width, depth, 'metal1')
    fp.place_pinlist(pins[2*n:3*n], 'w', width, depth, 'metal1')
    fp.place_pinlist(pins[3*n:4*n], 's', width, depth, 'metal1')

    fp.save('test.def')
