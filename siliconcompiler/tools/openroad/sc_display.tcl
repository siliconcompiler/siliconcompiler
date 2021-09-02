###############################
# Reading SC Manifest
###############################

source ./sc_manifest.tcl

###############################
# Manifest adapter
###############################

set sc_step        [dict get $sc_cfg arg step]
set sc_design      [dict get $sc_cfg design]
set sc_targetlibs  [dict get $sc_cfg asic targetlib]
set sc_mainlib     [lindex [dict get $sc_cfg asic targetlib] 0]
set sc_libtype     [dict get $sc_cfg stdcell $sc_mainlib libtype]
set sc_stackup     [dict get $sc_cfg asic stackup]
set sc_techlef     [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libtype lef]

###############################
# Read LEF/DEF
###############################


# read technolgoy lef
read_lef $sc_techlef

# must load stdcells lib
foreach lib $sc_targetlibs {
    read_lef [dict get $sc_cfg stdcell $lib lef]
}

# conditional load of macro libs
if {[dict exists $sc_cfg asic macrolib]} {
    foreach lib [dict exists $sc_cfg asic macrolib] {
	read_lef [dict get $sc_cfg macro $lib lef]
    }
}

# read def
read_def "outputs/$sc_design.def"
