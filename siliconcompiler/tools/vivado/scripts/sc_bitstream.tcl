open_checkpoint "inputs/${sc_topmodule}.dcp"

foreach sc_pre_script [sc_cfg_tool_task_get prescript] {
    puts "Sourcing pre script: ${sc_pre_script}"
    source $sc_pre_script
}

write_bitstream -force -file "outputs/${sc_topmodule}.bit"

foreach sc_post_script [sc_cfg_tool_task_get postscript] {
    puts "Sourcing post script: ${sc_post_script}"
    source $sc_post_script
}
