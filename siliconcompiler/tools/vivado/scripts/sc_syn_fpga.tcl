# set up project
create_project $sc_topmodule -force
set_property part $sc_partname [current_project]
set_property target_language Verilog [current_project]

foreach sc_pre_script [sc_cfg_tool_task_get prescript] {
    puts "Sourcing pre script: ${sc_pre_script}"
    source $sc_pre_script
}

# add imported files
if { [string equal [get_filesets -quiet sources_1] ""] } {
    create_fileset -srcset sources_1
}
add_files -norecurse -fileset [get_filesets sources_1] "inputs/${sc_topmodule}.v"
set_property top $sc_topmodule [current_fileset]

# add constraints
foreach xdc_file [sc_cfg_get_fileset $sc_designlib [sc_cfg_get option fileset] xdc] {
    if { [string equal [get_filesets -quiet constrs_1] ""] } {
        create_fileset -constrset constrs_1
    }
    add_files -norecurse -fileset [current_fileset] $xdc_file
}

# run synthesis
set synth_args []
lappend synth_args -directive [sc_cfg_tool_task_get var synth_directive]
set synth_mode [sc_cfg_tool_task_get var synth_mode]
if { $synth_mode != "none" } {
    lappend synth_args -mode $synth_mode
}
synth_design -top $sc_topmodule {*}$synth_args

opt_design

foreach sc_post_script [sc_cfg_tool_task_get postscript] {
    puts "Sourcing post script: ${sc_post_script}"
    source $sc_post_script
}
