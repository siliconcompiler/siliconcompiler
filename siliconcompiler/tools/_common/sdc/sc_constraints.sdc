# Default constraints file that sets up clocks based on definitions in schema.

source sc_manifest.tcl > /dev/null

### Create clocks
if { [sc_cfg_exists datasheet pin] } {
    set clock_idx 0
    foreach pin [dict keys [sc_cfg_get datasheet pin]] {
        if { [sc_cfg_get datasheet pin $pin type global] == "clock" } {
            # If clock...

            set periodtuple [sc_cfg_get datasheet pin $pin tperiod global]
            set period [sta::time_sta_ui [lindex $periodtuple 1]]
            set jittertuple [sc_cfg_get datasheet pin $pin tjitter global]
            set jitter [sta::time_sta_ui [lindex $jittertuple 1]]

            set clk_name "clk${clock_idx}"
            incr clock_idx

            set period_fmt \
                [sta::format_time [sta::time_ui_sta $period] 3][sta::unit_scale_abbreviation time]
            set jitter_fmt \
                [sta::format_time [sta::time_ui_sta $jitter] 3][sta::unit_scale_abbreviation time]
            puts \
                "Creating clock $clk_name with ${period_fmt}s period and ${jitter_fmt}s jitter."
            create_clock -name $clk_name -period $period $pin
            set_clock_uncertainty $jitter [get_clock $clk_name]
        }
    }
}

### Create IO constraints
set sc_sdc_buffer []
if { [sc_cfg_tool_task_exists {var} sdc_buffer] } {
    set sc_sdc_buffer [sc_cfg_tool_task_get {var} sdc_buffer]
}
set buffer_cell "NULL"
if { [llength $sc_sdc_buffer] == 0 } {
    foreach cell [get_lib_cells *] {
        if { [get_property $cell is_buffer] } {
            # Find first buffer and use that as IO constraints
            set buffer_cell $cell
            break
        }
    }
} else {
    set buffer_cell [get_lib_cells [lindex $sc_sdc_buffer 0]]
}

if { $buffer_cell != "NULL" && $buffer_cell != "" } {
    puts "Using [get_name $buffer_cell] as the SDC IO constraint cell"

    set driving_port "NULL"
    set load_cap 0.0
    set port_itr [$buffer_cell liberty_port_iterator]
    while { [$port_itr has_next] } {
        set port [$port_itr next]
        set pcap [$port capacitance NULL max]
        if { [get_property $port direction] == "input" } {
            set load_cap [expr { 10 * $pcap }]
        } elseif { [get_property $port direction] == "output" } {
            set driving_port [get_name $port]
        }
    }
    $port_itr finish

    if { $load_cap > 0.0 } {
        set cap_fmt [sta::format_capacitance $load_cap 3][sta::unit_scale_abbreviation capacitance]
        puts "Setting output load constraint to ${cap_fmt}F."
        set_load [sta::capacitance_sta_ui $load_cap] [all_outputs]
    }
    if { $driving_port != "NULL" } {
        puts "Setting input driving pin constraint to [get_name $buffer_cell]/$driving_port."
        set_driving_cell -lib_cell [$buffer_cell name] -pin $driving_port [all_inputs]
    }
}
