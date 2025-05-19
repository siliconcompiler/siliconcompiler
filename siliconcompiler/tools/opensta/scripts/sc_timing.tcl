###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
###############################

set sc_tool opensta
set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_flow [sc_cfg_get option flow]
set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]

set sc_refdir [sc_cfg_tool_task_get refdir]

# Design
set sc_design [sc_top]

# APR Parameters
set sc_targetlibs [sc_get_asic_libraries logic]
set sc_mainlib [lindex $sc_targetlibs 0]
set sc_delaymodel [sc_cfg_get asic delaymodel]
set sc_timing_mode [lindex [sc_cfg_tool_task_get var timing_mode] 0]
set sc_scenarios []
foreach corner [dict keys [sc_cfg_get constraint timing]] {
    if { [sc_cfg_get constraint timing $corner mode] == $sc_timing_mode } {
        lappend sc_scenarios $corner
    }
}

###############################
# Optional
###############################

# MACROS
set sc_macrolibs [sc_get_asic_libraries macro]

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
foreach lib "$sc_targetlibs $sc_macrolibs" {
    #Liberty
    foreach corner $sc_scenarios {
        foreach libcorner [sc_cfg_get constraint timing $corner libcorner] {
            if { [sc_cfg_exists library $lib output $libcorner $sc_delaymodel] } {
                foreach lib_file [sc_cfg_get library $lib output $libcorner $sc_delaymodel] {
                    puts "Reading liberty file for ${corner} ($libcorner): ${lib_file}"
                    read_liberty -corner $corner $lib_file
                }
                break
            }
        }
    }
}

# Read Verilog
if { [file exists "inputs/${sc_design}.vg"] } {
    puts "Reading netlist verilog: inputs/${sc_design}.vg"
    read_verilog "inputs/${sc_design}.vg"
} else {
    foreach netlist [sc_cfg_get input netlist verilog] {
        puts "Reading netlist verilog: ${netlist}"
        read_verilog $netlist
    }
}
link_design $sc_design

# Read SDC (in order of priority)
# TODO: add logic for reading from ['constraint', ...] once we support MCMM
if { [file exists "inputs/${sc_design}.sdc"] } {
    # get from previous step
    puts "Reading SDC: inputs/${sc_design}.sdc"
    read_sdc "inputs/${sc_design}.sdc"
} elseif { [sc_cfg_exists input constraint sdc] } {
    foreach sdc [sc_cfg_get input constraint sdc] {
        # read step constraint if exists
        puts "Reading SDC: ${sdc}"
        read_sdc $sdc
    }

    set sdc_files []
    foreach corner $sc_scenarios {
        foreach sdc [sc_cfg_get constraint timing $corner file] {
            if { [lsearch -exact $sdc_files $sdc] == -1 } {
                # read step constraint if exists
                puts "Reading mode (${sc_timing_mode}) SDC: ${sdc}"
                lappend sdc_files $sdc
                read_sdc $sdc
            }
        }
    }
} else {
    # fall back on default auto generated constraints file
    set sdc "[sc_cfg_tool_task_get file opensta_generic_sdc]"
    puts "Reading SDC: ${sdc}"
    puts "Warning: Defaulting back to default SDC"
    read_sdc "${sdc}"
}

# Create path groups
if { [llength [sta::path_group_names]] == 0 } {
    sc_path_group -name in2out -from [all_inputs -no_clocks] -to [all_outputs]

    if {
        [llength [all_clocks]] == 1 ||
        [lindex [sc_cfg_tool_task_get var unique_path_groups_per_clock] 0] == "false"
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

foreach corner $sc_scenarios {
    set pex_corner [sc_cfg_get constraint timing $corner pexcorner]

    set spef_file "inputs/${sc_design}.${pex_corner}.spef"
    if { [file exists $spef_file] } {
        puts "Reading SPEF ($corner): $spef_file"
        read_spef -corner $corner $spef_file
    }
}

foreach corner $sc_scenarios {
    set pex_corner [sc_cfg_get constraint timing $corner pexcorner]

    set input_sdf_file "inputs/${sc_design}.${pex_corner}.sdf"
    if { [file exists $input_sdf_file] } {
        puts "Reading SDF ($corner): $input_sdf_file"
        read_sdf -corner $corner $input_sdf_file
    }
}

###############################
# Report Metrics
###############################

set opensta_top_n_paths [lindex [sc_cfg_tool_task_get var top_n_paths] 0]

set fields "{capacitance slew input_pins hierarcial_pins net fanout}"
set PREFIX "SC_METRIC:"

puts "$PREFIX timeunit"
puts [sta::unit_scale_abbreviation time]

puts "$PREFIX report_checks -path_delay max"
report_checks -fields $fields -path_delay max -format full_clock_expanded \
    > reports/setup.rpt
sc_display_report reports/setup.rpt
report_checks -path_delay max -group_count $opensta_top_n_paths \
    > reports/setup.topN.rpt

puts "$PREFIX setupslack"
report_worst_slack -max > reports/worst_slack.setup.rpt
sc_display_report reports/worst_slack.setup.rpt

puts "$PREFIX setuppaths"
puts [sta::endpoint_violation_count max]

puts "$PREFIX setuptns"
report_tns > reports/total_negative_slack.rpt
sc_display_report reports/total_negative_slack.rpt

puts "$PREFIX report_checks -path_delay min"
report_checks -fields $fields -path_delay min -format full_clock_expanded \
    > reports/hold.rpt
sc_display_report reports/hold.rpt
report_checks -path_delay min -group_count $opensta_top_n_paths \
    > reports/hold.topN.rpt

puts "$PREFIX holdslack"
report_worst_slack -min > reports/worst_slack.hold.rpt
sc_display_report reports/worst_slack.hold.rpt

puts "$PREFIX holdpaths"
puts [sta::endpoint_violation_count max]

puts "$PREFIX holdtns"
puts "tns [sta::time_sta_ui [sta::total_negative_slack_cmd min]]"

report_checks -fields $fields -unconstrained -format full_clock_expanded \
    > reports/unconstrained.rpt
sc_display_report reports/unconstrained.rpt
report_checks -unconstrained -group_count $opensta_top_n_paths \
    > reports/unconstrained.topN.rpt

if { [llength [all_clocks]] > 0 } {
    puts "$PREFIX setupskew"
    report_clock_skew -setup -digits 4 > reports/skew.setup.rpt
    sc_display_report reports/skew.setup.rpt
    puts "$PREFIX holdskew"
    report_clock_skew -hold -digits 4 > reports/skew.hold.rpt
    sc_display_report reports/skew.hold.rpt
}

puts "$PREFIX drvs"
report_check_types -max_slew -max_capacitance -max_fanout -violators -no_line_splits \
    > reports/drv_violators.rpt
sc_display_report reports/drv_violators.rpt

# Model on: https://github.com/The-OpenROAD-Project/OpenSTA/blob/f913c3ddbb3e7b4364ed4437c65ac78c4da9174b/tcl/Search.tcl#L1078
set fmax_metric 0
foreach clk [sta::sort_by_name [all_clocks]] {
    puts "$PREFIX fmax"
    set clk_name [get_name $clk]
    set min_period [sta::find_clk_min_period $clk 1]
    if { $min_period == 0.0 } {
        continue
    }
    set fmax [expr { 1.0 / $min_period }]
    puts "$clk_name fmax = [format %.2f [expr { $fmax / 1e6 }]] MHz"
    set fmax_metric [expr { max($fmax_metric, $fmax) }]
}
if { $fmax_metric > 0 } {
    puts "fmax = [format %.2f [expr { $fmax_metric / 1e6 }]] MHz"
}

# get logic depth of design
puts "$PREFIX logicdepth"
puts [sc_count_logic_depth]

puts "$PREFIX power"
foreach corner [sta::corners] {
    set corner_name [$corner name]
    puts "Power for corner: $corner_name"
    report_power -corner $corner_name > reports/power.${corner_name}.rpt
    sc_display_report reports/power.${corner_name}.rpt
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
with_output_to_variable endpoints {check_setup -unconstrained_endpoints}
set unconstrained_endpoints [regexp -all -inline {[0-9]+} $endpoints]
if { $unconstrained_endpoints == "" } {
    set unconstrained_endpoints 0
}
puts "$PREFIX unconstrained"
puts $unconstrained_endpoints
