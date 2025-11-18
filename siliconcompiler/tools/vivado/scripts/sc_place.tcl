open_checkpoint "inputs/${sc_topmodule}.dcp"

if { [sc_cfg_tool_task_exists prescript] } {
    foreach sc_pre_script [sc_cfg_tool_task_get prescript] {
        puts "Sourcing pre script: ${sc_pre_script}"
        source $sc_pre_script
    }
}

place_design

if { [sc_cfg_tool_task_exists postscript] } {
    foreach sc_post_script [sc_cfg_tool_task_get postscript] {
        puts "Sourcing post script: ${sc_post_script}"
        source $sc_post_script
    }
}
