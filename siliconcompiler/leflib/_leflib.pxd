from libc.stdio cimport FILE

ctypedef void* lefiUserData

# A declaration of the signature of all callbacks that return nothing. 
ctypedef int (*lefrVoidCbkFnType) (lefrCallbackType_e, 
                                  void* num, 
                                  lefiUserData);

# A declaration of the signature of all callbacks that return a string. 
ctypedef int (*lefrStringCbkFnType) (lefrCallbackType_e, 
                                    const char *string, 
                                    lefiUserData);
 
# A declaration of the signature of all callbacks that return a integer. 
ctypedef int (*lefrIntegerCbkFnType) (lefrCallbackType_e, 
                                     int number, 
                                     lefiUserData);
 
# A declaration of the signature of all callbacks that return a double. 
ctypedef int (*lefrDoubleCbkFnType) (lefrCallbackType_e, 
                                    double number, 
                                    lefiUserData);

# A declaration of the signature of all callbacks that return a lefiUnits. 
ctypedef int (*lefrUnitsCbkFnType) (lefrCallbackType_e, 
                                   lefiUnits* units, 
                                   lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiLayer. 
# ctypedef int (*lefrLayerCbkFnType) (lefrCallbackType_e, 
                                   # lefiLayer* l, 
                                   # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiVia. 
# ctypedef int (*lefrViaCbkFnType) (lefrCallbackType_e, 
                                 # lefiVia* l, 
                                 # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiViaRule. 
# ctypedef int (*lefrViaRuleCbkFnType) (lefrCallbackType_e, 
                                     # lefiViaRule* l, 
                                     # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiSpacing. 
# ctypedef int (*lefrSpacingCbkFnType) (lefrCallbackType_e, 
                                     # lefiSpacing* l, 
                                     # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiIRDrop. 
# ctypedef int (*lefrIRDropCbkFnType) (lefrCallbackType_e, 
                                    # lefiIRDrop* l, 
                                    # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiMinFeature. 
# ctypedef int (*lefrMinFeatureCbkFnType) (lefrCallbackType_e, 
                                        # lefiMinFeature* l, 
                                        # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiNonDefault. 
# ctypedef int (*lefrNonDefaultCbkFnType) (lefrCallbackType_e, 
                                        # lefiNonDefault* l, 
                                        # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiSite. 
# ctypedef int (*lefrSiteCbkFnType) (lefrCallbackType_e, 
                                  # lefiSite* l, 
                                  # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiMacro. 
# ctypedef int (*lefrMacroCbkFnType) (lefrCallbackType_e, 
                                   # lefiMacro* l, 
                                   # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiPin. 
# ctypedef int (*lefrPinCbkFnType) (lefrCallbackType_e, 
                                 # lefiPin* l, 
                                 # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiObstruction. 
# ctypedef int (*lefrObstructionCbkFnType) (lefrCallbackType_e, 
                                         # lefiObstruction* l, 
                                         # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiArray. 
# ctypedef int (*lefrArrayCbkFnType) (lefrCallbackType_e, 
                                   # lefiArray* l, 
                                   # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiProp. 
# ctypedef int (*lefrPropCbkFnType) (lefrCallbackType_e, 
                                  # lefiProp* p, 
                                  # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiNoiseMargin. 
# ctypedef int (*lefrNoiseMarginCbkFnType) (lefrCallbackType_e, 
                                         # struct lefiNoiseMargin* p, 
                                         # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiNoiseTable. 
# ctypedef int (*lefrNoiseTableCbkFnType) (lefrCallbackType_e, 
                                        # lefiNoiseTable* p, 
                                        # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiCorrectionTable. 
# ctypedef int (*lefrCorrectionTableCbkFnType) (lefrCallbackType_e, 
                                             # lefiCorrectionTable* p, 
                                             # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiTiming. 
# ctypedef int (*lefrTimingCbkFnType) (lefrCallbackType_e, 
                                    # lefiTiming* p, 
                                    # lefiUserData);
 
# # A declaration of the signature of all callbacks that return a lefiUseMinSpacing. 
# ctypedef int (*lefrUseMinSpacingCbkFnType) (lefrCallbackType_e, 
                                           # lefiUseMinSpacing* l, 
                                           # lefiUserData);
 
  # # NEW CALLBACK - If your callback returns a pointer to a new class then
  # # you must add a type function here.

# # A declaration of the signature of all callbacks that return a lefiMaxStackVia. 
# ctypedef int (*lefrMaxStackViaCbkFnType) (lefrCallbackType_e, 
                                         # lefiMaxStackVia* l, 
                                         # lefiUserData);

# ctypedef int (*lefrMacroNumCbkFnType) (lefrCallbackType_e, 
                                      # lefiNum l, 
                                      # lefiUserData);

# ctypedef int (*lefrMacroSiteCbkFnType) (lefrCallbackType_e, 
                                      # const lefiMacroSite *site,
                                      # lefiUserData);

# ctypedef int (*lefrMacroForeignCbkFnType) (lefrCallbackType_e, 
                                          # const lefiMacroForeign *foreign,
                                          # lefiUserData);

# # 5.6 
# # A declaration of the signature of all callbacks that return a lefiDensity. 
# ctypedef int (*lefrDensityCbkFnType) (lefrCallbackType_e, 
                                     # lefiDensity* l, 
                                     # lefiUserData);
# # Must "forward declare" everything we reference from lefrReader.hpp here
cdef extern from "lefrReader.hpp":
    int lefrInit()
    int lefrRead (FILE *file, const char *fileName, void* userData)

    # Callback setters
    void lefrSetUnitsCbk(lefrUnitsCbkFnType)
    void lefrSetVersionCbk(lefrDoubleCbkFnType)
    # void lefrSetVersionStrCbk(lefrStringCbkFnType)
    # void lefrSetDividerCharCbk(lefrStringCbkFnType)
    # void lefrSetBusBitCharsCbk(lefrStringCbkFnType)
    # void lefrSetNoWireExtensionCbk(lefrStringCbkFnType)
    # void lefrSetCaseSensitiveCbk(lefrIntegerCbkFnType)
    # void lefrSetPropBeginCbk(lefrVoidCbkFnType)
    # void lefrSetPropCbk(lefrPropCbkFnType)
    # void lefrSetPropEndCbk(lefrVoidCbkFnType)
    # void lefrSetLayerCbk(lefrLayerCbkFnType)
    # void lefrSetViaCbk(lefrViaCbkFnType)
    # void lefrSetViaRuleCbk(lefrViaRuleCbkFnType)
    # void lefrSetSpacingCbk(lefrSpacingCbkFnType)
    # void lefrSetIRDropCbk(lefrIRDropCbkFnType)
    # void lefrSetDielectricCbk(lefrDoubleCbkFnType)
    # void lefrSetMinFeatureCbk(lefrMinFeatureCbkFnType)
    # void lefrSetNonDefaultCbk(lefrNonDefaultCbkFnType)
    # void lefrSetSiteCbk(lefrSiteCbkFnType)
    # void lefrSetMacroBeginCbk(lefrStringCbkFnType)
    # void lefrSetPinCbk(lefrPinCbkFnType)
    # void lefrSetObstructionCbk(lefrObstructionCbkFnType)
    # void lefrSetArrayCbk(lefrArrayCbkFnType)
    # void lefrSetMacroCbk(lefrMacroCbkFnType)
    # void lefrSetLibraryEndCbk(lefrVoidCbkFnType)
    
    # void lefrSetTimingCbk(lefrTimingCbkFnType)
    # void lefrSetSpacingBeginCbk(lefrVoidCbkFnType)
    # void lefrSetSpacingEndCbk(lefrVoidCbkFnType)
    # void lefrSetArrayBeginCbk(lefrStringCbkFnType)
    # void lefrSetArrayEndCbk(lefrStringCbkFnType)
    # void lefrSetIRDropBeginCbk(lefrVoidCbkFnType)
    # void lefrSetIRDropEndCbk(lefrVoidCbkFnType)
    # void lefrSetNoiseMarginCbk(lefrNoiseMarginCbkFnType)
    # void lefrSetEdgeRateThreshold1Cbk(lefrDoubleCbkFnType)
    # void lefrSetEdgeRateThreshold2Cbk(lefrDoubleCbkFnType)
    # void lefrSetEdgeRateScaleFactorCbk(lefrDoubleCbkFnType)
    # void lefrSetNoiseTableCbk(lefrNoiseTableCbkFnType)
    # void lefrSetCorrectionTableCbk(lefrCorrectionTableCbkFnType)
    # void lefrSetInputAntennaCbk(lefrDoubleCbkFnType)
    # void lefrSetOutputAntennaCbk(lefrDoubleCbkFnType)
    # void lefrSetInoutAntennaCbk(lefrDoubleCbkFnType)
    # void lefrSetAntennaInputCbk(lefrDoubleCbkFnType)
    # void lefrSetAntennaInoutCbk(lefrDoubleCbkFnType)
    # void lefrSetAntennaOutputCbk(lefrDoubleCbkFnType)
    # void lefrSetClearanceMeasureCbk(lefrStringCbkFnType)
    # void lefrSetManufacturingCbk(lefrDoubleCbkFnType)
    # void lefrSetUseMinSpacingCbk(lefrUseMinSpacingCbkFnType)
    # void lefrSetMacroClassTypeCbk(lefrStringCbkFnType)
    # void lefrSetMacroOriginCbk(lefrMacroNumCbkFnType)
    # void lefrSetMacroSiteCbk(lefrMacroSiteCbkFnType)
    # void lefrSetMacroForeignCbk(lefrMacroForeignCbkFnType)
    # void lefrSetMacroSizeCbk(lefrMacroNumCbkFnType)
    # void lefrSetMacroFixedMaskCbk(lefrIntegerCbkFnType)
    # void lefrSetMacroEndCbk(lefrStringCbkFnType)
    # void lefrSetMaxStackViaCbk(lefrMaxStackViaCbkFnType)
    # void lefrSetExtensionCbk(lefrStringCbkFnType)
    # void lefrSetDensityCbk(lefrDensityCbkFnType)
    # void lefrSetFixedMaskCbk(lefrIntegerCbkFnType)

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

    cdef cppclass lefiDensity:
        int numLayer()
        char* layerName(int index)
        double densityValue(int index, int rectIndex)
