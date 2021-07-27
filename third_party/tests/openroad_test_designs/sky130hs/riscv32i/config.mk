export DESIGN_NICKNAME = riscv32i
export DESIGN_NAME = riscv
export PLATFORM    = sky130hs

export VERILOG_FILES = $(sort $(wildcard ./designs/src/$(DESIGN_NICKNAME)/*.v))
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

# These values must be multiples of placement site
#export DIE_AREA    = 0 0 380 380.8
#export CORE_AREA   = 10 12 370 371.2
export CORE_UTILIZATION =30 
export CORE_ASPECT_RATIO = 1
export CORE_MARGIN = 2
#
export PLACE_DENSITY = 0.75
