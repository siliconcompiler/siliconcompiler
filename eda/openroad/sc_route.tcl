
########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

set stage      "route"
set last_stage "cts"

source ./sc_setup.tcl

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg flow $stage refdir]
if {[dict get $sc_cfg flow $stage copy] eq True} {
    set scriptdir "./"
}
# Sourcing helper procedures
source $scriptdir/sc_procedures.tcl

#Massaging dict into simple local variables
set stackup      [dict get $sc_cfg asic stackup]
set target_libs  [dict get $sc_cfg asic targetlib]
set minlayer     [dict get $sc_cfg asic minlayer]
set maxlayer     [dict get $sc_cfg asic maxlayer]
set minmetal     [dict get $sc_cfg pdk aprlayer $stackup $minlayer name]
set maxmetal     [dict get $sc_cfg pdk aprlayer $stackup $maxlayer name]
set mainlib      [lindex $target_libs 0]
set libarch      [dict get $sc_cfg stdcell $mainlib libtype]
set pdklef       [dict get $sc_cfg stdcell $mainlib lef]
set techlef      [dict get $sc_cfg pdk aprtech $stackup $libarch openroad]
set topmodule    [dict get $sc_cfg design]

# TODO: Fetch from config dictionary instead of hardcoding.
set groute_min_layer 2
set groute_max_layer 10
set overflow_iter    100


# TritonRoute cannot handle polygonal pin pads.
# This is only an issue in Nangate45, which also provides a
# '.mod.lef' file with rectangular pads.
if  {[dict get $sc_cfg target] eq "freepdk45"} {
    regsub -all {\.lef} $pdklef .mod.lef pdklef
}

#Inputs
set input_verilog   "inputs/$topmodule.v"
set input_def       "inputs/$topmodule.def"
set input_sdc       "inputs/$topmodule.sdc"

#Outputs
set output_verilog  "outputs/$topmodule.v"
set output_tmp_def  "outputs/$topmodule\_tmp.def"
set output_lef      "outputs/merged.lef"
set output_def      "outputs/$topmodule.def"
set output_drc      "outputs/$topmodule.drc"
set output_sdc      "outputs/$topmodule.sdc"
set output_guide    "outputs/$topmodule.guide"

################################################################
# Read Inputs
################################################################

# Setup process.
read_lef $techlef
# Setup libraries.
foreach lib $target_libs {
    read_liberty [dict get $sc_cfg stdcell $lib model typical nldm lib]
    # Correct for polygonal pin sizes in nangate45 liberty.
    if  {$lib eq "NangateOpenCellLibrary"} {
        set target_lef [dict get $sc_cfg stdcell $lib lef]
        regsub -all {\.lef} $target_lef .mod.lef target_lef
        read_lef $target_lef
    } else {
        read_lef [dict get $sc_cfg stdcell $lib lef]
    }
    set site [dict get $sc_cfg stdcell $lib site]
}
# Read design.
read_def $input_def

# Read SDC.
read_sdc $input_sdc


######################
# GLOBAL ROUTE
######################

set_global_routing_layer_adjustment $minmetal-$maxmetal 0.5
set_routing_layers -signal $minmetal-$maxmetal
set_macro_extension 2

global_route -guide_file ./route.guide \
    -overflow_iterations 100 \
    -verbose 2

######################
# Set RC estimation
######################

#TODO: parametrize
set_wire_rc -signal -layer metal3
set_wire_rc -clock  -layer metal5

######################
# Clock Propagation
######################

set_propagated_clock [all_clocks]
estimate_parasitics -global_routing


######################
# Detailed Route
######################
detailed_route -param $::env(OBJECTS_DIR)/TritonRoute.param

######################
# Report Metrics
######################
report_checks -path_delay min -fields {slew cap input nets fanout} -format full_clock_expanded
report_checks -path_delay max -fields {slew cap input nets fanout} -format full_clock_expanded
report_checks -unconstrained -fields {slew cap input nets fanout} -format full_clock_expanded
report_tns
report_wns
report_worst_slack
report_check_types -max_slew -max_capacitance -max_fanout -violators
report_clock_skew
report_power
report_design_area




# TritonRoute cannot read multiple LEF files, so merge them.
exec ./mergeLef.py --inputLef \
                   $techlef \
                   $pdklef \
                   --outputLef $output_lef

set param_file [open "route.params" "w"]
puts $param_file \
"guide:./$output_guide
outputDRC:./$output_drc
verbose:1"
close $param_file

set param_filepath [file normalize "route.params"]
puts $param_filepath

detailed_route -param $param_filepath


################################################################
# Reporting
################################################################

sc_write_reports $topmodule

################################################################
# Write Results
################################################################

#sc_write_outputs $topmodule
write_def $output_def
write_verilog $output_verilog
write_sdc $output_sdc
