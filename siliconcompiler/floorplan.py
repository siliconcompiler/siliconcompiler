# Copyright 2021 Silicon Compiler Authors. All Rights Reserved.

from collections import namedtuple
import logging
import math

import jinja2

from siliconcompiler import leflib

# Set up Jinja
env = jinja2.Environment(loader=jinja2.PackageLoader('siliconcompiler'),
                         trim_blocks=True, lstrip_blocks=True)

def render_tuple(vals):
    '''Jinja filter for rendering tuples in DEF style, e.g. (0, 0) becomes "( 0 0 )".'''
    vals_str = ' '.join([str(val) for val in vals])
    return f"( {vals_str} )"
env.filters['render_tuple'] = render_tuple

_MacroInfo = namedtuple("_MacroInfo", "width height")

# TODO: make sure all required schema entries are checked (and document!)

def _layer_i(layer):
    '''Helper function to go from SC layer name to layer position in stackup.'''
    try:
        return int(layer.lstrip('m'))
    except:
        raise ValueError(f'Invalid routing layer {layer}.')

def _get_rect_intersection(r1, r2):
    '''Get intersection of two rectangles r1 and r2.

    Rectangles are specified as tuples of 4 values: (xl, yl, xh, yh). If there's
    an intersection, the intersecting area is returned as a rectangle in the
    same form. If there is no intersection, the function returns None.

    r1 and r2 must be aligned to the x/y axes.

    Algorithm inspiration: https://stackoverflow.com/a/4549594.
    '''
    left1, bottom1, right1, top1 = r1
    left2, bottom2, right2, top2 = r2

    # get dimensions of possible intersection
    left = max(left1, left2)
    bottom = max(bottom1, bottom2)
    right = min(right1, right2)
    top = min(top1, top2)

    # ensure intersection is a valid rectangle
    if left < right and bottom < top:
        return (left, bottom, right, top)

    # if no intersection, we return None
    return None

def _wire_to_rect(wire):
    start = wire['start']
    end = wire['end']
    direction = wire['direction']
    width = wire['width']

    if direction == 'h':
        left = start[0]
        right = end[0]
        bottom = start[1] - width / 2
        top = bottom + width
    else:
        bottom = start[1]
        top = end[1]
        left = start[0] - width / 2
        right = left + width

    return (left, bottom, right, top)

def _get_tech_lef_data(chip, tool):
    stackup = chip.get('asic', 'stackup')
    libname = chip.get('asic', 'logiclib')[0]
    libtype = chip.get('library', libname, 'arch')

    tech_lef = chip.find_files('pdk', 'aprtech', tool, stackup, libtype, 'lef')[0]
    return leflib.parse(tech_lef)

def _get_stdcell_info(chip, tech_lef_data):
    libname = chip.get('asic', 'logiclib')[0]
    site_name = chip.getkeys('library', libname, 'site')[0]
    if 'sites' not in tech_lef_data or site_name not in tech_lef_data['sites']:
        raise ValueError('Site {site_name} not found in tech LEF.')

    site = tech_lef_data['sites'][site_name]
    if 'size' not in site:
        raise ValueError('Tech LEF does not specify size for site {site_name}.')

    width = site['size']['width']
    height = site['size']['height']

    return site_name, width, height

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
        tool (str): String specifying which tool will consume the generated
            floorplan. This tool should have an associated tech LEF configured
            in the PDK setup file. Defaults to 'openroad'.

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

        diearea (tuple): A tuple of two floats `(width, height)` storing the
            size of the die area in microns.
        layers (dict): A dictionary mapping names to technology-specific info
            about the layers. This dictionary can be accessed using either
            SC-standardized layer names or PDK-specific layer names. Note that
            this means the dictionary should not be iterated over to extract all
            layers. Instead, the function `get_layers()` can be used for this.
            The values in this dictionary are dictionaries themselves,
            containing the keys `name`, `width`, `xpitch`, `ypitch`, `xoffset`,
            and `yoffset`.
        stdcell_width (float): Width of standard cells in microns.
        stdcell_height (float): Height of standard cells in microns.
    '''

    def __init__(self, chip, tool='openroad'):
        self.chip = chip

        self.design = chip.get('design')
        self.diearea = None
        self.corearea = None
        self.pins = {}
        self.macros = []
        self.rows = []
        self.tracks = []
        self.nets = {}
        # Map of via names that were autogenerated by SC
        self.viastacks = {
            # (<bottom>, <bottomdir>, <top>, <topdir>, <width>, <height>):
            # [<vianame1>, <vianame2>, ... ],
        }
        # Stuff that gets placed into DEF
        self.vias = {}

        self.blockages = []
        self.obstructions = []

        # Set up custom Jinja `scale` filter as a closure around `self` so we
        # don't have to pass in db_units
        def scale(val):
            if isinstance(val, list):
                return [scale(item) for item in val]
            if isinstance(val, tuple):
                return tuple(scale(item) for item in val)
            # TODO: rounding and making this an int seems helpful for resolving
            # floating point rounding issues, but could be problematic if we
            # want to have floats in DEF file? Alternative could be to use
            # Python decimal library for internally representing micron values
            return int(round(val * self.db_units))
        env.filters['scale'] = scale

        # Used to generate unique instance names for I/O fill cells
        self.fillcell_id = 0
        self.via_i = 0

        ## Extract technology-specific info ##

        # extract std cell info based on libname
        # Extract data from LEFs
        # List of cells the user is able to place
        self.available_cells = {}

        for macrolib in self.chip.get('asic', 'macrolib'):
            lef_path = chip.find_files('library', macrolib, 'lef')[0]
            lef_data = leflib.parse(lef_path)

            if 'macros' not in lef_data:
                logging.warning(f'LEF {lef_path} added to library {macrolib} '
                    'contains no macros. Are you sure this is the correct file?')
                continue

            for name in lef_data['macros'].keys():
                if 'size' in lef_data['macros'][name]:
                    size = lef_data['macros'][name]['size']
                    width = size['width']
                    height = size['height']
                    self.available_cells[name] = _MacroInfo(width, height)
                else:
                    logging.warning(f'Macro {name} missing size in LEF, not adding '
                        'to available cells.')

        tech_lef_data = _get_tech_lef_data(chip, tool)

        stdcell_info = _get_stdcell_info(chip, tech_lef_data)
        self.stdcell_name, self.stdcell_width, self.stdcell_height = stdcell_info

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
        self._stackup = stackup
        # TODO: consider making this a dictionary of namedtuples to ensure layer
        # info is immutable.
        self.layers = {}
        for pdk_name in self.chip.getkeys('pdk', 'grid', stackup):
            sc_name = self.chip.get('pdk', 'grid', stackup, pdk_name, 'name')
            xpitch = self.chip.get('pdk', 'grid', stackup, pdk_name, 'xpitch')
            ypitch = self.chip.get('pdk', 'grid', stackup, pdk_name, 'ypitch')
            xoffset = self.chip.get('pdk', 'grid', stackup, pdk_name, 'xoffset')
            yoffset = self.chip.get('pdk', 'grid', stackup, pdk_name, 'yoffset')

            if ('layers' not in tech_lef_data) or (pdk_name not in tech_lef_data['layers']):
                raise ValueError(f'No layer named {pdk_name} in tech LEF!')
            layer = tech_lef_data['layers'][pdk_name]

            if 'width' not in layer:
                raise ValueError(f'No width for layer {pdk_name} in tech LEF!')
            if 'direction' not in layer:
                raise ValueError(f'No direction for layer {pdk_name} in tech LEF!')
            width = layer['width']
            direction = layer['direction']

            self.layers[sc_name] = {
                'name': pdk_name,
                'width': width,
                'direction': direction,
                'xpitch': xpitch,
                'ypitch': ypitch,
                'xoffset': xoffset,
                'yoffset': yoffset
            }
            self.layers[pdk_name] = self.layers[sc_name]

        # VIARULE GENERATEs extracted from tech LEF
        try:
            self.viarules = self._extract_viarules(tech_lef_data)
        except KeyError:
            raise ValueError('Error extracting viarules. Tech LEF may have errors.')

    def _extract_viarules(self, tech_lef_data):
        if 'viarules' not in tech_lef_data:
            return {}

        viarules = {}
        for name, rule in tech_lef_data['viarules'].items():
            if 'generate' not in rule:
                continue

            if ('layers' not in rule) or (len(rule['layers']) != 3):
                raise ValueError('VIARULE GENERATE expected to have 3 layers.')

            routing_layers = []
            cut_layers = []
            for layer in rule['layers']:
                layer_name = layer['name']
                layer_info = tech_lef_data['layers'][layer_name]
                if layer_info['type'] == 'CUT':
                    cut_layers.append(layer)
                elif layer_info['type'] == 'ROUTING':
                    routing_layers.append(layer)
                else:
                    raise ValueError('Viarule may not contain non-routing '
                        'or non-cut layer!')

            if len(routing_layers) != 2:
                raise ValueError('Viarule must specify exactly two routing layers')
            if len(cut_layers) != 1:
                raise ValueError('Viarule must specify exactly one cut layer')


            layer = cut_layers[0]
            xl, yl, xh, yh = layer['rect']
            cut_size = (xh - xl), (yh - yl)
            cut_spacing = (layer['spacing']['x'] - cut_size[0],
                            layer['spacing']['y'] - cut_size[1])

            l0_name = self._pdk_to_sc_layer(routing_layers[0]['name'])
            if l0_name is None:
                raise ValueError(f'No routing layer named {l0_name}')
            l1_name = self._pdk_to_sc_layer(routing_layers[1]['name'])
            if l1_name is None:
                raise ValueError(f'No routing layer named {l1_name}')

            try:
                l0 = _layer_i(l0_name)
                l1 = _layer_i(l1_name)
            except ValueError:
                # Some of the viarules might be for layers that are not part of
                # our SC metal stackup, so we throw those away - e.g. li1 in
                # Skywater130.
                continue

            if l0 < l1:
                bottom = routing_layers[0]
                bottom_i = l0
                top = routing_layers[1]
                top_i = l1
            else:
                bottom = routing_layers[1]
                bottom_i = l1
                top = routing_layers[0]
                top_i = l0

            key = (bottom_i, top_i)
            if key not in viarules:
                viarules[key] = []
            viarules[key].append({
                'name': name,
                'bottom': {
                    'layer': f'm{bottom_i}',
                    'enclosure': (
                        bottom['enclosure']['overhang1'],
                        bottom['enclosure']['overhang2']
                    )
                },
                'top': {
                    'layer': f'm{top_i}',
                    'enclosure': {
                        top['enclosure']['overhang1'],
                        top['enclosure']['overhang2']
                    }
                },
                'cut': {
                    'layer': cut_layers[0]['name'],
                    'size': cut_size,
                    'spacing': cut_spacing
                }
            })

        return viarules

    def get_layers(self):
        '''Returns list of SC-standardized layer names defined in schema.'''
        layers = []
        for pdk_name in self.chip.getkeys('pdk', 'grid', self._stackup):
            sc_name = self.chip.get('pdk', 'grid', self._stackup, pdk_name, 'name')
            layers.append(sc_name)
        return layers

    def create_diearea(self, diearea, corearea=None, generate_rows=True,
                        generate_tracks=True):
        '''Initializes die.

        Initializes the area of the die and generates placement rows and routing
        tracks. The provided die and core dimensions will overwrite the die/core
        size already present in the chip config.

        Args:
            diearea (list of (float, float)): List of points that form the die
                area. Currently only allowed to provide two points, specifying
                the two bounding corners of a rectangular die. Dimensions are
                specified in microns.
            corearea (list of (float, float)): List of points that form the
                core area of the physical design. If `None`, corearea is set to
                be equivalent to the die area. Currently only allowed to provide
                two points, specifying the two bounding corners of a rectangular
                area.  Dimensions are specified in microns.
            generate_rows (bool): Automatically generate rows to fill entire
                core area.
            generate_tracks (bool): Automatically generate tracks to fill entire
                core area.
        '''
        if len(diearea) != 2:
            raise ValueError('Non-rectangular floorplans not yet supported: '
                             'diearea must be list of two tuples.')
        if diearea[0] != (0, 0):
            # TODO: not sure if this would be a problem, except need to figure
            # out what a non-origin initial point would mean for the LEF output.
            raise ValueError('Non-origin initial die area point not yet supported.')

        # store diearea as 2-tuple since bottom left corner is always 0,0
        self.diearea = diearea
        if corearea is None:
            self.corearea = self.diearea
        else:
            self.corearea = corearea

        if len(self.corearea) != 2:
            raise ValueError('Non-rectangular core areas not yet supported: '
                             'corearea must be list of two tuples.')

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

    def place_pins(self, pins, x, y, xpitch, ypitch, width, height, layer,
                   direction='inout', netname=None, use='signal', fixed=True,
                   snap=False, add_port=False):
        '''Places pins along edge of floorplan.

        Args:
            pins (list of str): List of pin names to place.
            x (float): x-coordinate of first instance in microns.
            y (float): y-coordinate of first instance in microns.
            xpitch (float): Increment along x-axis in microns.
            ypitch (float): Increment along y-axis in microns.
            width (float): Width of pin.
            height (float): Height of pin.
            layer (str): Which metal layer pin is placed on.
            direction (str): I/O direction of pins (must be valid LEF/DEF
                direction).
            netname (str): Name of net that each pin is connected to. If
                `None`, the net name of each pin will correspond to the pin
                name.
            use (str): Usage of pin (must be valid LEF/DEF use).
            fixed (bool): Whether pin status is 'FIXED' or 'PLACED'.
            snap (bool): Whether to snap pin position to align it with the
                nearest routing track. Track direction is determined by
                preferred routing direction as specified in the tech LEF.
            add_port (bool): If True, then calls specifying a pin name that
                has already been placed on the floorplan will add a new port to
                the pin definition. This will disregard the netname, direction,
                and use arguments. If False, then calls specifying a pin name
                that has already been placed will add a new geometry to the most
                recently added port. This will disregard the netname, direction,
                use, and fixed arguments.
        '''
        logging.debug('Placing pins: %s', ' '.join(pins))

        if direction.lower() not in ('input', 'output', 'inout', 'feedthru'):
            raise ValueError('Invalid pin direction')
        if use.lower() not in ('signal', 'power', 'ground', 'clock', 'tieoff',
                               'analog', 'scan', 'reset'):
            raise ValueError('Invalid use')

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

            if pin_name in self.pins:
                if not add_port:
                    pos = self.pins[pin_name]['ports'][-1]['point']
                    shape = {
                        'box': [(x - pos[0], y - pos[1]),
                                ((x - pos[0]) + width, (y - pos[1]) + height)],
                        'layer': self.layers[layer]['name']
                    }
                    self.pins[pin_name]['ports'][-1]['shapes'].append(shape)
                else:
                    port = {
                        'shapes': [{
                            'box': [(-width/2, -height/2), (width/2, height/2)],
                            'layer': self.layers[layer]['name']
                        }],
                        'status': 'fixed' if fixed else 'placed',
                        'point': pos,
                        'orientation': 'N'
                    }
                    self.pins[pin_name]['ports'].append(port)
            else:
                port = {
                    'shapes': [{
                        'box': [(-width/2, -height/2), (width/2, height/2)],
                        'layer': self.layers[layer]['name']
                    }],
                    'status': 'fixed' if fixed else 'placed',
                    'point': pos,
                    'orientation': 'N'
                }

                pin = {
                    'net': netname if netname else pin_name,
                    'direction': direction,
                    'use': use,
                    'ports': [port]
                }

                self.pins[pin_name] = pin

            x += xpitch
            y += ypitch

    def place_macros(self, macros, x, y, xpitch, ypitch, orientation,
                    halo=None, fixed=True, snap=False):
        '''Places macros on floorplan.

        Args:
            macros (list of (str, str)): List of macros to place as tuples of
                (instance name, macro name).
            x (float): x-coordinate of first instance in microns.
            y (float): y-coordinate of first instance in microns.
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

        for instance_name, cell_name in macros:
            macro = {
                'name': instance_name,
                'cell': cell_name,
                'info': self.available_cells[cell_name],
                'x': self.snap(x, self.stdcell_width) if snap else x,
                'y': self.snap(y, self.stdcell_height) if snap else y,
                'status': 'fixed' if fixed else 'placed',
                'orientation': orientation.upper(),
                'halo': halo,
            }
            self.macros.append(macro)

            x += xpitch
            y += ypitch

    def place_wires(self, nets, x, y, xpitch, ypitch, width, height, layer,
                    shape=None, snap=False):
        '''Place wires on floorplan.

        Args:
            nets (list of str): List of net names of wires to place.
            x (float): x-coordinate of first instance in microns.
            y (float): y-coordinate of first instance in microns.
            xpitch (float): Increment along x-axis in microns.
            ypitch (float): Increment along y-axis in microns.
            width (float): Width of wire in microns.
            height (float): Height of wire in microns.
            layer (str): Which metal layer wire is placed on.
            shape (str): Specify wire with special connection requirements
                because of its shape. Must be a valid DEF shape value, such as
                "stripe" or "followpin", or None for no special shape. See the
                DEF 5.8 language reference for more information.
            snap (bool): Whether to snap wire position to align it with the
                nearest routing track. Track direction is determined by
                preferred routing direction as specified in the tech LEF.
        '''

        legal_shapes = (
            'ring', 'padring', 'blockring', 'stripe', 'followpin', 'iowire',
            'corewire', 'blockwire', 'blockagewire', 'fillwire', 'fillwireopc',
            'drcfill'
        )
        if shape is not None and shape.lower() not in legal_shapes:
            raise ValueError('Invalid shape')

        for netname in nets:
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

            if netname in self.nets:
                self.nets[netname]['wires'].append(wire)
            else:
                raise ValueError(f'Net {netname} not found. Please initialize '
                    f'it by calling add_net()')

            x += xpitch
            y += ypitch

    def place_vias(self, nets, x, y, xpitch, ypitch, name, snap=False):
        '''Place vias on floorplan.

        Args:
            nets (list of str): List of net names to associate with each via.
                This function will place one via per entry in this list. To
                place multiple vias associated with the same net, repeat that
                name in the list.
            x (float): x-coordinate of first instance in microns.
            y (float): y-coordinate of first instance in microns.
            xpitch (float): Increment along x-axis in microns.
            ypitch (float): Increment along y-axis in microns.
            name (str): Name of via definition to place.
            snap (bool): Whether to snap via position to align it with
                routing tracks. If the preferred routing direction of the bottom
                layer is horizontal, the via's x position is snapped to the
                nearest top layer x track and the y position is snapped to the
                nearest bottom layer y track. If the preferred routing direction
                of the bottom layer is vertical, the x position is snapped to
                the nearest bottom layer x track, and the y position is snaped
                to the nearest top layer y track.
        '''

        try:
            via_def = self.vias[name]
        except KeyError:
            raise ValueError(f'No via definition called {name}')

        bot_layer = via_def['layers'][0]
        bot_layer_sc = self._pdk_to_sc_layer(bot_layer)
        top_layer = via_def['layers'][2]
        top_layer_sc = self._pdk_to_sc_layer(top_layer)

        for netname in nets:
            if snap:
                if self.layers[bot_layer_sc]['direction'] == 'horizontal':
                    pos = (self.snap_to_x_track(x, top_layer_sc),
                           self.snap_to_y_track(y, bot_layer_sc))
                else:
                    pos = (self.snap_to_x_track(x, bot_layer_sc),
                           self.snap_to_y_track(y, top_layer_sc))
            else:
                pos = x, y

            via = {
                'point': pos,
                'layer': bot_layer,
                'name': name
            }

            if netname in self.nets:
                self.nets[netname]['vias'].append(via)
            else:
                raise ValueError(f'Net {netname} not found. Please initialize '
                    f'it by calling add_net()')

            x += xpitch
            y += ypitch

    def add_via(self, name, bottom_layer, bottom_shapes, cut_layer, cut_shapes,
                top_layer, top_shapes):
        '''Adds a fixed via definition that can be placed using place_vias.

        Args:
            name (str): Name of the via definition.
            bottom_layer (str): Name of bottom routing layer.
            bottom_shapes (list of tuple): Shapes to place on bottom layer.
                Each item in the list is a rectangle specified as a tuple of
                points representing the lower left and upper right corners of
                the rectangle, relative to the center of the via.
            cut_layer (str): Name of cut layer.
            cut_shapes (list of tuple): Shapes to place on cut layer,
                specified the same as bottom_shapes.
            top_layer (str): Name of top routing layer.
            top_shapes (list of tuple): Shapes to place on top layer,
                specified the same as bottom_shapes.

        Examples:
            >>> shapes = [
                ((-10, -10), (-2.5, -2.5)),
                ((2.5, -10), (10, -2.5)),
                ((-10, 2.5), (-2.5, 10)),
                ((2.5, 2.5), (10, 10))
                ]
            >>> fp.add_via('myvia', 'm1', shapes, 'via1', shapes, 'm2', shapes)
            Defines via connecting layers 'm1' and 'm2' through 'via1', in the
            form of a 2x2 array of squares.
        '''

        if name in self.vias:
            raise ValueError(f'There is already a via definition called {name}')

        if bottom_layer in self.layers:
            bottom_layer_name = self.layers[bottom_layer]['name']
        else:
            raise ValueError(f'{bottom_layer} is not a valid layer')

        if top_layer in self.layers:
            top_layer_name = self.layers[top_layer]['name']
        else:
            raise ValueError(f'{top_layer} is not a valid layer')

        layers = (bottom_layer_name, cut_layer, top_layer_name)
        all_shapes = {
            bottom_layer_name: bottom_shapes,
            top_layer_name: top_shapes,
            cut_layer: cut_shapes
        }

        rects = []
        for layer_name in layers:
            for ll, ur in all_shapes[layer_name]:
                rects.append({
                    'layer': layer_name,
                    'll': ll,
                    'ur': ur
                })

        self.vias[name] = {
            'rects': rects,
            'layers': layers,
            'generated': False
        }

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
            site_name = self.stdcell_name

        if area is None:
            area = self.corearea

        start_x, start_y = area[0]
        core_width = area[1][0] - start_x
        core_height = area[1][1] - start_y

        num_rows = int(core_height / self.stdcell_height)
        num_x = core_width // self.stdcell_width

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
                'stepx' : self.snap_to_grid(self.stdcell_width),
                'stepy' : 0
            }
            self.rows.append(row)

            start_y += self.stdcell_height

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
            area = self.diearea

        start_x, start_y = area[0]
        die_width, die_height = area[1]

        for sc_name in self.get_layers():
            layer = self.layers[sc_name]
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
            x = self.snap(x, self.stdcell_width)
            y = self.snap(y, self.stdcell_height)

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
            layers = self.get_layers()

        if snap:
            x = self.snap(x, self.stdcell_width)
            y = self.snap(y, self.stdcell_height)

        for layer in layers:
            if layer in self.layers:
                self.obstructions.append({
                    'll': (x, y),
                    'ur': (x + width, y + height),
                    'layer': self.layers[layer]['name']
                })
            else:
                raise ValueError(f'Layer {layer} not found in tech info!')

    def fill_io_region(self, region, fillcells, orientation, direction):
        '''Fill empty space in region with I/O filler cells.

        Args:
            region (list of tuple of float): bottom-left and top-right corner of
                region to fill.
            fillcells (list of str): List of names of I/O filler cells to use.
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

        if direction not in ('v', 'h'):
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
        io_fillcells = []
        for cell in fillcells:
            if not cell in self.available_cells:
                raise ValueError(f'Provided fill cell {cell} is not included in'
                    f'list of available macros')
            io_fillcells.append((cell, self.available_cells[cell]))

        io_fillcells = sorted(io_fillcells, key=lambda c: c[1].width, reverse=True)

        for start, end in gaps:
            cell_idx = 0
            while start != end:
                cell, cell_info = io_fillcells[cell_idx]
                width = cell_info.width
                if width > end - start:
                    cell_idx += 1
                    if cell_idx >= len(io_fillcells):
                        raise ValueError('Unable to fill gap with available cells!')
                    continue

                name = f'_sc_io_fill_cell_{self.fillcell_id}'
                self.fillcell_id += 1
                if direction == 'h':
                    self.place_macros(
                        [(name, cell)], start, region_min_y, 0, 0, orientation, snap=False
                    )
                else:
                    self.place_macros(
                        [(name, cell)], region_min_x, start, 0, 0, orientation, snap=False
                    )
                start += width

    def add_net(self, net, pins, use):
        '''Add special net.

        Must be called before placing a wire for a net. Calls after the first
        will overwrite configuration values, but leave wires placed.

        Args:
            net (str): Name of net.
            pins (list of str): Name of pins in macro to associate with this net.
            use (str): Use of net. Must be valid LEF/DEF use.
        '''

        if use.lower() not in (
            'analog', 'clock', 'ground', 'power', 'reset', 'scan', 'signal', 'tieoff'
        ):
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

    def place_ring(self, net, x, y, width, height, hwidth, vwidth, hlayer, vlayer):
        '''Place wire ring.

        Args:
            net (str): Name of net.
            x (float): x-coordinate of bottom left corner of ring.
            y (float): y-coordinate of bottom left corner of ring.
            width (float): Width of ring from edge-to-edge.
            height (float): Height of ring from edge-to-edge.
            hwidth (float): Width of horizontal wires used in ring.
            vwidth (float): Width of vertical wires used in ring.
            hlayer (str): Metal layer to place horizontal wires on.
            vlayer (str): Metal layer to place vertical wires on.
        '''

        # bottom
        self.place_wires([net], x, y, 0, 0, width, hwidth, hlayer, 'stripe')
        # top
        self.place_wires([net], x, y + height - hwidth, 0, 0, width, hwidth, hlayer, 'stripe')
        # left
        self.place_wires([net], x, y, 0, 0, vwidth, height, vlayer, 'stripe')
        # right
        self.place_wires([net], x + width - vwidth, y, 0, 0, vwidth, height, vlayer, 'stripe')

    def _determine_num_via_cols(self, viarule, width, lower_dir):
        '''Determine number of via columns we can insert in a given intersection.

        Based on OpenROAD TCL logic:
        https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/pdn/src/PdnGen.tcl#L2147
        '''

        lower_enclosure = viarule['bottom']['enclosure']
        upper_enclosure = viarule['top']['enclosure']
        cut_w, _ = viarule['cut']['size']
        spacing_x, _ = viarule['cut']['spacing']

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

        return cols

    def _determine_num_via_rows(self, viarule, height, lower_dir):
        '''Determine number of via rows we can insert in a given intersection.

        Based on OpenROAD TCL logic:
        https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/pdn/src/PdnGen.tcl#L2228
        '''

        lower_enclosure = viarule['bottom']['enclosure']
        upper_enclosure = viarule['top']['enclosure']
        _, cut_h = viarule['cut']['size']
        _, spacing_y = viarule['cut']['spacing']

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

        return rows

    def _generate_via(self, viarule, width, height, lower_dir, stack_bottom, stack_top):
        '''Given a viarule and an intersection of metal layers, generate a via
        array that can connect the intersection.
        '''

        lower_enclosure = viarule['bottom']['enclosure']
        upper_enclosure = viarule['top']['enclosure']
        cut_w, cut_h = viarule['cut']['size']
        spacing_x, spacing_y = viarule['cut']['spacing']

        # Calculate maximum of rows and cols of cuts that can fit
        rows = self._determine_num_via_rows(viarule, height, lower_dir)
        cols = self._determine_num_via_cols(viarule, width, lower_dir)

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
            'rowcol': (rows, cols),
            'generated': True
        }

        return score, via

    def _insert_via(self, net, pos, bottom_layer, top_layer, bottom_dir, top_dir, width, height):
        '''Insert vias between two given intersecting metal layers.'''

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
                    score, via = self._generate_via(
                        viarule, width, height, bottom_dir, i == bottom_i, i + 1 == top_i
                    )
                    if score < min_score:
                        best_via = via
                # TODO: error if no best_via

                # Add generated as one of our vias and to our current stack
                vianame = f'_via{self.via_i}'
                self.via_i += 1
                self.vias[vianame] = best_via
                stack.append(vianame)

                i += 1

            self.viastacks[stack_key] = stack

        for vianame in self.viastacks[stack_key]:
            self.place_vias([net], x, y, 0, 0, vianame)

    def insert_vias(self, nets=None, layers=None):
        '''Automatically insert vias.

        Automatically inserts vias between common specialnets that intersect on
        different metal layers. Via geometries are generated based on VIARULE
        GENERATE statements found in the tech LEF.

        Args:
            nets (list of str): List of nets to analyze for via insertion. If
                empty or None, look at all nets.
            layers (list of tuples): List of tuples representing pairs of layers
                to check for intersections between. If empty or None, look at all
                layer pairs.
        '''

        if not nets:
            nets = self.nets

        for net in nets:
            if net not in self.nets:
                raise ValueError(f'Unable to insert vias on net {net}, not '
                    'in list of known specialnets.')

            # TODO: is this valid? trying to sort from bottom to top
            wires = sorted(self.nets[net]['wires'], key=lambda w: w['sclayer'] )
            for i, wire_bottom in enumerate(wires):
                for wire_top in wires[i:]:
                    bottom_layer = wire_bottom['sclayer']
                    top_layer = wire_top['sclayer']

                    if bottom_layer == top_layer:
                        continue

                    if layers and (bottom_layer, top_layer) not in layers:
                        # If layers list defined, skip wires whose layers are
                        # not in it. We could do this more efficiently by
                        # limiting what we iterate over, but this seems
                        # performant enough for now.
                        continue

                    bottom_rect = _wire_to_rect(wire_bottom)
                    top_rect = _wire_to_rect(wire_top)

                    intersection = _get_rect_intersection(bottom_rect, top_rect)

                    if intersection is not None:
                        left, bottom, right, top = intersection
                        x = (left + right) / 2
                        y = (bottom + top) / 2
                        width = right - left
                        height = top - bottom
                        bottom_dir = self.layers[bottom_layer]['direction']
                        top_dir = self.layers[top_layer]['direction']

                        self._insert_via(
                            net, (x, y), bottom_layer, top_layer, bottom_dir, top_dir, width, height
                        )

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

    def _pdk_to_sc_layer(self, layer):
        return self.chip.get('pdk', 'grid', self._stackup, layer, 'name')

# Helper functions used for diearea inference. These are more-or-less
# floorplanning related, so including them in this file.

def _find_cell_area(chip, startstep, startindex):
    '''Helper to work back through the preceeding flowgraph steps to find a step
    that's set the cellarea.'''
    select = chip.get('flowstatus', startstep, startindex, 'select')
    for step, index in select:
        cell_area = chip.get('metric', step, index, 'cellarea', 'real')
        if cell_area:
            return cell_area

        cell_area = _find_cell_area(chip, step, index)
        if cell_area:
            return cell_area

    return None

def _calculate_core_dimensions(density, aspectratio, area, lib_height):
    target_area = area * 100 / density
    core_width = math.sqrt(target_area / aspectratio)
    core_height = core_width * aspectratio

    core_width = math.ceil(core_width / lib_height) * lib_height
    core_height = math.ceil(core_height / lib_height) * lib_height

    return core_width, core_height

def _infer_diearea(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    density = chip.get('asic', 'density')
    coremargin = chip.get('asic', 'coremargin')
    aspectratio = chip.get('asic', 'aspectratio')
    if density < 1 or density > 100:
        chip.logger.error('ASIC density must be between 1 and 100')
        chip.error = 1
        return None

    cell_area = _find_cell_area(chip, step, index)
    if not cell_area:
        chip.logger.error('No cell area set in previous step')
        chip.error = 1
        return None

    lef_data = _get_tech_lef_data(chip, 'openroad')
    _, _, lib_height = _get_stdcell_info(chip, lef_data)

    core_width, core_height = _calculate_core_dimensions(density,
                                                         aspectratio,
                                                         cell_area,
                                                         lib_height)

    diearea = [(0, 0),
               (2 * coremargin + core_width, 2 * coremargin + core_height)]
    corearea = [(coremargin, coremargin),
                (coremargin + core_width, coremargin + core_height)]

    return diearea, corearea
