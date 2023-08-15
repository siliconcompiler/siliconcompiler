set sc_partname  [dict get $sc_cfg fpga partname]
set build_dir [dict get $sc_cfg option builddir]
set job_name [dict get $sc_cfg option jobname]
set step [dict get $sc_cfg arg step]
set index [dict get $sc_cfg arg index]

set sc_syn_lut_size [dict get $sc_cfg fpga $sc_partname lutsize]

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

    yosys dfflegalize -cell \$_DFF_P_ 01 -cell \$_DFF_P??_ 01 

    #Perform preliminary buffer insertion before passing to ABC to help reduce
    #the overhead of final buffer insertion downstream
    yosys insbuf

    yosys abc -lut $sc_syn_lut_size -dff

    yosys flatten
    yosys clean

}

yosys echo off
yosys tee -o ./reports/stat.json stat -json -top $sc_design
yosys echo on
