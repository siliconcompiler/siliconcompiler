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
set sc_delaymodel [sc_cfg_get asic delaymodel]
set sc_scenarios [dict keys [sc_cfg_get constraint timing]]

###############################
# Optional
###############################

# MACROS
set sc_macrolibs [sc_get_asic_libraries macro]

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

# Report cells
foreach cell [get_lib_cells *] {
    set desc ""
    if { [get_property $cell is_buffer] } {
        set desc " (buffer)"
    } elseif { [get_property $cell is_inverter] } {
        set desc " (inverter)"
    } elseif {
        [llength [get_lib_pins -quiet [get_full_name $cell]/* -filter is_register_clock==1]] != 0
    } {
        set desc " (register)"
    }
    puts "[get_full_name $cell]$desc"

    set pins [get_lib_pins -quiet [get_full_name $cell]/*]
    if { [llength $pins] == 0 } {
        puts "  No pins"
        continue
    }
    foreach pin $pins {
        puts "  [get_full_name $pin] [get_property $pin direction]"
        set cap [expr { [sta::capacitance_ui_sta [get_property $pin capacitance]] / 1e-15 }]
        puts "    Capacitance:      [format %.3f $cap]fF"
        set res [sta::resistance_ui_sta [get_property $pin drive_resistance]]
        puts "    Drive resistance: [format %.3f $res]ohm"
        set delay [expr { [sta::time_ui_sta [get_property $pin intrinsic_delay]] / 1e-12 }]
        puts "    Intrinsic delay:  [format %.3f $delay]ps"
    }
}
