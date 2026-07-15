###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
###############################

# APR Parameters
set sc_timing_mode [sc_cfg_tool_task_get var timing_mode]

set sc_mainlib []
set sc_logiclibs []
set sc_delaymodel []
set sc_scenarios []
if { $opensta_timing_mode == "asic" } {
    set sc_mainlib [sc_cfg_get asic mainlib]
    set sc_logiclibs [sc_cfg_get asic asiclib]
    set sc_delaymodel [sc_cfg_get asic delaymodel]

    foreach corner [dict keys [sc_cfg_get constraint timing scenario]] {
        if {
            $sc_timing_mode == {} ||
            [sc_cfg_get constraint timing scenario $corner mode] == $sc_timing_mode
        } {
            lappend sc_scenarios $corner
        }
    }
} elseif { $opensta_timing_mode == "fpga" } {
    set sc_mainlib [sc_cfg_get fpga device]
    set sc_logiclibs [sc_cfg_get fpga device]
    set sc_delaymodel "nldm"
    lappend sc_scenarios "typical"
}

###############################
# Source helper functions
###############################

source "$sc_refdir/sc_procs.tcl"

###############################
# Read Files
###############################

# Read Liberty
puts "Defining timing corners: $sc_scenarios"
define_corners {*}$sc_scenarios

if { $opensta_timing_mode == "asic" } {
    foreach corner $sc_scenarios {
        foreach lib $sc_logiclibs {
            set lib_filesets []
            foreach libcorner [sc_cfg_get constraint timing scenario $corner libcorner] {
                if {
                    [sc_cfg_exists library $lib asic \
                        libcornerfileset $libcorner $sc_delaymodel]
                } {
                    lappend lib_filesets \
                        {*}[sc_cfg_get library $lib asic \
                            libcornerfileset $libcorner $sc_delaymodel]
                }
            }
            foreach lib_file [sc_cfg_get_fileset $lib $lib_filesets liberty] {
                puts "Reading liberty file for ${corner} ($libcorner): ${lib_file}"
                read_liberty -corner $corner $lib_file
            }
        }
    }
} elseif { $opensta_timing_mode == "fpga" } {
    foreach corner $sc_scenarios {
        foreach lib $sc_logiclibs {
            foreach lib_fileset [sc_cfg_get library $lib tool opensta liberty_filesets] {
                foreach lib_file [sc_cfg_get_fileset $lib $lib_fileset liberty] {
                    puts "Reading liberty file for ${corner} (typical): ${lib_file}"
                    read_liberty -corner ${corner} $lib_file
                }
            }
        }
    }
}

# Read Verilog
if { [file exists "inputs/${sc_topmodule}.vg"] } {
    puts "Reading netlist verilog: inputs/${sc_topmodule}.vg"
    read_verilog "inputs/${sc_topmodule}.vg"
} else {
    foreach fs [sc_get_filesets] {
        lassign $fs fs_lib fs_name
        foreach verilog [sc_cfg_get_fileset $fs_lib $fs_name verilog] {
            puts "Reading netlist verilog: ${verilog}"
            read_verilog $verilog
        }
    }
}
link_design $sc_topmodule

# Read SDC (in order of priority)
# Record every SDC read so sc_report_scenarios can list them
set sc_sdc_files_read []
if { [file exists "inputs/${sc_topmodule}.sdc"] } {
    # get from previous step
    puts "Reading SDC: inputs/${sc_topmodule}.sdc"
    read_sdc "inputs/${sc_topmodule}.sdc"
    lappend sc_sdc_files_read "inputs/${sc_topmodule}.sdc"
} else {
    set sdc_files []
    set base_sdcs []
    foreach fs [sc_get_filesets] {
        lassign $fs fs_lib fs_name
        lappend base_sdcs {*}[sc_cfg_get_fileset $fs_lib $fs_name sdc]
    }
    foreach sdc $base_sdcs {
        # read step constraint if exists
        puts "Reading SDC: ${sdc}"
        read_sdc $sdc
        lappend sdc_files $sdc
        lappend sc_sdc_files_read $sdc
    }

    if { $sc_timing_mode != {} } {
        foreach sdcinfo [sc_cfg_get constraint timing mode $sc_timing_mode sdcfileset] {
            lassign $sdcinfo mode_lib mode_fileset
            foreach fs [sc_get_filesets -library $mode_lib -filesets $mode_fileset] {
                lassign $fs fs_lib fs_name
                foreach sdc [sc_cfg_get_fileset $fs_lib $fs_name sdc] {
                    if { [lsearch -exact $sdc_files $sdc] == -1 } {
                        # read step constraint if exists
                        puts "Reading mode (${sc_timing_mode}) SDC: ${sdc}"
                        lappend sdc_files $sdc
                        read_sdc $sdc
                        lappend sc_sdc_files_read "(${sc_timing_mode}) $sdc"
                    }
                }
            }
        }
    }
}

# Create path groups
if { [llength [sta::path_group_names]] == 0 } {
    sc_path_group -name in2out -from [all_inputs -no_clocks] -to [all_outputs]

    if {
        [llength [all_clocks]] == 1 ||
        ![sc_cfg_tool_task_get var unique_path_groups_per_clock]
    } {
        sc_path_group -name in2reg -from [all_inputs -no_clocks] -to [all_registers]
        sc_path_group -name reg2reg -from [all_registers] -to [all_registers]
        sc_path_group -name reg2out -from [all_registers] -to [all_outputs]
    } else {
        foreach clock [all_clocks] {
            set clk_name [get_property $clock name]
            sc_path_group -name in2reg.${clk_name} \
                -from [all_inputs -no_clocks] \
                -to [all_registers -clock $clock]
            sc_path_group -name reg2reg.${clk_name} \
                -from [all_registers -clock $clock] \
                -to [all_registers -clock $clock]
            sc_path_group -name reg2out.${clk_name} \
                -from [all_registers -clock $clock] \
                -to [all_outputs]
        }
    }
}
puts "Timing path groups: [sta::path_group_names]"

###############################

if { $opensta_timing_mode == "asic" } {
    foreach corner $sc_scenarios {
        set pex_corner [sc_cfg_get constraint timing scenario $corner pexcorner]

        set spef_file "inputs/${sc_topmodule}.${pex_corner}.spef"
        if { [file exists $spef_file] } {
            puts "Reading SPEF ($corner / $pex_corner): $spef_file"
            read_spef -corner $corner $spef_file
        }
    }

    foreach corner $sc_scenarios {
        set pex_corner [sc_cfg_get constraint timing scenario $corner pexcorner]

        set input_sdf_file "inputs/${sc_topmodule}.${pex_corner}.sdf"
        if { [file exists $input_sdf_file] } {
            puts "Reading SDF ($corner / $pex_corner): $input_sdf_file"
            read_sdf -corner $corner $input_sdf_file
        }
    }
} elseif { $opensta_timing_mode == "fpga" } {
    foreach corner $sc_scenarios {
        set input_sdf_file "inputs/${sc_topmodule}.typical.sdf"
        if { [file exists $input_sdf_file] } {
            puts "Reading SDF ($corner / typical): $input_sdf_file"
            read_sdf -corner $corner $input_sdf_file
        }
    }
}

###############################
# Read power activities (VCD)
###############################
# Vector-based power analysis: annotate switching activity from a VCD so the
# report_power calls below use real activity instead of default toggle rates.

set sc_power_activities [sc_cfg_tool_task_get var power_activities]
set sc_read_vcd false
if { [llength $sc_power_activities] == 0 } {
    # Default: read the VCD from the active filesets (or the step input) with no
    # scope, i.e. the VCD hierarchy is assumed to match the design top.
    set vcd_files []
    set input_vcd "inputs/${sc_topmodule}.vcd"
    if { [file exists $input_vcd] } {
        lappend vcd_files $input_vcd
    } else {
        foreach fs [sc_get_filesets] {
            lassign $fs fs_lib fs_name
            lappend vcd_files {*}[sc_cfg_get_fileset $fs_lib $fs_name vcd]
        }
    }
    foreach vcd $vcd_files {
        puts "Reading power activities (VCD): $vcd"
        read_vcd $vcd
        set sc_read_vcd true
    }
} else {
    # Configured: each entry maps a VCD scope (the instance path of the design
    # top within the VCD) to a (library, fileset) source containing the VCD.
    foreach activity $sc_power_activities {
        lassign $activity scope act_lib act_fileset
        foreach fs [sc_get_filesets -library $act_lib -filesets $act_fileset] {
            lassign $fs fs_lib fs_name
            foreach vcd [sc_cfg_get_fileset $fs_lib $fs_name vcd] {
                puts "Reading power activities (VCD) for scope '$scope': $vcd"
                read_vcd -scope $scope $vcd
                set sc_read_vcd true
            }
        }
    }
    # Warn: activities were explicitly configured, so falling back to default
    # toggle rates would produce misleading power numbers.
    if { !$sc_read_vcd } {
        puts "Warning: power_activities is configured but no VCD files were\
            resolved from the referenced filesets"
    }
}

# Report how much of the design's switching activity was annotated from the VCD
if { $sc_read_vcd } {
    puts "Reporting power activity annotation coverage"
    puts "report: reports/power/activity_annotation.rpt"
    file mkdir reports/power
    report_activity_annotation -report_annotated -report_unannotated > \
        reports/power/activity_annotation.rpt
}

###############################
# Write SDF
###############################

if { [sc_cfg_tool_task_get var write_sdf] } {
    foreach corner $sc_scenarios {
        puts "Writing SDF for $corner"
        write_sdf -corner $corner \
            -include_typ \
            "outputs/${sc_topmodule}.${corner}.sdf"
    }
}

###############################
# Write Liberty
###############################

if { [sc_cfg_tool_task_get var write_liberty] } {
    foreach corner $sc_scenarios {
        puts "Writing liberty model for $corner"
        write_timing_model -library_name "${sc_topmodule}_${corner}" \
            -corner $corner \
            "outputs/${sc_topmodule}.${corner}.lib"
    }
}

###############################
# Report Metrics
###############################

file mkdir \
    reports/checks \
    reports/clocks \
    reports/constraints \
    reports/design \
    reports/power \
    reports/timing

set opensta_top_n_paths [sc_cfg_tool_task_get var top_n_paths]

set fields "{capacitance slew input_pins hierarcial_pins net fanout}"
set PREFIX "SC_METRIC:"

puts "$PREFIX timeunit"
puts [sta::unit_scale_abbreviation time]

if { [sc_cfg_tool_task_check_in_list scenarios var reports] } {
    sc_report_banner "Timing scenarios" \
        reports/constraints/scenarios.rpt
    sc_report_scenarios
}

if { [sc_cfg_tool_task_check_in_list check_setup var reports] } {
    sc_report_check_timing
}

if { [sc_cfg_tool_task_check_in_list setup var reports] } {
    sc_report_banner "Setup timing" \
        reports/timing/setup.rpt \
        reports/timing/setup.topN.rpt \
        reports/timing/setup.failing.rpt \
        reports/timing/setup.endpoints.rpt \
        reports/timing/worst_slack.setup.rpt \
        reports/timing/total_negative_slack.setup.rpt
    puts "$PREFIX report_checks -path_delay max"
    report_checks -sort_by_slack -fields $fields -path_delay max \
        -format full_clock_expanded \
        > reports/timing/setup.rpt
    sc_display_report reports/timing/setup.rpt
    report_checks -sort_by_slack -path_delay max -group_path_count $opensta_top_n_paths \
        > reports/timing/setup.topN.rpt
    report_checks -sort_by_slack -path_delay max -slack_max 0 -endpoint_path_count 1 \
        -group_path_count $opensta_top_n_paths -format short \
        > reports/timing/setup.failing.rpt
    report_checks -sort_by_slack -path_delay max -endpoint_path_count 1 \
        -group_path_count $opensta_top_n_paths -format end \
        > reports/timing/setup.endpoints.rpt
    sc_report_corner_timing -delay max -name setup \
        -fields $fields -top_paths $opensta_top_n_paths

    puts "$PREFIX setupslack"
    report_worst_slack -max > reports/timing/worst_slack.setup.rpt
    sc_display_report reports/timing/worst_slack.setup.rpt

    puts "$PREFIX setuppaths"
    puts [sta::endpoint_violation_count max]

    puts "$PREFIX setuptns"
    report_tns > reports/timing/total_negative_slack.setup.rpt
    sc_display_report reports/timing/total_negative_slack.setup.rpt
}

if { [sc_cfg_tool_task_check_in_list hold var reports] } {
    sc_report_banner "Hold timing" \
        reports/timing/hold.rpt \
        reports/timing/hold.topN.rpt \
        reports/timing/hold.failing.rpt \
        reports/timing/hold.endpoints.rpt \
        reports/timing/worst_slack.hold.rpt \
        reports/timing/total_negative_slack.hold.rpt
    puts "$PREFIX report_checks -path_delay min"
    report_checks -sort_by_slack -fields $fields -path_delay min \
        -format full_clock_expanded \
        > reports/timing/hold.rpt
    report_checks -sort_by_slack -path_delay min -group_path_count $opensta_top_n_paths \
        > reports/timing/hold.topN.rpt
    report_checks -sort_by_slack -path_delay min -slack_max 0 -endpoint_path_count 1 \
        -group_path_count $opensta_top_n_paths -format short \
        > reports/timing/hold.failing.rpt
    report_checks -sort_by_slack -path_delay min -endpoint_path_count 1 \
        -group_path_count $opensta_top_n_paths -format end \
        > reports/timing/hold.endpoints.rpt
    sc_report_corner_timing -delay min -name hold \
        -fields $fields -top_paths $opensta_top_n_paths

    puts "$PREFIX holdslack"
    report_worst_slack -min > reports/timing/worst_slack.hold.rpt
    sc_display_report reports/timing/worst_slack.hold.rpt

    puts "$PREFIX holdpaths"
    puts [sta::endpoint_violation_count min]

    puts "$PREFIX holdtns"
    report_tns -min > reports/timing/total_negative_slack.hold.rpt
    puts "tns [sta::time_sta_ui [sta::total_negative_slack_cmd min]]"
}

if { [sc_cfg_tool_task_check_in_list unconstrained var reports] } {
    sc_report_banner "Unconstrained paths" \
        reports/timing/unconstrained.rpt \
        reports/timing/unconstrained.topN.rpt
    report_checks -sort_by_slack -fields $fields -unconstrained \
        -format full_clock_expanded \
        -path_group unconstrained > reports/timing/unconstrained.rpt
    sc_display_report reports/timing/unconstrained.rpt
    report_checks -sort_by_slack -unconstrained -group_path_count $opensta_top_n_paths \
        > reports/timing/unconstrained.topN.rpt
}

if {
    [sc_cfg_tool_task_check_in_list clock_skew var reports] &&
    [llength [all_clocks]] > 0
} {
    sc_report_banner "Clock skew" \
        reports/clocks/skew.setup.rpt \
        reports/clocks/skew.hold.rpt
    puts "$PREFIX setupskew"
    report_clock_skew -setup -digits 4 > reports/clocks/skew.setup.rpt
    sc_display_report reports/clocks/skew.setup.rpt
    puts "$PREFIX holdskew"
    report_clock_skew -hold -digits 4 > reports/clocks/skew.hold.rpt
    sc_display_report reports/clocks/skew.hold.rpt
}

if { [sc_cfg_tool_task_check_in_list drv_violations var reports] } {
    sc_report_banner "DRV violators" \
        reports/checks/drv_violators.rpt
    puts "$PREFIX drvs"
    report_check_types -max_slew -max_capacitance -max_fanout -violators -no_line_splits \
        > reports/checks/drv_violators.rpt
}

if { [sc_cfg_tool_task_check_in_list fmax var reports] } {
    set fmax_report ""
    if { [llength [all_clocks]] > 0 } {
        sc_report_banner "Fmax" \
            reports/clocks/fmax.rpt
        set fmax_report [open reports/clocks/fmax.rpt w]
        puts $fmax_report [format "%-30s %12s %12s %12s %10s" \
            "clock" "period" "min_period" "fmax_mhz" "registers"]
    } else {
        sc_report_banner "Fmax"
    }
    # Model on: https://github.com/The-OpenROAD-Project/OpenSTA/blob/f913c3ddbb3e7b4364ed4437c65ac78c4da9174b/tcl/Search.tcl#L1078
    set fmax_metric 0
    foreach clk [sta::sort_by_name [all_clocks]] {
        puts "$PREFIX fmax"
        set clk_name [get_name $clk]
        set period [get_property $clk period]
        set regs [llength [all_registers -clock $clk]]
        set min_period [sta::find_clk_min_period $clk 1]
        if { $min_period == 0.0 } {
            puts $fmax_report [format "%-30s %12.4f %12s %12s %10d" \
                $clk_name $period "-" "-" $regs]
            continue
        }
        set fmax [expr { 1.0 / $min_period }]
        puts "$clk_name fmax = [format %.2f [expr { $fmax / 1e6 }]] MHz"
        puts $fmax_report [format "%-30s %12.4f %12.4f %12.2f %10d" \
            $clk_name $period [sta::time_sta_ui $min_period] \
            [expr { $fmax / 1e6 }] $regs]
        set fmax_metric [expr { max($fmax_metric, $fmax) }]
    }
    if { $fmax_report != "" } {
        close $fmax_report
    }
    if { $fmax_metric > 0 } {
        puts "fmax = [format %.2f [expr { $fmax_metric / 1e6 }]] MHz"
    }
}

# get logic depth of design
if { [sc_cfg_tool_task_check_in_list logicdepth var reports] } {
    puts "$PREFIX logicdepth"
    puts [sc_count_logic_depth -report reports/design/logic_depth.rpt]
}

if { [sc_cfg_tool_task_check_in_list power var reports] } {
    sc_report_banner "Power"
    puts "$PREFIX power"
    foreach scene $sc_scenarios {
        if {
            ![sc_is_scene_enabled $scene power] &&
            ![sc_is_scene_enabled $scene leakagepower] &&
            ![sc_is_scene_enabled $scene dynamicpower]
        } {
            continue
        }
        puts "Power for scene: $scene"
        puts "report: reports/power/${scene}.rpt"
        report_power -corner $scene > reports/power/${scene}.rpt
        sc_display_report reports/power/${scene}.rpt
    }
}

if { [sc_cfg_tool_task_check_in_list design_stats var reports] } {
    sc_report_banner "Design statistics" \
        reports/design/area.rpt \
        reports/design/registers.rpt \
        reports/design/high_fanout.rpt \
        reports/design/logic_depth.rpt

    set fid [open reports/design/area.rpt w]
    puts $fid "Design area: [sc_design_area]"
    close $fid

    set design_regs []
    foreach inst [all_registers] {
        lappend design_regs [get_full_name $inst]
    }
    set fid [open reports/design/registers.rpt w]
    foreach reg [lsort $design_regs] {
        puts $fid $reg
    }
    close $fid

    set net_fanouts []
    foreach net [get_nets -hierarchical *] {
        set loads 0
        foreach pin [get_pins -quiet -of_objects $net] {
            if { [get_property $pin direction] == "input" } {
                incr loads
            }
        }
        lappend net_fanouts [list [get_full_name $net] $loads]
    }
    set net_fanouts [lsort -integer -decreasing -index 1 $net_fanouts]
    set fid [open reports/design/high_fanout.rpt w]
    puts $fid [format "%-60s %8s" "net" "fanout"]
    foreach net_info [lrange $net_fanouts 0 49] {
        lassign $net_info net_name net_fanout
        puts $fid [format "%-60s %8d" $net_name $net_fanout]
    }
    close $fid

    sc_count_logic_depth -report reports/design/logic_depth.rpt
} else {
    sc_report_banner "Design statistics"
}
puts "$PREFIX cells"
puts [llength [get_cells *]]

puts "$PREFIX cellarea"
puts [sc_design_area]

# get number of nets in design
puts "$PREFIX nets"
puts [llength [get_nets *]]

# get number of registers
puts "$PREFIX registers"
puts [llength [all_registers]]

# get number of buffers
set bufs 0
set invs 0
foreach inst [get_cells -hierarchical *] {
    set cell [$inst cell]
    if { $cell == "NULL" } {
        continue
    }
    set liberty_cell [$cell liberty_cell]
    if { $liberty_cell == "NULL" } {
        continue
    }
    if { [$liberty_cell is_buffer] } {
        incr bufs
    } elseif { [$liberty_cell is_inverter] } {
        incr invs
    }
}
puts "$PREFIX buffers"
puts $bufs
puts "$PREFIX inverters"
puts $invs

puts "$PREFIX pins"
puts [llength [get_ports *]]

# get number of unconstrained endpoints
if { [sc_cfg_tool_task_check_in_list unconstrained var reports] } {
    with_output_to_variable endpoints {check_setup -unconstrained_endpoints}
    set unconstrained_endpoints [regexp -all -inline {[0-9]+} $endpoints]
    if { $unconstrained_endpoints == "" } {
        set unconstrained_endpoints 0
    }
    puts "$PREFIX unconstrained"
    puts $unconstrained_endpoints
}
