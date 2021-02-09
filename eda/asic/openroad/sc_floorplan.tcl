##############################################################
# SC SETUP
##############################################################

set stage      "floorplan"

source ./sc_setup.tcl

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg sc_tool $stage refdir]
if {[dict get $sc_cfg sc_tool $stage copy] eq True} {
    set scriptdir "./"
}

#Massaging dict into simple local variables
set stackup      [dict get $sc_cfg sc_target_stackup]
set target_libs  [dict get $sc_cfg sc_target_lib]
set libarch      [dict get $sc_cfg sc_target_libarch]
set techlef      [dict get $sc_cfg sc_pdk_pnrtech $stackup $libarch openroad]
set pnrlayers    [dict get $sc_cfg sc_pdk_pnrlayer $stackup]

set topmodule    [dict get $sc_cfg sc_design]
set corner       "typical"
set diesize      [dict get $sc_cfg sc_diesize]
set coresize     [dict get $sc_cfg sc_coresize]
set density      [dict get $sc_cfg sc_density]
set coremargin   [dict get $sc_cfg sc_coremargin]
set aspectratio  [dict get $sc_cfg sc_aspectratio]

#Inputs
set input_verilog   "inputs/$topmodule.v"
set input_def       [dict get $sc_cfg sc_def]

#Outputs
set output_verilog  "outputs/$topmodule.v"
set output_def      "outputs/$topmodule.def"
set output_sdc      "outputs/$topmodule.sdc"

####################
#Setup Process
####################
read_lef  $techlef

set outfile [open "sc_tracks.txt" w]
#loop through list one tuple4 at a time
for {set i 0} {$i < [llength $pnrlayers]} {set i [expr {$i + 4}]} {
    #extract tuple of 4
    set rule [lrange $pnrlayers $i [expr {$i+3}]]
    puts $outfile "$rule"
}
close $outfile

####################
#Setup Libs
####################
foreach lib $target_libs {
    read_liberty [dict get $sc_cfg sc_stdcells $lib nldm $corner]
    read_lef [dict get $sc_cfg sc_stdcells $lib lef]
    set site [dict get $sc_cfg sc_stdcells $lib site]
}

####################
#Setup Design
####################
read_verilog $input_verilog
link_design $topmodule


########################################################
# FLOORPLANNING
########################################################

if {[file exists $input_def]} {
    read_def $input_def
} else {
    if {[llength $sc_diesize] != "4"} {
	#1. get cell area
	#2. calculate die area based on density
    }
    #init floorplan
    initialize_floorplan -die_area $diesize \
	    -core_area $coresize \
	    -tracks ./sc_tracks.txt \
	    -site $site     
    #TODO!!! Put these into schema
    #randomize I/O placementa
    io_placer -hor_layer "4" \
	-ver_layer "3" \
	-random
    
}

remove_buffers

#################
# Write Output
#################

write_def $output_def


