#######################################
# Clock tree synthesis
# (skip if no clocks defined)
#######################################

if { [llength [all_clocks]] > 0 } {

  # Clone clock tree inverters next to register loads
  # so cts does not try to buffer the inverted clocks.
  repair_clock_inverters

  set sc_cts_arguments []
  if { $openroad_cts_balance_levels == "true" } {
    lappend sc_cts_arguments "-balance_levels"
  }
  if { $openroad_cts_obstruction_aware == "true" } {
    lappend sc_cts_arguments "-obstruction_aware"
  }

  clock_tree_synthesis -root_buf $sc_clkbuf -buf_list $sc_clkbuf \
    -sink_clustering_enable \
    -sink_clustering_size $openroad_cts_cluster_size \
    -sink_clustering_max_diameter $openroad_cts_cluster_diameter \
    -distance_between_buffers $openroad_cts_distance_between_buffers \
    {*}$sc_cts_arguments

  set_propagated_clock [all_clocks]

  estimate_parasitics -placement

  repair_clock_nets

  sc_detailed_placement

  estimate_parasitics -placement

  set repair_timing_args []
  if { $openroad_rsz_skip_pin_swap == "true" } {
    lappend repair_timing_args "-skip_pin_swap"
  }
  if { $openroad_rsz_skip_gate_cloning == "true" } {
    lappend repair_timing_args "-skip_gate_cloning"
  }

  repair_timing -setup -verbose \
    -setup_margin $openroad_rsz_setup_slack_margin \
    -hold_margin $openroad_rsz_hold_slack_margin \
    -repair_tns $openroad_rsz_repair_tns \
    {*}$repair_timing_args

  estimate_parasitics -placement
  repair_timing -hold -verbose \
    -setup_margin $openroad_rsz_setup_slack_margin \
    -hold_margin $openroad_rsz_hold_slack_margin \
    -repair_tns $openroad_rsz_repair_tns \
    {*}$repair_timing_args

  sc_detailed_placement
}

global_connect

# estimate for metrics
estimate_parasitics -placement
