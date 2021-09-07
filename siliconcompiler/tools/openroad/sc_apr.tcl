###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Openroad Constants
###############################

set openroad_overflow_iter 100
set openroad_cluster_diameter 100
set openroad_cluster_size 30

##############################
# Schema Adapter
###############################

set sc_tool    openroad
set sc_step    [dict get $sc_cfg arg step]
set sc_index   [dict get $sc_cfg arg index]

set openroad_place_density [lindex [dict get $sc_cfg eda $sc_tool $sc_step $sc_index option  place_density] 0]
set openroad_pad_global_place [lindex [dict get $sc_cfg eda $sc_tool $sc_step $sc_index option  pad_global_place] 0]
set openroad_pad_detail_place [lindex [dict get $sc_cfg eda $sc_tool $sc_step $sc_index option  pad_detail_place] 0]
set openroad_macro_place_halo [dict get $sc_cfg eda $sc_tool $sc_step $sc_index option  macro_place_halo]
set openroad_macro_place_channel [dict get $sc_cfg eda $sc_tool $sc_step $sc_index option  macro_place_channel]

#Handling remote/local script execution
if {[dict get $sc_cfg eda $sc_tool $sc_step $sc_index copy] eq True} {
    set sc_refdir "."
} else {
    set sc_refdir [dict get $sc_cfg eda $sc_tool $sc_step $sc_index refdir]
}

# Design
set sc_design     [dict get $sc_cfg design]
set sc_optmode    [dict get $sc_cfg optmode]

# APR Parameters
set sc_mainlib     [lindex [dict get $sc_cfg asic targetlib] 0]
set sc_targetlibs  [dict get $sc_cfg asic targetlib]
set sc_stackup     [dict get $sc_cfg asic stackup]
set sc_density     [dict get $sc_cfg asic density]
set sc_hpinlayer   [dict get $sc_cfg asic hpinlayer]
set sc_vpinlayer   [dict get $sc_cfg asic vpinlayer]
set sc_hpinmetal   [dict get $sc_cfg pdk grid $sc_stackup $sc_hpinlayer name]
set sc_vpinmetal   [dict get $sc_cfg pdk grid $sc_stackup $sc_vpinlayer name]
set sc_rclayer     [dict get $sc_cfg asic rclayer data]
set sc_clklayer    [dict get $sc_cfg asic rclayer clk]
set sc_rcmetal     [dict get $sc_cfg pdk grid $sc_stackup $sc_rclayer name]
set sc_clkmetal    [dict get $sc_cfg pdk grid $sc_stackup $sc_clklayer name]
set sc_aspectratio [dict get $sc_cfg asic aspectratio]
set sc_minlayer    [dict get $sc_cfg asic minlayer]
set sc_maxlayer    [dict get $sc_cfg asic maxlayer]
set sc_maxfanout   [dict get $sc_cfg asic maxfanout]
set sc_maxlength   [dict get $sc_cfg asic maxlength]
set sc_maxcap      [dict get $sc_cfg asic maxcap]
set sc_maxslew     [dict get $sc_cfg asic maxslew]

# Library
set sc_libtype     [dict get $sc_cfg library $sc_mainlib arch]
set sc_site        [dict get $sc_cfg library $sc_mainlib site]
set sc_driver      [dict get $sc_cfg library $sc_mainlib driver]
set sc_filler      [dict get $sc_cfg library $sc_mainlib cells filler]
set sc_dontuse     [dict get $sc_cfg library $sc_mainlib cells ignore]
set sc_clkbuf      [dict get $sc_cfg library $sc_mainlib cells clkbuf]
set sc_filler      [dict get $sc_cfg library $sc_mainlib cells filler]
set sc_tie         [dict get $sc_cfg library $sc_mainlib cells tie]
set sc_ignore      [dict get $sc_cfg library $sc_mainlib cells ignore]
set sc_tapcell     [dict get $sc_cfg library $sc_mainlib cells tapcell]
set sc_endcap      [dict get $sc_cfg library $sc_mainlib cells endcap]

# PDK Design Rules
set sc_techlef     [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libtype lef]
set sc_tapmax      [lindex [dict get $sc_cfg pdk tapmax] end]
set sc_tapoffset   [lindex [dict get $sc_cfg pdk tapoffset] end]

# APR Layers
set sc_minmetal    [dict get $sc_cfg pdk grid $sc_stackup $sc_minlayer name]
set sc_maxmetal    [dict get $sc_cfg pdk grid $sc_stackup $sc_maxlayer name]


# Layer Definitions
set sc_layers ""
dict for {key value} [dict get $sc_cfg pdk grid $sc_stackup] {
    lappend sc_layers $key
}

set sc_threads [dict get $sc_cfg eda $sc_tool $sc_step $sc_index threads]

###############################
# Optional
###############################

# MACROS
if {[dict exists $sc_cfg asic macrolib]} {
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
if {[dict exists $sc_cfg asic def]} {
    set sc_def [dict get $sc_cfg asic def]
} else {
    set sc_def  ""
}

# FLOORPLAN
if {[dict exists $sc_cfg asic floorplan]} {
    set sc_floorplan [dict get $sc_cfg asic floorplan]
} else {
    set sc_floorplan  ""
}

###############################
# Read Files
###############################

# read techlef
read_lef  $sc_techlef

# read targetlibs
foreach lib $sc_targetlibs {
	read_liberty [dict get $sc_cfg library $lib nldm typical lib]
	read_lef [dict get $sc_cfg library $lib lef]
 }

# Macrolibs
foreach lib $sc_macrolibs {
    if {[dict exists $sc_cfg library $lib model]} {
        read_liberty [dict get $sc_cfg library $lib nldm typical lib]
    }
    read_lef [dict get $sc_cfg library $lib lef]
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
# Write Design Data
###############################

source "$sc_refdir/sc_write.tcl"

###############################
# Reporting
###############################

source "$sc_refdir/sc_metrics.tcl"
