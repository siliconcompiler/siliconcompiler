###############################
# Reading SC Schema
###############################

source ./sc_schema.tcl

###############################
# Openroad Constants
###############################
set openroad_place_density 0.3

###############################
# Schema Adapter
###############################

#Handling remote/local script execution 
set sc_step   [dict get $sc_cfg status step]

if {[dict get $sc_cfg flow $sc_step copy] eq True} {
    set sc_refdir "."
} else {
    set sc_refdir [dict get $sc_cfg flow $sc_step refdir]
}
    
# Design
set sc_design     [lindex [dict get $sc_cfg design] end]
set sc_optmode     [lindex [dict get $sc_cfg optmode] end]



###############################
# Required
###############################

# APR Parameters		    
set sc_mainlib     [lindex [dict get $sc_cfg asic targetlib] 0]
set sc_targetlibs  [dict get $sc_cfg asic targetlib]
set sc_stackup     [lindex [dict get $sc_cfg asic stackup] end]
set sc_diesize     [dict get $sc_cfg asic diesize]
set sc_coresize    [dict get $sc_cfg asic coresize]
set sc_density     [lindex [dict get $sc_cfg asic density] end]
set sc_hpinlayer   [lindex [dict get $sc_cfg asic hpinlayer] end]
set sc_vpinlayer   [lindex [dict get $sc_cfg asic vpinlayer] end]
set sc_hpinmetal   [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_hpinlayer name]
set sc_vpinmetal   [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_vpinlayer name]
set sc_aspectratio [lindex [dict get $sc_cfg asic aspectratio] end]
set sc_minlayer    [lindex [dict get $sc_cfg asic minlayer] end]
set sc_maxlayer    [lindex [dict get $sc_cfg asic maxlayer] end]
set sc_maxfanout   [lindex [dict get $sc_cfg asic maxfanout] end]
set sc_maxlength   [lindex [dict get $sc_cfg asic maxlength] end]
set sc_maxcap      [lindex [dict get $sc_cfg asic maxcap] end]
set sc_maxslew     [lindex [dict get $sc_cfg asic maxslew] end]

#Library
set sc_libtype     [lindex [dict get $sc_cfg stdcell $sc_mainlib libtype] end]
set sc_site        [lindex [dict get $sc_cfg stdcell $sc_mainlib site] end]
set sc_driver      [lindex [dict get $sc_cfg stdcell $sc_mainlib driver] end]
set sc_filler      [dict get $sc_cfg stdcell $sc_mainlib cells filler]
set sc_dontuse     [dict get $sc_cfg stdcell $sc_mainlib cells ignore]
set sc_clkbuf      [dict get $sc_cfg stdcell $sc_mainlib cells clkbuf]
set sc_filler      [dict get $sc_cfg stdcell $sc_mainlib cells filler]
set sc_tie         [dict get $sc_cfg stdcell $sc_mainlib cells tie]
set sc_ignore      [dict get $sc_cfg stdcell $sc_mainlib cells ignore]
set sc_tapcell     [dict get $sc_cfg stdcell $sc_mainlib cells tapcell]
set sc_endcap      [dict get $sc_cfg stdcell $sc_mainlib cells endcap]

#PDK
set sc_techlef     [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libtype openroad]
set sc_minmetal    [lindex [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_minlayer name] end]
set sc_maxmetal    [lindex [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_maxlayer name] end]
set sc_tapmax      [lindex [dict get $sc_cfg pdk tapmax] end]
set sc_tapoffset   [lindex [dict get $sc_cfg pdk tapoffset] end]

###############################
# Optional
###############################

# MACROS
if {[dict exists $sc_cfg macrolib]} {    
    set sc_macrolibs    [dict get $sc_cfg asic macrolib]
} else {
    set sc_macrolibs    ""
}

# CONSTRAINTS
if {[dict exists $sc_cfg constraint]} {    
    set sc_constraint  [dict get $sc_cfg constraint]
} else {
    set sc_constraint  ""
}

# DEF
if {[dict exists $sc_cfg def]} {    
    set sc_def  [dict get $sc_cfg def]
} else {
    set sc_def  ""
}

# CLOCKS
if {[dict exists $sc_cfg clock]} { 
    set sc_clocks ""
    dict for {key value} [dict get $sc_cfg clock] {
	lappend sc_clocks $key
    }
    set sc_clocknets ""
    foreach clock $sc_clocks {
	lappend sc_clknets  [dict get $sc_cfg clock name]
    }
}

###############################
# Common Setup
###############################

# Techlef
read_lef  $sc_techlef

# Stdcells
foreach lib $sc_targetlibs {
    read_liberty [dict get $sc_cfg stdcell $lib model typical nldm lib]
    read_lef [dict get $sc_cfg stdcell $lib lef]
    set site [dict get $sc_cfg stdcell $lib site]
}

# Macrolibs
foreach lib $sc_macrolibs {
    read_liberty [dict get $sc_cfg macro $lib model typical nldm lib]
    read_lef [dict get $sc_cfg macro $lib lef]
}

# Floorplan reads synthesis verilog, others read def
if {$sc_step == "floorplan"} {
    read_verilog "inputs/$sc_design.v"
    link_design $sc_design
    foreach sdc $sc_constraint {
	read_sdc $sdc
    }
} else {    
    read_def "inputs/$sc_design.def"
    read_sdc "inputs/$sc_design.sdc"
}

###############################
# Source Step Script
###############################

source -echo -verbose "$sc_refdir/sc_$sc_step.tcl"

###############################
# Reporting
###############################

source -echo -verbose "$sc_refdir/sc_report.tcl"

###############################
# Write Design Data
###############################

source -echo -verbose "$sc_refdir/sc_write.tcl"

