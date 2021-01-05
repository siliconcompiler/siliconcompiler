# Read liberty files
foreach lib $sc_lib {
    read_liberty $lib
}

# Read library lefs
foreach lef $sc_lef {
    read_lef $lef
}

#if [file exists $::env(PLATFORM_DIR)/derate.tcl] {
#  source $::env(PLATFORM_DIR)/derate.tcl
#}
#
#if [file exists $::env(PLATFORM_DIR)/setRC.tcl] {
#  source $::env(PLATFORM_DIR)/setRC.tcl
#}
