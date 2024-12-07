###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl > /dev/null

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source -echo "$sc_refdir/apr/preamble.tcl"

###############################
# Do fill
###############################

set sc_libtype [sc_cfg_get library $sc_mainlib asic libarch]

if {
    $openroad_fin_add_fill == "true" &&
    [sc_cfg_exists pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype fill]
} {
    set sc_fillrules \
        [lindex [sc_cfg_get pdk $sc_pdk aprtech openroad $sc_stackup $sc_libtype fill] 0]
    density_fill -rules $sc_fillrules
}

# estimate for metrics
estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source -echo "$sc_refdir/apr/postamble.tcl"
