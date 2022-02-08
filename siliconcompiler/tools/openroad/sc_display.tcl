###############################
# Reading SC Manifest
###############################

source ./sc_manifest.tcl

###############################
# Manifest adapter
###############################

set sc_mainlib     [lindex [dict get $sc_cfg asic logiclib] 0]
set sc_libtype     [dict get $sc_cfg library $sc_mainlib arch]
set sc_stackup     [dict get $sc_cfg asic stackup]
set sc_techlef     [dict get $sc_cfg pdk aprtech openroad $sc_stackup $sc_libtype lef]

###############################
# Generic LEF/DEF Reader
###############################

# read technolgoy lef
read_lef $sc_techlef

if {[dict exists $sc_cfg asic macrolib]} {
    set sc_macrolibs [dict get $sc_cfg asic macrolib]
} else {
    set sc_macrolibs    ""
}

if {[dict exists $sc_cfg asic logiclib]} {
    set sc_stdlibs [dict get $sc_cfg asic logiclib]
} else {
    set sc_stdlibs    ""
}

# reading stdlib
foreach lib $sc_stdlibs {
    read_lef [dict get $sc_cfg library $lib lef]
}

# reading macrolibs
foreach lib $sc_macrolibs {
    read_lef [dict get $sc_cfg library $lib lef]
}

# read def
read_def $::env(SC_FILENAME)
