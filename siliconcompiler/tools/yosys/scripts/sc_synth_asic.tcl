###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

yosys echo on

###############################
# Schema Adapter
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]

####################
# DESIGNER's CHOICE
####################

set sc_optmode [sc_cfg_get option optmode]

########################################################
# Helper function
########################################################

source "$sc_refdir/procs.tcl"

####################
# DESIGNER's CHOICE
####################

set sc_mainlib [sc_cfg_get asic mainlib]
set sc_logiclibs [sc_cfg_get asic asiclib]

set sc_libraries [sc_cfg_tool_task_get var synthesis_libraries]

set sc_abc_constraints [sc_cfg_tool_task_get var abc_constraint_file]

set sc_blackboxes []
foreach lib $sc_logiclibs {
    if { [sc_cfg_exists library $lib tool yosys blackbox_fileset] } {
        set lib_fileset [sc_cfg_get library $lib tool yosys blackbox_fileset]
        foreach lib_f [sc_cfg_get_fileset $lib $lib_fileset verilog] {
            lappend sc_blackboxes $lib_f
        }
    }
}

set sc_memory_libmap_files [sc_cfg_tool_task_get var memory_libmap]
set sc_memory_techmap_files [sc_cfg_tool_task_get var memory_techmap]

########################################################
# Read Libraries
########################################################

foreach lib_file $sc_libraries {
    yosys read_liberty -overwrite -setattr liberty_cell -lib $lib_file
    yosys read_liberty -overwrite -setattr liberty_cell \
        -unit_delay -wb -ignore_miss_func -ignore_buses $lib_file
}
foreach bb_file $sc_blackboxes {
    yosys log "Reading blackbox model file: $bb_file"
    yosys read_verilog -setattr blackbox -sv $bb_file
}

########################################################
# Design Inputs
########################################################

set input_verilog "inputs/$sc_topmodule.v"
if { ![file exists $input_verilog] } {
    set input_verilog "inputs/$sc_topmodule.sv"
    if { ![file exists $input_verilog] } {
        set input_verilog []
        if { [sc_cfg_exists input rtl systemverilog] } {
            lappend input_verilog {*}[sc_cfg_get input rtl systemverilog]
        }
        if { [sc_cfg_exists input rtl verilog] } {
            lappend input_verilog {*}[sc_cfg_get input rtl verilog]
        }
    }
}

set use_slang false
if { [sc_cfg_tool_task_get var use_slang] } {
    if { ![sc_load_plugin slang] } {
        puts "WARNING: Unable to load slang plugin reverting back to yosys read_verilog"
    } else {
        set use_slang true
    }
}

if { $use_slang } {
    # This needs some reordering of loaded to ensure blackboxes are handled
    # before this
    set slang_params []
    set fileset [lindex [sc_cfg_get option fileset] 0]
    if { [sc_cfg_exists library $sc_designlib fileset $fileset param] } {
        dict for {key value} [sc_cfg_get library $sc_designlib fileset $fileset param] {
            lappend slang_params -G "${key}=${value}"
        }
    }
    yosys slang_version
    yosys read_slang \
        -D SYNTHESIS \
        --keep-hierarchy \
        --ignore-assertions \
        --allow-use-before-declare \
        --top $sc_topmodule \
        {*}$slang_params \
        {*}$input_verilog
    yosys setattr -unset init
} else {
    # Use -noblackbox to correctly interpret empty modules as empty,
    # actual black boxes are read in later
    # https://github.com/YosysHQ/yosys/issues/1468
    yosys read_verilog -noblackbox -sv {*}$input_verilog

    ########################################################
    # Override top level parameters
    ########################################################

    sc_apply_params
}

####################
# Helper functions
####################
proc preserve_modules { } {
    foreach pmodule [sc_cfg_tool_task_get var preserve_modules] {
        foreach module [get_modules $pmodule] {
            yosys log "Preserving module hierarchy: $module"
            yosys select -module $module
            yosys setattr -mod -set keep_hierarchy 1
            yosys select -clear
        }
    }
}

proc get_modules { { find "*" } } {
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
    set modules [lsearch -all -inline $modules $find]
    if { [llength $modules] == 0 } {
        yosys log "Warning: Unable to find modules matching: $find"
    }
    return [lsort $modules]
}

proc sc_annotate_gate_cost_equivalent { } {
    yosys cellmatch -derive_luts =A:liberty_cell
    # find a reference nand2 gate
    set found_cell ""
    set found_cell_area ""
    # iterate over all cells with a nand2 signature
    yosys echo off
    set nand2_cells [yosys tee -q -s result.string select -list-mod =*/a:lut=4'b0111 %m]
    yosys echo on
    foreach cell $nand2_cells {
        if { ![rtlil::has_attr -mod $cell area] } {
            puts "WARNING: Cell $cell missing area information"
            continue
        }
        set area [rtlil::get_attr -string -mod $cell area]
        if { $found_cell == "" || $area < $found_cell_area } {
            set found_cell $cell
            set found_cell_area $area
        }
    }
    if { $found_cell == "" } {
        set found_cell_area 1
        puts "WARNING: reference nand2 cell not found, using $found_cell_area as area"
    } else {
        puts "Using nand2 reference cell ($found_cell) with area: $found_cell_area"
    }

    # convert the area on all Liberty cells to a gate number equivalent
    yosys echo off
    set cells [yosys tee -q -s result.string select -list-mod =A:area =A:liberty_cell %i]
    yosys echo on
    foreach cell $cells {
        set area [rtlil::get_attr -mod -string $cell area]
        set gate_eq [expr { int(max(1, ceil($area / $found_cell_area))) }]
        puts "Setting gate_cost_equivalent for $cell as $gate_eq"
        rtlil::set_attr -mod -uint $cell gate_cost_equivalent $gate_eq
    }
}

#########################
# Schema helper functions
#########################

proc sc_has_tie_cell { type } {
    upvar sc_mainlib sc_mainlib

    return [sc_cfg_exists library $sc_mainlib tool yosys tie${type}_cell]
}

proc sc_get_tie_cell { type } {
    upvar sc_mainlib sc_mainlib

    set cell_port [sc_cfg_get library $sc_mainlib tool yosys tie${type}_cell]
    set cell [lindex $cell_port 0]
    set port [lindex $cell_port 1]

    return "$cell $port"
}

proc has_buffer_cell { } {
    upvar sc_mainlib sc_mainlib

    return [sc_cfg_exists library $sc_mainlib tool yosys buffer_cell]
}

proc get_buffer_cell { } {
    upvar sc_mainlib sc_mainlib

    return [sc_cfg_get library $sc_mainlib tool yosys buffer_cell]
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
yosys hierarchy -top $sc_topmodule

# Mark modules to keep from getting removed in flattening
preserve_modules

# Handle tristate buffers
set sc_tbuf "false"
if { [sc_cfg_get library $sc_mainlib tool yosys tristatebuffermap] != {} } {
    set sc_tbuf "true"

    yosys tribuf
}

set flatten_design [sc_cfg_tool_task_get var flatten]
set synth_args []
if { $flatten_design } {
    lappend synth_args "-flatten"
}
foreach extra_map [sc_cfg_tool_task_get var synth_extra_map] {
    lappend synth_args "-extra-map" $extra_map
}

# Specify hierarchy separator
yosys scratchpad \
    -set flatten.separator "[sc_cfg_tool_task_get var hierarchy_separator]"

# Start synthesis
yosys synth {*}$synth_args -top $sc_topmodule -run begin:fine

# Perform memory mapping, if available
sc_map_memory $sc_memory_libmap_files $sc_memory_techmap_files 0

# Perform hierarchy flattening
if { !$flatten_design && [sc_cfg_tool_task_get var auto_flatten] } {
    set sc_hier_threshold [sc_cfg_tool_task_get var hier_threshold]

    sc_annotate_gate_cost_equivalent
    yosys keep_hierarchy -min_cost $sc_hier_threshold

    yosys synth -flatten {*}$synth_args -top $sc_topmodule -run coarse:fine
}

# Finish synthesis
# Unroll of synth -run fine:check
set opt_args []
if { [sc_cfg_tool_task_get var opt_undriven] } {
    lappend opt_args -undriven
}
yosys opt -fast -mux_undef -mux_bool -fine {*}$opt_args
yosys memory_map
yosys opt -mux_undef -mux_bool -fine {*}$opt_args

set tech_map_args []
lappend tech_map_args "-map" "+/techmap.v"
foreach extra_map [sc_cfg_tool_task_get var synth_extra_map] {
    lappend tech_map_args "-map" $extra_map
}
yosys techmap {*}$tech_map_args

yosys opt -fast
yosys abc -fast
yosys opt -fast

yosys hierarchy -check
yosys stat
yosys check

# Logic locking
if { [sc_cfg_tool_task_get var lock_design] } {
    if { [sc_load_plugin moosic] } {
        # moosic cannot handle hierarchy
        foreach module [get_modules "*"] {
            yosys select -module $module
            yosys setattr -mod -unset keep_hierarchy
            yosys select -clear
        }
        yosys flatten
        yosys opt -fast

        set ll_port [sc_cfg_tool_task_get var lock_design_port]
        set ll_key [sc_cfg_tool_task_get var lock_design_key]
        set ll_bits [expr { 4 * [string length $ll_key] }]
        yosys select -module $sc_topmodule
        yosys logic_locking \
            -nb-locked $ll_bits \
            -key $ll_key \
            -port-name $ll_port
        yosys tee -o reports/logic_locking.rpt {ll_show}
        yosys select -clear
    } else {
        puts "ERROR: unable to load moosic"
    }
}

# https://github.com/hdl/bazel_rules_hdl/blob/4cca75f32a3869a57c0635bc7426a696a15ec143/synthesis/synth.tcl#L54C1-L58C26
# Remove $print cells.  These cells represent Verilog $display() tasks.
# Some place and route tools cannot handle these in the output Verilog,
# so remove them here.
yosys delete {*/t:$print}
yosys chformal -remove

# Recheck hierarchy to remove all unused modules
yosys hierarchy -top $sc_topmodule

yosys opt -purge

########################################################
# Technology Mapping
########################################################

# Handle tristate buffers
if { $sc_tbuf == "true" } {
    set sc_tbuf_techmap [sc_cfg_get library $sc_mainlib tool yosys tristatebuffermap]
    # Map tristate buffers
    yosys techmap -map $sc_tbuf_techmap
    post_techmap -fast
}

if { [sc_cfg_tool_task_get var map_adders] } {
    set sc_adder_techmap [sc_cfg_get library $sc_mainlib tool yosys addermap]
    # extract the full adders
    yosys extract_fa
    # map full adders
    yosys techmap -map $sc_adder_techmap
    post_techmap -fast
}

foreach mapfile [sc_cfg_get library $sc_mainlib tool yosys techmap] {
    yosys techmap -map $mapfile
    post_techmap -fast
}

if { [sc_cfg_tool_task_get var autoname] } {
    # use autoname to preserve some design naming
    # by doing it before dfflibmap the names will be slightly shorter since they will
    # only contain the $DFF_P names vs. the full library name of the associated flip-flop
    yosys rename -wire
}

if { [sc_cfg_tool_task_get var map_clockgates] } {
    set clockgate_dont_use []
    foreach lib $sc_logiclibs {
        foreach cell [sc_cfg_get library $lib asic cells dontuse] {
            lappend clockgate_dont_use -dont_use $cell
        }
    }
    set clockgate_liberty []
    foreach lib_file $sc_libraries {
        lappend clockgate_dont_use "-liberty" $lib_file
    }

    yosys clockgate \
        {*}$clockgate_dont_use \
        {*}$clockgate_liberty \
        -min_net_size [sc_cfg_tool_task_get var min_clockgate_fanout]
}

set dfflibmap_dont_use []
foreach lib $sc_logiclibs {
    foreach cell [sc_cfg_get library $lib asic cells dontuse] {
        lappend dfflibmap_dont_use -dont_use $cell
    }
}
set dfflibmap_liberty []
foreach lib_file $sc_libraries {
    lappend dfflibmap_liberty "-liberty" $lib_file
}

yosys dfflibmap {*}$dfflibmap_dont_use {*}$dfflibmap_liberty

# perform final techmap and opt in case previous techmaps introduced constructs that need
# techmapping
post_techmap

source "$sc_refdir/syn_strategies.tcl"

set script ""
set sc_strategy [sc_cfg_tool_task_get var strategy]
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
if { [sc_cfg_tool_task_exists var abc_clock_period] } {
    set abc_clock_period [sc_cfg_tool_task_get var abc_clock_period]
    if { [llength $abc_clock_period] != 0 } {
        # assumes units are ps
        lappend abc_args "-D" $abc_clock_period
    }
}
if { [file exists $sc_abc_constraints] } {
    lappend abc_args "-constr" $sc_abc_constraints
}
if { $script != "" } {
    lappend abc_args "-script" $script
}
# Synthesize to main library only
foreach lib_file [sc_cfg_tool_task_get var synthesis_libraries] {
    if { [string first "sc_${sc_mainlib}_" [lindex [file split $lib_file] end]] == 0 } {
        lappend abc_args "-liberty" $lib_file
    }
}
set abc_dont_use []
foreach group "dontuse hold clkbuf clkgate clklogic" {
    foreach cell [sc_cfg_get library $sc_mainlib asic cells $group] {
        lappend abc_dont_use -dont_use $cell
    }
}

yosys abc {*}$abc_args {*}$abc_dont_use

########################################################
# Cleanup
########################################################

yosys clean -purge

# Recheck hierarchy to remove all unused modules
yosys hierarchy -top $sc_topmodule

if { [sc_cfg_tool_task_get var tie_undef] == "high" } {
    yosys setundef -one
} elseif { [sc_cfg_tool_task_get var tie_undef] == "low" } {
    yosys setundef -zero
}

yosys splitnets

yosys clean -purge

set yosys_hilomap_args []
if { [sc_has_tie_cell low] } {
    lappend yosys_hilomap_args -locell {*}[sc_get_tie_cell low]
}
if { [sc_has_tie_cell high] } {
    lappend yosys_hilomap_args -hicell {*}[sc_get_tie_cell high]
}
if { [sc_cfg_tool_task_get var add_tieoffs] && [llength $yosys_hilomap_args] != 0 } {
    yosys hilomap -singleton {*}$yosys_hilomap_args
}

if {
    [has_buffer_cell] &&
    [sc_cfg_tool_task_get var add_buffers]
} {
    yosys insbuf -buf {*}[get_buffer_cell]
}

yosys clean -purge

set stat_libs []
foreach lib_file $sc_libraries {
    lappend stat_libs "-liberty" $lib_file
}
# turn off echo to prevent the stat command from showing up in the json file
yosys echo off
yosys tee -o ./reports/stat.json stat -json -top $sc_topmodule {*}$stat_libs
yosys echo on

########################################################
# Write Netlist
########################################################
yosys write_verilog -noexpr -nohex -nodec "outputs/${sc_topmodule}.vg"
yosys write_json "outputs/${sc_topmodule}.netlist.json"
