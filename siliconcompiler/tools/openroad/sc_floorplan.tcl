########################################################
# FLOORPLANNING
########################################################

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
} else {

    #########################
    #Init Floorplan
    #########################
	#NOTE: assuming a two tuple value as lower left, upper right
    set sc_diearea   [dict get $sc_cfg asic diearea]
    set sc_corearea  [dict get $sc_cfg asic corearea]
    set sc_diesize   [regsub -all {[\,\)\(]} $sc_diearea " "]
    set sc_coresize  [regsub -all {[\,\)\(]} $sc_corearea " "]
    puts $sc_diearea
    puts $sc_corearea
    puts $sc_diesize
    puts $sc_coresize

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
