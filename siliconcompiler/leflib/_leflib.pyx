# These imports let us use libc file I/O to communicate with C++ lef library
from libc.stdio cimport FILE, fopen, fclose

ctypedef int (*lefrDoubleCbkFnType)(lefrCallbackType_e typ, double number, void* data)

# Must "forward declare" everything we reference from lefrReader.hpp here
cdef extern from "lefrReader.hpp":
    int lefrInit()
    int lefrRead()
    int lefrRead (FILE *file, const char *fileName, void* userData)
    void lefrSetVersionCbk(lefrDoubleCbkFnType cbk)
    ctypedef enum lefrCallbackType_e:
       lefrUnspecifiedCbkType,
       lefrVersionCbkType,
       lefrVersionStrCbkType,
       lefrDividerCharCbkType,
       lefrBusBitCharsCbkType,
       lefrUnitsCbkType,
       lefrCaseSensitiveCbkType,
       lefrNoWireExtensionCbkType,
       lefrPropBeginCbkType,
       lefrPropCbkType,
       lefrPropEndCbkType,
       lefrLayerCbkType,
       lefrViaCbkType,
       lefrViaRuleCbkType,
       lefrSpacingCbkType,
       lefrIRDropCbkType,
       lefrDielectricCbkType,
       lefrMinFeatureCbkType,
       lefrNonDefaultCbkType,
       lefrSiteCbkType,
       lefrMacroBeginCbkType,
       lefrPinCbkType,
       lefrMacroCbkType,
       lefrObstructionCbkType,
       lefrArrayCbkType,
       lefrSpacingBeginCbkType,
       lefrSpacingEndCbkType,
       lefrArrayBeginCbkType,
       lefrArrayEndCbkType,
       lefrIRDropBeginCbkType,
       lefrIRDropEndCbkType,
       lefrNoiseMarginCbkType,
       lefrEdgeRateThreshold1CbkType,
       lefrEdgeRateThreshold2CbkType,
       lefrEdgeRateScaleFactorCbkType,
       lefrNoiseTableCbkType,
       lefrCorrectionTableCbkType,
       lefrInputAntennaCbkType,
       lefrOutputAntennaCbkType,
       lefrInoutAntennaCbkType,
       lefrAntennaInputCbkType,
       lefrAntennaInoutCbkType,
       lefrAntennaOutputCbkType,
       lefrManufacturingCbkType,
       lefrUseMinSpacingCbkType,
       lefrClearanceMeasureCbkType,
       lefrTimingCbkType,
       lefrMacroClassTypeCbkType,
       lefrMacroOriginCbkType,
       lefrMacroSizeCbkType,
       lefrMacroFixedMaskCbkType,
       lefrMacroEndCbkType,
       lefrMaxStackViaCbkType,
       lefrExtensionCbkType,
       lefrDensityCbkType,
       lefrFixedMaskCbkType,
       lefrMacroSiteCbkType,
       lefrMacroForeignCbkType,
       lefrLibraryEndCbkType

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
