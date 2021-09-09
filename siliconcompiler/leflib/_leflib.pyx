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

cdef int macro_cb(lefrCallbackType_e cb_type, lefiMacro* m, void* data):
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
