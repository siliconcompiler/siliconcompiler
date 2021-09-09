# These imports let us use libc file I/O to communicate with C++ lef library
from libc.stdio cimport fopen, fclose

# All of the callback functions that do not receive primitive types instead
# receive a pointer to an object defined by the C++ LEF parser. In order to access
# members of this object, we must dereference these pointers using Cython's
# `deref` operator.
#
# IMPORTANT NOTE: For memory safety purposes, we MUST NOT use a deref'd pointer
# as the right-hand side of an assignment.
#
# Although we can get away with it in some cases, this is super dangerous and to
# be extra careful we should never do it. Even though the assignment performs
# a copy-by-value, the problem is some of the LEF parser objects have members
# that are pointers to other objects, and they free these pointers when their
# destructor is called. Therefore, these internal objects will be double
# free()'d when the function returns and the destructor of the original object
# is called internally.
#
# Therefore, the correct way to call a method `func` of a C++ object pointer `o`
# is `deref(o).func()`.
from cython.operator import dereference as deref

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

cdef int units_cb(lefrCallbackType_e t, lefiUnits* u, lefiUserData data):
    if 'units' not in _state.data:
        _state.data['units'] = {}

    if deref(u).hasDatabase():
        _state.data['units']['database'] = deref(u).databaseNumber()
    if deref(u).hasCapacitance():
        _state.data['units']['capacitance'] = deref(u).capacitance()
    if deref(u).hasResistance():
        _state.data['units']['resistance'] = deref(u).resistance()
    if deref(u).hasTime():
        _state.data['units']['time'] = deref(u).time()
    if deref(u).hasPower():
        _state.data['units']['power'] = deref(u).power()
    if deref(u).hasCurrent():
        _state.data['units']['current'] = deref(u).current()
    if deref(u).hasVoltage():
        _state.data['units']['voltage'] = deref(u).voltage()
    if deref(u).hasFrequency():
        _state.data['units']['frequency'] = deref(u).frequency()

    return 0

cdef int layer_cb(lefrCallbackType_e cb_type, lefiLayer* l, void* data):
    if 'layers' not in _state.data:
        _state.data['layers'] = {}

    name = deref(l).name().decode('ascii')
    _state.data['layers'][name] = {}

    if deref(l).hasType():
        _state.data['layers'][name]['type'] = deref(l).type().decode('ascii')
    if deref(l).hasPitch():
        _state.data['layers'][name]['pitch'] = deref(l).pitch()
    if deref(l).hasXYPitch():
        _state.data['layers'][name]['pitch'] = (deref(l).pitchX(), deref(l).pitchY())
    if deref(l).hasOffset():
        _state.data['layers'][name]['offset'] = deref(l).offset()
    if deref(l).hasXYOffset():
        _state.data['layers'][name]['offset'] = (deref(l).offsetX(), deref(l).offsetY())
    if deref(l).hasWidth():
        _state.data['layers'][name]['width'] = deref(l).width()
    if deref(l).hasArea():
        _state.data['layers'][name]['area'] = deref(l).area()
    if deref(l).hasDirection():
        _state.data['layers'][name]['direction'] = deref(l).direction().decode()

    return 0

cdef int macro_begin_cb(lefrCallbackType_e cb_type, const char* name, lefiUserData data):
    if 'macros' not in _state.data:
        _state.data['macros'] = {}

    _state.cur_macro = name.decode('ascii')
    _state.data['macros'][_state.cur_macro] = {}

    return 0

cdef int pin_cb(lefrCallbackType_e cb_type, lefiPin* p, lefiUserData data):
    if 'pins' not in _state.data['macros'][_state.cur_macro]:
        _state.data['macros'][_state.cur_macro]['pins'] = {}


    name = deref(p).name().decode('ascii')
    _state.data['macros'][_state.cur_macro]['pins'][name] = {}

    ports = []
    for i in range(deref(p).numPorts()):
        portptr = deref(p).port(i)
        port = {}

        # The CLASS of a port is stored in its list of items, so search for that
        # here.
        for j in range(deref(portptr).numItems()):
            if deref(portptr).itemType(j) == lefiGeomClassE:
                port['class'] = deref(portptr).getClass(j).decode('ascii')

        # Otherwise, the other port "items" all refer to layerGeometries, which
        # are shared by several other types of things, so we extract them using
        # a separate helper function.
        geometries = extract_layer_geometries(portptr)
        if len(geometries) > 0:
            port['layer_geometries'] = geometries

        ports.append(port)

    if len(ports) > 0:
        _state.data['macros'][_state.cur_macro]['pins'][name]['ports'] = ports

    return 0

cdef extract_layer_geometries(lefiGeometries* g):
    geometries = []
    cur_geometry = {}

    for i in range(deref(g).numItems()):
        geo_type = deref(g).itemType(i)

        if geo_type == lefiGeomLayerE:
            # Geometries start with LAYER statements. If we already have a
            # geometry actively being worked on, we append it to the list
            # and start a new one.
            if cur_geometry != {}:
                geometries.append(cur_geometry)
                cur_geometry = {}

            cur_geometry['layer'] = deref(g).getLayer(i).decode('ascii')
            cur_geometry['shapes'] = []
        elif geo_type == lefiGeomLayerExceptPgNetE:
            cur_geometry['exceptpgnet'] = True
        elif geo_type == lefiGeomLayerMinSpacingE:
            cur_geometry['spacing'] = deref(g).getLayerMinSpacing(i)
        elif geo_type == lefiGeomLayerRuleWidthE:
            cur_geometry['designrulewidth'] = deref(g).getLayerRuleWidth(i)
        elif geo_type == lefiGeomWidthE:
            cur_geometry['width'] = deref(g).getWidth(i)
        elif geo_type == lefiGeomPathE:
            pathptr = deref(g).getPath(i)

            points = []
            for j in range(deref(pathptr).numPoints):
                points.append((deref(pathptr).x[i], deref(pathptr).y[i]))

            cur_geometry['shapes'].append({
                'path': points,
                'mask': deref(pathptr).colorMask,
            })
        elif geo_type == lefiGeomPathIterE:
            pathitrptr = deref(g).getPathIter(i)

            points = []
            for j in range(deref(pathitrptr).numPoints):
                points.append((deref(pathitrptr).x[i], deref(pathitrptr).y[i]))

            cur_geometry['shapes'].append({
                'path': points,
                'mask': deref(pathitrptr).colorMask,
                'iterate': {
                    'num_x': deref(pathitrptr).xStart,
                    'num_y': deref(pathitrptr).yStart,
                    'step_x': deref(pathitrptr).xStep,
                    'step_y': deref(pathitrptr).yStep
                }
            })
        elif geo_type == lefiGeomRectE:
            rectptr = deref(g).getRect(i)
            cur_geometry['shapes'].append({
                'rect': (deref(rectptr).xl, deref(rectptr).yl, deref(rectptr).xh, deref(rectptr).yh),
                'mask':  deref(rectptr).colorMask,
            })
        elif geo_type == lefiGeomRectIterE:
            rectitrptr = deref(g).getRectIter(i)
            cur_geometry['shapes'].append({
                'rect': (deref(rectitrptr).xl, deref(rectitrptr).yl, deref(rectitrptr).xh, deref(rectitrptr).yh),
                'mask': deref(rectitrptr).colorMask,
                'iterate': {
                    'num_x': deref(rectitrptr).xStart,
                    'num_y': deref(rectitrptr).yStart,
                    'step_x': deref(rectitrptr).xStep,
                    'step_y': deref(rectitrptr).yStep
                }
            })
        elif geo_type == lefiGeomPolygonE:
            polyptr = deref(g).getPolygon(i)

            points = []
            for j in range(deref(polyptr).numPoints):
                points.append((deref(polyptr).x[i], deref(polyptr).y[i]))

            cur_geometry['shapes'].append({
                'polygon': points,
                'mask': deref(polyptr).colorMask,
            })
        elif geo_type == lefiGeomPolygonIterE:
            polyitrptr = deref(g).getPolygonIter(i)

            points = []
            for j in range(deref(polyitrptr).numPoints):
                points.append((deref(polyitrptr).x[i], deref(polyitrptr).y[i]))

            cur_geometry['shapes'].append({
                'polygon': points,
                'mask': deref(polyitrptr).colorMask,
                'iterate': {
                    'num_x': deref(polyitrptr).xStart,
                    'num_y': deref(polyitrptr).yStart,
                    'step_x': deref(polyitrptr).xStep,
                    'step_y': deref(polyitrptr).yStep
                }
            })
        elif geo_type == lefiGeomViaE:
            viaptr = deref(g).getVia(i)

            top = hex(deref(viaptr).topMaskNum).lstrip('0x')
            cut = hex(deref(viaptr).cutMaskNum).lstrip('0x')
            bot = hex(deref(viaptr).bottomMaskNum).lstrip('0x')

            cur_geometry['via'] = {
                'pt': (deref(viaptr).x, deref(viaptr).y),
                'name': deref(viaptr).name.decode('ascii'),
                'mask': top+cut+bot
            }
        elif geo_type == lefiGeomViaIterE:
            viaitrptr = deref(g).getViaIter(i)

            print('via iter')
            top = hex(deref(viaitrptr).topMaskNum).lstrip('0x')
            cut = hex(deref(viaitrptr).cutMaskNum).lstrip('0x')
            bot = hex(deref(viaitrptr).bottomMaskNum).lstrip('0x')

            cur_geometry['via'] = {
                'pt': (deref(viaitrptr).x, deref(viaitrptr).y),
                'name': deref(viaitrptr).name.decode('ascii'),
                'mask': top+cut+bot,
                 'iterate': {
                     'num_x': deref(viaitrptr).xStart,
                     'num_y': deref(viaitrptr).yStart,
                     'step_x': deref(viaitrptr).xStep,
                     'step_y': deref(viaitrptr).yStep
                }
            }

    if cur_geometry != {}:
        geometries.append(cur_geometry)

    return geometries

cdef int macro_cb(lefrCallbackType_e cb_type, lefiMacro* m, void* data):
    if deref(m).hasSize():
        _state.data['macros'][_state.cur_macro]['size'] = {
            'width': deref(m).sizeX(),
            'height': deref(m).sizeY()
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
