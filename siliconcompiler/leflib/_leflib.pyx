'''
This module implements a Python wrapper of the Si2 C++ LEF parser. It's written
using the Cython extensions for Python, which allows it to interface directly
with the C++ LEF parser. Although this file looks for the most part like
standard Python, it contains several Cython-specific constructs, and Cython
converts it into a generated C++ file before compiling it, so this code is not
interpreted as Python usually is.

The overall structure of this wrapper is as follows: it exposes a single
top-level Python function, `parse`, which takes in a path to a LEF file, and
returns the data contained in this LEF file in the form of a dictionary (see the
docstring for parse() in __init__.py for more information about the API from a
user-facing perspective). The underlying C++ LEF parser's API is designed around
a collection of callbacks that get invoked every time the parser encounters a
particular entry in the LEF file. These callbacks receive the relevant data for
that particular entry. This wrapper defines a series of callback functions that
take this data and put it into a global object, `_state`, and after parsing is
complete the data stored in `_state` is returned to the user.

The main special Cython constructs used in this file is the `cdef` function
declaration, which we use to define callbacks for the C++ parser. The main
difference between `cdef` and regular Python functions are function declarations
starting with cdef have C-like static type signatures. With these functions,
Cython converts transparently between C primitive types and Python equivalents,
while the interfaces to more complex objects are specified in _leflib.pxd
(another Cython-specific filetype, which can be thought as the Cython analogue
to a C/C++header file).

Other Cython-specific things are documented inline throughout the code.

Some pitfalls to be aware of when writing Cython code:
- Although we receive pointers to objects in all our callbacks, we can just call
  methods on these directly using standard `.` notation, which Cython will
  automatically convert to `->` behind the scenes. Cython does have a `deref`
  operator for dereferencing pointers (equivalent to `*`), but if you're not
  careful then using `deref` can result in memory errors. In paricular, we ran
  into trouble with using `deref` on the RHS side of assignments in our callback
  functions. When the object that stores the value of the dereferenced pointer
  goes out of scope after the function returns, the object's destructor would
  get called, which would then free some memory and cause double frees when the
  C++ parser library attempted to free the same memory internally later on.
- Control structures like if/else don't create their own scope in Python! They
  do in C/C++, but remember that this code is all semantically equivalent to
  Python.
- `char*` types get converted to Python "bytes" objects instead of Python
  strings. We use `.decode('ascii')` to convert the bytes to strings.

Helpful resources:
- Cython docs: https://cython.readthedocs.io/en/latest/
- LEF standard: http://coriolis.lip6.fr/doc/lefdef/lefdefref/lefdefref.pdf
- LEF API docs: http://coriolis.lip6.fr/doc/lefdef/lefapi/lefapi.pdf
'''

# This let us use libc file I/O to communicate with the C++ lef library.
from libc.stdio cimport fopen, fclose

# This imports the type/function declarations found in _leflib.pxd.
cimport _leflib

import cython
import traceback

# These are definitions of some custom Cython "fused types". An instance of a
# fused type can be any one of the types listed in the definition.  For example,
# an instance of `RectGeometry` (as defined below) could be a pointer to a
# `lefiGeomRect or a `lefiGeomRectIter`. All of the types grouped together have
# some common interface, and using the fused types lets us make a single
# function that can deal with all of them (similar to Python's duck-typing, but
# implemented using C++ templates under the hood). In particular, these fused
# types enable us to use generic helper functions to simplify layer geometry
# extraction.
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

# We hold parsed LEF data in a global that gets cleared by parse() on each call.
# The intended use of the LEF parser library is to pass around this data
# structure via the void* passed into each callback, but using a global lets us
# avoid having to deal with raw pointers to Python objects.
class ParserState:
    def __init__(self):
        self.clear()

    def clear(self):
        self.data = {}
        self.cur_macro = None

_state = ParserState()

# Callback functions passed to LEF parser library. The callbacks are defined in
# the order that the corresponding statements are expected to appear in a LEF
# file, as documented in the LEF standard page 12.
#
# Note that each of these functions contains the block:
# try:
#    ...
# except Exception:
#    traceback.print_exc()
#    return 1
# return 0
#
# This ensures that if any sort of Python exception occurs during the callback,
# it is handled gracefully by printing out the error and returning an error code
# to the LEF parser, which will terminate parsing early and cause lefrRead() to
# return an error code downstream.
cdef int version_cb(lefrCallbackType_e cb_type, double value, lefiUserData data):
    try:
        _state.data['version'] = value
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

cdef int divider_chars_cb(lefrCallbackType_e cb_type, const char* val, lefiUserData data):
    try:
        _state.data['dividerchar'] = val.decode('ascii')
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

cdef int manufacturing_grid_cb(lefrCallbackType_e cb_type, double value, lefiUserData data):
    try:
        _state.data['manufacturinggrid'] = value
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int use_min_spacing_cb(lefrCallbackType_e cb_type, lefiUseMinSpacing* minspacing, lefiUserData data):
    try:
        if 'useminspacing' not in _state.data:
            _state.data['useminspacing'] = {}

        # I think this should always be 'OBS', but read from the object just to
        # be flexible.
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

cdef int clearance_measure_cb(lefrCallbackType_e cb_type, const char* val, lefiUserData data):
    try:
        _state.data['clearancemeasure'] = val.decode('ascii')
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int fixed_mask_cb(lefrCallbackType_e cb_type, int val, lefiUserData data):
    try:
        # I think val should always be 1.
        _state.data['fixedmask'] = True if val == 1 else False
    except Exception:
        traceback.print_exc()
        return 1
    return 0

cdef int layer_cb(lefrCallbackType_e cb_type, lefiLayer* layer, lefiUserData data):
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
                layer_data['direction'] = 'HORIZONTAL' if layer.isHorizontal() else 'VERTICAL'
            # generate only
            if layer.hasEnclosure():
                layer_data['enclosure'] = {
                    'overhang1': layer.enclosureOverhang1(),
                    'overhang2': layer.enclosureOverhang2()
                }
            if layer.hasRect():
                layer_data['rect'] = (layer.xl(), layer.yl(), layer.xh(), layer.xh())
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

# Macro information is passed in through several different callbacks. First,
# `macro_begin_cb` is called to start a new "macro session", so we just store
# the name of the current macro in `_state.cur_macro` here.  `pin_cb` and
# `obs_cb` are then called for each PIN and OBS statement in the current macro,
# and finally `macro_cb` is called with the remaining information for the
# current macro.
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

            # The CLASS of a port is stored in its list of items, so search for
            # that here.
            for j in range(port.numItems()):
                if port.itemType(j) == lefiGeomClassE:
                    port_data['class'] = port.getClass(j).decode('ascii')

            # Otherwise, the other port "items" all refer to layerGeometries,
            # which are shared by several other types of things, so we extract
            # them using a separate helper function.
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

        # Append geometries even if empty so that the dictionary reflects how
        # many OBS appear in the LEF (even if they're empty).
        _state.data['macros'][_state.cur_macro]['obs'].append(geometries)
    except Exception:
        traceback.print_exc()
        return 1
    return 0

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

# The following functions are used to extract generic objects that are used in
# several contexts by the LEF parser into Python lists or dictionaries.
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
    '''Extracts layer geometries used for defining pin ports and obs geometries.

    See "Layer Geometries" in the LEF standard page 130.
    '''
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

# Additional callback for logging warnings/errors.
cdef void log(const char* msg):
    print(msg.decode('ascii'))

# This is the module's main entry point and the single Python function exposed
# by this module.
def parse(path):
    ''' See leflib/__init__.py for full docstring. We put it there to ensure
    it's picked up by Sphinx.'''

    _state.clear()

    if lefrInit() != 0:
        return None

    lefrSetVersionCbk(version_cb)
    lefrSetBusBitCharsCbk(busbit_chars_cb)
    lefrSetDividerCharCbk(divider_chars_cb)
    lefrSetUnitsCbk(units_cb)
    lefrSetManufacturingCbk(manufacturing_grid_cb)
    lefrSetUseMinSpacingCbk(use_min_spacing_cb)
    lefrSetClearanceMeasureCbk(clearance_measure_cb)
    lefrSetFixedMaskCbk(fixed_mask_cb)
    lefrSetLayerCbk(layer_cb)
    lefrSetMaxStackViaCbk(max_via_stack_cb)
    lefrSetViaRuleCbk(viarule_cb)
    lefrSetSiteCbk(site_cb)
    lefrSetMacroBeginCbk(macro_begin_cb)
    lefrSetPinCbk(pin_cb)
    lefrSetObstructionCbk(obs_cb)
    lefrSetMacroCbk(macro_cb)

    lefrSetLogFunction(log)
    lefrSetWarningLogFunction(log)

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
