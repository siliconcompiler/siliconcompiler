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
# Error checking
###############################

if { [sc_design_has_unplaced_macros] } {
    utl::error FLW 1 "Design contains unplaced macros."
}

###############################
# Add blockages
###############################

set pdn_blockages []
set pdn_pin_keepout [lindex [sc_cfg_tool_task_get var fixed_pin_keepout] 0]
if { $pdn_pin_keepout > 0 } {
    foreach bterm [[ord::get_db_block] getBTerms] {
        foreach bpin [$bterm getBPins] {
            if {
                [$bpin getPlacementStatus] != "FIRM" &&
                [$bpin getPlacementStatus] != "LOCKED"
            } {
                continue
            }

            foreach box [$bpin getBoxes] {
                set layer [$box getTechLayer]
                if { $layer == "NULL" } {
                    continue
                }

                set tech_pitch [expr { [$layer getPitch] * $pdn_pin_keepout }]

                set xmin [expr { [$box xMin] - $tech_pitch }]
                set xmax [expr { [$box xMax] + $tech_pitch }]
                set ymin [expr { [$box yMin] - $tech_pitch }]
                set ymax [expr { [$box yMax] + $tech_pitch }]

                set blockage [odb::dbObstruction_create \
                    [ord::get_db_block] \
                    $layer \
                    $xmin $ymin \
                    $xmax $ymax]
                lappend pdn_blockages $blockage
            }
        }
    }

    utl::info FLW 1 "Added [llength $pdn_blockages] obstructions to pins"
}

###############################
# Power Network
###############################

set pdn_files []
foreach pdnconfig [sc_cfg_tool_task_get {file} pdn_config] {
    if { [lsearch -exact $pdn_files $pdnconfig] != -1 } {
        continue
    }
    puts "Sourcing PDNGEN configuration: ${pdnconfig}"
    source $pdnconfig

    lappend pdn_files $pdnconfig
}
tee -quiet -file reports/power_grid_configuration.rpt {pdngen -report_only}
pdngen -failed_via_report "reports/${sc_design}_pdngen_failed_vias.rpt"

###############################
# Check Power Network
###############################

foreach net [sc_supply_nets] {
    if { ![[[ord::get_db_block] findNet $net] isSpecial] } {
        utl::warn FLW 1 "$net_name is marked as a supply net, but is not marked as a special net"
    }
}

foreach net [sc_psm_check_nets] {
    puts "Check supply net: $net"

    set check_args []
    if {
        [sc_check_version 18610] &&
        [sc_cfg_tool_task_check_in_list $net var psm_allow_missing_terminal_nets]
    } {
        lappend check_args -dont_require_terminals
    }

    sc_report_args -command check_power_grid -args $check_args
    check_power_grid \
        -floorplanning \
        -error_file "reports/power_grid_${net}.rpt" \
        -net $net \
        {*}$check_args
}

###############################
# Remove blockages
###############################

if { [llength $pdn_blockages] > 0 } {
    foreach obstruction $pdn_blockages {
        odb::dbObstruction_destroy $obstruction
    }
    utl::info FLW 1 "Deleted [llength $pdn_blockages] obstructions"
}

###############################
# Task Postamble
###############################

source "$sc_refdir/apr/postamble.tcl"
