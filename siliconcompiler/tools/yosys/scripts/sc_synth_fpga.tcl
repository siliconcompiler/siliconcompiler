###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

yosys echo on

####################
# DESIGNER's CHOICE
####################

set sc_optmode [sc_cfg_get option optmode]

########################################################
# Helper function
########################################################

source "$sc_refdir/procs.tcl"

########################################################
# Design Inputs
########################################################

# TODO: the original OpenFPGA synth script used read_verilog with -nolatches. Is
# that a flag we might want here?

set input_verilog "inputs/$sc_topmodule.v"
if { ![file exists $input_verilog] } {
    set input_verilog "inputs/$sc_topmodule.sv"
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
        $input_verilog
    yosys setattr -unset init
} else {
    # Use -noblackbox to correctly interpret empty modules as empty,
    # actual black boxes are read in later
    # https://github.com/YosysHQ/yosys/issues/1468
    yosys read_verilog -noblackbox -sv $input_verilog

    ########################################################
    # Override top level parameters
    ########################################################

    sc_apply_params
}

set sc_designlib [sc_cfg_get fpga device]
set sc_partname [sc_cfg_get library $sc_designlib fpga partname]

set sc_syn_lut_size [sc_cfg_get library $sc_designlib fpga lutsize]

# TODO: add logic that remaps yosys built in name based on part number

# Run this first to handle module instantiations in generate blocks -- see
# comment in syn_asic.tcl for longer explanation.
yosys hierarchy -top $sc_topmodule

if {
    [sc_cfg_exists library $sc_designlib tool yosys fpga_config] &&
    [sc_cfg_get library $sc_designlib tool yosys fpga_config] != {} &&
    [sc_load_plugin wildebeest]
} {
    set synth_fpga_args []
    if { [sc_cfg_tool_task_get var synth_opt_mode] != "none" } {
        lappend synth_fpga_args \
            -opt [sc_cfg_tool_task_get var synth_opt_mode]
    }
    if { [sc_cfg_tool_task_get var synth_insert_buffers] } {
        lappend synth_fpga_args -insbuf
    }

    yosys synth_fpga \
        -config [sc_cfg_get library $sc_designlib tool yosys fpga_config] \
        -show_config \
        -top $sc_topmodule \
        {*}$synth_fpga_args
} elseif { [string match {ice*} $sc_partname] } {
    yosys synth_ice40 -top $sc_topmodule
} else {
    set sc_syn_feature_set [sc_cfg_get library $sc_designlib tool yosys feature_set]

    yosys log "Process Yosys DSP techmap options."
    set sc_syn_dsp_options [sc_cfg_get library $sc_designlib tool yosys dsp_options]
    yosys log "Yosys DSP techmap options = $sc_syn_dsp_options"

    # Pre-processing step:  if DSPs instance are hard-coded into
    # the user's design, we can use a blackbox flow for DSP mapping
    # as follows:

    foreach macrolib [sc_cfg_get library $sc_designlib tool yosys macrolib] {
        yosys read_verilog -lib $macrolib
    }

    # Match VPR reference flow's hierarchy check, including their comments

    yosys proc
    yosys flatten

    # Other hard macro passes can happen after the generic optimization
    # passes take place.

    #Generic optimization passes; this is a fusion of the VTR reference
    #flow and the Yosys synth_ice40 flow
    yosys opt_expr
    yosys opt_clean
    yosys check
    yosys opt -nodffe -nosdff
    yosys fsm
    yosys opt
    yosys wreduce
    yosys peepopt
    yosys opt_clean
    yosys share
    yosys techmap -map +/cmp2lut.v -D LUT_WIDTH=$sc_syn_lut_size
    yosys opt_expr
    yosys opt_clean

    # Here is a customization pass for DSP tech mapping

    #Map DSP blocks before doing anything else,
    #so that we don't convert any math blocks
    #into other primitives

    if { [sc_cfg_get library $sc_designlib tool yosys dsp_techmap] != {} } {
        set sc_syn_dsp_library \
            [sc_cfg_get library $sc_designlib tool yosys dsp_techmap]

        yosys log "Run techmap flow for DSP Blocks"
        yosys techmap -map +/mul2dsp.v -map $sc_syn_dsp_library \
            {*}[sc_fpga_get_dsp_options $sc_syn_dsp_options]

        post_techmap
    }

    #Mimic ICE40 flow by running an alumacc and memory -nomap passes
    #after DSP mapping
    yosys alumacc
    yosys opt
    yosys memory -nomap
    yosys opt -full

    yosys techmap -map +/techmap.v

    set sc_syn_memory_libmap [sc_cfg_get library $sc_designlib tool yosys memory_libmap]
    set sc_do_rom_map [expr { [lsearch -exact $sc_syn_feature_set mem_init] < 0 }]
    set sc_syn_memory_library [sc_cfg_get library $sc_designlib tool yosys memory_techmap]

    if { [sc_map_memory $sc_syn_memory_libmap $sc_syn_memory_library $sc_do_rom_map] } {
        post_techmap
    }

    #After doing memory mapping, turn any remaining
    #$mem_v2 instances into flop arrays
    yosys memory_map
    yosys demuxmap
    yosys simplemap

    sc_fpga_legalize_flops $sc_syn_feature_set

    set sc_syn_flop_library [sc_cfg_get library $sc_designlib tool yosys flop_techmap]
    if { $sc_syn_flop_library != {} } {
        yosys techmap -map $sc_syn_flop_library

        post_techmap
    }

    #Perform preliminary buffer insertion before passing to ABC to help reduce
    #the overhead of final buffer insertion downstream
    yosys insbuf

    yosys abc -lut $sc_syn_lut_size

    yosys setundef -zero
    yosys clean -purge
}

yosys echo off
yosys tee -o ./reports/stat.json stat -json -top $sc_topmodule
yosys echo on

########################################################
# Write Netlist
########################################################
yosys write_verilog -noexpr -nohex -nodec "outputs/${sc_topmodule}.vg"
yosys write_json "outputs/${sc_topmodule}.netlist.json"
yosys write_blif "outputs/${sc_topmodule}.blif"
