###############################
# Read timing constraints
###############################

if { [sc_has_input_files sdc "input constraint sdc"] } {
    foreach sdc [sc_get_input_files sdc "input constraint sdc"] {
        puts "Reading SDC: ${sdc}"
        read_sdc $sdc
    }
} else {
    # fall back on default auto generated constraints file
    set sdc [sc_cfg_tool_task_get {file} opensta_generic_sdc]
    puts "Reading SDC: ${sdc}"
    utl::warn FLW 1 "Defaulting back to default SDC"
    read_sdc "${sdc}"
}
