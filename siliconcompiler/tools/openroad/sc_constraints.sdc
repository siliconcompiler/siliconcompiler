# Default constraints file that sets up clocks based on definitions in schema.

source sc_manifest.tcl

set sc_design [sc_top]

if {[dict exists $sc_cfg datasheet] && [dict exists $sc_cfg datasheet $sc_design]} {
    foreach pin [dict keys [dict get $sc_cfg datasheet $sc_design pin]] {
        if {[dict get $sc_cfg datasheet $sc_design pin $pin type global] == "clk"} {
            # If clock...

            set periodtuple [dict get $sc_cfg datasheet $sc_design pin $pin tperiod global]
            set period [sta::time_sta_ui [lindex $periodtuple 1]]
            set jittertuple [dict get $sc_cfg datasheet $sc_design pin $pin tjitter global]
            set jitter [sta::time_sta_ui [lindex $jittertuple 1]]

            create_clock [get_ports $pin] -name $pin -period $period
            set_clock_uncertainty $jitter [get_clock $pin]
        }
    }
}
