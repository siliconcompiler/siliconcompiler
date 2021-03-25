# Yosys synthesis script for OpenFPGA
# Based on https://github.com/lnis-uofu/OpenFPGA/blob/master/openfpga_flow/misc/ys_tmpl_yosys_vpr_flow.ys

proc syn_openfpga {topmodule lut_size} {
    set output_blif "outputs/$topmodule.blif"

    # Technology mapping
    yosys hierarchy -top $topmodule
    yosys proc
    yosys techmap -D NO_LUT -map +/adff2dff.v

    # Synthesis
    yosys synth -top $topmodule -flatten
    yosys clean

    # LUT mapping
    yosys abc -lut $lut_size

    # Check
    yosys synth -run check

    # Clean and output blif
    yosys opt_clean -purge
    yosys write_blif $output_blif
}
