##############################
# Setup debugging
###############################

source "$sc_refdir/common/debugging.tcl"

###############################
# Setup helper functions
###############################

source "$sc_refdir/common/procs.tcl"

###############################
# Setup report directories
###############################

file mkdir \
    reports/checks \
    reports/clocks \
    reports/constraints \
    reports/design \
    reports/markers \
    reports/power \
    reports/route \
    reports/setup \
    reports/timing

###############################
# Design information
###############################

# Design
set sc_mainlib [sc_cfg_get asic mainlib]
set sc_optmode [sc_cfg_get option optmode]
set sc_pdk [sc_cfg_get asic pdk]

# APR Parameters
set sc_logiclibs [sc_cfg_get asic asiclib]
set sc_delaymodel [sc_cfg_get asic delaymodel]

###############################
# Read Files
###############################

source "$sc_refdir/common/read_liberty.tcl"

# Set before any design exists, since synthesis maps only to usable cells
sc_set_dont_use
