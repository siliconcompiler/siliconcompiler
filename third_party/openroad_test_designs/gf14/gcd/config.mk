export DESIGN_NICKNAME = gcd_$(TRACK_OPTION)_$(TECH_OPTION)
export DESIGN_NAME = gcd
export PLATFORM    = gf14

export VERILOG_FILES = ./designs/src/$(DESIGN_NAME)/gcd.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc

# These values must be multiples of placement site
export DIE_AREA    = 0 0 99.96 100.128
export CORE_AREA   = 9.996 10.08 89.964 90.048

export GLOBAL_PLACEMENT_ARGS = -skip_initial_place
