# These imports let us use libc file I/O to communicate with C++ lef library
from libc.stdio cimport fopen, fclose

from cython.operator import dereference as deref

cimport _leflib

# Hold parsed LEF data in a global that gets cleared by parse() on each call.
# The intended use of the LEF parser library is to pass around this data
# structure via the void* passed into each callback, but this lets us avoid
# having to deal with raw pointers to Python objects.
# TODO: we could maybe make things a bit cleaner by encapsulating this into a
# class, but probably no need for the additional complexity.
_data = {}

cdef int double_cb(lefrCallbackType_e cb_type, double value, lefiUserData data):
    global _data
    if cb_type == lefrManufacturingCbkType:
        _data['manufacturinggrid'] = value
    elif cb_type == lefrVersionCbkType:
        _data['version'] = value

cdef int units_cb(lefrCallbackType_e t, lefiUnits* unitsptr, lefiUserData data):
    global _data
    if 'units' not in _data:
        _data['units'] = {}
    
    cdef lefiUnits units = deref(unitsptr)
    if units.hasDatabase():
        _data['units']['database'] = units.databaseNumber()
    if units.hasCapacitance():
        _data['units']['capacitance'] = units.capacitance()
    if units.hasResistance():
        _data['units']['resistance'] = units.resistance()
    if units.hasTime():
        _data['units']['time'] = units.time()
    if units.hasPower():
        _data['units']['power'] = units.power()
    if units.hasCurrent():
        _data['units']['current'] = units.current()
    if units.hasVoltage():
        _data['units']['voltage'] = units.voltage()
    if units.hasFrequency():
        _data['units']['frequency'] = units.frequency()

    return 0

cdef int layer_cb(lefrCallbackType_e cb_type, lefiLayer* layer_ptr, void* data):
    global _data
    if 'layers' not in _data:
        _data['layers'] = {}

    cdef lefiLayer layer = deref(layer_ptr)
    name = layer.name().decode('ascii')
    _data['layers'][name] = {}
    
    if layer.hasType():
        _data['layers'][name]['type'] = layer.type().decode('ascii')
    if layer.hasPitch():
        _data['layers'][name]['pitch'] = layer.pitch()
    if layer.hasXYPitch():
        _data['layers'][name]['pitch'] = (layer.pitchX(), layer.pitchY())
    if layer.hasOffset():
        _data['layers'][name]['offset'] = layer.offset()
    if layer.hasXYOffset():
        _data['layers'][name]['offset'] = (layer.offsetX(), layer.offsetY())
    if layer.hasWidth():
        _data['layers'][name]['width'] = layer.width()
    if layer.hasArea():
        _data['layers'][name]['area'] = layer.area()
    if layer.hasDirection():
        _data['layers'][name]['direction'] = layer.direction().decode()

    return 0

cdef int macro_cb(lefrCallbackType_e cb_type, lefiMacro* m, void* data):
    # TODO: for some reason assigning deref(m) with a cdef results in double
    # free() error, so we have to just call functions directly on deref'd one.

    global _data
    if 'macros' not in _data:
        _data['macros'] = {}

    name = deref(m).name().decode('ascii')
    _data['macros'][name] = {}
   
    if deref(m).hasSize():
        _data['macros'][name]['size'] = {
            'width': deref(m).sizeX(),
            'height': deref(m).sizeY()
        }

    return 0

# The single wrapper function we expose
def parse(path):
    global _data
    _data = {}
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

    return _data
