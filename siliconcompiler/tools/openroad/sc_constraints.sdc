# Default constraints file that sets up clocks based on definitions in schema.

source sc_manifest.tcl

set sc_design [sc_get_entrypoint]

if {[dict exists $sc_cfg datasheet] && [dict exists $sc_cfg datasheet $sc_design]} {
    foreach pin [dict keys [dict get $sc_cfg datasheet $sc_design pin]] {
        if {[dict get $sc_cfg datasheet $sc_design pin $pin type global] == "clk"} {
            # If clock...

            set periodtuple [dict get $sc_cfg datasheet $sc_design pin $pin tperiod global]
            set period [lindex $periodtuple 1]
            set period_ns [expr $period * pow(10, 9)]

            create_clock [get_ports $pin] -name $pin  -period $period_ns
        }
    }
}
