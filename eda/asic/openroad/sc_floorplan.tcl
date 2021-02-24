##############################################################
# SC SETUP
##############################################################

set stage      "floorplan"

source ./sc_setup.tcl

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg tool $stage refdir]
if {[dict get $sc_cfg tool $stage copy] eq True} {
    set scriptdir "./"
}

#Massaging dict into simple local variables
set stackup      [dict get $sc_cfg stackup]
set target_libs  [dict get $sc_cfg target_lib]
set mainlib      [lindex $target_libs 0]
set libarch      [dict get $sc_cfg stdcells $mainlib libtype]
set techlef      [dict get $sc_cfg pdk_aprtech $stackup $libarch openroad]
set topmodule    [dict get $sc_cfg design]
set corner       "typical"
set diesize      [dict get $sc_cfg diesize]
set coresize     [dict get $sc_cfg coresize]


#Inputs
set input_verilog   "inputs/$topmodule.v"
set input_def       "inputs/$topmodule.def"
set input_sdc       "inputs/$topmodule.sdc"

#Outputs
set output_verilog  "outputs/$topmodule.v"
set output_def      "outputs/$topmodule.def"
set output_sdc      "outputs/$topmodule.sdc"

####################
#Setup Process
####################
read_lef  $techlef
set pnrlayers    [dict get $sc_cfg pdk_aprlayer $stackup]

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
    read_liberty [dict get $sc_cfg stdcells $lib model typical nldm lib]
    read_lef [dict get $sc_cfg stdcells $lib lef]
    set site [dict get $sc_cfg stdcells $lib site]
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
    if {[llength $diesize] != "4"} {
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


