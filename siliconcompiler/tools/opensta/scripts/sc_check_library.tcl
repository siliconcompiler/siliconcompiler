###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

##############################
# Schema Adapter
###############################

set sc_mainlib [sc_cfg_get asic mainlib]
set sc_logiclibs [sc_cfg_get asic asiclib]
set sc_delaymodel [sc_cfg_get asic delaymodel]
set sc_scenarios [dict keys [sc_cfg_get constraint timing scenario]]

# Standard cell libraries whose tool setup is validated below.
set sc_targetlibs $sc_mainlib
foreach lib $sc_logiclibs {
    if { [lsearch -exact $sc_targetlibs $lib] == -1 } {
        lappend sc_targetlibs $lib
    }
}

###############################
# Read Files
###############################

# Read Liberty
# Each file is read once. The files each scenario uses are kept so the pin checks
# below can look at every scenario on its own.
set sc_scene_liberty [dict create]
set sc_liberty_files_read []
foreach scene $sc_scenarios {
    set scene_files []
    foreach lib $sc_targetlibs {
        foreach libcorner [sc_cfg_get constraint timing scenario $scene libcorner] {
            if { ![sc_cfg_exists library $lib asic libcornerfileset $libcorner $sc_delaymodel] } {
                continue
            }
            set lib_filesets \
                [sc_cfg_get library $lib asic libcornerfileset $libcorner $sc_delaymodel]
            foreach lib_file [sc_cfg_get_fileset $lib $lib_filesets liberty] {
                # read_liberty records the native name, which is what the cells report
                set lib_file [file nativename $lib_file]
                if { [lsearch -exact $scene_files $lib_file] == -1 } {
                    lappend scene_files $lib_file
                }
                if { [lsearch -exact $sc_liberty_files_read $lib_file] == -1 } {
                    puts "Reading liberty file: ${lib_file}"
                    read_liberty $lib_file
                    lappend sc_liberty_files_read $lib_file
                }
            }
        }
    }
    dict set sc_scene_liberty $scene $scene_files
}

###############################
# Report Units
###############################

puts "Timing library units:"
report_units

###############################
# Report Cells
###############################

set report_fh [open reports/libraries.rpt w]
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
    puts $report_fh "[get_full_name $cell]$desc"

    set pins [get_lib_pins -quiet [get_full_name $cell]/*]
    if { [llength $pins] == 0 } {
        puts $report_fh "  No pins"
        continue
    }
    foreach pin $pins {
        puts $report_fh "  [get_full_name $pin] [get_property $pin direction]"
        set cap [expr { [sta::capacitance_ui_sta [get_property $pin capacitance]] / 1e-15 }]
        puts $report_fh "    Capacitance:      [format %.3f $cap]fF"
        set res [sta::resistance_ui_sta [get_property $pin drive_resistance]]
        puts $report_fh "    Drive resistance: [format %.3f $res]ohm"
        set delay [expr { [sta::time_ui_sta [get_property $pin intrinsic_delay]] / 1e-12 }]
        puts $report_fh "    Intrinsic delay:  [format %.3f $delay]ps"
    }
}
close $report_fh

###############################
# Check Cells
###############################

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

# Tool setup parameters are validated leniently: a library that does not
# declare a given parameter is skipped (not an error), so that a correctly
# configured target never fails this check just because it omits an optional
# setup value.

# Verify that a named cell is present in the loaded libraries.
proc check_cell { lib label cell } {
    puts "Checking $lib $label: $cell"
    assert_glob $cell
    if { [llength [get_lib_cells -quiet $cell]] == 0 } {
        puts "\[ERROR] $lib $label: cell '$cell' not found in libraries"
    }
}

# Verify that a cell's port exists (once per scenario) with the expected direction.
proc check_port { lib label cell port dir } {
    global sc_scene_liberty

    assert_glob $port
    set pins [get_lib_pins -quiet $cell/$port]
    if { [llength $pins] == 0 } {
        puts "\[ERROR] $lib $label: pin '$cell/$port' not found in libraries"
        return
    }
    dict for {scene scene_files} $sc_scene_liberty {
        set count 0
        foreach libcell [get_lib_cells -quiet $cell] {
            if {
                [lsearch -exact $scene_files [get_property $libcell filename]] != -1 &&
                [$libcell find_liberty_port $port] != "NULL"
            } {
                incr count
            }
        }
        if { $count != 1 } {
            puts "\[ERROR] $lib $label: pin '$cell/$port' defined in $count\
                libraries of scenario $scene, expected 1"
        }
    }
    foreach pin $pins {
        if { [get_property $pin direction] != $dir } {
            puts "\[ERROR] $lib $label: [get_full_name $pin] direction is\
                '[get_property $pin direction]', expected '$dir'"
        }
    }
}

# Check yosys setup
foreach lib $sc_targetlibs {
    # driver_cell: single cell name
    if { [sc_cfg_exists library $lib tool yosys driver_cell] } {
        check_cell $lib "yosys driver_cell" \
            [sc_cfg_get library $lib tool yosys driver_cell]
    }

    # buffer_cell: {cell input_port output_port}
    if { [sc_cfg_exists library $lib tool yosys buffer_cell] } {
        lassign [sc_cfg_get library $lib tool yosys buffer_cell] cell in out
        check_cell $lib "yosys buffer_cell" $cell
        check_port $lib "yosys buffer_cell input" $cell $in "input"
        check_port $lib "yosys buffer_cell output" $cell $out "output"
    }

    # tiehigh_cell / tielow_cell: {cell port}
    foreach tie {tiehigh_cell tielow_cell} {
        if { [sc_cfg_exists library $lib tool yosys $tie] } {
            lassign [sc_cfg_get library $lib tool yosys $tie] cell port
            check_cell $lib "yosys $tie" $cell
            check_port $lib "yosys $tie" $cell $port "output"
        }
    }

    # abc_clock_multiplier: expected to convert the liberty time unit to ps
    if { [sc_cfg_exists library $lib tool yosys abc_clock_multiplier] } {
        set expected [expr { round(1.0 / [sta::time_sta_ui 1e-12]) }]
        set actual [sc_cfg_get library $lib tool yosys abc_clock_multiplier]
        puts "Checking $lib yosys abc_clock_multiplier: $actual (expected $expected)"
        if { $actual != $expected } {
            puts "\[ERROR] $lib yosys abc_clock_multiplier is $actual, expected $expected"
        }
    }

    # abc_constraint_load: reported for reference (units are PDK dependent, so
    # this is informational rather than a hard check).
    if {
        [sc_cfg_exists library $lib tool yosys abc_constraint_load] &&
        [sc_cfg_exists library $lib tool yosys buffer_cell]
    } {
        lassign [sc_cfg_get library $lib tool yosys buffer_cell] cell in out
        set cap 0.0
        foreach pin [get_lib_pins -quiet $cell/$in] {
            set cap [expr { max($cap, [get_property $pin capacitance]) }]
        }
        set computed [expr { 4 * $cap }]
        set actual [sc_cfg_get library $lib tool yosys abc_constraint_load]
        puts "Checking $lib yosys abc_constraint_load: $actual\
            (4x max buffer input cap = [format %.4g $computed])"
    }
}

# Check openroad setup
foreach lib $sc_targetlibs {
    # tiehigh_cell / tielow_cell: {cell port}
    foreach tie {tiehigh_cell tielow_cell} {
        if { [sc_cfg_exists library $lib tool openroad $tie] } {
            lassign [sc_cfg_get library $lib tool openroad $tie] cell port
            check_cell $lib "openroad $tie" $cell
            check_port $lib "openroad $tie" $cell $port "output"
        }
    }
}
