
source "$sc_refdir/syn_asic_fpga_shared.tcl"

proc legalize_flops { feature_set } {

    set legalize_flop_types []

    if { [lsearch -exact $feature_set enable] >= 0 && \
         [lsearch -exact $feature_set async_set] >= 0 && \
         [lsearch -exact $feature_set async_reset] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN?_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN?P_
        lappend legalize_flop_types \$_DFFSR_PNN_
        lappend legalize_flop_types \$_DFFSRE_PNNP_
    } elseif { [lsearch -exact $feature_set enable] >= 0 && \
               [lsearch -exact $feature_set async_set] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN1_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN1P_
    } elseif { [lsearch -exact $feature_set enable] >= 0 && \
               [lsearch -exact $feature_set async_reset] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN0_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN0P_
    } elseif { [lsearch -exact $feature_set enable] >= 0 } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_P??_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_P??P_
    } elseif { [lsearch -exact $feature_set async_set] >= 0 && \
               [lsearch -exact $feature_set async_reset] >= 0 } {
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

    set option_text [ list ]
    foreach dsp_option $sc_syn_dsp_options {
        lappend option_text -D $dsp_option
    }
    return $option_text
}

set sc_partname [dict get $sc_cfg fpga partname]
set build_dir [dict get $sc_cfg option builddir]
set job_name [dict get $sc_cfg option jobname]
set step [dict get $sc_cfg arg step]
set index [dict get $sc_cfg arg index]

set sc_syn_lut_size \
    [dict get $sc_cfg fpga $sc_partname lutsize]

if { [dict exists $sc_cfg fpga $sc_partname var feature_set] } {
    set sc_syn_feature_set \
        [dict get $sc_cfg fpga $sc_partname var feature_set]
} else {
    set sc_syn_feature_set [ list ]
}

if { [dict exists $sc_cfg fpga $sc_partname var yosys_dsp_options] } {
    yosys log "Process Yosys DSP techmap options."
    set sc_syn_dsp_options \
        [dict get $sc_cfg fpga $sc_partname var yosys_dsp_options]
    yosys log "Yosys DSP techmap options = $sc_syn_dsp_options"
} else {
    set sc_syn_dsp_options [ list ]
}

# TODO: add logic that remaps yosys built in name based on part number

# Run this first to handle module instantiations in generate blocks -- see
# comment in syn_asic.tcl for longer explanation.
yosys hierarchy -top $sc_design

if { [string match {ice*} $sc_partname] } {
    yosys synth_ice40 -top $sc_design -json "${sc_design}_netlist.json"
} else {

    # Pre-processing step:  if DSPs instance are hard-coded into
    # the user's design, we can use a blackbox flow for DSP mapping
    # as follows:

    if { [dict exists $sc_cfg fpga $sc_partname file yosys_macrolib] } {

        set sc_syn_macrolibs \
            [dict get $sc_cfg fpga $sc_partname file yosys_macrolib]

        foreach macrolib $sc_syn_macrolibs {
            yosys read_verilog -lib $macrolib
        }
    }

    # Match VPR reference flow's hierarchy check, including their comments

    yosys proc
    yosys flatten

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

    #Map DSP blocks before doing anything else,
    #so that we don't convert any math blocks
    #into other primitives

    # Note there are two possibilities for how mapping might be done:
    # using the extract command (to pattern match user RTL against
    # the techmap) or using the techmap command.  The latter is better
    # for mapping simple multipliers; the former is better (for now)
    # for mapping more complex DSP blocks (MAC, pipelined blocks, etc).
    # and also more extensible to arbitrary hard macros.  Run separate
    # passes of both to get best of both worlds

    if { [dict exists $sc_cfg fpga $sc_partname file yosys_extractlib] } {
        set sc_syn_extractlibs \
            [dict get $sc_cfg fpga $sc_partname file yosys_extractlib]

        foreach extractlib $sc_syn_extractlibs {
            yosys log "Run extract with $extractlib"
            yosys extract -map $extractlib
        }
    }

    if { [dict exists $sc_cfg fpga $sc_partname file yosys_dsp_techmap] } {
        set sc_syn_dsp_library \
            [dict get $sc_cfg fpga $sc_partname file yosys_dsp_techmap]

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

    if { [dict exists $sc_cfg fpga $sc_partname file yosys_memory_libmap] } {

        set sc_syn_memory_libmap \
            [dict get $sc_cfg fpga $sc_partname file yosys_memory_libmap]

        yosys memory_libmap -lib $sc_syn_memory_libmap

    }

    if { [lsearch -exact $sc_syn_feature_set mem_init] < 0 } {
        yosys memory_map -rom-only
    }

    if { [dict exists $sc_cfg fpga $sc_partname file yosys_memory_techmap] } {

        set sc_syn_memory_library \
            [dict get $sc_cfg fpga $sc_partname file yosys_memory_techmap]
        yosys techmap -map $sc_syn_memory_library

        post_techmap
    }

    legalize_flops $sc_syn_feature_set

    if { [dict exists $sc_cfg fpga $sc_partname file yosys_flop_techmap] } {
        set sc_syn_flop_library \
            [dict get $sc_cfg fpga $sc_partname file yosys_flop_techmap]
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
