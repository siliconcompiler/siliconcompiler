'''
Cython pitfalls to be aware of:
- No need to deref() pointers we receive in C-style callbacks -- we can just
  call methods on these directly using standard `.` notation (it's equivalent to
  -> in C/C++). deref()ing and then assigning can result in memory errors due to
  the destructor of the resulting object being called when the function goes out
  of scope.
- Control structures like if/else don't create their own scope in Python! They
  do in C/C++, but remember that this code is all semantically equivalent to
  Python.
'''

# These imports let us use libc file I/O to communicate with C++ lef library
from libc.stdio cimport fopen, fclose

cimport _leflib

class ParserState:
    def __init__(self):
        self.clear()

    def clear(self):
        self.data = {}
        self.cur_macro = None

# Hold parsed LEF data in a global that gets cleared by parse() on each call.
# The intended use of the LEF parser library is to pass around this data
# structure via the void* passed into each callback, but using a global lets us
# avoid having to deal with raw pointers to Python objects.
_state = ParserState()

cdef int double_cb(lefrCallbackType_e cb_type, double value, lefiUserData data):
    if cb_type == lefrManufacturingCbkType:
        _state.data['manufacturinggrid'] = value
    elif cb_type == lefrVersionCbkType:
        _state.data['version'] = value

cdef int units_cb(lefrCallbackType_e t, lefiUnits* units, lefiUserData data):
    if 'units' not in _state.data:
        _state.data['units'] = {}

    if units.hasDatabase():
        _state.data['units']['database'] = units.databaseNumber()
    if units.hasCapacitance():
        _state.data['units']['capacitance'] = units.capacitance()
    if units.hasResistance():
        _state.data['units']['resistance'] = units.resistance()
    if units.hasTime():
        _state.data['units']['time'] = units.time()
    if units.hasPower():
        _state.data['units']['power'] = units.power()
    if units.hasCurrent():
        _state.data['units']['current'] = units.current()
    if units.hasVoltage():
        _state.data['units']['voltage'] = units.voltage()
    if units.hasFrequency():
        _state.data['units']['frequency'] = units.frequency()

    return 0

cdef int layer_cb(lefrCallbackType_e cb_type, lefiLayer* layer, void* data):
    if 'layers' not in _state.data:
        _state.data['layers'] = {}

    name = layer.name().decode('ascii')
    _state.data['layers'][name] = {}

    if layer.hasType():
        _state.data['layers'][name]['type'] = layer.type().decode('ascii')
    if layer.hasPitch():
        _state.data['layers'][name]['pitch'] = layer.pitch()
    if layer.hasXYPitch():
        _state.data['layers'][name]['pitch'] = (layer.pitchX(), layer.pitchY())
    if layer.hasOffset():
        _state.data['layers'][name]['offset'] = layer.offset()
    if layer.hasXYOffset():
        _state.data['layers'][name]['offset'] = (layer.offsetX(), layer.offsetY())
    if layer.hasWidth():
        _state.data['layers'][name]['width'] = layer.width()
    if layer.hasArea():
        _state.data['layers'][name]['area'] = layer.area()
    if layer.hasDirection():
        _state.data['layers'][name]['direction'] = layer.direction().decode()

    return 0

cdef int macro_begin_cb(lefrCallbackType_e cb_type, const char* name, lefiUserData data):
    if 'macros' not in _state.data:
        _state.data['macros'] = {}

    _state.cur_macro = name.decode('ascii')
    _state.data['macros'][_state.cur_macro] = {}

    return 0

cdef int pin_cb(lefrCallbackType_e cb_type, lefiPin* pin, lefiUserData data):
    if 'pins' not in _state.data['macros'][_state.cur_macro]:
        _state.data['macros'][_state.cur_macro]['pins'] = {}

    name = pin.name().decode('ascii')
    _state.data['macros'][_state.cur_macro]['pins'][name] = {}

    ports = []
    for i in range(pin.numPorts()):
        port = pin.port(i)
        port_data = {}

        # The CLASS of a port is stored in its list of items, so search for that
        # here.
        for j in range(port.numItems()):
            if port.itemType(j) == lefiGeomClassE:
                port_data['class'] = port.getClass(j).decode('ascii')

        # Otherwise, the other port "items" all refer to layerGeometries, which
        # are shared by several other types of things, so we extract them using
        # a separate helper function.
        geometries = extract_layer_geometries(port)
        if len(geometries) > 0:
            port_data['layer_geometries'] = geometries

        ports.append(port_data)

    if len(ports) > 0:
        _state.data['macros'][_state.cur_macro]['pins'][name]['ports'] = ports

    return 0

cdef extract_layer_geometries(lefiGeometries* geos):
    geometries = []
    cur_geometry = {}

    for i in range(geos.numItems()):
        geo_type = geos.itemType(i)

        if geo_type == lefiGeomLayerE:
            # Geometries start with LAYER statements. If we already have a
            # geometry actively being worked on, we append it to the list
            # and start a new one.
            if cur_geometry != {}:
                geometries.append(cur_geometry)
                cur_geometry = {}

            cur_geometry['layer'] = geos.getLayer(i).decode('ascii')
            cur_geometry['shapes'] = []
        elif geo_type == lefiGeomLayerExceptPgNetE:
            cur_geometry['exceptpgnet'] = True
        elif geo_type == lefiGeomLayerMinSpacingE:
            cur_geometry['spacing'] = geos.getLayerMinSpacing(i)
        elif geo_type == lefiGeomLayerRuleWidthE:
            cur_geometry['designrulewidth'] = geos.getLayerRuleWidth(i)
        elif geo_type == lefiGeomWidthE:
            cur_geometry['width'] = geos.getWidth(i)
        elif geo_type == lefiGeomPathE:
            path = geos.getPath(i)

            points = []
            for j in range(path.numPoints):
                points.append((path.x[i], path.y[i]))

            cur_geometry['shapes'].append({
                'path': points,
                'mask': path.colorMask,
            })
        elif geo_type == lefiGeomPathIterE:
            pathitr = geos.getPathIter(i)

            points = []
            for j in range(pathitr.numPoints):
                points.append((pathitr.x[i], pathitr.y[i]))

            cur_geometry['shapes'].append({
                'path': points,
                'mask': pathitr.colorMask,
                'iterate': {
                    'num_x': pathitr.xStart,
                    'num_y': pathitr.yStart,
                    'step_x': pathitr.xStep,
                    'step_y': pathitr.yStep
                }
            })
        elif geo_type == lefiGeomRectE:
            rect = geos.getRect(i)
            cur_geometry['shapes'].append({
                'rect': (rect.xl, rect.yl, rect.xh, rect.yh),
                'mask':  rect.colorMask,
            })
        elif geo_type == lefiGeomRectIterE:
            rectitr = geos.getRectIter(i)
            cur_geometry['shapes'].append({
                'rect': (rectitr.xl, rectitr.yl, rectitr.xh, rectitr.yh),
                'mask': rectitr.colorMask,
                'iterate': {
                    'num_x': rectitr.xStart,
                    'num_y': rectitr.yStart,
                    'step_x': rectitr.xStep,
                    'step_y': rectitr.yStep
                }
            })
        elif geo_type == lefiGeomPolygonE:
            poly = geos.getPolygon(i)

            points = []
            for j in range(poly.numPoints):
                points.append((poly.x[i], poly.y[i]))

            cur_geometry['shapes'].append({
                'polygon': points,
                'mask': poly.colorMask,
            })
        elif geo_type == lefiGeomPolygonIterE:
            polyitr = geos.getPolygonIter(i)

            points = []
            for j in range(polyitr.numPoints):
                points.append((polyitr.x[i], polyitr.y[i]))

            cur_geometry['shapes'].append({
                'polygon': points,
                'mask': polyitr.colorMask,
                'iterate': {
                    'num_x': polyitr.xStart,
                    'num_y': polyitr.yStart,
                    'step_x': polyitr.xStep,
                    'step_y': polyitr.yStep
                }
            })
        elif geo_type == lefiGeomViaE:
            via = geos.getVia(i)

            top = hex(via.topMaskNum).lstrip('0x')
            cut = hex(via.cutMaskNum).lstrip('0x')
            bot = hex(via.bottomMaskNum).lstrip('0x')

            cur_geometry['via'] = {
                'pt': (via.x, via.y),
                'name': via.name.decode('ascii'),
                'mask': top+cut+bot
            }
        elif geo_type == lefiGeomViaIterE:
            viaitr = geos.getViaIter(i)

            top = hex(viaitr.topMaskNum).lstrip('0x')
            cut = hex(viaitr.cutMaskNum).lstrip('0x')
            bot = hex(viaitr.bottomMaskNum).lstrip('0x')

            cur_geometry['via'] = {
                'pt': (viaitr.x, viaitr.y),
                'name': viaitr.name.decode('ascii'),
                'mask': top+cut+bot,
                 'iterate': {
                     'num_x': viaitr.xStart,
                     'num_y': viaitr.yStart,
                     'step_x': viaitr.xStep,
                     'step_y': viaitr.yStep
                }
           }

    if cur_geometry != {}:
        geometries.append(cur_geometry)

    return geometries

cdef int macro_cb(lefrCallbackType_e cb_type, lefiMacro* macro, void* data):
    if macro.hasSize():
        _state.data['macros'][_state.cur_macro]['size'] = {
            'width': macro.sizeX(),
            'height': macro.sizeY()
        }

    return 0

# The single wrapper function we expose
def parse(path):
    _state.clear()

    if lefrInit() != 0:
        return None

    lefrSetUnitsCbk(units_cb)
    lefrSetVersionCbk(double_cb)
    lefrSetLayerCbk(layer_cb)
    lefrSetMacroBeginCbk(macro_begin_cb)
    lefrSetMacroCbk(macro_cb)
    lefrSetPinCbk(pin_cb)
    lefrSetManufacturingCbk(double_cb)

    # Use this to pass path to C++ functions
    path_bytes = path.encode('ascii')

    f_ptr = fopen(path_bytes, 'r')
    if f_ptr == NULL:
        print("Couldn't open file " + path)
        return None

    r = lefrRead(f_ptr, path_bytes, NULL)

    fclose(f_ptr)

    return _state.data
