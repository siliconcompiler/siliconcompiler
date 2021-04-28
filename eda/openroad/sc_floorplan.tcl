########################################################
# FLOORPLANNING
########################################################

if {[llength $sc_def] > 0} {
    #TODO: Only one def supported for now
    read_def -floorplan_initialize $sc_def
} elseif {[llength $sc_floorplan] > 0} {
    read_def -floorplan_initialize "inputs/$sc_design.def"
} else {

    #########################
    #Init Floorplan
    #########################
    
    initialize_floorplan -die_area $sc_diesize \
	-core_area $sc_coresize \
	-site $sc_site

    ###########################
    # Track Creation
    ###########################

    set metal_list ""
    dict for {key value} [dict get $sc_cfg pdk aprlayer $sc_stackup] {
	lappend metal_list $key
    }
    
    foreach metal $metal_list {
	#extracting values from dictionary
	set name [dict get $sc_cfg pdk aprlayer $sc_stackup $metal name]
	set xpitch [dict get $sc_cfg pdk aprlayer $sc_stackup $metal xpitch]
	set xoffset [dict get $sc_cfg pdk aprlayer $sc_stackup $metal xoffset]
	set ypitch [dict get $sc_cfg pdk aprlayer $sc_stackup $metal ypitch]
	set yoffset [dict get $sc_cfg pdk aprlayer $sc_stackup $metal yoffset]

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
	
    ###########################
    # Tap Cells
    ###########################
    tapcell \
      -endcap_cpp $sc_tapoffset \
      -distance $sc_tapmax \
      -tapcell_master $sc_tapcell \
      -endcap_master $sc_endcap

    ###########################
    # Power Network (not good)
    ###########################
    #pdngen $::env(PDN_CFG) -verbose
    
}

remove_buffers


