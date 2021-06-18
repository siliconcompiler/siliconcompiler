# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.

import logging
import math
import jinja2

from siliconcompiler.leflib import Lef
from siliconcompiler.schema import schema_path

# Set up Jinja
env = jinja2.Environment(loader=jinja2.PackageLoader('siliconcompiler'),
                         trim_blocks=True, lstrip_blocks=True)

# Jinja filter for rendering tuples in DEF style, e.g. (0, 0) becomes "( 0 0 )"
def render_tuple(vals):
    vals_str = ' '.join([str(val) for val in vals])
    return f"( {vals_str} )"
env.filters['render_tuple'] = render_tuple

def pt_in_box(pt, box):
    x, y = pt
    box_min_x, box_min_y = box[0]
    box_max_x,  box_max_y = box[1]

    return x >= box_min_x and x < box_max_x and y >= box_min_y and y < box_max_y

class Floorplan:
    '''Floorplan layout class'''

    # These cell names correspond to I/O cells
    # They must be mapped to the technology-specific implementations in
    # chip.cfg['iocell'][libname]['cells'][...]

    # TODO: seems plausible an I/O library might contain more cells than this...
    # (for example, multiple corners?). We could generate this list dynamically
    # by looking at keys in chip.cfg['iocell'][libname]['cells']
    IO_CELLS = ['gpio', 'vdd', 'vss', 'vddio', 'vssio', 'corner']

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

        self.design = chip.get('design')[-1]
        self.db_units = db_units
        self.die_area = None
        self.core_area = None
        self.pins = []
        self.macros = []
        self.rows = []
        self.tracks = []

        self.blockage_layers = []

        # Set up custom Jinja `scale` filter as a closure around `self` so we
        # don't have to pass in db_units
        def scale(val):
            if isinstance(val, list):
                return [scale(item) for item in val]
            elif isinstance(val, tuple):
                return tuple([scale(item) for item in val])
            else:
                # TODO: rounding and making this an int seems helpful for resolving
                # floating point rounding issues, but could be problematic if we
                # want to have floats in DEF file? Alternative could be to use
                # Python decimal library for internally representing micron values
                return int(round(val * self.db_units))
        env.filters['scale'] = scale

        self.fill_cell_id = 0

        ## Extract technology-specific info ##

        # extract std cell info based on libname
        self.libname = self.chip.get('asic', 'targetlib')[-1]
        self.std_cell_name = self.chip.get('stdcell', libname, 'site')[-1]
        self.std_cell_width = float(self.chip.get('stdcell', libname, 'width')[-1])
        self.std_cell_height = float(self.chip.get('stdcell', libname, 'height')[-1])

        # Extract data from LEFs
        lef_parser = Lef()
        stackup = chip.get('asic', 'stackup')[-1]
        libtype = chip.get('stdcell', self.libname, 'libtype')[-1]

        tech_lef = schema_path(chip.get('pdk','aprtech', stackup, libtype, 'lef')[-1])
        with open(tech_lef, 'r') as f:
            tech_lef_data = lef_parser.parse(f.read())

        lib_lef = schema_path(chip.get('iocell', self.libname, 'lef')[-1])
        with open(lib_lef, 'r') as f:
            lib_lef_data = lef_parser.lib_parse(f.read())

        # TODO: would I/O cells be in a separate library?

        # List of cells the user is able to place
        # TODO: how much sense does it make to place I/O fill cells in this?
        self.available_cells = {}

        # Gather fill cells from schema into a list of ordered (name, size)
        # pairs. This lets us easily implement a greey fill algorithm in
        # `fill_io_region`.
        io_fill_cells = []
        self.io_cell_height = None
        for cell in self.chip.get('iocell', self.libname, 'cells', 'fill'):
            if cell in lib_lef_data['macros']:
                width, height = lib_lef_data['macros'][cell]['size']
            else:
                # TODO: throw nicer exception
                raise Exception()

            self.available_cells[cell] = {
                'tech_name': cell,
                'type': 'io',
                'width': width,
                'height': height
            }

            io_fill_cells.append((cell, float(width)))
            # TODO: throw an error if height is already set but does not match
            if not self.io_cell_height:
                self.io_cell_height = float(height)

        self.io_fill_cells = sorted(io_fill_cells, key=lambda c: c[1], reverse=True)
        
        for cell in self.IO_CELLS:
            tech_name = self.chip.get('iocell', self.libname, 'cells', cell)[-1]
            width, _ = lib_lef_data['macros'][tech_name]['size']
            # TODO: validate that I/O heights are constant?

            self.available_cells[cell] = {
                'tech_name': tech_name,
                'type': 'io',
                'width': width,
                'height': self.io_cell_height
            }

        for macro in self.chip.get('asic', 'macrolib'):
            tech_name = macro
            width = float(self.chip.get('macro', macro, 'width')[-1])
            height = float(self.chip.get('macro', macro, 'height')[-1])

            # TODO: consider assigning a NamedTuple here - that would make it
            # immutable, which is much safer given we'll be storing pointers to
            # these in a macro's 'info' field
            self.available_cells[macro] = {
                'tech_name': tech_name,
                'type': 'macro',
                'width': width,
                'height': height
            }

        # extract layers based on stackup
        stackup = self.chip.get('asic', 'stackup')[-1]
        self.layers = {}
        for name, layer in self.chip.cfg['pdk']['grid'][stackup].items():
            if name == 'default': continue
            self.layers[name] = {}
            pdk_name = layer['name']['value'][-1]
            self.layers[name]['name'] = pdk_name
            self.layers[name]['width'] = float(tech_lef_data['LAYER'][pdk_name]['WIDTH'][-1])
            self.layers[name]['xpitch'] = float(layer['xpitch']['value'][-1])
            self.layers[name]['ypitch'] = float(layer['ypitch']['value'][-1])
            self.layers[name]['xoffset'] = float(layer['xoffset']['value'][-1])
            self.layers[name]['yoffset'] = float(layer['yoffset']['value'][-1])


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
        elif units == 'relative':
            self.core_area = tuple(x * self.std_cell_height for x in core_area)
        else:
            self.core_area = core_area

        # TODO: is this necessary or a good idea?
        self.chip.set('asic', 'diesize', str((0, 0, width, height)))
        self.chip.set('asic', 'coresize', str(self.core_area))

        if generate_rows:
            self.generate_rows()
        if generate_tracks:
            self.generate_tracks()

    def write_def(self, filename):
        '''Writes chip layout to DEF file.

        Args:
            filename (str): Name of output file.
        '''
        logging.debug('Write DEF %s', filename)

        tmpl = env.get_template('floorplan_def.j2')
        with open(filename, 'w') as f:
            f.write(tmpl.render(fp=self))

    def write_lef(self, filename):
        '''Writes chip layout to LEF file.

        Args:
            filename (str): Name of output file.
            macro_name (str): Macro name to use in LEF.
        '''
        logging.debug('Write LEF %s', filename)

        tmpl = env.get_template('floorplan_lef.j2')
        with open(filename, 'w') as f:
            f.write(tmpl.render(fp=self))

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

            port = {
                'layer': self.layers[layer]['name'],
                'box': shape,
                'status': 'fixed' if fixed else 'placed',
                'point': pos,
                'orientation': 'N'
            }
            pin = {
                'name': pin_name,
                'net': net_name if net_name else pin_name,
                'direction': direction,
                'use': use,
                'port': port
            }
            self.pins.append(pin)

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
            'name': instance_name,
            'cell': self.available_cells[macro_name]['tech_name'],
            'info': self.available_cells[macro_name],
            'x': x,
            'y': y,
            'status': 'fixed' if fixed else 'placed',
            'orientation': orientation.upper(),
            'halo': halo,
        }
        self.macros.append(component)

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
        self.rows.clear()

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
                'name': name,
                'site': site_name,
                'x': start_x,
                'y': start_y,
                'orientation': orientation,
                'numx': num_x,
                'numy': 1,
                'stepx' : self.std_cell_width,
                'stepy' : 0
            }
            self.rows.append(row)

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
        self.tracks.clear()

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
                'name': f'{layer_name}_X',
                'layer': layer_name,
                'direction': 'x',
                'start': offset_x,
                'step': pitch_x,
                'total': num_tracks_x
            }
            track_y = {
                'name': f'{layer_name}_Y',
                'layer': layer_name,
                'direction': 'y',
                'start': offset_y,
                'step': pitch_y,
                'total': num_tracks_y
            }

            self.tracks.append(track_x)
            self.tracks.append(track_y)

    def place_blockage(self, layers=None):
        '''
        Places full-area blockages on the specified layers.

        The blockages specified using this method only take effect when dumping
        the floorplan as a LEF macro.

        Args:
            layers (list): List of layers to place blockages on. If `None`,
            block all metal layers.
        '''

        if layers is None:
            layers = list(self.layers.keys())

        for layer in layers:
            if layer in self.layers:
                self.blockage_layers.append(self.layers[layer]['name'])
            else:
                raise ValueError(f'Layer {layer} not found in tech info!')

    def place_macros(self, macros, start_pos, orientation, direction, spacing=0):
        '''Places macros on floorplan.

        Args:
            macros (list of (str, str)): List of macros to place as tuples of
                (instance name, type).
            start_pos (tuple): x, y coordinate where to place first instance.
            orientation (str): Orientation of macro
            direction (str): Direction to place macros ('h' for east-west, 'v'
                for north-south).
            spacing (int): Distance between this pad and previous, in microns.
        '''

        # TODO Validate orientation
        # TODO Validate direciton
        # TODO Validating spacing

        pos_x, pos_y = start_pos

        is_ew_ori = orientation.upper() in ('E', 'W', 'FE', 'FW')
        is_ns_ori = not is_ew_ori

        for instance_name, cell_name in macros:
            cell = self.available_cells[cell_name]
            width = cell['width']
            height = cell['height']

            self.place_macro(instance_name, cell_name, (pos_x, pos_y), orientation, units='absolute')
            
            if direction.lower() == 'h':
                pos_x += spacing + (width if is_ns_ori else height)
            else:
                pos_y += spacing + (width if is_ew_ori else height)

    def place_macros_spaced(self, macros, start_pos, orientation, direction, distance):
        '''Places macros on floorplan.

        Args:
            macros (list of (str, str)): List of macros to place as tuples of
                (instance name, type).
            location (str): Which side of the block to place the pads along. Options
                are 'n', 's', 'e', or 'w' (case insensitive).
            spacing (int): Distance between this pad and previous, in microns.
                If `None`, inserts appropriate space to fill the entire side
                evenly.
        '''
        filled_space = 0
        for _, cell_name in macros:
            width = self.available_cells[cell_name]['width']
            filled_space += width

        # TODO: make sure filled_space < distance
        spacing = (distance - filled_space) / (len(macros) + 1)

        x, y = start_pos
        if direction.lower() == 'h':
            x += spacing
        else:
            y += spacing

        self.place_macros(macros, (x, y), orientation, direction, spacing)

    def fill_io_region(self, region):
        ''' Fill empty space in region with I/O filler cells

        Args:
            region (list of tuple of int): bottom-left and top-right corner of
                region to fill.

        Raises:
            ValueError: Region contains macros such that it is unfillable.
        '''

        # Compute region direction, i.e. whether the cells in the region are
        # lined up horizontally or vertically. If it doesn't have one, raise an
        # exception!
        region_min_x, region_min_y = region[0]
        region_max_x, region_max_y = region[1]

        if (region_max_x - region_min_x) == self.io_cell_height:
            direction = 'v'
        elif (region_max_y - region_min_y) == self.io_cell_height:
            direction = 'h'
        else:
            raise ValueError('Fill region must have at least one dimension equal to I/O cell height!')

        # Gather macros in region. Macros in region must be aligned with the
        # direction of the region, and no macros may be partially contained
        # along the direction axis.
        macros = []
        for macro in self.macros:
            width = macro['info']['width']
            height = macro['info']['height']
            x = macro['x']
            y = macro['y']
            ori = macro['orientation']
            max_y = y + height if ori[-1].lower() in ('n', 's') else y + width
            max_x = x + width if ori[-1].lower() in ('n', 's') else x + height

            if direction == 'h':
                if y >= region_max_y or max_y <= region_min_y:
                    # outside of region vertically
                    continue
                if y != region_min_y and max_y != region_max_y:
                    raise ValueError("Fill region must not contain cells that don't fill it vertically.")

                # if we continue, cell is aligned to region vertically

                left_edge_in = (x >= region_min_x)
                right_edge_in = (max_x <= region_max_x)

                if left_edge_in or right_edge_in:
                    macros.append((x, max_x, macro))
            else:
                if x >= region_max_x or max_x  <= region_min_x:
                    # outside of region horizontally
                    continue
                if x != region_min_x and max_x != region_max_x:
                    raise ValueError("Fill region must not contain cells that don't fill it horizontally.")

                # if we continue, cell is aligned to region horizontally

                bottom_edge_in = (y >= region_min_y)
                top_edge_in = (max_y <= region_max_y)

                if bottom_edge_in or top_edge_in:
                    macros.append((y, max_y, macro))

        # Check macros in the region. They must all be I/O cells, and have the
        # same orientation (but may be flipped).
        orientation = None

        corner_cells = self.chip.get('iocell', self.libname, 'cells', 'corner')
        
        for _, _, macro in macros:
            if macro['info']['type'] != 'io':
                raise ValueError('Fill region must not contain cells other than I/O cells.')
            if macro['cell'] in corner_cells:
                # corner cells work in multiple orientations
                continue
            curr_ori = macro['orientation']
            # only consider last character in orientation since we don't care flipped vs not
            if orientation and orientation[-1] != curr_ori[-1]:
                raise ValueError('Fill region cells must all have same orientation.')
            orientation = curr_ori

        # TODO: need a way to set orientation if the region is only corners...

        # Iterate along direction axis
        # - determine gaps
        gaps = []
        macros = sorted(macros, key=lambda c: c[0])

        if direction == 'h':
            region_start = region_min_x
            region_end = region_max_x
        else:
            region_start = region_min_y
            region_end = region_max_y

        if region_start < macros[0][0]:
            gaps.append((region_start, macros[0][0]))

        for i in range(len(macros) - 1):
            gaps.append((macros[i][1], macros[i+1][0]))

        if region_end > macros[-1][1]:
            gaps.append((macros[-1][i], region_end))

        # Iterate over gaps and place filler cells
        for start, end in gaps:
            cell_idx = 0
            while start != end:
                cell, width = self.io_fill_cells[cell_idx]
                if width > end - start:
                    cell_idx += 1
                    if cell_idx >= len(self.io_fill_cells):
                        raise ValueError('Unable to fill gap with available cells!')
                    continue

                name = f'_sc_io_fill_cell_{self.fill_cell_id}'
                self.fill_cell_id += 1
                if direction == 'h':
                    self.place_macro(name, cell, (start, region_min_y), orientation, units='absolute')
                else:
                    self.place_macro(name, cell, (region_min_x, start), orientation, units='absolute')
                start += width

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

# smooshed padring
def example_padring1(chip):
    fp = Floorplan(chip)
    fp.create_die_area(720, 720, units='absolute')

    fp.place_macros([(f'gpio{i}', 'gpio') for i in range(5)], (150, 0), 'N', 'H')
    fp.place_macros([(f'gpio{i+5}', 'gpio') for i in range(5)], (0, 150), 'E', 'V')
    fp.place_macros([(f'gpio{i+10}', 'gpio') for i in range(5)], (150, 720 - 150), 'S', 'H')
    fp.place_macros([(f'gpio{i+15}', 'gpio') for i in range(5)], (720 - 150, 150), 'W', 'V')

    fp.place_macros([('corner_sw', 'corner')], (0, 0), 'N', 'H')
    fp.place_macros([('corner_nw', 'corner')], (0, 720-150), 'E', 'H')
    fp.place_macros([('corner_ne', 'corner')], (720-150, 720-150), 'S', 'V')
    fp.place_macros([('corner_se', 'corner')], (720-150, 0), 'FN', 'V')

    return fp

# spaced padring
def example_padring2(chip):
    fp = Floorplan(chip)
    fp.create_die_area(1200, 1200, units='absolute')

    fp.place_macros_spaced([(f'gpio{i}', 'gpio') for i in range(5)], (150, 0), 'N', 'H', 1200 - 300)
    fp.place_macros_spaced([(f'gpio{i+5}', 'gpio') for i in range(5)], (0, 150), 'E', 'V', 1200 - 300)
    fp.place_macros_spaced([(f'gpio{i+10}', 'gpio') for i in range(5)], (150, 1200 - 150), 'S', 'H', 1200-300)
    fp.place_macros_spaced([(f'gpio{i+15}', 'gpio') for i in range(5)], (1200 - 150, 150), 'W', 'V', 1200-300)

    fp.place_macros([('corner_sw', 'corner')], (0, 0), 'N', 'H')
    fp.place_macros([('corner_nw', 'corner')], (0, 1200-150), 'E', 'H')
    fp.place_macros([('corner_ne', 'corner')], (1200-150, 1200-150), 'S', 'V')
    fp.place_macros([('corner_se', 'corner')], (1200-150, 0), 'FN', 'V')

    return fp

# spaced padring w/ fill
def example_padring3(chip):
    fp = Floorplan(chip)
    fp.create_die_area(1200, 1200, units='absolute')

    fp.place_macros_spaced([(f'gpio{i}', 'gpio') for i in range(5)], (150, 0), 'N', 'H', 1200 - 300)
    fp.place_macros_spaced([(f'gpio{i+5}', 'gpio') for i in range(5)], (0, 150), 'E', 'V', 1200 - 300)
    fp.place_macros_spaced([(f'gpio{i+10}', 'gpio') for i in range(5)], (150, 1200 - 150), 'S', 'H', 1200-300)
    fp.place_macros_spaced([(f'gpio{i+15}', 'gpio') for i in range(5)], (1200 - 150, 150), 'W', 'V', 1200-300)

    fp.place_macros([('corner_sw', 'corner')], (0, 0), 'N', 'H')
    fp.place_macros([('corner_nw', 'corner')], (0, 1200-150), 'E', 'H')
    fp.place_macros([('corner_ne', 'corner')], (1200-150, 1200-150), 'S', 'V')
    fp.place_macros([('corner_se', 'corner')], (1200-150, 0), 'FN', 'V')

    fp.place_macros([('ram1', 'sram_32x2048_1rw'), ('ram2','sram_32x2048_1rw' )], (500, 600), 'N', 'H', spacing=50)

    fp.fill_io_region([(0, 0), (1200, 150)])
    fp.fill_io_region([(0, 0), (150, 1200)])
    fp.fill_io_region([(1200-150, 0), (1200, 1200)])
    fp.fill_io_region([(0, 1200-150), (1200, 1200)])

    return fp

if __name__ == '__main__':
    # Test: create floorplan with `n` equally spaced `width` x `depth` pins along
    # each side

    from siliconcompiler.core import Chip

    c = Chip()
    c.set('design', 'test')
    c.target('freepdk45')

    # set up YosysHQ/padring IO cell library
    libname = 'NangateOpenCellLibrary'
    c.set('iocell', libname, 'lef', 'siliconcompiler/iocells.lef')
    c.set('iocell', libname, 'cells', 'gpio', 'IOPAD')
    c.set('iocell', libname, 'cells', 'vdd', 'PWRPAD')
    c.set('iocell', libname, 'cells', 'vss', 'PWRPAD')
    c.set('iocell', libname, 'cells', 'vddio', 'PWRPAD')
    c.set('iocell', libname, 'cells', 'vssio', 'PWRPAD')
    c.set('iocell', libname, 'cells', 'corner', 'CORNER')
    c.set('iocell', libname, 'cells', 'fill',
        ['FILLER01', 'FILLER02', 'FILLER05', 'FILLER10', 'FILLER25', 'FILLER50'])
        
    macro = 'sram_32x2048_1rw'
    c.add('asic', 'macrolib', macro)
    c.set('macro', macro, 'lef', f'{macro}.lef')
    c.set('macro', macro, 'width', '190.76')
    c.set('macro', macro, 'height', '313.6')

    fp = example_padring1(c)
    fp.write_def('padring1.def')
    fp = example_padring2(c)
    fp.write_def('padring2.def')
    fp = example_padring3(c)
    fp.write_def('padring3.def')
