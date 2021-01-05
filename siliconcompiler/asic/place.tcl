################################################################
# Setup
################################################################

#Get path to script
set scriptdir [file dirname [file normalize [info script]]]

#Souce the SC generated TCL file from the current working directory
source -verbose  ./sc_setup.tcl

#Set up process
source -verbose $scriptdir/process_setup.tcl

#Set up libraries
source -verbose $scriptdir/library_setup.tcl

#Souce the SC generated TCL file from the current working directory
source -verbose  ./sc_setup.tcl

################################################################
# Read Inputs
################################################################

#Read data from previous stage
read_def $sc_floorplan_dir/${top_module}$sc_floorplan_suffix.def
read_sdc $sc_floorplan_dir/${top_module}$sc_floorplan_suffix.sdc

################################################################
# Global Placement
################################################################

global_placement -disable_routability_driven -density 0.1 \
    -pad_left $::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT) \
    -pad_right $::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT)

################################################################
# Resize
################################################################

estimate_parasitics -placement

set buffer_cell [get_lib_cell [lindex $::env(MIN_BUF_CELL_AND_PORTS) 0]]

set_dont_use $::env(DONT_USE_CELLS)

set_max_fanout $::env(MAX_FANOUT) [current_design]

repair_design -max_wire_length $::env(MAX_WIRE_LENGTH) -buffer_cell $buffer_cell

set tie_separation $env(TIE_SEPARATION)

# Repair tie lo fanout
puts "Repair tie lo fanout..."
set tielo_cell_name [lindex $env(TIELO_CELL_AND_PORT) 0]
set tielo_lib_name [get_name [get_property [get_lib_cell $tielo_cell_name] library]]
set tielo_pin $tielo_lib_name/$tielo_cell_name/[lindex $env(TIELO_CELL_AND_PORT) 1]
repair_tie_fanout -separation $tie_separation $tielo_pin

# Repair tie hi fanout
puts "Repair tie hi fanout..."
set tiehi_cell_name [lindex $env(TIEHI_CELL_AND_PORT) 0]
set tiehi_lib_name [get_name [get_property [get_lib_cell $tiehi_cell_name] library]]
set tiehi_pin $tiehi_lib_name/$tiehi_cell_name/[lindex $env(TIEHI_CELL_AND_PORT) 1]
repair_tie_fanout -separation $tie_separation $tiehi_pin

################################################################
# Reporting
################################################################
report_tns
report_wns
report_design_area

################################################################
# Write Results
################################################################

write_def $sc_place_dir/${top_module}$sc_place_suffix.def

exit
