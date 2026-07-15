###########################
# Count the logic depth of the critical path
###########################

proc sc_count_logic_depth { args } {
    sta::parse_key_args "sc_count_logic_depth" args \
        keys {-report} \
        flags {}

    set count 0
    set drivers []
    set paths [find_timing_paths -sort_by_slack]
    if { [llength $paths] > 0 } {
        set path_ref [[lindex $paths 0] path]
        set pins [$path_ref pins]
        foreach pin $pins {
            if { [$pin is_driver] } {
                incr count
                lappend drivers [get_full_name $pin]
            }
        }
    }
    # Subtract 1 to account for initial launch
    set depth [expr { max($count - 1, 0) }]

    if { [info exists keys(-report)] } {
        set fid [open $keys(-report) w]
        puts $fid "Logic depth: $depth"
        if { [llength $drivers] > 0 } {
            puts $fid ""
            puts $fid "Critical path drivers:"
            foreach driver $drivers {
                puts $fid "  $driver"
            }
        }
        close $fid
    }

    return $depth
}

proc sc_design_area { } {
    set area 0
    foreach inst [get_cells -hierarchical *] {
        set lib_cell [$inst liberty_cell]
        if { $lib_cell != "NULL" } {
            set area [expr { $area + [get_property $lib_cell area] }]
        }
    }
    return $area
}

proc sc_report_banner { title args } {
    set width 60
    puts ""
    puts [string repeat "=" $width]
    puts "== $title"
    foreach report $args {
        puts "== report: $report"
    }
    puts [string repeat "=" $width]
}

proc sc_display_report { report } {
    if { ![file exists $report] } {
        return
    }
    set fid [open $report r]
    set report_content [read $fid]
    close $fid
    puts $report_content
}

proc sc_path_group { args } {
    sta::parse_key_args "sc_path_group" args \
        keys {-name -to -from} \
        flags {}

    sta::check_argc_eq0 "sc_path_group" $args

    if { [llength $keys(-from)] == 0 } {
        return
    }
    if { [llength $keys(-to)] == 0 } {
        return
    }
    group_path -name $keys(-name) -from $keys(-from) -to $keys(-to)
}

proc sc_report_check_timing { } {
    sc_report_banner "Check timing setup"
    file mkdir reports/constraints/check_timing
    set checks "generated_clocks loops multiple_clock no_clock no_input_delay \
        no_output_delay unconstrained_endpoints"
    foreach check $checks {
        puts "report: reports/constraints/check_timing/${check}.rpt"
        check_setup -${check} > reports/constraints/check_timing/${check}.rpt
    }
}

proc sc_report_corner_timing { args } {
    sta::parse_key_args "sc_report_corner_timing" args \
        keys {-delay -name -fields -top_paths} \
        flags {}

    global sc_scenarios

    # A single corner would just duplicate the combined timing reports
    if { [llength $sc_scenarios] <= 1 } {
        return
    }

    foreach corner $sc_scenarios {
        puts "report: reports/timing/$keys(-name).${corner}.rpt"
        report_checks -sort_by_slack -fields $keys(-fields) -path_delay $keys(-delay) \
            -format full_clock_expanded -corner $corner \
            > reports/timing/$keys(-name).${corner}.rpt
        puts "report: reports/timing/$keys(-name).topN.${corner}.rpt"
        report_checks -sort_by_slack -path_delay $keys(-delay) \
            -group_path_count $keys(-top_paths) -corner $corner \
            > reports/timing/$keys(-name).topN.${corner}.rpt
    }
}

proc sc_report_scenarios { } {
    global opensta_timing_mode
    global sc_scenarios
    global sc_sdc_files_read

    file mkdir reports/constraints
    set fid [open reports/constraints/scenarios.rpt w]

    puts $fid "Timing scenarios:"
    if { $opensta_timing_mode == "asic" } {
        foreach scenario $sc_scenarios {
            puts $fid "  ${scenario}:"
            puts $fid \
                "    libcorner: [sc_cfg_get constraint timing scenario $scenario libcorner]"
            puts $fid \
                "    pexcorner: [sc_cfg_get constraint timing scenario $scenario pexcorner]"
            puts $fid "    mode: [sc_cfg_get constraint timing scenario $scenario mode]"
            puts $fid "    checks: [sc_cfg_get constraint timing scenario $scenario check]"
        }
    } else {
        foreach scenario $sc_scenarios {
            puts $fid "  ${scenario}"
        }
    }

    puts $fid ""
    puts $fid "SDC files loaded:"
    if { [info exists sc_sdc_files_read] && [llength $sc_sdc_files_read] > 0 } {
        foreach sdc $sc_sdc_files_read {
            puts $fid "  $sdc"
        }
    } else {
        puts $fid "  none"
    }
    close $fid

    sc_display_report reports/constraints/scenarios.rpt
}

proc sc_is_scene_enabled { scene check } {
    global opensta_timing_mode
    if { $opensta_timing_mode == "asic" } {
        if { [lsearch -exact [sc_cfg_get constraint timing scenario $scene check] $check] != -1 } {
            return true
        } else {
            return false
        }
    } else {
        return true
    }
}
