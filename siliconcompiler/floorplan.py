# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.

import logging
import math
import jinja2
from collections import namedtuple

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

MacroInfo = namedtuple("MacroInfo", "tech_name width height")

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

        # Used to generate unique instance names for I/O fill cells
        self.fill_cell_id = 0

        ## Extract technology-specific info ##

        # extract std cell info based on libname
        self.libname = self.chip.get('asic', 'targetlib')[-1]
        self.std_cell_name = self.chip.get('stdcell', self.libname, 'site')[-1]
        self.std_cell_width = float(self.chip.get('stdcell', self.libname, 'width')[-1])
        self.std_cell_height = float(self.chip.get('stdcell', self.libname, 'height')[-1])

        # Extract data from LEFs
        lef_parser = Lef()
        stackup = chip.get('asic', 'stackup')[-1]
        libtype = chip.get('stdcell', self.libname, 'libtype')[-1]

        tech_lef = schema_path(chip.get('pdk','aprtech', stackup, libtype, 'lef')[-1])
        with open(tech_lef, 'r') as f:
            tech_lef_data = lef_parser.parse(f.read())

        # List of cells the user is able to place
        self.available_cells = {}

        for macrolib in self.chip.get('asic', 'macrolib'):
            lef_path = schema_path(self.chip.get('macro', macrolib, 'lef')[-1])
            with open(lef_path, 'r') as f:
                lef_data = lef_parser.lib_parse(f.read())
        
            for name in self.chip.cfg['macro'][macrolib]['cells']:
                if name == 'default': continue
                tech_name = self.chip.get('macro', macrolib, 'cells', name)[-1]
                if tech_name in lef_data['macros']:
                    width, height = lef_data['macros'][tech_name]['size']
                else: 
                    raise KeyError(f'Implementation {tech_name} for macro {name}'
                        f'not found in library {lef_path}')

                self.available_cells[name] = MacroInfo(tech_name, width, height)

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
            'cell': self.available_cells[macro_name].tech_name,
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
            width = cell.width
            height = cell.height

            self.place_macro(instance_name, cell_name, (pos_x, pos_y), orientation, units='absolute')
            
            if direction.lower() == 'h':
                pos_x += spacing + (width if is_ns_ori else height)
            else:
                pos_y += spacing + (width if is_ew_ori else height)

    def place_macros_spaced(self, macros, start_pos, orientation, direction, distance):
        ''' Places macros on floorplan with even space.

        Args:
            macros (list of (str, str)): List of macros to place as tuples of
                (instance name, type).
            start_pos (tuple): coordinates of first macro placed.
            orientation (str): orientation of each macro.
            direction (str): which direction to repeat macro. Must be 'h' for
                horizontal or 'v' for vertical.
            distance (float): distance from start_pos to space macros within.
        '''
        filled_space = 0
        for _, cell_name in macros:
            width = self.available_cells[cell_name].width
            filled_space += width

        # TODO: raise error if filled_space < distance
        spacing = (distance - filled_space) / (len(macros) + 1)

        x, y = start_pos
        if direction.lower() == 'h':
            x += spacing
        else:
            y += spacing

        self.place_macros(macros, (x, y), orientation, direction, spacing)

    def fill_io_region(self, region, fill_cells, orientation):
        ''' Fill empty space in region with I/O filler cells

        Args:
            region (list of tuple of int): bottom-left and top-right corner of
                region to fill.

        Raises:
            ValueError: Region contains macros such that it is unfillable.
        '''
 
        # TODO: validate orientation

        region_min_x, region_min_y = region[0]
        region_max_x, region_max_y = region[1]

        # TODO: should direction be passed in explicitly?
        if orientation[-1].lower() in ('e', 'w'):
            direction = 'v'
            region_height = region_max_x - region_min_x
        else:
            direction = 'h'
            region_height = region_max_y - region_min_y

        # Gather macros in region. Macros in region must be aligned with the
        # direction of the region, and no macros may be partially contained
        # along the direction axis.
        macros = []
        for macro in self.macros:
            width = macro['info'].width
            height = macro['info'].height
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

        # Iterate along region direction and record gaps between macros.
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
        # TODO: this is only guaranteed to work if we have a width 1 filler
        # cell. Is that a valid assumption/should we use a more sophisticated
        # algorithm?
        
        # Gather I/O fill cells and sort by wider to narrower
        io_fill_cells = []
        for cell in fill_cells:
            if not cell in self.available_cells:
                raise ValueError(f'Provided fill cell {cell} is not included in'
                    f'list of available macros')

            cell_info = self.available_cells[cell]

            if cell_info.height != region_height:
                raise ValueError(f'Provided fill cell {cell} does not have '
                    f'appropriate height to fill region')

            io_fill_cells.append((cell, self.available_cells[cell]))

        io_fill_cells = sorted(io_fill_cells, key=lambda c: c[1].width, reverse=True)

        for start, end in gaps:
            cell_idx = 0
            while start != end:
                cell, cell_info = io_fill_cells[cell_idx]
                width = cell_info.width
                if width > end - start:
                    cell_idx += 1
                    if cell_idx >= len(io_fill_cells):
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

    fp.place_macros([('ram1', 'ram'), ('ram2', 'ram')], (500, 600), 'N', 'H', spacing=50)

    io_fill_cells = ['fill1', 'fill2', 'fill5', 'fill10', 'fill25', 'fill50']
    fp.fill_io_region([(0, 0), (1200, 150)], io_fill_cells, 'N')
    fp.fill_io_region([(0, 0), (150, 1200)], io_fill_cells, 'W')
    fp.fill_io_region([(1200-150, 0), (1200, 1200)], io_fill_cells, 'E')
    fp.fill_io_region([(0, 1200-150), (1200, 1200)], io_fill_cells, 'S')

    return fp

if __name__ == '__main__':
    # Test: create floorplan with `n` equally spaced `width` x `depth` pins along
    # each side

    from siliconcompiler.core import Chip

    c = Chip()
    c.set('design', 'test')
    c.target('freepdk45')

    macro = 'io'
    c.add('asic', 'macrolib', macro)
    c.set('macro', macro, 'lef', 'siliconcompiler/iocells.lef')
    c.set('macro', macro, 'cells', 'gpio', 'IOPAD')
    c.set('macro', macro, 'cells', 'pwr', 'PWRPAD')
    c.set('macro', macro, 'cells', 'corner', 'CORNER')
    c.set('macro', macro, 'cells', 'fill1', 'FILLER01')
    c.set('macro', macro, 'cells', 'fill2', 'FILLER02')
    c.set('macro', macro, 'cells', 'fill5', 'FILLER05')
    c.set('macro', macro, 'cells', 'fill10', 'FILLER10')
    c.set('macro', macro, 'cells', 'fill25', 'FILLER25')
    c.set('macro', macro, 'cells', 'fill50', 'FILLER50')
        
    macro = 'sram_32x2048_1rw'
    c.add('asic', 'macrolib', macro)
    c.set('macro', macro, 'lef', f'{macro}.lef')
    c.set('macro', macro, 'cells', 'ram', 'sram_32x2048_1rw')
    c.set('macro', macro, 'width', '190.76')
    c.set('macro', macro, 'height', '313.6')

    fp = example_padring1(c)
    fp.write_def('padring1.def')
    fp = example_padring2(c)
    fp.write_def('padring2.def')
    fp = example_padring3(c)
    fp.write_def('padring3.def')
