# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.

import logging
import math
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
DIVIDERCHAR "{{ layout.dividerchar }}" ;
BUSBITCHARS "{{ layout.busbitchars }}" ;
DESIGN {{ layout.design }} ;
UNITS DISTANCE MICRONS {{ layout.units }} ;
DIEAREA {% for coord in layout.diearea %}{{ coord | render_tuple }} {% endfor %};

{% for name, row in layout.row.items() %}
ROW {{ name }} {{ row.site }} {{ row.x }} {{ row.y }} {{ row.orientation }}
    DO {{ row.numx }} BY {{ row.numy }} STEP {{ row.stepx }} {{ row.stepy }} ;
{% endfor %}

{% for name, track in layout.track.items() %}
TRACKS {{ track.direction | upper }} {{ track.start }} DO {{ track.total }} STEP {{ track.step }}
    LAYER {{ track.layer}} ;
{% endfor %}

COMPONENTS {{ layout.component | length }} ;
{% for name, c in layout.component.items() %}
   - {{ name }} {{ c.cell }}
      {% if c.status %}
      + {{ c.status | upper }} ( {{c.x }} {{ c.y }} ) {{ c.orientation }}
      {% endif %}
      + HALO {{ c.halo | join(' ') }} ;
{% endfor %}
END COMPONENTS

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
    '''Floorplan layout class'''

    def __init__(self, chip, db_units=2000):
        '''Initializes Floorplan object.

        Args:
            chip (Chip): Object storing the chip config. The Floorplan API
                expects the chip's configuration to be populated with information
                from a tech library, and the API will write to the chip's
                layout configuration.
            db_units (int): Scaling factor to go from microns to DEF DB units.
        '''
        self.chip = chip

        self.die_area = None
        self.core_area = None

        self.chip.layout['version'] = '5.8'
        self.chip.layout['design'] = chip.get('design')[-1]
        self.chip.layout['units'] = db_units

        # extract std cell info based on libname
        libname = self.chip.get('asic', 'targetlib')[-1]
        self.std_cell_name = self.chip.get('stdcell', libname, 'site')[-1]
        self.std_cell_width = float(self.chip.get('stdcell', libname, 'width')[-1])
        self.std_cell_height = float(self.chip.get('stdcell', libname, 'height')[-1])

        # extract layers based on stackup
        stackup = self.chip.get('asic', 'stackup')[-1]
        self.layers = {}
        for name, layer in self.chip.cfg['pdk']['aprlayer'][stackup].items():
            if name == 'default': continue
            self.layers[name] = {}
            self.layers[name]['name'] = layer['name']['value'][-1]
            self.layers[name]['xpitch'] = float(layer['xpitch']['value'][-1])
            self.layers[name]['ypitch'] = float(layer['ypitch']['value'][-1])
            self.layers[name]['xoffset'] = float(layer['xoffset']['value'][-1])
            self.layers[name]['yoffset'] = float(layer['yoffset']['value'][-1])
            self.layers[name]['width'] = float(layer['width']['value'][-1])

        self.db_units = db_units

    def create_die_area(self, width, height, core_area=None, generate_rows=True,
                        generate_tracks=True, units='relative'):
        '''Initializes die.

        Initializes the area of the die and generates placement rows and routing
        tracks. This function must be called before calling place_pins. The
        provided die and core dimensions will overwrite the die/core size
        already present in the chip config.

        Args:
            width (float): Width of die in terms of standard cell height if
                using technology-independent units, otherwise microns.
            height (float): Height of die in terms of standard cell height if
                using technology-independent units, otherwise microns.
            core_area (tuple of float): The core cell area of the physical
                design. This is provided as a tuple (x0 y0 x1 y1), where (x0,
                y0), specifes the lower left corner of the block and (x1, y1)
                specifies the upper right corner. If `None`, core_area is set to
                be equivalent to the die area minus the standard cell height on
                each side.
            generate_rows (bool): Automatically generate rows to fill entire
                core area.
            generate_tracks (bool): Automatically generate tracks to fill entire
                core area.
            units (str): whether to use technology-relative ('relative') or
                absolute ('absolute') units.
        '''
        # store die_area as 2-tuple since bottom left corner is always 0,0
        if units == 'relative':
            width *= self.std_cell_height
            height *= self.std_cell_height

        self.die_area = (width, height)
        if core_area == None:
            self.core_area = (self.std_cell_height,
                              self.std_cell_height,
                              width - self.std_cell_height,
                              height - self.std_cell_height)
        else:
            self.core_area = core_area

        self.chip.set('asic', 'diesize', str((0, 0, width, height)))
        self.chip.set('asic', 'coresize', str(self.core_area))
        self.chip.layout['diearea'] = self._def_scale([(0, 0), self.die_area])

        if generate_rows:
            self.generate_rows()
        if generate_tracks:
            self.generate_tracks()

    def save(self, filename):
        '''Writes chip layout to DEF file.

        Args:
            filename (str): Name of output file.
        '''
        logging.debug('Write DEF %s', filename)

        tmpl = env.from_string(DEF_TEMPLATE)
        layout = self._filter_defaults(self.chip.layout)
        with open(filename, 'w') as f:
            f.write(tmpl.render(layout=layout))

    def place_pins(self, pins, side, width, depth, layer, offset=0, pitch=None,
                   direction='inout', net_name=None, use='signal', fixed=True,
                   units='relative'):
        '''Places pin(s) on floorplan.

        Examples:
            >>> place_pins(['a[0]', 'a[1]'], 'w', 1, 3, 'm1')
            Places pins a[0] and a[1] evenly spaced along the left edge of the
            block

            >>> place_pins(['a[0]', 'a[1]'], 'w', 1, 3, 'm1', pitch=1)
            Places pins a[0] and a[1] centered on the left edge of the block
            with minimal spacing

            >>> place_pins(['out'], 'n', 1, 3, 'm1', offset=3.5, units='absolute')
            Places pin out along the top edge of the block, 3.5 microns from the
            left side

        Args:
            pins (list of str): List of pin names to place.
            side (str): Which side of the block to place the pins along. Options
                are 'n', 's', 'e', or 'w' (case insensitive).
            width (float): Width of pin.
            depth (float): Depth of pin.
            layer (str): Which metal layer pin is placed on.
            offset (int): How far to place first pin from edge. If `None`,
                center pins along edge, snapped to grid.
            pitch (int): Spacing between pins. If `None`, pins will be evenly
                spaced between `offset` and the far edge of the side, snapped to
                grid.
            direction (str): I/O direction of pins (must be valid LEF/DEF
                direction).
            net_name (str): Name of net that each pin is connected to. If `None`,
                the net name of each pin will correspond to the pin name.
            use (str): Usage of pin (must be valid LEF/DEF use).
            fixed (bool): Whether pin status is 'FIXED' or 'PLACED'.
            units (str): whether to use technology-relative ('relative') or
                absolute ('absolute') units.
        '''
        logging.debug('Placing pins: %s', ' '.join(pins))

        if side.upper() not in ('N', 'S', 'E', 'W'):
            raise ValueError('Invalid side')
        if direction.upper() not in ('INPUT', 'OUTPUT', 'INOUT', 'FEEDTHRU'):
            raise ValueError('Invalid direction')
        if use.upper() not in ('SIGNAL', 'POWER', 'GROUND', 'CLOCK', 'TIEOFF',
                               'ANALOG', 'SCAN', 'RESET'):
            raise ValueError('Invalid use')
        self._validate_units(units)

        if self.die_area is None:
            raise ValueError('Die area must be initialized with create_die_area!')

        # Convert all received dimensions to microns
        if units == 'relative':
            pin_scale_factor = self.layers[layer]['width']
            if side.upper() in ('N', 'S'):
                pos_scale_factor = self.layers[layer]['xoffset']
            else: # E, W
                pos_scale_factor = self.layers[layer]['yoffset']

            width *= pin_scale_factor
            depth *= pin_scale_factor

            if pitch is not None:
                pitch *= pos_scale_factor
            if offset is not None:
                offset *= pos_scale_factor

        block_w, block_h = self.die_area

        if pitch is None:
            if offset is None: offset = 0

            # no pitch provided => infer equal pin spacing
            num_pins = len(pins)
            if side.upper() in ('N', 'S'):
                pitch = (block_w - offset) / (num_pins + 1)
            else:
                pitch = (block_h - offset) / (num_pins + 1)
            offset += pitch
        elif offset is None:
            # no offset provided => infer center pins
            if side.upper() in ('N', 'S'):
                die_center = block_w / 2
            else:
                die_center = block_h / 2

            pin_distance = pitch * len(pins)
            offset = die_center - pin_distance / 2

        # TODO: might be nice to add sanity checks for pitch and offset values
        # (to make sure there are no overlapping pins etc.)

        if side.upper() == 'N':
            x     = offset
            y     = block_h - depth/2
            xincr = pitch
            yincr = 0.0
            shape = [(-width/2, -depth/2), (width/2, depth/2)]
        elif side.upper() == 'S':
            x     = offset
            y     = depth/2
            xincr = pitch
            yincr = 0.0
            shape = [(-width/2, -depth/2), (width/2, depth/2)]
        elif side.upper() == 'W':
            x     = depth/2
            y     = offset
            xincr = 0
            yincr = pitch
            shape = [(-depth/2, -width/2), (depth/2, width/2)]
        elif side.upper() == 'E':
            x     = block_w - depth/2
            y     = offset
            xincr = 0
            yincr = pitch
            shape = [(-depth/2, -width/2), (depth/2, width/2)]

        for pin_name in pins:
            # if units == relative, snap the appropriate dimension to grid
            # before placing
            if units == 'relative':
                if side.upper() in ('N', 'S'):
                    pos = self._snap_to_x_track(x, layer), y
                else:
                    pos = x, self._snap_to_y_track(y, layer)
            else:
                pos = x, y

            pin = {
                'net': net_name if net_name else pin_name,
                'direction': direction,
                'use': use
            }
            port = {
                'layer': self.layers[layer]['name'],
                'box': self._def_scale(shape),
                'status': 'fixed' if fixed else 'placed',
                'point': self._def_scale(pos),
                'orientation': 'N'
            }
            self.chip.layout['pin'][pin_name] = pin
            self.chip.layout['pin'][pin_name]['port'] = port

            x += xincr
            y += yincr


    def place_macro(self, instance_name, macro_name, pos, orientation,
                    halo=(0, 0, 0, 0), fixed=True, units='relative'):
        ''' Places macro on floorplan.

        Args:
            name (str): Name of macro instance in design.
            macro_name (str): name of macro in library.
            pos (tuple of int): Position of macro as tuple of 2 numbers.
            orientation (str): Orientation of macro (as LEF/DEF orientation).
            halo (tuple of int): Halo around macro as tuple (left bottom right
                top).
            fixed (bool): Whether or not macro placement is fixed or placed.
            units (str): Whether to use technology-independent ('relative') or
                absolute ('absolute') units.
        '''
        logging.debug('Placing macro: %s', instance_name)

        self._validate_orientation(orientation)
        self._validate_units(units)

        x, y = pos
        if units == 'relative':
            x *= self.std_cell_width
            y *= self.std_cell_height

        component = {
            'cell': macro_name,
            'x': self._def_scale(x),
            'y': self._def_scale(y),
            'status': 'fixed' if fixed else 'placed',
            'orientation': orientation.upper(),
            'halo': halo,
        }
        self.chip.layout['component'][instance_name] = component

    def generate_rows(self, site_name=None, flip_first_row=False, area=None,
                      units='relative'):
        '''Auto-generates placement rows based on floorplan parameters and tech
        library.

        Args:
            site_name (str): Name of placement site to specify in rows. If
                `None`, uses default site specified by library file.
            flip_first_row (bool): Determines orientation of row placement
                sites. If `False`, alternates starting at "FS", if `True`,
                alternates starting at "N".
            area (tuple of float): Area to fill with rows as tuple of four floats.
                If `None`, fill entire core area. Specified as microns.
            units (str): Whether to use technology-independent ('relative') or
                absolute ('absolute') units.
        '''
        logging.debug("Placing rows")

        # clear existing rows, since we'll generate new ones from scratch using
        # floorplan parameters
        self.chip.layout['row'].clear()

        if site_name == None:
            site_name = self.std_cell_name

        if area and units == 'relative':
            area = [v * self.std_cell_height for v in area]
        elif area == None:
            area = self.core_area

        start_x = area[0]
        start_y = area[1]
        core_width = area[2] - start_x
        core_height = area[3] - start_y

        num_rows = int(core_height / self.std_cell_height)
        num_x = core_width // self.std_cell_width

        for i in range(num_rows):
            name = f'ROW_{i}'
            orientation = 'FS' if (i % 2 == 0 and not flip_first_row) else 'N'
            row = {
                'site': site_name,
                'x': self._def_scale(start_x),
                'y': self._def_scale(start_y),
                'orientation': orientation,
                'numx': num_x,
                'numy': 1,
                'stepx' : self._def_scale(self.std_cell_width),
                'stepy' : 0
            }
            self.chip.layout['row'][name] = row

            start_y += self.std_cell_height

    def generate_tracks(self, area=None, units='relative'):
        '''
        Auto-generates routing tracks based on floorplan parameters and tech
        library.

        Args:
            area (tuple of float): Area to fill with tracks as tuple of four floats.
                If `None`, fill entire die area. Specified as microns.
            units (str): Whether to use technology-independent ('relative') or
                absolute ('absolute') units.
        '''
        logging.debug("Placing tracks")

        # clear existing rows, since we'll generate new ones from scratch using
        # floorplan parameters
        self.chip.layout['track'].clear()

        if area and units == 'relative':
            area = [v * self.std_cell_height for v in area]
        elif area == None:
            area = (0, 0, self.die_area[0], self.die_area[1])

        start_x, start_y, die_width, die_height = area

        for layer in self.layers.values():
            layer_name = layer['name']
            offset_x = layer['xoffset'] + start_x
            offset_y = layer['yoffset'] + start_y
            pitch_x = layer['xpitch']
            pitch_y = layer['ypitch']

            num_tracks_x = math.floor((die_width - offset_x) / pitch_x) + 1
            num_tracks_y = math.floor((die_height - offset_y) / pitch_y) + 1

            track_x = {
                'layer': layer_name,
                'direction': 'x',
                'start': self._def_scale(offset_x),
                'step': self._def_scale(pitch_x),
                'total': num_tracks_x
            }
            track_y = {
                'layer': layer_name,
                'direction': 'y',
                'start': self._def_scale(offset_y),
                'step': self._def_scale(pitch_y),
                'total': num_tracks_y
            }

            self.chip.layout['track'][f'{layer_name}_X'] = track_x
            self.chip.layout['track'][f'{layer_name}_Y'] = track_y

    def _filter_defaults(self, layout):
        layout = self.chip.layout.copy()
        del layout['pin']['default']
        del layout['component']['default']
        return layout

    def _def_scale(self, val):
        if isinstance(val, list):
            return [self._def_scale(item) for item in val]
        elif isinstance(val, tuple):
            return tuple([self._def_scale(item) for item in val])
        else:
            # TODO: rounding and making this an int seems helpful for resolving
            # floating point rounding issues, but could be problematic if we
            # want to have floats in DEF file? Alternative could be to use
            # Python decimal library for internally representing micron values
            return int(round(val * self.db_units))

    def _snap_to_x_track(self, x, layer):
        offset = self.layers[layer]['xoffset']
        pitch = self.layers[layer]['xpitch']
        return round((x - offset) / pitch) * pitch + offset

    def _snap_to_y_track(self, y, layer):
        offset = self.layers[layer]['yoffset']
        pitch = self.layers[layer]['ypitch']
        return round((y - offset) / pitch) * pitch + offset

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
    from asic.targets.freepdk45 import *
    c = Chip()
    c.set('design', 'test')
    setup_platform(c)
    setup_libs(c)
    setup_design(c)

    fp = Floorplan(c)
    fp.create_die_area(100.13, 100.8, core_area=(10.07, 11.2, 90.25, 91))

    n = 4 # pins per side
    width = 10
    depth = 30
    metal = 'm3'

    fp.place_macro('myram', 'RAM', (25, 25), 'N')

    pins = [f"in[{i}]" for i in range(4 * n)]
    fp.place_pins(pins[0:n], 'n', width, depth, metal)
    fp.place_pins(pins[n:2*n], 'e', width, depth, metal)
    fp.place_pins(pins[2*n:3*n], 'w', width, depth, metal)
    fp.place_pins(pins[3*n:4*n], 's', width, depth, metal)

    fp.save('test.def')
