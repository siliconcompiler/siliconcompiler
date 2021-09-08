# These imports let us use libc file I/O to communicate with C++ lef library
from libc.stdio cimport fopen, fclose

cimport _leflib

# Hold parsed LEF data in a global that gets cleared by parse() on each call.
# The intended use of the LEF parser library is to pass around this data
# structure via the void* passed into each callback, but this lets us avoid
# having to deal with raw pointers to Python objects.
# TODO: we could maybe make things a bit cleaner by encapsulating this into a
# class, but probably no need for the additional complexity.
_data = {}

cdef int version_cb(lefrCallbackType_e type, double number, void* data):
    global _data
    _data['version'] = number
    return 0

# The single wrapper function we expose
def parse(path):
    global _data
    _data = {}
    if lefrInit() != 0:
        return None

    lefrSetVersionCbk(version_cb)

    # Use this to pass path to C++ functions
    path_bytes = path.encode('ascii')

    f_ptr = fopen(path_bytes, 'r')
    if f_ptr == NULL:
        print("Couldn't open file " + path)
        return None

    r = lefrRead(f_ptr, path_bytes, NULL)

    fclose(f_ptr)

    return _data
