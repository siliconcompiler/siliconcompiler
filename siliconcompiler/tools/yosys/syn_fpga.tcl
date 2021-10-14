set sc_partname  [dict get $sc_cfg fpga partname]

#TODO: add logic that remaps yosys built in name based on part number

# Run this first to handle module instantiations in generate blocks -- see
# comment in syn_asic.tcl for longer explanation.
yosys hierarchy -top $sc_design

if {[string match {ice*} $sc_partname]} {
    yosys synth_ice40 -top $sc_design -json "${sc_design}_netlist.json"
} else {

    source fpga_lutsize.tcl

    set output_blif "outputs/$topmodule.blif"

    # Technology mapping
    yosys proc
    yosys techmap -D NO_LUT -map +/adff2dff.v

    # Synthesis
    yosys synth -top $sc_design -flatten
    yosys clean

    # LUT mapping
    yosys abc -lut $lutsize

    # Check
    yosys synth -run check

    # Clean and output blif
    yosys opt_clean -purge
}
