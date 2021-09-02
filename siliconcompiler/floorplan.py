# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.

import logging
import math
import jinja2
from collections import namedtuple

from siliconcompiler import leflib
from siliconcompiler.schema_utils import schema_path

# Set up Jinja
env = jinja2.Environment(loader=jinja2.PackageLoader('siliconcompiler'),
                         trim_blocks=True, lstrip_blocks=True)

# Jinja filter for rendering tuples in DEF style, e.g. (0, 0) becomes "( 0 0 )"
def render_tuple(vals):
    vals_str = ' '.join([str(val) for val in vals])
    return f"( {vals_str} )"
env.filters['render_tuple'] = render_tuple

_MacroInfo = namedtuple("_MacroInfo", "width height")

# TODO: make sure all required schema entries are checked (and document!)

def _layer_i(layer):
    return int(layer.lstrip('m'))

# Line intersection helper functions for via insertion routine
def _lines_intersect(p1, p2, q1, q2):
    ''' Determine if line segment between p1 and p2 intersects with line segment
    between q1 and q2.

    Algorithm based on
    https://www.geeksforgeeks.org/check-if-two-given-line-segments-intersect/.

    TODO: distinguish between intersecting and coincident lines
    '''

    o1 = _orientation(q1, q2, p1)
    o2 = _orientation(q1, q2, p2)
    o3 = _orientation(p1, p2, q1)
    o4 = _orientation(p1, p2, q2)

    # if first pair and second pair of orientations different, then we have intersection
    if o1 != o2 and o3 != o4:
        return True

    # Alternatively, if we have colinearity and the relevant point is on the
    # line segment, we have an intersection.
    if o1 == 0 and _on_segment(q1, q2, p1):
        return True
    if o2 == 0 and _on_segment(q1, q2, p2):
        return True
    if o3 == 0 and _on_segment(p1, p2, q1):
        return True
    if o4 == 0 and _on_segment(p1, p2, q2):
        return True

    return False

def _orientation(p1, p2, p3):
    ''' Returns the orientation of ordered triplet p1, p2, p3. Can be clockwise
    (1), counter-clockwise (-1) or colinear (0).

    https://www.geeksforgeeks.org/orientation-3-ordered-points/
    '''
    o  = ((p3[0] - p2[0]) * (p2[1] - p1[1]) -
          (p3[1] - p2[1]) * (p2[0] - p1[0]))

    if o > 0:
        return 1
    elif o < 0:
        return -1
    else:
        return 0

def _on_segment(p1, p2, q):
    ''' Return if point q on line segment (p1, p2). Points p1, p2, and q must be
    colinear.
    '''
    return (((p1[0] <= q[0] and q[0] <= p2[0]) or (p2[0] <= q[0] and q[0] <= p1[0])) and
            ((p1[1] <= q[1] and q[1] <= p2[1]) or (p2[1] <= q[1] and q[1] <= p1[1])))

def _get_intersection(p1, p2, q1, q2):
    ''' Get the intersection point of two intersecting lines (p1, p2) and (q1, q2)

    I have no idea how this algorithm works, I took it from one of my classes.
    '''
    print(f'line 1: {p1}; {p2}')
    print(f'line 2: {q1}; {q2}')
    u = (((q2[0] - q1[0]) * (p1[1] - q1[1]) - (q2[1] - q1[1]) * (p1[0] - q1[0])) /
         ((q2[1] - q1[1]) * (p2[0] - p1[0]) - (q2[0] - q1[0]) * (p2[1] - p1[1])))

    return (p1[0] + u * (p2[0] - p1[0]),
            p1[1] + u * (p2[1] - p1[1]))

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

    Attributes:
        available_cells (dict): A dictionary mapping macro names to information
            about each macro. The values stored in this dictionary have two
            keys: `width`, the width of the macro in microns and `height`, the
            height of the macro in microns.

            In order to make macro libraries usable by the Floorplan API, a user
            must specify them in the chip configuration.

            To point SC to a certain macro library's LEF file:

                .. code-block:: python

                    chip.add('asic', 'macrolib', libname)
                    chip.set('library', libname, 'lef', lef_path)

        die_area (tuple): A tuple of two floats `(width, height)` storing the
            size of the die area in microns.
        layers (dict): A dictionary mapping SiliconCompiler layer names to
            technology-specific info about the layers. The values in this
            dictionary are dictionaries themselves, containing the keys `name`,
            `width`, `xpitch`, `ypitch`, `xoffset`, and `yoffset`.
        std_cell_width (float): Width of standard cells in microns.
        std_cell_height (float): Height of standard cells in microns.
    '''

    def __init__(self, chip, viarules={}):
        self.chip = chip

        self.design = chip.get('design')
        self.die_area = None
        self.core_area = None
        self.pins = []
        self.macros = []
        self.rows = []
        self.tracks = []
        self.nets = {}
        # VIARULE GENERATEs extracted from tech LEF
        self.viarules = viarules
        '''
        {
            (<bottom>, <top>): {
                'name': <name>,
                'bottom': {
                    'enclosure': (<overhang1>, <overhang2>),
                },
                'cut': {
                    'size': (<width>, <height>),
                    'spacing': (<x>, <y>)
                }
                'top': {
                    'enclosure': (<overhang1>, <overhang2>)
                }
            }
        }
        '''
        # Map of via names that were autogenerated by SC
        self.viastacks = {
            # (<bottom>, <bottomdir>, <top>, <topdir>, <width>, <height>): [<vianame1>, <vianame2>, ... ],
        }
        # Stuff that gets placed into DEF
        self.vias = []

        self.blockages = []
        self.obstructions = []

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
        self.via_i = 0

        ## Extract technology-specific info ##

        # extract std cell info based on libname
        self.libname = self.chip.get('asic', 'targetlib')[0]
        self.std_cell_name = self.chip.get('library', self.libname, 'site')
        self.std_cell_width = self.chip.get('library', self.libname, 'width')
        self.std_cell_height = self.chip.get('library', self.libname, 'height')

        # Extract data from LEFs
        stackup = chip.get('asic', 'stackup')
        libtype = chip.get('library', self.libname, 'arch')

        # List of cells the user is able to place
        self.available_cells = {}

        for macrolib in self.chip.get('asic', 'macrolib'):
            lef_path = schema_path(self.chip.get('library', macrolib, 'lef')[0])
            lef_data = leflib.parse(lef_path)

            if 'macros' not in lef_data:
                logging.warn(f'LEF {lef_path} added to library {macrolib} '
                    'contains no macros. Are you sure this is the correct file?')
                continue

            for name in lef_data['macros'].keys():
                if 'size' in lef_data['macros'][name]:
                    size = lef_data['macros'][name]['size']
                    width = size['width']
                    height = size['height']
                    self.available_cells[name] = _MacroInfo(width, height)
                else:
                    logging.warn(f'Macro {name} missing size in LEF, not adding '
                        'to available cells.')

        tech_lef = schema_path(chip.get('pdk', 'aprtech', stackup, libtype, 'lef')[0])
        tech_lef_data = leflib.parse(tech_lef)

        if 'units' in tech_lef_data and 'database' in tech_lef_data['units']:
            self.db_units = int(tech_lef_data['units']['database'])
        else:
            raise ValueError('No DB units specified in tech LEF.')

        if 'manufacturinggrid' in tech_lef_data:
            self.grid = tech_lef_data['manufacturinggrid']
        else:
            # If unspecified in the LEF, tech_lef_data.grid will be None and
            # snap_to_grid will just pass values through.
            self.grid = None

        # extract layers based on stackup
        stackup = self.chip.get('asic', 'stackup')
        self.layers = {}
        for name in self.chip.getkeys('pdk', 'grid', stackup):
            pdk_name = self.chip.get('pdk', 'grid', stackup, name, 'name')
            xpitch = self.chip.get('pdk', 'grid', stackup, name, 'xpitch')
            ypitch = self.chip.get('pdk', 'grid', stackup, name, 'ypitch')
            xoffset = self.chip.get('pdk', 'grid', stackup, name, 'xoffset')
            yoffset = self.chip.get('pdk', 'grid', stackup, name, 'yoffset')

            if ('layers' not in tech_lef_data) or (pdk_name not in tech_lef_data['layers']):
                raise ValueError(f'No layer named {pdk_name} in tech LEF!')
            layer = tech_lef_data['layers'][pdk_name]

            if 'width' not in layer:
                raise ValueError(f'No width for layer {pdk_name} in tech LEF!')
            if 'direction' not in layer:
                raise ValueError(f'No direction for layer {pdk_name} in tech LEF!')
            width = layer['width']
            direction = layer['direction']

            self.layers[name] = {
                'name': pdk_name,
                'width': width,
                'direction': direction,
                'xpitch': xpitch,
                'ypitch': ypitch,
                'xoffset': xoffset,
                'yoffset': yoffset
            }

    def create_die_area(self, die_area, core_area=None, generate_rows=True,
                        generate_tracks=True):
        '''Initializes die.

        Initializes the area of the die and generates placement rows and routing
        tracks. The provided die and core dimensions will overwrite the die/core
        size already present in the chip config.

        Args:
            die_area (list of (float, float)): List of points that form the die
                area. Currently only allowed to provide two points, specifying
                the two bounding corners of a rectangular die. Dimensions are
                specified in microns.
            core_area (list of (float, float)): List of points that form the
                core area of the physical design. If `None`, core_area is set to
                be equivalent to the die area. Currently only allowed to provide
                two points, specifying the two bounding corners of a rectangular
                area.  Dimensions are specified in microns.
            generate_rows (bool): Automatically generate rows to fill entire
                core area.
            generate_tracks (bool): Automatically generate tracks to fill entire
                core area.
        '''
        if len(die_area) != 2:
            raise ValueError('Non-rectangular floorplans not yet supported: '
                             'die_area must be list of two tuples.')
        if die_area[0] != (0, 0):
            # TODO: not sure if this would be a problem, except need to figure
            # out what a non-origin initial point would mean for the LEF output.
            raise ValueError('Non-origin initial die area point not yet supported.')

        # store die_area as 2-tuple since bottom left corner is always 0,0
        self.die_area = die_area
        if core_area == None:
            self.core_area = self.die_area
        else:
            self.core_area = core_area

        if len(self.core_area) != 2:
            raise ValueError('Non-rectangular core areas not yet supported: '
                             'core_area must be list of two tuples.')

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
                'cell': cell_name,
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
            if width > height:
                # horizontal
                if snap:
                    start = x, self.snap_to_y_track(y + height/2, layer)
                    end = x + width, self.snap_to_y_track(y + height/2, layer)
                else:
                    start = x, y + height/2
                    end = x + width, y + height/2
                wire_width = height
                direction = 'h'
            else:
                # vertical
                if snap:
                    start = self.snap_to_x_track(x + width/2, layer), y
                    end = self.snap_to_y_track(x + width/2, layer), y + height
                else:
                    start = x + width/2, y
                    end = x + width/2, y + height
                wire_width = width
                direction = 'v'

            wire = {
                'layer': self.layers[layer]['name'],
                # TODO: I think this value has to be even, should probably
                # ensure that? (I think that's in terms of DEF scale)
                'width': wire_width,
                'shape': shape,
                'start': start,
                'end': end,

                # don't need these for DEF, but helps with via insertion
                'direction': direction,
                'sclayer': layer
            }

            if net_name in self.nets:
                self.nets[net_name]['wires'].append(wire)
            else:
                raise ValueError(f'Net {net_name} not found. Please initialize '
                    f'it by calling configure_net()')

            x += xpitch
            y += ypitch

    def place_vias(self, nets, x0, y0, xpitch, ypitch, layer, rule):
        # TODO: document
        # TODO: add snap arg?

        x = x0
        y = y0
        for net_name in nets:
            via = {
                'point': (x, y),
                'layer': self.layers[layer]['name'],
                'rule': rule
            }

            if net_name in self.nets:
                self.nets[net_name]['vias'].append(via)
            else:
                raise ValueError(f'Net {net_name} not found. Please initialize '
                    f'it by calling configure_net()')

            x += xpitch
            y += ypitch

    def add_via(self, name, cutsize, layers, cutspacing, enclosure, rowcol=None, rule=None):
        # TODO: document
        # TODO: look at VIA docs in DEF to see if this makes sense/if I should
        # add anything else

        # TODO: do we want SC-agnostic via layer names? For now, just pass
        # through non metal layers
        tech_layers = []
        for layer in layers:
            if layer in self.layers:
                tech_layers.append(self.layers[layer]['name'])
            else:
                tech_layers.append(layer)

        self.viarules.append({
            'name': name,
            'rule': rule,
            'cutsize': cutsize,
            'layers': tech_layers,
            'cutspacing': cutspacing,
            'enclosure': enclosure,
            'rowcol': rowcol
        })

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

        start_x, start_y = area[0]
        core_width = area[1][0] - start_x
        core_height = area[1][1] - start_y

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
            area = self.die_area

        start_x, start_y = area[0]
        die_width, die_height = area[1]

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

    def place_blockage(self, x, y, width, height, layer=None, snap=False):
        '''Places blockage at specified location.

        Args:
            x (float): x-coordinate of blockage in microns.
            y (float): y-coordinate of blockage in microns.
            width (float): Width of blockage in microns.
            height (float): Height of blockage in microns.
            layers (str): Metal layer to block routing on. If `None`, mark as
                placement blockage.
            snap (bool): Whether or not to snap blockage position to be aligned
                with the nearest placement site.
        '''

        if snap:
            x = fp.snap(x, self.std_cell_width)
            y = fp.snap(y, self.std_cell_height)

        self.blockages.append({
            'll': (x, y),
            'ur': (x + width, y + height),
            'layer': self.layers[layer]['name'] if layer is not None else None
        })

    def place_obstruction(self, x, y, width, height, layers=None, snap=False):
        '''Places obstruction at specified location.

        The obstructions specified using this method only take effect when
        dumping the floorplan as a LEF macro.

        Args:
            x (float): x-coordinate of blockage in microns.
            y (float): y-coordinate of blockage in microns.
            width (float): Width of blockage in microns.
            height (float): Height of blockage in microns.
            layers (list): List of layers to place obstructions on. If `None`,
                block all metal layers.
            snap (bool): Whether or not to snap obstruction position to be
                aligned with the nearest placement site.
        '''

        if layers is None:
            layers = list(self.layers.keys())

        if snap:
            x = fp.snap(x, self.std_cell_width)
            y = fp.snap(y, self.std_cell_height)

        for layer in layers:
            if layer in self.layers:
                self.obstructions.append({
                    'll': (x, y),
                    'ur': (x + width, y + height),
                    'layer': self.layers[layer]['name']
                })
            else:
                raise ValueError(f'Layer {layer} not found in tech info!')

    def fill_io_region(self, region, fill_cells, orientation, direction):
        '''Fill empty space in region with I/O filler cells.

        Args:
            region (list of tuple of float): bottom-left and top-right corner of
                region to fill.
            fill_cells (list of str): List of names of I/O filler cells to use.
            orientation (str): The orientation the filler cells are placed in
                (must be valid LEF/DEF orientation).
            direction (str): The direction to place fill cells along. Must be
                'h' for horizontal or 'v' for vertical.

        Raises:
            ValueError: Region contains macros such that it is unfillable.
        '''

        self._validate_orientation(orientation)

        region_min_x, region_min_y = region[0]
        region_max_x, region_max_y = region[1]

        if direction == 'v':
            region_height = region_max_x - region_min_x
        elif direction == 'h':
            region_height = region_max_y - region_min_y
        else:
            raise ValueError("Invalid direction specified, must be 'h' or 'v'")

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

    def configure_net(self, net, pins, use):
        '''Configure net.

        Must be called before placing a wire for a net. Calls after the first
        will overwrite configuration values, but leave wires placed.

        Args:
            net (str): Name of net.
            pins (list of str): Name of pins in macro to associate with this net.
            use (str): Use of net. Must be valid LEF/DEF use.
        '''

        if use.lower() not in ('analog', 'clock', 'ground', 'power', 'reset', 'scan', 'signal', 'tieoff'):
            raise ValueError('Invalid use')

        if net in self.nets:
            self.nets[net]['use'] = use
            self.nets[net]['pins'] = pins
        else:
            self.nets[net] = {
                'use': use,
                'pins': pins,
                'wires': [],
                'vias': []
            }

    def place_ring(self):
        pass

    def _determine_num_via_cols(self, viarule, width, height, lower_dir, upper_dir, stack_bottom, stack_top):
        lower_enclosure = viarule['bottom']['enclosure']
        upper_enclosure = viarule['top']['enclosure']
        cut_w, cut_h = viarule['cut']['size']
        spacing_x, spacing_y = viarule['cut']['spacing']

        i = 1
        if lower_dir == 'h':
            via_width_lower = cut_w * i + spacing_x * (i - 1) + 2 * min(lower_enclosure)
            via_width_upper = cut_w * i + spacing_x * (i - 1) + 2 * max(upper_enclosure)
        else:
            via_width_lower = cut_w * i  + spacing_x * (i - 1) + 2 * max(lower_enclosure)
            via_width_upper = cut_w * i + spacing_x * (i - 1) + 2 * min(upper_enclosure)

        while via_width_lower < width and via_width_upper < width:
            i += 1
            if lower_dir == 'h':
                via_width_lower = cut_w * i + spacing_x * (i - 1) + 2 * min(lower_enclosure)
                via_width_upper = cut_w * i + spacing_x * (i - 1) + 2 * max(upper_enclosure)
            else:
                via_width_lower = cut_w * i + spacing_x * (i - 1) + 2 * max(lower_enclosure)
                via_width_upper = cut_w * i + spacing_x * (i - 1) + 2 * min(upper_enclosure)

        cols = max(1, i-1)

        # TODO: check constraints (how are these set?)

        return cols

    def _determine_num_via_rows(self, viarule, width, height, lower_dir, upper_dir, stack_bottom, stack_top):
        lower_enclosure = viarule['bottom']['enclosure']
        upper_enclosure = viarule['top']['enclosure']
        cut_w, cut_h = viarule['cut']['size']
        spacing_x, spacing_y = viarule['cut']['spacing']

        i = 1
        if lower_dir == 'h':
            via_height_lower = cut_h * i + spacing_y * (i - 1) + 2 * min(lower_enclosure)
            via_height_upper = cut_h * i + spacing_y * (i - 1) + 2 * max(upper_enclosure)
        else:
            via_height_lower = cut_h * i + spacing_y * (i - 1) + 2 * max(lower_enclosure)
            via_height_upper = cut_h * i + spacing_y * (i - 1) + 2 * min(upper_enclosure)

        while via_height_lower <= height and via_height_upper <= height:
            i += 1
            if lower_dir == 'h':
                via_height_lower = cut_h * i + spacing_y * (i - 1) + 2 * min(lower_enclosure)
                via_height_upper = cut_h * i + spacing_y * (i - 1) + 2 * max(upper_enclosure)
            else:
                via_height_lower = cut_h * i + spacing_y * (i - 1) + 2 * max(lower_enclosure)
                via_height_upper = cut_h * i + spacing_y * (i - 1) + 2 * min(upper_enclosure)

        rows = max(1, i-1)

        # TODO: check constraints (how are these set?)

        return rows

    def _generate_via(self, viarule, width, height, lower_dir, upper_dir, stack_bottom, stack_top):
        lower_enclosure = viarule['bottom']['enclosure']
        upper_enclosure = viarule['top']['enclosure']
        cut_w, cut_h = viarule['cut']['size']
        spacing_x, spacing_y = viarule['cut']['spacing']

        # Calculate maximum of rows and cols of cuts that can fit
        rows = self._determine_num_via_rows(viarule, width, height, lower_dir, upper_dir, stack_bottom, stack_top)
        cols = self._determine_num_via_cols(viarule, width, height, lower_dir, upper_dir, stack_bottom, stack_top)

        # Calculate enclosures based on leftover
        lower_enc_width = (width - (cut_w * cols + spacing_x * (cols - 1))) / 2
        upper_enc_width = lower_enc_width
        lower_enc_height = (height - (cut_h * rows + spacing_y * (rows - 1))) / 2
        upper_enc_height = lower_enc_height

        # Logic from OpenROAD that shrinks enclosures on in-between metal layers
        if lower_dir == 'h':
            if not stack_top:
                upper_enc_width = min(upper_enclosure)
        else:
            if not stack_bottom:
                lower_enc_width = min(lower_enclosure)
        if lower_dir == 'h':
            if not stack_bottom:
                lower_enc_height = min(lower_enclosure)
        else:
            if not stack_top:
                upper_enc_height = min(upper_enclosure)

        # Score is area of all cuts
        score = rows * cols * cut_w * cut_h
        # Stuff via info into dict
        layers = (
            self.layers[viarule['bottom']['layer']]['name'],
            viarule['cut']['layer'],
            self.layers[viarule['top']['layer']]['name']
        )

        via = {
            'rule': viarule['name'],
            'layers': layers,
            'cutsize': (cut_w, cut_h),
            'cutspacing': (spacing_x, spacing_y),
            'enclosure': (lower_enc_width, lower_enc_height, upper_enc_width, upper_enc_height),
            'rowcol': (rows, cols)
        }

        return score, via

    def _insert_via(self, net, pos, bottom_layer, top_layer, bottom_dir, top_dir, width, height):
        x, y = pos
        stack_key = (bottom_layer, bottom_dir, top_layer, top_dir, width, height)

        if stack_key not in self.viastacks:
            # Need to compute a stack
            stack = []
            bottom_i = _layer_i(bottom_layer)
            top_i = _layer_i(top_layer)
            i = bottom_i
            while i != top_i:
                min_score = float('inf')
                best_via = None
                key = (i, i+1)
                if key not in self.viarules:
                    raise ValueError(f"Unable to automatically insert vias: tech "
                        f"file doesn't specify a viarule connecting layers m{i} and m{i+1}")
                for viarule in self.viarules[key]:
                    score, via = self._generate_via(viarule, width, height, bottom_dir, top_dir, i == bottom_i, i + 1 == top_i)
                    if score < min_score:
                        best_via = via
                # TODO: error if no best_via

                # Add generated as one of our vias and to our current stack
                vianame = f'_via{self.via_i}'
                best_via['name'] = vianame
                self.via_i += 1
                self.vias.append(best_via)
                stack.append((vianame, f'm{i}'))

                i += 1

            self.viastacks[stack_key] = stack

        for vianame, layer in self.viastacks[stack_key]:
            # TODO: bottom_layer is wrong thing here we need bottom laye rof
            # this particular via
            self.place_vias([net], x, y, 0, 0, layer, vianame)

    def insert_vias(self):
        for net in self.nets:
            # TODO: is this valid? trying to sort from bottom to top
            wires = sorted(self.nets[net]['wires'], key=lambda w: w['sclayer'] )
            for i, wire_bottom in enumerate(wires):
                for wire_top in wires[i:]:
                    bottom_start = wire_bottom['start']
                    bottom_end = wire_bottom['end']
                    bottom_layer = wire_bottom['sclayer']
                    bottom_dir = wire_bottom['direction']
                    bottom_width = wire_bottom['width']
                    top_start = wire_top['start']
                    top_end = wire_top['end']
                    top_layer = wire_top['sclayer']
                    top_dir = wire_top['direction']
                    top_width = wire_top['width']

                    if bottom_layer == top_layer:
                        continue

                    do_lines_intersect = _lines_intersect(bottom_start, bottom_end, top_start, top_end)

                    # TODO: detect colinear (how does OR handle this?)
                    if bottom_dir == top_dir:
                        raise ValueError("cannot insert vias between wires in same direction")

                    if do_lines_intersect:
                        x, y = _get_intersection(bottom_start, bottom_end, top_start, top_end)

                        width = bottom_width if bottom_dir == 'v' else top_width
                        height = bottom_width if bottom_dir == 'h' else top_width
                        self._insert_via(net, (x, y), bottom_layer, top_layer, bottom_dir, top_dir, width, height)

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
