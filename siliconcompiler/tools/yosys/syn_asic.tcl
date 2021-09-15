

########################################################
# Read Macro Libraries
########################################################
set sc_process     [dict get $sc_cfg pdk process]
set sc_mainlib     [lindex [dict get $sc_cfg asic targetlib] 0]
set sc_targetlibs  [dict get $sc_cfg asic targetlib]
set sc_tie         [dict get $sc_cfg library $sc_mainlib cells tie]
set sc_buf         [dict get $sc_cfg library $sc_mainlib cells buf]

#TODO: fix to handle multiple libraries
# (note that ABC and dfflibmap can only accept one library from Yosys, so
# for now everything needs to be concatenated into one library regardless)
set library_file [dict get $sc_cfg library $sc_mainlib nldm typical lib]

yosys read_liberty -lib $library_file

set sc_macrolibs [dict get $sc_cfg asic macrolib]

# Read macro library files, and gather argument list to pass into stat later
# on (for area estimation).
set stat_libs ""
foreach libname $sc_macrolibs {
    # TODO: we assume corner name is "typical" - this should probably be
    # documented somewhere?
    if {[dict exists $sc_cfg library $libname nldm]} {
        set macro_lib [dict get $sc_cfg library $libname nldm typical lib]
        yosys read_liberty -lib $macro_lib
        append stat_libs "-liberty $macro_lib "
    }
}

########################################################
# Synthesis
########################################################

yosys synth "-flatten" -top $sc_design

yosys opt -purge

########################################################
# Technology Mapping
########################################################

if {[dict exists $sc_cfg eda yosys $sc_step $sc_index option techmap]} {
    set sc_techmap [dict get $sc_cfg eda yosys $sc_step $sc_index option techmap]
} else {
    set sc_techmap ""
}

foreach mapfile $sc_techmap {
    yosys techmap -map $mapfile
}

yosys dfflibmap -liberty $library_file

yosys opt

yosys abc -liberty $library_file

yosys stat -liberty $library_file {*}$stat_libs

########################################################
# Cleanup
########################################################

yosys setundef -zero

if {[llength $sc_tie] == 2} {
    set sc_tiehi [split [lindex $sc_tie 0] /]
    set sc_tielo [split [lindex $sc_tie 1] /]

    yosys hilomap -hicell {*}$sc_tiehi -locell {*}$sc_tielo
}

if {[llength $sc_buf] == 1} {
    set sc_buf_split [split $sc_buf /]
    yosys insbuf -buf {*}$sc_buf_split
}

yosys splitnets

yosys clean
