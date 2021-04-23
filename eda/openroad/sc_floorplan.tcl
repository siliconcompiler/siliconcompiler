########################################################
# FLOORPLANNING
########################################################

if {[llength $sc_def] > 0} {
    #TODO: Only one def supported for now
    read_def -floorplan_initialize $sc_def
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
	set hgrid [dict get $sc_cfg pdk aprlayer $sc_stackup $metal hgrid]
	set hoffset [dict get $sc_cfg pdk aprlayer $sc_stackup $metal hoffset]
	set vgrid [dict get $sc_cfg pdk aprlayer $sc_stackup $metal vgrid]
	set voffset [dict get $sc_cfg pdk aprlayer $sc_stackup $metal voffset]

	make_tracks $name \
	    -x_offset $hoffset \
	    -x_pitch $hgrid \
	    -y_offset $voffset \
	    -y_pitch $vgrid
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
    
}

remove_buffers


