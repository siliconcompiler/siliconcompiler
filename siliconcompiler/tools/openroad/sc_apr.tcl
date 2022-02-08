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

set openroad_place_density [lindex [dict get $sc_cfg eda $sc_tool {variable} $sc_step $sc_index  place_density] 0]
set openroad_pad_global_place [lindex [dict get $sc_cfg eda $sc_tool {variable} $sc_step $sc_index  pad_global_place] 0]
set openroad_pad_detail_place [lindex [dict get $sc_cfg eda $sc_tool {variable} $sc_step $sc_index  pad_detail_place] 0]
set openroad_macro_place_halo [dict get $sc_cfg eda $sc_tool {variable} $sc_step  $sc_index  macro_place_halo]
set openroad_macro_place_channel [dict get $sc_cfg eda $sc_tool {variable} $sc_step $sc_index  macro_place_channel]

#Handling remote/local script execution
if {[dict get $sc_cfg eda $sc_tool copy] eq True} {
    set sc_refdir "."
} else {
    set sc_refdir [dict get $sc_cfg eda $sc_tool refdir $sc_step $sc_index ]
}

# Design
set sc_design     [dict get $sc_cfg design]
set sc_optmode    [dict get $sc_cfg optmode]

# APR Parameters
set sc_mainlib     [lindex [dict get $sc_cfg asic logiclib] 0]
set sc_targetlibs  [dict get $sc_cfg asic logiclib]

set sc_stackup     [dict get $sc_cfg asic stackup]
set sc_density     [dict get $sc_cfg asic density]
set sc_hpinmetal   [dict get $sc_cfg asic hpinlayer]
set sc_vpinmetal   [dict get $sc_cfg asic vpinlayer]
set sc_rcmetal     [dict get $sc_cfg asic rclayer data]
set sc_clkmetal    [dict get $sc_cfg asic rclayer clk]
set sc_aspectratio [dict get $sc_cfg asic aspectratio]
set sc_minmetal    [dict get $sc_cfg asic minlayer]
set sc_maxmetal    [dict get $sc_cfg asic maxlayer]
set sc_maxfanout   [dict get $sc_cfg asic maxfanout]
set sc_maxlength   [dict get $sc_cfg asic maxlength]
set sc_maxcap      [dict get $sc_cfg asic maxcap]
set sc_maxslew     [dict get $sc_cfg asic maxslew]

# TPDK agnostic design rule translation
dict for {key value} [dict get $sc_cfg pdk grid $sc_stackup] {
    set sc_name [dict get $sc_cfg pdk grid $sc_stackup $key name]

    if {$sc_name == $sc_minmetal} {
	set sc_minmetal $key
    }
    if {$sc_name == $sc_maxmetal} {
	set sc_maxmetal $key
    }
    if {$sc_name == $sc_hpinmetal} {
	set sc_hpinmetal $key
    }
    if {$sc_name == $sc_vpinmetal} {
	set sc_vpinmetal $key
    }
    if {$sc_name == $sc_rcmetal} {
	set sc_rcmetal $key
    }
    if {$sc_name == $sc_clkmetal} {
	set sc_clkmetal $key
    }
}

# Library
set sc_libtype     [dict get $sc_cfg library $sc_mainlib arch]
set sc_site        [lindex [dict get $sc_cfg library $sc_mainlib site] 0]
set sc_filler      [dict get $sc_cfg library $sc_mainlib cells filler]
set sc_dontuse     [dict get $sc_cfg library $sc_mainlib cells ignore]
set sc_clkbuf      [dict get $sc_cfg library $sc_mainlib cells clkbuf]
set sc_filler      [dict get $sc_cfg library $sc_mainlib cells filler]
set sc_tie         [dict get $sc_cfg library $sc_mainlib cells tie]
set sc_ignore      [dict get $sc_cfg library $sc_mainlib cells ignore]
set sc_tapcell     [dict get $sc_cfg library $sc_mainlib cells tapcell]
set sc_endcap      [dict get $sc_cfg library $sc_mainlib cells endcap]

# PDK Design Rules
set sc_techlef     [dict get $sc_cfg pdk aprtech openroad $sc_stackup $sc_libtype lef]

# TODO: workaround until OpenROAD allows floating-point 'tapmax' values.
set sc_tapmax      [expr {int([lindex [dict get $sc_cfg pdk tapmax] end])}]
set sc_tapoffset   [lindex [dict get $sc_cfg pdk tapoffset] end]

set sc_threads     [dict get $sc_cfg eda $sc_tool threads $sc_step $sc_index ]

###############################
# Optional
###############################

# MACROS
set sc_macrolibs [dict get $sc_cfg asic macrolib]
set sc_constraints [dict get $sc_cfg constraint]

###############################
# Read Files
###############################

# Read techlef
read_lef  $sc_techlef

# Read Targetlibs
foreach lib $sc_targetlibs {
	read_liberty [dict get $sc_cfg library $lib nldm typical lib]
	read_lef [dict get $sc_cfg library $lib lef]
}

# Read Macrolibs
foreach lib $sc_macrolibs {
    if {[dict exists $sc_cfg library $lib nldm]} {
        read_liberty [dict get $sc_cfg library $lib nldm typical lib]
    }
    read_lef [dict get $sc_cfg library $lib lef]
}

# Read Verilog
if {$sc_step == "floorplan"} {
    if {[dict exists $sc_cfg "read" netlist $sc_step $sc_index]} {
        foreach netlist [dict get $sc_cfg "read" netlist $sc_step $sc_index] {
            read_verilog $netlist
        }
    } else {
        read_verilog "inputs/$sc_design.vg"
    }
    link_design $sc_design
}

# Read DEF
if {[dict exists $sc_cfg "read" def $sc_step $sc_index]} {
    foreach def [dict get $sc_cfg "read" def $sc_step $sc_index] {
	if {$sc_step == "floorplan"} {
	    #only one floorplan supported
	    read_def -floorplan_initialize $def
	} else {
	    read_def $def
	}
    }
} elseif {[file exists "inputs/$sc_design.def"]} {
    read_def "inputs/$sc_design.def"
}

# Read SDC (in order of priority)
if {[dict exists $sc_cfg "read" sdc $sc_step $sc_index]} {
    foreach sdc [dict get $sc_cfg "read" sdc $sc_step $sc_index] {
	# read step constraint if exists
	read_sdc $sdc
    }
} elseif {[file exists "inputs/$sc_design.sdc"]} {
    # get from previous step
    read_sdc "inputs/$sc_design.sdc"
} elseif {[llength $sc_constraints] > 0} {
    # otherwise, if we have user-provided constraints, read those
    foreach sdc $sc_constraints {
        read_sdc $sdc
    }
} else {
    # fall back on default auto generated constraints file
    read_sdc "${sc_refdir}/sc_constraints.sdc"
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
