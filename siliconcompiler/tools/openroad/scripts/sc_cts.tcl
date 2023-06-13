#######################################
# Clock tree synthesis
# (skip if no clocks defined)
#######################################

if {[llength [all_clocks]] > 0} {

  # Clone clock tree inverters next to register loads
  # so cts does not try to buffer the inverted clocks.
  repair_clock_inverters

  set sc_cts_arguments []
  if {$openroad_cts_balance_levels == "true"} {
    lappend sc_cts_arguments "-balance_levels"
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

  set_placement_padding -global \
    -left $openroad_dpl_padding \
    -right $openroad_dpl_padding

  set dpl_args []
  if { $openroad_dpl_disallow_one_site == "true" } {
    lappend dpl_args "-disallow_one_site_gaps"
  }

  detailed_placement -max_displacement $openroad_dpl_max_displacement \
    {*}$dpl_args
  check_placement -verbose

  estimate_parasitics -placement

  set repair_timing_args []
  if { $openroad_rsz_skip_pin_swap == "true" } {
    lappend repair_timing_args "-skip_pin_swap"
  }

  puts "Repair setup violations"
  repair_timing -setup \
    -setup_margin $openroad_rsz_setup_slack_margin \
    -hold_margin $openroad_rsz_hold_slack_margin \
    -repair_tns $openroad_rsz_repair_tns

  estimate_parasitics -placement
  puts "Repair hold violations"
  repair_timing -hold \
    -setup_margin $openroad_rsz_setup_slack_margin \
    -hold_margin $openroad_rsz_hold_slack_margin \
    -repair_tns $openroad_rsz_repair_tns

  detailed_placement -max_displacement $openroad_dpl_max_displacement \
    {*}$dpl_args
  check_placement -verbose
}

global_connect

# estimate for metrics
estimate_parasitics -placement
