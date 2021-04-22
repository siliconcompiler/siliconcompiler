###############################
# Python to TCL Interface
###############################

#Dictionary Configuration
source ./sc_schema.tcl

#Converting dictionary to scalars
source ./sc_adapter.tcl

###############################
# Openroad Setup
###############################
#1. Read lef/def/sdc
#2. Misc common settings

source ./sc_setup.tcl

###############################
# Select Execution Step
###############################
set verbose "-echo -verbose"
switch $sc_step {
    "floorplan" {
	source $verbose "./sc_floorplan.tcl"
    }
    "place" {
	source $verbose "./sc_place.tcl"
    }
    "cts" {
	source $verbose "./sc_cts.tcl"
    }
    "route" {
	source $verbose "./sc_route.tcl"
    }
}

###############################
# Reporting
###############################
source ./sc_report.tcl

###############################
# Write Design Data
###############################
source ./sc_write.tcl

