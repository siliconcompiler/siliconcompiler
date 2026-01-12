if { [sc_cfg_tool_task_get var load_sdcs] } {
    write_sdc "outputs/${sc_topmodule}.sdc"
}
