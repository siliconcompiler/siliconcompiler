export DESIGN_NICKNAME = vanilla5
export DESIGN_NAME = bsg_manycore_tile
export PLATFORM    = tsmc65lp

export VERILOG_FILES = ./designs/src/$(DESIGN_NAME)/bsg_manycore_tile.sv2v.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg10_w32_all.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_2rf_lg5_w32_all.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg10_w32_byte.lef
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg10_w32_all_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_2rf_lg5_w32_all_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg10_w32_byte_ss_1p08v_1p08v_125c.lib
export ADDITIONAL_GDS  = $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg10_w32_all.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_2rf_lg5_w32_all.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg10_w32_byte.gds2

# These values must be multiples of placement site
export DIE_AREA    = 0 0 1100 400.8
export CORE_AREA   = 10 12 1090 391.2
