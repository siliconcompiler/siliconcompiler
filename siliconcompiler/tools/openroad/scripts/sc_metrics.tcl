###############################
# Report Metrics
###############################

proc sc_display_report {report} {
  if { ![file exists $report] } {
    return
  }
  set fid [open $report r]
  set report_content [read $fid]
  close $fid
  puts $report_content
}

set fields "{capacitance slew input_pins nets fanout}"
set PREFIX "SC_METRIC:"

puts "$PREFIX report_checks -path_delay max"
report_checks -fields $fields -path_delay max -format full_clock_expanded > reports/timing/setup.rpt
sc_display_report reports/timing/setup.rpt
report_checks -path_delay max -group_count $openroad_sta_top_n_paths > reports/timing/setup.topN.rpt

puts "$PREFIX report_checks -path_delay min"
report_checks -fields $fields -path_delay min -format full_clock_expanded > reports/timing/hold.rpt
sc_display_report reports/timing/hold.rpt
report_checks -path_delay min -group_count $openroad_sta_top_n_paths > reports/timing/hold.topN.rpt

puts "$PREFIX unconstrained"
report_checks -fields $fields -unconstrained -format full_clock_expanded > reports/timing/unconstrained.rpt
sc_display_report reports/timing/unconstrained.rpt
report_checks -unconstrained -group_count $openroad_sta_top_n_paths > reports/timing/unconstrained.topN.rpt

if {[llength [all_clocks]] > 0} {
  puts "$PREFIX clock_skew"
  report_clock_skew > reports/timing/skew.rpt
  sc_display_report reports/timing/skew.rpt
  report_clock_skew_metric -setup
  report_clock_skew_metric -hold
}

puts "$PREFIX DRV violators"
report_check_types -max_slew -max_capacitance -max_fanout -violators > reports/timing/drv_violators.rpt
sc_display_report reports/timing/drv_violators.rpt
report_erc_metrics

puts "$PREFIX floating nets"
report_floating_nets -verbose > reports/floating_nets.rpt
sc_display_report reports/floating_nets.rpt

puts "$PREFIX tns"
report_tns > reports/timing/total_negative_slack.rpt
sc_display_report reports/timing/total_negative_slack.rpt
report_tns_metric -setup
report_tns_metric -hold

puts "$PREFIX setupslack"
report_worst_slack -max > reports/timing/worst_slack.setup.rpt
sc_display_report reports/timing/worst_slack.setup.rpt
report_worst_slack_metric -setup

puts "$PREFIX holdslack"
report_worst_slack -min > reports/timing/worst_slack.hold.rpt
sc_display_report reports/timing/worst_slack.hold.rpt
report_worst_slack_metric -hold

utl::metric_int "timing__clocks" [llength [all_clocks]]
if { [llength [all_clocks]] == 1 } {
  # Based on
  # https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/34f853f2d2344b6f9198cbeadb1e08e46dde6c09/flow/scripts/write_ref_sdc.tcl
  puts "$PREFIX fmax"
  set period [get_property [lindex [all_clocks] 0] "period"]
  set slack [sta::time_sta_ui [sta::worst_slack_cmd "max"]]
  if { $slack < 1e30 } {
    # Guard against unconstrained designs
    set ref_period [sta::time_ui_sta [expr $period - $slack]]
    set fmax [expr 1.0 / $ref_period]
    utl::metric_float "timing__fmax" $fmax
    puts "[expr $fmax / 1e6] MHz"
  }
}

puts "$PREFIX power"
foreach corner [sta::corners] {
  set corner_name [$corner name]
  puts "Power for corner: $corner_name"
  report_power -corner $corner_name > reports/power/${corner_name}.rpt
  sc_display_report reports/power/${corner_name}.rpt
}
report_power_metric -corner $sc_power_corner

puts "$PREFIX cellarea"
report_design_area
report_design_area_metrics

# get number of nets in design
utl::metric_int "design__nets" [llength [[ord::get_db_block] getNets]]

# get number of registers
utl::metric_int "design__registers" [llength [all_registers]]

# get number of buffers
set bufs 0
set invs 0
foreach inst [get_cells -hierarchical *] {
  set cell [$inst cell]
  if { $cell == "NULL" } {
    continue
  }
  set liberty_cell [$cell liberty_cell]
  if { $liberty_cell == "NULL" } {
    continue
  }
  if { [$liberty_cell is_buffer] } {
    incr bufs
  } elseif { [$liberty_cell is_inverter] } {
    incr invs
  }
}
utl::metric_int "design__buffers" [expr $bufs + $invs]

# get number of unconstrained endpoints
with_output_to_variable endpoints {check_setup -unconstrained_endpoints}
set unconstrained_endpoints [regexp -all -inline {[0-9]+} $endpoints]
if { $unconstrained_endpoints == "" } {
  set unconstrained_endpoints 0
}
utl::metric_int "timing__unconstrained" $unconstrained_endpoints
