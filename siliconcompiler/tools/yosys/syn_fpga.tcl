
proc legalize_flops { feature_set } {

    set legalize_flop_types []

    if { ( [lsearch -exact $feature_set enable] ) && \
	     ( [lsearch -exact $feature_set async_set] ) && \
	     ( [lsearch -exact $feature_set async_reset] ) } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN?_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN?P_
        lappend legalize_flop_types \$_DFFSR_PNN_
        lappend legalize_flop_types \$_DFFSRE_PNNP_
    } elseif { ( [lsearch -exact $feature_set enable] ) && \
		   ( [lsearch -exact $feature_set async_set] ) } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN1_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN1P_
    } elseif { ( [lsearch -exact $feature_set enable] ) && \
		   ( [lsearch -exact $feature_set async_reset] ) } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN0_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_PN0P_
    } elseif { ( [lsearch -exact $feature_set enable] ) } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_P??_
        lappend legalize_flop_types \$_DFFE_PP_
        lappend legalize_flop_types \$_DFFE_P??P_
    } elseif { ( [lsearch -exact $feature_set async_set] ) && \
		   ( [lsearch -exact $feature_set async_reset] ) } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN?_
        lappend legalize_flop_types \$_DFFSR_PNN_
    } elseif { ( [lsearch -exact $feature_set async_set] ) } {
        lappend legalize_flop_types \$_DFF_P_
        lappend legalize_flop_types \$_DFF_PN1_
    } elseif { ( [lsearch -exact $feature_set async_reset] ) } {
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

set sc_partname [dict get $sc_cfg fpga partname]
set build_dir [dict get $sc_cfg option builddir]
set job_name [dict get $sc_cfg option jobname]
set step [dict get $sc_cfg arg step]
set index [dict get $sc_cfg arg index]

set sc_syn_lut_size \
    [dict get $sc_cfg fpga $sc_partname lutsize]

set sc_syn_feature_set \
    [dict get $sc_cfg tool $sc_tool task $sc_task var feature_set]

set sc_syn_legalize_flops \
    [dict get $sc_cfg tool $sc_tool task $sc_task var legalize_flops]

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
        legalize_flops $sc_syn_feature_set
    }

    #Perform preliminary buffer insertion before passing to ABC to help reduce
    #the overhead of final buffer insertion downstream
    yosys insbuf

    yosys abc -lut $sc_syn_lut_size -dff

    yosys flatten
    yosys clean

    if {[dict exists $sc_cfg tool $sc_tool task $sc_task file flop_techmap]} {
        set sc_syn_flop_library \
            [dict get $sc_cfg tool $sc_tool task $sc_task file flop_techmap]
        yosys techmap -map $sc_syn_flop_library

        # perform techmap in case previous techmaps introduced constructs
        # that need techmapping
        yosys techmap
        # Quick optimization
        yosys opt -purge
    }

}

yosys echo off
yosys tee -o ./reports/stat.json stat -json -top $sc_design
yosys echo on
