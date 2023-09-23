####################
# Helper functions
####################
proc preserve_modules {} {
    global sc_cfg
    global sc_tool
    global sc_task

    if {[dict exists $sc_cfg tool $sc_tool task $sc_task var preserve_modules]} {
        foreach module [dict get $sc_cfg tool $sc_tool task $sc_task var preserve_modules] {
            yosys select -module $module
            yosys setattr -mod -set keep_hierarchy 1
            yosys select -clear
        }
    }
}

proc get_modules {} {
    yosys echo off
    set modules_ls [yosys tee -q -s result.string ls]
    yosys echo on
    # Grab only the modules and not the header and footer
    set modules [list]
    foreach module [lrange [split $modules_ls \n] 2 end-1] {
        set module [string trim $module]
        if { [string length $module] == 0 } {
            continue
        }
        lappend modules $module
    }
    return [lsort $modules]
}

proc determine_keep_hierarchy { iter cell_limit } {
    global sc_design

    # Grab only the modules and not the header and footer
    set modules [get_modules]

    # Save a copy of the current design so we can do a few optimizations and techmap
    yosys design -save hierarchy_checkpoint
    yosys techmap
    yosys opt -fast -full -purge

    set cell_counts [dict create]

    foreach module $modules {
        yosys stat -top $module
        yosys echo off
        set cells_count [yosys tee -q -s result.string scratchpad -get stat.num_cells]
        yosys echo on
        dict set cell_counts $module [expr int($cells_count)]
    }

    # Restore design
    yosys design -load hierarchy_checkpoint
    foreach module $modules {
        yosys select -module $module
        yosys setattr -mod -set keep_hierarchy [expr [dict get $cell_counts $module] > $cell_limit]
        yosys select -clear
    }

    preserve_modules

    # Rerun coarse synth with flatten
    yosys synth -flatten -top $sc_design -run coarse:fine

    return [expr [llength $modules] != [llength [get_modules]]]
}

####################
# DESIGNER's CHOICE
####################

set sc_logiclibs        [dict get $sc_cfg asic logiclib]
set sc_macrolibs        [dict get $sc_cfg asic macrolib]

set sc_libraries        [dict get $sc_cfg tool $sc_tool task $sc_task {file} synthesis_libraries]
if {[dict exists $sc_cfg tool $sc_tool task $sc_task {file} synthesis_libraries_macros]} {
    set sc_macro_libraries [dict get $sc_cfg tool $sc_tool task $sc_task {file} synthesis_libraries_macros]
} else {
    set sc_macro_libraries []
}
set sc_mainlib          [lindex $sc_logiclibs 0]

set sc_dff_library      [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {file} dff_liberty_file] 0]
set sc_abc_constraints  [lindex [dict get $sc_cfg tool $sc_tool task $sc_task {file} abc_constraint_file] 0]

set sc_blackboxes       []
foreach lib [dict get $sc_cfg asic macrolib] {
    if { [dict exist $sc_cfg library $lib output blackbox verilog] } {
        foreach lib_f [dict get $sc_cfg library $lib output blackbox verilog] {
            lappend sc_blackboxes $lib_f
        }
    }
}

#########################
# Schema helper functions
#########################

proc has_tie_cell { type } {
    upvar sc_cfg sc_cfg
    upvar sc_mainlib sc_mainlib
    upvar sc_tool sc_tool

    return [dict exists $sc_cfg library $sc_mainlib option {var} yosys_tie${type}_cell] && \
           [dict exists $sc_cfg library $sc_mainlib option {var} yosys_tie${type}_port]
}

proc get_tie_cell { type } {
    upvar sc_cfg sc_cfg
    upvar sc_mainlib sc_mainlib
    upvar sc_tool sc_tool

    set cell [lindex [dict get $sc_cfg library $sc_mainlib option {var} yosys_tie${type}_cell] 0]
    set port [lindex [dict get $sc_cfg library $sc_mainlib option {var} yosys_tie${type}_port] 0]

    return "$cell $port"
}

proc has_buffer_cell { } {
    upvar sc_cfg sc_cfg
    upvar sc_mainlib sc_mainlib
    upvar sc_tool sc_tool

    return [dict exists $sc_cfg library $sc_mainlib option {var} yosys_buffer_cell] && \
           [dict exists $sc_cfg library $sc_mainlib option {var} yosys_buffer_input] && \
           [dict exists $sc_cfg library $sc_mainlib option {var} yosys_buffer_output]
}

proc get_buffer_cell { } {
    upvar sc_cfg sc_cfg
    upvar sc_mainlib sc_mainlib
    upvar sc_tool sc_tool

    set cell [lindex [dict get $sc_cfg library $sc_mainlib option {var} yosys_buffer_cell] 0]
    set in   [lindex [dict get $sc_cfg library $sc_mainlib option {var} yosys_buffer_input] 0]
    set out  [lindex [dict get $sc_cfg library $sc_mainlib option {var} yosys_buffer_output] 0]

    return "$cell $in $out"
}

########################################################
# Read Libraries
########################################################

foreach lib_file "$sc_libraries $sc_macro_libraries" {
    yosys read_liberty -lib $lib_file
}
foreach bb_file $sc_blackboxes {
    puts "Reading blackbox model file: $bb_file"
    yosys read_verilog -sv $bb_file
}

########################################################
# Synthesis
########################################################

# Although the `synth` command also runs `hierarchy`, we run it here without the
# `-check` flag first in order to resolve parameters before looking for missing
# modules. This works around the fact that Surelog doesn't pickle modules that
# are instantiated inside generate blocks that will get eliminated. This seems
# to give us the same behavior as passing the `-defer` flag to read_verilog, but
# `-defer` gave us different post-synth results on one of our test cases (while
# this appears to result in no differences). Note this must be called after the
# read_liberty calls for it to not affect synthesis results.
yosys hierarchy -top $sc_design

# Mark modules to keep from getting removed in flattening
preserve_modules

set synth_args []
if {[dict get $sc_cfg tool $sc_tool task $sc_task var flatten] == "true"} {
    lappend synth_args "-flatten"
}
# Start synthesis
yosys synth {*}$synth_args -top $sc_design -run begin:fine

# Perform hierarchy flattening
if {[dict get $sc_cfg tool $sc_tool task $sc_task var flatten] != "true"} {
    set sc_hier_iterations [lindex [dict get $sc_cfg tool $sc_tool task $sc_task var hier_iterations] 0]
    set sc_hier_threshold [lindex [dict get $sc_cfg tool $sc_tool task $sc_task var hier_threshold] 0]
    for {set i 0} {$i < $sc_hier_iterations} {incr i} {
        if { [determine_keep_hierarchy $i $sc_hier_threshold] == 0} {
            break
        }
    }
}

# Finish synthesis
yosys synth {*}$synth_args -top $sc_design -run fine:check

yosys opt -purge

########################################################
# Technology Mapping
########################################################
proc post_techmap { { opt_args "" } } {
    # perform techmap in case previous techmaps introduced constructs that need techmapping
    yosys techmap
    # Quick optimization
    yosys opt {*}$opt_args -purge
}
if {[dict get $sc_cfg tool $sc_tool task $sc_task var map_adders] == "true"} {
    set sc_adder_techmap [lindex [dict get $sc_cfg library $sc_mainlib option {file} yosys_addermap] 0]
    # extract the full adders
    yosys extract_fa
    # map full adders
    yosys techmap -map $sc_adder_techmap
    post_techmap -fast
}

if { [dict exists $sc_cfg tool $sc_tool task $sc_task {file} techmap] } {
    foreach mapfile [dict get $sc_cfg tool $sc_tool task $sc_task {file} techmap] {
        yosys techmap -map $mapfile
        post_techmap -fast
    }
}

if {[dict get $sc_cfg tool $sc_tool task $sc_task var autoname] == "true"} {
    # use autoname to preserve some design naming
    # by doing it before dfflibmap the names will be slightly shorter since they will
    # only contain the $DFF_P names vs. the full library name of the associated flip-flop
    yosys autoname
}

yosys dfflibmap -liberty $sc_dff_library

# perform final techmap and opt in case previous techmaps introduced constructs that need techmapping
post_techmap

source "$sc_refdir/syn_strategies.tcl"

set script ""
set sc_strategy [dict get $sc_cfg tool $sc_tool task $sc_task var strategy]
if { [string length $sc_strategy] == 0 } {
    # Do nothing
} elseif { [dict exists $syn_strategies $sc_strategy] } {
    set script [dict get $syn_strategies $sc_strategy]
} elseif { [string match "+*" $sc_strategy] } {
    # ABC script passthrough
    set script $sc_strategy
} else {
    yosys log "Warning: no such synthesis strategy $sc_strategy"
}

# TODO: other abc flags passed in by OpenLANE we can adopt:
# -D: clock period
# -constr: in the case of OpenLANE, an autogenerated SDC that includes a
#   set_driving_cell and set_load call (but perhaps we should just pass along a
#   user-provided constraint)

set abc_args []
if {[dict exists $sc_cfg tool $sc_tool task $sc_task var abc_clock_period]} {
    set abc_clock_period [dict get $sc_cfg tool $sc_tool task $sc_task var abc_clock_period]
    if { [llength $abc_clock_period] != 0 } {
        # assumes units are ps
        lappend abc_args "-D" $abc_clock_period
    }
}
if {[file exists $sc_abc_constraints]} {
    lappend abc_args "-constr" $sc_abc_constraints
}
if {$script != ""} {
    lappend abc_args "-script" $script
}
foreach lib_file $sc_libraries {
    lappend abc_args "-liberty" $lib_file
}
set abc_dont_use []
foreach lib "$sc_logiclibs $sc_macrolibs" {
    foreach cell [dict get $sc_cfg library $lib asic cells dontuse] {
        lappend abc_dont_use -dont_use $cell
    }
}

yosys abc {*}$abc_args {*}$abc_dont_use

########################################################
# Cleanup
########################################################

yosys clean -purge
yosys setundef -zero

yosys splitnets

yosys clean -purge

set yosys_hilomap_args []
if { [has_tie_cell low]} {
    lappend yosys_hilomap_args -locell {*}[get_tie_cell low]
}
if { [has_tie_cell high]} {
    lappend yosys_hilomap_args -hicell {*}[get_tie_cell high]
}
if {[llength $yosys_hilomap_args] != 0} {
    yosys hilomap -singleton {*}$yosys_hilomap_args
}

if {[has_buffer_cell] && [dict get $sc_cfg tool $sc_tool task $sc_task var add_buffers] == "true"} {
    yosys insbuf -buf {*}[get_buffer_cell]
}

yosys clean -purge

set stat_libs []
lappend stat_libs "-liberty" $sc_dff_library
foreach lib_file "$sc_libraries $sc_macro_libraries" {
    lappend stat_libs "-liberty" $lib_file
}
# turn off echo to prevent the stat command from showing up in the json file
yosys echo off
yosys tee -o ./reports/stat.json stat -json -top $sc_design {*}$stat_libs
yosys echo on
