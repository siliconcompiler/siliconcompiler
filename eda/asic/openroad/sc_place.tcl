##############################################################
# SC SETUP
##############################################################

set stage      "place"
set last_stage "floorplan"

source ./sc_setup.tcl

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg tool $stage refdir]
if {[dict get $sc_cfg tool $stage copy] eq True} {
    set scriptdir "./"
}
# Sourcing helper procedures
source $scriptdir/sc_procedures.tcl

#Massaging dict into simple local variables
set stackup      [dict get $sc_cfg stackup]
set target_libs  [dict get $sc_cfg target_lib]
set mainlib      [lindex $target_libs 0]
set libarch      [dict get $sc_cfg stdcells $mainlib libtype]
set techlef      [dict get $sc_cfg pdk_aprtech $stackup $libarch openroad]
set topmodule    [dict get $sc_cfg design]
set corner       "typical"

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
    read_liberty [dict get $sc_cfg stdcells $lib model typical nldm lib]
    read_lef [dict get $sc_cfg stdcells $lib lef]
    set site [dict get $sc_cfg stdcells $lib site]
}

# Read Design
read_def $input_def

# Read SDC
if {[file exists $input_sdc]} {
    read_sdc $input_sdc
}

# Global Placement
global_placement -disable_routability_driven -density 0.3

#-disable_routability_driven -density $SC_DENSITY
#-pad_left $::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT) \
#-pad_right $::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT)

################################################################
# Resize
################################################################


#estimate_parasitics -placement

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

sc_write_reports $topmodule

################################################################
# Outputs (def,verilog,sdc)
################################################################

sc_write_outputs $topmodule
