###############################
# Reading Schema
###############################

source ./sc_schema.tcl

###############################
# Schema Adaptet
###############################

#Handling remote/local script execution 
set sc_step   [dict get $sc_cfg status step]

if {[dict get $sc_cfg flow $sc_step copy] eq True} {
    set sc_refdir "."
} else {
    set sc_refdir [dict get $sc_cfg flow $sc_step refdir]
}
    
set sc_step        [dict get $sc_cfg status step]
set sc_design      [dict get $sc_cfg design]
set sc_optmode     [dict get $sc_cfg optmode]

set sc_stackup     [dict get $sc_cfg asic stackup]
set sc_targetlib   [dict get $sc_cfg asic targetlib]
set sc_diesize     [dict get $sc_cfg asic diesize]
set sc_coresize    [dict get $sc_cfg asic coresize]
set sc_minlayer    [dict get $sc_cfg asic minlayer]
set sc_maxlayer    [dict get $sc_cfg asic maxlayer]

set sc_mainlib     [lindex $sc_targetlib 0]
set sc_libarch     [dict get $sc_cfg stdcell $sc_mainlib libtype]
set sc_site        [dict get $sc_cfg stdcell $sc_mainlib site]

set sc_minmetal    [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_minlayer name]
set sc_maxmetal    [dict get $sc_cfg pdk aprlayer $sc_stackup $sc_maxlayer name]
set sc_techlef     [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libarch openroad]
set sc_filler      [dict get $sc_cfg pdk aprtech $sc_stackup $sc_libarch openroad]
set sc_tapmax      [dict get $sc_cfg pdk tapmax]
set sc_tapoffset   [dict get $sc_cfg pdk tapoffset]

if {[dict exists $sc_cfg macrolib]} {    
    set sc_macrolib    [dict get $sc_cfg asic macrolib]
} else {
    set sc_macrolib    ""
}

if {[dict exists $sc_cfg constraint]} {    
    set sc_constraint  [dict get $sc_cfg constraint]
} else {
    set sc_constraint  ""
}
if {[dict exists $sc_cfg def]} {    
    set sc_def  [dict get $sc_cfg def]
} else {
    set sc_def  ""
}

###############################
# Common Setup
###############################

# Techlef
read_lef  $sc_techlef

# Stdcells
foreach lib $sc_targetlib {
    read_liberty [dict get $sc_cfg stdcell $lib model typical nldm lib]
    read_lef [dict get $sc_cfg stdcell $lib lef]
    set site [dict get $sc_cfg stdcell $lib site]
}

# Macrolibs
foreach lib $sc_macrolib {
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

