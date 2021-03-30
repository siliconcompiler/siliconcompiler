##############################################################
# SC SETUP
##############################################################

set step      "place"
set last_step "floorplan"

source ./sc_setup.tcl

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg flow $step refdir]
if {[dict get $sc_cfg flow $step copy] eq True} {
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
# TODO: Put in config dictionary instead of hardcoding.
set corner       "typical"
set gp_density   0.3
set max_fanout   100
set max_wire_len 1000
set buf_lib_cell "BUF_X1 A Z"
set dont_use     "FILCELL_X1 AOI211_X1 OAI211_X1"
set parasitics_layer metal3

#Inputs
set input_verilog   "inputs/$topmodule.v"
set input_def       "inputs/$topmodule.def"
set input_sdc       "inputs/$topmodule.sdc"

#Outputs
set output_verilog  "outputs/$topmodule.v"
set output_def      "outputs/$topmodule.def"
set output_sdc      "outputs/$topmodule.sdc"

#Setup Process

read_lef  $techlef

#Setup Libs
foreach lib $target_libs {
    read_liberty [dict get $sc_cfg stdcell $lib model typical nldm lib]
    # Correct for polygonal pin sizes in nangate45 liberty.
    if  {$lib eq "NangateOpenCellLibrary"} {
        set target_lef [dict get $sc_cfg stdcell $lib lef]
        regsub -all {\.lef} $target_lef .mod.lef target_lef
        read_lef $target_lef
    } else {
        read_lef [dict get $sc_cfg stdcell $lib lef]
    }
    set site [dict get $sc_cfg stdcell $lib site]
}

# Read Design
read_def $input_def

# Read SDC
if {[file exists $input_sdc]} {
    read_sdc $input_sdc
}

# Global Placement
#global_placement -disable_routability_driven -density 0.3 -skip_initial_place
global_placement -disable_routability_driven -density $gp_density

#-disable_routability_driven -density $SC_DENSITY
#-pad_left $::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT) \
#-pad_right $::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT)

################################################################
# Resize
################################################################


set_wire_rc -layer $parasitics_layer
estimate_parasitics -placement

set buffer_cell [get_lib_cell [lindex $buf_lib_cell 0]]
set_dont_use $dont_use

set_max_fanout $max_fanout [current_design]
repair_design -max_wire_length $max_wire_len -buffer_cell $buffer_cell

# TODO: OpenROAD appears to perform detailed placement after the CTS step.
# Is that right? I thought that CTS at least needed a legalized design.
# Detail placement.
#set_placement_padding -global
    #-left $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) \
    #-right $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)
#detailed_placement
#optimize_mirroring
#check_placement -verbose

#set buffer_cell [get_lib_cell [lindex $::env(MIN_BUF_CELL_AND_PORTS) 0]]

#set_dont_use $::env(DONT_USE_CELLS)

#set_max_fanout $SC_MAXFANOUT [current_design]

#repair_design -max_wire_length $::env(MAX_WIRE_LENGTH) -buffer_cell $buffer_cell

#set tie_separation $env(TIE_SEPARATION)

# Repair tie lo fanout
#puts "Repair tie lo fanout..."
#set tielo_cell_name [lindex $env(TIELO_CELL_AND_PORT) 0]
#set tielo_lib_name [get_name [get_property [get_lib_cell $tielo_cell_name] library]]
#set tielo_pin $tielo_lib_name/$tielo_cell_name/[lindex $env(TIELO_CELL_AND_PORT) 1]
#repair_tie_fanout -separation $tie_separation $tielo_pin

# Repair tie hi fanout
#puts "Repair tie hi fanout..."
#set tiehi_cell_name [lindex $env(TIEHI_CELL_AND_PORT) 0]
#set tiehi_lib_name [get_name [get_property [get_lib_cell $tiehi_cell_name] library]]
#set tiehi_pin $tiehi_lib_name/$tiehi_cell_name/[lindex $env(TIEHI_CELL_AND_PORT) 1]
#repair_tie_fanout -separation $tie_separation $tiehi_pin

################################################################
# Reporting
################################################################

report_tns
report_wns
report_design_area

################################################################
# Outputs (def,verilog,sdc)
################################################################

write_def     "outputs/$topmodule.def"
write_verilog "outputs/$topmodule.v"
write_sdc     "outputs/$topmodule.sdc"

