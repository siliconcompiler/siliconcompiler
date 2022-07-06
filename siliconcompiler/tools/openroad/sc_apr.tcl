###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl  > /dev/null

###############################
# Openroad Hard Coded Constants
###############################

set openroad_overflow_iter 100
set openroad_cluster_diameter 100
set openroad_cluster_size 30

##############################
# Schema Adapter
###############################

set sc_tool   openroad
set sc_step   [dict get $sc_cfg arg step]
set sc_index  [dict get $sc_cfg arg index]

set sc_refdir [dict get $sc_cfg tool $sc_tool refdir $sc_step $sc_index ]

# Design
set sc_design     [sc_get_entrypoint]
set sc_optmode    [dict get $sc_cfg option optmode]
set sc_flow       [dict get $sc_cfg option flow]
set sc_pdk        [dict get $sc_cfg option pdk]

# APR Parameters
set sc_mainlib     [lindex [dict get $sc_cfg asic logiclib] 0]
set sc_targetlibs  [dict get $sc_cfg asic logiclib]
set sc_delaymodel  [dict get $sc_cfg asic delaymodel]
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
set sc_scenarios   [dict keys [dict get $sc_cfg constraint]]

# PDK agnostic design rule translation
dict for {key value} [dict get $sc_cfg pdk $sc_pdk grid $sc_stackup] {
    set sc_name [dict get $sc_cfg pdk $sc_pdk grid $sc_stackup $key name]

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
set sc_libtype     [dict get $sc_cfg library $sc_mainlib asic libarch]
# TODO: handle multiple sites properly
set sc_site        [lindex [dict keys [dict get $sc_cfg library $sc_mainlib asic footprint]] 0]
set sc_filler      [dict get $sc_cfg library $sc_mainlib asic cells filler]
set sc_dontuse     [dict get $sc_cfg library $sc_mainlib asic cells ignore]
set sc_clkbuf      [dict get $sc_cfg library $sc_mainlib asic cells clkbuf]
set sc_filler      [dict get $sc_cfg library $sc_mainlib asic cells filler]
set sc_tie         [dict get $sc_cfg library $sc_mainlib asic cells tie]
set sc_ignore      [dict get $sc_cfg library $sc_mainlib asic cells ignore]
set sc_tap         [dict get $sc_cfg library $sc_mainlib asic cells tap]
set sc_endcap      [dict get $sc_cfg library $sc_mainlib asic cells endcap]

# PDK Design Rules
set sc_techlef     [dict get $sc_cfg pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype lef]

if {[dict exists $sc_cfg datasheet $sc_design]} {
   set sc_pins    [dict keys [dict get $sc_cfg datasheet $sc_design pin]]
} else {
   set sc_pins    [list]
}

set sc_threads     [dict get $sc_cfg tool $sc_tool threads $sc_step $sc_index ]

# Sweep parameters

set openroad_place_density [lindex [dict get $sc_cfg tool $sc_tool {var} $sc_step $sc_index  place_density] 0]
set openroad_pad_global_place [lindex [dict get $sc_cfg tool $sc_tool {var} $sc_step $sc_index  pad_global_place] 0]
set openroad_pad_detail_place [lindex [dict get $sc_cfg tool $sc_tool {var} $sc_step $sc_index  pad_detail_place] 0]
set openroad_macro_place_halo [dict get $sc_cfg tool $sc_tool {var} $sc_step  $sc_index  macro_place_halo]
set openroad_macro_place_channel [dict get $sc_cfg tool $sc_tool {var} $sc_step $sc_index  macro_place_channel]

set sc_batch [expr ![string match "show*" $sc_step]]

###############################
# Optional
###############################

# MACROS
set sc_macrolibs [dict get $sc_cfg asic macrolib]

###############################
# Read Files
###############################

# Read techlef
read_lef  $sc_techlef

# Read Liberty
foreach item $sc_scenarios {
    set corner [dict get $sc_cfg constraint $item libcorner]
    foreach lib "$sc_targetlibs $sc_macrolibs" {
	#Liberty
	if {[dict exists $sc_cfg library $lib model timing $sc_delaymodel]} {
	    set lib_file [dict get $sc_cfg library $lib model timing $sc_delaymodel $corner]
	    read_liberty $lib_file
	}
    }
}

# Read Lefs
foreach lib "$sc_targetlibs $sc_macrolibs" {
    read_lef [dict get $sc_cfg library $lib model layout lef $sc_stackup]
}

# Read Verilog
if {$sc_step == "floorplan"} {
    if {[dict exists $sc_cfg "input" netlist]} {
        foreach netlist [dict get $sc_cfg "input" netlist] {
            read_verilog $netlist
        }
    } else {
        read_verilog "inputs/$sc_design.vg"
    }
    link_design $sc_design
}

# Read DEF
if {[dict exists $sc_cfg "input" def]} {
    if {$sc_step != "floorplan"} {
        # Floorplan initialize handled separately in sc_floorplan.tcl
        foreach def [dict get $sc_cfg "input" def] {
            read_def $def
        }
    }
} elseif {[file exists "inputs/$sc_design.def"]} {
    read_def "inputs/$sc_design.def"
} elseif {$sc_step == "showdef"} {
    read_def $env(SC_FILENAME)
}

# Read SDC (in order of priority)
# TODO: add logic for reading from ['constraint', ...] once we support MCMM
if {[dict exists $sc_cfg "input" sdc]} {
    foreach sdc [dict get $sc_cfg "input" sdc] {
	# read step constraint if exists
	read_sdc $sdc
    }
} elseif {[file exists "inputs/$sc_design.sdc"]} {
    # get from previous step
    read_sdc "inputs/$sc_design.sdc"
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

if {$sc_batch} {
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
}
