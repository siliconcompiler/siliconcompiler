###############################
# Reading SC Schema
###############################

source ./sc_schema.tcl

###############################
# Openroad Constants
###############################

set openroad_place_density 0.3
set openroad_overflow_iter 100
set openroad_pad_global_place 2
set openroad_cluster_diameter 100
set openroad_cluster_size 30

###############################
# Schema Adapter
###############################

#Handling remote/local script execution 
set sc_step   [dict get $sc_cfg status step]

if {[dict get $sc_cfg flow $sc_step copy] eq True} {
    set sc_refdir "."
} else {
    set sc_refdir [dict get $sc_cfg flow $sc_step refdir]
}
    
# Design
set sc_design     [lindex [dict get $sc_cfg design] end]
set sc_optmode     [lindex [dict get $sc_cfg optmode] end]

###############################
# Required
###############################

# APR Parameters		    
set sc_mainlib     [lindex [dict get $sc_cfg asic targetlib] 0]
set sc_targetlibs  [dict get $sc_cfg asic targetlib]
set sc_stackup     [lindex [dict get $sc_cfg asic stackup] end]
set sc_diesize     [dict get $sc_cfg asic diesize]
set sc_coresize    [dict get $sc_cfg asic coresize]
set sc_density     [lindex [dict get $sc_cfg asic density] end]
set sc_hpinlayer   [lindex [dict get $sc_cfg asic hpinlayer] end]
set sc_vpinlayer   [lindex [dict get $sc_cfg asic vpinlayer] end]
set sc_hpinmetal   [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_hpinlayer name]
set sc_vpinmetal   [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_vpinlayer name]
set sc_rclayer     [lindex [dict get $sc_cfg asic rclayer] end]
set sc_clklayer    [lindex [dict get $sc_cfg asic clklayer] end]
set sc_rcmetal     [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_rclayer name]
set sc_clkmetal    [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_clklayer name]

set sc_aspectratio [lindex [dict get $sc_cfg asic aspectratio] end]
set sc_minlayer    [lindex [dict get $sc_cfg asic minlayer] end]
set sc_maxlayer    [lindex [dict get $sc_cfg asic maxlayer] end]
set sc_maxfanout   [lindex [dict get $sc_cfg asic maxfanout] end]
set sc_maxlength   [lindex [dict get $sc_cfg asic maxlength] end]
set sc_maxcap      [lindex [dict get $sc_cfg asic maxcap] end]
set sc_maxslew     [lindex [dict get $sc_cfg asic maxslew] end]

#Library
set sc_libtype     [lindex [dict get $sc_cfg stdcell $sc_mainlib libtype] end]
set sc_site        [lindex [dict get $sc_cfg stdcell $sc_mainlib site] end]
set sc_driver      [lindex [dict get $sc_cfg stdcell $sc_mainlib driver] end]
set sc_filler      [dict get $sc_cfg stdcell $sc_mainlib cells filler]
set sc_dontuse     [dict get $sc_cfg stdcell $sc_mainlib cells ignore]
set sc_clkbuf      [dict get $sc_cfg stdcell $sc_mainlib cells clkbuf]
set sc_filler      [dict get $sc_cfg stdcell $sc_mainlib cells filler]
set sc_tie         [dict get $sc_cfg stdcell $sc_mainlib cells tie]
set sc_ignore      [dict get $sc_cfg stdcell $sc_mainlib cells ignore]
set sc_tapcell     [dict get $sc_cfg stdcell $sc_mainlib cells tapcell]
set sc_endcap      [dict get $sc_cfg stdcell $sc_mainlib cells endcap]

#PDK
set sc_techlef     [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libtype openroad]
set sc_minmetal    [lindex [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_minlayer name] end]
set sc_maxmetal    [lindex [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_maxlayer name] end]
set sc_tapmax      [lindex [dict get $sc_cfg pdk tapmax] end]
set sc_tapoffset   [lindex [dict get $sc_cfg pdk tapoffset] end]

###############################
# Optional
###############################

# MACROS
if {[dict exists $sc_cfg macrolib]} {    
    set sc_macrolibs [dict get $sc_cfg asic macrolib]
} else {
    set sc_macrolibs    ""
}

# CONSTRAINTS
if {[dict exists $sc_cfg constraint]} {    
    set sc_constraint [dict get $sc_cfg constraint]
} else {
    set sc_constraint  ""
}

# DEF
if {[dict exists $sc_cfg def]} {    
    set sc_def [dict get $sc_cfg def]
} else {
    set sc_def  ""
}

###############################
# Read Files
###############################

# Triton Hack b/c it can't handle multiple LEFs!!
# TODO: Fix as soon as triton is merged
if {$sc_step == "route"} {    
    exec "$sc_refdir/mergeLef.py" --inputLef \
	$sc_techlef \
	[dict get $sc_cfg stdcell $sc_mainlib lef] \
	--outputLef "triton_merged.lef"
    read_lef "triton_merged.lef"
} else {
    #Techlef
    read_lef  $sc_techlef
    # Stdcells
    foreach lib $sc_targetlibs {
	read_liberty [dict get $sc_cfg stdcell $lib model typical nldm lib]
	read_lef [dict get $sc_cfg stdcell $lib lef]
    }
}
 
# Macrolibs
foreach lib $sc_macrolibs {
    read_liberty [dict get $sc_cfg macro $lib model typical nldm lib]
    read_lef [dict get $sc_cfg macro $lib lef]    
}

# Floorplan reads synthesis verilog, others read def
if {$sc_step == "floorplan"} {
    read_verilog "inputs/$sc_design.v"
    link_design $sc_design
    foreach sdc $sc_constraint {
	read_sdc $sdc
    }
} else {    
    read_def "inputs/$sc_design.def"
    read_sdc "inputs/$sc_design.sdc"
}

###############################
# Common Setup
###############################

set_dont_use $sc_dontuse

set_wire_rc -clock  -layer $sc_clkmetal
set_wire_rc -signal -layer $sc_rcmetal

set_placement_padding -global \
    -left $openroad_pad_global_place \
    -right $openroad_pad_global_place

###############################
# Source Step Script
###############################

source "$sc_refdir/sc_$sc_step.tcl"

###############################
# Reporting
###############################

source "$sc_refdir/sc_metrics.tcl"

###############################
# Write Design Data
###############################

source "$sc_refdir/sc_write.tcl"

