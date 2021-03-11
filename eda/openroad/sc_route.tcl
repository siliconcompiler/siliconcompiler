
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
set stackup      [dict get $sc_cfg stackup]
set target_libs  [dict get $sc_cfg target_lib]
set mainlib      [lindex $target_libs 0]
set libarch      [dict get $sc_cfg stdcell $mainlib libtype]
set pdklef       [dict get $sc_cfg stdcell $mainlib lef]
set techlef      [dict get $sc_cfg pdk_aprtech $stackup $libarch openroad]
set topmodule    [dict get $sc_cfg design]
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

################################################################
# ROUTE CORE SCRIPT
################################################################

for {set layer 2} {$layer <= 10} {incr layer} {
  set_global_routing_layer_adjustment $layer 0.5
}

fastroute -layers 2-10 \
          -unidirectional_routing \
          -overflow_iterations 100 \
          -guide_file $output_guide \
          -verbose 2

write_def $output_tmp_def

# TritonRoute cannot read multiple LEF files, so merge them.
exec ./mergeLef.py --inputLef \
                   $techlef \
                   $pdklef \
                   --outputLef $output_lef

exec TritonRoute -lef $output_lef \
                 -guide $output_guide \
                 -def $output_tmp_def \
                 -output $output_def


################################################################
# Reporting
################################################################

sc_write_reports $topmodule

################################################################
# Write Results
################################################################

#sc_write_outputs $topmodule
#write_def $output_def
write_verilog $output_verilog
write_sdc $output_sdc
