# These imports let us use libc file I/O to communicate with C++ lef library
from libc.stdio cimport fopen, fclose

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

cdef int units_cb(lefrCallbackType_e t, lefiUnits* unitsptr, lefiUserData data):
    if 'units' not in _state.data:
        _state.data['units'] = {}
 
    cdef lefiUnits units = deref(unitsptr)
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

cdef int layer_cb(lefrCallbackType_e cb_type, lefiLayer* layer_ptr, void* data):
    if 'layers' not in _state.data:
        _state.data['layers'] = {}

    cdef lefiLayer layer = deref(layer_ptr)
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

cdef int macro_cb(lefrCallbackType_e cb_type, lefiMacro* m, void* data):
    # TODO: for some reason assigning deref(m) with a cdef results in double
    # free() error, so we have to just call functions directly on deref'd one.

    if 'macros' not in _state.data:
        _state.data['macros'] = {}

    name = deref(m).name().decode('ascii')
    _state.data['macros'][name] = {}

    if deref(m).hasSize():
        _state.data['macros'][name]['size'] = {
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
    lefrSetMacroCbk(macro_cb)
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
