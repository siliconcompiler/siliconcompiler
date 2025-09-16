###############################
# Read timing constraints
###############################

if { [file exists "inputs/${sc_topmodule}.sdc"] } {
    set sdc "inputs/${sc_topmodule}.sdc"
    puts "Reading SDC: ${sdc}"
    read_sdc $sdc
} else {
    set sdcs [sc_cfg_get_fileset $sc_designlib [sc_cfg_get option fileset] sdc]
    if { [llength $sdcs] > 0 } {
        foreach sdc $sdcs {
            puts "Reading SDC: ${sdc}"
            read_sdc $sdc
        }
    } else {
        # fall back on default auto generated constraints file
        set sdc [sc_cfg_tool_task_get var opensta_generic_sdc]
        puts "Reading SDC: ${sdc}"
        utl::warn FLW 1 "Defaulting back to default SDC"
        read_sdc "${sdc}"
    }
}
