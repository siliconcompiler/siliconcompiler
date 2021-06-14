def get_import_info(chip):
    importstep = ['import'] # standard verilog import just runs Verilator
    importvendor = 'verilator'

    if chip.get('sv')[-1] == 'true':
        if chip.get('ir')[-1] == 'uhdm':
            # UHDM import only runs SureLog in UHDM mode
            importstep = ['import']
            importvendor = 'surelog'
        else:
            # Verilog SV import runs SureLog to validate SV and then sv2v to convert
            # Since sv2v's parser is not strict we first parse using SureLog to ensure
            # that the input SV is valid. Compiling invalid SV using sv2v may result
            # in valid but buggy Verilog code, which we want to avoid.
            importstep = ['validate', 'import']
            importvendor = 'sv2v'
    return importstep, importvendor
