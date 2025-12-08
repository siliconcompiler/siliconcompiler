###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

set nets []
if { [llength [sc_cfg_tool_task_get var net]] > 0 } {
    set nets [sc_cfg_tool_task_get var net]
} else {
    set nets [sc_psm_check_nets]
}

###############################
# Assign power
###############################

foreach inst_setting [sc_cfg_tool_task_get var instance_power] {
    lassign $inst_setting inst power
    set pwr_mw [expr { $power * 1000 }]
    puts "Setting power for $inst to: [format "%.3f" $pwr_mw]mW"

    set_pdnsim_inst_power \
        -inst $inst \
        -power $power
}

###############################
# Depopulate Terminals
###############################

if { [sc_cfg_tool_task_get var source_disconnection_rate] > 0 } {
    expr { srand([sc_cfg_tool_task_get var source_disconnection_seed]) }

    set depop_target [expr { [sc_cfg_tool_task_get var source_disconnection_rate] / 100.0 }]

    foreach net $nets {
        set count 0
        set disabled 0
        foreach bpin [[[ord::get_db_block] findBTerm $net] getBPins] {
            foreach box [$bpin getBoxes] {
                incr count
                if { rand() < $depop_target } {
                    incr disabled
                    odb::dbBoolProperty_create $box PSM_DISCONNECT 1
                }
            }
        }
        set term_proc [expr { 100 * (double($disabled) / $count) }]
        utl::info FLW 1 "$net terminals disabled $disabled / $count ([format "%.1f" $term_proc]%)"
    }
}

###############################
# Setup power grid analysis
###############################

set source_args []

set res [sc_cfg_tool_task_get var external_resistance]
if { $res > 0 } {
    puts "Setting external resistance to $res ohms"
    lappend source_args -external_resistance $res
}

if { [llength $source_args] != 0 } {
    set_pdnsim_source_settings {*}$source_args
}

###############################
# Analyze nets
###############################

lassign [sc_cfg_tool_task_get var heatmap_grid] heatmap_x heatmap_y
gui::save_display_controls

sc_image_setup_default
gui::set_display_controls "Shape Types/Pin*" visible false

foreach net $nets {
    file mkdir reports/${net}
    foreach corner $sc_scenarios {
        analyze_power_grid -net $net -corner $corner -allow_reuse

        save_animated_gif -start "reports/${net}/${corner}.gif"

        foreach layer [[ord::get_db_tech] getLayers] {
            if { [$layer getRoutingLevel] == 0 } {
                continue
            }
            set layer_name [$layer getName]

            gui::set_heatmap IRDrop Net $net
            gui::set_heatmap IRDrop Corner $corner
            gui::set_heatmap IRDrop Layer $layer_name
            gui::set_heatmap IRDrop LogScale 0
            gui::set_heatmap IRDrop ShowLegend 1
            gui::set_heatmap IRDrop GridX $heatmap_x
            gui::set_heatmap IRDrop GridY $heatmap_y
            gui::set_display_controls "Heat Maps/IR Drop" visible true

            gui::set_heatmap IRDrop rebuild

            if { ![gui::get_heatmap_bool IRDrop has_data] } {
                continue
            }

            # Save CSV
            gui::dump_heatmap IRDrop reports/${net}/${corner}.${layer_name}.csv

            set box [[ord::get_db_block] getDieArea]
            set x [ord::dbu_to_microns [$box xMax]]
            set y [ord::dbu_to_microns [$box yMin]]
            set label [add_label -position "$x $y" -anchor "bottom right" -color white $layer_name]

            sc_save_image \
                "IR drop for $net on $layer_name for $corner heatmap" \
                reports/${net}/${corner}.${layer_name}.png \
                true

            gui::set_heatmap IRDrop LogScale 1
            gui::set_heatmap IRDrop rebuild

            sc_save_image \
                "IR drop for $net on $layer_name for $corner heatmap" \
                reports/${net}/${corner}.${layer_name}_log.png \
                false

            gui::set_display_controls "Heat Maps/IR Drop" visible false

            if { $label != "" } {
                gui::delete_label $label
            }
        }
        save_animated_gif -end
    }
}

gui::restore_display_controls
