# This file contains a set of procedures that are shared
# between syn_asic.tcl and syn_fpga.tcl

proc post_techmap { { opt_args "" } } {
    # perform techmap in case previous techmaps introduced constructs
    # that need techmapping
    yosys techmap
    # Quick optimization
    yosys opt {*}$opt_args -purge
}
