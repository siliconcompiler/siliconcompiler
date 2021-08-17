
#######################################
# Clock tree synthesis
# (skip if no clocks defined)
#######################################


if {[llength [all_clocks]] > 0} {

    # Clone clock tree inverters next to register loads
    # so cts does not try to buffer the inverted clocks.
    repair_clock_inverters

    # Allow CTS to fail without interrupting the flow.
    # Sometimes it decides to skip the specified nets, do nothing, and error out.
    catch {
        if {[dict exists $sc_cfg clock] && [dict exists $sc_cfg clock clk]} {
            set sc_clkpins [join [dict get $sc_cfg clock clk pin] " "]
            clock_tree_synthesis -root_buf $sc_clkbuf -buf_list $sc_clkbuf \
                -sink_clustering_enable \
                -sink_clustering_size $openroad_cluster_size \
                -sink_clustering_max_diameter $openroad_cluster_diameter \
                -clk_nets "$sc_clkpins" \
                -distance_between_buffers $openroad_cluster_diameter
        }
        # (Try to infer clock net[s] if none are specified)
        else {
            clock_tree_synthesis -root_buf $sc_clkbuf -buf_list $sc_clkbuf \
                -sink_clustering_enable \
                -sink_clustering_size $openroad_cluster_size \
                -sink_clustering_max_diameter $openroad_cluster_diameter \
                -distance_between_buffers $openroad_cluster_diameter
        }
    } err

    set_propagated_clock [all_clocks]

    estimate_parasitics -placement

    repair_clock_nets

    set_placement_padding -global \
	-left $openroad_pad_global_place \
	-right $openroad_pad_global_place

    detailed_placement

    estimate_parasitics -placement

    check_placement

}
