# set up project
create_project $sc_design -force
set_property part $sc_partname [current_project]
set_property target_language Verilog [current_project]

# add imported files
if { [string equal [get_filesets -quiet sources_1] ""] } {
    create_fileset -srcset sources_1
}
add_files -norecurse -fileset [get_filesets sources_1] "inputs/$sc_design.v"
set_property top $sc_design [current_fileset]

# add constraints
if { $sc_constraint != "" } {
    if { [string equal [get_filesets -quiet constrs_1] ""] } {
        create_fileset -constrset constrs_1
    }
    foreach item $sc_constraint {
        add_files -norecurse -fileset [current_fileset] $item
    }
}

# run synthesis
set synth_args []
lappend synth_args -directive [lindex [sc_cfg_tool_task_get var synth_directive] 0]
set synth_mode [lindex [sc_cfg_tool_task_get var synth_mode] 0]
if { $synth_mode != "none" } {
    lappend synth_args -mode $synth_mode
}
synth_design -top $sc_design {*}$synth_args

opt_design
