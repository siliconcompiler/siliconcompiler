# Read liberty files
foreach lib $SC_LIB {
    read_liberty $lib
}

# Read library lefs
foreach lef $SC_LEF {
    read_lef $lef
}

#if [file exists $::env(PLATFORM_DIR)/derate.tcl] {
#  source $::env(PLATFORM_DIR)/derate.tcl
#}
#
#if [file exists $::env(PLATFORM_DIR)/setRC.tcl] {
#  source $::env(PLATFORM_DIR)/setRC.tcl
#}
