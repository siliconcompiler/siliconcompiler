
proc legalize_flops { async_reset async_set enable library } {

    if { $library eq "None" } {
        # ***NOTE:  Choose to legalize to async resets even though they won't
        #           tech map to get the user to fix their code and put in
        #           synchronous resets
        yosys dfflegalize \
            -cell \$_DFF_P_ 01 \
            -cell \$_DFF_P??_ 01 \

    } else {
        if { $enable == 1 } {
            if { $async_set == 1 } {
                if { $async_reset == 1 } {
                    yosys log "Legalize DFFs for flop enable"
                    yosys log "Legalize DFFs for async set"
                    yosys log "Legalize DFFs for async reset"
                    yosys dfflegalize \
                        -cell \$_DFF_P_ 01 \
                        -cell \$_DFF_PN?_ 01 \
                        -cell \$_DFFE_PP_ 01 \
                        -cell \$_DFFE_PN?P_ 01 \
                        -cell \$_DFFSR_PNN_ 01 \
                        -cell \$_DFFSRE_PNNP_ 01 \

                } else {
                    yosys log "Legalize DFFs for flop enable"
                    yosys log "Legalize DFFs for async set"
                    yosys dfflegalize \
                        -cell \$_DFF_P_ 01 \
                        -cell \$_DFF_PN1_ 01 \
                        -cell \$_DFFE_PP_ 01 \
                        -cell \$_DFFE_PN1P_ 01 \

                }
            } else {
                if { $async_reset == 1 } {
                    yosys log "Legalize DFFs for flop enable"
                    yosys log "Legalize DFFs for async reset"
                    yosys dfflegalize \
                        -cell \$_DFF_P_ 01 \
                        -cell \$_DFF_PN0_ 01 \
                        -cell \$_DFFE_PP_ 01 \
                        -cell \$_DFFE_PN0P_ 01 \

                } else {
                    # Choose to legalize to async resets even though they won't
                    # tech map to get the user to fix their code and put in
                    # synchronous resets
                    yosys log "Legalize DFFs for flop enable"
                    yosys dfflegalize \
                        -cell \$_DFF_P_ 01  \
                        -cell \$_DFF_P??_ 01 \
                        -cell \$_DFFE_PP_ 01 \
                        -cell \$_DFFE_P??P_ 01 \

                }
            }
        } else {
            if { $async_set == 1 } {
                if { $async_reset == 1 } {
                    yosys log "Legalize DFFs for async set"
                    yosys log "Legalize DFFs for async reset"
                    yosys dfflegalize \
                        -cell \$_DFF_P_ 01 \
                        -cell \$_DFF_PN?_ 01 \
                        -cell \$_DFFSR_PNN_ 01 \

                } else {
                    yosys log "Legalize DFFs for async set"
                    yosys dfflegalize \
                        -cell \$_DFF_P_ 01 \
                        -cell \$_DFF_PN1_ 01 \

                }
            } else {
                if { $async_reset == 1 } {
                    yosys log "Legalize DFFs for async reset"
                    yosys dfflegalize \
                        -cell \$_DFF_P_ 01 \
                        -cell \$_DFF_PN0_ 01 \

                } else {
                    # Choose to legalize to async resets even though they
                    # won't tech map.  Goal is to get the user to fix
                    # their code and put in synchronous resets
                    yosys log "Legalize DFFs for synchronous reset only"
                    yosys dfflegalize \
                        -cell \$_DFF_P_ 01 \
                        -cell \$_DFF_P??_ 01 \

                }
            }
        }
    }
}

set sc_partname [dict get $sc_cfg fpga partname]
set build_dir [dict get $sc_cfg option builddir]
set job_name [dict get $sc_cfg option jobname]
set step [dict get $sc_cfg arg step]
set index [dict get $sc_cfg arg index]

set sc_syn_lut_size \
    [dict get $sc_cfg fpga $sc_partname lutsize]
set sc_syn_flop_async_set \
    [dict get $sc_cfg tool $sc_tool task $sc_task var flop_async_set]
set sc_syn_flop_async_reset \
    [dict get $sc_cfg tool $sc_tool task $sc_task var flop_async_reset]
set sc_syn_flop_enable \
    [dict get $sc_cfg tool $sc_tool task $sc_task var flop_enable]
set sc_syn_legalize_flops \
    [dict get $sc_cfg tool $sc_tool task $sc_task var legalize_flops]

if {[dict exists $sc_cfg tool $sc_tool task $sc_task file flop_techmap]} {
    set sc_syn_flop_library \
        [dict get $sc_cfg tool $sc_tool task $sc_task file flop_techmap]
} else {
    set sc_syn_flop_library "None"
}

# TODO: add logic that remaps yosys built in name based on part number

# Run this first to handle module instantiations in generate blocks -- see
# comment in syn_asic.tcl for longer explanation.
yosys hierarchy -top $sc_design

if {[string match {ice*} $sc_partname]} {
    yosys synth_ice40 -top $sc_design -json "${sc_design}_netlist.json"
} else {
    # Match VPR reference flow's hierarchy check, including their comments

    # Here are the notes from the VPR developers
    # These commands follow the generic `synth'
    # command script inside Yosys
    # The -libdir argument allows Yosys to search the current
    # directory for any definitions to modules it doesn't know
    # about, such as hand-instantiated (not inferred) memories

    yosys hierarchy -check -auto-top

    #Rename top level module to match selected design name;
    #This allows us to enforce some naming consistency in
    #automated flows
    yosys rename -top ${sc_design}

    yosys proc
    #select -module ${sc_design}
    #flatten -wb
    #flatten

    #Match the optimization passes of the VTR reference yosys flow
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
    yosys opt
    yosys memory -nomap
    yosys opt -full

    #Do our own thing from here
    yosys techmap -map +/techmap.v

    if { $sc_syn_legalize_flops != 0 } {
        legalize_flops \
            $sc_syn_flop_async_reset \
            $sc_syn_flop_async_set \
            $sc_syn_flop_enable \
            $sc_syn_flop_library
    }

    #Perform preliminary buffer insertion before passing to ABC to help reduce
    #the overhead of final buffer insertion downstream
    yosys insbuf

    yosys abc -lut $sc_syn_lut_size -dff

    yosys flatten
    yosys clean

    if { $sc_syn_flop_library ne "None" } {
        yosys techmap -map $sc_syn_flop_library
    }

}

yosys echo off
yosys tee -o ./reports/stat.json stat -json -top $sc_design
yosys echo on
