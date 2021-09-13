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

import cython

import traceback

# Fused types that let us use helper functions to simplify layer geometry
# extraction. All of these types grouped together have some common interface,
# and using the fused types lets us make a single function that can deal with
# all of them (similar to Python's duck-typing, but implemented using C++
# templates under the hood).
RectGeometry = cython.fused_type(
    # common members: xl, yl, xh, yl
    cython.pointer(lefiGeomRect),
    cython.pointer(lefiGeomRectIter)
)

PointListGeometry = cython.fused_type(
    # common members: x, y, numPoints, colorMask
    cython.pointer(lefiGeomPath),
    cython.pointer(lefiGeomPathIter),
    cython.pointer(lefiGeomPolygon),
    cython.pointer(lefiGeomPolygonIter)
)

ViaGeometry = cython.fused_type(
    # common members: name, x, y, topMaskNum, cutMaskNum, bottomMaskNum
    cython.pointer(lefiGeomVia),
    cython.pointer(lefiGeomViaIter)
)

IterableGeometry = cython.fused_type(
    # common members: xStart, yStart, xStep, yStep
    cython.pointer(lefiGeomRectIter),
    cython.pointer(lefiGeomPathIter),
    cython.pointer(lefiGeomPolygonIter),
    cython.pointer(lefiGeomViaIter)
)

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
    try:
        if cb_type == lefrManufacturingCbkType:
            _state.data['manufacturinggrid'] = value
        elif cb_type == lefrVersionCbkType:
            _state.data['version'] = value
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int units_cb(lefrCallbackType_e t, lefiUnits* units, lefiUserData data):
    try:
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
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int divider_chars_cb(lefrCallbackType_e cb_type, const char* val, lefiUserData data):
    try:
        _state.data['dividerchars'] = val.decode('ascii')
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int busbit_chars_cb(lefrCallbackType_e cb_type, const char* val, lefiUserData data):
    try:
        _state.data['busbitchars'] = val.decode('ascii')
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int layer_cb(lefrCallbackType_e cb_type, lefiLayer* layer, void* data):
    try:
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
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int macro_begin_cb(lefrCallbackType_e cb_type, const char* name, lefiUserData data):
    try:
        if 'macros' not in _state.data:
            _state.data['macros'] = {}

        _state.cur_macro = name.decode('ascii')
        _state.data['macros'][_state.cur_macro] = {}
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int pin_cb(lefrCallbackType_e cb_type, lefiPin* pin, lefiUserData data):
    try:
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
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int obs_cb(lefrCallbackType_e cb_type, lefiObstruction* obs, lefiUserData data):
    try:
        if 'obs' not in _state.data['macros'][_state.cur_macro]:
            _state.data['macros'][_state.cur_macro]['obs'] = []

        geometries = extract_layer_geometries(obs.geometries())

        # Append geometries even if empty so that the dictionary reflects how many
        # OBS appear in the LEF (even if they're empty).
        _state.data['macros'][_state.cur_macro]['obs'].append(geometries)
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int clearance_measure_cb(lefrCallbackType_e cb_type, const char* val, lefiUserData data):
    try:
        _state.data['clearancemeasure'] = val.decode('ascii')
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int fixed_mask_cb(lefrCallbackType_e cb_type, int val, lefiUserData data):
    try:
        _state.data['fixedmask'] = True if val == 1 else False
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int max_via_stack_cb(lefrCallbackType_e cb_type, lefiMaxStackVia* maxstackvia, lefiUserData data):
    try:
        _state.data['maxviastack'] = {
            'value': maxstackvia.maxStackVia(),
        }

        if maxstackvia.hasMaxStackViaRange():
            _state.data['maxviastack']['range'] = {
                'bottom': maxstackvia.maxStackViaBottomLayer().decode('ascii'),
                'top': maxstackvia.maxStackViaTopLayer().decode('ascii')
            }
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int site_cb(lefrCallbackType_e cb_type, lefiSite* site, lefiUserData data):
    try:
        if 'sites' not in _state.data:
            _state.data['sites'] = {}

        site_data = {}
        if site.hasClass():
            site_data['class'] = site.siteClass().decode('ascii')

        symmetries = []
        if site.hasXSymmetry():
            symmetries.append('X')
        if site.hasYSymmetry():
            symmetries.append('Y')
        if site.has90Symmetry():
            symmetries.append('R90')
        if len(symmetries) > 0:
            site_data['symmetry'] = symmetries

        rowpattern = []
        for i in range(site.numSites()):
            rowpattern.append({
                'name': site.siteName(i).decode('ascii'),
                'orient': site.siteOrientStr(i).decode('ascii')
            })
        if len(rowpattern) > 0:
            site_data['rowpattern'] = rowpattern

        if site.hasSize():
            site_data['size'] = {
                'width': site.sizeX(),
                'height': site.sizeY()
            }

        name = site.name().decode('ascii')
        _state.data['sites'][name] = site_data
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef extract_points(PointListGeometry geo):
    points = []
    for i in range(geo.numPoints):
        pt = (geo.x[i], geo.y[i])
        points.append(pt)
    return points

cdef extract_rect(RectGeometry rect):
    return (rect.xl, rect.yl, rect.xh, rect.yh)

cdef extract_via(ViaGeometry via):
    top = hex(via.topMaskNum)[2:]
    cut = hex(via.cutMaskNum)[2:]
    bot = hex(via.bottomMaskNum)[2:]

    return {
        'pt': (via.x, via.y),
        'name': via.name.decode('ascii'),
        'mask': top+cut+bot
    }

cdef extract_iterate(IterableGeometry iterable):
    return {
        'num_x': iterable.xStart,
        'num_y': iterable.yStart,
        'step_x': iterable.xStep,
        'step_y': iterable.yStep
    }

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
            cur_geometry['shapes'].append({
                'path': extract_points(path),
                'mask': path.colorMask,
            })
        elif geo_type == lefiGeomPathIterE:
            pathiter = geos.getPathIter(i)
            cur_geometry['shapes'].append({
                'path': extract_points(pathiter),
                'mask': pathiter.colorMask,
                'iterate': extract_iterate(pathiter)
            })
        elif geo_type == lefiGeomRectE:
            rect = geos.getRect(i)
            cur_geometry['shapes'].append({
                'rect': extract_rect(rect),
                'mask':  rect.colorMask,
            })
        elif geo_type == lefiGeomRectIterE:
            rectiter = geos.getRectIter(i)
            cur_geometry['shapes'].append({
                'rect': extract_rect(rectiter),
                'mask': rectiter.colorMask,
                'iterate': extract_iterate(rectiter)
            })
        elif geo_type == lefiGeomPolygonE:
            poly = geos.getPolygon(i)
            cur_geometry['shapes'].append({
                'polygon': extract_points(poly),
                'mask': poly.colorMask
            })
        elif geo_type == lefiGeomPolygonIterE:
            polyiter = geos.getPolygonIter(i)
            cur_geometry['shapes'].append({
                'polygon': extract_points(polyiter),
                'mask': polyiter.colorMask,
                'iterate': extract_iterate(polyiter)
            })
        elif geo_type == lefiGeomViaE:
            via = geos.getVia(i)
            cur_geometry['via'] = extract_via(via)
        elif geo_type == lefiGeomViaIterE:
            viaiter = geos.getViaIter(i)
            cur_geometry['via'] = extract_via(viaiter)
            cur_geometry['via']['iterate'] = extract_iterate(viaiter)

    if cur_geometry != {}:
        geometries.append(cur_geometry)

    return geometries

cdef int macro_cb(lefrCallbackType_e cb_type, lefiMacro* macro, void* data):
    try:
        if macro.hasSize():
            _state.data['macros'][_state.cur_macro]['size'] = {
                'width': macro.sizeX(),
                'height': macro.sizeY()
            }
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int viarule_cb(lefrCallbackType_e cb_type, lefiViaRule* viarule, void* data):
    try:
        if 'viarules' not in _state.data:
            _state.data['viarules'] = {}

        viarule_data = {}
        if viarule.hasDefault():
            viarule_data['default'] = True
        if viarule.hasGenerate():
            viarule_data['generate'] = True

        layers = []
        for i in range(viarule.numLayers()):
            layer = viarule.layer(i)
            layer_data = {'name': layer.name().decode('ascii')}
            # nongenerate only
            if layer.hasDirection():
                layer_data['direction'] = 'HORZIONTAL' if layer.isHorizontal() else 'VERTICAL'
            # generate only
            if layer.hasEnclosure():
                layer_data['enclosure'] = {
                    'overhang1': layer.enclosureOverhang1(),
                    'overhang2': layer.enclosureOverhang2()
                }
            if layer.hasRect():
                layer_data['rect'] = (layer.xl(), layer.yl(), layer.xl(), layer.xh())
            if layer.hasSpacing():
                layer_data['spacing'] = {
                    'x': layer.spacingStepX(),
                    'y': layer.spacingStepY()
                }
            if layer.hasResistance():
                layer_data['resistance'] = layer.resistance()

            # nongenerate and generate
            if layer.hasWidth():
                layer_data['width'] = {
                    'min': layer.widthMin(),
                    'max': layer.widthMax()
                }

            layers.append(layer_data)

        vias = []
        for i in range(viarule.numVias()):
            vias.append(viarule.viaName(i).decode('ascii'))

        if len(layers) > 0:
            viarule_data['layers'] = layers
        if len(vias) > 0:
            viarule_data['vias'] = vias

        name = viarule.name().decode('ascii')
        _state.data['viarules'][name] = viarule_data
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int use_min_spacing_cb(lefrCallbackType_e cb_type, lefiUseMinSpacing* minspacing, lefiUserData data):
    try:
        if 'useminspacing' not in _state.data:
            _state.data['useminspacing'] = {}

        # I think this should always be 'OBS', but read from the object just to be flexible. 
        name = minspacing.name().decode('ascii')
        if minspacing.value() == 1:
            val = 'ON'
        else:
            val = 'OFF'

        _state.data['useminspacing'][name] = val
    except Exception:
        traceback.print_exc()
        return 1
    return 0

# The single wrapper function we expose
def parse(path):
    ''' See leflib/__init__.py for full docstring. We put it there to ensure
    it's picked up by Sphinx.'''

    _state.clear()

    if lefrInit() != 0:
        return None

    lefrSetUnitsCbk(units_cb)
    lefrSetVersionCbk(double_cb)
    lefrSetDividerCharCbk(divider_chars_cb)
    lefrSetBusBitCharsCbk(busbit_chars_cb)
    lefrSetLayerCbk(layer_cb)
    lefrSetSiteCbk(site_cb)
    lefrSetMacroBeginCbk(macro_begin_cb)
    lefrSetMacroCbk(macro_cb)
    lefrSetPinCbk(pin_cb)
    lefrSetObstructionCbk(obs_cb)
    lefrSetClearanceMeasureCbk(clearance_measure_cb)
    lefrSetManufacturingCbk(double_cb)
    lefrSetViaRuleCbk(viarule_cb)
    lefrSetMaxStackViaCbk(max_via_stack_cb)
    lefrSetFixedMaskCbk(fixed_mask_cb)
    lefrSetUseMinSpacingCbk(use_min_spacing_cb)

    # Use this to pass path to C++ functions
    path_bytes = path.encode('ascii')

    f_ptr = fopen(path_bytes, 'r')
    if f_ptr == NULL:
        print("Couldn't open file " + path)
        return None

    r = lefrRead(f_ptr, path_bytes, NULL)

    fclose(f_ptr)

    if r != 0:
        print("Error parsing LEF!")
        return None

    return _state.data
