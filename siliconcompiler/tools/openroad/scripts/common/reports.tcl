###############################
# Report Metrics
###############################

set fields "{capacitance slew input_pins hierarcial_pins net fanout}"
set sta_top_n_paths [sc_cfg_tool_task_get var sta_top_n_paths]

if { [sc_cfg_tool_task_check_in_list scenarios var reports] } {
    sc_report_banner "Timing scenarios" \
        reports/constraints/scenarios.rpt
    sc_report_scenarios
}

if { [sc_cfg_tool_task_check_in_list setup var reports] } {
    sc_report_banner "Setup timing" \
        reports/timing/setup.rpt \
        reports/timing/setup.topN.rpt \
        reports/timing/setup.failing.rpt \
        reports/timing/setup.endpoints.rpt \
        reports/timing/worst_slack.setup.rpt \
        reports/timing/total_negative_slack.setup.rpt
    tee -file reports/timing/setup.rpt \
        "report_checks -sort_by_slack -fields $fields -path_delay max -format full_clock_expanded"
    tee -file reports/timing/setup.topN.rpt -quiet \
        "report_checks -sort_by_slack -fields $fields -path_delay max \
        -group_path_count $sta_top_n_paths"
    tee -quiet -file reports/timing/setup.failing.rpt \
        "report_checks -sort_by_slack -path_delay max -slack_max 0 -endpoint_path_count 1 \
        -group_path_count $sta_top_n_paths -format short"
    tee -quiet -file reports/timing/setup.endpoints.rpt \
        "report_checks -sort_by_slack -path_delay max -endpoint_path_count 1 \
        -group_path_count $sta_top_n_paths -format end"

    tee -file reports/timing/worst_slack.setup.rpt \
        "report_worst_slack -max"
    report_worst_slack_metric -setup

    tee -file reports/timing/total_negative_slack.setup.rpt \
        "report_tns"
    report_tns_metric -setup

    if { [sc_check_version 24 3 3932] && [llength [all_clocks]] > 0 } {
        puts "report: reports/timing/setup.histogram.rpt"
        tee -quiet -file reports/timing/setup.histogram.rpt \
            "report_timing_histogram -num_bins 20 -setup"
    }

    sc_report_scene_timing -delay max -name setup \
        -fields $fields -top_paths $sta_top_n_paths
}

if { [sc_cfg_tool_task_check_in_list hold var reports] } {
    sc_report_banner "Hold timing" \
        reports/timing/hold.rpt \
        reports/timing/hold.topN.rpt \
        reports/timing/hold.failing.rpt \
        reports/timing/hold.endpoints.rpt \
        reports/timing/worst_slack.hold.rpt \
        reports/timing/total_negative_slack.hold.rpt
    tee -quiet -file reports/timing/hold.rpt \
        "report_checks -sort_by_slack -fields $fields -path_delay min -format full_clock_expanded"
    tee -file reports/timing/hold.topN.rpt -quiet \
        "report_checks -sort_by_slack -fields $fields -path_delay min \
        -group_path_count $sta_top_n_paths"
    tee -quiet -file reports/timing/hold.failing.rpt \
        "report_checks -sort_by_slack -path_delay min -slack_max 0 -endpoint_path_count 1 \
        -group_path_count $sta_top_n_paths -format short"
    tee -quiet -file reports/timing/hold.endpoints.rpt \
        "report_checks -sort_by_slack -path_delay min -endpoint_path_count 1 \
        -group_path_count $sta_top_n_paths -format end"

    tee -file reports/timing/worst_slack.hold.rpt \
        "report_worst_slack -min"
    report_worst_slack_metric -hold

    tee -file reports/timing/total_negative_slack.hold.rpt \
        "report_tns -min"
    report_tns_metric -hold

    if { [sc_check_version 24 3 3932] && [llength [all_clocks]] > 0 } {
        puts "report: reports/timing/hold.histogram.rpt"
        tee -quiet -file reports/timing/hold.histogram.rpt \
            "report_timing_histogram -num_bins 20 -hold"
    }

    sc_report_scene_timing -delay min -name hold \
        -fields $fields -top_paths $sta_top_n_paths
}

if { [sc_cfg_tool_task_check_in_list unconstrained var reports] } {
    sc_report_banner "Unconstrained paths" \
        reports/timing/unconstrained.rpt \
        reports/timing/unconstrained.topN.rpt
    tee -file reports/timing/unconstrained.rpt \
        "report_checks -sort_by_slack -fields $fields -unconstrained -format full_clock_expanded \
        -path_group unconstrained"
    tee -file reports/timing/unconstrained.topN.rpt -quiet \
        "report_checks -sort_by_slack -fields $fields -unconstrained \
        -group_path_count $sta_top_n_paths"
}

if {
    [sc_cfg_tool_task_check_in_list clock_skew var reports] &&
    [llength [all_clocks]] > 0
} {
    sc_report_banner "Clock skew" \
        reports/clocks/skew.setup.rpt \
        reports/clocks/skew.hold.rpt
    tee -file reports/clocks/skew.setup.rpt \
        "report_clock_skew -setup -digits 4"
    report_clock_skew_metric -setup
    tee -file reports/clocks/skew.hold.rpt \
        "report_clock_skew -hold -digits 4"
    report_clock_skew_metric -hold
}

if { [sc_cfg_tool_task_check_in_list drv_violations var reports] } {
    sc_report_banner "DRV violators" \
        reports/checks/drv_violators.rpt
    tee -quiet -file reports/checks/drv_violators.rpt \
        "report_check_types -max_slew -max_capacitance -max_fanout -violators"
    report_erc_metrics
}

if { [sc_cfg_tool_task_check_in_list floating_nets var reports] } {
    sc_report_banner "Floating nets" \
        reports/checks/floating_nets.rpt
    tee -quiet -file reports/checks/floating_nets.rpt \
        "report_floating_nets -verbose"
}
if {
    [sc_cfg_tool_task_check_in_list overdriven_nets var reports] &&
    [sc_check_version 24 3 3461]
} {
    sc_report_banner "Overdriven nets" \
        reports/checks/overdriven_nets.rpt \
        reports/checks/overdriven_nets_with_parallel.rpt
    tee -quiet -file reports/checks/overdriven_nets.rpt \
        "report_overdriven_nets -verbose"
    utl::push_metrics_stage "sc__metric__{}_parallel"
    tee -quiet -file reports/checks/overdriven_nets_with_parallel.rpt \
        "report_overdriven_nets -include_parallel_driven -verbose"
    utl::pop_metrics_stage
}

utl::metric_int "timing__clocks" [llength [all_clocks]]

if { [sc_cfg_tool_task_check_in_list fmax var reports] } {
    set fmax_report ""
    if { [llength [all_clocks]] > 0 } {
        sc_report_banner "Fmax" \
            reports/clocks/fmax.rpt
        set fmax_report [open reports/clocks/fmax.rpt w]
        puts $fmax_report [format "%-30s %12s %12s %12s %10s" \
            "clock" "period" "min_period" "fmax_mhz" "registers"]
    } else {
        sc_report_banner "Fmax"
    }
    # Model on: https://github.com/The-OpenROAD-Project/OpenSTA/blob/f913c3ddbb3e7b4364ed4437c65ac78c4da9174b/tcl/Search.tcl#L1078
    set fmax_metric 0
    foreach clk [sta::sort_by_name [all_clocks]] {
        set clk_name [get_name $clk]
        set period [get_property $clk period]
        set regs [llength [all_registers -clock $clk]]
        set min_period [sta::find_clk_min_period $clk 1]
        if { $min_period == 0.0 } {
            puts $fmax_report [format "%-30s %12.4f %12s %12s %10d" \
                $clk_name $period "-" "-" $regs]
            continue
        }
        set fmax [expr { 1.0 / $min_period }]
        utl::metric_float "timing__fmax__clock:${clk_name}" $fmax
        puts "$clk_name fmax = [format %.2f [expr { $fmax / 1e6 }]] MHz (registers: $regs)"
        puts $fmax_report [format "%-30s %12.4f %12.4f %12.2f %10d" \
            $clk_name $period [sta::time_sta_ui $min_period] \
            [expr { $fmax / 1e6 }] $regs]
        set fmax_metric [expr { max($fmax_metric, $fmax) }]
    }
    if { $fmax_report != "" } {
        close $fmax_report
    }
    if { $fmax_metric == 0 } {
        # attempt to compute based on combinatorial path
        set fmax_valid true
        set max_path [find_timing_paths -unconstrained -path_delay max]
        if { $max_path == "" } {
            set fmax_valid false
        } else {
            set max_path_delay [$max_path data_arrival_time]
        }
        set min_path [find_timing_paths -unconstrained -path_delay min]
        if { $min_path == "" } {
            set fmax_valid false
        } else {
            set min_path_delay [$min_path data_arrival_time]
        }
        if { $fmax_valid } {
            set path_delay [expr { $max_path_delay - min(0, $min_path_delay) }]
            if { $path_delay > 0 } {
                set fmax_metric [expr { 1.0 / $path_delay }]
            }
        }
    }
    if { $fmax_metric > 0 } {
        utl::metric_float "timing__fmax" $fmax_metric
    }
}

if { [llength [all_clocks]] > 0 } {
    sc_report_banner "Clock properties" \
        reports/clocks/clocks.rpt
    tee -file "reports/clocks/clocks.rpt" {report_clock_properties}
}

# get logic depth of design
if { [sc_cfg_tool_task_check_in_list logicdepth var reports] } {
    utl::metric_int "design__logic__depth" \
        [sc_count_logic_depth -report reports/design/logic_depth.rpt]
}

if { [sc_cfg_tool_task_check_in_list power var reports] } {
    sc_report_banner "Power"
    if { [sc_has_sta_mcmm_support] } {
        foreach scene $sc_scenarios {
            if {
                ![sc_is_scene_enabled $scene power] &&
                ![sc_is_scene_enabled $scene leakagepower] &&
                ![sc_is_scene_enabled $scene dynamicpower]
            } {
                continue
            }
            puts "Power for scene: $scene"
            puts "report: reports/power/${scene}.rpt"

            tee -file reports/power/${scene}.rpt \
                "report_power -scene $scene"
        }
    } else {
        foreach corner [sta::corners] {
            set corner_name [$corner name]
            puts "Power for corner: $corner_name"
            puts "report: reports/power/${corner_name}.rpt"

            tee -file reports/power/${corner_name}.rpt \
                "report_power -corner $corner_name"
        }
    }

    report_power_metric -corner [sc_cfg_tool_task_get var power_corner]

    puts "report: reports/power/activity_annotation.rpt"
    tee -quiet -file reports/power/activity_annotation.rpt \
        "report_activity_annotation"
}

sc_report_banner "Design area"
report_design_area
report_design_area_metrics

if { [sc_cfg_tool_task_check_in_list design_stats var reports] } {
    sc_report_banner "Design statistics" \
        reports/design/area.rpt \
        reports/design/registers.rpt \
        reports/design/high_fanout.rpt \
        reports/design/logic_depth.rpt

    tee -quiet -file reports/design/area.rpt {report_design_area}

    set regs []
    foreach inst [all_registers] {
        lappend regs [get_full_name $inst]
    }
    set fid [open reports/design/registers.rpt w]
    foreach reg [lsort $regs] {
        puts $fid $reg
    }
    close $fid
    puts "Registers: [llength $regs]"

    set net_fanouts []
    foreach net [[ord::get_db_block] getNets] {
        set sig_type [$net getSigType]
        if { $sig_type == "POWER" || $sig_type == "GROUND" || $sig_type == "CLOCK" } {
            continue
        }
        set loads 0
        foreach iterm [$net getITerms] {
            if { [$iterm isInputSignal] } {
                incr loads
            }
        }
        foreach bterm [$net getBTerms] {
            if { [$bterm getIoType] == "OUTPUT" } {
                incr loads
            }
        }
        lappend net_fanouts [list [$net getName] $loads]
    }
    set net_fanouts [lsort -integer -decreasing -index 1 $net_fanouts]
    set fid [open reports/design/high_fanout.rpt w]
    puts $fid [format "%-60s %8s" "net" "fanout"]
    foreach net_info [lrange $net_fanouts 0 49] {
        lassign $net_info net_name net_fanout
        puts $fid [format "%-60s %8d" $net_name $net_fanout]
    }
    close $fid

    sc_count_logic_depth -report reports/design/logic_depth.rpt
}

if { ![sc_check_version 26 2 219] } {
    # get number of nets in design
    utl::metric_int "design__nets" [llength [[ord::get_db_block] getNets]]
}

if { ![sc_check_version 26 1 0] } {
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
}

if { [sc_cfg_tool_task_check_in_list unconstrained var reports] } {
    # get number of unconstrained endpoints
    with_output_to_variable endpoints {check_setup -unconstrained_endpoints}
    set unconstrained_endpoints [regexp -all -inline {[0-9]+} $endpoints]
    if { $unconstrained_endpoints == "" } {
        set unconstrained_endpoints 0
    }
    utl::metric_int "timing__unconstrained" $unconstrained_endpoints
}

# Write markers
foreach markerdb [[ord::get_db_block] getMarkerCategories] {
    if { [$markerdb getMarkerCount] == 0 } {
        continue
    }

    if { [lsearch -exact $sc_starting_markers [$markerdb getName]] != -1 } {
        continue
    }

    puts "report: reports/markers/${sc_topmodule}.[$markerdb getName].rpt"
    $markerdb writeTR "reports/markers/${sc_topmodule}.[$markerdb getName].rpt"
    puts "report: reports/markers/${sc_topmodule}.[$markerdb getName].json"
    $markerdb writeJSON "reports/markers/${sc_topmodule}.[$markerdb getName].json"
}

utl::push_metrics_stage "sc__cellarea__{}"
sc_report_banner "Cell usage" \
    reports/design/cell_usage.rpt
tee -file reports/design/cell_usage.rpt {report_cell_usage -verbose}
utl::pop_metrics_stage
