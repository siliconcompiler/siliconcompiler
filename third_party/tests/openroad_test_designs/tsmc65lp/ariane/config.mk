export DESIGN_NAME = ariane
export PLATFORM    = tsmc65lp

export VERILOG_FILES = ./designs/src/$(DESIGN_NAME)/ariane.sv2v.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg8_w64_byte.lef
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg8_w64_byte_ss_1p08v_1p08v_125c.lib
export ADDITIONAL_GDS  = $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg8_w64_byte.gds2

# These values must be multiples of placement site
export DIE_AREA    = 0 0 2200 1560
export CORE_AREA   = 10 12 2190 1550.4
