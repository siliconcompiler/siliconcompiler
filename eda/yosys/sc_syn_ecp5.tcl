# Yosys synthesis script for ecp5

proc syn_ecp5 {topmodule} {
    set output_json "outputs/${topmodule}_netlist.json"

    # Use built-in ecp5 synthesis command:
    # http://www.clifford.at/yosys/cmd_synth_ecp5.html
    yosys synth_ecp5 -top $topmodule -json $output_json
}
