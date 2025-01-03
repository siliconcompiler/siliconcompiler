###############################
# Report Metrics
###############################

# Setup reports directories
file mkdir reports/timing
file mkdir reports/power
file mkdir reports/markers

set fields "{capacitance slew input_pins hierarcial_pins net fanout}"
set sta_top_n_paths [lindex [sc_cfg_tool_task_get var sta_top_n_paths] 0]
set PREFIX "SC_METRIC:"

if { [sc_cfg_tool_task_check_in_list setup var reports] } {
    puts "$PREFIX report_checks -path_delay max"
    tee -file reports/timing/setup.rpt \
        "report_checks -fields $fields -path_delay max -format full_clock_expanded"
    tee -file reports/timing/setup.topN.rpt -quiet \
        "report_checks -fields $fields -path_delay max -group_count $sta_top_n_paths"

    puts "$PREFIX setupslack"
    tee -file reports/timing/worst_slack.setup.rpt \
        "report_worst_slack -max"
    report_worst_slack_metric -setup

    puts "$PREFIX tns"
    tee -file reports/timing/total_negative_slack.rpt \
        "report_tns"
    report_tns_metric -setup
}

if { [sc_cfg_tool_task_check_in_list hold var reports] } {
    puts "$PREFIX report_checks -path_delay min"
    tee -file reports/timing/hold.rpt \
        "report_checks -fields $fields -path_delay min -format full_clock_expanded"
    tee -file reports/timing/hold.topN.rpt -quiet \
        "report_checks -fields $fields -path_delay min -group_count $sta_top_n_paths"

    puts "$PREFIX holdslack"
    tee -file reports/timing/worst_slack.hold.rpt \
        "report_worst_slack -min"
    report_worst_slack_metric -hold

    report_tns_metric -hold
}

if { [sc_cfg_tool_task_check_in_list unconstrained var reports] } {
    puts "$PREFIX unconstrained"
    tee -file reports/timing/unconstrained.rpt \
        "report_checks -fields $fields -unconstrained -format full_clock_expanded"
    tee -file reports/timing/unconstrained.topN.rpt -quiet \
        "report_checks -fields $fields -unconstrained -group_count $sta_top_n_paths"
}

if {
    [sc_cfg_tool_task_check_in_list clock_skew var reports] &&
    [llength [all_clocks]] > 0
} {
    puts "$PREFIX clock_skew"
    tee -file reports/timing/skew.setup.rpt \
        "report_clock_skew -setup -digits 4"
    report_clock_skew_metric -setup
    tee -file reports/timing/skew.hold.rpt \
        "report_clock_skew -hold -digits 4"
    report_clock_skew_metric -hold
}

if { [sc_cfg_tool_task_check_in_list drv_violations var reports] } {
    puts "$PREFIX DRV violators"
    tee -file reports/timing/drv_violators.rpt \
        "report_check_types -max_slew -max_capacitance -max_fanout -violators"
    report_erc_metrics

    puts "$PREFIX floating nets"
    tee -file reports/floating_nets.rpt \
        "report_floating_nets -verbose"
}

utl::metric_int "timing__clocks" [llength [all_clocks]]

if { [sc_cfg_tool_task_check_in_list fmax var reports] } {
    puts "$PREFIX fmax"
    # Model on: https://github.com/The-OpenROAD-Project/OpenSTA/blob/f913c3ddbb3e7b4364ed4437c65ac78c4da9174b/tcl/Search.tcl#L1078
    set fmax_metric 0
    foreach clk [sta::sort_by_name [all_clocks]] {
        set clk_name [get_name $clk]
        set min_period [sta::find_clk_min_period $clk 1]
        if { $min_period == 0.0 } {
            continue
        }
        set fmax [expr { 1.0 / $min_period }]
        utl::metric_float "timing__fmax__clock:${clk_name}" $fmax
        puts "$clk_name fmax = [format %.2f [expr { $fmax / 1e6 }]] MHz"
        set fmax_metric [expr { max($fmax_metric, $fmax) }]
    }
    if { $fmax_metric > 0 } {
        utl::metric_float "timing__fmax" $fmax_metric
    }
}

# get logic depth of design
utl::metric_int "design__logic__depth" [sc_count_logic_depth]

if { [sc_cfg_tool_task_check_in_list power var reports] } {
    puts "$PREFIX power"
    foreach corner [sta::corners] {
        set corner_name [$corner name]
        puts "Power for corner: $corner_name"

        tee -file reports/power/${corner_name}.rpt \
            "report_power -corner $corner_name"
    }
    report_power_metric -corner [sc_cfg_tool_task_get var power_corner]
}

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
utl::metric_int "design__buffers" $bufs
utl::metric_int "design__inverters" $invs

# get number of unconstrained endpoints
with_output_to_variable endpoints {check_setup -unconstrained_endpoints}
set unconstrained_endpoints [regexp -all -inline {[0-9]+} $endpoints]
if { $unconstrained_endpoints == "" } {
    set unconstrained_endpoints 0
}
utl::metric_int "timing__unconstrained" $unconstrained_endpoints

# Write markers
foreach markerdb [[ord::get_db_block] getMarkerCategories] {
    if { [$markerdb getMarkerCount] == 0 } {
        continue
    }

    $markerdb writeTR "reports/markers/${sc_design}.[$markerdb getName].rpt"
    $markerdb writeJSON "reports/markers/${sc_design}.[$markerdb getName].json"
}

utl::push_metrics_stage "sc__cellarea__{}"
tee -file reports/cell_usage.rpt {report_cell_usage -verbose}

foreach modinst [[ord::get_db_block] getModInsts] {
    tee -quiet -append -file reports/cell_usage.rpt { puts "" }
    tee -quiet -append -file reports/cell_usage.rpt {
    puts "########################################################"
}
    tee -quiet -append -file reports/cell_usage.rpt { puts "" }

    utl::metric "design__instance__name__in_module:[[$modinst getMaster] getName]" \
        [$modinst getHierarchicalName]
    tee -quiet -append -file reports/cell_usage.rpt \
        "report_cell_usage -verbose [$modinst getHierarchicalName]"
}
utl::pop_metrics_stage
