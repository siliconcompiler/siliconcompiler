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

# These are magic tuning constants that vary per-technology. We set their values
# here since they're OpenROAD-specific, and therefore we don't want to define
# them in the schema.

set target [dict get $sc_cfg target]
set targetlist [split $target _]
set target_tech [lindex [lindex $targetlist 0] end]

if {$target_tech eq "freepdk45"} {
    set openroad_place_density 0.3
    set openroad_pad_global_place 2
    set openroad_pad_detail_place 1
    set openroad_macro_place_halo "22.4 15.12"
    set openroad_macro_place_channel "18.8 19.95"
} elseif {$target_tech eq "asap7"} {
    set openroad_place_density 0.77
    set openroad_pad_global_place 2
    set openroad_pad_detail_place 1
    set openroad_macro_place_halo "22.4 15.12"
    set openroad_macro_place_channel "18.8 19.95"
} elseif {$target_tech eq "skywater130"} {
    set openroad_place_density 0.6
    set openroad_pad_global_place 4
    set openroad_pad_detail_place 2
    set openroad_macro_place_halo "1 1"
    set openroad_macro_place_channel "80 80"
} else {
    puts "WARNING: OpenROAD tuning constants not set for $target_tech in sc_apr.tcl, using generic values."
    set openroad_place_density 0.3
    set openroad_pad_global_place 2
    set openroad_pad_detail_place 1
    set openroad_macro_place_halo "22.4 15.12"
    set openroad_macro_place_channel "18.8 19.95"
}

###############################
# Schema Adapter
###############################

set tool openroad


#Handling remote/local script execution
set sc_step   [dict get $sc_cfg status step]

if {[dict get $sc_cfg eda $tool $sc_step copy] eq True} {
    set sc_refdir "."
} else {
    set sc_refdir [dict get $sc_cfg eda $tool $sc_step refdir]
}

# Design
set sc_design      [dict get $sc_cfg design]
set sc_optmode     [dict get $sc_cfg optmode]

# APR Parameters
set sc_mainlib     [lindex [dict get $sc_cfg asic targetlib] 0]
set sc_targetlibs  [dict get $sc_cfg asic targetlib]
set sc_stackup     [dict get $sc_cfg asic stackup]
set sc_density     [dict get $sc_cfg asic density]
set sc_hpinlayer   [dict get $sc_cfg asic hpinlayer]
set sc_vpinlayer   [dict get $sc_cfg asic vpinlayer]
set sc_hpinmetal   [dict get $sc_cfg pdk grid $sc_stackup $sc_hpinlayer name]
set sc_vpinmetal   [dict get $sc_cfg pdk grid $sc_stackup $sc_vpinlayer name]
set sc_rclayer     [dict get $sc_cfg asic rclayer]
set sc_clklayer    [dict get $sc_cfg asic clklayer]
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

set sc_threads [dict get $sc_cfg eda openroad $sc_step threads]

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
    if {[dict exists $sc_cfg macro $lib model]} {
        read_liberty [dict get $sc_cfg macro $lib model typical nldm lib]
    }
    read_lef [dict get $sc_cfg macro $lib lef]
}

# Floorplan reads synthesis verilog, others read def
if {$sc_step == "floorplan" | $sc_step == "synopt"} {
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
