# Yosys synthesis script for ice40

proc syn_ice40 {topmodule} {
    set output_json "outputs/$topmodule.json"

    # Use built-in ice40 synthesis command:
    # http://yosyshq.net/yosys/cmd_synth_ice40.html
    yosys synth_ice40 -top $topmodule -json $output_json
}
