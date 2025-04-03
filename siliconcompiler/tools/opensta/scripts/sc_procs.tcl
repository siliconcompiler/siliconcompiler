###########################
# Count the logic depth of the critical path
###########################

proc sc_count_logic_depth { } {
    set count 0
    set paths [find_timing_paths -sort_by_slack]
    if { [llength $paths] == 0 } {
        return 0
    }
    set path_ref [[lindex $paths 0] path]
    set pins [$path_ref pins]
    foreach pin $pins {
        if { [$pin is_driver] } {
            incr count
        }
        set vertex [lindex [$pin vertices] 0]
        # Stop at clock vertex
        if { [$vertex is_clock] } {
            break
        }
    }
    # Subtract 1 to account for initial launch
    return [expr { $count - 1 }]
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
