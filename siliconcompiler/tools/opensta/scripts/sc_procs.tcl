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

proc sc_write_report_line { file line } {
    set fid [open $file w]
    puts $fid $line
    close $fid
}

proc sc_timing_corners { } {
    global sc_scenarios

    # A single corner would just duplicate the combined timing reports
    if { [llength $sc_scenarios] <= 1 } {
        return []
    }

    return $sc_scenarios
}

# Worst slack and TNS have no public report command that accepts a corner, so they are
# mirrored from the scene-aware accessors, which only exist in builds carrying the scene
# timing model.
proc sc_has_scene_slack { } {
    return [expr { [info commands sta::worst_slack_scene] ne "" }]
}

# The reports sc_report_corner_timing will write, so the section banner can name them all
# up front instead of announcing them one by one after the combined output.
proc sc_corner_timing_reports { args } {
    sta::parse_key_args "sc_corner_timing_reports" args \
        keys {-name} \
        flags {-unconstrained}

    set reports []
    foreach corner [sc_timing_corners] {
        set dir "reports/timing/scenarios/${corner}"
        set base "${dir}/$keys(-name).${corner}"

        lappend reports ${base}.rpt ${base}.topN.rpt

        if { [info exists flags(-unconstrained)] } {
            continue
        }

        lappend reports ${base}.failing.rpt ${base}.endpoints.rpt

        if { [sc_has_scene_slack] } {
            lappend reports \
                ${dir}/worst_slack.$keys(-name).${corner}.rpt \
                ${dir}/total_negative_slack.$keys(-name).${corner}.rpt
        }
    }

    return $reports
}

proc sc_report_corner_timing { args } {
    sta::parse_key_args "sc_report_corner_timing" args \
        keys {-delay -name -fields -top_paths} \
        flags {-unconstrained}

    global sta_report_default_digits

    set corners [sc_timing_corners]
    if { [llength $corners] == 0 } {
        return
    }

    # Mirror the combined reports exactly, adding only the corner selector. Each corner gets
    # its own directory, so the file names match their combined counterparts. Unconstrained
    # paths have no failing/endpoints counterpart, so they stop after topN.
    # $path_sel and $full_extra must be {*}-expanded: report_checks is invoked directly
    # here, so an unexpanded "-path_delay max" would arrive as a single argument.
    set unconstrained [info exists flags(-unconstrained)]
    if { $unconstrained } {
        set path_sel "-unconstrained"
        set full_extra "-path_group unconstrained"
    } else {
        set path_sel "-path_delay $keys(-delay)"
        set full_extra ""
    }

    # The corner is repeated in the file name, not just the directory, so reports gathered
    # from several corners into one place stay unique without renaming.
    foreach corner $corners {
        set dir "reports/timing/scenarios/${corner}"
        file mkdir $dir
        set base "${dir}/$keys(-name).${corner}"

        report_checks -sort_by_slack -fields $keys(-fields) {*}$path_sel \
            -format full_clock_expanded {*}$full_extra -corner $corner \
            > ${base}.rpt

        report_checks -sort_by_slack -fields $keys(-fields) {*}$path_sel \
            -group_path_count $keys(-top_paths) -corner $corner \
            > ${base}.topN.rpt

        if { $unconstrained } {
            continue
        }

        report_checks -sort_by_slack {*}$path_sel -slack_max 0 -endpoint_path_count 1 \
            -group_path_count $keys(-top_paths) -format short -corner $corner \
            > ${base}.failing.rpt

        report_checks -sort_by_slack {*}$path_sel -endpoint_path_count 1 \
            -group_path_count $keys(-top_paths) -format end -corner $corner \
            > ${base}.endpoints.rpt

        if { ![sc_has_scene_slack] } {
            continue
        }

        set scene_obj [sta::find_scene $corner]
        set scene_slack [sta::format_time \
            [sta::worst_slack_scene $scene_obj $keys(-delay)] $sta_report_default_digits]
        set scene_tns [sta::format_time \
            [sta::total_negative_slack_scene_cmd $scene_obj $keys(-delay)] \
            $sta_report_default_digits]

        sc_write_report_line ${dir}/worst_slack.$keys(-name).${corner}.rpt \
            "worst slack $keys(-delay) $scene_slack"
        sc_write_report_line ${dir}/total_negative_slack.$keys(-name).${corner}.rpt \
            "tns $keys(-delay) $scene_tns"
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
