'''
This file contains declarations of all C/C++ types and functions defined in the
LEF parser that we need to interface with from Cython.

We need to declare all these things here since Cython is unable to parse the
header files directly. However, note that we don't need to redeclare everything,
or each member of an object we want to use. Instead, we just need to declare
everything we actually use by name in Cython.

In general, the contents of this file have been copy-pasted directly from the
LEF parser library (and cleaned up as needed).
'''

from libc.stdio cimport FILE

# lefiUserData used in each callback is just defined by the LEF parser as a
# `#define` macro for void*.
ctypedef void* lefiUserData

# These typedefs define the function signatures of each LEF parser callback.
# (Order same as in lefrReader.hpp)
ctypedef int (*lefrVoidCbkFnType) (lefrCallbackType_e,
                                  void* num,
                                  lefiUserData);
ctypedef int (*lefrStringCbkFnType) (lefrCallbackType_e,
                                    const char *string,
                                    lefiUserData);
ctypedef int (*lefrIntegerCbkFnType) (lefrCallbackType_e,
                                     int number,
                                     lefiUserData);
ctypedef int (*lefrDoubleCbkFnType) (lefrCallbackType_e,
                                    double number,
                                    lefiUserData);
ctypedef int (*lefrUnitsCbkFnType) (lefrCallbackType_e,
                                   lefiUnits* units,
                                   lefiUserData);
ctypedef int (*lefrLayerCbkFnType) (lefrCallbackType_e,
                                   lefiLayer* l,
                                   lefiUserData);
ctypedef int (*lefrViaRuleCbkFnType) (lefrCallbackType_e,
                                     lefiViaRule* l,
                                     lefiUserData);
ctypedef int (*lefrSiteCbkFnType) (lefrCallbackType_e,
                                  lefiSite* l,
                                  lefiUserData);
ctypedef int (*lefrMacroCbkFnType) (lefrCallbackType_e,
                                   lefiMacro* l,
                                   lefiUserData);
ctypedef int (*lefrPinCbkFnType) (lefrCallbackType_e,
                                 lefiPin* l,
                                 lefiUserData);
ctypedef int (*lefrObstructionCbkFnType) (lefrCallbackType_e,
                                         lefiObstruction* l,
                                         lefiUserData);
ctypedef int (*lefrUseMinSpacingCbkFnType) (lefrCallbackType_e,
                                           lefiUseMinSpacing* l,
                                           lefiUserData);
ctypedef int (*lefrMaxStackViaCbkFnType) (lefrCallbackType_e,
                                         lefiMaxStackVia* l,
                                         lefiUserData);

ctypedef void (*LEFI_LOG_FUNCTION) (const char*);
ctypedef void (*LEFI_WARNING_LOG_FUNCTION) (const char*);

# Must declare everything we reference from lefrReader.hpp here
cdef extern from "lefrReader.hpp":
    int lefrInit()
    int lefrRead (FILE *file, const char *fileName, void* userData)

    # Callback setters
    void lefrSetVersionCbk(lefrDoubleCbkFnType)
    void lefrSetBusBitCharsCbk(lefrStringCbkFnType)
    void lefrSetDividerCharCbk(lefrStringCbkFnType)
    void lefrSetUnitsCbk(lefrUnitsCbkFnType)
    void lefrSetManufacturingCbk(lefrDoubleCbkFnType)
    void lefrSetUseMinSpacingCbk(lefrUseMinSpacingCbkFnType)
    void lefrSetClearanceMeasureCbk(lefrStringCbkFnType)
    void lefrSetFixedMaskCbk(lefrIntegerCbkFnType)
    void lefrSetLayerCbk(lefrLayerCbkFnType)
    void lefrSetMaxStackViaCbk(lefrMaxStackViaCbkFnType)
    void lefrSetViaRuleCbk(lefrViaRuleCbkFnType)
    void lefrSetSiteCbk(lefrSiteCbkFnType)
    void lefrSetMacroBeginCbk(lefrStringCbkFnType)
    void lefrSetPinCbk(lefrPinCbkFnType)
    void lefrSetObstructionCbk(lefrObstructionCbkFnType)
    void lefrSetMacroCbk(lefrMacroCbkFnType)

    # Additional callbacks
    void lefrSetLogFunction(LEFI_LOG_FUNCTION)
    void lefrSetWarningLogFunction(LEFI_WARNING_LOG_FUNCTION)

    # Some enums we need to reference
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

    cdef enum lefiGeomEnum:
        lefiGeomUnknown,
        lefiGeomLayerE,
        lefiGeomLayerExceptPgNetE,
        lefiGeomLayerMinSpacingE,
        lefiGeomLayerRuleWidthE,
        lefiGeomWidthE,
        lefiGeomPathE,
        lefiGeomPathIterE,
        lefiGeomRectE,
        lefiGeomRectIterE,
        lefiGeomPolygonE,
        lefiGeomPolygonIterE,
        lefiGeomViaE,
        lefiGeomViaIterE,
        lefiGeomClassE,
        lefiGeomEnd

    # Objects passed into callbacks
    cdef cppclass lefiUnits:
        int hasDatabase()
        int hasCapacitance()
        int hasResistance()
        int hasTime()
        int hasPower()
        int hasCurrent()
        int hasVoltage()
        int hasFrequency()
        double databaseNumber()
        double capacitance()
        double resistance()
        double time()
        double power()
        double current()
        double voltage()
        double frequency()

    cdef cppclass lefiUseMinSpacing:
        const char* name()
        int value()

    cdef cppclass lefiLayer:
        int hasType()
        int hasMask()
        int hasPitch()
        int hasXYPitch()
        int hasOffset()
        int hasXYOffset()
        int hasWidth()
        int hasArea()
        int hasDirection()

        char* name()
        const char* type()
        double pitch()
        int    mask()
        double pitchX()
        double pitchY()
        double offset()
        double offsetX()
        double offsetY()
        double width()
        double area()
        const char* direction()

    cdef cppclass lefiMaxStackVia:
        int maxStackVia()
        int hasMaxStackViaRange()
        const char* maxStackViaBottomLayer()
        const char* maxStackViaTopLayer()

    cdef cppclass lefiViaRule:
        int hasGenerate()
        int hasDefault()
        char* name()

        int numLayers()
        lefiViaRuleLayer* layer(int index)

        int numVias()
        char* viaName(int index)

        int numProps()
        const char*  propName(int index)
        const char*  propValue(int index)
        double propNumber(int index)
        char   propType(int index)
        int    propIsNumber(int index)
        int    propIsString(int index)

    cdef cppclass lefiViaRuleLayer:
        int hasDirection()
        int hasEnclosure()
        int hasWidth()
        int hasResistance()
        int hasOverhang()
        int hasMetalOverhang()
        int hasSpacing()
        int hasRect()

        char* name()
        int isHorizontal()
        int isVertical()
        double enclosureOverhang1()
        double enclosureOverhang2()
        double widthMin()
        double widthMax()
        double overhang()
        double metalOverhang()
        double resistance()
        double spacingStepX()
        double spacingStepY()
        double xl()
        double yl()
        double xh()
        double yh()

    cdef cppclass lefiSite:
        const char* name()
        int hasClass()
        const char* siteClass()
        double sizeX()
        double sizeY()
        int hasSize()
        int hasXSymmetry()
        int hasYSymmetry()
        int has90Symmetry()
        int hasRowPattern()
        int numSites()
        char* siteName(int index)
        int   siteOrient(int index)
        char* siteOrientStr(int index)

    cdef cppclass lefiMacro:
        int hasSize()

        const char* name()
        double sizeX()
        double sizeY()

    cdef cppclass lefiPin:
        const char* name()
        int numPorts()
        lefiGeometries* port(int index)

    cdef cppclass lefiObstruction:
        lefiGeometries* geometries()

    cdef cppclass lefiGeometries:
        int numItems()
        lefiGeomEnum itemType(int index)
        const char* getLayer(int index)
        double getLayerMinSpacing(int index)
        double getLayerRuleWidth(int index)
        double getWidth(int index)
        lefiGeomPath* getPath(int index)
        lefiGeomPathIter* getPathIter(int index)
        lefiGeomRect* getRect(int index)
        lefiGeomRectIter* getRectIter(int index)
        lefiGeomPolygon* getPolygon(int index)
        lefiGeomPolygonIter* getPolygonIter(int index)
        lefiGeomVia* getVia(int index)
        lefiGeomViaIter* getViaIter(int index)

        const char* getClass(int index)

    # Structs defining generic geometries
    cdef struct lefiGeomRect:
        double xl
        double yl
        double xh
        double yh
        int colorMask

    cdef struct lefiGeomRectIter:
        double xl
        double yl
        double xh
        double yh
        double xStart
        double yStart
        double xStep
        double yStep
        int    colorMask

    cdef struct lefiGeomPath:
        int numPoints
        double* x
        double* y
        int colorMask

    cdef struct lefiGeomPathIter:
        int numPoints
        double* x
        double* y
        double xStart
        double yStart
        double xStep
        double yStep
        int colorMask

    cdef struct lefiGeomPolygon:
        int numPoints
        double* x
        double* y
        int colorMask

    cdef struct lefiGeomPolygonIter:
        int numPoints
        double* x
        double* y
        double xStart
        double yStart
        double xStep
        double yStep
        int colorMask

    cdef struct lefiGeomVia:
        char* name
        double x
        double y
        int topMaskNum
        int cutMaskNum
        int bottomMaskNum

    cdef struct lefiGeomViaIter:
        char* name
        double x
        double y
        double xStart
        double yStart
        double xStep
        double yStep
        int topMaskNum
        int cutMaskNum
        int bottomMaskNum
