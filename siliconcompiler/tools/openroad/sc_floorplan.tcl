########################################################
# FLOORPLANNING
########################################################

proc calculate_core_size {density coremargin aspectratio syn_area lib_height} {

    set target_area [expr {$syn_area * 100.0 / $density}]
    set core_width [expr {sqrt($target_area / $aspectratio)}]

    set core_width_rounded [expr {ceil($core_width / $lib_height) * $lib_height}]
    set core_height [expr {$aspectratio * $core_width}]
    set core_height_rounded [expr {ceil($core_height / $lib_height) * $lib_height}]

    set core_max_x [expr {$core_width_rounded + $coremargin}]
    set core_max_y [expr {$core_height_rounded + $coremargin}]

    return "$coremargin $coremargin $core_max_x $core_max_y"
}

proc calculate_die_size {coresize coremargin} {
    set core_max_x [lindex $coresize 2]
    set core_max_y [lindex $coresize 3]
    set die_max_x [expr {$core_max_x + $coremargin}]
    set die_max_y [expr {$core_max_y + $coremargin}]

    return "0 0 $die_max_x $die_max_y"
}

# Functon adapted from OpenROAD:
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/ca3004b85e0d4fbee3470115e63b83c498cfed85/flow/scripts/macro_place.tcl#L26
proc design_has_macros {} {
  set db [::ord::get_db]
  set block [[$db getChip] getBlock]
  foreach inst [$block getInsts] {
    set inst_master [$inst getMaster]

    # BLOCK means MACRO cells
    if { [string match [$inst_master getType] "BLOCK"] } {
        return true
    }
  }
  return false
}

if {[llength $sc_def] > 0} {
    #TODO: Only one def supported for now
    read_def -floorplan_initialize $sc_def
} elseif {[llength $sc_floorplan] > 0} {
    read_def -floorplan_initialize "inputs/$sc_design.def"
} else {

    #########################
    #Init Floorplan
    #########################
    if {[dict exists $sc_cfg asic diesize] &&
        [dict exists $sc_cfg asic coresize]} {
        set sc_diesize     [dict get $sc_cfg asic diesize]
        set sc_coresize    [dict get $sc_cfg asic coresize]
    } else {
        set sc_density [dict get $sc_cfg asic density]
        set sc_coremargin [dict get $sc_cfg asic coremargin]
        if {$sc_density < 1 || $sc_density > 100} {
            puts "Error: ASIC density must be between 1 and 100!"
            exit 1
        }

        set syn_area [dict get $sc_cfg metric syn real area_cells]
        set lib_height [dict get $sc_cfg stdcell $sc_mainlib height]
        set sc_coresize [calculate_core_size $sc_density $sc_coremargin $sc_aspectratio $syn_area $lib_height]
        set sc_diesize [calculate_die_size $sc_coresize $sc_coremargin]

    }

    initialize_floorplan -die_area $sc_diesize \
	-core_area $sc_coresize \
	-site $sc_site

    ###########################
    # Track Creation
    ###########################

    set metal_list ""
    dict for {key value} [dict get $sc_cfg pdk grid $sc_stackup] {
	lappend metal_list $key
    }

    foreach metal $metal_list {
	#extracting values from dictionary
	set name [dict get $sc_cfg pdk grid $sc_stackup $metal name]
	set xpitch [dict get $sc_cfg pdk grid $sc_stackup $metal xpitch]
	set xoffset [dict get $sc_cfg pdk grid $sc_stackup $metal xoffset]
	set ypitch [dict get $sc_cfg pdk grid $sc_stackup $metal ypitch]
	set yoffset [dict get $sc_cfg pdk grid $sc_stackup $metal yoffset]

	make_tracks $name \
	    -x_offset $xoffset \
	    -x_pitch $xpitch \
	    -y_offset $yoffset \
	    -y_pitch $ypitch
    }

    ###########################
    # Automatic Pin Placement
    ###########################

    place_pins -hor_layers $sc_hpinmetal \
	-ver_layers $sc_vpinmetal \
	-random \

    # Need to check if we have any macros before performing macro placement,
    # since we get an error otherwise.
    if {[design_has_macros]} {
        ###########################
        # TDMS Placement
        ###########################

        global_placement -density $openroad_place_density \
            -pad_left $openroad_pad_global_place \
            -pad_right $openroad_pad_global_place

        ###########################
        # Macro placement
        ###########################

        macro_placement \
            -halo $openroad_macro_place_halo \
            -channel $openroad_macro_place_channel

        # Note: some platforms set a "macro blockage halo" at this point, but the
        # technologies we support do not, so we don't include that step for now.
    }

    ###########################
    # Power Network (not good)
    ###########################
    #pdngen $::env(PDN_CFG) -verbose

}

###########################
# Tap Cells
###########################
tapcell \
    -endcap_cpp $sc_tapoffset \
    -distance $sc_tapmax \
    -tapcell_master $sc_tapcell \
    -endcap_master $sc_endcap

remove_buffers
