###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

yosys echo on

###############################
# Schema Adapter
###############################

set sc_tool yosys
set sc_step [sc_cfg_get arg step]
set sc_index [sc_cfg_get arg index]
set sc_flow [sc_cfg_get option flow]
set sc_task [sc_cfg_get flowgraph $sc_flow $sc_step $sc_index task]
set sc_refdir [sc_cfg_tool_task_get refdir]

####################
# DESIGNER's CHOICE
####################

set sc_design [sc_top]
set sc_flow [sc_cfg_get option flow]
set sc_optmode [sc_cfg_get option optmode]
set sc_pdk [sc_cfg_get option pdk]

########################################################
# Helper function
########################################################

source "$sc_refdir/procs.tcl"

########################################################
# Design Inputs
########################################################

# TODO: the original OpenFPGA synth script used read_verilog with -nolatches. Is
# that a flag we might want here?

set input_verilog "inputs/$sc_design.v"
if { [file exists $input_verilog] } {
    if { [lindex [sc_cfg_tool_task_get var use_slang] 0] == "true" && [sc_load_plugin slang] } {
        # This needs some reordering of loaded to ensure blackboxes are handled
        # before this
        set slang_params []
        if { [sc_cfg_exists option param] } {
            dict for {key value} [sc_cfg_get option param] {
                if { ![string is integer $value] } {
                    set value [concat \"$value\"]
                }

                lappend slang_params -G "${key}=${value}"
            }
        }
        yosys read_slang \
            -D SYNTHESIS \
            --keep-hierarchy \
            --top $sc_design \
            {*}$slang_params \
            $input_verilog
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
}

####################
# Helper functions
####################
proc legalize_flops { feature_set } {
    set legalize_flop_types []

    if {
        [lsearch -exact $feature_set enable] >= 0 &&
        [lsearch -exact $feature_set async_set] >= 0 &&
        [lsearch -exact $feature_set async_reset] >= 0
    } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN?_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN?P_
        lappend legalize_flop_types \$_DFFSR_PNN_
        lappend legalize_flop_types \$_DFFSRE_PNNP_
    } elseif {
        [lsearch -exact $feature_set enable] >= 0 &&
        [lsearch -exact $feature_set async_set] >= 0
    } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN1_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN1P_
    } elseif {
        [lsearch -exact $feature_set enable] >= 0 &&
        [lsearch -exact $feature_set async_reset] >= 0
    } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN0_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN0P_
    } elseif { [lsearch -exact $feature_set enable] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_P??_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_P??P_
    } elseif {
        [lsearch -exact $feature_set async_set] >= 0 &&
        [lsearch -exact $feature_set async_reset] >= 0
    } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN?_
        lappend legalize_flop_types \$_DFFSR_PNN_
    } elseif { [lsearch -exact $feature_set async_set] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN1_
    } elseif { [lsearch -exact $feature_set async_reset] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN0_
    } else {
        # Choose to legalize to async resets even though they
        # won't tech map.  Goal is to get the user to fix
        # their code and put in synchronous resets
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_P??_
    }

    set legalize_list []
    foreach flop_type $legalize_flop_types {
        lappend legalize_list -cell $flop_type 01
    }
    yosys log "Legalize list: $legalize_list"
    yosys dfflegalize {*}$legalize_list
}

proc get_dsp_options { sc_syn_dsp_options } {
    set option_text [list]
    foreach dsp_option $sc_syn_dsp_options {
        lappend option_text -D $dsp_option
    }
    return $option_text
}

set sc_partname [sc_cfg_get fpga partname]
set build_dir [sc_cfg_get option builddir]
set job_name [sc_cfg_get option jobname]
set step [sc_cfg_get arg step]
set index [sc_cfg_get arg index]

set sc_syn_lut_size \
    [sc_cfg_get fpga $sc_partname lutsize]

if { [sc_cfg_exists fpga $sc_partname var feature_set] } {
    set sc_syn_feature_set \
        [sc_cfg_get fpga $sc_partname var feature_set]
} else {
    set sc_syn_feature_set [list]
}

if { [sc_cfg_exists fpga $sc_partname var yosys_dsp_options] } {
    yosys log "Process Yosys DSP techmap options."
    set sc_syn_dsp_options \
        [sc_cfg_get fpga $sc_partname var yosys_dsp_options]
    yosys log "Yosys DSP techmap options = $sc_syn_dsp_options"
} else {
    set sc_syn_dsp_options [list]
}

# TODO: add logic that remaps yosys built in name based on part number

# Run this first to handle module instantiations in generate blocks -- see
# comment in syn_asic.tcl for longer explanation.
yosys hierarchy -top $sc_design

if { [string match {ice*} $sc_partname] } {
    yosys synth_ice40 -top $sc_design -json "${sc_design}.netlist.json"
} else {
    # Pre-processing step:  if DSPs instance are hard-coded into
    # the user's design, we can use a blackbox flow for DSP mapping
    # as follows:

    if { [sc_cfg_exists fpga $sc_partname file yosys_macrolib] } {
        set sc_syn_macrolibs \
            [sc_cfg_get fpga $sc_partname file yosys_macrolib]

        foreach macrolib $sc_syn_macrolibs {
            yosys read_verilog -lib $macrolib
        }
    }

    # Match VPR reference flow's hierarchy check, including their comments

    yosys proc
    yosys flatten

    # Note there are two possibilities for how macro mapping might be done:
    # using the extract command (to pattern match user RTL against
    # the techmap) or using the techmap command.  The latter is better
    # for mapping simple multipliers; the former is better (for now)
    # for mapping more complex DSP blocks (MAC, pipelined blocks, etc).
    # and is also more easily extensible to arbitrary hard macros.
    # Run separate passes of both to get best of both worlds

    # An extract pass needs to happen prior to other optimizations,
    # otherwise yosys can transform its internal model into something
    # that doesn't match the patterns defined in the extract library
    if { [sc_cfg_exists fpga $sc_partname file yosys_extractlib] } {
        set sc_syn_extractlibs \
            [sc_cfg_get fpga $sc_partname file yosys_extractlib]

        foreach extractlib $sc_syn_extractlibs {
            yosys log "Run extract with $extractlib"
            yosys extract -map $extractlib
        }
    }

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

    # Here is a remaining customization pass for DSP tech mapping

    #Map DSP blocks before doing anything else,
    #so that we don't convert any math blocks
    #into other primitives

    if { [sc_cfg_exists fpga $sc_partname file yosys_dsp_techmap] } {
        set sc_syn_dsp_library \
            [sc_cfg_get fpga $sc_partname file yosys_dsp_techmap]

        yosys log "Run techmap flow for DSP Blocks"
        set formatted_dsp_options [get_dsp_options $sc_syn_dsp_options]
        yosys techmap -map +/mul2dsp.v -map $sc_syn_dsp_library \
            {*}$formatted_dsp_options

        post_techmap
    }

    #Mimic ICE40 flow by running an alumacc and memory -nomap passes
    #after DSP mapping
    yosys alumacc
    yosys opt
    yosys memory -nomap
    yosys opt -full

    yosys techmap -map +/techmap.v

    set sc_syn_memory_libmap ""
    if { [sc_cfg_exists fpga $sc_partname file yosys_memory_libmap] } {
        set sc_syn_memory_libmap \
            [sc_cfg_get fpga $sc_partname file yosys_memory_libmap]
    }
    set sc_do_rom_map [expr { [lsearch -exact $sc_syn_feature_set mem_init] < 0 }]
    set sc_syn_memory_library ""
    if { [sc_cfg_exists fpga $sc_partname file yosys_memory_techmap] } {
        set sc_syn_memory_library \
            [sc_cfg_get fpga $sc_partname file yosys_memory_techmap]
    }

    if { [sc_map_memory $sc_syn_memory_libmap $sc_syn_memory_library $sc_do_rom_map] } {
        post_techmap
    }

    #After doing memory mapping, turn any remaining
    #$mem_v2 instances into flop arrays
    yosys memory_map
    yosys demuxmap
    yosys simplemap

    legalize_flops $sc_syn_feature_set

    if { [sc_cfg_exists fpga $sc_partname file yosys_flop_techmap] } {
        set sc_syn_flop_library \
            [sc_cfg_get fpga $sc_partname file yosys_flop_techmap]
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
yosys tee -o ./reports/stat.json stat -json -top $sc_design
yosys echo on

########################################################
# Write Netlist
########################################################
yosys write_verilog -noexpr -nohex -nodec "outputs/${sc_design}.vg"
yosys write_json "outputs/${sc_design}.netlist.json"
yosys write_blif "outputs/${sc_design}.blif"
