###############################
# Reading SC Schema
###############################

source ./sc_manifest.tcl

###############################
# Task Preamble
###############################

set sc_refdir [sc_cfg_tool_task_get refdir]
source "$sc_refdir/apr/preamble.tcl"

###############################
# Report and Repair Antennas
###############################

set ant_violations [check_antennas -report_file "reports/route/${sc_topmodule}.antenna.rpt"]

# A non-zero margin means fix nets that are merely close to the limit, so the repair
# has to be attempted even when check_antennas reports the design clean.
if {
    ($ant_violations != 0 || [sc_cfg_tool_task_get var ant_margin] > 0) &&
    [sc_cfg_tool_task_get var ant_repair] &&
    [sc_cfg_tool_task_get var ant_reroute_iterations] > 0
} {
    # Initializing the detailed router is not free, so only do it once a repair is
    # actually going to be attempted. The reroute needs the same configuration the
    # initial route used.
    sc_setup_detailed_route
    set drt_arguments [sc_detailed_route_args]

    if {
        [sc_repair_antennas \
            -reroute_iterations [sc_cfg_tool_task_get var ant_reroute_iterations] \
            -reroute {detailed_route {*}$drt_arguments}]
    } {
        # Check antennas again to get final report
        check_antennas -report_file "reports/route/${sc_topmodule}.antenna_post_repair.rpt"

        if { ![design_is_routed] } {
            utl::error FLW 1 "Design has unrouted nets after antenna repair"
        }
    }
}

# estimate for metrics
estimate_parasitics -global_routing

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
