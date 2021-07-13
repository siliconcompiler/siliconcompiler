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

_MacroInfo = namedtuple("_MacroInfo", "tech_name width height")

def snap(val, grid):
    '''Helper function for snapping `val` to nearest multiple of `grid`.'''
    return grid * round(val/grid)

class Floorplan:
    '''Floorplan layout class.

    This is the main object used to interact with the Floorplan API. In the
    context of a full SiliconCompiler flow, a Floorplan instance pre-populated
    with the current chip configuration is passed to the user, who will then
    call the member functions of this class to define objects and their location
    within the floorplan.

    In order to define the floorplan geometry in a technology-agnostic way, this
    object exposes several attributes that allow the user to access
    technology-specific dimensions, such as standard cell width and height.
    These attributes can be used as scaling factors to determine the locations
    and sizes of objects on the floorplan.

    Args:
        chip (Chip): Object storing the chip config. The Floorplan API expects
            the chip's configuration to be populated with information from a
            tech library.
        grid (float): Minimum manufacturing grid that all positions and
            dimensions are automatically snapped to. If `None`, all received
            values are kept as-is.
        db_units (int): Scaling factor to go from microns to DEF DB units.

    Attributes:
        available_cells (dict): A dictionary mapping macro names to information
            about each macro. The values stored in this dictionary have three
            keys: `tech_name`, the technology-specific name corresponding to the
            macro; `width`, the width of the macro in microns; and `height`, the
            height of the macro in microns.

            In order to make macro libraries usable by the Floorplan API, a user
            must specify them in the chip configuration.

            To point SC to a certain macro library's LEF file:

                .. code-block:: python

                    chip.add('asic', 'macrolib', libname)
                    chip.set('macro', libname, 'lef', lef_path)

            In order to make the macros in a library accessible from the
            Floorplan API, each macro must be provided a tech-agnostic name
            (`macro_name`), which maps to a tech-specific name (the name of the
            macro in the associated LEF file, `tech_name`):

                .. code-block:: python

                    chip.set('macro', libname, 'cells', macro_name, tech_name)

            All Floorplan API calls related to macros must use the tech-agnostic
            macro name.
        die_area (tuple): A tuple of two floats `(width, height)` storing the
            size of the die area in microns.
        layers (dict): A dictionary mapping SiliconCompiler layer names to
            technology-specific info about the layers. The values in this
            dictionary are dictionaries themselves, containing the keys `name`,
            `width`, `xpitch`, `ypitch`, `xoffset`, and `yoffset`.
        std_cell_width (float): Width of standard cells in microns.
        std_cell_height (float): Height of standard cells in microns.
    '''

    def __init__(self, chip, grid=0.005, db_units=2000):
        self.chip = chip
        self.grid = grid
        self.db_units = db_units

        self.design = chip.get('design')[-1]
        self.die_area = None
        self.core_area = None
        self.pins = []
        self.macros = []
        self.rows = []
        self.tracks = []
        self.nets = {}

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

                self.available_cells[name] = _MacroInfo(tech_name, width, height)

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
                        generate_tracks=True):
        '''Initializes die.

        Initializes the area of the die and generates placement rows and routing
        tracks. This function must be called before calling `place_pins`. The
        provided die and core dimensions will overwrite the die/core size
        already present in the chip config.

        Args:
            width (float): Width of die in microns.
            height (float): Height of die in microns.
            core_area (tuple of float): The core cell area of the physical
                design. This is provided as a tuple (x0 y0 x1 y1), where (x0,
                y0), specifes the lower left corner of the block and (x1, y1)
                specifies the upper right corner. If `None`, core_area is set to
                be equivalent to the die area. Dimensions are specified in
                microns.
            generate_rows (bool): Automatically generate rows to fill entire
                core area.
            generate_tracks (bool): Automatically generate tracks to fill entire
                core area.
        '''
        # store die_area as 2-tuple since bottom left corner is always 0,0
        width = self.snap_to_grid(width)
        height = self.snap_to_grid(height)

        self.die_area = (width, height)
        if core_area == None:
            self.core_area = (0, 0, width, height)
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

    def place_pins(self, pins, offset, pitch, side, width, depth, layer,
                   pin_dir='inout', net_name=None, use='signal', fixed=True):
        '''Places pins along edge of floorplan.

        Args:
            pins (list of str): List of pin names to place.
            offset (int): How far to place first pin from edge, in microns.
            pitch (int): Spacing between pins in microns.
            side (str): Which side of the block to place the pins along. Options
                are 'n', 's', 'e', or 'w' (case insensitive).
            width (float): Width of pin.
            depth (float): Depth of pin.
            layer (str): Which metal layer pin is placed on.
            pin_dir (str): I/O direction of pins (must be valid LEF/DEF
                direction).
            net_name (str): Name of net that each pin is connected to. If
                `None`, the net name of each pin will correspond to the pin
                name.
            use (str): Usage of pin (must be valid LEF/DEF use).
            fixed (bool): Whether pin status is 'FIXED' or 'PLACED'.
        '''
        logging.debug('Placing pins: %s', ' '.join(pins))

        if pin_dir.lower() not in ('input', 'output', 'inout', 'feedthru'):
            raise ValueError('Invalid pin direction')
        if use.lower() not in ('signal', 'power', 'ground', 'clock', 'tieoff',
                               'analog', 'scan', 'reset'):
            raise ValueError('Invalid use')

        if self.die_area is None:
            raise ValueError('Die area must be initialized with create_die_area!')


        width = self.snap_to_grid(width)
        depth = self.snap_to_grid(depth)

        block_w, block_h = self.die_area

        # TODO: should shape be snapped to grid?
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
            pos = self.snap_to_grid(x), self.snap_to_grid(y)

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
                'direction': pin_dir,
                'use': use,
                'port': port
            }
            self.pins.append(pin)

            x += xincr
            y += yincr

    def place_macros(self, macros, pos, spacing, direction, orientation,
                    halo=None, fixed=True):
        '''Places macros on floorplan.

        Args:
            macros (list of (str, str)): List of macros to place as tuples of
                (instance name, macro name).
            pos (tuple): x, y coordinate where to place first instance, in
                microns.
            spacing (int): Distance between this macro and previous, in microns.
            direction (str): Direction to place macros ('h' for east-west, 'v'
                for north-south).
            orientation (str): Orientation of macros (must be valid LEF/DEF
                orientation).
            halo (tuple of int): Halo around macro as tuple (left bottom right
                top), in microns.
            fixed (bool): Whether or not macro placement is fixed or placed.
        '''

        self._validate_orientation(orientation)
        if direction.lower() not in ('h', 'v'):
            raise ValueError('Invalid direction')

        x, y = pos
        ns_ori = orientation[-1].lower() in ('n', 's')

        for instance_name, cell_name in macros:
            cell = self.available_cells[cell_name]
            width = cell.width
            height = cell.height

            macro = {
                'name': instance_name,
                'cell': self.available_cells[cell_name].tech_name,
                'info': self.available_cells[cell_name],
                'x': self.snap_to_grid(x),
                'y': self.snap_to_grid(y),
                'status': 'fixed' if fixed else 'placed',
                'orientation': orientation.upper(),
                'halo': halo,
            }
            self.macros.append(macro)

            if direction.lower() == 'h':
                x += spacing + (width if ns_ori else height)
            else:
                y += spacing + (height if ns_ori else width)

    def place_wires(self, nets, pos, pitch, direction, layer, width, length, shape):
        '''Place wires on floorplan.

        Args:
            nets (list of str): List of net names of wires to place.
            pos (tuple): x, y coordinate where to place first instance, in
                microns.
            pitch (int): Distance between this wire and previous, in microns.
            direction (str): Direction to place wires along ('h' for east-west,
                'v' for north-south). Note that the wires themselves will run in
                the opposite direction.
            layer (str): Which metal layer wire is placed on.
            width (float): Width of wire in microns.
            length (float): Length of wire in microns.
            shape (str): Shape of wire as LEF/DEF shape.
        '''

        if shape.lower() not in ('ring', 'padring', 'blockring', 'stripe',
            'followpin', 'iowire', 'corewire', 'blockwire', 'blockagewire',
            'fillwire', 'fillwireopc', 'drcfill'):
            raise ValueError('Invalid shape')

        for net_name in nets:
            x, y = pos
            if direction.lower() == 'h':
                end = x, y + length
            elif direction.lower() == 'v':
                end = x + length, y
            else:
                raise ValueError(f'Invalid direction {direction}')

            wire = {
                'layer': self.layers[layer]['name'],
                'width': width,
                'shape': shape,
                'start': pos,
                'end': end
            }

            if net_name in self.nets:
                self.nets[net_name]['wires'].append(wire)
            else:
                raise ValueError(f'Net {net_name} not found. Please initialize '
                    f'it by calling init_net()')

            if direction.lower() == 'h':
                pos = x + pitch, y
            elif direction.lower() == 'v':
                pos = x, y + pitch

    def generate_rows(self, site_name=None, flip_first_row=False, area=None):
        '''Auto-generates placement rows based on floorplan parameters and tech
        library.

        Args:
            site_name (str): Name of placement site to specify in rows. If
                `None`, uses default standard cell site.
            flip_first_row (bool): Determines orientation of row placement
                sites. If `False`, alternates starting at "FS", if `True`,
                alternates starting at "N".
            area (tuple of float): Area to fill with rows as tuple of four
                floats.  If `None`, fill entire core area. Specified as microns.
        '''
        logging.debug("Placing rows")

        # clear existing rows, since we'll generate new ones from scratch using
        # floorplan parameters
        self.rows.clear()

        if site_name is None:
            site_name = self.std_cell_name

        if area is None:
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
                'x': self.snap_to_grid(start_x),
                'y': self.snap_to_grid(start_y),
                'orientation': orientation,
                'numx': num_x,
                'numy': 1,
                'stepx' : self.snap_to_grid(self.std_cell_width),
                'stepy' : 0
            }
            self.rows.append(row)

            start_y += self.std_cell_height

    def generate_tracks(self, area=None):
        '''Auto-generates routing tracks based on floorplan parameters and tech
        library.

        Args:
            area (tuple of float): Area to fill with tracks as tuple of four
                floats.  If `None`, fill entire die area. Specified in microns.
        '''
        logging.debug("Placing tracks")

        # clear existing rows, since we'll generate new ones from scratch using
        # floorplan parameters
        self.tracks.clear()

        if area is None:
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
                'start': self.snap_to_grid(offset_x),
                'step': self.snap_to_grid(pitch_x),
                'total': num_tracks_x
            }
            track_y = {
                'name': f'{layer_name}_Y',
                'layer': layer_name,
                'direction': 'y',
                'start': self.snap_to_grid(offset_y),
                'step': self.snap_to_grid(pitch_y),
                'total': num_tracks_y
            }

            self.tracks.append(track_x)
            self.tracks.append(track_y)

    def place_blockage(self, layers=None):
        '''Places full-area blockages on the specified layers.

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

    def fill_io_region(self, region, fill_cells, orientation):
        '''Fill empty space in region with I/O filler cells.

        Args:
            region (list of tuple of float): bottom-left and top-right corner of
                region to fill.
            fill_cells (list of str): List of names of I/O filler cells to use.
            orientation (str): The orientation the filler cells are placed in
                (must be valid LEF/DEF orientation).

        Raises:
            ValueError: Region contains macros such that it is unfillable.
        '''

        self._validate_orientation(orientation)

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
                    self.place_macros([(name, cell)], (start, region_min_y), 0, 'h', orientation)
                else:
                    self.place_macros([(name, cell)], (region_min_x, start), 0, 'h', orientation)
                start += width

    def configure_net(self, net, pin_name, use):
        '''Configure net.

        Must be called before placing a wire for a net. Calls after the first
        will overwrite configuration values, but leave wires placed.

        Args:
            net (str): Name of net.
            pin_name (str): Name of pins in macro to associate with this net.
            use (str): Use of net. Must be valid LEF/DEF use.
        '''

        if use.lower() not in ('analog', 'clock', 'ground', 'power', 'reset', 'scan', 'signal', 'tieoff'):
            raise ValueError('Invalid use')

        if net in self.nets:
            self.nets[net]['use'] = use
            self.nets[net]['pin_name'] = pin_name
        else:
            self.nets[net] = {
                'use': use,
                'pin_name': pin_name,
                'wires': []
            }

    def snap_to_grid(self, val):
        if self.grid is None:
            return val
        return snap(val, self.grid)

    def snap_to_x_track(self, x, layer):
        '''Helper function to snap a value `x` to the x coordinate of the
        nearest vertical routing track on `layer`.
        '''
        offset = self.layers[layer]['xoffset']
        pitch = self.layers[layer]['xpitch']
        return round((x - offset) / pitch) * pitch + offset

    def snap_to_y_track(self, y, layer):
        '''Helper function to snap a value `y` to the y coordinate of the
        nearest horizontal routing track on `layer`.
        '''
        offset = self.layers[layer]['yoffset']
        pitch = self.layers[layer]['ypitch']
        return round((y - offset) / pitch) * pitch + offset

    def _validate_orientation(self, orientation):
        if orientation.lower() not in ('n', 's', 'w', 'e', 'fn', 'fs', 'fw', 'fe'):
            raise ValueError('Invalid orientation')
