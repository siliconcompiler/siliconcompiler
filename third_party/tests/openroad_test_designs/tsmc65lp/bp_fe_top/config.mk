export DESIGN_NICKNAME = bp_fe
export DESIGN_NAME = bp_fe_top
export PLATFORM    = tsmc65lp

export VERILOG_FILES = ./designs/src/$(DESIGN_NAME)/pickled.v \
                       ./designs/$(PLATFORM)/$(DESIGN_NAME)/macros.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/constraint.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg6_w8_bit.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg6_w96_bit.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg9_w64_bit.lef \
                         $(PLATFORM_DIR)/lef/tsmc65lp_1rf_lg9_w64_all.lef
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg6_w8_bit_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg6_w96_bit_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg9_w64_bit_ss_1p08v_1p08v_125c.lib \
                         $(PLATFORM_DIR)/lib/tsmc65lp_1rf_lg9_w64_all_ss_1p08v_1p08v_125c.lib
export ADDITIONAL_GDS  = $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg6_w8_bit.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg6_w96_bit.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg9_w64_bit.gds2 \
                         $(PLATFORM_DIR)/gds/tsmc65lp_1rf_lg9_w64_all.gds2

# These values must be multiples of placement site
export DIE_AREA    = 0 0 1200 1000.8
export CORE_AREA   = 10 12 1190 991.2

export PLACE_DENSITY = 0.37
