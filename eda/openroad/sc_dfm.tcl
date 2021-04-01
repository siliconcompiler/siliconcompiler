########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

# (Currently a nop script)

set stage      "dfm"
set last_stage "route"

source ./sc_setup.tcl

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg flow $stage refdir]
if {[dict get $sc_cfg flow $stage copy] eq True} {
    set scriptdir "./"
}
# Sourcing helper procedures
source $scriptdir/sc_procedures.tcl

#Massaging dict into simple local variables
set stackup      [dict get $sc_cfg asic stackup]
set target_libs  [dict get $sc_cfg asic targetlib]
set mainlib      [lindex $target_libs 0]
set libarch      [dict get $sc_cfg stdcell $mainlib libtype]
set techlef      [dict get $sc_cfg pdk aprtech $stackup $libarch openroad]
set topmodule    [dict get $sc_cfg design]

#Inputs
set input_verilog   "inputs/$topmodule.v"
set input_def       "inputs/$topmodule.def"
set input_sdc       "inputs/$topmodule.sdc"

#Outputs
set output_verilog  "outputs/$topmodule.v"
set output_def      "outputs/$topmodule.def"
set output_sdc      "outputs/$topmodule.sdc"

################################################################
# Read Inputs
################################################################

# Setup process.
read_lef $techlef
# Setup libraries.
foreach lib $target_libs {
    read_liberty [dict get $sc_cfg stdcell $lib model typical nldm lib]
    read_lef [dict get $sc_cfg stdcell $lib lef]
    set site [dict get $sc_cfg stdcell $lib site]
}
# Read design.
read_def $input_def
# Read SDC.
read_sdc $input_sdc

################################################################
# DFM CORE SCRIPT
################################################################

################################################################
# Write Results
################################################################

#sc_write_outputs $topmodule
write_def $output_def
write_verilog $output_verilog
write_sdc $output_sdc
