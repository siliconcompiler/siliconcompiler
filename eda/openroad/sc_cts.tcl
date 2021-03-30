
########################################################
# SC setup (!!DO NOT EDIT THIS SECTION!!)
########################################################

set stage      "cts"
set last_stage "place"

source ./sc_setup.tcl

# Setting script path to local or refdir
set scriptdir [dict get $sc_cfg flow $stage refdir]
if {[dict get $sc_cfg flow $stage copy] eq True} {
    set scriptdir "./"
}
# Sourcing helper procedures
source $scriptdir/sc_procedures.tcl

set stackup      [dict get $sc_cfg asic stackup]
set topmodule    [dict get $sc_cfg design]
set target_libs  [dict get $sc_cfg asic targetlib]
set mainlib      [lindex $target_libs 0]
set libarch      [dict get $sc_cfg stdcell $mainlib libtype]
set techlef      [dict get $sc_cfg pdk aprtech $stackup $libarch openroad]
# TODO: Make these schema config values, and where to put lut/sol files.
# (These are some default freepdk45 OpenROAD values.)
set clock_nets   "clk"
set cts_buf      "BUF_X4"
set fillcells    "FILLCELL_X1 FILLCELL_X2 FILLCELL_X4 FILLCELL_X8 FILLCELL_X16 FILLCELL_X32"
set max_slew     1e-9
set max_cap      1e-9
set wire_unit    20
set parasitics_layer metal3

#Inputs
set input_verilog    "inputs/$topmodule.v"
set input_sdc        "inputs/$topmodule.sdc"
set input_def        "inputs/$topmodule.def"

#Outputs
set output_verilog  "outputs/$topmodule.v"
set output_def      "outputs/$topmodule.def"
set output_sdc      "outputs/$topmodule.sdc"

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
# CTS CORE SCRIPT
################################################################

# Clone clock tree inverters.
repair_clock_inverters

configure_cts_characterization -max_slew $max_slew \
                               -max_cap $max_cap

# Run CTS
clock_tree_synthesis -buf_list "$cts_buf" \
                     -clk_nets "$clock_nets" \
                     -wire_unit $wire_unit

set_propagated_clock [all_clocks]

filler_placement $fillcells
check_placement

# TODO: Programmable metal layer
set_wire_rc -layer $parasitics_layer

estimate_parasitics -placement
repair_clock_nets -buffer_cell "$cts_buf"

set_placement_padding -global
detailed_placement
optimize_mirroring
check_placement -verbose

estimate_parasitics -placement
repair_timing -hold

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
