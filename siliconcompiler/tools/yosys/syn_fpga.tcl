set sc_partname  [dict get $sc_cfg fpga partname]
set build_dir [dict get $sc_cfg option builddir]
set job_name [dict get $sc_cfg option jobname]
set step [dict get $sc_cfg arg step]
set index [dict get $sc_cfg arg index]

#TODO: add logic that remaps yosys built in name based on part number

# Run this first to handle module instantiations in generate blocks -- see
# comment in syn_asic.tcl for longer explanation.
yosys hierarchy -top $sc_design

if {[string match {ice*} $sc_partname]} {
    yosys synth_ice40 -top $sc_design -json "${sc_design}_netlist.json"
} else {
    yosys script "${build_dir}/${sc_design}/${job_name}/${step}/${index}/inputs/vpr_yosyslib/synthesis.ys"
}

# turn off echo to prevent the stat command from showing up in the json file
yosys echo off
yosys tee -o ./reports/stat.json stat -json -top $sc_design
yosys echo on
