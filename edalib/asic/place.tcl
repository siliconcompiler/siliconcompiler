########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

source ./sc_setup.tcl

set scriptdir [file dirname [lindex $SC_PLACE_SCRIPT 0]]

source -verbose $scriptdir/sc_procedures.tcl

source -verbose $scriptdir/process.tcl

source -verbose $scriptdir/library.tcl

set jobid         [lindex $SC_FLOORPLAN_JOBID 0]
set topmodule     [lindex $SC_TOPMODULE 0]
set mainlib       [lindex $SC_LIB 0]

#Inputs
set input_verilog    "../../floorplan/job$jobid/$topmodule.v"
set input_sdc        "../../floorplan/job$jobid/$topmodule.sdc"
set input_def        "../../floorplan/job$jobid/$topmodule.def"

################################################################
# Read Inputs
################################################################

#Read data from previous stage
read_def $input_def

if {[file exists $input_sdc]} {
    read_sdc $input_sdc
}

################################################################
# Global Placement
################################################################

## What to put for density???
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
# Write Results
################################################################

sc_write_outputs $topmodule
