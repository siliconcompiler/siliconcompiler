if { [sc_cfg_tool_task_get var load_sdcs] } {
    puts "Writing SDC: outputs/${sc_topmodule}.sdc"
    write_sdc "outputs/${sc_topmodule}.sdc"
}
