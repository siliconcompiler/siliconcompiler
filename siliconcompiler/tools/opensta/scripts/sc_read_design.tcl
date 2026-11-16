# Reads everything the timing engine needs -- liberty, netlist, SDC, parasitics
# and switching activity -- and leaves OpenSTA with a linked design whose path
# groups are defined.
#
# Sourced by sc_timing.tcl, which then reports on what was read, and by
# sc_open.tcl, which hands the loaded design to an interactive session. The
# caller is responsible for sourcing ./sc_manifest.tcl first and for defining
# $opensta_timing_mode.

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
# Each file is read once. The liberty files of every scenario are collected here so
# define_scene can hand them to the scene once the design is linked.
set sc_scene_liberty [dict create]
foreach scene $sc_scenarios {
    set scene_files []
    foreach lib $sc_logiclibs {
        set lib_files []
        if { $opensta_timing_mode == "asic" } {
            set lib_filesets []
            foreach libcorner [sc_cfg_get constraint timing scenario $scene libcorner] {
                if {
                    [sc_cfg_exists library $lib asic \
                        libcornerfileset $libcorner $sc_delaymodel]
                } {
                    lappend lib_filesets \
                        {*}[sc_cfg_get library $lib asic \
                            libcornerfileset $libcorner $sc_delaymodel]
                }
            }
            set lib_files [sc_cfg_get_fileset $lib $lib_filesets liberty]
        } elseif { $opensta_timing_mode == "fpga" } {
            foreach lib_fileset [sc_cfg_get library $lib tool opensta liberty_filesets] {
                lappend lib_files {*}[sc_cfg_get_fileset $lib $lib_fileset liberty]
            }
        }
        foreach lib_file $lib_files {
            # read_liberty records the native name, and define_scene matches on it
            set lib_file [file nativename $lib_file]
            if { [lsearch -exact $scene_files $lib_file] == -1 } {
                lappend scene_files $lib_file
            }
        }
    }
    dict set sc_scene_liberty $scene $scene_files
}

set sc_liberty_files_read []
dict for {scene scene_files} $sc_scene_liberty {
    foreach lib_file $scene_files {
        if { [lsearch -exact $sc_liberty_files_read $lib_file] == -1 } {
            puts "Reading liberty file: ${lib_file}"
            read_liberty $lib_file
            lappend sc_liberty_files_read $lib_file
        }
    }
}

# The default delay calculator reads the NLDM tables and ignores the
# current-source models, so a CCS liberty is only worth reading if the
# calculator is switched over with it.
if { $sc_delaymodel == "ccs" } {
    puts "Using CCS delay calculation"
    set_delay_calculator prima
}

# Read Verilog
# .vg.gz is accepted as well because OpenTask copies whatever showfilepath points
# at into inputs/ under its own extension, and the netlists SC writes are gzipped.
set sc_netlist ""
foreach ext {vg vg.gz} {
    if { [file exists "inputs/${sc_topmodule}.${ext}"] } {
        set sc_netlist "inputs/${sc_topmodule}.${ext}"
        break
    }
}
if { $sc_netlist != "" } {
    puts "Reading netlist verilog: $sc_netlist"
    read_verilog $sc_netlist
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

# Read SPEF
# Each pex corner is read once, under its own name, so every scenario that shares the
# corner can be handed the same parasitics.
set sc_scene_spef [dict create]
if { $opensta_timing_mode == "asic" } {
    set spefs_read []
    foreach scene $sc_scenarios {
        set pex_corner [sc_cfg_get constraint timing scenario $scene pexcorner]

        set spef_file "inputs/${sc_topmodule}.${pex_corner}.spef"
        if { ![file exists $spef_file] } {
            continue
        }
        if { [lsearch -exact $spefs_read $pex_corner] == -1 } {
            puts "Reading SPEF ($pex_corner): $spef_file"
            read_spef -name $pex_corner $spef_file
            lappend spefs_read $pex_corner
        }
        dict set sc_scene_spef $scene $pex_corner
    }
}

# Define scenes
# Every scene uses the current mode, and define_scene clears the port loads of its
# mode, so the scenes have to exist before the SDC is read.
foreach scene $sc_scenarios {
    set scene_args [list -liberty [dict get $sc_scene_liberty $scene]]
    if { [dict exists $sc_scene_spef $scene] } {
        lappend scene_args -spef [dict get $sc_scene_spef $scene]
    }
    puts "Defining timing scene: $scene"
    define_scene $scene {*}$scene_args
}

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
    foreach scene $sc_scenarios {
        set pex_corner [sc_cfg_get constraint timing scenario $scene pexcorner]

        set input_sdf_file "inputs/${sc_topmodule}.${pex_corner}.sdf"
        if { [file exists $input_sdf_file] } {
            puts "Reading SDF ($scene / $pex_corner): $input_sdf_file"
            read_sdf -scene $scene $input_sdf_file
        }
    }
} elseif { $opensta_timing_mode == "fpga" } {
    foreach scene $sc_scenarios {
        set input_sdf_file "inputs/${sc_topmodule}.typical.sdf"
        if { [file exists $input_sdf_file] } {
            puts "Reading SDF ($scene / typical): $input_sdf_file"
            read_sdf -scene $scene $input_sdf_file
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
