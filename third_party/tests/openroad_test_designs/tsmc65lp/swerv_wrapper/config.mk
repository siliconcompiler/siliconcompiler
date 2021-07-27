export DESIGN_NAME = swerv_wrapper
export PLATFORM    = tsmc65lp

export VERILOG_FILES = ./designs/src/swerv/swerv_wrapper.sv2v.v \
                       ./designs/$(PLATFORM)/$(DESIGN_NAME)/macros.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg11_w40_all.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg6_w22_all.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg8_w34_all.lef
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg11_w40_all_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg6_w22_all_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg8_w34_all_ss_1p08v_1p08v_125c.lib
export ADDITIONAL_GDS  = $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg11_w40_all.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg6_w22_all.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg8_w34_all.gds2

export REMOVE_BUFFER_TREE     = 1

# These values must be multiples of placement site
export DIE_AREA    = 0 0 2000 2000
export CORE_AREA   = 5 5 1995 1995

export PLACE_DENSITY ?= .4
export MACRO_BLOCKAGE_HALO    = 60
