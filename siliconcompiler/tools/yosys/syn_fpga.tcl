set sc_partname  [dict get $sc_cfg fpga partname]

#TODO: add logic that remaps yosys built in name based on part number

# Run this first to handle module instantiations in generate blocks -- see
# comment in syn_asic.tcl for longer explanation.
yosys hierarchy -top $sc_design

if {[string match {ice*} $sc_partname]} {
    yosys synth_ice40 -top $sc_design -json "${sc_design}_netlist.json"
} else {
    yosys script "/home/kimia/vpr_example/build/or1200/syn/input/vpr_yosyslib/synthesis.ys"
}
