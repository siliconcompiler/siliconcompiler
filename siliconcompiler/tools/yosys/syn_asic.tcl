

########################################################
# Read Macro Libraries
########################################################

#TODO: fix to handle multiple libraries
# (note that ABC and dfflibmap can only accept one library from Yosys, so
# for now everything needs to be concatenated into one library regardless)
if {$sc_process eq "skywater130"} {
    # TODO: hack, we use separate synth library for Skywater
    set library_file [dict get $sc_cfg stdcell $sc_mainlib model typical nldm lib_synth]
} else {
    set library_file [dict get $sc_cfg stdcell $sc_mainlib model typical nldm lib]
}

if {[dict exists $sc_cfg asic macrolib]} {
    set sc_macrolibs [dict get $sc_cfg asic macrolib]
} else {
    set sc_macrolibs  ""
}

# Read macro library files, and gather argument list to pass into stat later
# on (for area estimation).
set stat_libs ""
foreach libname $sc_macrolibs {
    set macro_lib [dict get $sc_cfg macro $libname model typical nldm lib]
    yosys read_liberty -lib $macro_lib
    append stat_libs "-liberty $macro_lib "
}

########################################################
# Synthesis
########################################################

yosys synth "-flatten" -top $sc_design

yosys opt -purge

########################################################
# Technology Mapping
########################################################

yosys dfflibmap -liberty $library_file

yosys opt

yosys abc -liberty $library_file

yosys stat -liberty $library_file {*}$stat_libs

########################################################
# Cleanup
########################################################

yosys setundef -zero

yosys splitnets

yosys clean
