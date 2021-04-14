##############################################################
# SC SETUP
##############################################################

set step      "floorplan"

source ./sc_setup.tcl

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg flow $step refdir]
if {[dict get $sc_cfg flow $step copy] eq True} {
    set scriptdir "./"
}

#Massaging dict into simple local variables
set stackup      [dict get $sc_cfg asic stackup]
set target_libs  [dict get $sc_cfg asic targetlib]
set mainlib      [lindex $target_libs 0]
set libarch      [dict get $sc_cfg stdcell $mainlib libtype]
set techlef      [dict get $sc_cfg pdk aprtech $stackup $libarch openroad]
set topmodule    [dict get $sc_cfg design]
set corner       "typical"
set diesize      [dict get $sc_cfg asic diesize]
set coresize     [dict get $sc_cfg asic coresize]
# TODO: Retrieve from dictionary instead of hardcoding.
# Horizontal / Vertical I/O layers.
set io_hlayer    "4"
set io_vlayer    "3"
# Tapcell values.
set endcap_cpp   "2"
set tapcell_dist 120
set tapcell_fill "FILLCELL_X1"

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

#creating routing preference file
set metal_list ""
dict for {key value} [dict get $sc_cfg pdk aprlayer $stackup] {
    lappend metal_list $key
}

#TODO: replace with tcl commands instead of file for new openroad
set outfile [open "sc_tracks.txt" w]
foreach metal $metal_list {
    set name [dict get $sc_cfg pdk aprlayer $stackup $metal name]
    set xpitch [dict get $sc_cfg pdk aprlayer $stackup $metal xpitch]
    set xoffset [dict get $sc_cfg pdk aprlayer $stackup $metal xoffset]
    set ypitch [dict get $sc_cfg pdk aprlayer $stackup $metal ypitch]
    set yoffset [dict get $sc_cfg pdk aprlayer $stackup $metal yoffset]    
    puts $outfile "$name X $xoffset $xpitch"
    puts $outfile "$name Y $yoffset $ypitch"
}
close $outfile

####################
#Setup Libs
####################
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

####################
#Setup Design
####################
read_verilog $input_verilog
link_design $topmodule

########################################################
# FLOORPLANNING
########################################################

if {[file exists $input_def]} {
    read_def -floorplan_initialize $input_def
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
    io_placer -hor_layer $io_hlayer \
	-ver_layer $io_vlayer \
	-random
    # Tapcell insertion.
    tapcell \
      -endcap_cpp $endcap_cpp \
      -distance $tapcell_dist \
      -tapcell_master $tapcell_fill \
      -endcap_master $tapcell_fill
    
}

remove_buffers

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
