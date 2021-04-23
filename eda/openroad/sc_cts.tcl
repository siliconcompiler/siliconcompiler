
#######################################
# Clock tree synthesis
# (skip if no clocks defined)
#######################################


if {[llength [all_clocks]] > 0} {

    # Clone clock tree inverters next to register loads
    # so cts does not try to buffer the inverted clocks.
    repair_clock_inverters
    
    clock_tree_synthesis -root_buf $sc_clkbuf -buf_list $sc_clkbuf \
	-sink_clustering_enable \
	-sink_clustering_size $openroad_cluster_size \
	-sink_clustering_max_diameter $openroad_cluster_diameter \
	-distance_between_buffers $openroad_cluster_diameter

    set_propagated_clock [all_clocks]
    
    estimate_parasitics -placement

    repair_clock_nets -buffer_cell $sc_clkbuf

    #######################
    # Detailed Placement
    #######################
    
    set_placement_padding -global \
	-left $openroad_pad_global_place \
	-right $openroad_pad_global_place
    
    detailed_placement

    #######################
    # Fix setup/hold
    #######################    

    repair_timing -hold

    repair_timing -setup
    
    detailed_placement

    #######################
    # Add Fillers
    #######################    
    
    filler_placement $sc_filler    
    
    #######################
    # Check Placement
    #######################    
    check_placement
    
}


    
