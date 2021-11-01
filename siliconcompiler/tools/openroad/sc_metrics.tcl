proc reopenStdout {file} {
    close stdout
    open $file w        ;# The standard channels are special
}


###############################
# Report Metrics
###############################

set fields "{capacitance slew input_pins nets fanout}"
set PREFIX "SC_METRIC:"

puts "$PREFIX report_checks -path_delay max"
report_checks -fields $fields -path_delay max -format full_clock_expanded

puts "$PREFIX report_checks -path_delay min"
report_checks -fields $fields -path_delay min -format full_clock_expanded

puts "$PREFIX unconstrained"
report_checks  -fields $fields -unconstrained -format full_clock_expanded

#TODO: should only be executed when there is a clock
#puts "$PREFIX clock_skew"
#report_clock_skew

puts "$PREFIX wns"
report_wns

puts "$PREFIX tns"
report_tns

puts "$PREFIX setupslack"
report_worst_slack -max

puts "$PREFIX holdslack"
report_worst_slack -min

puts "$PREFIX power"
report_power

puts "$PREFIX cellarea"
report_design_area
