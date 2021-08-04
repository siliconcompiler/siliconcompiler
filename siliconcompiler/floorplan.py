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
                    raise KeyError(f'Implementation {tech_name} for macro {name} '
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
            self.layers[name]['direction'] = tech_lef_data['LAYER'][pdk_name]['DIRECTION'][-1]
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

    def place_pins(self, pins, x0, y0, xpitch, ypitch, width, height, layer,
                   direction='inout', net_name=None, use='signal', fixed=True,
                   snap=False):
        '''Places pins along edge of floorplan.

        Args:
            pins (list of str): List of pin names to place.
            x0 (float): x-coordinate of first instance in microns.
            y0 (float): y-coordinate of first instance in microns.
            xpitch (float): Increment along x-axis in microns.
            ypitch (float): Increment along y-axis in microns.
            width (float): Width of pin.
            height (float): Height of pin.
            layer (str): Which metal layer pin is placed on.
            direction (str): I/O direction of pins (must be valid LEF/DEF
                direction).
            net_name (str): Name of net that each pin is connected to. If
                `None`, the net name of each pin will correspond to the pin
                name.
            use (str): Usage of pin (must be valid LEF/DEF use).
            fixed (bool): Whether pin status is 'FIXED' or 'PLACED'.
            snap (bool): Whether to snap pin position to align it with the
                nearest routing track. Track direction is determined by
                preferred routing direction as specified in the tech LEF.
        '''
        logging.debug('Placing pins: %s', ' '.join(pins))

        if direction.lower() not in ('input', 'output', 'inout', 'feedthru'):
            raise ValueError('Invalid pin direction')
        if use.lower() not in ('signal', 'power', 'ground', 'clock', 'tieoff',
                               'analog', 'scan', 'reset'):
            raise ValueError('Invalid use')

        if self.die_area is None:
            raise ValueError('Die area must be initialized with create_die_area!')

        x = x0
        y = y0

        for pin_name in pins:
            # we place pins by center point internally to make sure we can
            # easily snap them so that the center is aligned with the
            # appropriate track

            pos = x + width/2, y + height/2
            if snap:
                layer_dir = self.layers[layer]['direction']
                if layer_dir == 'HORIZONTAL':
                    pos = x + width/2, self.snap_to_y_track(y + height/2, layer)
                elif layer_dir == 'VERTICAL':
                    pos = self.snap_to_x_track(x + width/2, layer), y + height/2
                else:
                    logging.warning(f'Unable to snap pin on layer with '
                        f'preferred direction {layer_dir}')

            port = {
                'layer': self.layers[layer]['name'],
                'box': [(-width/2, -height/2), (width/2, height/2)],
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

            x += xpitch
            y += ypitch

    def place_macros(self, macros, x0, y0, xpitch, ypitch, orientation,
                    halo=None, fixed=True, snap=False):
        '''Places macros on floorplan.

        Args:
            macros (list of (str, str)): List of macros to place as tuples of
                (instance name, macro name).
            x0 (float): x-coordinate of first instance in microns.
            y0 (float): y-coordinate of first instance in microns.
            xpitch (float): Increment along x-axis in microns.
            ypitch (float): Increment along y-axis in microns.
            orientation (str): Orientation of macros (must be valid LEF/DEF
                orientation).
            halo (tuple of int): Halo around macro as tuple (left bottom right
                top), in microns.
            fixed (bool): Whether or not macro placement is fixed or placed.
            snap (bool): Whether or not to snap macro position to be aligned
                with the nearest placement site.
        '''

        self._validate_orientation(orientation)

        x = x0
        y = y0

        for instance_name, cell_name in macros:
            macro = {
                'name': instance_name,
                'cell': self.available_cells[cell_name].tech_name,
                'info': self.available_cells[cell_name],
                'x': self.snap(x, self.std_cell_width) if snap else x,
                'y': self.snap(y, self.std_cell_height) if snap else y,
                'status': 'fixed' if fixed else 'placed',
                'orientation': orientation.upper(),
                'halo': halo,
            }
            self.macros.append(macro)

            x += xpitch
            y += ypitch

    def place_wires(self, nets, x0, y0, xpitch, ypitch, width, height, layer, 
                    shape, snap=False):
        '''Place wires on floorplan.

        Args:
            nets (list of str): List of net names of wires to place.
            x0 (float): x-coordinate of first instance in microns.
            y0 (float): y-coordinate of first instance in microns.
            xpitch (float): Increment along x-axis in microns.
            ypitch (float): Increment along y-axis in microns.
            width (float): Width of wire in microns.
            height (float): Height of wire in microns.
            layer (str): Which metal layer wire is placed on.
            shape (str): Shape of wire as LEF/DEF shape.
            snap (bool): Whether to snap wire position to align it with the
                nearest routing track. Track direction is determined by
                preferred routing direction as specified in the tech LEF.
        '''

        x = x0
        y = y0

        if shape.lower() not in ('ring', 'padring', 'blockring', 'stripe',
            'followpin', 'iowire', 'corewire', 'blockwire', 'blockagewire',
            'fillwire', 'fillwireopc', 'drcfill'):
            raise ValueError('Invalid shape')

        for net_name in nets:
            # we place pins by center point internally to make sure we can
            # easily snap them so that the center is aligned with the
            # appropriate track
            start = x, y + height/2
            end = x + width, y + height/2
            wire_width = height
            if snap:
                layer_dir = self.layers[layer]['direction']
                if layer_dir == 'HORIZONTAL':
                    start = x, self.snap_to_y_track(y + height/2, layer)
                    end = x + width, self.snap_to_y_track(y + height/2, layer)
                    wire_width = height
                elif layer_dir == 'VERTICAL':
                    start = self.snap_to_x_track(x + width/2, layer), y
                    end = self.snap_to_y_track(x + width/2, layer), y + height
                    wire_width = width
                else:
                    # TODO: do we have a warning log level?
                    logging.warning(f'Unable to snap wire on layer with '
                        f'preferred direction {layer_dir}')

            wire = {
                'layer': self.layers[layer]['name'],
                # TODO: I think this value has to be even, should probably
                # ensure that? (I think that's in terms of DEF scale)
                'width': wire_width,
                'shape': shape,
                'start': start,
                'end': end
            }

            if net_name in self.nets:
                self.nets[net_name]['wires'].append(wire)
            else:
                raise ValueError(f'Net {net_name} not found. Please initialize '
                    f'it by calling init_net()')

            x += xpitch
            y += ypitch

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

                left_edge_in = (x >= region_min_x)
                right_edge_in = (max_x <= region_max_x)

                if left_edge_in or right_edge_in:
                    macros.append((x, max_x, macro))
            else:
                if x >= region_max_x or max_x  <= region_min_x:
                    # outside of region horizontally
                    continue

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
            gaps.append((macros[-1][1], region_end))

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
                    self.place_macros([(name, cell)], start, region_min_y, 0, 0, orientation, snap=False)
                else:
                    self.place_macros([(name, cell)], region_min_x, start, 0, 0, orientation, snap=False)
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

    def snap(self, val, grid):
        '''Helper function for snapping `val` to nearest multiple of `grid`.'''
        return grid * round(val/grid)

    def snap_to_grid(self, val):
        if self.grid is None:
            return val
        return self.snap(val, self.grid)

    def snap_to_x_track(self, x, layer):
        '''Helper function to snap a value `x` to the x coordinate of the
        nearest vertical routing track on `layer`.
        '''
        offset = self.layers[layer]['xoffset']
        pitch = self.layers[layer]['xpitch']
        # snapping to grid cleans up floating point imprecision
        return self.snap_to_grid(round((x - offset) / pitch) * pitch + offset)

    def snap_to_y_track(self, y, layer):
        '''Helper function to snap a value `y` to the y coordinate of the
        nearest horizontal routing track on `layer`.
        '''
        offset = self.layers[layer]['yoffset']
        pitch = self.layers[layer]['ypitch']
        # snapping to grid cleans up floating point imprecision
        return self.snap_to_grid(round((y - offset) / pitch) * pitch + offset)

    def _validate_orientation(self, orientation):
        if orientation.lower() not in ('n', 's', 'w', 'e', 'fn', 'fs', 'fw', 'fe'):
            raise ValueError('Invalid orientation')
