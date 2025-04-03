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

proc assert_glob { str } {
    if { [string first "*" $str] != -1 } {
        puts "\[ERROR] Regex detected: $str"
    }
}

# Check cells
# check for globbing and report list if globs are detected
# check each cell
foreach lib $sc_targetlibs {
    dict for {cell_type cells} [sc_cfg_get library $lib asic cells] {
        if { [llength $cells] == 0 } {
            continue
        }

        puts "Checking: $lib / asic / cells / $cell_type"

        foreach cell $cells {
            puts "  $cell:"

            if { $cell_type != "dontuse" } {
                assert_glob $cell
            }
            set libcells [get_lib_cells $cell]
            foreach libcell $libcells {
                puts "    [get_full_name $libcell]"
            }
        }
    }
}

# Check yosys setup
# yosys_driver_cell
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_driver_cell"
    assert_glob [sc_cfg_get library $lib option var yosys_driver_cell]
    if { [get_lib_cells [sc_cfg_get library $lib option var yosys_driver_cell]] == 0 } {
        puts "\[ERROR] missing"
    }
}
# yosys_buffer_cell
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_buffer_cell"
    assert_glob [sc_cfg_get library $lib option var yosys_buffer_cell]
    if { [get_lib_cells [sc_cfg_get library $lib option var yosys_buffer_cell]] == 0 } {
        puts "\[ERROR] missing"
    }
}
# yosys_buffer_input
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_buffer_input"
    assert_glob [sc_cfg_get library $lib option var yosys_buffer_input]
    set cellname [sc_cfg_get library $lib option var yosys_buffer_cell]
    set pins [get_lib_pins $cellname/[sc_cfg_get library $lib option var yosys_buffer_input]]
    if { [llength $pins] != [llength [sta::corners]] } {
        puts "\[ERROR] mismatch"
    }
    foreach pin $pins {
        if { [get_property $pin direction] != "input" } {
            puts "\[ERROR] [get_full_name $pin] incorrect direction"
        }
    }
}
# yosys_buffer_output
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_buffer_output"
    assert_glob [sc_cfg_get library $lib option var yosys_buffer_output]
    set cellname [sc_cfg_get library $lib option var yosys_buffer_cell]
    set pins [get_lib_pins $cellname/[sc_cfg_get library $lib option var yosys_buffer_output]]
    if { [llength $pins] != [llength [sta::corners]] } {
        puts "\[ERROR] mismatch"
    }
    foreach pin $pins {
        if { [get_property $pin direction] != "output" } {
            puts "\[ERROR] [get_full_name $pin] incorrect direction"
        }
    }
}
# yosys_tiehigh_cell
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_tiehigh_cell"
    assert_glob [sc_cfg_get library $lib option var yosys_tiehigh_cell]
    if { [get_lib_cells [sc_cfg_get library $lib option var yosys_tiehigh_cell]] == 0 } {
        puts "\[ERROR] missing"
    }
}
# yosys_tiehigh_port
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_tiehigh_port"
    assert_glob [sc_cfg_get library $lib option var yosys_tiehigh_port]
    set cellname [sc_cfg_get library $lib option var yosys_tiehigh_cell]
    set pins [get_lib_pins $cellname/[sc_cfg_get library $lib option var yosys_tiehigh_port]]
    if { [llength $pins] != [llength [sta::corners]] } {
        puts "\[ERROR] mismatch"
    }
    foreach pin $pins {
        if { [get_property $pin direction] != "output" } {
            puts "\[ERROR] [get_full_name $pin] incorrect direction"
        }
    }
}
# yosys_tielow_cell
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_tielow_cell"
    assert_glob [sc_cfg_get library $lib option var yosys_tielow_cell]
    if { [get_lib_cells [sc_cfg_get library $lib option var yosys_tielow_cell]] == 0 } {
        puts "\[ERROR] missing"
    }
}
# yosys_tielow_port
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_tielow_port"
    assert_glob [sc_cfg_get library $lib option var yosys_tielow_port]
    set cellname [sc_cfg_get library $lib option var yosys_tielow_cell]
    set pins [get_lib_pins $cellname/[sc_cfg_get library $lib option var yosys_tielow_port]]
    if { [llength $pins] != [llength [sta::corners]] } {
        puts "\[ERROR] mismatch"
    }
    foreach pin $pins {
        if { [get_property $pin direction] != "output" } {
            puts "\[ERROR] [get_full_name $pin] incorrect direction"
        }
    }
}
# yosys_abc_constraint_load
foreach lib $sc_targetlibs {
    set cap 0.0
    puts "Checking $lib yosys_abc_constraint_load"
    set cellname [sc_cfg_get library $lib option var yosys_buffer_cell]
    set pins [get_lib_pins $cellname/[sc_cfg_get library $lib option var yosys_buffer_input]]
    foreach pin $pins {
        set cap [expr { max($cap, [get_property $pin capacitance]) }]
    }
    set lib_cap [sc_cfg_get library $lib option var yosys_abc_constraint_load]
    set cap [expr { 4 * $cap }]
    set cap "[format "%.3f" $cap][sta::unit_scaled_suffix capacitance]"

    if { $lib_cap != $cap } {
        puts "\[ERROR] mismatch, should be $cap, not $lib_cap"
    }
}

# yosys_abc_clock_multiplier
foreach lib $sc_targetlibs {
    puts "Checking $lib yosys_abc_clock_multiplier"
    set ps_convert [expr { round(1.0 / [sta::time_sta_ui 1e-12]) }]
    set convert [sc_cfg_get library $lib option var yosys_abc_clock_multiplier]
    if { $convert != $ps_convert } {
        puts "\[ERROR] incorrect multiplier: should be $ps_convert, not $convert"
    }
}

# Check openroad setup
# openroad_tiehigh_cell
foreach lib $sc_targetlibs {
    puts "Checking $lib openroad_tiehigh_cell"
    assert_glob [sc_cfg_get library $lib option var openroad_tiehigh_cell]
    if { [get_lib_cells [sc_cfg_get library $lib option var openroad_tiehigh_cell]] == 0 } {
        puts "\[ERROR] missing"
    }
}
# openroad_tiehigh_port
foreach lib $sc_targetlibs {
    puts "Checking $lib openroad_tiehigh_port"
    assert_glob [sc_cfg_get library $lib option var openroad_tiehigh_port]
    set cellname [sc_cfg_get library $lib option var openroad_tiehigh_cell]
    set pins [get_lib_pins $cellname/[sc_cfg_get library $lib option var openroad_tiehigh_port]]
    if { [llength $pins] != [llength [sta::corners]] } {
        puts "\[ERROR] mismatch"
    }
    foreach pin $pins {
        if { [get_property $pin direction] != "output" } {
            puts "\[ERROR] [get_full_name $pin] incorrect direction"
        }
    }
}

# openroad_tielow_cell
foreach lib $sc_targetlibs {
    puts "Checking $lib openroad_tielow_cell"
    assert_glob [sc_cfg_get library $lib option var openroad_tielow_cell]
    if { [get_lib_cells [sc_cfg_get library $lib option var openroad_tielow_cell]] == 0 } {
        puts "\[ERROR] missing"
    }
}
# openroad_tielow_port
foreach lib $sc_targetlibs {
    puts "Checking $lib openroad_tielow_port"
    assert_glob [sc_cfg_get library $lib option var openroad_tielow_port]
    set cellname [sc_cfg_get library $lib option var openroad_tielow_cell]
    set pins [get_lib_pins $cellname/[sc_cfg_get library $lib option var openroad_tielow_port]]
    if { [llength $pins] != [llength [sta::corners]] } {
        puts "\[ERROR] mismatch"
    }
    foreach pin $pins {
        if { [get_property $pin direction] != "output" } {
            puts "\[ERROR] [get_full_name $pin] incorrect direction"
        }
    }
}
