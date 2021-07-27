export DESIGN_NAME = gcd
export PLATFORM    = nangate45

export VERILOG_FILES = ./designs/src/$(DESIGN_NAME)/gcd.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc

# Adders degrade GCD
export ADDER_MAP_FILE :=

# These values must be multiples of placement site
# x=0.19 y=1.4
export DIE_AREA    = 0 0 100.13 100.8
export CORE_AREA   = 10.07 11.2 90.25 91

