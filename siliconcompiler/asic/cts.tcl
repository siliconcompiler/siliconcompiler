################################################################
# Setup
################################################################

#Get path to script
set scriptdir [file dirname [file normalize [info script]]]

#Souce the SC generated TCL file from the current working directory
source -verbose  ./sc_setup.tcl

#Set up process
source -verbose $scriptdir/process.tcl

#Set up libraries
source -verbose $scriptdir/library.tcl

#Souce the SC generated TCL file from the current working directory
source -verbose  ./sc_setup.tcl

################################################################
# Read Inputs
################################################################

#Read data from synthesis

read_verilog $sc_syn_dir/${top_module}$sc_syn_suffix.v
link_design $sc_topmodule
read_sdc $sc_syn_dir/${top_module}$sc_syn_suffix.sdc

################################################################
# Options for floor-planning
################################################################ 

read_def $sc_syn_dir/${top_module}$sc_syn_suffix.def

#1. Take input .def
#2. Auto-generate if nothing is provided

################################################################
# Reporting
################################################################
report_tns
report_wns
report_design_area

################################################################
# Write Results
################################################################

write_def $sc_floorplan_dir/$top_module$sc_floorplan_suffix.def

exit
