proc reopenStdout {file} {
    close stdout
    open $file w        ;# The standard channels are special
}

set fields "{capacitance slew input_pins nets fanout}"

report_checks -fields $fields -path_delay max -format full_clock_expanded > reports/$sc_design.setup.rpt

report_checks -fields $fields -path_delay min -format full_clock_expanded > "reports/$sc_design.hold.rpt"

report_checks  -fields $fields -unconstrained -format full_clock_expanded > "reports/$sc_design.unconstrained.rpt"

report_clock_skew > "reports/$sc_design.clockskew.rpt"

report_wns > "reports/$sc_design.wns.rpt"

report_tns > "reports/$sc_design.tns.rpt"

report_power > "reports/$sc_design.power.rpt"

