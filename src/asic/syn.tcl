########################################################
# Options
########################################################
source ./scc_setup.tcl

set syn_verilog "../import/$scc_topmodule.v"

########################################################
# Technology Mapping
########################################################

yosys read_verilog $syn_verilog
yosys synth "-flatten" -top $scc_topmodule
yosys opt -purge

########################################################
# Technology Mapping
########################################################

yosys dfflibmap -liberty $scc_lib
yosys opt
yosys abc -liberty $scc_lib

########################################################
# Write Netlist
########################################################
yosys setundef -zero
yosys splitnets
yosys clean
yosys write_verilog -noattr -noexpr -nohex -nodec "$scc_topmodule.v"
