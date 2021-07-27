export DESIGN_NAME = gcd
export PLATFORM    = tsmc65lp

export VERILOG_FILES = ./designs/src/$(DESIGN_NAME)/gcd.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc

# These values must be multiples of placement site
export DIE_AREA    = 0 0 100 100.8
export CORE_AREA   = 10 12 90 91.2

export PLACE_DENSITY = 0.50
